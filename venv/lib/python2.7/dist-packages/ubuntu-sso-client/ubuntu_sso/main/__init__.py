# -*- coding: utf-8 -*-
#
# Copyright 2011-2012 Canonical Ltd.
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
"""Single Sign On client main module.

Provides a utility which accepts requests to the Ubuntu Single Sign On
service. The OAuth process is handled, including adding the OAuth access token
to the local keyring.

"""

import sys

from twisted.internet import defer

from ubuntu_sso import utils
from ubuntu_sso.account import Account
from ubuntu_sso.credentials import (
    Credentials,
    HELP_TEXT_KEY,
    PING_URL_KEY,
    POLICY_URL_KEY,
    TC_URL_KEY,
    UI_EXECUTABLE_KEY,
    UserCancellationError,
    WINDOW_ID_KEY,
)
from ubuntu_sso.keyring import get_token_name, Keyring
from ubuntu_sso.logger import setup_logging, log_call
from ubuntu_sso.utils import compat


logger = setup_logging("ubuntu_sso.main")
TIMEOUT_INTERVAL = 10000  # 10 seconds

# pylint: disable=C0103, W0703, W0621

if sys.platform == 'win32':
    from ubuntu_sso.main import windows as source
    from ubuntu_sso.main.perspective_broker import (
        finish_setup,
        main as main_func,
        timeout_func,
        shutdown_func,
        start_setup,
    )

    source.finish_setup = finish_setup
    source.timeout_func = timeout_func
    source.shutdown_func = shutdown_func
    source.start_setup = start_setup
    source.main = main_func

    TIMEOUT_INTERVAL = 10000000000  # forever (hack)
elif sys.platform == 'darwin':
    from ubuntu_sso.main import darwin as source
    from ubuntu_sso.main.perspective_broker import (
        finish_setup,
        main as main_func,
        timeout_func,
        shutdown_func,
        start_setup,
    )

    source.finish_setup = finish_setup
    source.timeout_func = timeout_func
    source.shutdown_func = shutdown_func
    source.start_setup = start_setup
    source.main = main_func
else:
    from ubuntu_sso.main import linux as source


UbuntuSSOClient = source.UbuntuSSOClient
UbuntuSSOProxy = source.UbuntuSSOProxy
get_sso_client = source.get_sso_client


def except_to_errdict(e):
    """Turn an exception into a dictionary to return thru IPC."""
    result = {
        "errtype": e.__class__.__name__,
    }
    if len(e.args) == 0:
        result["message"] = e.__class__.__doc__
    elif isinstance(e.args[0], dict):
        result.update(e.args[0])
    elif isinstance(e.args[0], compat.basestring):
        result["message"] = e.args[0]

    return result


