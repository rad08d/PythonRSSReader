# -*- coding: utf-8 -*-
#
# Copyright 2010-2013 Canonical Ltd.
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
"""Single Sign On account management.

All the methods in Account expect unicode as parameters.

"""

from __future__ import unicode_literals

import os
import re

from twisted.internet import defer

from ubuntu_sso import SSO_AUTH_BASE_URL
from ubuntu_sso.logger import setup_logging
from ubuntu_sso.utils import compat, webclient
from ubuntu_sso.utils.webclient import restful
from ubuntu_sso.utils.webclient.common import WebClientError


logger = setup_logging("ubuntu_sso.account")
SERVICE_URL = "%s/api/1.0/" % SSO_AUTH_BASE_URL
SSO_STATUS_OK = 'ok'
SSO_STATUS_ERROR = 'error'


class InvalidEmailError(Exception):
    """The email is not valid."""


class InvalidPasswordError(Exception):
    """The password is not valid.

    Must provide at least 8 characters, one upper case, one number.
    """


class RegistrationError(Exception):
    """The registration failed."""


class AuthenticationError(Exception):
    """The authentication failed."""


class EmailTokenError(Exception):
    """The email token is not valid."""


class ResetPasswordTokenError(Exception):
    """The token for password reset could not be generated."""


class NewPasswordError(Exception):
    """The new password could not be set."""


