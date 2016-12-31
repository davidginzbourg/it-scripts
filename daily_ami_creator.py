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

    old_amis_id = []

    ami_list = client.describe_images(
        ImageIds=[ami_prefix + '*']
    )

    for ami in ami_list['Images']:
        if is_ami_expired(ami['ImageId'], expiration):
            old_amis_id.append(ami['ImageId'])
            client.deregisger_image(ImageId=old_amis_id)

    return old_amis_id


def get_client(profile_name):
    """Creates an AWS boto3 client

    :param expiration: Number of days allowed to elapse after the last ami
    creation
    """
    session = boto3.Session(profile_name=profile_name)
    return session.client('ec2')


def is_ami_expired(ami_name, expiration):
    """Check if the AMI has expired

    :param ami_name: The AMI name
    :param expiration: Expiration time in seconds
    :return: True if expired, False
    """

    pass


def daily_run():
    """Script to be run daily
    """

# client.create_image(
#     InstanceId=instance_id,
#     Name=ami_name,
#     NoReboot=True)
# create_ami('i-d689e86b', 'david_test_1', 'default')
