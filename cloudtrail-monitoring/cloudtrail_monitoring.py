import os
import re
import json
import gzip
import logging
import tempfile
import time
from datetime import datetime

import boto3
import botocore
import gspread
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CONFIG_FILE_PATH = os.environ.get('CONFIG_FILE_PATH')
if not CONFIG_FILE_PATH:
    raise Exception('No CONFIG_FILE_PATH provided in OS ENV VARS')
ROLE_SESSION_NAME = os.environ.get('ROLE_SESSION_NAME')
if not ROLE_SESSION_NAME:
    raise Exception('No ROLE_SESSION_NAME provided in OS ENV VARS')

SCOPES = ['https://spreadsheets.google.com/feeds']
CREDENTIALS_FILE_PATH = os.environ.get('CREDENTIALS_FILE_PATH')
if not CREDENTIALS_FILE_PATH:
    raise Exception('No CREDENTIALS_FILE_PATH provided in OS ENV VARS')
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
if not SPREADSHEET_ID:
    raise Exception('No SPREADSHEET_ID provided in OS ENV VARS')
WORKSHEET_NAME = os.environ.get('WORKSHEET_NAME')
if not WORKSHEET_NAME:
    raise Exception('No WORKSHEET_NAME provided in OS ENV VARS')
COLUMNS = {
    'BUCKET_NAME': 0,
    'CREATED_BY': 1,
    'CREATED_AT': 2,
    'WEIGHT': 3,
    'ACCOUNT': 4,
    'REGION': 5
}

ACCOUNT_DETAILS = {
    '11111': {'RoleArn': os.getenv('11111111' + '_RoleArn'),
              'BucketName': os.getenv('11111111' + '_BucketName')},
    '22222': {'RoleArn': os.getenv('22222' + '_RoleArn'),
              'BucketName': os.getenv('22222' + '_BucketName')},
}

S3_CLIENTS = {
}
# In seconds
REFRESH_PERIOD = 3500
BOTOCORE_CONFIG = botocore.client.Config(connect_timeout=5, read_timeout=5)

credentials = ServiceAccountCredentials.from_json_keyfile_name(
    CREDENTIALS_FILE_PATH, scopes=SCOPES)
gc = gspread.authorize(credentials)

def set_credentials(sts_client):
    """Sets the S3 CLIENTS dictionary.

    :param sts_client: sts client to use.
    """
    for account_num, account_details in ACCOUNT_DETAILS.items():
        cred = sts_client.assume_role(
            RoleArn=account_details['RoleArn'],
            RoleSessionName=ROLE_SESSION_NAME)['Credentials']
        boto3_kwargs = {
            'aws_access_key_id': cred['AccessKeyId'],
            'aws_secret_access_key': cred['SecretAccessKey'],
            'aws_session_token': cred['SessionToken']
        }
        S3_CLIENTS[account_num] = boto3.client('s3',
                                               config=BOTOCORE_CONFIG,
                                               **boto3_kwargs)
    global credentials_last_refresh
    credentials_last_refresh = time.time()


sts_client = boto3.client('sts', config=BOTOCORE_CONFIG)
set_credentials(sts_client)


def get_current_account_number(event):
    """
    :param event: event to parse.
    :return: the current account number it's dealing with.
    """
    arn = event['Sns']['TopicArn']
    pattern = re.compile('[0-9a-z-_]+')
    return pattern.findall(arn)[4]


def get_config():
    """Loads the config from the local path provided.

    :return: returns the dict representing the configuration file stored in S3.
    """
    with open(CONFIG_FILE_PATH, 'r') as f:
        return json.load(f)


def get_events(event):
    """Gets the objects that were put - the ones that caused this script to be
    invoked.

    :param event: the given AWS event.
    :return: a list of dicts representing the objects
    """
    obj_list = []
    for obj in event['Records']:
        curr_account_num = get_current_account_number(obj)
        s3_events = obj['Sns']['Message']
        json_s3_events = json.loads(s3_events)
        if 'Records' in json_s3_events:
            for s3_event in json_s3_events['Records']:
                obj_list.extend(
                    get_raw_events(S3_CLIENTS[curr_account_num],
                                   s3_event['s3']['object']['key'],
                                   s3_event['s3']['bucket']['name']))

    return obj_list


