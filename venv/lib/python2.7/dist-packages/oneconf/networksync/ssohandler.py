#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2010-2011 Canonical
#
# Authors:
#  Michael Vogt
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

import dbus
import gettext
from gi.repository import GObject, GLib
import logging
import os

from oneconf.enums import MIN_TIME_WITHOUT_ACTIVITY

#from gettext import gettext as _
gettext.textdomain("software-center")

NO_OP = lambda *args, **kwargs: None

LOG = logging.getLogger(__name__)

class LoginBackendDbusSSO(GObject.GObject):


    __gsignals__ = {
        "login-result" : (GObject.SIGNAL_RUN_LAST,
                          GObject.TYPE_NONE,
                          (GObject.TYPE_PYOBJECT,),
                         ),
        }

    def __init__(self):
        super(LoginBackendDbusSSO, self).__init__()

        # use USC credential
        #self.appname = _("Ubuntu Software Center Store")
        self.appname = "Ubuntu Software Center"

        if "ONECONF_SSO_CRED" in os.environ:
            if os.environ["ONECONF_SSO_CRED"].lower() == 'true':
                LOG.warn('forced fake sso cred...')
                GLib.idle_add(self._on_credentials_found, self.appname, "foo")
            else:
                LOG.warn('forced not having any sso cred...')
                GLib.idle_add(self._on_credentials_not_found, self.appname)
            return

        self.bus = dbus.SessionBus()

        self.proxy = None
        self._get_sso_proxy()
        # try it in a spawn/retry process to avoid ubuntu sso login issues
        GLib.timeout_add_seconds(MIN_TIME_WITHOUT_ACTIVITY,
                                 self._get_sso_proxy)

    def _get_sso_proxy(self):
        '''avoid crashing if ubuntu sso doesn't answer, which seems common'''

        LOG.debug("Try to get a proxy")
        try:
            # recreate a proxy object to respawn the sso daemon
            # (TODO: migration to gdbus and dbus owner changed should help)
            self.proxy = self.bus.get_object('com.ubuntu.sso', '/com/ubuntu/sso/credentials')
            self.proxy.connect_to_signal("CredentialsFound",
                                         self._on_credentials_found)
            self.proxy.connect_to_signal("CredentialsNotFound",
                                         self._on_credentials_not_found)
            self.proxy.connect_to_signal("CredentialsError",
                                         self._on_credentials_error)
            LOG.debug("look for credential")
            self.proxy.find_credentials(self.appname, '', reply_handler=NO_OP, error_handler=NO_OP)
        except dbus.DBusException as e:
            LOG.debug("No reply from ubuntu sso: %s" % e)
        return True # try again

    def _on_credentials_found(self, app_name, credentials):
        if app_name != self.appname:
            return
        LOG.debug("credential found")
        self.emit("login-result", credentials)

    def _on_credentials_not_found(self, app_name):
        if app_name != self.appname:
            return
        LOG.debug("credential not found")
        self.emit("login-result", None)

    def _on_credentials_error(self, app_name, error):
        if app_name != self.appname:
            return
        LOG.error("credential error")
        self.emit("login-result", None)



if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)

    login = LoginBackendDbusSSO()

    loop = GLib.MainLoop()

    def print_result(obj, foo):
        print(foo)

    login.connect("login-result", print_result)

    loop.run()
