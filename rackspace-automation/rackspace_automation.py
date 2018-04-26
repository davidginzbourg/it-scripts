import os
import datetime
import dateutil.parser

import boto3
from keystoneauth1 import session

from keystoneauth1.identity import v3
from novaclient import client as novaclient
from keystoneclient.v3 import client as keystoneclient

s3_client = boto3.client('s3')
sns_client = boto3.client('sns')

SHELVE_THRESHOLD = 11  # Days
SHELVE_WARN_THRESHOLD = 9  # Days


class Verdict:
    """Enum class for states.
    """
    DELETE, SHELVE, WARN_DELETE, WARN_SHELVE = range(4)


def get_verdict(instance):
    """
    :param instance: instance to check.
    :return: which state to assign instance.
    """
    pass


def is_above_threshold(time, threshold):
    """
    :param time: time to check.
    :param threshold: threshold.
    :return: whether more time has passed since 'time' than the threshold.
    """
    updated_at = dateutil.parser.parse(time).replace(tzinfo=None)
    expiration_threshold = datetime.datetime.utcnow() - \
                           datetime.timedelta(days=threshold)
    return updated_at - expiration_threshold <= datetime.timedelta(0)


def send_warnings(shelve_warnings, delete_warnings):
    """Sends out a warning regarding the given instances.

    :param shelve_warnings: instances that their owners should be warned before
     shelving.
    :param delete_warnings: instances that their owners should be warned before
     deletion.
    """
    print('Shelved warnings: {}'.format(shelve_warnings))
    print('Delete warnings: {}'.format(delete_warnings))


def delete_instances(delete_shelved):
    """Delete the shelved instances.

    :param delete_shelved: instances to delete.
    """
    print('DELETE: {}'.format(delete_shelved))


def shelve(shelve_instances):
    """Shelve the instances.

    :param shelve_instances: instances to shelve.
    """
    print('SHELVE: {}'.format(shelve_instances))


def get_violating_instances(tenant_names, ignore_dict):
    """Retrieve instances that violate violations.

    :param tenant_names: all the tenant names.
    :param ignore_dict: instances to ignore (tenant -> instance_name).
    :return: shelve_instances, delete_shelved_instances, shelve_warnings,
        delete_warnings.
    """

    def add_instance_to_dicts(verdict):
        """Adds the instance to the corresponding dict.
        :param verdict: verdict to follow.
        """
        # is_above_threshold(instance.updated, SHELVE_THRESHOLD)
        pass

    shelve_instances = {}
    delete_shelved_instances = {}
    shelve_warnings = {}
    delete_warnings = {}
    for project in tenant_names:
        credentials = get_credentials(project)
        nova = novaclient.Client(version='2.0', session=credentials)
        instances_list = nova.servers.list()

        for instance in instances_list:
            add_instance_to_dicts(get_verdict(instance))

        return shelve_instances, delete_shelved_instances, shelve_warnings, \
               delete_warnings


def get_tenant_names(credentials):
    """Retrieve tenant names.

    :param credentials: Openstack credentials.
    :return: all tenant names in the main application where the credentials
        reside.
    """
    keystone = keystoneclient.Client(session=credentials)

    projects_name = []
    projects_list = keystone.projects.list(user=credentials.get_user_id())

    for project in projects_list:
        projects_name.append(project.name.encode('ascii'))
    return projects_name


def fetch_ignore_dict(s3_client):
    """Get the ignore dict (JSON file) from S3.

    :param s3_client: S3 client.
    :return: the python dict version of the JSON file.
    """
    return {}


def get_credentials(project):
    """Get the OpenStack credentials from the ENV vars.

    :param project: project to connect to.
    :return: keystoneclient.v3.Password instance.
    """
    url = os.environ['OPENSTACK_URL']
    username = os.environ['OPENSTACK_USERNAME']
    password = os.environ['OPENSTACK_PASSWORD']
    auth = v3.Password(auth_url=url,
                       username=username,
                       password=password,
                       user_domain_name='Default',
                       project_name=project,
                       project_domain_name='Default')
    return session.Session(auth=auth)


def check_environs():
    """Checks if all the environs are setup.
    """
    pass


def main():
    check_environs()
    main_credentials = get_credentials(
        os.environ['OPENSTACK_MAIN_PROJECT'])
    ignore_dict = fetch_ignore_dict(s3_client)
    tenant_names = get_tenant_names(main_credentials)
    shelve_instances, delete_shelved_instances, shelve_warnings, \
    delete_warnings = get_violating_instances(tenant_names, ignore_dict)
    shelve(shelve_instances)
    delete_instances(delete_shelved_instances)
    send_warnings(shelve_warnings, delete_warnings)


if __name__ == '__main__':
    main()