def get_raw_events(s3client, key, bucket_name):
    """Returns a python object from a compressed file.

    :param s3client: the boto3 client to be used.
    :param key: the key of the file to be downloaded.
    :param bucket_name: bucket name to download from.
    :return: the raw python object underneath.
    """
    raw_file = ''
    fd, path = tempfile.mkstemp()
    os.close(fd)
    with open(path, 'wb') as tmp:
        # s3client.download_fileobj(FILTER_CONFIG_BUCKET, key, tmp)
        tmp.write(s3client.get_object(
            Bucket=bucket_name,
            Key=key)['Body'].read())
        logger.info('get_raw_events() after get_object')

    with gzip.open(path, 'r') as gz_file:
        for line in gz_file:
            raw_file += line
    json_file = json.loads(raw_file)
    if 'Records' in json_file:
        return json.loads(raw_file)['Records']
    return []


def event_matches_config(config, target_object):
    """Checks if the pattern configured in config matches anything at
    target_object.

    :param config: the configuration which holds the relevant regex
    :param target_object: the object to be searched
    :return: a boolean representing whether the regex was a match or not
    """
    match = False
    s_target_object = json.dumps(target_object)

    for source in config['source']:
        match |= source in target_object['eventSource']
        if match:
            break
    if match:
        for include in config['includes']:
            match &= include in s_target_object
        for not_include in config['not_includes']:
            if not_include in s_target_object:
                return False

    return match


def get_notification(matched_obj):
    """Notifies via AWS SNS.

    :param matched_obj: the object that the notification should notify about
    """
    subject = \
        'S3 notification: new bucket created {0}'.format(
            matched_obj['requestParameters']
            ['bucketName'])
    message = \
        'New bucket created in account: {0}.\nBucket name: {1}\n' \
        'ARN of the creator: {2}\n' \
        'Region: {3}'.format(matched_obj['recipientAccountId'],
                             matched_obj['requestParameters']['bucketName'],
                             matched_obj['userIdentity']['arn'],
                             matched_obj['awsRegion'])

    return {subject: message}


def notify(config, subject, message):
    """Notifies via AWS SNS.

    :param config: the configuration which contains the SNS topic ARN
    :param subject: the subject to publish with
    :param message: the message to publish with
    """
    snsclient = boto3.client('sns', region_name=config['sns']['region'])
    snsclient.publish(
        TopicArn=config['sns']['topicARN'],
        Subject=subject,
        Message=message)
    logger.info('Message "{0}" was sent to {1}'.format(
        message, config['sns']['topicARN']))


def add_row(values):
    """Adds a row with the given values.

    :param values: values to add (each value is a column).
    """
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
    sheet.append_row(values)


def save_event(event):
    """Saves the event to a Google Spreadsheet.

    :param event: event to save.
    """
    values = [None] * len(COLUMNS.keys())
    values[COLUMNS['BUCKET_NAME']] = event['requestParameters']['bucketName']
    values[COLUMNS['CREATED_AT']] = datetime.now().strftime(
        '%m/%d/%Y %H:%M:%S')  # Matching the Google Spreadsheet format
    values[COLUMNS['CREATED_BY']] = event['userIdentity']['arn']
    values[COLUMNS['WEIGHT']] = 0  # The bucket is empty when created
    values[COLUMNS['ACCOUNT']] = event['recipientAccountId']
    values[COLUMNS['REGION']] = event['awsRegion']
    add_row(values)


def main(event, context):
    if (time.time() - credentials_last_refresh) >= REFRESH_PERIOD:
        set_credentials(sts_client)
    logger.info('Handling event: {0}'.format(event))
    config = get_config()
    logger.info('Fetched the following config: {0}'.format(config))
    events = get_events(event)
    logger.info('Checking {0} events'.format(len(events)))

    notifications = {}
    for ev in events:
        if event_matches_config(config, ev):
            save_event(ev)
            notifications.update(get_notification(ev))

    for notify_subject in notifications:
        notify(config, notify_subject, notifications[notify_subject])

    return True
