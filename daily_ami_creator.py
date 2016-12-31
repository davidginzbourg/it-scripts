import boto3


def create_ami(client, instance_id, ami_name):
    """Creates an AMI from the given instance

    :param client: AWS boto3 client
    :param instance_id: EC2 instance ID
    :param ami_name: Desired AMI name
    :param profile_name: AWS credentials local profile name
    """

    return client.create_image(
        InstanceId=instance_id,
        Name=ami_name,
        NoReboot=True)


def deregister_old_amis(client, ami_prefix, expiration):
    """Deregisters old amis that are older than the given expiration days.

    :param client: AWS client
    :param ami_prefix: A prefix of the ami which represents the prefix after
    which in the creation time (in unix time) appears. I.e.
    '<ami_prefix><unix_time>'
    :param expiration: Expiration time in seconds
    """


    ami_list = client.describe_images(
        ImageIds=['*' + ami_prefix + '*']
    )

def get_client(profile_name):
    """Creates an AWS boto3 client

    :param expiration: Number of days allowed to elapse after the last ami
    creation
    """
    session = boto3.Session(profile_name=profile_name)
    return session.client('ec2')


# create_ami('i-d689e86b', 'david_test_1', 'default')

"""

Filter [
    {
        Name: image-id
        Values: ['image-id']
        }
]
"""
