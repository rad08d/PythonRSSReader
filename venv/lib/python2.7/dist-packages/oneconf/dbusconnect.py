# Copyright (C) 2010 Canonical
#
# Authors:
#  Didier Roche <didrocks@ubuntu.com>
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

import dbus
import dbus.service
from gi.repository import GLib
import logging
import sys

from gettext import gettext as _

LOG = logging.getLogger(__name__)

from oneconf.enums import ONECONF_SERVICE_NAME

HOSTS_OBJECT_NAME = "/com/ubuntu/oneconf/HostsHandler"
PACKAGE_SET_INTERFACE = "com.ubuntu.OneConf.HostsHandler.PackageSetHandler"
HOSTS_INTERFACE = "com.ubuntu.OneConf.HostsHandler.Hosts"
ONECONF_DBUS_TIMEOUT = 300

def none_to_null(var):
    '''return var in dbus compatible format'''
    if not var:
        var = ''
    return var

class DbusHostsService(dbus.service.Object):

    """
    Dbus service, daemon side
    """

    def __init__(self, loop):
        '''registration over dbus'''
        bus_name = dbus.service.BusName(ONECONF_SERVICE_NAME,
                                        bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, HOSTS_OBJECT_NAME)
        # Only import oneconf module now for only getting it on server side
        from oneconf.hosts import Hosts

        self.hosts = Hosts()
        self._packageSetHandler = None
        self.activity = False
        self.synchandler = None
        self.loop = loop

    # TODO: can be a decorator, handling null case and change the API so that if it returns
    # the None value -> no result
    def get_packageSetHandler(self):
        '''Ensure we load the package set handler at the right time'''
        if not self._packageSetHandler:
            from oneconf.packagesethandler import PackageSetHandler, PackageSetInitError
            try:
                self._packageSetHandler = PackageSetHandler(self.hosts)
            except PackageSetInitError as e:
                LOG.error (e)
                self._packageSetHandler = None
        return self._packageSetHandler

    @dbus.service.method(HOSTS_INTERFACE)
    def get_all_hosts(self):
        self.activity = True
        return self.hosts.get_all_hosts()

    @dbus.service.method(HOSTS_INTERFACE)
    def set_share_inventory(self, share_inventory, hostid, hostname):
        self.activity = True
        if share_inventory: # map to boolean to avoid difference in dbus call and direct
            share_inventory = True
        else:
            share_inventory = False
        return self.hosts.set_share_inventory(share_inventory, hostid, hostname)

    @dbus.service.method(PACKAGE_SET_INTERFACE)
    def get_packages(self, hostid, hostname, only_manual):
        self.activity = True
        if not self.get_packageSetHandler():
            return ''
        return none_to_null(self.get_packageSetHandler().get_packages(hostid, hostname, only_manual))

    @dbus.service.method(PACKAGE_SET_INTERFACE)
    def diff(self, hostid, hostname):
        self.activity = True
        if not self.get_packageSetHandler():
            return ('', '')
        return self.get_packageSetHandler().diff(hostid, hostname)

    @dbus.service.method(PACKAGE_SET_INTERFACE)
    def update(self):
        self.activity = True
        if self.get_packageSetHandler():
            self.get_packageSetHandler().update()

    @dbus.service.method(PACKAGE_SET_INTERFACE)
    def async_update(self):
        self.activity = True
        if self.get_packageSetHandler():
            GLib.timeout_add_seconds(1, self.get_packageSetHandler().update)

    @dbus.service.signal(HOSTS_INTERFACE)
    def hostlist_changed(self):
        LOG.debug("Send host list changed dbus signal")

    @dbus.service.signal(PACKAGE_SET_INTERFACE)
    def packagelist_changed(self, hostid):
        LOG.debug("Send package list changed dbus signal for hostid: %s" % hostid)

    @dbus.service.signal(HOSTS_INTERFACE)
    def logo_changed(self, hostid):
        LOG.debug("Send logo changed dbus signal for hostid: %s" % hostid)

    @dbus.service.signal(HOSTS_INTERFACE)
    def latestsync_changed(self, timestamp):
        LOG.debug("Send last sync timestamp: %s" % timestamp)

    @dbus.service.method(HOSTS_INTERFACE)
    def get_last_sync_date(self):
        self.activity = True
        return self.hosts.get_last_sync_date()

    @dbus.service.method(HOSTS_INTERFACE)
    def stop_service(self):
        LOG.debug("Request for stopping OneConf service")
        self.loop.quit()
        return True

class DbusConnect(object):

    """
    Dbus request sender, daemon connection
    """

    def __init__(self):
        '''connect to the bus and get packagesethandler object'''
        self.bus = dbus.SessionBus()
        self.hosts_dbus_object = self.bus.get_object(ONECONF_SERVICE_NAME,
                                                     HOSTS_OBJECT_NAME)

    def _get_package_handler_dbusobject(self):
        '''get package handler dbus object'''
        return dbus.Interface(self.hosts_dbus_object, PACKAGE_SET_INTERFACE)

    def _get_hosts_dbusobject(self):
        '''get hosts dbus object'''
        return dbus.Interface(self.hosts_dbus_object, HOSTS_INTERFACE)

    def get_all_hosts(self):
        '''get a dictionnary of all available hosts'''
        return self._get_hosts_dbusobject().get_all_hosts()

    def set_share_inventory(self, share_inventory, hostid='', hostname=''):
        '''update if we share the chosen host inventory on the server'''
        self._get_hosts_dbusobject().set_share_inventory(share_inventory,
                                                         hostid, hostname,
                                                         timeout=ONECONF_DBUS_TIMEOUT)

    def get_packages(self, hostid, hostname, only_manual):
        '''trigger getpackages handling'''

        try:
            return self._get_package_handler_dbusobject().get_packages(hostid,
                                                           hostname, only_manual)
        except dbus.exceptions.DBusException as e:
            print(e)
            sys.exit(1)

    def diff(self, hostid, hostname):
        '''trigger diff handling'''

        try:
            return self._get_package_handler_dbusobject().diff(hostid,
                                                            hostname,
                                                            timeout=ONECONF_DBUS_TIMEOUT)
        except dbus.exceptions.DBusException as e:
            print(e)
            sys.exit(1)

    def update(self):
        '''trigger update handling'''
        self._get_package_handler_dbusobject().update(timeout=ONECONF_DBUS_TIMEOUT)

    def async_update(self):
        '''trigger update handling'''
        self._get_package_handler_dbusobject().async_update()

    def get_last_sync_date(self):
        '''just send a kindly ping to retrieve the last sync date'''
        return self._get_hosts_dbusobject().get_last_sync_date(timeout=ONECONF_DBUS_TIMEOUT)

    def stop_service(self):
        '''kindly ask the oneconf service to stop'''
        try:
            self._get_hosts_dbusobject().stop_service()
        except dbus.exceptions.DBusException as e:
            print(_("Wasn't able to request stopping the service: %s" % e))
            sys.exit(1)
