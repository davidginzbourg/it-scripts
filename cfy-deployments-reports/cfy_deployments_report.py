import os

import boto3
from cloudify_rest_client import CloudifyClient

import html_formats as h_format


def list(api_func):
    offset = 999
    response = api_func(_size=offset)
    result = response.items
    total = response.metadata.pagination.total
    for cur_offset in range(offset, total, offset):
        response = api_func(_size=offset, _offset=cur_offset)
        result.extend(response.items)
    return result


def main(event, context):
    manager_url = os.environ.get('MANAGER_URL')
    username = os.environ.get('USERNAME')
    password = os.environ.get('PASSWORD')
    to_address = os.environ.get('TO_ADDRESS')
    from_address = os.environ.get('FROM_ADDRESS')
    subject = os.environ.get('SUBJECT')

    if not manager_url:
        raise Exception('MANAGER_URL os env is missing.')
    if not username:
        raise Exception('USERNAME os env is missing.')
    if not password:
        raise Exception('PASSWORD os env is missing.')
    if not to_address:
        raise Exception('TO_ADDRESS os env is missing.')
    if not from_address:
        raise Exception('FROM_ADDRESS os env is missing.')

    client = CloudifyClient(manager_url,
                            username=username,
                            password=password,
                            tenant='default_tenant')

    instances = list(client.node_instances.list)
    deployments = dict(map(
        lambda x: (x.id, x), list(client.deployments.list)))
    table_cells = ""
    msg = h_format.p.format("Here are the current active deployments:")
    cnt = 0
    for instance in instances:
        if instance['state'] == 'started':
            deployent_id = instance.deployment_id
            if 'customer_name' in deployments[deployent_id].inputs:
                customer_name = \
                    deployments[deployent_id].inputs['customer_name']
            else:
                customer_name = 'NO NAME'
            created_at = deployments[deployent_id]['created_at']
            updated_at = deployments[deployent_id]['updated_at']
            table_cells += h_format.depl_cell.format(
                customer_name, deployent_id, created_at, updated_at)
            cnt += 1
    total_sum = h_format.depl_cell.format("TOTAL", cnt, "-", "-")
    table_cells = total_sum + table_cells
    table = h_format.depl_table.format(table_cells)
    msg += table
    h_msg = h_format.html_email.format(msg)
    ses = boto3.client('ses')
    destination = {'ToAddresses': [to_address]}
    ses.send_email(Source=from_address,
                   Destination=destination,
                   Message={
                       'Subject': {
                           'Data': subject},
                       'Body': {
                           'Html': {
                               'Data': h_msg}}
                   })
