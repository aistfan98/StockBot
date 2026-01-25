import os
import boto3

s3_client = boto3.client("s3")

def fetch_prompt_from_s3():
    """
    Fetch the prompt from S3 and return both the text and version ID.

    Returns:
        tuple: (prompt_text, version_id)
    """
    bucket_name = os.environ["RULES_BUCKET_NAME"]
    obj = s3_client.get_object(Bucket=bucket_name, Key="prompt.txt")
    prompt_text = obj["Body"].read().decode("utf-8")
    version_id = obj.get("VersionId", "unknown")

    return prompt_text, version_id