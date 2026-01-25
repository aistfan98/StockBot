import os
import uuid
import boto3
from datetime import datetime
from typing import Dict, List

dynamodb = boto3.resource("dynamodb")


def save_portfolio_to_dynamodb(
    data_date: str,
    portfolio_id: str,
    prompt_version: str,
    raw_output: str,
    stocks: List[Dict],
    stock_count: int,
    sectors: Dict[str, float],
    risk_balance: Dict[str, float],
    market_context: str,
    orchestrator_lambda_request_id: str,
    report_generation_duration: str,
    model_used: str,
    status: str,
    email_sent: bool,
) -> bool:
    """
    Save portfolio data to DynamoDB asynchronously (fire and forget).

    Args:
        data_date: ISO week number (e.g., "2026-W01")
        portfolio_id: Unique portfolio identifier
        prompt_version: S3 version ID of the prompt
        raw_output: Raw AI response text
        stocks: List of stock dictionaries
        stock_count: Number of stocks in portfolio
        sectors: Sector name to percentage mapping
        risk_balance: Risk category to percentage mapping
        market_context: Market summary paragraph
        orchestrator_lambda_request_id: AWS Lambda request ID from orchestrator
        report_generation_duration: Human-readable duration (e.g., "5m 10s")
        model_used: Bedrock model identifier
        status: "success" or "error"
        email_sent: Whether the email notification was successfully sent

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        table_name = os.environ["PORTFOLIO_TABLE_NAME"]
        table = dynamodb.Table(table_name)

        # All numeric values are already Decimal types from parser
        item = {
            "data_date": data_date,
            "portfolio_id": portfolio_id,
            "prompt_version": prompt_version,
            "raw_output": raw_output,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "stocks": stocks,
            "stock_count": stock_count,
            "sectors": sectors,
            "risk_balance": risk_balance,
            "market_context": market_context,
            "orchestrator_lambda_request_id": orchestrator_lambda_request_id,
            "report_generation_duration": report_generation_duration,
            "model_used": model_used,
            "status": status,
            "email_sent": email_sent,
        }

        table.put_item(Item=item)
        print(
            f"[DynamoDB] Successfully saved portfolio {portfolio_id} for date {data_date}"
        )
        return True

    except Exception as e:
        # Log error but don't raise - this is fire-and-forget
        print(f"[DynamoDB ERROR] Failed to save portfolio: {str(e)}")
        print(f"[DynamoDB ERROR] Portfolio ID: {portfolio_id}, Date: {data_date}")
        return False
