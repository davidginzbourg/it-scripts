import os
import time
import logging

import boto3

# Counts ami name generation
gen_ami_name_iteration = 0


def deregister_old_amis(client, ami_prefix, expiration, owners):
    """Deregisters old amis that are older than the given expiration days.

    :param client: AWS client
    :param ami_prefix: A prefix of the ami which represents the prefix after
    which in the creation time (in unix time) appears. I.e.
    '<ami_prefix><unix_time>'
    :param expiration: Expiration time in seconds
    :param owners: List of owners IDs to filter
    :return: Old amis imade IDs
    """

    old_amis_ids = []

    ami_list = client.describe_images(Owners=owners)

    for ami in ami_list['Images']:
        if ami_prefix in ami['Name']:
            if is_ami_expired(ami['Name'], ami_prefix, expiration):
                old_amis_ids.append(ami['ImageId'])
                client.deregister_image(ImageId=ami['ImageId'])

    return old_amis_ids


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
    timestamp = \
        float(time.time()) \
        + float('0.{0}'.format(gen_ami_name_iteration))

    global gen_ami_name_iteration
    gen_ami_name_iteration += 1

    return ami_name_prefix + str(timestamp)


def delete_old_snapshots(client, ami_ids, owners):
    """Deletes old snapshots given an ami id

    :param client: AWS client
    :param ami_id: AMI IDs list
    :param owners: Snapshot owners IDs
    """

    snapshots = client.describe_snapshots(OwnerIds=owners)
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
                # Skip to the next snapshot
                break

    return snapshot_ids


def get_owner_ids():
    """Gets the owner IDs from the environmental variables.

    :return: List of owner IDs
    """
    owner_ids = []
    cur_owner = 'temp'

    i = 0
    while cur_owner:
        cur_owner = os.environ.get('OWNER_ID' + str(i))
        owner_ids.append(cur_owner)
        i += 1

    return owner_ids


def get_instance_ids():
    """Gets the instance IDs from the environmental variables.

    :return: List of instance IDs
    """
    instance_ids = []
    cur_instance = 'temp'

    i = 0
    while cur_instance:
        cur_instance = os.environ.get('INSTANCE_ID' + str(i))
        instance_ids.append(cur_instance)
        i += 1

    return instance_ids


def main(event, context):
    """Script to be run daily

    Owner IDs should be set as follows:
        OWNER_ID0 = ...
        OWNER_ID1 = ...
        .
        .
        .

    Instance IDs should be set as follows:
        INSTANCE_ID0 = ...
        INSTANCE_ID1 = ...
        .
        .
        .
    """

    # Expiration time in seconds
    expiration = int(os.environ.get('EXPIRATION'))
    ami_name_prefix = os.environ.get('AMI_PREFIX')
    instance_ids = get_instance_ids()
    owner_ids = get_owner_ids()

    logging.debug(
        'Init values: expiration: {0}, ami_name_prefix: {1}, '
        'instance_ids: {2}'.format(expiration, ami_name_prefix, instance_ids))

    client = boto3.client('ec2')

    for instance_id in instance_ids:
        generated_ami_name = gen_ami_name(ami_name_prefix)

        logging.info('Generated ami name prefix: ' + generated_ami_name)

        # Register AMI
        client.create_image(
            InstanceId=instance_id,
            Name=generated_ami_name,
            NoReboot=True)

    # Delete old AMIs
    old_ami_ids = deregister_old_amis(
        client,
        ami_name_prefix,
        expiration,
        owner_ids)

    logging.info('Deleting old snapshots: {0}'.format(old_ami_ids))

    delete_old_snapshots(client, old_ami_ids, owner_ids)
