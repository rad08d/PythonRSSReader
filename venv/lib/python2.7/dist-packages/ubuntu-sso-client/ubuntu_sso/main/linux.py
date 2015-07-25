# -*- coding: utf-8 -*-
#
# Copyright 2009-2012 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# In addition, as a special exception, the copyright holders give
# permission to link the code of portions of this program with the
# OpenSSL library under certain conditions as described in each
# individual source file, and distribute linked combinations
# including the two.
# You must obey the GNU General Public License in all respects
# for all of the code used other than OpenSSL.  If you modify
# file(s) with this exception, you may extend this exception to your
# version of the file(s), but you are not obligated to do so.  If you
# do not wish to do so, delete this exception statement from your
# version.  If you delete this exception statement from all source
# files in the program, then also delete it here.
"""Main module implementation specific for linux.

This module should never import from the multiplatform one (main/__init__.py),
but the other way around. Likewise, this module should *not* have any logic
regarding error processing or decision making about when to send a given
signal.

Also, most of the logging is being made in the main module to avoid
duplication between the different platform implementations.

"""

import signal

import dbus
import dbus.service

from twisted.internet import defer

from ubuntu_sso import (
    DBUS_ACCOUNT_PATH,
    DBUS_BUS_NAME,
    DBUS_CREDENTIALS_IFACE,
    DBUS_CREDENTIALS_PATH,
    DBUS_IFACE_USER_NAME,
    NO_OP,
)
from ubuntu_sso.logger import setup_logging


# Disable the invalid name warning, as we have a lot of DBus style names
# pylint: disable=C0103


logger = setup_logging("ubuntu_sso.main.linux")


