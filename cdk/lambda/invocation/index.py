import os
import json
import boto3
import datetime
import uuid
from agent import invoke_agent, MODEL_USED
from prompt import fetch_prompt_from_s3

lambda_client = boto3.client("lambda")


def handler(event, context):
    # Track execution start time
    start_time = datetime.datetime.now()

    processor_function_name = os.environ["PROCESSOR_FUNCTION_NAME"]

    # Fetch prompt and capture version ID
    prompt_text, prompt_version = fetch_prompt_from_s3()
    print(f"[MAIN] Fetched prompt version: {prompt_version}")

    # Invoke agent
    bedrock_response = invoke_agent(prompt_text)
    raw_output = str(bedrock_response)
    print(f"[MAIN] Received bedrock response ({len(raw_output)} chars)")

    # Generate identifiers - single source of truth for date/ID
    today = datetime.datetime.today()
    year = today.isocalendar()[0]
    week_num = today.isocalendar()[1]
    data_date = f"{year}-W{week_num:02d}"

    portfolio_id = str(uuid.uuid4())
    print(f"[MAIN] Portfolio ID: {portfolio_id}, Date: {data_date}")

    # Calculate report generation duration in human-readable format
    duration_seconds = int((datetime.datetime.now() - start_time).total_seconds())
    minutes = duration_seconds // 60
    seconds = duration_seconds % 60
    report_generation_duration = f"{minutes}m {seconds}s"

    # Invoke processor Lambda asynchronously with full context
    processor_payload = {
        "raw_output": raw_output,
        "prompt_version": prompt_version,
        "data_date": data_date,
        "portfolio_id": portfolio_id,
        "orchestrator_lambda_request_id": context.aws_request_id,
        "report_generation_duration": report_generation_duration,
        "model_used": MODEL_USED,
    }

    lambda_client.invoke(
        FunctionName=processor_function_name,
        InvocationType="Event",  # async
        Payload=json.dumps(processor_payload),
    )

    print(f"[MAIN] Processor Lambda invoked. Execution complete.")

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "portfolio_id": portfolio_id,
                "data_date": data_date,
                "report_generation_duration": report_generation_duration,
            }
        ),
    }
