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
"""Utils to be used by the UI modules."""

import argparse
import os
import re

from ubuntu_sso.logger import setup_logging

from ubuntu_sso.utils.translation import get_gettext

source_path = os.path.join(os.path.dirname(__file__),
                           os.path.pardir, os.path.pardir,
                           'build', 'mo')
_ = get_gettext('ubuntu-sso-client',
                fallback_path=os.path.abspath(source_path))

logger = setup_logging('ubuntu_sso.utils.ui')


# Undefined variable '_', pylint: disable=E0602

# all the text that is used in the gui
AGREE_TO_PRIVACY_POLICY = _('By signing up to {app_name} you agree to '
    'our {privacy_policy}')
AGREE_TO_TERMS = _('By signing up to {app_name} you agree to '
    'our {terms_and_conditions}')
AGREE_TO_TERMS_AND_PRIVACY_POLICY = AGREE_TO_TERMS + _(' and {privacy_policy}')
CANCEL_BUTTON = _('Cancel')
CAPTCHA_SOLUTION_ENTRY = _('Type the characters above')
CAPTCHA_LOAD_ERROR = _('There was a problem getting the captcha, '
                       'reloading...')
CAPTCHA_RELOAD_MESSAGE = _('If you can\'t read this then %(reload_link)s '
    'this page')
CAPTCHA_RELOAD_TEXT = _('refresh')
CAPTCHA_RELOAD_TOOLTIP = _('Reload')
CAPTCHA_REQUIRED_ERROR = _('The captcha is a required field')
CLOSE_AND_SETUP_LATER = _('Close window and set up later')
CONGRATULATIONS = _("Congratulations, {app_name} is installed!")
CONNECT_HELP_LABEL = _('To connect this computer to %(app_name)s enter your '
    'details below.')
CREATE_ACCOUNT_LABEL = _('Register with {app_name}.')
EMAIL_LABEL = EMAIL1_ENTRY = _('Email address')
EMAIL2_ENTRY = _('Re-type Email address')
EMAIL_INVALID = _('The email must be a valid email address.')
EMAIL_MISMATCH = _('The email addresses don\'t match, please double check '
                   'and try entering them again.')
EMAIL = _("Email")
EMAIL_MATCH = _("The email addresses do not match")
EMAIL_TOKEN_ENTRY = _('Enter code verification here')
EMPTY_NAME = _("Please enter your name")
ERROR = _('The process did not finish successfully.')
ERROR_EMAIL_TOKEN = 'email_token'
EXISTING_ACCOUNT_CHOICE_BUTTON = _('Sign me in with my existing account')
FIELD_REQUIRED = _('This field is required.')
FORGOTTEN_PASSWORD_BUTTON = _('I\'ve forgotten my password')
FORGOTTEN_PASSWORD_TITLE = _('Reset password')
FORGOTTEN_PASSWORD_SUBTITLE = _('To reset your {app_name} password, enter '
    'your registered email address below. We will send instructions to reset '
    'your password.')
INVALID_EMAIL = _("Please enter a valid email address")
GENERIC_BACKEND_ERROR = _('There was a problem accessing the Ubuntu'
                          ' One backend.')
JOIN_HEADER_LABEL = _('Create %(app_name)s account')
LOADING = _('Loading...')
LOADING_OVERLAY = _('Getting information, please wait...')
LOGIN_BUTTON_LABEL = _('Already have an account? Click here to sign in')
LOGIN_EMAIL_ENTRY = _('Email address')
LOGIN_HEADER_LABEL = _('Connect to %(app_name)s')
LOGIN_PASSWORD_ENTRY = _('Password')
LOGIN_PASSWORD_LABEL = LOGIN_PASSWORD_ENTRY
LOGIN_TITLE = _('Sign In to {app_name}')
LOGIN_SUBTITLE = CONNECT_HELP_LABEL
NAME_ENTRY = _('Name')
NAME_INVALID = _('The name must not be empty.')
NEXT = _('Next')
NETWORK_DETECTION_TITLE = _('Network detection')
NETWORK_DETECTION_WARNING = _('Are you online? We can\'t detect an internet '
    'connection - you will need to be connected to set up %(app_name)s')
