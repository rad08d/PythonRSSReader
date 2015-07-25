# -*- coding: utf-8 -*-
#
# Copyright 2012 Canonical Ltd.
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
"""Generic SSO client using Twisted Perspective Broker.

This module should never import from the multiplatform one (main/__init__.py),
but the other way around. Likewise, this module should *not* have any logic
regarding error processing or decision making about when to send a given
signal.

Also, most of the logging is being made in the main module to avoid
duplication between the different platform implementations.

"""

from twisted.internet.task import LoopingCall
from twisted.python.failure import Failure

from ubuntu_sso.logger import setup_logging
from ubuntu_sso.utils.ipc import (
    BaseService,
    RemoteClient,
    RemoteService,
    signal,
)

logger = setup_logging("ubuntu_sso.main.perspective_broker")
SSO_SERVICE_NAME = "ubuntu-sso-client"

# Invalid name for signals that are CamelCase
# pylint: disable=C0103


class SSOLoginProxy(RemoteService):
    """Login thru the Single Sign On service."""

    remote_calls = [
        'generate_captcha',
        'register_user',
        'login',
        'login_and_ping',
        'validate_email',
        'validate_email_and_ping',
        'request_password_reset_token',
        'set_new_password',
    ]

    def __init__(self, root, *args, **kwargs):
        super(SSOLoginProxy, self).__init__(*args, **kwargs)
        self.root = root

    # generate_capcha signals
    @signal
    def CaptchaGenerated(self, app_name, result):
        """Signal thrown after the captcha is generated."""

    @signal
    def CaptchaGenerationError(self, app_name, error):
        """Signal thrown when there's a problem generating the captcha."""

    def generate_captcha(self, app_name, filename):
        """Call the matching method in the processor."""
        self.root.sso_login.generate_captcha(app_name, filename)

    # register_user signals
    @signal
    def UserRegistered(self, app_name, result):
        """Signal thrown when the user is registered."""

    @signal
    def UserRegistrationError(self, app_name, error):
        """Signal thrown when there's a problem registering the user."""

    def register_user(self, app_name, email, password, name,
                      captcha_id, captcha_solution):
        """Call the matching method in the processor."""
        self.root.sso_login.register_user(app_name, email, password, name,
            captcha_id, captcha_solution)

    # login signals
    @signal
    def LoggedIn(self, app_name, result):
        """Signal thrown when the user is logged in."""

    @signal
    def LoginError(self, app_name, error):
        """Signal thrown when there is a problem in the login."""

    @signal
    def UserNotValidated(self, app_name, result):
        """Signal thrown when the user is not validated."""

    def login(self, app_name, email, password, ping_url=None):
        """Call the matching method in the processor."""
        self.root.sso_login.login(app_name, email, password, ping_url)

    login_and_ping = login

    # validate_email signals
    @signal
    def EmailValidated(self, app_name, result):
        """Signal thrown after the email is validated."""

    @signal
    def EmailValidationError(self, app_name, error):
        """Signal thrown when there's a problem validating the email."""

    def validate_email(self, app_name, email, password, email_token,
                       ping_url=None):
        """Call the matching method in the processor."""
        self.root.sso_login.validate_email(app_name,
            email, password, email_token, ping_url)

    validate_email_and_ping = validate_email

    # request_password_reset_token signals
    @signal
    def PasswordResetTokenSent(self, app_name, result):
        """Signal thrown when the token is succesfully sent."""

    @signal
    def PasswordResetError(self, app_name, error):
        """Signal thrown when there's a problem sending the token."""

    def request_password_reset_token(self, app_name, email):
        """Call the matching method in the processor."""
        self.root.sso_login.request_password_reset_token(app_name, email)

    # set_new_password signals
    @signal
    def PasswordChanged(self, app_name, result):
        """Signal thrown when the token is succesfully sent."""

    @signal
    def PasswordChangeError(self, app_name, error):
        """Signal thrown when there's a problem sending the token."""

    def set_new_password(self, app_name, email, token, new_password):
        """Call the matching method in the processor."""
        self.root.sso_login.set_new_password(app_name,
            email, token, new_password)


