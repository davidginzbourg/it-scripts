#!/bin/python

import time
import subprocess

import boto3


ACCESS_KEY = 'AKI...UA'
SECRET_KEY = 'l3....cn8'
BUCKET_NAME = 'gigavault'
BASE_PATH = 'audit_logs'

cmd = "ls -Art /var/log/vault*.gz| tail -n 1"
list_files = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
LAST_ARCHIVE = list_files.communicate()[0][:-1]

s3 = boto3.resource('s3',
                    aws_access_key_id=ACCESS_KEY,
                    aws_secret_access_key=SECRET_KEY)


def s3_upload(data):
    current_minute = time.strftime("%Y/%d.%m-%I:%M")
    s3.Bucket(BUCKET_NAME).put_object(
        Key='{0}/{1}'.format(BASE_PATH, current_minute), Body=data)


with open(LAST_ARCHIVE, 'r') as data:
    s3_upload(data)
