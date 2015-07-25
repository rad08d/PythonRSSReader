# -*- coding: utf-8 -*-

# Copyright (C) 2011 Canonical
#
# Authors:
#  Didier Roche
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

from gi.repository import GObject, GLib
import json
import logging
import os
import time

from oneconf.enums import MIN_TIME_WITHOUT_ACTIVITY
from oneconf import utils
from .netstatus import NetworkStatusWatcher
from .ssohandler import LoginBackendDbusSSO

from oneconf.paths import (
    LAST_SYNC_DATE_FILENAME, ONECONF_CACHE_DIR, OTHER_HOST_FILENAME,
    PACKAGE_LIST_PREFIX, PENDING_UPLOAD_FILENAME)

from piston_mini_client.failhandlers import APIError
try:
    from http.client import BadStatusLine
except ImportError:
    # Python 2
    from httplib import BadStatusLine
from httplib2 import socket, ServerNotFoundError, RedirectLimit

LOG = logging.getLogger(__name__)

class SyncHandler(GObject.GObject):
    '''Handle sync request with the server from the dbus service'''

    def __init__(self, hosts,
                 package_handler=None, infraclient=None, dbusemitter=None):
        GObject.GObject.__init__(self)

        self._netstate = NetworkStatusWatcher()
        self._sso_login = LoginBackendDbusSSO()
        self._can_sync = False
        self.credential = None
        self.hosts = hosts
        self.infraclient = infraclient
        self.package_handler = package_handler

        if dbusemitter:
            self.emit_new_hostlist = dbusemitter.hostlist_changed
            self.emit_new_packagelist = dbusemitter.packagelist_changed
            self.emit_new_logo = dbusemitter.logo_changed
            self.emit_new_latestsync = dbusemitter.latestsync_changed

        self._netstate.connect("changed", self._network_state_changed)
        self._sso_login.connect("login-result", self._sso_login_result)


    def _refresh_can_sync(self):
        '''compute current syncable state before asking for refresh the value'''
        new_can_sync = (self.credential is not None) and (self.infraclient is not None) and self._netstate.connected
        if self._can_sync == new_can_sync:
            return
        self._can_sync = new_can_sync

        # we can now start syncing (as it's a new status), adding the timeout
        # TODO: self.infraclient should be built here
        if self._can_sync:
            self.process_sync()
            # adding the timeout only if we are not on a single sync
            if os.environ.get('ONECONF_SINGLE_SYNC') is None:
                GLib.timeout_add_seconds(MIN_TIME_WITHOUT_ACTIVITY,
                                         self.process_sync)

    def _sso_login_result(self, sso_login, credential):
        if credential == self.credential:
            return

        self.credential = credential
        # Prepare the authenticated infraclient
        if self.credential and not self.infraclient:
            from piston_mini_client.auth import OAuthAuthorizer
            from .infraclient_pristine import WebCatalogAPI
            from oneconf.distributor import get_distro
            distro = get_distro()
            # No update if not supported distribution
            if not distro:
               return
            service_root = distro.ONECONF_SERVER
            authorizer = OAuthAuthorizer(token_key=credential['token'],
                token_secret=credential['token_secret'],
                consumer_key=credential['consumer_key'],
                consumer_secret=credential['consumer_secret'],
                oauth_realm='Ubuntu Software Center')
            self.infraclient = WebCatalogAPI(service_root=service_root,
                                             auth=authorizer)
        self._refresh_can_sync()

    def _network_state_changed(self, netstate, connected):
        self._refresh_can_sync()

    def check_if_refresh_needed(self, old_data, new_data, hostid, key):
        '''Return if data dictionnary needs to be refreshed'''
        need_refresh = False
        LOG.debug("Check if %s needs to be refreshed for %s" % (key, hostid))
        try:
            if old_data[hostid]['%s_checksum' % key] != new_data[hostid]['%s_checksum' % key]:
                need_refresh = True
        except KeyError:
            # there was no old_data, if the new ones are not none, refresh
            if new_data[hostid]['%s_checksum' % key]:
                need_refresh = True
        if need_refresh:
            LOG.debug("Refresh new %s" % key)
        return need_refresh

    def check_if_push_needed(self, local_data, distant_data, key):
        '''Return if data dictionnary needs to be refreshed

            Contrary to refresh needed, we are sure that the host is registered.
            However the local checksum can be null, telling that no refresh is needed'''
        LOG.debug("Check if %s for current host need to be pushed to infra" % key)
        try:
            need_push = (local_data['%s_checksum' % key] and (local_data['%s_checksum' % key] != distant_data['%s_checksum' % key]))
        except KeyError:
            need_push = True
        if need_push:
            LOG.debug("Push new %s" % key)
        return need_push

    def emit_new_hostlist(self):
        '''this signal will be bound at init time'''
        LOG.warning("emit_new_hostlist not bound to anything")

    def emit_new_packagelist(self, hostid):
        '''this signal will be bound at init time'''
        LOG.warning("emit_new_packagelist(%s) not bound to anything" % hostid)

    def emit_new_logo(self, hostid):
        '''this signal will be bound at init time'''
        LOG.warning("emit_new_logo(%s) not bound to anything" % hostid)

    def emit_new_latestsync(self, timestamp):
        '''this signal will be bound at init time'''
        LOG.warning("emit_new_lastestsync(%s) not bound to anything" % timestamp)

    def process_sync(self):
        '''start syncing what's needed if can sync

        process sync can be either started directly, or when can_sync changed'''

        # we can't no more sync, removing the timeout
        if not self._can_sync:
            return False
        LOG.debug("Start processing sync")

        # Check server connection
        try:
            if self.infraclient.server_status() != 'ok':
                LOG.error("WebClient server answering but not available")
                return True
        except (APIError, socket.error, ValueError, ServerNotFoundError,
                BadStatusLine, RedirectLimit) as e:
            LOG.error ("WebClient server answer error: %s", e)
            return True

        # Try to do every other hosts pending changes first (we will get fresh
        # data then)
        try:
            pending_upload_filename = os.path.join(
                self.hosts.get_currenthost_dir(), PENDING_UPLOAD_FILENAME)
            with open(pending_upload_filename, 'r') as f:
                pending_changes = json.load(f)
            # We're going to mutate the dictionary inside the loop, so we need
            # to make a copy of the keys dictionary view.
            for hostid in list(pending_changes.keys()):
                # now do action depending on what needs to be refreshed
                try:
                    # we can only remove distant machines for now, not
                    # register new ones
                    try:
                        if not pending_changes[hostid].pop('share_inventory'):
                            LOG.debug('Removing machine %s requested as a '
                                      'pending change' % hostid)
                            self.infraclient.delete_machine(
                                machine_uuid=hostid)
                    except APIError as e:
                        LOG.error("WebClient server doesn't want to remove "
                                  "hostid (%s): %s" % (hostid, e))
                        # append it again to be done
                        pending_changes[hostid]['share_inventory'] = False
                except KeyError:
                    pass
                # after all changes, is hostid still relevant?
                if not pending_changes[hostid]:
                    pending_changes.pop(hostid)
            # no more change, remove the file
            if not pending_changes:
                LOG.debug(
                    "No more pending changes remaining, removing the file")
                os.remove(pending_upload_filename)
            # update the remaining tasks
            else:
                utils.save_json_file_update(
                    pending_upload_filename, pending_changes)
        except IOError:
            pass
        except ValueError:
            LOG.warning("The pending file is broken, ignoring")

        current_hostid = self.hosts.current_host['hostid']
        old_hosts = self.hosts.other_hosts
        hostlist_changed = None
        packagelist_changed = []
        logo_changed = []

        # Get all machines
        try:
            full_hosts_list = self.infraclient.list_machines()
        except APIError as e:
            LOG.error("Invalid machine list from server, stopping sync: %s" % e)
            return True
        other_hosts = {}
        distant_current_host = {}
        for machine in full_hosts_list:
            hostid = machine.pop("uuid")
            if hostid != current_hostid:
                other_hosts[hostid] = machine
            else:
                distant_current_host = machine

        # now refresh packages list for every hosts
        for hostid in other_hosts:
            # init the list as the infra can not send it
            if not "packages_checksum" in other_hosts[hostid]:
                other_hosts[hostid]["packages_checksum"] = None
            packagelist_filename = os.path.join(self.hosts.get_currenthost_dir(), '%s_%s' % (PACKAGE_LIST_PREFIX, hostid))
            if self.check_if_refresh_needed(old_hosts, other_hosts, hostid, 'packages'):
                try:
                    new_package_list = self.infraclient.list_packages(machine_uuid=hostid)
                    utils.save_json_file_update(packagelist_filename, new_package_list)
                    # if already loaded, unload the package cache
                    if self.package_handler:
                        try:
                           self.package_handler.package_list[hostid]['valid'] = False
                        except KeyError:
                            pass
                    packagelist_changed.append(hostid)
                except APIError as e:
                    LOG.error ("Invalid package data from server: %s", e)
                    try:
                        old_checksum = old_hosts[hostid]['packages_checksum']
                    except KeyError:
                        old_checksum = None
                    other_hosts[hostid]['packages_checksum'] = old_checksum

            # refresh the logo for every hosts as well
            # WORKING but not wanted on the isd side for now
            #if self.check_if_refresh_needed(old_hosts, other_hosts, hostid, 'logo'):
            #    try:
            #        logo_content = self.infraclient.get_machine_logo(machine_uuid=hostid)
            #        logo_file = open(os.path.join(self.hosts.get_currenthost_dir(), "%s_%s.png" % (LOGO_PREFIX, hostid)), 'wb+')
            #        logo_file.write(self.infraclient.get_machine_logo(machine_uuid=hostid))
            #        logo_file.close()
            #        logo_changed.append(hostid)
            #    except APIError, e:
            #        LOG.error ("Invalid data from server: %s", e)
            #        try:
            #            old_checksum = old_hosts[hostid]['logo_checksum']
            #        except KeyError:
            #            old_checksum = None
            #        other_hosts[hostid]['logo_checksum'] = old_checksum

        # Now that the package list and logo are successfully downloaded, save
        # the hosts metadata there. This removes as well the remaining package list and logo
        LOG.debug("Check if other hosts metadata needs to be refreshed")
        if other_hosts != old_hosts:
            LOG.debug("Refresh new host")
            hostlist_changed = True
            other_host_filename = os.path.join(ONECONF_CACHE_DIR, current_hostid, OTHER_HOST_FILENAME)
            utils.save_json_file_update(other_host_filename, other_hosts)
            self.hosts.update_other_hosts()

        # now push current host
        if not self.hosts.current_host['share_inventory']:
            LOG.debug("Ensure that current host is not shared")
            try:
                self.infraclient.delete_machine(machine_uuid=current_hostid)
            except APIError as e:
                # just a debug message as it can be already not shared
                LOG.debug ("Can't delete current host from infra: %s" % e)
        else:
            LOG.debug("Push current host to infra now")
            # check if current host changed
            try:
                if self.hosts.current_host['hostname'] != distant_current_host['hostname']:
                    try:
                        self.infraclient.update_machine(machine_uuid=current_hostid, hostname=self.hosts.current_host['hostname'])
                        LOG.debug ("Host data refreshed")
                    except APIError as e:
                        LOG.error ("Can't update machine: %s", e)
            except KeyError:
                try:
                    self.infraclient.update_machine(machine_uuid=current_hostid, hostname=self.hosts.current_host['hostname'])
                    LOG.debug ("New host registered done")
                    distant_current_host = {'packages_checksum': None, 'logo_checksum': None}
                except APIError as e:
                    LOG.error ("Can't register new host: %s", e)

            # local package list
            if self.check_if_push_needed(self.hosts.current_host, distant_current_host, 'packages'):
                local_packagelist_filename = os.path.join(self.hosts.get_currenthost_dir(), '%s_%s' % (PACKAGE_LIST_PREFIX, current_hostid))
                try:
                    with open(local_packagelist_filename, 'r') as f:
                        self.infraclient.update_packages(machine_uuid=current_hostid, packages_checksum=self.hosts.current_host['packages_checksum'], package_list=json.load(f))
                except (APIError, IOError) as e:
                        LOG.error ("Can't push current package list: %s", e)

            # local logo
            # WORKING but not wanted on the isd side for now
            #if self.check_if_push_needed(self.hosts.current_host, distant_current_host, 'logo'):
            #    logo_file = open(os.path.join(self.hosts.get_currenthost_dir(), "%s_%s.png" % (LOGO_PREFIX, current_hostid))).read()
            #    try:
            #        self.infraclient.update_machine_logo(machine_uuid=current_hostid, logo_checksum=self.hosts.current_host['logo_checksum'], logo_content=logo_file)
            #        LOG.debug ("refresh done")
            #    except APIError, e:
            #        LOG.error ("Error while pushing current logo: %s", e)

        # write the last sync date
        timestamp = str(time.time())
        content = {"last_sync":  timestamp}
        utils.save_json_file_update(os.path.join(self.hosts.get_currenthost_dir(), LAST_SYNC_DATE_FILENAME), content)

        # send dbus signal if needed events (just now so that we don't block on remaining operations)
        if hostlist_changed:
            self.emit_new_hostlist()
        for hostid in packagelist_changed:
            self.emit_new_packagelist(hostid)
        for hostid in logo_changed:
            self.emit_new_logo(hostid)
        self.emit_new_latestsync(timestamp)

        # continue syncing in the main loop
        return True
