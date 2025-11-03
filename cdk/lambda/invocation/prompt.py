import os
import boto3

s3_client = boto3.client("s3")

def fetch_prompt_from_s3():
    bucket_name = os.environ["RULES_BUCKET_NAME"]
    obj = s3_client.get_object(Bucket=bucket_name, Key="prompt.txt")
    prompt_text = obj["Body"].read().decode("utf-8")

    return prompt_text