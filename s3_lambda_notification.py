import boto3
import time
import urllib

s3 = boto3.client('s3')
sns = boto3.client(service_name="sns")

def lambda_handler(event, context):
    # Get the object from the event and show its content
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.unquote_plus(event['Records'][0]['s3']['object']['key'].encode('utf8'))
    time = event['Records'][0]['eventTime']
    user = event['Records'][0]['userIdentity']['principalId']
    operation = event['Records'][0]['eventName']
    #Message
    message = "\n\nBucket Name:\t " + bucket + "\n\n File Name:\t " + key + "\n\n Operation DateTimeStamp:\t " + time + "\n\n User who performed the Operation:\t " + user + "\n\n Operation:\t " + operation
    #ARN of SNS Topic
    topicArn = 'arn:aws:sns:us-east-1:328115522647:S3-Notification'
    sns.publish(
        TopicArn = topicArn,
        Message = message
    )
    return
