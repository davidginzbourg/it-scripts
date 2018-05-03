import os
import datetime
import dateutil.parser

import boto3
from keystoneauth1 import session

from keystoneauth1.identity import v3
from novaclient import client as novaclient
from keystoneclient.v3 import client as keystoneclient

sns_client = boto3.client('sns')

SHELVE_THRESHOLD = 11  # Days
SHELVE_WARN_THRESHOLD = 9  # Days


class Verdict:
    """Enum class for states.
    """
    DELETE, SHELVE, WARN_DELETE, WARN_SHELVE = range(4)


def get_verdict(project_name, instance, configuration):
    """
    :param project_name: project the instance belongs to.
    :param instance: instance to check.
    :param configuration: program configuration.
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


def send_warnings(shelve_warnings, delete_warnings, **kwargs):
    """Sends out a warning regarding the given instances.

    :param shelve_warnings: instances that their owners should be warned before
     shelving.
    :param delete_warnings: instances that their owners should be warned before
     deletion.
    """
    print('Shelved warnings: {}'.format(shelve_warnings))
    print('Delete warnings: {}'.format(delete_warnings))


def delete_instances(delete_shelved, **kwargs):
    """Delete the shelved instances.

    :param delete_shelved: instances to delete.
    """
    print('DELETE: {}'.format(delete_shelved))


def shelve(shelve_instances, **kwargs):
    """Shelve the instances.

    :param shelve_instances: instances to shelve.
    """
    print('SHELVE: {}'.format(shelve_instances))


def get_violating_instances(project_names, configuration):
    """Retrieve instances that violate violations.

    :param project_names: all the tenant names.
    :param configuration: program configuration.
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
    for project in project_names:
        credentials = get_credentials(project)
        nova = novaclient.Client(version='2.0', session=credentials)
        instances_list = nova.servers.list()

        for instance in instances_list:
            add_instance_to_dicts(
                get_verdict(project, instance, configuration))

        return {'shelve_instances': shelve_instances,
                'delete_shelved_instances': delete_shelved_instances,
                'shelve_warnings': shelve_warnings,
                'delete_warnings': delete_warnings}


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


def fetch_ignore_dict(spreadsheet_creds):
    """Fetch the program settings from a Google Spreadsheet.

    :param spreadsheet_creds: Google Spreadsheet credentials.
    :return: the program settings.
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


def get_spreadsheet_creds():
    """
    :return: Google Spreadsheet credentials.
    """
    pass


def main():
    check_environs()
    main_proj_creds = get_credentials(
        os.environ['OPENSTACK_MAIN_PROJECT'])
    spreadsheet_credentials = get_spreadsheet_creds()
    configuration = fetch_ignore_dict(spreadsheet_credentials)
    project_names = get_tenant_names(main_proj_creds)
    violating_instances = get_violating_instances(project_names, configuration)
    shelve(**violating_instances)
    delete_instances(**violating_instances)
    send_warnings(**violating_instances)


if __name__ == '__main__':
    main()
