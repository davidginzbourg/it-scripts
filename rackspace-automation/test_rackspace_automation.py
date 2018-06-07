import unittest
from mock import MagicMock
import rackspace_automation


class OsEnvVarsTest(unittest.TestCase):
    """Tests os environment variables check.
    """

    def test_all_os_vars(self):
        """Tests that all os variables are checked.
        """
        SCOPES = ['https://spreadsheets.google.com/feeds']
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
