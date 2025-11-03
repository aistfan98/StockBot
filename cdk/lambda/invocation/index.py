import os, json
import boto3
from agent import invoke_agent
from prompt import fetch_prompt_from_s3

lambda_client = boto3.client("lambda")

def handler(event, context):
    notification_function_name = os.environ["NOTIFICATION_FUNCTION_NAME"]

    prompt = fetch_prompt_from_s3()

    bedrock_response = invoke_agent(prompt)

    lambda_payload = {
        "message": str(bedrock_response)
    }

    lambda_client.invoke(
        FunctionName=notification_function_name,
        InvocationType="Event",  # async
        Payload=json.dumps(lambda_payload)
    )