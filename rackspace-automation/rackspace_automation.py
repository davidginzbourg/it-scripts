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

import html_formats as h_formats

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ses_client = boto3.client('ses', region_name='eu-west-1')

###############
DRY_RUN = True
###############

INSTANCE_SETTINGS = 'instance_settings'
GLOBAL_SETTINGS = 'settings'
EMAIL_ADDRESSES = 'email_addresses'
TENANT_SETTINGS = 'tenant_settings'
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
TENANT_SETTINGS_WORKSHEET = os.environ.get('TENANT_SETTINGS_WORKSHEET')
OPENSTACK_MAIN_PROJECT = os.environ.get('OPENSTACK_MAIN_PROJECT')
OPENSTACK_URL = os.environ.get('OPENSTACK_URL')
OPENSTACK_USERNAME = os.environ.get('OPENSTACK_USERNAME')
OPENSTACK_PASSWORD = os.environ.get('OPENSTACK_PASSWORD')
DEFAULT_NOTIFICATION_EMAIL_ADDRESS = \
    os.environ.get('DEFAULT_NOTIFICATION_EMAIL_ADDRESS')

EMAIL_SUBJECT_FORMAT = "(test) RackSpace action and warning notifications " \
                       "for the {} tenant"
GLOBAL_EMAIL_SUBJECT = "(test) RackSpace action and warning notifications"

SHELVE_WARNING_MSG = 'The following instances in the {0} tenant will be ' \
                     'shelved soon:'
GLOBAL_SHELVE_WARNING_MSG = 'The following instances will be shelved soon:'

DELETE_WARNING_MSG = 'The following instances in the {0} tenant will be ' \
                     'deleted soon:'
GLOBAL_DELETE_WARNING_MSG = 'The following instances will be deleted soon:'

DELETE_NOTIF_MSG = 'The following instances in the {0} tenant were deleted:'
GLOBAL_DELETE_NOTIF_MSG = 'The following instances were deleted:'

SHELVE_NOTIF_MSG = 'The following instances in the {0} tenant were ' \
                   'shelved:'
GLOBAL_SHELVE_NOTIF_MSG = 'The following instances were shelved:'


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
                or shelve_stopped_warning_threshold > \
                        shelve_stopped_threshold \
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

    def get_shelve_running_warning_days(self):
        """
        :return: a 1.f days format of the threshold.
        """
        return '%.1f' % float(self.shelve_running_warning_threshold / 86400)

    def get_shelve_stopped_warning_days(self):
        """
        :return: a 1.f days format of the threshold.
        """
        return '%.1f' % float(self.shelve_stopped_warning_threshold / 86400)

    def get_delete_warning_days(self):
        """
        :return: a 1.f days format of the threshold.
        """
        return '%.1f' % float(self.delete_warning_threshold / 86400)

    def get_shelve_running_days(self):
        """
        :return: a 1.f days format of the threshold.
        """
        return '%.1f' % float(self.shelve_running_threshold / 86400)

    def get_shelve_stopped_days(self):
        """
        :return: a 1.f days format of the threshold.
        """
        return '%.1f' % float(self.shelve_stopped_threshold / 86400)

    def get_delete_shelved_days(self):
        """
        :return: a 1.f days format of the threshold.
        """
        return '%.1f' % float(self.delete_shelved_threshold / 86400)


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

        self.last_action_result = None
        self.action_message = None

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
        if not self.actions_log or not self.is_running:
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
        if not self.actions_log or not self.is_stopped:
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
        if not self.actions_log or not self.is_shelved:
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
        self.last_action_result = True
        if not DRY_RUN:
            response = self.instance.delete()
            self.last_action_result = response \
                                      and response[0] == self._delete_succ_code
        return self.last_action_result

    def shelve(self):
        """Shelves the instance.

        :return: whether it was successful or not.
        """
        self.last_action_result = True
        if not DRY_RUN:
            response = self.instance.shelve()
            self.last_action_result = response \
                                      and response[0] == self._shelve_succ_code
        return self.last_action_result

    def get_last_action_result(self):
        return self.last_action_result

    def add_action_message(self, message):
        """Adds a reason to display for the action to be taken.

        :param message: message to display for the action to be taken.
        """
        self.action_message = message

    def get_action_message(self):
        """
        :return: action message (i.e. the Note/Reason action message).
        """
        return self.action_message

    def get_status(self):
        """
        :return: a user friendly instance status.
        """
        if self.is_running:
            return 'running'
        if self.is_stopped:
            return 'stopped'
        if self.is_shelved:
            return 'shelved'
        return 'unknown'

    @property
    def is_running(self):
        return self.status in self.active_vm_states

    @property
    def is_stopped(self):
        return self.status in self.stopped_vm_states

    @property
    def is_shelved(self):
        return self.status in self.shelved_vm_states


