import os
import json
import gzip
import logging
import tempfile
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

FILTER_CONFIG_BUCKET = os.environ.get('FILTER_CONFIG_BUCKET')
FILTER_CONFIG_FILE = os.environ.get('FILTER_CONFIG_FILE')


def get_config(s3client):
    """Fetches the configuration file stored in S3.

    :param s3client: the boto3 client to be used
    :return: returns the dict representing the configuration file stored in S3,
    False if failed to retrieve it.
    """
    raw_file = ''
    path = tempfile.mkstemp()[1]
    with open(path, 'wb') as tmp:
        s3client.download_fileobj(
            FILTER_CONFIG_BUCKET, FILTER_CONFIG_FILE, tmp)
    with open(path, 'r') as f:
        for line in f:
            raw_file += line
    return json.loads(raw_file)


def get_events(s3client, event):
    """Gets the objects that were put - the ones that caused this script to be
    invoked.

    :param s3client: the boto3 client to be used
    :param event: the given AWS event
    :return: a list of dicts representing the objects
    """
    obj_list = []
    for obj in event['Records']:
        obj_list.extend(get_raw_events(s3client, obj['s3']['object']['key']))

    return obj_list


def get_raw_events(s3client, key):
    """Returns a python object from a compressed file.

    :param s3client: the boto3 client to be used
    :param key: the key of the file to be downloaded
    :return: the raw python object underneath
    """
    raw_file = ''
    path = tempfile.mkstemp()[1]
    with open(path, 'wb') as tmp:
        s3client.download_fileobj(FILTER_CONFIG_BUCKET, key, tmp)

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
    if match:
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
        'The user that created it was: {2}'.format(
            matched_obj['recipientAccountId'],
            matched_obj['requestParameters']
            ['bucketName'],
            matched_obj['userIdentity']
            ['userName'])

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


def main(event, context):
    logger.info('Handling event: {0}'.format(event))
    s3client = boto3.client('s3')
    config = get_config(s3client)
    logger.info('Fetched the following config: {0}'.format(config))
    events = get_events(s3client, event)
    logger.info('Checking {0} events'.format(len(events)))

    notifications = {}
    for obj in events:
        if event_matches_config(config, obj):
            notifications.update(get_notification(obj))

    for notif_subject in notifications:
        notify(config, notif_subject, notifications[notif_subject])

    return True
