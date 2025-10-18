import os, json
import boto3

lambda_client = boto3.client("lambda")

def handler(event, context):
    notification_function_name = os.environ["NOTIFICATION_FUNCTION_NAME"]

    payload = {
        "message": "Hello world! This is coming from the invocation lambda!"
    }

    lambda_client.invoke(
        FunctionName=notification_function_name,
        InvocationType="Event",  # async
        Payload=json.dumps(payload)
    )