ONE_MOMENT_PLEASE = _('One moment please...')
PASSWORD = _("Create a password")
PASSWORD_CHANGED = _('Your password was successfully changed.')
PASSWORD_DIGIT = _("At least one number")
PASSWORD1_ENTRY = RESET_PASSWORD1_ENTRY = _('Password')
PASSWORD2_ENTRY = RESET_PASSWORD2_ENTRY = _('Re-type Password')
PASSWORD_HELP = _('The password must have a minimum of 8 characters and '
    'include one uppercase character and one number.')
PASSWORD_LENGTH = _("At least 8 characters")
PASSWORD_MATCH = _("Passwords don't match")
PASSWORD_MISMATCH = _('The passwords don\'t match, please double check '
    'and try entering them again.')
PASSWORD_MUST_CONTAIN = _("Your password must contain")
PASSWORD_TOO_WEAK = _('The password is too weak.')
PASSWORD_UPPER = _("At least one uppercase letter")
PRIVACY_POLICY_TEXT = _("Privacy Policy")
PROXY_CREDS_CONNECTION = _('Connecting to:')
PROXY_CREDS_DIALOG_TITLE = _('Proxy Settings')
PROXY_CREDS_ERROR = _('Incorrect login details. Please try again.')
PROXY_CREDS_EXPLANATION = _('Please provide login details.')
PROXY_CREDS_HEADER = _('You are connecting through a proxy.')
PROXY_CREDS_HELP_BUTTON = _('Get Help With Proxies')
PROXY_CREDS_PSWD_LABEL = _('Proxy password:')
PROXY_CREDS_SAVE_BUTTON = _('Save and Connect')
PROXY_CREDS_USER_LABEL = _('Proxy username:')
RESET_TITLE = _("Reset password")
RESET_SUBTITLE = _('A password reset code has been sent to your e-mail. '
    'Please enter the code below along with your new password.')
RETYPE_EMAIL = _("Retype email")
RETYPE_PASSWORD = _("Retype password")
REQUEST_PASSWORD_TOKEN_LABEL = _('To reset your %(app_name)s password,'
                                 ' enter your email address below:')
REQUEST_PASSWORD_TOKEN_TECH_ERROR = _('We are very Sorry! The service that'
    ' signs you on is not responding right now\nPlease try again or'
    ' come back in a few minutes.')
REQUEST_PASSWORD_TOKEN_WRONG_EMAIL = _('Sorry we did not recognize the email'
    ' address.')
RESET_CODE_ENTRY = _('Reset code')
RESET_EMAIL_ENTRY = _('Email address')
RESET_PASSWORD = RESET_TITLE
SET_NEW_PASSWORD_LABEL = _('A password reset code has been sent to '
    '%(email)s.\nPlease enter the code below along with your new password.')
SET_UP_ACCOUNT_BUTTON = _('Set Up Account')
SET_UP_ACCOUNT_CHOICE_BUTTON = _('I don\'t have an account yet - sign me up')
SIGN_IN_BUTTON = _('Sign In')
SIGN_IN_LABEL = _('Log-in with my existing account.')
SSL_APPNAME_HELP = _('the appname whose ssl error we are going to show.')
SSL_CERT_DETAILS = _('Certificate details')
SSL_CONNECT_BUTTON = _('Connect')
SSL_DETAILS_HELP = _('the details ssl certificate we are going to show.')
SSL_DETAILS_TEMPLATE = ('Organization:\t%(organization)s\n'
                        'Common Name:\t%(common_name)s\n'
                        'Locality Name:\t%(locality_name)s\n'
                        'Unit:\t%(unit)s\n'
                        'Country:\t%(country_name)s\n'
                        'State or Province:\t%(state_name)s')
SSL_DESCRIPTION = _('Open the SSL certificate UI.')
SSL_DIALOG_TITLE = _('SSL Certificate Not Valid')
SSL_DOMAIN_HELP = _('the domain whose ssl certificate we are going to show.')
SSL_EXPLANATION = _('You are trying to connect to a proxy server on'
    ' %(domain)s. This server uses a secure connection, and the SSL '
    'certificate is not valid because:')