class CredentialsManagementProxy(RemoteService):
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

    remote_calls = [
        'find_credentials',
        'clear_credentials',
        'store_credentials',
        'register',
        'login',
        'login_email_password',
    ]

    def __init__(self, root, *args, **kwargs):
        super(CredentialsManagementProxy, self).__init__(*args, **kwargs)
        self.root = root

    @signal
    def AuthorizationDenied(self, app_name):
        """Signal thrown when the user denies the authorization."""

    @signal
    def CredentialsFound(self, app_name, credentials):
        """Signal thrown when the credentials are found."""

    @signal
    def CredentialsNotFound(self, app_name):
        """Signal thrown when the credentials are not found."""

    @signal
    def CredentialsCleared(self, app_name):
        """Signal thrown when the credentials were cleared."""

    @signal
    def CredentialsStored(self, app_name):
        """Signal thrown when the credentials were cleared."""

    @signal
    def CredentialsError(self, app_name, error_dict):
        """Signal thrown when there is a problem getting the credentials."""

    def find_credentials(self, app_name, args):
        """Look for the credentials for an application.

        - 'app_name': the name of the application which credentials are
        going to be removed.

        - 'args' is a dictionary, currently not used.

        """
        self.root.cred_manager.find_credentials(app_name, args)

    def clear_credentials(self, app_name, args):
        """Clear the credentials for an application.

        - 'app_name': the name of the application which credentials are
        going to be removed.

        - 'args' is a dictionary, currently not used.

        """
        self.root.cred_manager.clear_credentials(app_name, args)

    def store_credentials(self, app_name, args):
        """Store the token for an application.

        - 'app_name': the name of the application which credentials are
        going to be stored.

        - 'args' is the dictionary holding the credentials. Needs to provide
        the following mandatory keys: 'token', 'token_key', 'consumer_key',
        'consumer_secret'.

        """
        self.root.cred_manager.store_credentials(app_name, args)

    def register(self, app_name, args):
        """Get credentials if found else prompt GUI to register."""
        self.root.cred_manager.register(app_name, args)

    def login(self, app_name, args):
        """Get credentials if found else prompt GUI to login."""
        self.root.cred_manager.login(app_name, args)

    def login_email_password(self, app_name, args):
        """Get credentials if found, else login using email and password.

        - 'args' should contain at least the follwing keys: 'email' and
        'password'. Those will be used to issue a new SSO token, which will be
        returned trough the CredentialsFound signal.

        """
        self.root.cred_manager.login_email_password(app_name, args)


class UbuntuSSOProxyBase(BaseService):
    """Object that exposes the diff referenceable objects."""

    services = {
        'sso_login': SSOLoginProxy,
        'cred_manager': CredentialsManagementProxy,
    }

    name = SSO_SERVICE_NAME


# ============================== client classes ==============================


class SSOLoginClient(RemoteClient):
    """Client that can perform calls to the remote SSOLogin object."""

    call_remote_functions = SSOLoginProxy.remote_calls
    signal_handlers = [
        'CaptchaGenerated',
        'CaptchaGenerationError',
        'UserRegistered',
        'UserRegistrationError',
        'LoggedIn',
        'LoginError',
        'UserNotValidated',
        'EmailValidated',
        'EmailValidationError',
        'PasswordResetTokenSent',
        'PasswordResetError',
        'PasswordChanged',
        'PasswordChangeError',
    ]


class CredentialsManagementClient(RemoteClient):
    """Client that can perform calls to the remote CredManagement object."""

    call_remote_functions = CredentialsManagementProxy.remote_calls
    signal_handlers = [
        'AuthorizationDenied',
        'CredentialsFound',
        'CredentialsNotFound',
        'CredentialsCleared',
        'CredentialsStored',
        'CredentialsError',
    ]


def add_timeout(interval, callback, *args, **kwargs):
    """Add a timeout callback as a task."""
    time_out_task = LoopingCall(callback, *args, **kwargs)
    time_out_task.start(interval / 1000, now=False)


timeout_func = add_timeout
start_setup = lambda *a, **kw: None

# the reactor does have run and stop methods
# pylint: disable=E1101


def shutdown_func():
    """Stop the reactor."""
    from twisted.internet import reactor
    reactor.stop()


def finish_setup(result, loop):
    """Stop the reactor if a failure ocurred."""
    if isinstance(result, Failure):
        shutdown_func()


def main():
    """Run the specific mainloop."""
    from twisted.internet import reactor
    reactor.run()

# pylint: enable=E1101