class SSOLoginProxy(dbus.service.Object):
    """Login thru the Single Sign On service."""

    # Use of super on an old style class
    # pylint: disable=E1002

    def __init__(self, root, *args, **kwargs):
        """Initiate the Login object."""
        # pylint: disable=E1002
        super(SSOLoginProxy, self).__init__(*args, **kwargs)
        self.root = root

    # Operator not preceded by a space (fails with dbus decorators)
    # pylint: disable=C0322

    # generate_capcha signals
    @dbus.service.signal(DBUS_IFACE_USER_NAME, signature="ss")
    def CaptchaGenerated(self, app_name, result):
        """Signal thrown after the captcha is generated."""

    @dbus.service.signal(DBUS_IFACE_USER_NAME, signature="sa{ss}")
    def CaptchaGenerationError(self, app_name, error):
        """Signal thrown when there's a problem generating the captcha."""

    @dbus.service.method(dbus_interface=DBUS_IFACE_USER_NAME,
                         in_signature='ss')
    def generate_captcha(self, app_name, filename):
        """Call the matching method in the processor."""
        self.root.sso_login.generate_captcha(app_name, filename)

    # register_user signals
    @dbus.service.signal(DBUS_IFACE_USER_NAME, signature="ss")
    def UserRegistered(self, app_name, result):
        """Signal thrown when the user is registered."""

    @dbus.service.signal(DBUS_IFACE_USER_NAME, signature="sa{ss}")
    def UserRegistrationError(self, app_name, error):
        """Signal thrown when there's a problem registering the user."""

    @dbus.service.method(dbus_interface=DBUS_IFACE_USER_NAME,
                         in_signature='ssssss')
    def register_user(self, app_name, email, password, name,
                      captcha_id, captcha_solution):
        """Call the matching method in the processor."""
        self.root.sso_login.register_user(app_name, email, password, name,
            captcha_id, captcha_solution)

    # login signals
    @dbus.service.signal(DBUS_IFACE_USER_NAME, signature="ss")
    def LoggedIn(self, app_name, result):
        """Signal thrown when the user is logged in."""

    @dbus.service.signal(DBUS_IFACE_USER_NAME, signature="sa{ss}")
    def LoginError(self, app_name, error):
        """Signal thrown when there is a problem in the login."""

    @dbus.service.signal(DBUS_IFACE_USER_NAME, signature="ss")
    def UserNotValidated(self, app_name, result):
        """Signal thrown when the user is not validated."""

    @dbus.service.method(dbus_interface=DBUS_IFACE_USER_NAME,
                         in_signature='sss')
    def login(self, app_name, email, password):
        """Call the matching method in the processor."""
        self.root.sso_login.login(app_name, email, password, ping_url=None)

    @dbus.service.method(dbus_interface=DBUS_IFACE_USER_NAME,
                         in_signature='ssss')
    def login_and_ping(self, app_name, email, password, ping_url):
        """Call the matching method in the processor."""
        self.root.sso_login.login(app_name, email, password, ping_url)

    # validate_email signals
    @dbus.service.signal(DBUS_IFACE_USER_NAME, signature="ss")
    def EmailValidated(self, app_name, result):
        """Signal thrown after the email is validated."""

    @dbus.service.signal(DBUS_IFACE_USER_NAME, signature="sa{ss}")
    def EmailValidationError(self, app_name, error):
        """Signal thrown when there's a problem validating the email."""

    @dbus.service.method(dbus_interface=DBUS_IFACE_USER_NAME,
                         in_signature='ssss')
    def validate_email(self, app_name, email, password, email_token):
        """Call the matching method in the processor."""
        self.root.sso_login.validate_email(app_name,
            email, password, email_token, ping_url=None)

    @dbus.service.method(dbus_interface=DBUS_IFACE_USER_NAME,
                         in_signature='sssss')
    def validate_email_and_ping(self, app_name, email, password, email_token,
                                ping_url):
        """Call the matching method in the processor."""
        self.root.sso_login.validate_email(app_name,
            email, password, email_token, ping_url)

    # request_password_reset_token signals
    @dbus.service.signal(DBUS_IFACE_USER_NAME, signature="ss")
    def PasswordResetTokenSent(self, app_name, result):
        """Signal thrown when the token is succesfully sent."""

    @dbus.service.signal(DBUS_IFACE_USER_NAME, signature="sa{ss}")
    def PasswordResetError(self, app_name, error):
        """Signal thrown when there's a problem sending the token."""

    @dbus.service.method(dbus_interface=DBUS_IFACE_USER_NAME,
                         in_signature='ss')
    def request_password_reset_token(self, app_name, email):
        """Call the matching method in the processor."""
        self.root.sso_login.request_password_reset_token(app_name, email)

    # set_new_password signals
    @dbus.service.signal(DBUS_IFACE_USER_NAME, signature="ss")
    def PasswordChanged(self, app_name, result):
        """Signal thrown when the token is succesfully sent."""

    @dbus.service.signal(DBUS_IFACE_USER_NAME, signature="sa{ss}")
    def PasswordChangeError(self, app_name, error):
        """Signal thrown when there's a problem sending the token."""

    @dbus.service.method(dbus_interface=DBUS_IFACE_USER_NAME,
                         in_signature='ssss')
    def set_new_password(self, app_name, email, token, new_password):
        """Call the matching method in the processor."""
        self.root.sso_login.set_new_password(app_name,
            email, token, new_password)


