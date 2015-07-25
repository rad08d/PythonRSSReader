import time
import logging
import os
import pickle


LOG = logging.getLogger(__name__)

# decorator to add a fake network delay if set
# in FakeReviewSettings.fake_network_delay
def network_delay(fn):
    def slp(self, *args, **kwargs):
        #FIXME: CHECK how a decorator can take parameters
        #delay = fake_settings.get_setting('fake_network_delay')
        delay = 2
        if delay:
            time.sleep(delay)
        return fn(self, *args, **kwargs)
    return slp


class FakeWebCatalogSilo(object):

    """An object that simply holds settings and data which are used by
    WebCatalogAPI in the infraclient_fake module. Using this module allows a
    developer to test the oneconf functionality without any interaction with a
    webcatalog server.  Each setting here provides complete control over how
    the 'server' will respond. Changes to these settings should be made to the
    class attributes directly without creating an instance of this class.  The
    intended usage is for unit tests where a predictable response is required
    and where the application should THINK it has spoken to a server.

    The unit test would make changes to settings in this class before running
    the unit test.

    It also contains some data for integration test, faking a in memory
    WebCatalog server.
    """

    _FAKE_SETTINGS = {}

    # Default stored data
    #_FAKE_SETTINGS['hosts_metadata'] = {
    #    'AAAAA': {'hostname': 'aaaaa', 'logo_checksum': 'logoAAAAA', 'packages_checksum': 'packageAAAAAA'},
    #    'BBBBB': {'hostname': 'bbbbb', 'logo_checksum': 'logoBBBBB', 'packages_checksum': 'packageBBBBBB'},}
    #_FAKE_SETTINGS['packages_metadata'] = {
    #    'AAAAA': {'kiki': {'auto': False}, 'unity': {'auto': False},
    #              'libFoo': {'auto': True}, 'libFool': {'auto': True}},
    #    'BBBBB': {'kiki': {'auto': False}, 'gnome-panel': {'auto': False},
    #              'libBar': {'auto': True}, 'libFool': {'auto': False}},}
    _FAKE_SETTINGS['hosts_metadata'] = {}
    _FAKE_SETTINGS['packages_metadata'] = {}

    # general settings
    # *****************************
    # delay (in seconds) before returning from any of the fake cat methods
    # useful for emulating real network timings (use None for no delays)
    _FAKE_SETTINGS['fake_network_delay'] = 2

    # server status
    # *****************************
    # can be env variables as well like: ONECONF_server_response_error
    # raises APIError if True
    _FAKE_SETTINGS['server_response_error'] = False

    # list machines
    # *****************************
    # raises APIError if True
    _FAKE_SETTINGS['list_machines_error'] = False

    # update machine
    # *****************************
    # raises APIError if True
    _FAKE_SETTINGS['update_machine_error'] = False

    # delete machine
    # *****************************
    # raises APIError if True
    _FAKE_SETTINGS['delete_machine_error'] = False

    # get machine logo
    # *****************************
    # raises APIError if True
    _FAKE_SETTINGS['get_machine_logo_error'] = False

    # update machine logo
    # *****************************
    # raises APIError if True
    _FAKE_SETTINGS['update_machine_logo_error'] = False

    # list packages
    # *****************************
    # raises APIError if True
    _FAKE_SETTINGS['list_packages_error'] = False

    # update package list
    # *****************************
    # raises APIError if True
    _FAKE_SETTINGS['update_packages_error'] = False


    def __init__(self, silo_filepath=None):
        """Initialises the object and loads the settings into the
        _FAKE_SETTINGS dict.. If settings_file is not provided, any existing
        settings in the cache file are ignored and the cache file is
        overwritten with the defaults set in the class.
        """

        if silo_filepath:
            self._update_from_file(silo_filepath)

    def get_setting(self, key_name):
        """Takes a string (key_name) which corresponds to a setting in this
        object.

        Raises a NameError if the setting name doesn't exist
        """
        if 'error' in key_name:
            value = os.getenv('ONECONF_' + key_name)
            # The value should be the string True or False, but it can be None.
            if value is not None:
                if value.lower() == 'true':
                    return True
                elif value.lower() == 'false':
                    return False
                else:
                    raise RuntimeError('unexpected value %s' % value)
        if not key_name in self._FAKE_SETTINGS:
            raise NameError('Setting %s does not exist' % key_name)
        return self._FAKE_SETTINGS[key_name]

    def get_host_silo(self):
        """ return a reference to the host list silo"""
        return self._FAKE_SETTINGS['hosts_metadata']

    def get_package_silo(self):
        """ return a reference to the package list silo"""
        return self._FAKE_SETTINGS['packages_metadata']

    def _update_from_file(self, filepath):
        '''Loads existing settings from cache file into _FAKE_SETTINGS dict'''
        if os.path.exists(filepath):
            with open(filepath, 'rb') as fp:
                self._FAKE_SETTINGS = pickle.load(fp)
        else:
            LOG.warning("Settings file %s doesn't exist. "
                        'Will run with the default' % filepath)
        return

    def save_settings(self, filepath):
        """write the dict out to cache file, for generating new cases"""
        try:
            if not os.path.exists(os.path.dirname(filepath)):
                os.makedirs(os.path.dirname(filepath))
            # File must be open in binary mode since pickle will write bytes.
            with open(filepath, 'wb') as fp:
                pickle.dump(self._FAKE_SETTINGS, fp)
            return True
        except:
            return False
