import os
import datetime
import dateutil.parser

import boto3
import gspread
from keystoneauth1 import session
from keystoneauth1.identity import v3
from novaclient import client as novaclient
from keystoneclient.v3 import client as keystoneclient
from oauth2client.service_account import ServiceAccountCredentials

sns_client = boto3.client('sns')

INSTANCE_SETTINGS = 'instance_settings'
GLOBAL_SETTINGS = 'settings'
PROJECT_NAME = 'project_name'
INSTANCE_NAME = 'instance_name'
SHELVE_RUNNING_WARNING_THRESHOLD = 'shelve_running_warning_threshold'
SHELVE_RUNNING_THRESHOLD = 'shelve_running_threshold'
SHELVE_STOPPED_WARNING_THRESHOLD = 'shelve_stopped_warning_threshold'
SHELVE_STOPPED_THRESHOLD = 'shelve_stopped_threshold'
DELETE_WARNING_THRESHOLD = 'delete_warning_threshold'
DELETE_SHELVED_THRESHOLD = 'delete_shelved_threshold'

SCOPES = ['https://spreadsheets.google.com/feeds']
CREDENTIALS_FILE_PATH = os.environ.get('CREDENTIALS_FILE_PATH')
if not CREDENTIALS_FILE_PATH:
    raise Exception('Missing CREDENTIALS_FILE_PATH env var')

SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
if not SPREADSHEET_ID:
    raise Exception('Missing SPREADSHEET_ID env var')

SETTINGS_WORKSHEET = os.environ.get('SETTINGS_WORKSHEET')
if not SETTINGS_WORKSHEET:
    raise Exception('Missing SETTINGS_WORKSHEET env var')

INSTANCE_SETTINGS_WORKSHEET = os.environ.get('INSTANCE_SETTINGS_WORKSHEET')
if INSTANCE_SETTINGS_WORKSHEET:
    raise Exception('Missing INSTANCE_SETTINGS_WORKSHEET env var')

OPENSTACK_MAIN_PROJECT = os.environ['OPENSTACK_MAIN_PROJECT']
if not OPENSTACK_MAIN_PROJECT:
    raise Exception('Missing OPENSTACK_MAIN_PROJECT env var')


class Verdict:
    """Enum class for states.
    """
    DELETE, SHELVE, DELETE_WARN, SHELVE_WARN, DO_NOTHING = range(5)


class TimeThresholdSettings:
    """Represents some configuration of the settings.
    """

    def __init__(self, shelve_running_warning_threshold,
                 shelve_stopped_warning_threshold, delete_warning_threshold,
                 shelve_running_threshold, shelve_stopped_threshold,
                 delete_shelved_threshold):
        """Initializes a new configuration.

        :param shelve_running_warning_threshold: a warning threshold for
            shelving a running instance (seconds).
        :param shelve_stopped_warning_threshold: a warning threshold for
            shelving a stopped instance (seconds).
        :param delete_warning_threshold: a warning threshold for deletion
            (seconds).
        :param shelve_running_threshold: running time threshold (seconds).
        :param shelve_stopped_threshold: stopped time threshold (seconds).
        :param delete_shelved_threshold: shelved time threshold (seconds).
        """
        self.shelve_running_warning_threshold = \
            shelve_running_warning_threshold
        self.shelve_stopped_warning_threshold = \
            shelve_stopped_warning_threshold
        self.delete_warning_threshold = delete_warning_threshold
        self.shelve_running_threshold = shelve_running_threshold
        self.shelve_stopped_threshold = shelve_stopped_threshold
        self.delete_shelved_threshold = delete_shelved_threshold

    def should_shelve_warn(self, inst_dec):
        """Checks if it should it warn for shelving. This applies to
        running/stopped instances.
        :param inst_dec: instance decorator.
        :type: InstanceDecorator.
        :return: whether it should.
        """
        return \
            self.is_above_threshold(inst_dec.running_since,
                                    self.shelve_running_warning_threshold) or \
            self.is_above_threshold(inst_dec.stopped_since,
                                    self.shelve_stopped_warning_threshold)

    def should_delete_warn(self, inst_dec):
        """Checks if it should it warn before deleting. This applies to shelved
         instances.
        :param inst_dec: instance decorator.
        :type: InstanceDecorator.
        :return: whether it should.
        """
        return self.is_above_threshold(inst_dec.shelved_since,
                                       self.delete_warning_threshold)

    def should_shelve(self, inst_dec):
        """Checks if it should it shelve the instance. Applies to
        running/stopped instances.
        :param inst_dec: instance decorator.
        :type: InstanceDecorator.
        :return: whether it should.
        """
        return \
            self.is_above_threshold(inst_dec.running_since,
                                    self.shelve_running_threshold) or \
            self.is_above_threshold(inst_dec.stopped_since,
                                    self.shelve_stopped_threshold)

    def should_delete(self, inst_dec):
        """Checks if it should delete the instance. Applies to shelved
        instances.
        :param inst_dec: instance decorator.
        :type: InstanceDecorator.
        :return: whether it should.
        """
        return self.is_above_threshold(inst_dec.shelved_since,
                                       self.delete_shelved_threshold)

    @staticmethod
    def is_above_threshold(time, threshold):
        """Calculates the time difference between now and the given time and
        checks it against the threshold.
        :param time: time to check.
        :param threshold: threshold.
        :return: whether more time has passed since 'time' than the threshold.
        """
        updated_at = dateutil.parser.parse(time).replace(tzinfo=None)
        expiration_threshold = datetime.datetime.utcnow() - \
                               datetime.timedelta(days=threshold)
        return updated_at - expiration_threshold <= datetime.timedelta(0)


