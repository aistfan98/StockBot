import { Duration, Stack, StackProps, RemovalPolicy } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as path from "path";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as sns from "aws-cdk-lib/aws-sns";
import * as iam from "aws-cdk-lib/aws-iam";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";

export class StockBotStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    // 1️⃣ S3 bucket to store the static prompt / trading rules
    const rulesBucket = new s3.Bucket(this, "TradingRulesBucket", {
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    // 2️⃣ DynamoDB table for portfolio history
    const portfolioTable = new dynamodb.Table(this, "PortfolioHistoryTable", {
      tableName: "StockBotPortfolios",
      partitionKey: { name: "portfolio_id", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "data_date", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      removalPolicy: RemovalPolicy.RETAIN,
    });

    // 3️⃣ SNS Topic for outbound alerts
    const alertsTopic = new sns.Topic(this, "TradeAlertsTopic", {
      displayName: "StockBot Trade Recommendations",
    });

    // 4️⃣ Lambda: Portfolio Processor (email -> parse -> store)
    const portfolioProcessorLambda = new lambda.Function(this, "PortfolioProcessorLambda", {
      functionName: "StockBotPortfolioProcessorLambda",
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "index.handler",
      code: lambda.Code.fromAsset(
        path.join(__dirname, "..", "lambda", "portfolio_processor")
      ),
      timeout: Duration.seconds(60),
      memorySize: 256,
      environment: {
        TOPIC_ARN: alertsTopic.topicArn,
        PORTFOLIO_TABLE_NAME: portfolioTable.tableName,
      },
    });

    // Create a secret to store the Finnhub API key
    const finnhubSecret = new secretsmanager.Secret(this, "FinnhubApiKey", {
      secretName: "FinnhubApiKey",
      description: "API key used by StockBot to call Finnhub",
    });

    // 5️⃣ Lambda: Invocation / Orchestrator
    const invocationLambda = new lambda.Function(this, "InvocationLambda", {
      functionName: "StockbotInvocationLambda",
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "index.handler",
      code: lambda.Code.fromAsset(
        path.join(
          __dirname,
          "..",
          "lambda",
          "invocation",
          "deployed_assets.zip"
        )
      ),
      timeout: Duration.seconds(900),
      memorySize: 512,
      environment: {
        RULES_BUCKET_NAME: rulesBucket.bucketName,
        PROCESSOR_FUNCTION_NAME: "StockBotPortfolioProcessorLambda",
        FINNHUB_API_KEY_SECRET_ARN: finnhubSecret.secretArn,
      },
    });

    // Grant all necessary invocation Lambda permissions
    rulesBucket.grantRead(invocationLambda);
    invocationLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ],
        resources: ["*"],
      })
    );
    portfolioProcessorLambda.grantInvoke(invocationLambda);
    finnhubSecret.grantRead(invocationLambda);

    // Grant all necessary portfolio processor Lambda permissions
    alertsTopic.grantPublish(portfolioProcessorLambda);
    portfolioTable.grantWriteData(portfolioProcessorLambda);

    // 6️⃣ EventBridge rule – daily at 14:00 UTC, Mon‑Fri
    const scheduleRule = new events.Rule(this, "WeeklyTriggerRule", {
      schedule: events.Schedule.cron({
        minute: "0", // 0th minute
        hour: "2", // 2:00 UTC = 8 PM central time previous day (SUN)
        weekDay: "MON",
      }),
    });

    scheduleRule.addTarget(new targets.LambdaFunction(invocationLambda));
  }
}
