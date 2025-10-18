import { Duration, Stack, StackProps } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as path from "path";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as sns from "aws-cdk-lib/aws-sns";
import * as iam from "aws-cdk-lib/aws-iam";

export class StockBotStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    // 1️⃣ S3 bucket to store the static prompt / trading rules
    const rulesBucket = new s3.Bucket(this, "TradingRulesBucket", {
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
    });

    // 2️⃣ SNS Topic for outbound alerts
    const alertsTopic = new sns.Topic(this, "TradeAlertsTopic", {
      displayName: "StockBot Trade Recommendations",
    });

    // 3️⃣ Lambda: Notification
    const notificationLambda = new lambda.Function(this, "NotificationLambda", {
      functionName: "StockBotNotificationLambda",
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "index.handler",
      code: lambda.Code.fromAsset(
        path.join(__dirname, "..", "lambda", "notification")
      ),
      timeout: Duration.seconds(30),
      memorySize: 256,
      environment: {
        TOPIC_ARN: alertsTopic.topicArn,
      },
    });

    // 4️⃣ Lambda: Invocation / Orchestrator
    const invocationLambda = new lambda.Function(this, "InvocationLambda", {
      functionName: "StockbotInvocationLambda",
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "index.handler",
      code: lambda.Code.fromAsset(
        path.join(__dirname, "..", "lambda", "invocation")
      ),
      timeout: Duration.seconds(60),
      memorySize: 512,
      environment: {
        RULES_BUCKET_NAME: rulesBucket.bucketName,
        MCP_FUNCTION_NAME: "StockBotMCPLambda",
        NOTIFICATION_FUNCTION_NAME: "StockBotNotificationLambda",
      },
    });

    // 5️⃣ Lambda: MCP (data fetcher)
    const mcpLambda = new lambda.Function(this, "MCPLambda", {
      functionName: "StockBotMCPLambda",
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "index.handler",
      code: lambda.Code.fromAsset(path.join(__dirname, "..", "lambda", "mcp")),
      timeout: Duration.seconds(60),
      memorySize: 512,
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
    mcpLambda.grantInvoke(invocationLambda);
    notificationLambda.grantInvoke(invocationLambda);

    // Grant all necessary notification Lambda permissions
    alertsTopic.grantPublish(notificationLambda);

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