def get_transition(action_str):
    """Given an action, it returns the corresponding transition of that action.
    e.g. 'start' action returns a to_running transition, meaning that 'start'
    transitions the instance to a running state.

    :param action_str: action to check with.
    :return: a transition.
    :rtype: StateTransition
    """
    to_running = {'create', 'rebuild', 'resume', 'restore', 'start',
                  'unpause', 'unshelve', 'unrescue', 'set admin password',
                  'backup', 'snapshot', 'reboot', 'revert resize',
                  'confirm resize'}
    to_shelved = {'shelve', 'shelveOffload'}
    to_stopped = {'stop', 'snapshot', 'backup'}
    if action_str in to_running:
        return StateTransition.TO_RUNNING
    if action_str in to_shelved:
        return StateTransition.TO_SHELVED
    if action_str in to_stopped:
        return StateTransition.TO_STOPPED
    return StateTransition.NO_CHANGE


def get_days_remaining(in_cur_state_since, threshold):
    """Calculates the days remaining until the threshold is breached.

    :param in_cur_state_since: date in iso format.
    :param threshold: threshold (seconds).
    :return: how many days remaining until the threshold is breached.
    """
    if threshold == float('inf'):
        return 'inf'
    in_cur_state_since_parsed = dateutil.parser.parse(
        in_cur_state_since).replace(tzinfo=None)
    days_delta = in_cur_state_since_parsed + datetime.timedelta(
        seconds=threshold) - get_utc_now()
    return str(days_delta.days)


def get_action_message(inst_dec, verdict, threshold_settings):
    """
    :param inst_dec: instance decorator.
    :param verdict: action verdict
    :param threshold_settings: threshold settings of the instance.
    :return: the message to display for the given verdict.
    """
    message = ''
    days = '?'
    days_remaining = '?'
    if verdict == Verdict.SHELVE:
        if inst_dec.is_running:
            days = threshold_settings.get_shelve_running_days()
        elif inst_dec.is_stopped:
            days = threshold_settings.get_shelve_stopped_days()
        message = h_formats.action_msg_fmt.format(
            inst_dec.get_status(), days)

    elif verdict == Verdict.SHELVE_WARN:
        if inst_dec.is_running:
            days_remaining = get_days_remaining(
                inst_dec.running_since(),
                threshold_settings.shelve_running_threshold)
            days = threshold_settings.get_shelve_running_days()
        elif inst_dec.is_stopped:
            days_remaining = get_days_remaining(
                inst_dec.stopped_since(),
                threshold_settings.shelve_stopped_threshold)
            days = threshold_settings.get_shelve_stopped_days()
        message = h_formats.shlv_wrn_msg_fmt.format(
            days_remaining, inst_dec.get_status(), days)

    elif verdict == Verdict.DELETE:
        days = threshold_settings.get_delete_shelved_days()
        message = h_formats.action_msg_fmt.format(
            inst_dec.get_status(), days)

    elif verdict == Verdict.DELETE_WARN:
        days_remaining = get_days_remaining(
            inst_dec.shelved_since(),
            threshold_settings.delete_shelved_threshold)
        days = threshold_settings.get_delete_warning_days()
        message = h_formats.del_wrn_msg_fmt.format(
            days_remaining, inst_dec.get_status(), days)

    return message


