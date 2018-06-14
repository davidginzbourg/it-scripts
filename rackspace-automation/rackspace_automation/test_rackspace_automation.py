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
'''

glb_exc_class = rackspace_automation.RackspaceAutomationException


class OsEnvVarsTest(unittest.TestCase):
    """Tests os environment variables check.
    """

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
