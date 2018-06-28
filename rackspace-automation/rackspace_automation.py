import os
import logging
import datetime
import dateutil.parser

import boto3
import gspread
from keystoneauth1 import session
from keystoneauth1.identity import v3
from novaclient import client as novaclient
from keystoneclient.v3 import client as keystoneclient
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ses_client = boto3.client('ses', region_name='eu-west-1')

###############
DRY_RUN = True
###############

INSTANCE_SETTINGS = 'instance_settings'
GLOBAL_SETTINGS = 'settings'
EMAIL_ADDRESSES = 'email_addresses'
PROJECT_NAME = 'project_name'
INSTANCE_ID = 'instance_id'
SHELVE_RUNNING_WARNING_THRESHOLD = 'shelve_running_warning_threshold'
SHELVE_RUNNING_THRESHOLD = 'shelve_running_threshold'
SHELVE_STOPPED_WARNING_THRESHOLD = 'shelve_stopped_warning_threshold'
SHELVE_STOPPED_THRESHOLD = 'shelve_stopped_threshold'
DELETE_WARNING_THRESHOLD = 'delete_warning_threshold'
DELETE_SHELVED_THRESHOLD = 'delete_shelved_threshold'
TENANT_NAME = 'tenant_name'
EMAIL_ADDRESS = 'email_address'

SCOPES = ['https://spreadsheets.google.com/feeds']
SOURCE_EMAIL_ADDRESS = os.environ.get('SOURCE_EMAIL_ADDRESS')
CREDENTIALS_FILE_PATH = os.environ.get('CREDENTIALS_FILE_PATH')
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
SETTINGS_WORKSHEET = os.environ.get('SETTINGS_WORKSHEET')
EMAIL_ADDRESSES_WORKSHEET = os.environ.get('EMAIL_ADDRESSES_WORKSHEET')
INSTANCE_SETTINGS_WORKSHEET = os.environ.get('INSTANCE_SETTINGS_WORKSHEET')
OPENSTACK_MAIN_PROJECT = os.environ.get('OPENSTACK_MAIN_PROJECT')
OPENSTACK_URL = os.environ.get('OPENSTACK_URL')
OPENSTACK_USERNAME = os.environ.get('OPENSTACK_USERNAME')
OPENSTACK_PASSWORD = os.environ.get('OPENSTACK_PASSWORD')
DEFAULT_NOTIFICATION_EMAIL_ADDRESS = \
    os.environ.get('DEFAULT_NOTIFICATION_EMAIL_ADDRESS')

SHELVE_WARNING_SUBJ = 'Rackspace SHELVE warning (test phase)'
SHELVE_WARNING_MSG = 'The following instances in the {0} tenant will be ' \
                     'shelved soon: {1}'
DELETE_WARNING_SUBJ = 'Rackspace DELETE warning (test phase)'
DELETE_WARNING_MSG = 'The following instances in the {0} tenant will be ' \
                     'deleted soon: {1}'
DELETE_NOTIF_SUBJ = 'Rackspace DELETE notification (test phase)'
DELETE_NOTIF_MSG = 'The following instances in the {0} tenant has been ' \
                   'deleted: {1}'
SHELVE_NOTIF_SUBJ = 'Rackspace SHELVE notification (test phase)'
SHELVE_NOTIF_MSG = 'The following instances in the {0} tenant has been ' \
                   'shelved: {1}'


class RackspaceAutomationException(Exception):
    """Rackspace automation exception.
    """
    pass


class StateTransition:
    """Enum class for state transitions.
    """
    TO_RUNNING, TO_SHELVED, TO_STOPPED, NO_CHANGE = range(4)


class Verdict:
    """Enum class for states.
    """
    DELETE, SHELVE, DELETE_WARN, SHELVE_WARN, DO_NOTHING = range(5)


def get_utc_now():
    """
    :return: the time now, UTC.
    """
    return datetime.datetime.utcnow()


