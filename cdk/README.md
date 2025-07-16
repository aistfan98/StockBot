# StockBot CDK

> Infrastructure‑as‑Code for the StockBot trading‑assistant backend.

```bash
# Bootstrap your AWS environment (once per account/region)
cdk bootstrap aws://<ACCOUNT>/<REGION>

# Install dependencies
npm install

# Synth the CloudFormation templates
npm run build && cdk synth

# Deploy (creates/modifies stacks)
cdk deploy
```

### Environment Variables

Each Lambda picks up needed values via their `process.env.*` variables.

### Next Steps

- Point _Invocation Lambda_ at your prompt‑fetch/Bedrock invocation logic.
- Replace placeholder handlers with your production code.
- Add real SNS subscriptions (email, SMS, SQS, or Lambda targets).
- Fine‑tune IAM policies for least‑privilege.