class InstanceDecorator:
    """A decorator for the novaclient instances.
    """

    def __init__(self, instance):
        """Initializer.

        :param instance: novaclient server instance.
        """
        self.instance = instance

    @property
    def name(self):
        return self.instance.human_id

    @property
    def running_since(self):
        pass

    @property
    def stopped_since(self):
        pass

    @property
    def shelved_since(self):
        pass


def get_verdict(project_name, inst_dec, configuration):
    """
    :param project_name: project the instance belongs to.
    :param inst_dec: instance decorator.
    :type: InstanceDecorator.
    :param configuration: program configuration.
    :return: which state to assign instance.
    """
    threshold_settings = configuration[GLOBAL_SETTINGS]  # Default

    if project_name in configuration[INSTANCE_SETTINGS]:
        if inst_dec.name in configuration[INSTANCE_SETTINGS][project_name]:
            threshold_settings = \
                configuration[INSTANCE_SETTINGS][project_name][inst_dec.name]

    if threshold_settings.should_shelve_warn(inst_dec):
        return Verdict.SHELVE_WARN
    if threshold_settings.should_delete_warn(inst_dec):
        return Verdict.DELETE_WARN
    if threshold_settings.should_shelve(inst_dec):
        return Verdict.SHELVE
    if threshold_settings.should_delete(inst_dec):
        return Verdict.DELETE
    return Verdict.DO_NOTHING


def send_warnings(shelve_warnings, delete_warnings, **kwargs):
    """Sends out a warning regarding the given instances.

    :param shelve_warnings: instances that their owners should be warned before
     shelving.
    :param delete_warnings: instances that their owners should be warned before
     deletion.
    """
    print('Shelved warnings: {}'.format(shelve_warnings))
    print('Delete warnings: {}'.format(delete_warnings))


def delete_instances(instances_to_delete, **kwargs):
    """Delete the shelved instances.

    :param instances_to_delete: instances to delete.
    """
    print('DELETE: {}'.format(instances_to_delete))


def shelve(instances_to_shelve, **kwargs):
    """Shelve the instances.

    :param instances_to_shelve: instances to shelve.
    """
    print('SHELVE: {}'.format(instances_to_shelve))


