import unittest
import mock
from mock import MagicMock
import rackspace_automation

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

class OsEnvVarsTest(unittest.TestCase):
    """Tests os environment variables check.
    """

    def test_all_os_vars(self):
        """Tests that all os variables are checked.
        """
        os_environ_dict = {}
        magic_mock = MagicMock()
        magic_mock.mock.dict('os.environ', os_environ_dict)
        self.assertRaises(rackspace_automation.RackspaceAutomationException,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['SOURCE_EMAIL_ADDRESS'] = 'something'
        self.assertRaises(rackspace_automation.RackspaceAutomationException,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['CREDENTIALS_FILE_PATH'] = 'something'
        self.assertRaises(rackspace_automation.RackspaceAutomationException,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['SPREADSHEET_ID'] = 'something'
        self.assertRaises(rackspace_automation.RackspaceAutomationException,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['SETTINGS_WORKSHEET'] = 'something'
        self.assertRaises(rackspace_automation.RackspaceAutomationException,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['EMAIL_ADDRESSES_WORKSHEET'] = 'something'
        self.assertRaises(rackspace_automation.RackspaceAutomationException,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['INSTANCE_SETTINGS_WORKSHEET'] = 'something'
        self.assertRaises(rackspace_automation.RackspaceAutomationException,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['OPENSTACK_MAIN_PROJECT'] = 'something'
        self.assertRaises(rackspace_automation.RackspaceAutomationException,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['OPENSTACK_URL'] = 'something'
        self.assertRaises(rackspace_automation.RackspaceAutomationException,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['OPENSTACK_USERNAME'] = 'something'
        self.assertRaises(rackspace_automation.RackspaceAutomationException,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['OPENSTACK_PASSWORD'] = 'something'
        self.assertRaises(rackspace_automation.RackspaceAutomationException,
                          rackspace_automation.check_os_environ_vars)
        os_environ_dict['DEFAULT_NOTIFICATION_EMAIL_ADDRESS'] = 'something'
        self.assertRaises(rackspace_automation.RackspaceAutomationException,
                          rackspace_automation.check_os_environ_vars)


class FetchConfigurationsTests(unittest.TestCase):
    """Fetch configurations test cases.
    """
    os_environ = {
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

    @mock.patch('os.environ', os_environ)
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
