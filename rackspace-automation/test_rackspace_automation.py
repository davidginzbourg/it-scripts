import datetime as dt
import unittest

import mock
import numpy as np
import rackspace_automation
from mock import MagicMock
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
    def __init__(self, action, start_time=None):
        self._action = action
        self._start_time = start_time if start_time else \
            TestInstanceDecorator.fixed_test_date

    @property
    def action(self):
        return self._action

    @property
    def start_time(self):
        return self._start_time


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
        self.assertFalse(is_above_threshold(time, float('inf')))

        time = dt.datetime(now_year, now_month, now_day).isoformat()
        self.assertFalse(is_above_threshold(time, 0))

        self.assertFalse(is_above_threshold(None, 10))

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

    def test_get_shelve_running_warning_days(self):
        tts = rackspace_automation.TimeThresholdSettings(*[2, 3, 2, 3, 2, 3])
        tts.shelve_running_warning_threshold = 86401  # a little more than 1 day
        self.assertEqual(tts.get_shelve_running_warning_days(), '1.0')

    def test_get_shelve_stopped_warning_days(self):
        tts = rackspace_automation.TimeThresholdSettings(*[2, 3, 2, 3, 2, 3])
        tts.shelve_stopped_warning_threshold = 86401  # a little more than 1 day
        self.assertEqual(tts.get_shelve_stopped_warning_days(), '1.0')

    def test_get_delete_warning_days(self):
        tts = rackspace_automation.TimeThresholdSettings(*[2, 3, 2, 3, 2, 3])
        tts.delete_warning_threshold = 86401  # a little more than 1 day
        self.assertEqual(tts.get_delete_warning_days(), '1.0')

    def test_get_shelve_running_days(self):
        tts = rackspace_automation.TimeThresholdSettings(*[2, 3, 2, 3, 2, 3])
        tts.shelve_running_threshold = 86401  # a little more than 1 day
        self.assertEqual(tts.get_shelve_running_days(), '1.0')

    def test_get_shelve_stopped_days(self):
        tts = rackspace_automation.TimeThresholdSettings(*[2, 3, 2, 3, 2, 3])
        tts.shelve_stopped_threshold = 86401  # a little more than 1 day
        self.assertEqual(tts.get_shelve_stopped_days(), '1.0')

    def test_get_delete_shelved_days(self):
        tts = rackspace_automation.TimeThresholdSettings(*[2, 3, 2, 3, 2, 3])
        tts.delete_shelved_threshold = 86401  # a little more than 1 day
        self.assertEqual(tts.get_delete_shelved_days(), '1.0')


