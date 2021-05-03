import json
import boto3
import email
import re
from sms_spam_classifier_utilities import one_hot_encode
from sms_spam_classifier_utilities import vectorize_sequences
from botocore.exceptions import ClientError
import time
import os

def lambda_handler(event, context):
    # Update
    EndpointName = os.environ['myEnvParameterEndpointName']

    objectKey = event["Records"][0]["s3"]["object"]["key"]
    bucket = 'hw3-spam-detection-email-s1-cf'
    s3 = boto3.resource('s3')
    obj = s3.Object(bucket, objectKey)
    msg = obj.get()['Body'].read().decode('utf-8')
    msg = email.message_from_string(msg)

    pay_load_text = ''
    if msg.is_multipart():
        for part in msg.get_payload():
            if part.get_content_type() == 'text/plain':
                pay_load_text = part.get_payload()
    else:
        pay_load_text = msg.get_payload()

    EMAIL_BODY = pay_load_text
    messages = re.sub('[ \n\r\t\f]+', ' ', pay_load_text).replace('*', '').strip()
    print(messages)
    EMAIL_RECEIVE_DATE = msg['Date']
    EMAIL_SUBJECT = msg['Subject']
    EMAIL_FROM = msg['from']

    # EMAIL_BODY = "FreeMsg: Txt: CALL to No: 86888 & claim your reward of 3 hours talk time to use from your phone now! ubscribe6GBP/ mnth inc 3hrs 16 stop?txtStop"
    # EMAIL_BODY = re.sub('[ \t\n]+', ' ', EMAIL_BODY).replace('*', '').strip()
    # print(EMAIL_BODY)
    # # EMAIL_BODY = "I am Jim."
    # EMAIL_RECEIVE_DATE = 'Fri, 26 Mar 2021 05:58:41 +0000'
    # EMAIL_SUBJECT = 'Dummy email subject'
    # EMAIL_FROM = 'iPhone5 A1429 <iphone5a1429@gmail.com>'

    # Encode to narray
    vocabulary_length = 9013
    messages = [messages]
    one_hot_messages = one_hot_encode(messages, vocabulary_length)
    encoded_messages = vectorize_sequences(one_hot_messages, vocabulary_length)
    payload = json.dumps(encoded_messages.tolist())

    # Predict by SageMaker
    client = boto3.client('sagemaker-runtime')
    response = client.invoke_endpoint(
    EndpointName=EndpointName,
    Body=payload,
    ContentType='application/json'
    )

    result = json.loads(response['Body'].read().decode())
    CLASSIFICATION_CONFIDENCE_SCORE = result['predicted_probability'][0][0]
    predicted_label = result['predicted_label'][0][0]
    CLASSIFICATION = 'ham'
    if predicted_label == 0:
        CLASSIFICATION = 'ham'
        CLASSIFICATION_CONFIDENCE_SCORE = 1 - CLASSIFICATION_CONFIDENCE_SCORE
    else:
        CLASSIFICATION = 'spam'

    # Reply to the sender of the email
    # Amazon SES
    SENDER = "iPhone5 A1429 <iphone5a1429@gmail.com>"
    RECIPIENT = EMAIL_FROM
    AWS_REGION = "us-east-1"
    SUBJECT = 'Spam detection of ' + EMAIL_SUBJECT

    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = ("We received your email sent at " + EMAIL_RECEIVE_DATE + " with the subject " + EMAIL_SUBJECT + ".\n\n"
    + "Here is the email body:\n"
    + EMAIL_BODY + "\n\n"
    + "The email was categorized as " + CLASSIFICATION + " with a " + str(float(CLASSIFICATION_CONFIDENCE_SCORE) * 100) + "% confidence.")

    # The character encoding for the email.
    CHARSET = "UTF-8"

    client = boto3.client(
        'ses',
        region_name=AWS_REGION,
        aws_access_key_id='aws_access_key_id',
        aws_secret_access_key='aws_secret_access_key'
    )

    # Try to send the email.
    try:
        #Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
            # If you are not using a configuration set, comment or delete the
            # following line
            # ConfigurationSetName=CONFIGURATION_SET,
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:")
        print(response['MessageId'])

    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