class SSOLogin(object):
    """Login thru the Single Sign On service."""

    def __init__(self, proxy):
        """Initiate the Login object."""
        self.processor = Account()
        self.proxy = proxy

    @defer.inlineCallbacks
    def _process_new_token(self, app_name, email, credentials, ping_url):
        """Process a new set of credentials for 'email'."""
        if ping_url:
            yield utils.ping_url(ping_url, email, credentials)
            logger.info('Url %r successfully opened!', ping_url)

        yield Keyring().set_credentials(app_name, credentials)

    @log_call(logger.debug)
    def CaptchaGenerated(self, app_name, result):
        """Signal thrown after the captcha is generated."""
        self.proxy.CaptchaGenerated(app_name, result)

    @log_call(logger.debug)
    def CaptchaGenerationError(self, app_name, error):
        """Signal thrown when there's a problem generating the captcha."""
        error_dict = except_to_errdict(error)
        self.proxy.CaptchaGenerationError(app_name, error_dict)

    @defer.inlineCallbacks
    def generate_captcha(self, app_name, filename):
        """Call the matching method in the processor."""
        try:
            result = yield self.processor.generate_captcha(filename)
            self.CaptchaGenerated(app_name, result)
        except Exception as e:
            self.CaptchaGenerationError(app_name, e)

    @log_call(logger.debug)
    def UserRegistered(self, app_name, result):
        """Signal thrown when the user is registered."""
        self.proxy.UserRegistered(app_name, result)

    @log_call(logger.debug)
    def UserRegistrationError(self, app_name, error):
        """Signal thrown when there's a problem registering the user."""
        error_dict = except_to_errdict(error)
        self.proxy.UserRegistrationError(app_name, error_dict)

    @defer.inlineCallbacks
    def register_user(self, app_name, email, password, name, captcha_id,
                      captcha_solution):
        """Call the matching method in the processor."""
        try:
            result = yield self.processor.register_user(email, password, name,
                                                captcha_id, captcha_solution)
            self.UserRegistered(app_name, result)
        except Exception as e:
            self.UserRegistrationError(app_name, e)

    @log_call(logger.debug)
    def LoggedIn(self, app_name, result):
        """Signal thrown when the user is logged in."""
        self.proxy.LoggedIn(app_name, result)

    @log_call(logger.debug)
    def LoginError(self, app_name, error):
        """Signal thrown when there is a problem in the login."""
        error_dict = except_to_errdict(error)
        self.proxy.LoginError(app_name, error_dict)

    @log_call(logger.debug)
    def UserNotValidated(self, app_name, email):
        """Signal thrown when the user is not validated."""
        self.proxy.UserNotValidated(app_name, email)

    @defer.inlineCallbacks
    def login(self, app_name, email, password, ping_url=None):
        """Call the matching method in the processor."""
        try:
            token_name = get_token_name(app_name)
            logger.debug('login: token_name %r, email %r, password <hidden>.',
                         token_name, email)
            credentials = yield self.processor.login(email, password,
                                                     token_name)
            logger.debug('login returned not None credentials? %r.',
                         credentials is not None)
            is_validated = yield self.processor.is_validated(credentials)
            logger.debug('user is validated? %r.', is_validated)
            if is_validated:
                yield self._process_new_token(app_name, email,
                                              credentials, ping_url)
                self.LoggedIn(app_name, email)
            else:
                self.UserNotValidated(app_name, email)
        except Exception as e:
            self.LoginError(app_name, e)

    @log_call(logger.debug)
    def EmailValidated(self, app_name, result):
        """Signal thrown after the email is validated."""
        self.proxy.EmailValidated(app_name, result)

    @log_call(logger.debug)
    def EmailValidationError(self, app_name, error):
        """Signal thrown when there's a problem validating the email."""
        error_dict = except_to_errdict(error)
        self.proxy.EmailValidationError(app_name, error_dict)

    @defer.inlineCallbacks
    def validate_email(self, app_name, email, password, email_token,
                       ping_url=None):
        """Call the matching method in the processor."""
        try:
            token_name = get_token_name(app_name)
            credentials = yield self.processor.validate_email(email, password,
                                                      email_token, token_name)
            yield self._process_new_token(app_name, email,
                                          credentials, ping_url)
            self.EmailValidated(app_name, email)
        except Exception as e:
            self.EmailValidationError(app_name, e)

    @log_call(logger.debug)
    def PasswordResetTokenSent(self, app_name, result):
        """Signal thrown when the token is succesfully sent."""
        self.proxy.PasswordResetTokenSent(app_name, result)

    @log_call(logger.debug)
    def PasswordResetError(self, app_name, error):
        """Signal thrown when there's a problem sending the token."""
        error_dict = except_to_errdict(error)
        self.proxy.PasswordResetError(app_name, error_dict)

    @defer.inlineCallbacks
    def request_password_reset_token(self, app_name, email):
        """Call the matching method in the processor."""
        try:
            result = yield self.processor.request_password_reset_token(email)
            self.PasswordResetTokenSent(app_name, result)
        except Exception as e:
            self.PasswordResetError(app_name, e)

    @log_call(logger.debug)
    def PasswordChanged(self, app_name, result):
        """Signal thrown when the token is succesfully sent."""
        self.proxy.PasswordChanged(app_name, result)

    @log_call(logger.debug)
    def PasswordChangeError(self, app_name, error):
        """Signal thrown when there's a problem sending the token."""
        error_dict = except_to_errdict(error)
        self.proxy.PasswordChangeError(app_name, error_dict)

    @defer.inlineCallbacks
    def set_new_password(self, app_name, email, token, new_password):
        """Call the matching method in the processor."""
        try:
            result = yield self.processor.set_new_password(email, token,
                                                           new_password)
            self.PasswordChanged(app_name, result)
        except Exception as e:
            self.PasswordChangeError(app_name, e)


