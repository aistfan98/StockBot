import os
import boto3
import datetime

# Create an SNS client
sns = boto3.client("sns")

def handler(event, context):
    """
    Lambda entry point.
    Publishes a simple 'Hello world' message to the SNS topic.
    """
    topic_arn = os.environ["TOPIC_ARN"]

    today = datetime.datetime.today()
    year = today.isocalendar()[0]
    week_num = today.isocalendar()[1]

    message = event.get("message", "Error! Could not find notification text!")
    subject = f"Week {week_num}, {year} Report"

    # Publish the message to the SNS topic
    response = sns.publish(
        TopicArn=topic_arn,
        Message=message,
        Subject=subject
    )

    print(f"Published message ID: {response['MessageId']}")
    return {
        "statusCode": 200,
        "body": f"Message sent to SNS topic {topic_arn}"
    }