class Account(object):
    """Login and register users using the Ubuntu Single Sign On service."""

    def __init__(self, service_url=None):
        """Create a new SSO Account manager."""
        if service_url is not None:
            self.service_url = service_url
        else:
            self.service_url = os.environ.get('USSOC_SERVICE_URL', SERVICE_URL)
        logger.info('Creating a new SSO access layer for service url %r',
                     self.service_url)
        assert self.service_url.endswith("/")

    def _valid_email(self, email):
        """Validate the given email."""
        return email is not None and '@' in email

    def _valid_password(self, password):
        """Validate the given password."""
        res = (len(password) > 7 and  # at least 8 characters
               re.search('[A-Z]', password) and  # one upper case
               re.search('\d+', password))  # one number
        return res

    def _format_webservice_errors(self, errdict):
        """Turn each list of strings in the errdict into a LF separated str."""
        result = {}
        for key, val in errdict.items():
            # workaround until bug #624955 is solved
            if isinstance(val, compat.basestring):
                result[key] = val
            else:
                result[key] = "\n".join(val)
        return result

    @defer.inlineCallbacks
    def generate_captcha(self, filename):
        """Generate a captcha using the SSO service."""
        logger.debug('generate_captcha: requesting captcha, filename: %r',
                     filename)
        restful_client = restful.RestfulClient(self.service_url)
        try:
            captcha = yield restful_client.restcall("captchas.new")
        finally:
            restful_client.shutdown()

        # download captcha and save to 'filename'
        logger.debug('generate_captcha: server answered: %r', captcha)
        wc = webclient.webclient_factory()
        try:
            response = yield wc.request(captcha['image_url'])
            with open(filename, 'wb') as f:
                f.write(response.content)
        except:
            msg = 'generate_captcha crashed while downloading the image.'
            logger.exception(msg)
            raise
        finally:
            wc.shutdown()

        defer.returnValue(captcha['captcha_id'])

    @defer.inlineCallbacks
    def register_user(self, email, password, displayname,
                      captcha_id, captcha_solution):
        """Register a new user with 'email' and 'password'."""
        logger.debug('register_user: email: %r password: <hidden>, '
                     'displayname: %r, captcha_id: %r, captcha_solution: %r',
                     email, displayname, captcha_id, captcha_solution)
        restful_client = restful.RestfulClient(self.service_url)
        try:
            if not self._valid_email(email):
                logger.error('register_user: InvalidEmailError for email: %r',
                             email)
                raise InvalidEmailError()
            if not self._valid_password(password):
                logger.error('register_user: InvalidPasswordError')
                raise InvalidPasswordError()

            result = yield restful_client.restcall("registration.register",
                        email=email, password=password,
                        displayname=displayname,
                        captcha_id=captcha_id,
                        captcha_solution=captcha_solution)
        finally:
            restful_client.shutdown()
        logger.info('register_user: email: %r result: %r', email, result)

        if result['status'].lower() == SSO_STATUS_ERROR:
            errorsdict = self._format_webservice_errors(result['errors'])
            raise RegistrationError(errorsdict)
        elif result['status'].lower() != SSO_STATUS_OK:
            raise RegistrationError('Received unknown status: %s' % result)
        else:
            defer.returnValue(email)

    @defer.inlineCallbacks
    def login(self, email, password, token_name):
        """Login a user with 'email' and 'password'."""
        logger.debug('login: email: %r password: <hidden>, token_name: %r',
                     email, token_name)
        restful_client = restful.RestfulClient(self.service_url,
                                               username=email,
                                               password=password)
        try:
            credentials = yield restful_client.restcall(
                        "authentications.authenticate",
                        token_name=token_name)
        except WebClientError:
            logger.exception('login failed with:')
            raise AuthenticationError()
        finally:
            restful_client.shutdown()

        logger.debug('login: authentication successful! consumer_key: %r, '
                     'token_name: %r', credentials['consumer_key'], token_name)
        defer.returnValue(credentials)

    @defer.inlineCallbacks
    def is_validated(self, token):
        """Return if user with 'email' and 'password' is validated."""
        logger.debug('is_validated: requesting accounts.me() info.')
        restful_client = restful.RestfulClient(self.service_url,
                                               oauth_credentials=token)
        try:
            me_info = yield restful_client.restcall("accounts.me")
        finally:
            restful_client.shutdown()
        key = 'preferred_email'
        result = key in me_info and me_info[key] is not None

        logger.info('is_validated: consumer_key: %r, result: %r.',
                    token['consumer_key'], result)
        defer.returnValue(result)

    @defer.inlineCallbacks
    def validate_email(self, email, password, email_token, token_name):
        """Validate an email token for user with 'email' and 'password'."""
        logger.debug('validate_email: email: %r password: <hidden>, '
                     'email_token: %r, token_name: %r.',
                     email, email_token, token_name)
        credentials = yield self.login(email=email, password=password,
                                       token_name=token_name)
        restful_client = restful.RestfulClient(self.service_url,
                                               oauth_credentials=credentials)
        try:
            result = yield restful_client.restcall("accounts.validate_email",
                                                   email_token=email_token)
        finally:
            restful_client.shutdown()
        logger.info('validate_email: email: %r result: %r', email, result)
        if 'errors' in result:
            errorsdict = self._format_webservice_errors(result['errors'])
            raise EmailTokenError(errorsdict)
        elif 'email' in result:
            defer.returnValue(credentials)
        else:
            raise EmailTokenError('Received invalid reply: %s' % result)

    @defer.inlineCallbacks
    def request_password_reset_token(self, email):
        """Request a token to reset the password for the account 'email'."""
        restful_client = restful.RestfulClient(self.service_url)
        try:
            operation = "registration.request_password_reset_token"
            result = yield restful_client.restcall(operation, email=email)
        except WebClientError as e:
            logger.exception('request_password_reset_token failed with:')
            raise ResetPasswordTokenError(e[1].split('\n')[0])
        finally:
            restful_client.shutdown()

        if result['status'].lower() == SSO_STATUS_OK:
            defer.returnValue(email)
        else:
            raise ResetPasswordTokenError('Received invalid reply: %s' %
                                          result)

    @defer.inlineCallbacks
    def set_new_password(self, email, token, new_password):
        """Set a new password for the account 'email' to be 'new_password'.

        The 'token' has to be the one resulting from a call to
        'request_password_reset_token'.

        """
        restful_client = restful.RestfulClient(self.service_url)
        try:
            result = yield restful_client.restcall(
                                        "registration.set_new_password",
                                        email=email, token=token,
                                        new_password=new_password)
        except WebClientError as e:
            logger.exception('set_new_password failed with:')
            raise NewPasswordError(e[1].split('\n')[0])
        finally:
            restful_client.shutdown()

        if result['status'].lower() == SSO_STATUS_OK:
            defer.returnValue(email)
        else:
            raise NewPasswordError('Received invalid reply: %s' % result)
