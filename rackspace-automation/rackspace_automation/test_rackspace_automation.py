import unittest
import datetime as dt
from datetime import datetime

import mock
import numpy as np
from mock import MagicMock

import rackspace_automation
from rackspace_automation import InstanceDecorator, StateTransition

'''
List of rackspace_automation functions:

InstanceDecorator
RackspaceAutomationException
ServiceAccountCredentials
StateTransition
TimeThresholdSettings
Verdict
add_missing_tenant_email_addresses
check_os_environ_vars
delete_instances
fetch_configuration
fetch_email_addresses
fetch_global_settings
fetch_instance_settings
get_credentials
get_spreadsheet_creds
get_tenant_names
get_transition
get_verdict
get_violating_instances
main
send_warnings
shelve
'''

SECONDS_TO_DAYS = 86400
glb_exc_class = rackspace_automation.RackspaceAutomationException


class MockInstDec:
    def __init__(self, running_since=None, stopped_since=None,
                 shelved_since=None):
        self._running_since = running_since
        self._stopped_since = stopped_since
        self._shelved_since = shelved_since

    def running_since(self):
        return self._running_since

    def stopped_since(self):
        return self._stopped_since

    def shelved_since(self):
        return self._shelved_since


class MockInstDecNova:
    def __init__(self, instance_actions):
        self._instance_actions = instance_actions

    @property
    def instance_action(self):
        return self

    def list(self, _):
        return self._instance_actions


class MockAction:
    def __init__(self, action):
        self._action = action

    @property
    def action(self):
        return self._action

    @property
    def start_time(self):
        return TestInstanceDecorator.fixed_test_date