def get_violating_instances(project_names, configuration):
    """Retrieve instances that violate violations.

    :param project_names: all the tenant names.
    :param configuration: program configuration.
    :return: instances_to_shelve, instances_to_delete, shelve_warnings,
        delete_warnings.
    """

    def add_to_dict(project, inst_dec, dest_dict):
        """Appends the instance decorator to the project list.

        :param project: project to append to it's list.
        :param inst_dec: instance decorator.
        :param dest_dict: dictionary to add to.
        :type: InstanceDecorator.
        """
        if project not in dest_dict:
            dest_dict[project] = list([inst_dec])
        else:
            dest_dict[project].append(inst_dec)

    def add_instance_to_dicts(project, inst_dec, verdict):
        """Adds the instance to the corresponding dict.
        :param project: project name.
        :param inst_dec: instance decorator.
        :type inst_dec: InstanceDecorator.
        :param verdict: verdict to follow.
        """
        if verdict == Verdict.DELETE:
            add_to_dict(project, inst_dec, instances_to_delete)
        if verdict == Verdict.SHELVE:
            add_to_dict(project, inst_dec, instances_to_shelve)
        if verdict == Verdict.DELETE_WARN:
            add_to_dict(project, inst_dec, delete_warnings)
        if verdict == Verdict.SHELVE_WARN:
            add_to_dict(project, inst_dec, shelve_warnings)

    instances_to_shelve = {}
    instances_to_delete = {}
    shelve_warnings = {}
    delete_warnings = {}
    for project in project_names:
        credentials = get_credentials(project)
        nova = novaclient.Client(version='2.0', session=credentials)
        instances_list = nova.servers.list()

        for instance in instances_list:
            inst_dec = InstanceDecorator(instance)
            verdict = get_verdict(project, inst_dec,
                                  configuration)
            if verdict != Verdict.DO_NOTHING:
                add_instance_to_dicts(project, inst_dec, verdict)

        return {'instances_to_shelve': instances_to_shelve,
                'instances_to_delete': instances_to_delete,
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


def fetch_configuration(spreadsheet_creds):
    """Fetch the program settings from a Google Spreadsheet.

    {
    'instance_settings':
        {
            'project_i':
                {
                    'instance_j': TimeThresholdSettings
                }
        }
    'settings': TimeThresholdSettings
    }

    :param spreadsheet_creds: Google Spreadsheet credentials.
    :return: the program settings.
    """
    return {INSTANCE_SETTINGS: fetch_instance_settings(spreadsheet_creds),
            GLOBAL_SETTINGS: fetch_global_settings(spreadsheet_creds)}


def fetch_instance_settings(spreadsheet_creds):
    """Returns the instance settings.

    :param spreadsheet_creds:
    :return: the instance settings as a dict:
    {
        'project_i':
            {
                'instance_j': TimeThresholdSettings
            }
    }
    """

    def append_to_key_dict_dict(project_name, instance_name,
                                time_threshold_settings):
        if project_name not in instance_settings:
            instance_settings[project_name] = {instance_name:
                                                   time_threshold_settings}
        else:
            instance_settings[project_name][instance_name] = \
                time_threshold_settings

    def parse_value(value):
        if not value:
            return float('inf')
        return float(value)

    def get_time_threshold_settings_params(project_i):
        shelve_running_warning_threshold = \
            parse_value(contents[SHELVE_RUNNING_WARNING_THRESHOLD][project_i])
        shelve_stopped_warning_threshold = \
            parse_value(contents[SHELVE_STOPPED_WARNING_THRESHOLD][project_i])
        delete_warning_threshold = \
            parse_value(contents[DELETE_WARNING_THRESHOLD][project_i])
        shelve_running_threshold = \
            parse_value(contents[SHELVE_RUNNING_THRESHOLD][project_i])
        shelve_stopped_threshold = \
            parse_value(contents[SHELVE_STOPPED_THRESHOLD][project_i])
        delete_shelved_threshold = \
            parse_value(contents[DELETE_SHELVED_THRESHOLD][project_i])
        return {
            'shelve_running_warning_threshold':
                shelve_running_warning_threshold,
            'shelve_stopped_warning_threshold':
                shelve_stopped_warning_threshold,
            'delete_warning_threshold': delete_warning_threshold,
            'shelve_running_threshold': shelve_running_threshold,
            'shelve_stopped_threshold': shelve_stopped_threshold,
            'delete_shelved_threshold': delete_shelved_threshold}

    instance_settings = {}
    gc = gspread.authorize(spreadsheet_creds)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet(
        INSTANCE_SETTINGS_WORKSHEET)
    contents = sheet.get_all_records()
    for project_i in range(contents[PROJECT_NAME]):
        project_name = contents[PROJECT_NAME][project_i]
        if project_name:
            append_to_key_dict_dict(project_name,
                                    contents[INSTANCE_NAME][project_i],
                                    TimeThresholdSettings(
                                        **get_time_threshold_settings_params(
                                            project_i))
                                    )
    return instance_settings


def fetch_global_settings(spreadsheet_creds):
    """Returns the global settings from the Spreadsheet.

    :param spreadsheet_creds:
    :return: global settings of the program.
    :rtype: TimeThresholdSettings
    """
    gc = gspread.authorize(spreadsheet_creds)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet(SETTINGS_WORKSHEET)
    contents = sheet.get_all_records()
    for key in contents.keys():
        # It returns a list of values but in this case there's only one value.
        # This just simplifies the TimeThresholdSettings instantiation.
        contents[key] = contents[key][0]
    return TimeThresholdSettings(**contents)


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


def get_spreadsheet_creds():
    """
    :return: Google Spreadsheet credentials.
    """
    return ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIALS_FILE_PATH, scopes=SCOPES)


def main():
    main_proj_creds = get_credentials(OPENSTACK_MAIN_PROJECT)
    spreadsheet_credentials = get_spreadsheet_creds()
    configuration = fetch_configuration(spreadsheet_credentials)
    project_names = get_tenant_names(main_proj_creds)
    violating_instances = get_violating_instances(project_names, configuration)
    shelve(**violating_instances)
    delete_instances(**violating_instances)
    send_warnings(**violating_instances)


if __name__ == '__main__':
    main()