class TestInstanceDecorator(unittest.TestCase):
    max_datetime = str(dt.datetime.max)
    fixed_test_date = dt.datetime(1990, 1, 1).isoformat()

    def test_id(self):
        instance = MagicMock()
        instance.id = 'id'
        inst_dec = InstanceDecorator(instance, MockInstDecNova([]))
        id = inst_dec.id

        self.assertEqual(id, 'id')

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

        target_date = dt.datetime(1995, 1, 1).isoformat()

        # Create transitions the instance into a running state.
        actions_log = [
            MockAction('os-start', target_date),
            MockAction('os-stop', dt.datetime(1992, 1, 1).isoformat()),
            MockAction('os-start', dt.datetime(1993, 1, 1).isoformat()),
            MockAction('os-stop', dt.datetime(1994, 1, 1).isoformat()),
            MockAction('create', dt.datetime(1991, 1, 1).isoformat())
        ]

        inst_dec = InstanceDecorator(instance, MockInstDecNova(actions_log))
        self.assertEqual(inst_dec.running_since(), target_date)

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

        target_date = dt.datetime(1994, 1, 1).isoformat()

        # Create transitions the instance into a running state.
        actions_log = [
            MockAction('os-stop', target_date),
            MockAction('os-start', dt.datetime(1995, 1, 1).isoformat()),
            MockAction('os-stop', dt.datetime(1992, 1, 1).isoformat()),
            MockAction('os-start', dt.datetime(1993, 1, 1).isoformat()),
            MockAction('create', dt.datetime(1991, 1, 1).isoformat())
        ]

        inst_dec = InstanceDecorator(instance, MockInstDecNova(actions_log))
        self.assertEqual(inst_dec.stopped_since(), target_date)

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

        target_date = dt.datetime(1994, 1, 1).isoformat()

        # Create transitions the instance into a running state.
        actions_log = [
            MockAction('pause', dt.datetime(1993, 1, 1).isoformat()),
            MockAction('shelve', dt.datetime(1992, 1, 1).isoformat()),
            MockAction('pause', dt.datetime(1995, 1, 1).isoformat()),
            MockAction('shelve', target_date),
            MockAction('create', dt.datetime(1991, 1, 1).isoformat())
        ]

        inst_dec = InstanceDecorator(instance, MockInstDecNova(actions_log))
        self.assertEqual(inst_dec.shelved_since(), target_date)

    def test_delete_dry_run(self):
        rackspace_automation.DRY_RUN = True
        instance = MagicMock()
        instance.delete = MagicMock()

        inst_dec = InstanceDecorator(instance, MagicMock())

        res = inst_dec.delete()
        instance.delete.assert_not_called()
        self.assertTrue(res)
        self.assertTrue(inst_dec.get_last_action_result())

    def test_delete(self):
        rackspace_automation.DRY_RUN = False
        instance = MagicMock()
        instance.delete = MagicMock(return_value=[
            InstanceDecorator._delete_succ_code])

        inst_dec = InstanceDecorator(instance, MagicMock())

        res = inst_dec.delete()
        instance.delete.assert_called()
        self.assertTrue(res)
        self.assertTrue(inst_dec.get_last_action_result())

    def test_delete_failed(self):
        rackspace_automation.DRY_RUN = False
        instance = MagicMock()
        instance.delete = MagicMock(return_value=[-1])

        inst_dec = InstanceDecorator(instance, MagicMock())

        res = inst_dec.delete()
        instance.delete.assert_called()
        self.assertFalse(res)
        self.assertFalse(inst_dec.get_last_action_result())

    def test_shelve_dry_run(self):
        rackspace_automation.DRY_RUN = True
        instance = MagicMock()
        instance.shelve = MagicMock()

        inst_dec = InstanceDecorator(instance, MagicMock())

        res = inst_dec.shelve()
        instance.shelve.assert_not_called()
        self.assertTrue(res)

    def test_shelve(self):
        rackspace_automation.DRY_RUN = False
        instance = MagicMock()
        instance.shelve = MagicMock(return_value=[
            InstanceDecorator._shelve_succ_code])

        inst_dec = InstanceDecorator(instance, MagicMock())

        res = inst_dec.shelve()
        instance.shelve.assert_called()
        self.assertTrue(res)
        self.assertTrue(inst_dec.get_last_action_result())

    def test_shelve_failed(self):
        rackspace_automation.DRY_RUN = False
        instance = MagicMock()
        instance.shelve = MagicMock(return_value=[-1])

        inst_dec = InstanceDecorator(instance, MagicMock())

        res = inst_dec.shelve()
        instance.shelve.assert_called()
        self.assertFalse(res)
        self.assertFalse(inst_dec.get_last_action_result())

    def test_get_status_returns_running(self):
        instance = MagicMock()

        setattr(instance, 'OS-EXT-STS:vm_state', 'active')
        inst_dec = InstanceDecorator(instance, MagicMock())

        self.assertEqual(inst_dec.get_status(), 'running')

    def test_get_status_returns_stopped(self):
        instance = MagicMock()

        setattr(instance, 'OS-EXT-STS:vm_state', 'stopped')
        inst_dec = InstanceDecorator(instance, MagicMock())

        self.assertEqual(inst_dec.get_status(), 'stopped')

    def test_get_status_returns_shelved(self):
        instance = MagicMock()

        setattr(instance, 'OS-EXT-STS:vm_state', 'shelved_offloaded')
        inst_dec = InstanceDecorator(instance, MagicMock())

        self.assertEqual(inst_dec.get_status(), 'shelved')

    def test_get_status_returns_unknown(self):
        instance = MagicMock()

        setattr(instance, 'OS-EXT-STS:vm_state', 'say_what?')
        inst_dec = InstanceDecorator(instance, MagicMock())

        self.assertEqual(inst_dec.get_status(), 'unknown')

    def test_is_running_true(self):
        instance = MagicMock()

        setattr(instance, 'OS-EXT-STS:vm_state', 'active')
        inst_dec = InstanceDecorator(instance, MagicMock())

        self.assertTrue(inst_dec.is_running)

    def test_is_running_false(self):
        instance = MagicMock()

        setattr(instance, 'OS-EXT-STS:vm_state', 'stopped')
        inst_dec = InstanceDecorator(instance, MagicMock())

        self.assertFalse(inst_dec.is_running)

    def test_is_stopped_true(self):
        instance = MagicMock()

        setattr(instance, 'OS-EXT-STS:vm_state', 'stopped')
        inst_dec = InstanceDecorator(instance, MagicMock())

        self.assertTrue(inst_dec.is_stopped)

    def test_is_stopped_false(self):
        instance = MagicMock()

        setattr(instance, 'OS-EXT-STS:vm_state', 'active')
        inst_dec = InstanceDecorator(instance, MagicMock())

        self.assertFalse(inst_dec.is_stopped)

    def test_is_shelved_true(self):
        instance = MagicMock()

        setattr(instance, 'OS-EXT-STS:vm_state', 'shelved_offloaded')
        inst_dec = InstanceDecorator(instance, MagicMock())

        self.assertTrue(inst_dec.is_shelved)

    def test_is_shelved_false(self):
        instance = MagicMock()

        setattr(instance, 'OS-EXT-STS:vm_state', 'active')
        inst_dec = InstanceDecorator(instance, MagicMock())

        self.assertFalse(inst_dec.is_shelved)


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
        inst_set1 = {rackspace_automation.INSTANCE_ID: inst1,
                     'shelve_running_warning_threshold':
                         '',
                     'shelve_stopped_warning_threshold':
                         1.0,
                     'delete_warning_threshold': 2.0,
                     'shelve_running_threshold': '',
                     'shelve_stopped_threshold': 4.0,
                     'delete_shelved_threshold': 5.0}
        inst2 = 'inst2'
        inst_set2 = {rackspace_automation.INSTANCE_ID: inst2,
                     'shelve_running_warning_threshold':
                         10.0,
                     'shelve_stopped_warning_threshold':
                         11.0,
                     'delete_warning_threshold': 12.0,
                     'shelve_running_threshold': 13.0,
                     'shelve_stopped_threshold': 14.0,
                     'delete_shelved_threshold': 15.0}
        inst3 = 'inst3'
        inst_set3 = {rackspace_automation.INSTANCE_ID: inst3,
                     'shelve_running_warning_threshold':
                         110.0,
                     'shelve_stopped_warning_threshold':
                         111.0,
                     'delete_warning_threshold': 112.0,
                     'shelve_running_threshold': 113.0,
                     'shelve_stopped_threshold': 114.0,
                     'delete_shelved_threshold': 115.0}
        row1 = inst_set1
        row2 = inst_set2
        row3 = inst_set3
        contents.extend([row1, row2, row3])

        result = rackspace_automation.fetch_instance_settings(None)

        # This must be done in order to successfully do the double
        # 'dereference'
        for inst in [inst_set1, inst_set2, inst_set3]:
            del inst[rackspace_automation.INSTANCE_ID]

        inst_set1['shelve_running_warning_threshold'] = float('inf')
        inst_set1['shelve_running_threshold'] = float('inf')
        correct_result = {
            inst1: rackspace_automation.TimeThresholdSettings(**inst_set1),
            inst3: rackspace_automation.TimeThresholdSettings(**inst_set3),
            inst2: rackspace_automation.TimeThresholdSettings(**inst_set2)
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
        inst_dec = MagicMock()
        inst_dec.id = 999
        global_settings = MagicMock()
        instance_settings = {}
        configuration = {
            rackspace_automation.GLOBAL_SETTINGS:
                global_settings,
            rackspace_automation.INSTANCE_SETTINGS:
                instance_settings}

        global_settings.should_shelve = MagicMock(return_value=True)

        rackspace_automation.get_verdict(inst_dec, configuration)
        global_settings.should_shelve.assert_any_call(inst_dec)

    def test_get_verdict_configuration_swap(self):
        inst_dec = MagicMock()
        inst_dec.id = 'inst1'
        instance_time_settings = MagicMock()
        global_settings = MagicMock()
        instance_settings = {inst_dec.id: instance_time_settings}
        configuration = {
            rackspace_automation.GLOBAL_SETTINGS:
                global_settings,
            rackspace_automation.INSTANCE_SETTINGS:
                instance_settings}

        instance_time_settings.should_shelve = MagicMock(return_value=True)

        rackspace_automation.get_verdict(inst_dec, configuration)
        instance_time_settings.should_shelve.assert_any_call(inst_dec)

    def test_get_verdict_shelves(self):
        inst_dec = MagicMock()
        inst_dec.id = 'inst1'
        instance_time_settings = MagicMock()
        global_settings = MagicMock()
        instance_settings = {inst_dec.id: instance_time_settings}
        configuration = {
            rackspace_automation.GLOBAL_SETTINGS:
                global_settings,
            rackspace_automation.INSTANCE_SETTINGS:
                instance_settings}

        instance_time_settings.should_shelve = MagicMock(return_value=True)

        res = rackspace_automation.get_verdict(inst_dec, configuration)

        self.assertEqual(res, rackspace_automation.Verdict.SHELVE)

    def test_get_verdict_returns_shelves_warn(self):
        inst_dec = MagicMock()
        inst_dec.id = 'inst1'
        instance_time_settings = MagicMock()
        global_settings = MagicMock()
        instance_settings = {inst_dec.id: instance_time_settings}
        configuration = {
            rackspace_automation.GLOBAL_SETTINGS:
                global_settings,
            rackspace_automation.INSTANCE_SETTINGS:
                instance_settings}

        instance_time_settings.should_shelve = MagicMock(return_value=False)
        instance_time_settings.should_shelve_warn = MagicMock(
            return_value=True)

        res = rackspace_automation.get_verdict(inst_dec, configuration)

        self.assertEqual(res, rackspace_automation.Verdict.SHELVE_WARN)

    def test_get_verdict_returns_delete(self):
        inst_dec = MagicMock()
        inst_dec.id = 'inst1'
        instance_time_settings = MagicMock()
        global_settings = MagicMock()
        instance_settings = {inst_dec.id: instance_time_settings}
        configuration = {
            rackspace_automation.GLOBAL_SETTINGS:
                global_settings,
            rackspace_automation.INSTANCE_SETTINGS:
                instance_settings}

        instance_time_settings.should_shelve = MagicMock(return_value=False)
        instance_time_settings.should_shelve_warn = MagicMock(
            return_value=False)
        instance_time_settings.should_delete = MagicMock(return_value=True)

        res = rackspace_automation.get_verdict(inst_dec, configuration)

        self.assertEqual(res, rackspace_automation.Verdict.DELETE)

    def test_get_verdict_returns_delete_warn(self):
        inst_dec = MagicMock()
        inst_dec.id = 'inst1'
        instance_time_settings = MagicMock()
        global_settings = MagicMock()
        instance_settings = {inst_dec.id: instance_time_settings}
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

        res = rackspace_automation.get_verdict(inst_dec, configuration)

        self.assertEqual(res, rackspace_automation.Verdict.DELETE_WARN)

    def test_get_verdict_returns_do_nothing(self):
        inst_dec = MagicMock()
        inst_dec.id = 'inst1'
        instance_time_settings = MagicMock()
        global_settings = MagicMock()
        instance_settings = {inst_dec.id: instance_time_settings}
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

        res = rackspace_automation.get_verdict(inst_dec, configuration)

        self.assertEqual(res, rackspace_automation.Verdict.DO_NOTHING)

    @mock.patch('rackspace_automation.get_verdict')
    @mock.patch('rackspace_automation.InstanceDecorator')
    @mock.patch('rackspace_automation.novaclient')
    @mock.patch('rackspace_automation.get_credentials')
    def test_get_violating_instances(self, mock_get_credentials,
                                     mock_novaclient, mock_inst_dec,
                                     mock_get_verdict):
        project_names = ['p1', 'p2']
        i1 = MagicMock()
        i2 = MagicMock()
        i3 = MagicMock()
        i4 = MagicMock()
        i5 = MagicMock()
        p1_instance_list = [i1, i2]
        p2_instance_list = [i3, i4, i5]
        verdicts = {i1: rackspace_automation.Verdict.SHELVE,
                    i2: rackspace_automation.Verdict.SHELVE_WARN,
                    i3: rackspace_automation.Verdict.DELETE,
                    i4: rackspace_automation.Verdict.DELETE_WARN,
                    i5: rackspace_automation.Verdict.DO_NOTHING}

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
        mock_get_verdict.side_effect = lambda name, z: verdicts[name]

        expected_res = {'instances_to_shelve': {'p1': [i1]},
                        'instances_to_delete': {'p2': [i3]},
                        'shelve_warnings': {'p1': [i2]},
                        'delete_warnings': {'p2': [i4]}}
        res = rackspace_automation.get_violating_instances(project_names, None)

        self.assertDictEqual(expected_res, res)

    @mock.patch('rackspace_automation.get_verdict')
    @mock.patch('rackspace_automation.InstanceDecorator')
    @mock.patch('rackspace_automation.novaclient')
    @mock.patch('rackspace_automation.get_credentials')
    def test_get_violating_instances_dict_is_empty(self,
                                                   mock_get_credentials,
                                                   mock_novaclient,
                                                   mock_inst_dec,
                                                   mock_get_verdict):
        project_names = ['p1', 'p2']
        i1 = MagicMock()
        i2 = MagicMock()
        i3 = MagicMock()
        i4 = MagicMock()
        i5 = MagicMock()
        p1_instance_list = [i1, i2]
        p2_instance_list = [i3, i4, i5]
        verdicts = {i1: rackspace_automation.Verdict.DO_NOTHING,
                    i2: rackspace_automation.Verdict.DO_NOTHING,
                    i3: rackspace_automation.Verdict.DO_NOTHING,
                    i4: rackspace_automation.Verdict.DO_NOTHING,
                    i5: rackspace_automation.Verdict.DO_NOTHING}

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
        mock_get_verdict.side_effect = lambda name, z: verdicts[name]

        expected_res = {'instances_to_shelve': {},
                        'instances_to_delete': {},
                        'shelve_warnings': {},
                        'delete_warnings': {}}
        res = rackspace_automation.get_violating_instances(project_names, None)

        self.assertDictEqual(expected_res, res)

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

    # @mock.patch('rackspace_automation.get_ses_client')
    # def test_send_email(self, mock_get_ses):
    #     mock_ses = MagicMock()
    #     mock_get_ses.return_value = mock_ses
    #     mock_ses.send_email = MagicMock()
    #
    #     rackspace_automation.SOURCE_EMAIL_ADDRESS = 'source_email'
    #     items_dict = {'tenant1': ['i1']}
    #     configuration = {rackspace_automation.EMAIL_ADDRESSES:
    #                          {'tenant1': 'destination'}}
    #     rackspace_automation.send_email(configuration, items_dict, 'subject',
    #                                     'message')
    #
    #     mock_ses.send_email.assert_called_with(
    #         Source='source_email',
    #         Destination={'ToAddresses': ['destination']},
    #         Message={
    #             'Subject': {
    #                 'Data': 'subject'},
    #             'Body': {
    #                 'Html': {
    #                     'Data': 'message'}}
    #         })
    #
    # @mock.patch('rackspace_automation.send_email')
    # def test_send_warnings(self, mock_send_email):
    #     configuration = 'conf'
    #     shelve_warnings = 'shelve_warnings'
    #     delete_warnings = 'delete_warnings'
    #     rackspace_automation.send_warnings(configuration, shelve_warnings,
    #                                        delete_warnings)
    #
    #     mock_send_email.assert_any_call(
    #         configuration, shelve_warnings,
    #         rackspace_automation.SHELVE_WARNING_SUBJ,
    #         rackspace_automation.SHELVE_WARNING_MSG)
    #
    #     mock_send_email.assert_any_call(
    #         configuration, delete_warnings,
    #         rackspace_automation.DELETE_WARNING_SUBJ,
    #         rackspace_automation.DELETE_WARNING_MSG)
    #
    # @mock.patch('rackspace_automation.send_email')
    # def test_delete_instances(self, mock_send_email):
    #     configuration = 'conf'
    #     inst1 = MagicMock()
    #     inst2 = MagicMock()
    #     inst1.delete = MagicMock()
    #     inst2.delete = MagicMock()
    #     instances_to_delete = {
    #         'tenant1': [inst1, inst2]
    #     }
    #
    #     rackspace_automation.delete_instances(configuration,
    #                                           instances_to_delete)
    #
    #     inst1.delete.assert_called()
    #     inst2.delete.assert_called()
    #
    #     mock_send_email.assert_any_call(
    #         configuration, instances_to_delete,
    #         rackspace_automation.DELETE_NOTIF_SUBJ,
    #         rackspace_automation.DELETE_NOTIF_MSG)
    #
    # @mock.patch('rackspace_automation.send_email')
    # def test_shelve_instances(self, mock_send_email):
    #     configuration = 'conf'
    #     inst1 = MagicMock()
    #     inst2 = MagicMock()
    #     inst1.shelve = MagicMock()
    #     inst2.shelve = MagicMock()
    #     instances_to_shelve = {
    #         'tenant1': [inst1, inst2]
    #     }
    #
    #     rackspace_automation.shelve_instances(configuration,
    #                                           instances_to_shelve)
    #
    #     inst1.shelve.assert_called()
    #     inst2.shelve.assert_called()
    #
    #     mock_send_email.assert_any_call(
    #         configuration, instances_to_shelve,
    #         rackspace_automation.SHELVE_NOTIF_SUBJ,
    #         rackspace_automation.SHELVE_NOTIF_MSG)

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

    def test_get_action_message_shelve_running(self):
        inst_dec = MagicMock(is_running=True, is_stopped=False)
        inst_dec.get_status = MagicMock(return_value='running')
        verdict = rackspace_automation.Verdict.SHELVE
        threshold_settings = MagicMock()
        threshold_settings.get_shelve_running_days = MagicMock(return_value=7)

        expected_res = rackspace_automation.h_formats.action_msg_fmt.format(
            'running', 7)
        self.assertEqual(
            rackspace_automation.get_action_message(inst_dec, verdict,
                                                    threshold_settings),
            expected_res)

    def test_get_action_message_shelve_stopped(self):
        inst_dec = MagicMock(is_running=False, is_stopped=True)
        inst_dec.get_status = MagicMock(return_value='stopped')
        verdict = rackspace_automation.Verdict.SHELVE
        threshold_settings = MagicMock()
        threshold_settings.get_shelve_stopped_days = MagicMock(return_value=7)

        expected_res = rackspace_automation.h_formats.action_msg_fmt.format(
            'stopped', 7)
        self.assertEqual(
            rackspace_automation.get_action_message(inst_dec, verdict,
                                                    threshold_settings),
            expected_res)

    @mock.patch('rackspace_automation.get_utc_now')
    def test_get_action_message_shelve_warn_running(self, mock_utc_now):
        mock_utc_now.return_value = dt.datetime(1990, 1, 3)

        inst_dec = MagicMock(is_running=True, is_stopped=False)
        inst_dec.get_status = MagicMock(return_value='running')
        inst_dec.running_since = MagicMock(
            return_value=dt.datetime(1990, 1, 1).isoformat())

        verdict = rackspace_automation.Verdict.SHELVE_WARN
        threshold_settings = MagicMock()
        threshold_settings.shelve_running_threshold = 5 * 24 * 60 * 60
        threshold_settings.get_shelve_running_warning_days = MagicMock(
            return_value=5)

        expected_res = rackspace_automation.h_formats.shlv_wrn_msg_fmt.format(
            '3', 'running', 5)
        self.assertEqual(
            rackspace_automation.get_action_message(inst_dec, verdict,
                                                    threshold_settings),
            expected_res)

    @mock.patch('rackspace_automation.get_utc_now')
    def test_get_action_message_shelve_warn_stopped(self, mock_utc_now):
        mock_utc_now.return_value = dt.datetime(1990, 1, 3)

        inst_dec = MagicMock(is_running=False, is_stopped=True)
        inst_dec.get_status = MagicMock(return_value='stopped')
        inst_dec.stopped_since = MagicMock(
            return_value=dt.datetime(1990, 1, 1).isoformat())

        verdict = rackspace_automation.Verdict.SHELVE_WARN
        threshold_settings = MagicMock()
        threshold_settings.shelve_stopped_threshold = 5 * 24 * 60 * 60
        threshold_settings.get_shelve_stopped_warning_days = MagicMock(
            return_value=5)

        expected_res = rackspace_automation.h_formats.shlv_wrn_msg_fmt.format(
            '3', 'stopped', 5)
        self.assertEqual(
            rackspace_automation.get_action_message(inst_dec, verdict,
                                                    threshold_settings),
            expected_res)

    def test_get_action_message_delete(self):
        inst_dec = MagicMock()
        inst_dec.get_status = MagicMock(return_value='shelved')
        verdict = rackspace_automation.Verdict.DELETE
        threshold_settings = MagicMock()
        threshold_settings.get_delete_shelved_days = MagicMock(return_value=7)

        expected_res = rackspace_automation.h_formats.action_msg_fmt.format(
            'shelved', 7)
        self.assertEqual(
            rackspace_automation.get_action_message(inst_dec, verdict,
                                                    threshold_settings),
            expected_res)

    @mock.patch('rackspace_automation.get_utc_now')
    def test_get_action_message_delete_warn(self, mock_utc_now):
        mock_utc_now.return_value = dt.datetime(1990, 1, 3)

        inst_dec = MagicMock()
        inst_dec.get_status = MagicMock(return_value='shelved')
        inst_dec.shelved_since = MagicMock(
            return_value=dt.datetime(1990, 1, 1).isoformat())

        verdict = rackspace_automation.Verdict.DELETE_WARN
        threshold_settings = MagicMock()
        threshold_settings.delete_warning_threshold = 5 * 24 * 60 * 60
        threshold_settings.get_delete_warning_days = MagicMock(
            return_value=5)

        expected_res = rackspace_automation.h_formats.del_wrn_msg_fmt.format(
            '3', 'shelved', 5)
        self.assertEqual(
            rackspace_automation.get_action_message(inst_dec, verdict,
                                                    threshold_settings),
            expected_res)

    def test_get_action_message_empty(self):
        verdict = rackspace_automation.Verdict.DO_NOTHING

        self.assertEqual(rackspace_automation.get_action_message(
            MagicMock(), verdict, MagicMock()), '')

    @mock.patch('rackspace_automation.get_utc_now')
    def test_get_days_remaining(self, mock_utc_now):
        mock_utc_now.return_value = dt.datetime(1990, 1, 3)
        some_date = dt.datetime(1990, 1, 1).isoformat()
        threshold = 5 * 24 * 60 * 60

        self.assertEqual(
            rackspace_automation.get_days_remaining(some_date, threshold), '3')
