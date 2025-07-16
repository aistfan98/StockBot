import * as cdk from "aws-cdk-lib";
import { StockBotStack } from "../lib/app";

const app = new cdk.App();
new StockBotStack(app, "StockBotStack", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});
