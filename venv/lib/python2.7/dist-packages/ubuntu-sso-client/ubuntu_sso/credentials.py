# -*- coding: utf-8 -*-
#
# Copyright 2010-2012 Canonical Ltd.
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
"""Credential management utilities.

'Credentials' provides the following fault-tolerant methods:

 * find_credentials
 * clear_credentials
 * store_credentials
 * register
 * login

All the methods return a Deferred that will be fired when the operation was
completed.

For details, please read the Credentials class documentation.

"""

from functools import wraps

from twisted.internet import defer

from ubuntu_sso import (
    UI_EXECUTABLE_QT,
    USER_CANCELLATION,
    USER_SUCCESS,
)
from ubuntu_sso.keyring import Keyring
from ubuntu_sso.logger import setup_logging
from ubuntu_sso.utils import compat, get_bin_cmd, runner


logger = setup_logging('ubuntu_sso.credentials')


APP_NAME_KEY = 'app_name'
TC_URL_KEY = 'tc_url'
HELP_TEXT_KEY = 'help_text'
WINDOW_ID_KEY = 'window_id'
PING_URL_KEY = 'ping_url'
POLICY_URL_KEY = 'policy_url'
UI_EXECUTABLE_KEY = 'ui_executable'


class CredentialsError(Exception):
    """Generic credentials error."""


class UserCancellationError(CredentialsError):
    """The user cancelled the process of authentication."""


class UserNotValidatedError(CredentialsError):
    """The user is not validated."""


class GUINotAvailableError(CredentialsError):
    """No user graphical interface is available."""


def handle_failures(msg):
    """Handle failures using 'msg' as error message."""

    def middle(f):
        """Decorate 'f' to catch all errors."""

        @wraps(f)
        @defer.inlineCallbacks
        def inner(self, *a, **kw):
            """Call 'f' within a try-except block.

            If any exception occurs, the exception is logged and re-raised.

            """
            result = None
            try:
                result = yield f(self, *a, **kw)
            except:
                logger.exception('%s (app_name: %s): %s.',
                                 f.__name__, self.app_name, msg)
                raise

            defer.returnValue(result)

        return inner

    return middle