SSL_FIRST_REASON = _('The certificate has not been verified')
SSL_HEADER = _('Do you want to connect to this server?')
SSL_HELP_BUTTON = _('Get Help With SSL')
SSL_NOT_SURE = _('If you are not sure about this server, do not use it to'
                 ' connect to %(app_name)s.')
SSL_REMEMBER_DECISION = _('Remember my settings for this certificate.')
SSL_SECOND_REASON = _('The name on the certificate isn\'t valid or doesn\'t'
    ' match the name of the site')
SSL_THIRD_REASON = _('The certificate has expired')
SUCCESS = _('You are now logged into %(app_name)s.')
SURNAME_ENTRY = _('Surname')
TERMS_TEXT = _("Terms of Service")
TITLE = REGISTER_TITLE = _("Sign Up to {app_name}")
TC_BUTTON = _('Show Terms & Conditions')
TC_NOT_ACCEPTED = _('Agreeing to the %(app_name)s Terms & Conditions is '
    'required to subscribe.')
TOS_LABEL = _("You can also find these terms at <a href='%(url)s'>%(url)s</a>")
TRY_AGAIN_BUTTON = _('Try again')
UNKNOWN_ERROR = _('There was an error when trying to complete the '
    'process. Please check the information and try again.')
VERIFICATION_CODE = _('Verification code')
VERIFY_EMAIL_CONTENT = _('Check %(email)s for an email from Ubuntu One. '
    'This message contains a verification code. Enter the code in '
    'the field below and click OK to complete creating your %(app_name)s '
    'account.')
VERIFY_EMAIL_TITLE = _('Enter verification code')
VERIFY_EMAIL_LABEL = ('<b>%s</b>\n\n' % VERIFY_EMAIL_TITLE +
                      VERIFY_EMAIL_CONTENT)
YES_TO_TC = _('I agree with the %(app_name)s terms and conditions')
YES_TO_UPDATES = _('Yes! Email me %(app_name)s tips and updates.')

# pylint: enable=E0602


def get_password_strength(password):
    """Return the strength of the password.

    This function returns the strength of the password so that ui elements
    can show the user how good his password is. The logic used is the
    following:

    * 1 extra point for 4 chars passwords
    * 1 extra point for 8 chars passwords
    * 1 extra point for more than 11 chars passwords.
    * 1 extra point for passwords with at least one number.
    * 1 extra point for passwords for lower and capital chars.
    * 1 extra point for passwords with a special char.

    A passwords starts with 0 and the extra points are added accordingly.
    """
    score = 0
    if len(password) < 1:
        return 0
    if len(password) < 4:
        score = 1
    if len(password) >= 8:
        score += 1
    if len(password) >= 11:
        score += 1
    if re.search('\d+', password):
        score += 1
    if re.search('[a-z]', password) and re.search('[A-Z]', password):
        score += 1
    if re.search('.[!,@,#,$,%,^,&,*,?,_,~,-,£,(,)]', password):
        score += 1
    return score


def is_min_required_password(password):
    """Return if the password meets the minimum requirements."""
    if len(password) < 8 or \
            re.search('[A-Z]', password) is None or \
            re.search('\d+', password) is None:
        return False
    return True


def is_correct_email(email_address):
    """Return if the email is correct."""
    return '@' in email_address


def parse_args():
    """Parse sys.argv options."""
    parser = argparse.ArgumentParser(description='Open the Ubuntu One UI.')
    parser.add_argument('--app_name', default='',
        help='the name of the application to retrieve credentials for')
    parser.add_argument('--ping_url', default='',
        help='a link to be used as the ping url (to notify about new tokens)')
    parser.add_argument('--policy_url', default='',
        help='a link to be used as Privacy Policy url')
    parser.add_argument('--tc_url', default='',
        help='a link to be used as Terms & Conditions url')
    parser.add_argument('--help_text', default='',
        help='extra text that will be shown below the headers')
    parser.add_argument('--window_id', type=int, default=0,
        help='the window id to be set transient for the Ubuntu One dialogs')
    parser.add_argument('--login_only', action='store_true', default=False,
        help='whether the Ubuntu One UI should only offer login or not')

    args = parser.parse_args()
    return args