class TimeThresholdSettings:
    """Represents some configuration of the settings.
    """

    def __init__(self, shelve_running_warning_threshold,
                 shelve_running_threshold, shelve_stopped_warning_threshold,
                 shelve_stopped_threshold, delete_warning_threshold,
                 delete_shelved_threshold):
        """Initializes a new configuration.

        :param shelve_running_warning_threshold: a warning threshold for
            shelving a running instance (seconds).
        :param shelve_running_threshold: running time threshold (seconds).
        :param shelve_stopped_warning_threshold: a warning threshold for
            shelving a stopped instance (seconds).
        :param shelve_stopped_threshold: stopped time threshold (seconds).
        :param delete_warning_threshold: a warning threshold for deletion
            (seconds).
        :param delete_shelved_threshold: shelved time threshold (seconds).
        """
        if shelve_running_warning_threshold > shelve_running_threshold \
                or shelve_stopped_warning_threshold > shelve_stopped_threshold \
                or delete_warning_threshold > delete_shelved_threshold:
            raise RackspaceAutomationException("One or more warning "
                                               "thresholds is greater than "
                                               "the it's action threshold.")
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
            self.is_above_threshold(inst_dec.running_since(),
                                    self.shelve_running_warning_threshold) or \
            self.is_above_threshold(inst_dec.stopped_since(),
                                    self.shelve_stopped_warning_threshold)

    def should_delete_warn(self, inst_dec):
        """Checks if it should it warn before deleting. This applies to shelved
         instances.
        :param inst_dec: instance decorator.
        :type: InstanceDecorator.
        :return: whether it should.
        """
        return self.is_above_threshold(inst_dec.shelved_since(),
                                       self.delete_warning_threshold)

    def should_shelve(self, inst_dec):
        """Checks if it should it shelve the instance. Applies to
        running/stopped instances.
        :param inst_dec: instance decorator.
        :type: InstanceDecorator.
        :return: whether it should.
        """
        return \
            self.is_above_threshold(inst_dec.running_since(),
                                    self.shelve_running_threshold) or \
            self.is_above_threshold(inst_dec.stopped_since(),
                                    self.shelve_stopped_threshold)

    def should_delete(self, inst_dec):
        """Checks if it should delete the instance. Applies to shelved
        instances.
        :param inst_dec: instance decorator.
        :type: InstanceDecorator.
        :return: whether it should.
        """
        return self.is_above_threshold(inst_dec.shelved_since(),
                                       self.delete_shelved_threshold)

    @staticmethod
    def is_above_threshold(time, threshold):
        """Calculates the time difference between now and the given time and
        checks it against the threshold.
        :param time: time to check.
        :param threshold: threshold in seconds.
        :return: whether more time has passed since 'time' than the threshold.
        """
        if not time or not threshold or threshold == float('inf'):
            return False
        updated_at = dateutil.parser.parse(time).replace(tzinfo=None)
        expiration_threshold = get_utc_now() - datetime.timedelta(
            seconds=threshold)
        return updated_at - expiration_threshold <= datetime.timedelta(0)

    def __eq__(self, other):
        return self.shelve_running_warning_threshold == \
               other.shelve_running_warning_threshold \
               and self.shelve_stopped_warning_threshold == \
                   other.shelve_stopped_warning_threshold \
               and self.delete_warning_threshold == \
                   other.delete_warning_threshold \
               and self.shelve_running_threshold == \
                   other.shelve_running_threshold \
               and self.shelve_stopped_threshold == \
                   other.shelve_stopped_threshold \
               and self.delete_shelved_threshold == \
                   other.delete_shelved_threshold


class InstanceDecorator:
    """A decorator for the novaclient instances.
    """

    active_vm_states = {'active', 'building', 'paused', 'resized'}
    stopped_vm_states = {'stopped', 'suspended'}
    shelved_vm_states = {'shelved_offloaded'}
    _delete_succ_code = 204
    _shelve_succ_code = 202

    def __init__(self, instance, nova):
        """Initializer.

        :param instance: novaclient server instance.
        :param nova: a novaclient instance for API requests.
        """
        self.instance = instance
        self.nova = nova
        actions = self.nova.instance_action.list(self.instance)
        self.actions_log = sorted(actions,
                                  key=lambda x: x.start_time,
                                  reverse=True)

    @property
    def id(self):
        return self.instance.id

    @property
    def name(self):
        return self.instance.name

    @property
    def status(self):
        return getattr(self.instance, 'OS-EXT-STS:vm_state')

    def running_since(self):
        if not self.actions_log or self.status not in self.active_vm_states:
            return None
        for action in self.actions_log:
            trans = get_transition(action.action)
            # First one to cause it to transition to a running state.
            if trans == StateTransition.TO_RUNNING:
                return action.start_time
        # Assume that the action log is corrupt and therefore no action should
        # be taken
        return str(datetime.datetime.max)

    def stopped_since(self):
        if not self.actions_log or self.status not in self.stopped_vm_states:
            return None
        for action in self.actions_log:
            trans = get_transition(action.action)
            # First one to cause it to transition to a stopped state.
            if trans == StateTransition.TO_STOPPED:
                return action.start_time
        # Assume that the action log is corrupt and therefore no action should
        # be taken
        return str(datetime.datetime.max)

    def shelved_since(self):
        if not self.actions_log or self.status not in self.shelved_vm_states:
            return None
        for action in self.actions_log:
            trans = get_transition(action.action)
            # First one to cause it to transition to a shelved state.
            if trans == StateTransition.TO_SHELVED:
                return action.start_time
        # Assume that the action log is corrupt and therefore no action should
        # be taken
        return str(datetime.datetime.max)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def delete(self):
        """Deletes the instance.

        :return: whether it was successful or not.
        """
        if not DRY_RUN:
            response = self.instance.delete()
            return response and response[0] == self._delete_succ_code
        return True

    def shelve(self):
        """Shelves the instance.

        :return: whether it was successful or not.
        """
        if not DRY_RUN:
            response = self.instance.shelve()
            return response and response[0] == self._shelve_succ_code
        return True