class CredentialsManagementProxy(dbus.service.Object):
    """Object that manages credentials.

    Every exposed method in this class requires one mandatory argument:

        - 'app_name': the name of the application. Will be displayed in the
        GUI header, plus it will be used to find/build/clear tokens.

    And accepts another parameter named 'args', which is a dictionary that
    can contain the following:

        - 'help_text': an explanatory text for the end-users, will be
        shown below the header. This is an optional free text field.

        - 'ping_url': the url to open after successful token retrieval. If
        defined, the email will be attached to the url and will be pinged
        with a OAuth-signed request.

        - 'tc_url': the link to the Terms and Conditions page. If defined,
        the checkbox to agree to the terms will link to it.

        - 'window_id': the id of the window which will be set as a parent
        of the GUI. If not defined, no parent will be set.

    """

    # Use of super on an old style class
    # pylint: disable=E1002

    def __init__(self, root, *args, **kwargs):
        # pylint: disable=E1002
        super(CredentialsManagementProxy, self).__init__(*args, **kwargs)
        self.root = root

    # Operator not preceded by a space (fails with dbus decorators)
    # pylint: disable=C0322

    @dbus.service.signal(DBUS_CREDENTIALS_IFACE, signature='s')
    def AuthorizationDenied(self, app_name):
        """Signal thrown when the user denies the authorization."""

    @dbus.service.signal(DBUS_CREDENTIALS_IFACE, signature='sa{ss}')
    def CredentialsFound(self, app_name, credentials):
        """Signal thrown when the credentials are found."""

    @dbus.service.signal(DBUS_CREDENTIALS_IFACE, signature='s')
    def CredentialsNotFound(self, app_name):
        """Signal thrown when the credentials are not found."""

    @dbus.service.signal(DBUS_CREDENTIALS_IFACE, signature='s')
    def CredentialsCleared(self, app_name):
        """Signal thrown when the credentials were cleared."""

    @dbus.service.signal(DBUS_CREDENTIALS_IFACE, signature='s')
    def CredentialsStored(self, app_name):
        """Signal thrown when the credentials were cleared."""

    @dbus.service.signal(DBUS_CREDENTIALS_IFACE, signature='sa{ss}')
    def CredentialsError(self, app_name, error_dict):
        """Signal thrown when there is a problem getting the credentials."""

    @dbus.service.method(dbus_interface=DBUS_CREDENTIALS_IFACE,
                         in_signature='sa{ss}', out_signature='')
    def find_credentials(self, app_name, args):
        """Look for the credentials for an application.

        - 'app_name': the name of the application which credentials are
        going to be removed.

        - 'args' is a dictionary, currently not used.

        """
        self.root.cred_manager.find_credentials(app_name, args)

    @dbus.service.method(dbus_interface=DBUS_CREDENTIALS_IFACE,
                         in_signature="sa{ss}", out_signature="a{ss}",
                         async_callbacks=("reply_handler", "error_handler"))
    def find_credentials_sync(self, app_name, args,
                              reply_handler=NO_OP, error_handler=NO_OP):
        """Get the credentials from the keyring or {} if not there.

        This method SHOULD NOT be used, is here only for compatibilty issues.

        """

        def _drop_dict(error_dict):
            """Call 'error_handler' properly."""
            error_handler(dbus.service.DBusException(error_dict['errtype']))

        self.root.cred_manager.find_credentials(app_name, args,
                                   success_cb=reply_handler,
                                   error_cb=_drop_dict)

    @dbus.service.method(dbus_interface=DBUS_CREDENTIALS_IFACE,
                         in_signature='sa{ss}', out_signature='')
    def clear_credentials(self, app_name, args):
        """Clear the credentials for an application.

        - 'app_name': the name of the application which credentials are
        going to be removed.

        - 'args' is a dictionary, currently not used.

        """
        self.root.cred_manager.clear_credentials(app_name, args)

    @dbus.service.method(dbus_interface=DBUS_CREDENTIALS_IFACE,
                         in_signature='sa{ss}', out_signature='')
    def store_credentials(self, app_name, args):
        """Store the token for an application.

        - 'app_name': the name of the application which credentials are
        going to be stored.

        - 'args' is the dictionary holding the credentials. Needs to provide
        the following mandatory keys: 'token', 'token_key', 'consumer_key',
        'consumer_secret'.

        """
        self.root.cred_manager.store_credentials(app_name, args)

    @dbus.service.method(dbus_interface=DBUS_CREDENTIALS_IFACE,
                         in_signature='sa{ss}', out_signature='')
    def register(self, app_name, args):
        """Get credentials if found else prompt GUI to register."""
        self.root.cred_manager.register(app_name, args)

    @dbus.service.method(dbus_interface=DBUS_CREDENTIALS_IFACE,
                         in_signature='sa{ss}', out_signature='')
    def login(self, app_name, args):
        """Get credentials if found else prompt GUI to login."""
        self.root.cred_manager.login(app_name, args)

    @dbus.service.method(dbus_interface=DBUS_CREDENTIALS_IFACE,
                         in_signature='sa{ss}', out_signature='')
    def login_email_password(self, app_name, args):
        """Get credentials if found, else login using email and password.

        - 'args' should contain at least the follwing keys: 'email' and
        'password'. Those will be used to issue a new SSO token, which will be
        returned trough the CredentialsFound signal.

        """
        self.root.cred_manager.login_email_password(app_name, args)


