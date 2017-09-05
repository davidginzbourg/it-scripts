# Adds SNS publish permissions to the events
import json
import yaml

import boto3

ACCOUNTS = [

]
REGIONS = [
    'us-east-2',
    'us-east-1',
    'us-west-1',
    'us-west-2',
    'ap-south-1',
    'ap-northeast-2',
    'ap-southeast-1',
    'ap-southeast-2',
    'ap-northeast-1',
    'ca-central-1',
    'eu-central-1',
    'eu-west-1',
    'eu-west-2',
    'sa-east-1'
]
sns_policy = {
    "Sid": "AWSEvents_health-sns_Id23456789",
    "Effect": "Allow",
    "Principal": {
        "Service": "events.amazonaws.com"
    },
    "Action": "sns:Publish",
    "Resource": None
}
topic_name = 'cloudwatch_event_parser'
arn_temp = 'arn:aws:sns:{0}:{1}:cloudwatch_event_parser'

with open('./credentials', 'r') as f:
    credentials = yaml.load(f)

for account in ACCOUNTS:
    for region in REGIONS:
        arn = arn_temp.format(region, account)
        client = boto3.client('sns', region_name=region,
                              **credentials[account])
        policy = client.get_topic_attributes(
            TopicArn=arn)['Attributes']['Policy']
        if 'events.amazonaws.com' not in policy:
            policy_dict = json.loads(policy)
            sns_policy['Resource'] = arn
            policy_dict['Statement'].append(sns_policy)
            client.set_topic_attributes(
                TopicArn=arn,
                AttributeName='Policy',
                AttributeValue=json.dumps(policy_dict)
            )
