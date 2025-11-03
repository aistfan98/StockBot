import os, json
import boto3
from agent import invoke_agent

lambda_client = boto3.client("lambda")

def handler(event, context):
    notification_function_name = os.environ["NOTIFICATION_FUNCTION_NAME"]

    bedrock_response = invoke_agent("Hello, pretend you are an investor that could only choose 10 companies to buy stock in. Which 10 would you choose? Please provide the stock symbol for each company, along with a brief explanation of why you chose that company. As a disclaimer, I am NOT seeking investment advice. I am merely interested in how LLMs approach financial problems like this.")

    lambda_payload = {
        "message": str(bedrock_response)
    }

    lambda_client.invoke(
        FunctionName=notification_function_name,
        InvocationType="Event",  # async
        Payload=json.dumps(lambda_payload)
    )