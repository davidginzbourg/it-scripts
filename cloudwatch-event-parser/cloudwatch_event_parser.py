import os
import json
import logging

import boto3

ACCOUNTS = {


}
SOURCE = os.getenv('SOURCE')
TO_ADDRESSES = [os.getenv('TO_ADDRESS')]
DESTINATION = {'ToAddresses': TO_ADDRESSES}

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ses_client = boto3.client('ses', region_name='eu-west-1')


def main(event, context):
    """Parses the SNS message into a JSON format.
    Main handler.
    """
    sns_message = None
    logger.info('Handling event ' + json.dumps(event))
    sns_message = event['Records'][0]['Sns']['Message']

    sns_message = json.loads(sns_message)
    send_email(sns_message)


def send_email(sns_message):
    """Sends an email of the sns_message

    :param sns_message: sns message in JSON format
    """
    subject = 'Attention required - AWS account ' + ACCOUNTS[
        sns_message['account']]
    logger.info('Building message HTML...')
    message_html = '<html><body><h3>Description</h3>'

    for description in sns_message['detail']['eventDescription']:
        message_html += '<p>'
        message_html += description['latestDescription']
        message_html += '</p>'

    message_html += '<h3>Affected resources</h3>'

    message_html += '<p>'
    for entity in sns_message['detail']['affectedEntities']:
        message_html += entity['entityValue'] + '\n'
    message_html += '</p>'

    message_html += '</body></html>'

    message_id = ses_client.send_email(Source=SOURCE, Destination=DESTINATION,
                                       Message={
                                           'Subject': {'Data': subject},
                                           'Body': {
                                               'Html': {'Data': message_html}}
                                       })['MessageId']
    logger.info('Sent a message, ID: ' + message_id)