class TestTimeThresholdSettings(unittest.TestCase):
    def test_init(self):
        # warning, action, w, a, w, a
        args = [0, 1, 0, 1, 0, 1]

        for i in range(0, len(args), 2):
            args[i] = 1
            args[i + 1] = 0
            self.assertRaises(glb_exc_class,
                              rackspace_automation.TimeThresholdSettings,
                              *args)
            args[i] = 0
            args[i + 1] = 1
            # Should not raise an error
            rackspace_automation.TimeThresholdSettings(*args)

    @mock.patch('rackspace_automation.get_utc_now')
    def test_should_shelve_warn(self, mock_utcnow):
        # warning, action, w, a, w, a - in days (makes it easier to read the
        # dates
        args = np.array([2, 3, 2, 3, 2, 3]) * SECONDS_TO_DAYS
        now_year = 2000
        now_month = 1
        now_day = 10
        mock_utcnow.return_value = dt.datetime(now_year, now_month, now_day)

        tts = rackspace_automation.TimeThresholdSettings(*args)
        mock_inst_dec = MockInstDec()
        self.assertFalse(tts.should_shelve_warn(mock_inst_dec),
                         "Sent shelve warning when both "
                         "running\stopped_since() returned None.")

        mock_inst_dec = MockInstDec(
            running_since=dt.datetime(
                now_year, now_month, now_day - 1).isoformat())
        self.assertFalse(tts.should_shelve_warn(mock_inst_dec))

        mock_inst_dec = MockInstDec(stopped_since=dt.datetime(
            now_year, now_month, now_day - 1).isoformat())
        self.assertFalse(tts.should_shelve_warn(mock_inst_dec))

        mock_inst_dec = MockInstDec(
            running_since=dt.datetime(
                now_year, now_month, now_day - 1).isoformat(),
            stopped_since=dt.datetime(
                now_year, now_month, now_day - 1).isoformat())
        self.assertFalse(tts.should_shelve_warn(mock_inst_dec))

        mock_inst_dec = MockInstDec(
            running_since=dt.datetime(
                now_year, now_month, now_day - 3).isoformat())
        self.assertTrue(tts.should_shelve_warn(mock_inst_dec))

        mock_inst_dec = MockInstDec(
            stopped_since=dt.datetime(
                now_year, now_month, now_day - 3).isoformat())
        self.assertTrue(tts.should_shelve_warn(mock_inst_dec))

        mock_inst_dec = MockInstDec(
            running_since=dt.datetime(
                now_year, now_month, now_day - 3).isoformat(),
            stopped_since=dt.datetime(
                now_year, now_month, now_day - 3).isoformat())
        self.assertTrue(tts.should_shelve_warn(mock_inst_dec))

    @mock.patch('rackspace_automation.get_utc_now')
    def test_should_delete_warn(self, mock_utcnow):
        # warning, action, w, a, w, a - in days (makes it easier to read the
        # dates
        args = np.array([2, 3, 2, 3, 2, 3]) * SECONDS_TO_DAYS
        now_year = 2000
        now_month = 1
        now_day = 10
        mock_utcnow.return_value = dt.datetime(now_year, now_month, now_day)

        tts = rackspace_automation.TimeThresholdSettings(*args)
        mock_inst_dec = MockInstDec()
        self.assertFalse(tts.should_delete_warn(mock_inst_dec),
                         "Sent shelve warning when both "
                         "running\stopped_since() returned None.")

        mock_inst_dec = MockInstDec(
            shelved_since=dt.datetime(
                now_year, now_month, now_day - 1).isoformat())
        self.assertFalse(tts.should_delete_warn(mock_inst_dec))

        mock_inst_dec = MockInstDec(
            shelved_since=dt.datetime(
                now_year, now_month, now_day - 3).isoformat())
        self.assertTrue(tts.should_delete_warn(mock_inst_dec))

    @mock.patch('rackspace_automation.get_utc_now')
    def test_should_shelve(self, mock_utcnow):
        # warning, action, w, a, w, a - in days (makes it easier to read the
        # dates
        args = np.array([2, 3, 2, 3, 2, 3]) * SECONDS_TO_DAYS
        now_year = 2000
        now_month = 1
        now_day = 10
        mock_utcnow.return_value = dt.datetime(now_year, now_month, now_day)

        tts = rackspace_automation.TimeThresholdSettings(*args)
        mock_inst_dec = MockInstDec()
        self.assertFalse(tts.should_shelve(mock_inst_dec),
                         "Sent shelve warning when both "
                         "running\stopped_since() returned None.")

        mock_inst_dec = MockInstDec(
            running_since=dt.datetime(
                now_year, now_month, now_day - 1).isoformat())
        self.assertFalse(tts.should_shelve(mock_inst_dec))

        mock_inst_dec = MockInstDec(stopped_since=dt.datetime(
            now_year, now_month, now_day - 1).isoformat())
        self.assertFalse(tts.should_shelve(mock_inst_dec))

        mock_inst_dec = MockInstDec(
            running_since=dt.datetime(
                now_year, now_month, now_day - 1).isoformat(),
            stopped_since=dt.datetime(
                now_year, now_month, now_day - 1).isoformat())
        self.assertFalse(tts.should_shelve(mock_inst_dec))

        mock_inst_dec = MockInstDec(
            running_since=dt.datetime(
                now_year, now_month, now_day - 3).isoformat())
        self.assertTrue(tts.should_shelve(mock_inst_dec))

        mock_inst_dec = MockInstDec(
            stopped_since=dt.datetime(
                now_year, now_month, now_day - 3).isoformat())
        self.assertTrue(tts.should_shelve(mock_inst_dec))

        mock_inst_dec = MockInstDec(
            running_since=dt.datetime(
                now_year, now_month, now_day - 3).isoformat(),
            stopped_since=dt.datetime(
                now_year, now_month, now_day - 3).isoformat())
        self.assertTrue(tts.should_shelve(mock_inst_dec))

    @mock.patch('rackspace_automation.get_utc_now')
    def test_should_delete(self, mock_utcnow):
        # warning, action, w, a, w, a - in days (makes it easier to read the
        # dates
        args = np.array([2, 3, 2, 3, 2, 3]) * SECONDS_TO_DAYS
        now_year = 2000
        now_month = 1
        now_day = 10
        mock_utcnow.return_value = dt.datetime(now_year, now_month, now_day)

        tts = rackspace_automation.TimeThresholdSettings(*args)
        mock_inst_dec = MockInstDec()
        self.assertFalse(tts.should_delete(mock_inst_dec),
                         "Sent shelve warning when both "
                         "running\stopped_since() returned None.")

        mock_inst_dec = MockInstDec(
            shelved_since=dt.datetime(
                now_year, now_month, now_day - 1).isoformat())
        self.assertFalse(tts.should_delete(mock_inst_dec))

        mock_inst_dec = MockInstDec(
            shelved_since=dt.datetime(
                now_year, now_month, now_day - 3).isoformat())
        self.assertTrue(tts.should_delete(mock_inst_dec))

    @mock.patch('rackspace_automation.get_utc_now')
    def test_is_above_threshold(self, mock_utcnow):
        now_year = 2000
        now_month = 1
        now_day = 10
        mock_utcnow.return_value = dt.datetime(now_year, now_month, now_day)
        threshold_days = 4
        threshold_seconds = threshold_days * SECONDS_TO_DAYS
        is_above_threshold = rackspace_automation.TimeThresholdSettings \
            .is_above_threshold

        time = dt.datetime(now_year, now_month, now_day).isoformat()
        self.assertFalse(is_above_threshold(time, threshold_seconds))

        time = dt.datetime(
            now_year, now_month, now_day - (threshold_days // 2)).isoformat()
        self.assertFalse(is_above_threshold(time, threshold_seconds))

        time = dt.datetime(
            now_year, now_month, now_day - (2 * threshold_days)).isoformat()
        self.assertTrue(is_above_threshold(time, threshold_seconds))

        time = dt.datetime(
            now_year, now_month, now_day - threshold_days).isoformat()
        self.assertTrue(is_above_threshold(time, threshold_seconds))


class TestInstanceDecorator(unittest.TestCase):
    max_datetime = str(dt.datetime.max)
    fixed_test_date = dt.datetime(1990, 1, 1).isoformat()

    def test_name(self):
        instance = MagicMock()
        instance.name = 'name'
        inst_dec = InstanceDecorator(instance, MockInstDecNova([]))
        name = inst_dec.name

        self.assertEqual(name, 'name')

    def test_status(self):
        instance = MagicMock()
        setattr(instance, 'OS-EXT-STS:vm_state', 'cash me ousside')
        inst_dec = InstanceDecorator(instance, MockInstDecNova([]))
        status = inst_dec.status

        self.assertEqual(status, 'cash me ousside')

    def test_running_since_no_actions_log(self):
        inst_dec = InstanceDecorator(None, MockInstDecNova([]))

        self.assertIsNone(inst_dec.running_since())

    def test_running_since_wrong_server_status(self):
        instance = MagicMock()
        setattr(instance, 'OS-EXT-STS:vm_state', 'random_status')

        actions_log = [MockAction('random_action')]

        inst_dec = InstanceDecorator(instance, MockInstDecNova(actions_log))
        self.assertIsNone(inst_dec.running_since())

    def test_running_since_no_corresponding_action(self):
        instance = MagicMock()
        setattr(instance, 'OS-EXT-STS:vm_state', 'active')

        actions_log = [MockAction('shelve')]

        inst_dec = InstanceDecorator(instance, MockInstDecNova(actions_log))
        self.assertEqual(inst_dec.running_since(), self.max_datetime)

    def test_running_since_succeeds(self):
        instance = MagicMock()
        setattr(instance, 'OS-EXT-STS:vm_state', 'active')

        # Create transitions the instance into a running state.
        actions_log = [MockAction('shelve'), MockAction('create')]

        inst_dec = InstanceDecorator(instance, MockInstDecNova(actions_log))
        self.assertEqual(inst_dec.running_since(), self.fixed_test_date)

    def test_stopped_since_no_actions_log(self):
        inst_dec = InstanceDecorator(None, MockInstDecNova([]))

        self.assertIsNone(inst_dec.stopped_since())

    def test_stopped_since_wrong_server_status(self):
        instance = MagicMock()
        setattr(instance, 'OS-EXT-STS:vm_state', 'random_status')

        actions_log = [MockAction('random_action')]

        inst_dec = InstanceDecorator(instance, MockInstDecNova(actions_log))
        self.assertIsNone(inst_dec.stopped_since())

    def test_stopped_since_no_corresponding_action(self):
        instance = MagicMock()
        setattr(instance, 'OS-EXT-STS:vm_state', 'stopped')

        actions_log = [MockAction('unpause')]

        inst_dec = InstanceDecorator(instance, MockInstDecNova(actions_log))
        self.assertEqual(inst_dec.stopped_since(), self.max_datetime)

    def test_stopped_since_succeeds(self):
        instance = MagicMock()
        setattr(instance, 'OS-EXT-STS:vm_state', 'stopped')

        # Create transitions the instance into a running state.
        actions_log = [MockAction('shelve'), MockAction('pause')]

        inst_dec = InstanceDecorator(instance, MockInstDecNova(actions_log))
        self.assertEqual(inst_dec.stopped_since(), self.fixed_test_date)

    def test_shelved_since_no_actions_log(self):
        inst_dec = InstanceDecorator(None, MockInstDecNova([]))

        self.assertIsNone(inst_dec.shelved_since())

    def test_shelved_since_wrong_server_status(self):
        instance = MagicMock()
        setattr(instance, 'OS-EXT-STS:vm_state', 'random_status')

        actions_log = [MockAction('random_action')]

        inst_dec = InstanceDecorator(instance, MockInstDecNova(actions_log))
        self.assertIsNone(inst_dec.shelved_since())

    def test_shelved_since_no_corresponding_action(self):
        instance = MagicMock()
        setattr(instance, 'OS-EXT-STS:vm_state', 'shelved_offloaded')

        actions_log = [MockAction('unpause')]

        inst_dec = InstanceDecorator(instance, MockInstDecNova(actions_log))
        self.assertEqual(inst_dec.shelved_since(), self.max_datetime)

    def test_shelved_since_succeeds(self):
        instance = MagicMock()
        setattr(instance, 'OS-EXT-STS:vm_state', 'shelved_offloaded')

        # Create transitions the instance into a running state.
        actions_log = [MockAction('pause'), MockAction('shelve')]

        inst_dec = InstanceDecorator(instance, MockInstDecNova(actions_log))
        self.assertEqual(inst_dec.shelved_since(), self.fixed_test_date)


class TestGeneral(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)
        self.os_environ = {
            'SOURCE_EMAIL_ADDRESS': 'value_source_email_address',
            'CREDENTIALS_FILE_PATH': 'value_credentials_file_path',
            'SPREADSHEET_ID': 'value_spreadsheet_id',
            'SETTINGS_WORKSHEET': 'value_settings_worksheet',
            'EMAIL_ADDRESSES_WORKSHEET': 'value_email_addresses_worksheet',
            'INSTANCE_SETTINGS_WORKSHEET': 'value_instance_settings_worksheet',
            'OPENSTACK_MAIN_PROJECT': 'value_openstack_main_project',
            'OPENSTACK_URL': 'value_openstack_url',
            'OPENSTACK_USERNAME': 'value_openstack_username',
            'OPENSTACK_PASSWORD': 'value_openstack_password',
            'DEFAULT_NOTIFICATION_EMAIL_ADDRESS':
                'value_default_notification_email_address'
        }

    def mock_global_os_env_vars(self):
        rackspace_automation.SOURCE_EMAIL_ADDRESS = self.os_environ[
            'SOURCE_EMAIL_ADDRESS']
        rackspace_automation.CREDENTIALS_FILE_PATH = self.os_environ[
            'CREDENTIALS_FILE_PATH']
        rackspace_automation.SPREADSHEET_ID = self.os_environ[
            'SPREADSHEET_ID']
        rackspace_automation.SETTINGS_WORKSHEET = self.os_environ[
            'SETTINGS_WORKSHEET']
        rackspace_automation.EMAIL_ADDRESSES_WORKSHEET = self.os_environ[
            'EMAIL_ADDRESSES_WORKSHEET']
        rackspace_automation.INSTANCE_SETTINGS_WORKSHEET = self.os_environ[
            'INSTANCE_SETTINGS_WORKSHEET']
        rackspace_automation.OPENSTACK_MAIN_PROJECT = self.os_environ[
            'OPENSTACK_MAIN_PROJECT']
        rackspace_automation.OPENSTACK_URL = self.os_environ[
            'OPENSTACK_URL']
        rackspace_automation.OPENSTACK_USERNAME = self.os_environ[
            'OPENSTACK_USERNAME']
        rackspace_automation.OPENSTACK_PASSWORD = self.os_environ[
            'OPENSTACK_PASSWORD']
        rackspace_automation.DEFAULT_NOTIFICATION_EMAIL_ADDRESS = \
            self.os_environ['DEFAULT_NOTIFICATION_EMAIL_ADDRESS']

    @mock.patch('rackspace_automation.fetch_email_addresses')
    @mock.patch('rackspace_automation.fetch_global_settings')
    @mock.patch('rackspace_automation.fetch_instance_settings')
    def test_fetch_configuration(self, mock_fetch_instance_settings,
                                 mock_fetch_global_settings,
                                 mock_fetch_email_addresses):
        """Tests fetch_configuration.
        """
        some_inst_settings = 'some_inst_settings'
        some_global_settings = 'some_global_settings'
        some_email_addr = 'some_email_addr'

        mock_fetch_instance_settings.return_value = some_inst_settings
        mock_fetch_global_settings.return_value = some_global_settings
        mock_fetch_email_addresses.return_value = some_email_addr

        return_val = rackspace_automation.fetch_configuration('dummy_str')
        mock_fetch_instance_settings.assert_called()
        mock_fetch_global_settings.assert_called()
        mock_fetch_email_addresses.assert_called()

        self.assertEqual(return_val[rackspace_automation.INSTANCE_SETTINGS],
                         some_inst_settings,
                         'Instance settings value is incorrect')
        self.assertEqual(return_val[rackspace_automation.GLOBAL_SETTINGS],
                         some_global_settings,
                         'Global settings value is incorrect')
        self.assertEqual(return_val[rackspace_automation.EMAIL_ADDRESSES],
                         some_email_addr,
                         'Email Addresses value is incorrect')

    @mock.patch('rackspace_automation.get_worksheet_contents')
    def test_fetch_email_addresses(self, mock_contents):
        """Tests the fetch_email_addresses function.
        """
        contents = []
        mock_contents.return_value = contents

        self.assertRaises(glb_exc_class,
                          rackspace_automation.fetch_email_addresses, None)

        contents.extend([{'random_key': 'random_val'}])
        self.assertRaises(glb_exc_class,
                          rackspace_automation.fetch_email_addresses, None)
        del contents[:]

        tenant1 = 'tenant1'
        tenant2 = 'tenant2'
        email1 = 'email1'
        email2 = 'email2'
        contents.extend([{rackspace_automation.TENANT_NAME: tenant1,
                          rackspace_automation.EMAIL_ADDRESS: email1},
                         {rackspace_automation.TENANT_NAME: tenant2,
                          rackspace_automation.EMAIL_ADDRESS: email2}])
        result = rackspace_automation.fetch_email_addresses(None)
        self.assertIn(tenant1, result, "tenant1 doesn't appear in the result")
        self.assertIn(tenant2, result, "tenant2 doesn't appear in the result")
        self.assertEqual(result[tenant1], email1, 'first email address was '
                                                  'not found')
        self.assertEqual(result[tenant2], email2, 'first email address was '
                                                  'not found')

    @mock.patch('rackspace_automation.TimeThresholdSettings')
    @mock.patch('rackspace_automation.get_worksheet_contents')
    def test_fetch_global_settings(self, mock_contents, mock_ttsettings):
        """Tests the fetch_global_settings function.
        """
        contents = []
        mock_contents.return_value = contents
        self.assertRaises(glb_exc_class,
                          rackspace_automation.fetch_global_settings, None)

        contents.extend([{'random_key': 'random_val'}])
        self.assertRaises(glb_exc_class,
                          rackspace_automation.fetch_global_settings, None)
        del contents[:]

        val1 = 'val1'
        val2 = 'val2'
        val3 = 'val3'
        val4 = 'val4'
        val5 = 'val5'
        val6 = 'val6'
        contents.extend([{'shelve_running_warning_threshold': val1,
                          'shelve_stopped_warning_threshold': val2,
                          'delete_warning_threshold': val3,
                          'shelve_running_threshold': val4,
                          'shelve_stopped_threshold': val5,
                          'delete_shelved_threshold': val6}])
        rackspace_automation.fetch_global_settings(None)
        mock_ttsettings.assert_called_with(**contents[0])

    @mock.patch('rackspace_automation.get_worksheet_contents')
    def test_fetch_instance_settings(self, mock_contents):
        """Tests fetch_instance_settings.
        """
        contents = []
        mock_contents.return_value = contents

        self.assertFalse(rackspace_automation.fetch_instance_settings(None),
                         "Fetch instance settings returned a non-empty dict.")

        inst1 = 'inst1'
        inst_set1 = {rackspace_automation.INSTANCE_NAME: inst1,
                     'shelve_running_warning_threshold':
                         '',
                     'shelve_stopped_warning_threshold':
                         1.0,
                     'delete_warning_threshold': 2.0,
                     'shelve_running_threshold': 3.0,
                     'shelve_stopped_threshold': 4.0,
                     'delete_shelved_threshold': 5.0}
        inst2 = 'inst2'
        inst_set2 = {rackspace_automation.INSTANCE_NAME: inst2,
                     'shelve_running_warning_threshold':
                         10.0,
                     'shelve_stopped_warning_threshold':
                         11.0,
                     'delete_warning_threshold': 12.0,
                     'shelve_running_threshold': 13.0,
                     'shelve_stopped_threshold': 14.0,
                     'delete_shelved_threshold': 15.0}
        inst3 = 'inst3'
        inst_set3 = {rackspace_automation.INSTANCE_NAME: inst3,
                     'shelve_running_warning_threshold':
                         110.0,
                     'shelve_stopped_warning_threshold':
                         111.0,
                     'delete_warning_threshold': 112.0,
                     'shelve_running_threshold': 113.0,
                     'shelve_stopped_threshold': 114.0,
                     'delete_shelved_threshold': 115.0}
        project1 = 'project1'
        project2 = 'project2'
        row1 = {rackspace_automation.PROJECT_NAME: project1}
        row1.update(inst_set1)
        row2 = {rackspace_automation.PROJECT_NAME: project2}
        row2.update(inst_set2)
        row3 = {rackspace_automation.PROJECT_NAME: project1}
        row3.update(inst_set3)
        contents.extend([row1, row2, row3])

        result = rackspace_automation.fetch_instance_settings(None)

        # This must be done in order to successfully do the double
        # 'dereference'
        for inst in [inst_set1, inst_set2, inst_set3]:
            del inst[rackspace_automation.INSTANCE_NAME]

        inst_set1['shelve_running_warning_threshold'] = float('inf')
        correct_result = {
            project1: {
                inst1: rackspace_automation.TimeThresholdSettings(**inst_set1),
                inst3: rackspace_automation.TimeThresholdSettings(**inst_set3)
            },
            project2: {
                inst2: rackspace_automation.TimeThresholdSettings(**inst_set2)
            }
        }

        self.assertDictEqual(result, correct_result, "Result dict isn't "
                                                     "correct.")

    def test_get_transition(self):
        to_running = 'create'
        to_shelved = 'shelve'
        to_stopped = 'suspend'
        get_transition = rackspace_automation.get_transition
        self.assertEqual(get_transition(to_running),
                         StateTransition.TO_RUNNING)
        self.assertEqual(get_transition(to_shelved),
                         StateTransition.TO_SHELVED)
        self.assertEqual(get_transition(to_stopped),
                         StateTransition.TO_STOPPED)
        self.assertEqual(get_transition('random_action'),
                         StateTransition.NO_CHANGE)

    def test_get_verdict_uses_default_configuration(self):
        project_name = 'project_name'
        inst_dec = None
        global_settings = MagicMock()
        instance_settings = {}
        configuration = {
            rackspace_automation.GLOBAL_SETTINGS:
                global_settings,
            rackspace_automation.INSTANCE_SETTINGS:
                instance_settings}

        global_settings.should_shelve = MagicMock(return_value=True)

        rackspace_automation.get_verdict(project_name, inst_dec, configuration)
        global_settings.should_shelve.assert_any_call(None)

    def test_get_verdict_configuration_swap(self):
        project_name = 'project_name'
        inst_dec = MagicMock()
        inst_dec.name = 'inst1'
        instance_time_settings = MagicMock()
        global_settings = MagicMock()
        instance_settings = {
            project_name: {
                inst_dec.name: instance_time_settings}}
        configuration = {
            rackspace_automation.GLOBAL_SETTINGS:
                global_settings,
            rackspace_automation.INSTANCE_SETTINGS:
                instance_settings}

        instance_time_settings.should_shelve = MagicMock(return_value=True)

        rackspace_automation.get_verdict(project_name, inst_dec, configuration)
        instance_time_settings.should_shelve.assert_any_call(inst_dec)

    def test_get_verdict_shelves(self):
        project_name = 'project_name'
        inst_dec = MagicMock()
        inst_dec.name = 'inst1'
        instance_time_settings = MagicMock()
        global_settings = MagicMock()
        instance_settings = {
            project_name: {
                inst_dec.name: instance_time_settings}}
        configuration = {
            rackspace_automation.GLOBAL_SETTINGS:
                global_settings,
            rackspace_automation.INSTANCE_SETTINGS:
                instance_settings}

        instance_time_settings.should_shelve = MagicMock(return_value=True)

        res = rackspace_automation.get_verdict(
            project_name, inst_dec, configuration)

        self.assertEqual(res, rackspace_automation.Verdict.SHELVE)

    def test_get_verdict_returns_shelves_warn(self):
        project_name = 'project_name'
        inst_dec = MagicMock()
        inst_dec.name = 'inst1'
        instance_time_settings = MagicMock()
        global_settings = MagicMock()
        instance_settings = {
            project_name: {
                inst_dec.name: instance_time_settings}}
        configuration = {
            rackspace_automation.GLOBAL_SETTINGS:
                global_settings,
            rackspace_automation.INSTANCE_SETTINGS:
                instance_settings}

        instance_time_settings.should_shelve = MagicMock(return_value=False)
        instance_time_settings.should_shelve_warn = MagicMock(
            return_value=True)

        res = rackspace_automation.get_verdict(
            project_name, inst_dec, configuration)

        self.assertEqual(res, rackspace_automation.Verdict.SHELVE_WARN)

    def test_get_verdict_returns_delete(self):
        project_name = 'project_name'
        inst_dec = MagicMock()
        inst_dec.name = 'inst1'
        instance_time_settings = MagicMock()
        global_settings = MagicMock()
        instance_settings = {
            project_name: {
                inst_dec.name: instance_time_settings}}
        configuration = {
            rackspace_automation.GLOBAL_SETTINGS:
                global_settings,
            rackspace_automation.INSTANCE_SETTINGS:
                instance_settings}

        instance_time_settings.should_shelve = MagicMock(return_value=False)
        instance_time_settings.should_shelve_warn = MagicMock(
            return_value=False)
        instance_time_settings.should_delete = MagicMock(return_value=True)

        res = rackspace_automation.get_verdict(
            project_name, inst_dec, configuration)

        self.assertEqual(res, rackspace_automation.Verdict.DELETE)

    def test_get_verdict_returns_delete_warn(self):
        project_name = 'project_name'
        inst_dec = MagicMock()
        inst_dec.name = 'inst1'
        instance_time_settings = MagicMock()
        global_settings = MagicMock()
        instance_settings = {
            project_name: {
                inst_dec.name: instance_time_settings}}
        configuration = {
            rackspace_automation.GLOBAL_SETTINGS:
                global_settings,
            rackspace_automation.INSTANCE_SETTINGS:
                instance_settings}

        instance_time_settings.should_shelve = MagicMock(return_value=False)
        instance_time_settings.should_shelve_warn = MagicMock(
            return_value=False)
        instance_time_settings.should_delete = MagicMock(return_value=False)
        instance_time_settings.should_delete_warn = MagicMock(
            return_value=True)

        res = rackspace_automation.get_verdict(
            project_name, inst_dec, configuration)

        self.assertEqual(res, rackspace_automation.Verdict.DELETE_WARN)

    def test_get_verdict_returns_do_nothing(self):
        project_name = 'project_name'
        inst_dec = MagicMock()
        inst_dec.name = 'inst1'
        instance_time_settings = MagicMock()
        global_settings = MagicMock()
        instance_settings = {
            project_name: {
                inst_dec.name: instance_time_settings}}
        configuration = {
            rackspace_automation.GLOBAL_SETTINGS:
                global_settings,
            rackspace_automation.INSTANCE_SETTINGS:
                instance_settings}

        instance_time_settings.should_shelve = MagicMock(return_value=False)
        instance_time_settings.should_shelve_warn = MagicMock(
            return_value=False)
        instance_time_settings.should_delete = MagicMock(return_value=False)
        instance_time_settings.should_delete_warn = MagicMock(
            return_value=False)

        res = rackspace_automation.get_verdict(
            project_name, inst_dec, configuration)

        self.assertEqual(res, rackspace_automation.Verdict.DO_NOTHING)

    @mock.patch('rackspace_automation.get_verdict')
    @mock.patch('rackspace_automation.InstanceDecorator')
    @mock.patch('rackspace_automation.novaclient')
    @mock.patch('rackspace_automation.get_credentials')
    def test_get_violating_instances(self, mock_get_credentials,
                                     mock_novaclient, mock_inst_dec,
                                     mock_get_verdict):
        project_names = ['p1', 'p2']
        p1_instance_list = ['i1', 'i2']
        p2_instance_list = ['i3', 'i4', 'i5']
        verdicts = {'i1': rackspace_automation.Verdict.SHELVE,
                    'i2': rackspace_automation.Verdict.SHELVE_WARN,
                    'i3': rackspace_automation.Verdict.DELETE,
                    'i4': rackspace_automation.Verdict.DELETE_WARN,
                    'i5': rackspace_automation.Verdict.DO_NOTHING}

        def client(session, **kwargs):
            nova_client = MagicMock()
            if session == 'p1':
                l = p1_instance_list
            else:
                l = p2_instance_list
            nova_client.servers.list = MagicMock(return_value=l)
            return nova_client

        mock_get_credentials.side_effect = lambda x: x
        mock_novaclient.Client = MagicMock(side_effect=client)

        mock_inst_dec.side_effect = lambda inst, nova: inst
        mock_get_verdict.side_effect = lambda x, name, z: verdicts[name]

        expected_res = {'instances_to_shelve': {'p1': ['i1']},
                        'instances_to_delete': {'p2': ['i3']},
                        'shelve_warnings': {'p1': ['i2']},
                        'delete_warnings': {'p2': ['i4']}}
        res = rackspace_automation.get_violating_instances(project_names, None)

        self.assertDictEqual(expected_res, res)

    def test_get_violating_instances_dict_is_empty(self):
        pass

    @mock.patch('rackspace_automation.keystoneclient')
    def test_get_tenant_names(self, mock_keystone):
        p1 = MagicMock()
        p2 = MagicMock()
        p1.name = 'p1'
        p2.name = 'p2'
        project_list = [p1, p2]
        Client = MagicMock()
        Client.return_value = Client
        Client.projects.list = MagicMock(return_value=project_list)
        mock_keystone.Client = Client
        credentials = MagicMock()
        res = rackspace_automation.get_tenant_names(credentials)
        self.assertListEqual(['p1', 'p2'], res)

    def test_get_worksheet_contents(self):
        pass

    @mock.patch('keystoneauth1.session.Session')
    @mock.patch('keystoneauth1.identity.v3.Password')
    def test_get_credentials(self, mock_v3_pw, mock_session):
        """Tests get_credentials.
        """
        self.mock_global_os_env_vars()
        url = self.os_environ['OPENSTACK_URL']
        username = self.os_environ['OPENSTACK_USERNAME']
        password = self.os_environ['OPENSTACK_PASSWORD']
        project = '_project'
        call_params = {
            'auth_url': url,
            'username': username,
            'password': password,
            'user_domain_name': 'Default',
            'project_name': project,
            'project_domain_name': 'Default'}
        auth = 'auth'
        mock_v3_pw.return_value = auth

        rackspace_automation.get_credentials(project)

        mock_v3_pw.assert_called_with(**call_params)
        mock_session.assert_called_with(**{auth: auth})

    def test_get_spreadsheet_creds(self):
        pass

    def test_send_warnings(self):
        pass

    def test_delete_instances(self):
        pass

    def test_shelve(self):
        pass

    def test_add_missing_tenant_email_addresses(self):
        pass

    def test_all_os_vars(self):
        """Tests that all os variables are checked.
        """
        os_environ_dict = {}
        magic_mock = MagicMock()
        magic_mock.mock.dict('os.environ', os_environ_dict)
        self.assertRaises(glb_exc_class,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['SOURCE_EMAIL_ADDRESS'] = 'something'
        self.assertRaises(glb_exc_class,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['CREDENTIALS_FILE_PATH'] = 'something'
        self.assertRaises(glb_exc_class,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['SPREADSHEET_ID'] = 'something'
        self.assertRaises(glb_exc_class,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['SETTINGS_WORKSHEET'] = 'something'
        self.assertRaises(glb_exc_class,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['EMAIL_ADDRESSES_WORKSHEET'] = 'something'
        self.assertRaises(glb_exc_class,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['INSTANCE_SETTINGS_WORKSHEET'] = 'something'
        self.assertRaises(glb_exc_class,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['OPENSTACK_MAIN_PROJECT'] = 'something'
        self.assertRaises(glb_exc_class,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['OPENSTACK_URL'] = 'something'
        self.assertRaises(glb_exc_class,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['OPENSTACK_USERNAME'] = 'something'
        self.assertRaises(glb_exc_class,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['OPENSTACK_PASSWORD'] = 'something'
        self.assertRaises(glb_exc_class,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['DEFAULT_NOTIFICATION_EMAIL_ADDRESS'] = 'something'
        self.assertRaises(glb_exc_class,
                          rackspace_automation.check_os_environ_vars)

    def test_main(self):
        pass