class CredentialsManagement(object):
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

    def __init__(self, timeout_func, shutdown_func, proxy):
        super(CredentialsManagement, self).__init__()
        self._ref_count = 0
        self.timeout_func = timeout_func
        self.shutdown_func = shutdown_func
        self.proxy = proxy

    def _get_ref_count(self):
        """Get value of ref_count."""
        return self._ref_count

    def _set_ref_count(self, new_value):
        """Set a new value to ref_count."""
        logger.debug('ref_count is %r, changing value to %r.',
                     self._ref_count, new_value)
        if new_value < 0:
            self._ref_count = 0
            msg = 'Attempting to decrease ref_count to a negative value (%r).'
            logger.warning(msg, new_value)
        else:
            self._ref_count = new_value

        if self._ref_count == 0:
            logger.debug('Setting up timer with %r (%r, %r).',
                         self.timeout_func, TIMEOUT_INTERVAL, self.shutdown)
            self.timeout_func(TIMEOUT_INTERVAL, self.shutdown)

    ref_count = property(fget=_get_ref_count, fset=_set_ref_count)

    def shutdown(self):
        """If no ongoing requests, call self.shutdown_func."""
        logger.debug('shutdown!, ref_count is %r.', self._ref_count)
        if self._ref_count == 0:
            logger.info('Shutting down, calling %r.', self.shutdown_func)
            self.shutdown_func()

    valid_keys = (HELP_TEXT_KEY, PING_URL_KEY, POLICY_URL_KEY, TC_URL_KEY,
                  UI_EXECUTABLE_KEY, WINDOW_ID_KEY)

    def _parse_args(self, args):
        """Retrieve values from the generic param 'args'."""
        result = dict(i for i in args.items() if i[0] in self.valid_keys)
        result[WINDOW_ID_KEY] = int(args.get(WINDOW_ID_KEY, 0))
        return result

    @log_call(logger.info)
    def AuthorizationDenied(self, app_name):
        """Signal thrown when the user denies the authorization."""
        self.ref_count -= 1
        self.proxy.AuthorizationDenied(app_name)

    # do not use log_call decorator since we should not log credentials
    def CredentialsFound(self, app_name, credentials):
        """Signal thrown when the credentials are found."""
        self.ref_count -= 1
        logger.info('%s: emitting CredentialsFound with app_name %r.',
                    self.__class__.__name__, app_name)
        self.proxy.CredentialsFound(app_name, credentials)

    @log_call(logger.info)
    def CredentialsNotFound(self, app_name):
        """Signal thrown when the credentials are not found."""
        self.ref_count -= 1
        self.proxy.CredentialsNotFound(app_name)

    @log_call(logger.info)
    def CredentialsCleared(self, app_name):
        """Signal thrown when the credentials were cleared."""
        self.ref_count -= 1
        self.proxy.CredentialsCleared(app_name)

    @log_call(logger.info)
    def CredentialsStored(self, app_name):
        """Signal thrown when the credentials were cleared."""
        self.ref_count -= 1
        self.proxy.CredentialsStored(app_name)

    @log_call(logger.error)
    def CredentialsError(self, app_name, error):
        """Signal thrown when there is a problem getting the credentials."""
        self.ref_count -= 1
        if isinstance(error, dict):
            error_dict = error
        else:
            error_dict = except_to_errdict(error)
        self.proxy.CredentialsError(app_name, error_dict)

    def find_credentials(self, app_name, args, success_cb=None, error_cb=None):
        """Look for the credentials for an application.

        - 'app_name': the name of the application which credentials are
        going to be removed.

        - 'args' is a dictionary, currently not used.

        - 'success_cb', if not None, will be executed if the operation was
        a success.

        - 'error_cb', if not None, will be executed if the operation had
        an error.

        """
        def _analize_creds(credentials):
            """Find credentials and notify using signals."""
            if credentials is not None and len(credentials) > 0:
                self.CredentialsFound(app_name, credentials)
            else:
                self.CredentialsNotFound(app_name)

        def _tweaked_success_cb(creds):
            """Decrease ref counter and call 'success_cb'."""
            self.ref_count -= 1
            success_cb(creds)

        if success_cb is None:
            _success_cb = _analize_creds
        else:
            _success_cb = _tweaked_success_cb

        def _tweaked_error_cb(error, app):
            """Decrease ref counter and call 'error_cb', modifying the dict."""
            self.ref_count -= 1
            error_cb(except_to_errdict(error.value))

        if error_cb is None:
            _error_cb = lambda f, _: self.CredentialsError(app_name, f.value)
        else:
            _error_cb = _tweaked_error_cb

        self.ref_count += 1
        obj = Credentials(app_name)
        d = obj.find_credentials()
        d.addCallback(_success_cb)
        d.addErrback(_error_cb, app_name)

    def _process_failures(self, failure, app_name):
        """Process failure returned by the Credentials module."""
        if failure.check(UserCancellationError):
            self.AuthorizationDenied(app_name)
        else:
            self.CredentialsError(app_name, failure.value)

    def clear_credentials(self, app_name, args):
        """Clear the credentials for an application.

        - 'app_name': the name of the application which credentials are
        going to be removed.

        - 'args' is a dictionary, currently not used.

        """
        self.ref_count += 1
        obj = Credentials(app_name)
        d = obj.clear_credentials()
        d.addCallback(lambda _: self.CredentialsCleared(app_name))
        d.addErrback(lambda f: self.CredentialsError(app_name, f.value))

    def store_credentials(self, app_name, args):
        """Store the token for an application.

        - 'app_name': the name of the application which credentials are
        going to be stored.

        - 'args' is the dictionary holding the credentials. Needs to provide
        the following mandatory keys: 'token', 'token_key', 'consumer_key',
        'consumer_secret'.

        """
        self.ref_count += 1
        obj = Credentials(app_name)
        d = obj.store_credentials(args)
        d.addCallback(lambda _: self.CredentialsStored(app_name))
        d.addErrback(lambda f: self.CredentialsError(app_name, f.value))

    def register(self, app_name, args):
        """Get credentials if found else prompt GUI to register."""
        self.ref_count += 1
        obj = Credentials(app_name, **self._parse_args(args))
        d = obj.register()
        d.addCallback(lambda creds: self.CredentialsFound(app_name, creds))
        d.addErrback(self._process_failures, app_name)

    def login(self, app_name, args):
        """Get credentials if found else prompt GUI to login."""
        self.ref_count += 1
        obj = Credentials(app_name, **self._parse_args(args))
        d = obj.login()
        d.addCallback(lambda creds: self.CredentialsFound(app_name, creds))
        d.addErrback(self._process_failures, app_name)

    def login_email_password(self, app_name, args):
        """Get credentials if found else try to login.

        Login will be done by inspecting 'args' and expecting to find two keys:
        'email' and 'password'.

        """
        self.ref_count += 1
        email = args.pop('email')
        password = args.pop('password')
        obj = Credentials(app_name, **self._parse_args(args))
        d = obj.login(email=email, password=password)
        d.addCallback(lambda creds: self.CredentialsFound(app_name, creds))
        d.addErrback(self._process_failures, app_name)


# pylint: enable=C0103

class UbuntuSSOService(object):
    """Manager that exposes the diff referenceable objects."""

    def __init__(self):
        self.proxy = UbuntuSSOProxy(self)
        self.sso_login = None
        self.cred_manager = None

    @defer.inlineCallbacks
    def start(self):
        """Start the service."""
        logger.debug('Starting up Ubuntu SSO service...')
        try:
            yield self.proxy.start()
        except:
            logger.exception('Can not start Ubuntu SSO service:')
            raise
        else:
            logger.info('Ubuntu SSO service started.')

        self.sso_login = SSOLogin(proxy=self.proxy.sso_login)
        self.cred_manager = CredentialsManagement(
                                timeout_func=source.timeout_func,
                                shutdown_func=source.shutdown_func,
                                proxy=self.proxy.cred_manager)

    def shutdown(self):
        """Shutdown the service."""
        return self.proxy.shutdown()


def main():
    """Run the backend service."""
    logger.info('Setting up Ubuntu SSO service.')
    loop = source.start_setup()
    service = UbuntuSSOService()
    d = service.start()
    d.addBoth(source.finish_setup, loop)
    source.main()
