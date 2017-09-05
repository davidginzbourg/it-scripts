import yaml

import boto3

REGIONS = []
# All the account IDs
ACCOUNTS = []
MAIN_ACCOUNT = 'ID'
ALARM_EMAIL = 'email@domain'
PARSER_EMAIL = 'email@domain'
LAMBDA_ROLE_ARN = 'arn:aws:iam::' + MAIN_ACCOUNT \
                  + ':role/cloudwatch_health_event_parser'
RESOURCES_OUTPUT_LOCATION = './resources'


def import_credentials(location):
    """Imports credentials from the given location.
    """
    with open(location, 'r') as f:
        return yaml.load(f)


def deploy_alarm(credentials, lambda_name, region):
    """Deploys an error alarm.

    :param credentials: used as kwargs for the boto3 client.
    :param lambda_name: name of the function to monitor.
    :param region: region to deploy in.
    """
    alarm_name = 'cloudwatch_event_parser_errors'
    sns_client = boto3.client('sns', region_name=region, **credentials)
    topic_arn = sns_client.create_topic(Name='cloudwatch_alarms')['TopicArn']
    add_resource_to_resources_file('sns topic: ' + topic_arn)
    sns_client.subscribe(
        TopicArn=topic_arn,
        Protocol='email',
        Endpoint=ALARM_EMAIL)
    cloudwatch_client = boto3.client('cloudwatch', region_name=region,
                                     **credentials)
    cloudwatch_client.put_metric_alarm(
        AlarmName=alarm_name,
        ActionsEnabled=True,
        AlarmActions=[topic_arn],
        MetricName='Errors',
        Namespace='AWS/Lambda',
        Dimensions=[{'Name': 'FunctionName', 'Value': lambda_name}],
        Statistic='Sum',
        Period=86400,
        EvaluationPeriods=1,
        Threshold=1,
        ComparisonOperator='GreaterThanOrEqualToThreshold',
        TreatMissingData='notBreaching')
    add_resource_to_resources_file(
        'alarm: ' + alarm_name + ', region: ' + region)


def handle_lambda(credentials):
    """Handles the lambda deployments.

    :param credentials: used as kwargs for the boto3 client.
    :returns a dict with the lambdas' info with their corresponding regions
    """
    lambdas = {}
    lambda_name = 'cloudwatch_event_parser'
    lambda_env = {'Variables': {'SOURCE': PARSER_EMAIL,
                                'TO_ADDRESS': PARSER_EMAIL}}
    with open('../cloudwatch-event-parser/cloudwatch_event_parser.zip',
              'r') as f:
        lambda_zip = f.read()
    for region in REGIONS:
        client = boto3.client('lambda', region_name=region, **credentials)
        result = client.create_function(
            FunctionName=lambda_name,
            Runtime='python2.7',
            Role=LAMBDA_ROLE_ARN,
            Handler=lambda_name + '.main',
            Code={'ZipFile': lambda_zip},
            Description='Parses SNS notifications of health events in JSON '
                        'format',
            Timeout=20,
            Environment=lambda_env)
        lambdas[region] = {'Arn': result['FunctionArn'], 'Name': lambda_name}
        add_resource_to_resources_file('lambda: ' + result['FunctionArn'])
        deploy_alarm(credentials, lambda_name, region)

    return lambdas


def handle_sns_deployment(credentials, region):
    """Deploys SNS topics.

    :param credentials: used as kwargs for the boto3 client.
    :param region: region to deploy in.
    :return: SNS ARN of the created SNS topic
    """
    client = boto3.client('sns', region_name=region, **credentials)
    topic_arn = client.create_topic(Name='cloudwatch_event_parser')['TopicArn']
    add_resource_to_resources_file('sns topic: ' + topic_arn)
    client.add_permission(
        TopicArn=topic_arn,
        Label='lambda-access',
        AWSAccountId=[MAIN_ACCOUNT],
        ActionName=['Subscribe', 'ListSubscriptionsByTopic', 'Receive'])
    return topic_arn


def deploy_event_rule(credentials, region, target_sns_arn):
    """Deploys a health event rule.

    :param credentials: used as kwargs for the boto3 client.
    :param region: region to deploy in.
    :param target_sns_arn: SNS ARN to add as a target for the rule.
    """
    rule_name = 'cloudwatch_health_event_parser'
    pattern = '{"source": ["aws.health"]}'
    client = boto3.client('events', region_name=region, **credentials)
    rule_arn = client.put_rule(
        Name=rule_name,
        EventPattern=pattern,
        State='ENABLED',
        Description='A rule that makes sure all the health events are sent to'
                    ' a SNS')['RuleArn']
    add_resource_to_resources_file('rule: ' + rule_arn)
    client.put_targets(
        Rule=rule_name,
        Targets=[{
            'Id': 'cloudwatch_health_event_parser_' + region,
            'Arn': target_sns_arn}])


def handle_asset_deployments(credentials):
    """Handles all the other assets' deployment.

    :param credentials: used as kwargs for the boto3 client.
    :return: a dict of all the created sns arns with the regions as keys.
    """
    sns_arns = {}
    for region in REGIONS:
        sns_arns[region] = handle_sns_deployment(
            credentials,
            region)
        deploy_event_rule(credentials, region, sns_arns[region])
    return sns_arns


def establish_lambda_sns_relationship(credentials, lambdas, sns_arns):
    """Adds invoke permissions for each SNS to each lambdas with respect to a
    region.

    :param credentials: used as kwargs for the boto3 client.
    :param lambdas: a dict of lambda functions with regions as keys.
    :param sns_arns: a dict of all the sns arns with the regions as keys.
    """
    for region in REGIONS:
        lambda_client = boto3.client('lambda', region_name=region,
                                     **credentials)
        lambda_client.add_permission(
            FunctionName=lambdas[region]['Name'],
            StatementId=lambdas[region]['Name'] + '_' + region + '_' + str(
                time.time()).replace('.', '-'),
            Action='lambda:InvokeFunction',
            Principal='sns.amazonaws.com',
            SourceArn=sns_arns[region])

        sns_client = boto3.client('sns', region_name=region, **credentials)
        sns_client.subscribe(
            TopicArn=sns_arns[region],
            Protocol='lambda',
            Endpoint=lambdas[region]['Arn'])


def add_resource_to_resources_file(resource):
    """Writes down to a file  the added resource.

    :param resource: resource arn.
    """
    with open(RESOURCES_OUTPUT_LOCATION, 'a') as f:
        f.write(resource + '\n')


def reset_resources():
    """Resets the resources file.
    """
    try:
        os.remove(RESOURCES_OUTPUT_LOCATION)
    except OSError:
        pass


def main():
    reset_resources()
    all_creds = import_credentials('')
    lambdas = handle_lambda(all_creds[MAIN_ACCOUNT])
    for account in ACCOUNTS:
        sns_arns = handle_asset_deployments(all_creds[account])
        establish_lambda_sns_relationship(all_creds[MAIN_ACCOUNT], lambdas,
                                          sns_arns)


if __name__ == '__main__':
    main()