def get_verdict(inst_dec, configuration, project_name):
    """Calculates which state to assign instance and a message to display
    regarding the action. Note that the configuration of an instance has a
    higher priority over a tenant settings.

    :param inst_dec: instance decorator.
    :type: InstanceDecorator.
    :param configuration: program configuration.
    :param project_name: project name that the instance resides in.
    :return: which state to assign instance and a message to display regarding
    the action.
    """
    threshold_settings = configuration[GLOBAL_SETTINGS]  # Default

    if project_name in configuration[TENANT_SETTINGS]:
        threshold_settings = configuration[TENANT_SETTINGS][project_name]

    if inst_dec.id in configuration[INSTANCE_SETTINGS]:
        threshold_settings = \
            configuration[INSTANCE_SETTINGS][inst_dec.id]

    verdict = Verdict.DO_NOTHING
    if threshold_settings.should_shelve(inst_dec):
        verdict = Verdict.SHELVE
    elif threshold_settings.should_shelve_warn(inst_dec):
        verdict = Verdict.SHELVE_WARN
    elif threshold_settings.should_delete(inst_dec):
        verdict = Verdict.DELETE
    elif threshold_settings.should_delete_warn(inst_dec):
        verdict = Verdict.DELETE_WARN
    message = get_action_message(inst_dec, verdict, threshold_settings)
    inst_dec.add_action_message(message)
    return verdict


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
            verdict = get_verdict(inst_dec, configuration, project)
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
    'tenant_settings':
        {
            'project_j': TimeThresholdSettings
        }
    'settings': TimeThresholdSettings,
    'email_addresses': { 'tenant_name': 'email_address', ... }
    }

    :param spreadsheet_creds: Google Spreadsheet credentials.
    :return: the program settings.
    """
    return {INSTANCE_SETTINGS: fetch_instance_settings(spreadsheet_creds),
            GLOBAL_SETTINGS: fetch_global_settings(spreadsheet_creds),
            EMAIL_ADDRESSES: fetch_email_addresses(spreadsheet_creds),
            TENANT_SETTINGS: fetch_tenant_settings(spreadsheet_creds)}


def fetch_tenant_settings(spreadsheet_creds):
    """
    :param spreadsheet_creds: GSpread credentials.
    :return: the tenant settings dict.
    """
    tenant_settings = {}
    contents = get_worksheet_contents(spreadsheet_creds,
                                      TENANT_SETTINGS_WORKSHEET)
    if not contents:
        return {}
    for row_dict in contents:
        validate_has_min_vals(row_dict)
        project_name = row_dict[PROJECT_NAME]
        tenant_settings[project_name] = TimeThresholdSettings(
            **get_time_threshold_settings_params(row_dict))
    return tenant_settings


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


def parse_value(value):
    """Parses value from string to float
    :param value: value to parse.
    :return: parsed value.
    """
    if not value:
        return float('inf')
    v = float(value)
    if v < 0:
        raise RackspaceAutomationException('Threshold cannot be negative.')
    return v


def get_time_threshold_settings_params(row_dict):
    """
    :param row_dict: dictionary representing the row.
    :return: the parsed settings values.
    """
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


def fetch_instance_settings(spreadsheet_creds):
    """Returns the instance settings.

    :param spreadsheet_creds: Google Spreadsheet credentials.
    :return: the instance settings as a dict:
    {
        '(ID of) instance_j': TimeThresholdSettings
    }
    """
    instance_settings = {}
    contents = get_worksheet_contents(spreadsheet_creds,
                                      INSTANCE_SETTINGS_WORKSHEET)
    if not contents:
        return {}
    for row_dict in contents:
        validate_has_min_vals(row_dict)
        instance_id = row_dict[INSTANCE_ID]
        if instance_id:
            instance_settings[instance_id] = \
                TimeThresholdSettings(
                    **get_time_threshold_settings_params(
                        row_dict))
    return instance_settings


def validate_has_min_vals(row):
    """Validates that the row has all the basic required keys.

    Raises RackspaceAutomationException when row is in an invalid format.
    :param row: row in the spreadsheet.
    """
    if 'shelve_running_warning_threshold' not in row \
            or 'shelve_stopped_warning_threshold' not in row \
            or 'delete_warning_threshold' not in row \
            or 'shelve_running_threshold' not in row \
            or 'shelve_stopped_threshold' not in row \
            or 'delete_shelved_threshold' not in row:
        raise RackspaceAutomationException("Invalid threshold settings.")


def fetch_global_settings(spreadsheet_creds):
    """Returns the global settings from the Spreadsheet.

    :param spreadsheet_creds: Google Spreadsheet credentials.
    :return: global settings of the program.
    :rtype: TimeThresholdSettings
    """
    contents = get_worksheet_contents(spreadsheet_creds, SETTINGS_WORKSHEET)
    if not contents:
        raise RackspaceAutomationException("Settings worksheet is empty.")
    validate_has_min_vals(contents[0])
    for key in contents[0].keys():
        contents[0][key] = parse_value(contents[0][key])
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


def send_email(subject, message, to_addresses):
    """Sends out an email with the given subject and message.

    :param subject: email subject.
    :param message: email message.
    :param to_addresses: addresses to send to.
    """

    destination = {'ToAddresses': to_addresses}
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


def perform_actions(violating_instances, configuration):
    """Performs actions.

    :param violating_instances: a dict of lists of rule violating instances.
    :param configuration: program configuration.
    """
    shelve_instances(configuration=configuration,
                     instances_to_shelve=violating_instances[
                         'instances_to_shelve'])
    delete_instances(configuration=configuration,
                     instances_to_delete=violating_instances[
                         'instances_to_delete'])


def send_email_notifications(violating_instances, configuration):
    """Sends out notifications.

    :param violating_instances: a dict of lists of rule violating instances.
    :param configuration: program configuration.
    """
    tenant_messages = {}

    def build_html(instances_key, p_text_format, is_action):
        for tenant, instances in violating_instances[instances_key].items():
            if configuration[EMAIL_ADDRESSES][tenant] != \
                    DEFAULT_NOTIFICATION_EMAIL_ADDRESS:
                table_row_str_buf = ""
                for inst_dec in instances:
                    status = "Succeeded" \
                        if inst_dec.get_last_action_result() else "Failed"
                    if is_action:
                        table_row_str_buf += \
                            h_formats.action_table_cell_format.format(
                                inst_dec.name,
                                status,
                                inst_dec.get_action_message())
                    else:
                        table_row_str_buf += \
                            h_formats.warning_table_cell_format.format(
                                inst_dec.name,
                                inst_dec.get_action_message())
                paragraph_text = p_text_format.format(tenant)
                if is_action:
                    table_str = h_formats.action_table.format(
                        table_row_str_buf)
                else:
                    table_str = h_formats.warning_table.format(
                        table_row_str_buf)

                tenant_messages[tenant] = h_formats.p.format(
                    paragraph_text) + table_str

    def build_global_html(instances_key, p_text, is_action):
        table_row_str_buf = ""
        is_empty = True
        for tenant, instances in violating_instances[instances_key].items():
            is_empty = False
            for inst_dec in instances:
                status = "Succeeded" \
                    if inst_dec.get_last_action_result() else "Failed"
                if is_action:
                    table_row_str_buf += \
                        h_formats.global_action_table_cell_format.format(
                            tenant,
                            inst_dec.name,
                            status,
                            inst_dec.get_action_message())
                else:
                    table_row_str_buf += \
                        h_formats.global_warning_table_cell_format.format(
                            tenant,
                            inst_dec.name,
                            inst_dec.get_action_message())
        if is_empty:
            return ''
        if is_action:
            table_str = h_formats.global_action_table.format(
                table_row_str_buf)
        else:
            table_str = h_formats.global_warning_table.format(
                table_row_str_buf)
        return h_formats.p.format(p_text) + table_str

    build_html('instances_to_shelve', SHELVE_NOTIF_MSG, True)
    build_html('instances_to_delete', DELETE_NOTIF_MSG, True)
    build_html('shelve_warnings', SHELVE_WARNING_MSG, False)
    build_html('delete_warnings', DELETE_WARNING_MSG, False)
    global_tenant_message = build_global_html(
        'instances_to_shelve', GLOBAL_SHELVE_NOTIF_MSG, True)
    global_tenant_message += build_global_html(
        'instances_to_delete', GLOBAL_DELETE_NOTIF_MSG, True)
    global_tenant_message += build_global_html(
        'shelve_warnings', GLOBAL_SHELVE_WARNING_MSG, False)
    global_tenant_message += build_global_html(
        'delete_warnings', GLOBAL_DELETE_WARNING_MSG, False)
    for tenant_name, msg in tenant_messages.items():
        if configuration[EMAIL_ADDRESSES][tenant_name] != \
                DEFAULT_NOTIFICATION_EMAIL_ADDRESS:
            send_email(
                EMAIL_SUBJECT_FORMAT.format(tenant_name),
                h_formats.msg_html.format(msg),
                [configuration[EMAIL_ADDRESSES][tenant_name]])
    send_email(
        GLOBAL_EMAIL_SUBJECT,
        h_formats.msg_html.format(global_tenant_message),
        [DEFAULT_NOTIFICATION_EMAIL_ADDRESS])


def main(event, context):
    check_os_environ_vars()
    spreadsheet_credentials = get_spreadsheet_creds()
    configuration = fetch_configuration(spreadsheet_credentials)
    main_proj_creds = get_credentials(OPENSTACK_MAIN_PROJECT)
    project_names = get_tenant_names(main_proj_creds)
    add_missing_tenant_email_addresses(project_names, configuration,
                                       spreadsheet_credentials)
    violating_instances = get_violating_instances(project_names, configuration)
    perform_actions(violating_instances, configuration)
    send_email_notifications(violating_instances, configuration)
