"""This module provides the RatingsAndReviewsAPI class for talking to the
ratings and reviews API, plus a few helper classes.
"""

from piston_mini_client import (
    PistonAPI,
    returns_json,
    )
from piston_mini_client.validators import validate_pattern
from piston_mini_client.failhandlers import APIError

# These are factored out as constants for if you need to work against a
# server that doesn't support both schemes (like http-only dev servers)
PUBLIC_API_SCHEME = 'http'
AUTHENTICATED_API_SCHEME = 'https'

from .fake_webcatalog_silo import FakeWebCatalogSilo, network_delay
import os
import json

from oneconf.paths import WEBCATALOG_SILO_RESULT, WEBCATALOG_SILO_DIR

class WebCatalogAPI(PistonAPI):
    """A fake client pretending to be WebCatalogAPI from infraclient_pristine.

       Uses settings from fake_webcatalog_settings to provide predictable responses
       to methods that try to use the WebCatalogAPI for testing purposes
       (i.e. without network activity).
       To use this, instead of importing from infraclient_pristine, you can import
       from infraclient_fake instead.
    """

    default_service_root = 'http://localhost:8000/cat/api/1.0'
    default_content_type = 'application/x-www-form-urlencoded'

    _exception_msg = 'Fake WebCatalogAPI raising fake exception'

    def __init__(self, fake_settings_filename = None):
        super(WebCatalogAPI, self).__init__()
        self.silo = FakeWebCatalogSilo(fake_settings_filename)
        self.silo.save_settings(WEBCATALOG_SILO_RESULT)

    def machineuuid_exist(self, machine_uuid):
        '''Generic method to check before doing an update operation that the machine_uuid exist in the host list'''
        return (machine_uuid in self.silo.get_host_silo())

    @returns_json
    @network_delay
    def server_status(self):
        if self.silo.get_setting('server_response_error'):
            raise APIError(self._exception_msg)
        return json.dumps('ok')

    @network_delay
    def list_machines(self):
        if self.silo.get_setting('list_machines_error'):
            raise APIError(self._exception_msg)
        dict_of_hosts = self.silo.get_setting('hosts_metadata')
        # the server is returning a list
        result = []
        for hostid in dict_of_hosts:
            machine = dict_of_hosts[hostid]
            machine['uuid'] = hostid
            result.append(machine)
        return result

    @validate_pattern('machine_uuid', r'[-\w+]+')
    @validate_pattern('hostname', r'[-\w+]+')
    @returns_json
    @network_delay
    def update_machine(self, machine_uuid, hostname):
        if self.silo.get_setting('update_machine_error'):
            raise APIError(self._exception_msg)

        # update our content dictionnary with new data or creating a new entry
        hosts = self.silo.get_host_silo()
        if self.machineuuid_exist(machine_uuid):
            hosts[machine_uuid]['hostname'] = hostname
        else:
            hosts[machine_uuid] = {'hostname': hostname,
                                   'logo_checksum': None,
                                   'packages_checksum': None,
                                   }
        self.silo.save_settings(WEBCATALOG_SILO_RESULT)
        return json.dumps('Success')

    @validate_pattern('machine_uuid', r'[-\w+]+')
    @returns_json
    def delete_machine(self, machine_uuid):
        if self.silo.get_setting('delete_machine_error'):
            raise APIError(self._exception_msg)

        # delete the host if exist from the entry
        hosts = self.silo.get_host_silo()
        packages = self.silo.get_package_silo()
        try:
            del(packages[machine_uuid])
        except KeyError:
            pass # there was no package list
        logo_path = os.path.join(WEBCATALOG_SILO_DIR, "%s.png" % machine_uuid)
        try:
            os.remove(logo_path)
        except OSError:
            pass # there was no logo
        if not self.machineuuid_exist(machine_uuid):
            raise APIError('Host Not Found')
        del hosts[machine_uuid]
        self.silo.save_settings(WEBCATALOG_SILO_RESULT)
        return json.dumps('Success')

    @validate_pattern('machine_uuid', r'[-\w+]+')
    def get_machine_logo(self, machine_uuid):
        if self.silo.get_setting('get_machine_logo_error'):
            raise APIError(self._exception_msg)

        logo_path = os.path.join(WEBCATALOG_SILO_DIR, "%s.png" % machine_uuid)
        if not os.path.exists(logo_path):
            raise APIError("No logo found")
        with open(logo_path) as fp:
            return fp.read()

    @validate_pattern('machine_uuid', r'[-\w+]+')
    @validate_pattern('logo_checksum', r'[-\w+]+\.[-\w+]+')
    @returns_json
    def update_machine_logo(self, machine_uuid, logo_checksum, logo_content):
        if self.silo.get_setting('update_machine_logo_error'):
            raise APIError(self._exception_msg)

        if not self.machineuuid_exist(machine_uuid):
            raise APIError('Host Not Found')
        image_path = os.path.join(WEBCATALOG_SILO_DIR,'%s.png' % machine_uuid)
        with open(image_path, 'wb+') as image_on_disk:
            image_on_disk.write(logo_content)
        hosts = self.silo.get_host_silo()
        hosts[machine_uuid]['logo_checksum'] = logo_checksum
        self.silo.save_settings(WEBCATALOG_SILO_RESULT)
        return json.dumps('Success')

    @validate_pattern('machine_uuid', r'[-\w+]+')
    @returns_json
    def list_packages(self, machine_uuid):
        if self.silo.get_setting('list_packages_error'):
            raise APIError(self._exception_msg)

        packages = self.silo.get_package_silo()
        if machine_uuid not in packages:
            raise APIError('Package list empty')
        package_list = packages[machine_uuid]
        if not package_list:
            raise APIError('Package list empty')
        return json.dumps(package_list)

    @validate_pattern('machine_uuid', r'[-\w+]+')
    @validate_pattern('packages_checksum', r'[-\w+]+')
    @returns_json
    def update_packages(self, machine_uuid, packages_checksum, package_list):
        if self.silo.get_setting('update_packages_error'):
            raise APIError(self._exception_msg)

        if not self.machineuuid_exist(machine_uuid):
            raise APIError('Host Not Found')

        packages = self.silo.get_package_silo()
        packages[machine_uuid] = package_list
        hosts = self.silo.get_host_silo()
        hosts[machine_uuid]['packages_checksum'] = packages_checksum
        self.silo.save_settings(WEBCATALOG_SILO_RESULT)
        return json.dumps('Success')
