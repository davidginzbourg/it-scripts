import os
import logging
from datetime import datetime, timedelta
from multiprocessing.dummy import Process, Lock
from multiprocessing.dummy import Pool as ThreadPool

import boto3
import gspread
from oauth2client.service_account import ServiceAccountCredentials

sts_client = boto3.client('sts')
logger = logging.getLogger()
logger.level = logging.INFO

# Role name to assume, use the same name for all the other accounts.
ROLE_SESSION_NAME = os.getenv('ROLE_SESSION_NAME')
if not ROLE_SESSION_NAME:
    raise Exception('Missing ROLE_SESSION_NAME env var')

SCOPES = ['https://spreadsheets.google.com/feeds']
CREDENTIALS_FILE_PATH = os.environ.get('CREDENTIALS_FILE_PATH')
if not CREDENTIALS_FILE_PATH:
    raise Exception('Missing CREDENTIALS_FILE_PATH env var')

SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
if not SPREADSHEET_ID:
    raise Exception('Missing SPREADSHEET_ID env var')

WORKSHEET_NAME = os.environ.get('WORKSHEET_NAME')
if not WORKSHEET_NAME:
    raise Exception('Missing WORKSHEET_NAME env var')

COLUMNS = {
    'BUCKET_NAME': 0,
    'CREATED_BY': 1,
    'CREATED_AT': 2,
    'WEIGHT': 3,
    'ACCOUNT': 4,
    'REGION': 5
}

ACCOUNTS_NUMBER_TO_NAME = {
    '111111': 'account_name'
}
ROLE_ARNS = {
    '11111111': {'RoleArn': os.getenv(
        ACCOUNTS_NUMBER_TO_NAME['111111'] + '_RoleArn')}
}
BUCKET_LIST = {
    '111111': set()
}


def get_bucket_size(bucket_name, client, byte_conv_fun=lambda x: x):
    """Returns the bucket size.

    :param bucket_name: bucket name to get it's size
    :param client: cloudwatch client.
    :param byte_conv_fun: a byte conversion function.
    """
    response = client.get_metric_statistics(
        Namespace="AWS/S3",
        MetricName="BucketSizeBytes",
        Dimensions=[
            {
                "Name": "BucketName",
                "Value": bucket_name
            },
            {
                "Name": "StorageType",
                "Value": "StandardStorage"
            }
        ],
        StartTime=datetime.now() - timedelta(days=2),
        EndTime=datetime.now(),
        Period=86400,
        Statistics=['Average']
    )
    if not response['Datapoints']:
        return -1
    return byte_conv_fun(int(response['Datapoints'][-1]['Average']))


def get_credentials_dict(sts_client):
    """Returns a dict of access and secret keys for each account in ACCOUNTS.

    :param sts_client: STS client to use for client dict init.
    """

    cred_dict = dict()

    def get_assumed_role_credentials((account_num, value)):
        cred = sts_client.assume_role(
            RoleArn=value['RoleArn'],
            RoleSessionName=ROLE_SESSION_NAME)['Credentials']
        cred_dict[account_num] = {
            'aws_access_key_id': cred['AccessKeyId'],
            'aws_secret_access_key': cred['SecretAccessKey'],
            'aws_session_token': cred['SessionToken']
        }

    pool = ThreadPool()
    logger.info('Retrieving AWS credentials...')
    pool.map(get_assumed_role_credentials, ROLE_ARNS.items())

    return cred_dict


def is_exist(bucket_name, client, account_number):
    """Returns whether the bucket exists.

    :param bucket_name: bucket name to check.
    :param client: s3 client to use.
    :param account_number: account number to save it's S3 buckets.
    """
    if not BUCKET_LIST[account_number]:
        for bucket in client.list_buckets()['Buckets']:
            BUCKET_LIST[account_number].add(bucket['Name'])
    return bucket_name in BUCKET_LIST[account_number]


def execute_updates(contents, sheet):
    """Executes the relevant updates, modify first and delete after.

    :param contents: contents containing the changings.
    :param sheet: Google Spreadsheet client.
    """

    def handle_update_value(item):
        if 'value' in item and 'index' in item:
            sheet.update_cell(
                item['index'] + 1,
                COLUMNS['WEIGHT'] + 1,
                item['value'])

    pool = ThreadPool()
    logger.info('Executing value updates...')
    # Main headers are also in contents
    pool.map(handle_update_value, contents[1:])

    logger.info('Executing deletions...')
    for i in range(len(contents) - 1, 0, -1):
        if 'delete' in contents[i]:
            sheet.delete_row(i + 1)


def get_clients(service_name, credentials):
    """Returns a dict of service_name clients, keys are the account number.

    :param service_name: service name to use with boto3
    :param credentials: credentials dict.
    :return:
    """
    clients = {}

    def get_service_client((account_num, cred_dict)):
        clients[account_num] = boto3.client(service_name, **cred_dict)

    pool = ThreadPool()
    logger.info('Creating {0} clients...'.format(service_name))
    pool.map(get_service_client, credentials.items())

    return clients


def validate_data(credentials):
    """Validates and updates the data in the given Google Spreadsheet.

    :param credentials: a dict of credentials, keys should be account numbers.
    """
    google_credentials = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIALS_FILE_PATH, scopes=SCOPES)
    gc = gspread.authorize(google_credentials)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
    contents = sheet.get_all_values()
    s3_clients = get_clients('s3', credentials)
    cloudwatch_clients = get_clients('cloudwatch', credentials)
    bucket_names = set()

    for i in range(len(contents)):
        contents[i] = [i, contents[i]]

    def update_cell_status(item, lock):
        """Updates the cell's status, whether to delete or modify.

        :param item: item in the array of the spreadsheet contents.
        :param lock: lock instance.
        """
        index = item[0]

        def mark_cell_for_deletion():
            contents[index] = {'delete': True}

        def mark_cell_for_modification(value):
            contents[index] = {'value': value, 'index': index}

        def mark_cell_neutral():
            contents[index] = {}

        curr_row = item[1]
        bucket_name = curr_row[COLUMNS['BUCKET_NAME']]
        lock.acquire()
        duplicate = bucket_name in bucket_names
        if not duplicate:
            bucket_names.add(bucket_name)
        lock.release()

        if duplicate or not is_exist(
                bucket_name,
                s3_clients[curr_row[COLUMNS['ACCOUNT']]],
                curr_row[COLUMNS['ACCOUNT']]):
            mark_cell_for_deletion()
        else:
            weight = get_bucket_size(
                bucket_name,
                cloudwatch_clients[curr_row[COLUMNS['ACCOUNT']]],
                lambda x: round(x / 1000000.0, 2))
            if str(weight) != curr_row[COLUMNS['WEIGHT']]:
                mark_cell_for_modification(weight)
            else:
                mark_cell_neutral()

    logger.info('Calculating updates...')
    # Main headers are also in contents
    lock = Lock()
    processes = []
    for i in contents[1:]:
        p = Process(target=update_cell_status, args=(i, lock))
        processes.append(p)
        p.start()
    for p in processes:
        p.join()
    execute_updates(contents, sheet)


def main(event, context):
    credentials = get_credentials_dict(sts_client)
    validate_data(credentials)
