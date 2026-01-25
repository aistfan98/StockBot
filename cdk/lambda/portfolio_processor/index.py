import os
import boto3

from parser import parse_portfolio
from storage import save_portfolio_to_dynamodb

sns = boto3.client("sns")


def handler(event, context):
    """
    Portfolio Processor Lambda entry point.

    Receives portfolio data from the invocation Lambda and:
    1. Sends email notification with raw output. Sending the email before any
    processing to ensure subscribers always get notified regardles of
    parsing/storage success.
    2. Parses the raw output into structured data
    3. Saves parsed portfolio to DynamoDB

    Expected event payload:
    {
        "raw_output": str,                       # Raw Bedrock response
        "prompt_version": str,                   # S3 version ID
        "data_date": str,                        # ISO week (e.g., "2026-W04")
        "portfolio_id": str,                     # UUID from orchestrator
        "orchestrator_lambda_request_id": str,   # Orchestrator's request ID
        "report_generation_duration": str,       # Human-readable duration (e.g., "5m 10s")
        "model_used": str                        # Model identifier
    }
    """
    topic_arn = os.environ["TOPIC_ARN"]

    # Extract payload from invocation Lambda
    raw_output = event.get("raw_output", None)
    prompt_version = event.get("prompt_version", "unknown")
    data_date = event.get("data_date", "unknown")
    portfolio_id = event.get("portfolio_id", "unknown")
    orchestrator_lambda_request_id = event.get("orchestrator_lambda_request_id", "unknown")
    report_generation_duration = event.get("report_generation_duration", "unknown")
    model_used = event.get("model_used", "unknown")

    # Extract week info from data_date for email subject (e.g., "2026-W04" -> "Week 4, 2026")
    try:
        year, week_part = data_date.split("-W")
        week_num = int(week_part)
        subject = f"Week {week_num}, {year} Report"
    except (ValueError, AttributeError):
        subject = "StockBot Weekly Report"

    # 1. SEND EMAIL FIRST - ensures subscribers always get notified
    email_sent = False
    try:
        if raw_output is not None:
            response = sns.publish(
                TopicArn=topic_arn,
                Message=raw_output,
                Subject=subject
            )
            email_sent = True
            print(f"[PROCESSOR] Email sent successfully. MessageId: {response['MessageId']}")
        else:
            raise Exception("Orchestrator did not provide raw output")
    except Exception as e:
        print(f"[PROCESSOR ERROR] Failed to send email: {e}")

    # 2. PARSE the raw output into structured data
    parsed = parse_portfolio(raw_output)
    print(f"[PROCESSOR] Parsed {len(parsed.get('stocks', []))} stocks")

    # 3. SAVE to DynamoDB
    try:
        save_portfolio_to_dynamodb(
            data_date=data_date,
            portfolio_id=portfolio_id,
            prompt_version=prompt_version,
            raw_output=raw_output,
            stocks=parsed["stocks"],
            stock_count=parsed["summary"]["stock_count"],
            sectors=parsed["summary"]["sectors"],
            risk_balance=parsed["summary"]["risk_balance"],
            market_context=parsed["summary"]["market_context"],
            orchestrator_lambda_request_id=orchestrator_lambda_request_id,
            report_generation_duration=report_generation_duration,
            model_used=model_used,
            status="success",
            email_sent=email_sent,
        )
        print(f"[PROCESSOR] Portfolio saved to DynamoDB: {portfolio_id}")
    except Exception as e:
        print(f"[PROCESSOR ERROR] Failed to save to DynamoDB: {e}")

    return {
        "statusCode": 200,
        "body": {
            "portfolio_id": portfolio_id,
            "data_date": data_date,
            "stocks_parsed": len(parsed.get("stocks", [])),
            "email_sent": email_sent
        }
    }
