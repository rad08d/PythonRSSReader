"""This module provides the WebCatalogAPI class for talking to the
webcatalog API, plus a few helper classes.
"""

import ast
import json
from piston_mini_client import (
    PistonAPI,
    returns_json
    )
from piston_mini_client.validators import (
    oauth_protected,
    validate_pattern,
    )
from piston_mini_client.failhandlers import APIError

# These are factored out as constants for if you need to work against a
# server that doesn't support both schemes (like http-only dev servers)
PUBLIC_API_SCHEME = 'http'
AUTHENTICATED_API_SCHEME = 'https'

class WebCatalogAPI(PistonAPI):
    """A client for talking to the webcatalog API.

    If you pass no arguments into the constructor it will try to connect to
    localhost:8000 so you probably want to at least pass in the
    ``service_root`` constructor argument.
    """
#    default_service_root = 'http://localhost:8000/cat/api/1.0'
    default_service_root = 'https://apps.staging.ubuntu.com/cat/api/1.0'
    default_content_type = 'application/x-www-form-urlencoded'

    @returns_json
    def server_status(self):
        """Check the state of the server, to see if everything's ok."""
        return self._get('server-status/', scheme=PUBLIC_API_SCHEME)

    @oauth_protected
    def list_machines(self):
        """List all machine for the current user."""
        return ast.literal_eval(self._get('list-machines/', scheme=AUTHENTICATED_API_SCHEME))

    @validate_pattern('machine_uuid', r'[-\w+]+')
    @validate_pattern('hostname', r'[-\w+]+')
    @returns_json
    @oauth_protected
    def update_machine(self, machine_uuid, hostname):
        """Register or update an existing machine with new name."""
        # fake logo_checksum for now
        data = {"hostname": hostname, "logo_checksum": "a"}
        return self._post('machine/%s/' % machine_uuid, data=data,
            scheme=AUTHENTICATED_API_SCHEME, content_type='application/json')

    @validate_pattern('machine_uuid', r'[-\w+]+')
    @returns_json
    @oauth_protected
    def delete_machine(self, machine_uuid):
        """Delete an existing machine."""
        return self._delete('machine/%s/' % machine_uuid, scheme=AUTHENTICATED_API_SCHEME)

    @validate_pattern('machine_uuid', r'[-\w+]+')
    @oauth_protected
    def get_machine_logo(self, machine_uuid):
        """get the logo for a machine."""
        return self._get('logo/%s/' % machine_uuid, scheme=AUTHENTICATED_API_SCHEME)

    @validate_pattern('machine_uuid', r'[-\w+]+')
    @validate_pattern('logo_checksum', r'[-\w+]+\.[-\w+]+')
    @returns_json
    @oauth_protected
    def update_machine_logo(self, machine_uuid, logo_checksum, logo_content):
        """update the logo for a machine."""
        return self._post('logo/%s/%s/' % (machine_uuid, logo_checksum), data=logo_content,
        content_type='image/png', scheme=AUTHENTICATED_API_SCHEME)

    @validate_pattern('machine_uuid', r'[-\w+]+')
    @returns_json
    @oauth_protected
    def list_packages(self, machine_uuid):
        """List all packages for that machine"""
        package_list = self._get('packages/%s/' % machine_uuid, scheme=AUTHENTICATED_API_SCHEME)
        if not package_list:
            raise APIError('Package list empty')
        # FIXME: need to do this hack to transform the http request to a json format content
        try:
            package_list = json.loads(package_list[1:-1].replace("'", '"').replace("True", "true").replace("False", 'false'))
        except ValueError as e:
            raise APIError('Package list invalid: %s' % e)
        return package_list

    @validate_pattern('machine_uuid', r'[-\w+]+')
    @validate_pattern('packages_checksum', r'[-\w+]+')
    @returns_json
    @oauth_protected
    def update_packages(self, machine_uuid, packages_checksum, package_list):
        """update the package list for a machine."""

        data_content = {"package_list": package_list, "packages_checksum": packages_checksum}
        return self._post('packages/%s/' % machine_uuid, data=data_content, content_type='application/json', scheme=AUTHENTICATED_API_SCHEME)
