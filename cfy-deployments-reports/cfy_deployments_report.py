import os

from cloudify_rest_client import CloudifyClient


def main(event, context):
    manager_url = os.environ.get('MANAGER_URL')
    username = os.environ.get('USERNAME')
    password = os.environ.get('PASSWORD')
    to_address = os.environ.get('TO_ADDRESS')
    from_address = os.environ.get('FROM_ADDRESS')

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
        password=password)
    deployments = client.deployments.list()

    for depl in deployments:
        print(depl.id)


if __name__ == '__main__':
    main(None, None)
