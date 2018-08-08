import os

import boto3
from cloudify_rest_client import CloudifyClient

import html_formats as h_format


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
    deployments = sorted(client.deployments.list(),
                         key=lambda x: x['updated_at'],
                         reverse=True)

    table_cells = ""
    msg = h_format.p.format("Here are the current active deployments:")
    for depl in deployments:
        ID = depl.id
        customer_name = depl.inputs['customer_name'] if \
            'customer_name' in depl.inputs else 'NO NAME'
        created_at = depl['created_at']
        updated_at = depl['updated_at']
        table_cells += h_format.depl_cell.format(
            ID, customer_name, created_at, updated_at)
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


if __name__ == '__main__':
    main(None, None)
