import os
import time

import boto3


def deregister_old_amis(client, ami_prefix, expiration):
    """Deregisters old amis that are older than the given expiration days.

    :param client: AWS client
    :param ami_prefix: A prefix of the ami which represents the prefix after
    which in the creation time (in unix time) appears. I.e.
    '<ami_prefix><unix_time>'
    :param expiration: Expiration time in seconds
    :return: Old amis imade IDs
    """

    old_amis_ids = []

    ami_list = client.describe_images(
        ImageIds=[ami_prefix + '*']
    )

    for ami in ami_list['Images']:
        if is_ami_expired(ami_prefix, ami['ImageId'], expiration):
            old_amis_ids.append(ami['ImageId'])
            client.deregister_image(ImageId=old_amis_ids)

    return old_amis_ids


def get_client(aws_access_key_id, aws_secret_access_key):
    """Creates an AWS boto3 client

    :param aws_access_key_id: AWS Key ID
    :param aws_secret_access_key: AWS Secret Access Key
    """
    session = boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key)
    return session.client('ec2')


def is_ami_expired(ami_name, ami_prefix, expiration):
    """Check if the AMI has expired

    :param ami_name: The AMI name
    :param ami_prefix: The AMI prefix
    :param expiration: Expiration time in seconds
    :return: True if expired, False
    """

    creation_time = int(ami_name.strip(ami_prefix))

    current_time = int(time.time())

    time_diff = current_time - creation_time

    if time_diff > expiration:
        return True

    return False


def gen_ami_name(ami_name_prefix):
    """Generates AMI name

    :param ami_name_prefix: The AMI name, used as a prefix
    :return: Generated AMI name
    """
    timestamp = int(time.time())

    return ami_name_prefix + str(timestamp)


def delete_old_snapshots(client, ami_ids):
    """Deletes old snapshots given an ami id

    :param client: AWS client
    :param ami_id: AMI IDs list
    """

    snapshots = client.describe_snapshots()
    snapshot_ids = get_snapshots_ids(ami_ids, snapshots)

    for snapshot_id in snapshot_ids:
        client.delete_snapshot(SnapshotId=snapshot_id)


def get_snapshots_ids(ami_ids, snapshots):
    """Gets the snapshot IDs using the AMI ID in the description

    :param snapshots: List of snapshots
    :param ami_ids: List of AMI IDs to search
    """

    snapshot_ids = []

    for snapshot in snapshots['Snapshots']:
        for ami in ami_ids:
            if ami in snapshot['Description']:
                snapshot_ids.append(snapshot['SnapshotId'])
                # No need to append a second time
                break

    return snapshot_ids


def main(event, context):
    """Script to be run daily
    """

    # Expiration time in seconds
    expiration = os.environ.get('EXPIRATION')
    ami_name_prefix = os.environ.get('AMI_PREFIX')
    instance_id = os.environ.get('INSTANCE_ID')

    aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')

    client = get_client(aws_access_key_id, aws_secret_access_key)

    generated_ami_name = gen_ami_name(ami_name_prefix)

    # Register AMI
    client.create_image(
        InstanceId=instance_id,
        Name=generated_ami_name,
        NoReboot=True)

    # Delete old AMIs
    old_ami_ids = deregister_old_amis(client, ami_name_prefix, expiration)

    delete_old_snapshots(client, old_ami_ids)


if __name__ == '__main__':
    main()