class Credentials(object):
    """Credentials management gateway."""

    def __init__(self, app_name, tc_url=None, help_text='',
                 window_id=0, ping_url=None, policy_url=None,
                 ui_executable=UI_EXECUTABLE_QT):
        """Return a Credentials management object.

        'app_name' is the application name to be displayed in the GUI.

        'tc_url' is the url pointing to Terms & Conditions. If None, no
        TOS agreement will be displayed.

        'help_text' is an explanatory text for the end-users, will be shown
         below the headers.

        'window_id' is the id of the window which will be set as a parent of
         the GUI. If 0, no parent will be set.

        'ping_url' is the url that will be pinged when a user registers/logins
        successfully. The user email will be attached to 'ping_url'.

        'policy_url' is the url pointing to the privacy policy. If None, no
        privacy policy agreement will be displayed.

        When the credentials are retrieved successfully, a dictionary like the
        one below is returned:

            {'token': <value>,
             'token_secret': <value>,
             'consumer_key': <value>,
             'consumer_secret': <value>,
             'name': <the token name, matches "[app_name] @ [host name]">}

        """
        self.app_name = app_name
        self.help_text = help_text
        self.window_id = window_id
        self.ping_url = ping_url
        self.tc_url = tc_url
        self.policy_url = policy_url
        self.ui_executable = ui_executable

    @defer.inlineCallbacks
    def _show_ui(self, login_only):
        """Show the UI and wait for it to finish.

        Upon analyzing returning code from the UI process, emit proper signals
        to the caller.

        The caller can specify a preference for the UI, but if the preferred
        one is not available, the service will try to open any available UI.

        If no GUI is available, GUINotAvailableError will be raised.

        """
        guis = (self.ui_executable, UI_EXECUTABLE_QT)
        for gui_exe_name in guis:
            try:
                args = get_bin_cmd(gui_exe_name)
            except OSError:
                logger.error('The given UI %r does not exist.',
                             gui_exe_name)
            else:
                break
        else:
            raise GUINotAvailableError('Can not find a GUI to present to the '
                                       'user (tried with %r). Aborting.' %
                                       repr(guis))

        for arg in ('app_name', 'help_text', 'ping_url', 'policy_url',
                    'tc_url', 'window_id'):
            value = getattr(self, arg)
            if value:
                args.append('--%s' % arg)
                if not isinstance(value, compat.basestring):
                    value = compat.text_type(value)
                args.append(value)

        if login_only:
            args.append('--login_only')

        return_code = yield runner.spawn_program(args)
        logger.info('_show_ui: received from the ui return code %r.',
                    return_code)

        credentials = None
        if return_code == USER_SUCCESS:
            credentials = yield self.find_credentials()
        elif return_code == USER_CANCELLATION:
            raise UserCancellationError()
        else:
            raise CredentialsError(return_code)

        defer.returnValue(credentials)

    def _do_login(self, email, password):
        """Login using email/password, connect outcome signals."""
        from ubuntu_sso.main import SSOLogin

        d = defer.Deferred()

        class DummyProxy(object):
            """A temporary proxy to handle non-traditional login."""

            # pylint: disable=C0103

            def LoggedIn(self, app_name, result):
                """User was logged in."""
                d.callback(result)

            def LoginError(self, app_name, error):
                """There was an error on login."""
                error = CredentialsError(error['errtype'])
                d.errback(error)

            def UserNotValidated(self, app_name, email):
                """User is not validated."""
                d.errback(UserNotValidatedError(email))

            # pylint: enable=C0103

        inner = SSOLogin(proxy=DummyProxy())
        inner.login(app_name=self.app_name,
                    email=email, password=password,
                    ping_url=self.ping_url)

        d.addCallback(lambda _: self.find_credentials())
        return d

    @defer.inlineCallbacks
    def _login_or_register(self, login_only, email=None, password=None):
        """Get credentials if found else prompt the GUI.

        Will return either the credentials, or will raise UserCancellationError
        if the user aborted the operation when the UI was opened.

        """
        logger.info("_login_or_register: login_only=%r email=%r.",
                    login_only, email)
        token = yield self.find_credentials()
        if not token:
            if email and password:
                token = yield self._do_login(email, password)
            else:
                token = yield self._show_ui(login_only)

        defer.returnValue(token)

    @handle_failures(msg='Problem while getting credentials from the keyring')
    @defer.inlineCallbacks
    def find_credentials(self):
        """Get the credentials for 'self.app_name'. Return {} if not there."""
        creds = yield Keyring().get_credentials(self.app_name)
        logger.info('find_credentials: self.app_name %r, '
                    'result is {}? %s', self.app_name, creds is None)
        defer.returnValue(creds if creds is not None else {})

    @handle_failures(msg='Problem while clearing credentials in the keyring')
    def clear_credentials(self):
        """Clear the credentials for 'self.app_name'."""
        return Keyring().delete_credentials(self.app_name)

    @handle_failures(msg='Problem while storing credentials in the keyring')
    def store_credentials(self, token):
        """Store the credentials for 'self.app_name'."""
        return Keyring().set_credentials(self.app_name, token)

    @handle_failures(msg='Problem while performing register')
    def register(self):
        """Get credentials if found else prompt the GUI to register."""
        return self._login_or_register(login_only=False)

    @handle_failures(msg='Problem while performing login')
    def login(self, email=None, password=None):
        """Get credentials if found else prompt the GUI to login.

        if 'email' and 'password' are given, do not prompt the user and use
        that to retrieve a token.

        """
        if email is None or password is None:
            return self._login_or_register(login_only=True)
        else:
            return self._login_or_register(login_only=True,
                                           email=email, password=password)