class UbuntuSSOProxy(object):
    """Object that exposes the diff referenceable objects."""

    def __init__(self, root):
        self.root = root
        self.sso_login = None
        self.cred_manager = None

        try:
            self.bus = dbus.SessionBus()
        except dbus.service.DBusException as e:
            logger.exception(e)
            shutdown_func()

    def start(self):
        """Start listening, nothing async to be done in this platform."""
        # Register DBus service for making sure we run only one instance
        name = self.bus.request_name(DBUS_BUS_NAME,
                                     dbus.bus.NAME_FLAG_DO_NOT_QUEUE)
        if name == dbus.bus.REQUEST_NAME_REPLY_EXISTS:
            raise AlreadyStartedError()

        bus_name = dbus.service.BusName(DBUS_BUS_NAME, bus=self.bus)
        self.sso_login = SSOLoginProxy(self.root,
                                       bus_name=bus_name,
                                       object_path=DBUS_ACCOUNT_PATH)
        self.cred_manager = CredentialsManagementProxy(self.root,
                                bus_name=bus_name,
                                object_path=DBUS_CREDENTIALS_PATH)

        return defer.succeed(None)

    def shutdown(self):
        """Shutdown the service."""
        self.sso_login.remove_from_connection()
        self.cred_manager.remove_from_connection()
        self.bus.release_name(DBUS_BUS_NAME)
        return defer.succeed(None)


# ============================== client classes ==============================


class RemoteClient(object):
    """Client that can perform calls to remote DBus object."""

    bus_name = None
    path = None
    interface = None

    def __init__(self):
        self.bus = dbus.SessionBus()
        obj = self.bus.get_object(bus_name=self.bus_name,
                                  object_path=self.path,
                                  follow_name_owner_changes=True)
        self.dbus_iface = dbus.Interface(obj, dbus_interface=self.interface)
        self.dbus_iface.call_method = self.call_method
        self.dbus_iface.disconnect_from_signal = lambda _, sig: sig.remove()

    def call_method(self, method_name, *args, **kwargs):
        """Call asynchronously 'method_name(*args)'.

        Return a deferred that will be fired when the call finishes.

        """
        d = defer.Deferred()

        reply_handler = kwargs.get('reply_handler', None)
        if reply_handler is not None:
            d.addCallback(lambda a: reply_handler(*a))

        error_handler = kwargs.get('error_handler', None)
        if error_handler is not None:
            d.addErrback(lambda f: error_handler(f.value))

        self.bus.call_async(
            bus_name=self.bus_name, object_path=self.path,
            dbus_interface=self.interface, method=method_name,
            signature=None, args=args,
            reply_handler=lambda *a: d.callback(a),
            error_handler=d.errback)

        return d


class SSOLoginClient(RemoteClient):
    """Access the UserManagement DBus interface."""

    bus_name = DBUS_BUS_NAME
    path = DBUS_ACCOUNT_PATH
    interface = DBUS_IFACE_USER_NAME


class CredentialsManagementClient(RemoteClient):
    """Access the CredentialsManagement DBus interface."""

    bus_name = DBUS_BUS_NAME
    path = DBUS_CREDENTIALS_PATH
    interface = DBUS_CREDENTIALS_IFACE


class UbuntuSSOClient(object):
    """Base client that provides remote access to the sso API."""

    def __init__(self):
        self.sso_login = SSOLoginClient().dbus_iface
        self.cred_manager = CredentialsManagementClient().dbus_iface

    def connect(self):
        """No need to connect DBus proxy objects."""
        return defer.succeed(None)

    def disconnect(self):
        """No need to disconnect DBus proxy objects."""
        return defer.succeed(None)


def get_sso_client():
    """Get a client to access the SSO service."""
    result = UbuntuSSOClient()
    return defer.succeed(result)


try:
    from ubuntu_sso.main import qt
    source = qt
except ImportError:  # no PyQt4.QtCore in the system
    from ubuntu_sso.main import glib
    source = glib


timeout_func = source.timeout_func
shutdown_func = source.shutdown_func
start_setup = source.start_setup


def sighup_handler(*a, **kw):
    """Stop the service."""
    # This handler may be called in any thread, so is not thread safe.
    # See the link below for info:
    # www.listware.net/201004/gtk-devel-list/115067-unix-signals-in-glib.html
    logger.info("Stoping Ubuntu SSO service since SIGHUP was received.")
    shutdown_func()


class AlreadyStartedError(Exception):
    """The backend service has already been started."""


def finish_setup(result, loop):
    """Run the specific mainloop only if no failure ocurred."""
    if result is None:  # no failure ocurred, start the service
        logger.debug("Hooking up SIGHUP with handler %r.", sighup_handler)
        signal.signal(signal.SIGHUP, sighup_handler)
        source.run_func(loop)


def main():
    """Run the specific mainloop."""