def get_transition(action_str):
    """Given an action, it returns the corresponding transition of that action.
    e.g. 'start' action returns a to_running transition, meaning that 'start'
    transitions the instance to a running state.

    :param action_str: action to check with.
    :return: a transition.
    :rtype: StateTransition
    """
    to_running = {'create', 'rebuild', 'resume', 'os-start', 'unpause',
                  'unshelve'}
    to_shelved = {'shelve', 'shelveOffload'}
    to_stopped = {'pause', 'os-stop', 'suspend'}
    if action_str in to_running:
        return StateTransition.TO_RUNNING
    if action_str in to_shelved:
        return StateTransition.TO_SHELVED
    if action_str in to_stopped:
        return StateTransition.TO_STOPPED
    return StateTransition.NO_CHANGE


def get_verdict(inst_dec, configuration):
    """
    :param inst_dec: instance decorator.
    :type: InstanceDecorator.
    :param configuration: program configuration.
    :return: which state to assign instance.
    """
    threshold_settings = configuration[GLOBAL_SETTINGS]  # Default

    if inst_dec.id in configuration[INSTANCE_SETTINGS]:
        threshold_settings = \
            configuration[INSTANCE_SETTINGS][inst_dec.id]

    if threshold_settings.should_shelve(inst_dec):
        return Verdict.SHELVE
    if threshold_settings.should_shelve_warn(inst_dec):
        return Verdict.SHELVE_WARN
    if threshold_settings.should_delete(inst_dec):
        return Verdict.DELETE
    if threshold_settings.should_delete_warn(inst_dec):
        return Verdict.DELETE_WARN
    return Verdict.DO_NOTHING


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
            inst_dec = InstanceDecorator(instance, nova)
            verdict = get_verdict(inst_dec, configuration)
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
            '(ID of) instance_j': TimeThresholdSettings
        }
    'settings': TimeThresholdSettings,
    'email_addresses': { 'tenant_name': 'email_address', ... }
    }

    :param spreadsheet_creds: Google Spreadsheet credentials.
    :return: the program settings.
    """
    return {INSTANCE_SETTINGS: fetch_instance_settings(spreadsheet_creds),
            GLOBAL_SETTINGS: fetch_global_settings(spreadsheet_creds),
            EMAIL_ADDRESSES: fetch_email_addresses(spreadsheet_creds)}


def get_worksheet_contents(spreadsheet_creds, worksheet_name):
    """
    :param spreadsheet_creds: GSpread crednetials.
    :param worksheet_name:  worksheet name.
    :return: the contents of the worksheet (using get_all_records() func).
    """
    gc = gspread.authorize(spreadsheet_creds)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet(
        worksheet_name)
    return sheet.get_all_records()


def fetch_instance_settings(spreadsheet_creds):
    """Returns the instance settings.

    :param spreadsheet_creds: Google Spreadsheet credentials.
    :return: the instance settings as a dict:
    {
        '(ID of) instance_j': TimeThresholdSettings
    }
    """

    def parse_value(value):
        if not value:
            return float('inf')
        v = float(value)
        if v < 0:
            raise RackspaceAutomationException('Treshold cannot be negative.')
        return v

    def get_time_threshold_settings_params(row_dict):
        shelve_running_warning_threshold = \
            parse_value(row_dict[SHELVE_RUNNING_WARNING_THRESHOLD])
        shelve_stopped_warning_threshold = \
            parse_value(row_dict[SHELVE_STOPPED_WARNING_THRESHOLD])
        delete_warning_threshold = \
            parse_value(row_dict[DELETE_WARNING_THRESHOLD])
        shelve_running_threshold = \
            parse_value(row_dict[SHELVE_RUNNING_THRESHOLD])
        shelve_stopped_threshold = \
            parse_value(row_dict[SHELVE_STOPPED_THRESHOLD])
        delete_shelved_threshold = \
            parse_value(row_dict[DELETE_SHELVED_THRESHOLD])
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
    contents = get_worksheet_contents(spreadsheet_creds,
                                      INSTANCE_SETTINGS_WORKSHEET)
    if not contents:
        return {}
    for row_dict in contents:
        instance_id = row_dict[INSTANCE_ID]
        if instance_id:
            instance_settings[instance_id] = \
                TimeThresholdSettings(
                    **get_time_threshold_settings_params(
                        row_dict))
    return instance_settings


def fetch_global_settings(spreadsheet_creds):
    """Returns the global settings from the Spreadsheet.

    :param spreadsheet_creds: Google Spreadsheet credentials.
    :return: global settings of the program.
    :rtype: TimeThresholdSettings
    """

    def validate_row(row):
        if 'shelve_running_warning_threshold' not in row \
                or 'shelve_stopped_warning_threshold' not in row \
                or 'delete_warning_threshold' not in row \
                or 'shelve_running_threshold' not in row \
                or 'shelve_stopped_threshold' not in row \
                or 'delete_shelved_threshold' not in row:
            raise RackspaceAutomationException("Invalid global threshold "
                                               "settings.")

    contents = get_worksheet_contents(spreadsheet_creds, SETTINGS_WORKSHEET)
    if not contents:
        raise RackspaceAutomationException("Settings worksheet is empty.")
    validate_row(contents[0])
    return TimeThresholdSettings(**contents[0])


def fetch_email_addresses(spreadsheet_creds):
    """Returns the tenant's notification email addresses from the Spreadsheet.

    :param spreadsheet_creds: Google Spreadsheet credentials.
    :return: email addresses that are setup for each tenant.
    """

    def validate_row(row):
        if TENANT_NAME not in row or EMAIL_ADDRESS not in row:
            raise RackspaceAutomationException("{} is not in the row "
                                               "content, probably worksheet "
                                               "headers are setup "
                                               "incorrectly.")

    contents = get_worksheet_contents(spreadsheet_creds,
                                      EMAIL_ADDRESSES_WORKSHEET)
    if not contents:
        raise RackspaceAutomationException(
            "Email addresses worksheet is empty.")
    email_addresses = {}
    for row in contents:
        validate_row(row)
        email_addresses[row[TENANT_NAME]] = row[EMAIL_ADDRESS]
    return email_addresses


def get_credentials(project):
    """Get the OpenStack credentials from the ENV vars.

    :param project: project to connect to.
    :return: keystoneclient.v3.Password instance.
    """
    url = OPENSTACK_URL
    username = OPENSTACK_USERNAME
    password = OPENSTACK_PASSWORD
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


def get_ses_client():
    """
    :return: the ses client, made for the tests.
    """
    return ses_client


def send_email(configuration, items_dict, subject, message_format):
    """Sends out an email with the given subjct and message format.

    :param configuration:  program configuration.
    :param items_dict: dict to iterate through its items (tenants to instances
        list).
    :param subject: email subject.
    :param message_format: email message format.
    """
    for tenant, instances in items_dict.items():
        destination = {'ToAddresses': [configuration[EMAIL_ADDRESSES][tenant]]}
        message = message_format.format(tenant, instances)
        message_id = get_ses_client().send_email(Source=SOURCE_EMAIL_ADDRESS,
                                                 Destination=destination,
                                                 Message={
                                                     'Subject': {
                                                         'Data': subject},
                                                     'Body': {
                                                         'Html': {
                                                             'Data': message}}
                                                 })['MessageId']
        logger.info('Sent a message to {0} with ID {1}.'.format(destination,
                                                                message_id))


def send_warnings(configuration, shelve_warnings, delete_warnings):
    """Sends out a warning regarding the given instances.

    :param configuration: program configuration.
    :param shelve_warnings: instances that their owners should be warned before
     shelving.
    :param delete_warnings: instances that their owners should be warned before
     deletion.
    """
    subject = SHELVE_WARNING_SUBJ
    message = SHELVE_WARNING_MSG
    send_email(configuration, shelve_warnings, subject, message)

    subject = DELETE_WARNING_SUBJ
    message = DELETE_WARNING_MSG
    send_email(configuration, delete_warnings, subject, message)


def delete_instances(configuration, instances_to_delete):
    """Delete the shelved instances.

    :param configuration: program configuration.
    :param instances_to_delete: instances to delete.
    """
    for tenant, instances in instances_to_delete.items():
        for inst_dec in instances:
            if not inst_dec.delete():
                logger.error(
                    'Could not delete instance with name: {0} and '
                    'id: {1} at tenant {2}'.format(
                        inst_dec.name, inst_dec.id, tenant))
    subject = DELETE_NOTIF_SUBJ
    message = DELETE_NOTIF_MSG
    send_email(configuration, instances_to_delete, subject, message)


def shelve_instances(configuration, instances_to_shelve):
    """Shelve the instances.

    :param configuration: program configuration.
    :param instances_to_shelve: instances to shelve.
    """
    for tenant, instances in instances_to_shelve.items():
        for inst_dec in instances:
            if not inst_dec.shelve():
                logger.error(
                    'Could not shelve instance with name: {0} and '
                    'id: {1} at tenant {2}'.format(
                        inst_dec.name, inst_dec.id, tenant))

    subject = SHELVE_NOTIF_SUBJ
    message = SHELVE_NOTIF_MSG
    send_email(configuration, instances_to_shelve, subject, message)


def add_missing_tenant_email_addresses(project_names, configuration,
                                       spreadsheet_creds):
    """Adds default notification email addresses for new tenants.

    :param project_names: tenant names.
    :param configuration: current configuration.
    :param spreadsheet_creds: Google Spreadsheet credentials.
    """
    tenants_to_add = []
    for project in project_names:
        if project not in configuration[EMAIL_ADDRESSES]:
            configuration[EMAIL_ADDRESSES][project] = \
                DEFAULT_NOTIFICATION_EMAIL_ADDRESS
            tenants_to_add.append(project)

    gc = gspread.authorize(spreadsheet_creds)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet(EMAIL_ADDRESSES_WORKSHEET)
    for project in tenants_to_add:
        sheet.append_row([project, DEFAULT_NOTIFICATION_EMAIL_ADDRESS])


def check_os_environ_vars():
    """Checks whether all the OS Environment exist.
    :raises: if any os.environ is missing.
    """
    if not SOURCE_EMAIL_ADDRESS:
        raise RackspaceAutomationException(
            'Missing SOURCE_EMAIL_ADDRESS env var')
    if not CREDENTIALS_FILE_PATH:
        raise RackspaceAutomationException(
            'Missing CREDENTIALS_FILE_PATH env var')
    if not SPREADSHEET_ID:
        raise RackspaceAutomationException('Missing SPREADSHEET_ID env var')
    if not SETTINGS_WORKSHEET:
        raise RackspaceAutomationException(
            'Missing SETTINGS_WORKSHEET env var')
    if not EMAIL_ADDRESSES_WORKSHEET:
        raise RackspaceAutomationException(
            'Missing EMAIL_ADDRESSES_WORKSHEET env var')
    if not INSTANCE_SETTINGS_WORKSHEET:
        raise RackspaceAutomationException(
            'Missing INSTANCE_SETTINGS_WORKSHEET env var')
    if not OPENSTACK_MAIN_PROJECT:
        raise RackspaceAutomationException(
            'Missing OPENSTACK_MAIN_PROJECT env var')
    if not OPENSTACK_URL:
        raise RackspaceAutomationException('Missing OPENSTACK_URL env var')
    if not OPENSTACK_USERNAME:
        raise RackspaceAutomationException(
            'Missing OPENSTACK_USERNAME env var')
    if not OPENSTACK_PASSWORD:
        raise RackspaceAutomationException(
            'Missing OPENSTACK_PASSWORD env var')
    if not DEFAULT_NOTIFICATION_EMAIL_ADDRESS:
        raise RackspaceAutomationException(
            'Missing DEFAULT_NOTIFICATION_EMAIL_ADDRESS env var')


def main(event, context):
    check_os_environ_vars()
    spreadsheet_credentials = get_spreadsheet_creds()
    configuration = fetch_configuration(spreadsheet_credentials)
    main_proj_creds = get_credentials(OPENSTACK_MAIN_PROJECT)
    project_names = get_tenant_names(main_proj_creds)
    add_missing_tenant_email_addresses(project_names, configuration,
                                       spreadsheet_credentials)
    violating_instances = get_violating_instances(project_names, configuration)
    shelve_instances(configuration=configuration,
                     instances_to_shelve=violating_instances[
                         'instances_to_shelve'])
    delete_instances(configuration=configuration,
                     instances_to_delete=violating_instances[
                         'instances_to_delete'])
    send_warnings(configuration=configuration,
                  shelve_warnings=violating_instances['shelve_warnings'],
                  delete_warnings=violating_instances['delete_warnings'])
