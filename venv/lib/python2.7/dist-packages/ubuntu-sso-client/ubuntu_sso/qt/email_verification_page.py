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
"""Email Verification page UI."""

from functools import partial

from PyQt4 import QtGui, QtCore

from ubuntu_sso import NO_OP
from ubuntu_sso.logger import setup_gui_logging
from ubuntu_sso.qt import build_general_error_message
from ubuntu_sso.qt.sso_wizard_page import SSOWizardPage
from ubuntu_sso.qt.ui.email_verification_ui import Ui_EmailVerificationPage
from ubuntu_sso.utils import compat
from ubuntu_sso.utils.ui import (
    ERROR_EMAIL_TOKEN,
    NEXT,
    VERIFICATION_CODE,
    VERIFY_EMAIL_TITLE,
    VERIFY_EMAIL_CONTENT,
)


logger = setup_gui_logging('ubuntu_sso.email_verification_page')


class EmailVerificationPage(SSOWizardPage):
    """Widget used to input the email verification code."""

    ui_class = Ui_EmailVerificationPage
    registrationSuccess = QtCore.pyqtSignal(compat.text_type)

    def __init__(self, *args, **kwargs):
        self.email = ''
        self.password = ''
        super(EmailVerificationPage, self).__init__(*args, **kwargs)

    @property
    def _signals(self):
        """The signals to connect to the backend."""
        result = {
            'EmailValidated':
                self._filter_by_app_name(self.on_email_validated),
            'EmailValidationError':
                self._filter_by_app_name(self.on_email_validation_error),
        }
        return result

    @property
    def verification_code(self):
        """Return the content of the verification code edit."""
        return str(self.ui.verification_code_edit.text())

    @property
    def next_button(self):
        """Return the button that move to the next stage."""
        return self.ui.next_button

    def _connect_ui(self):
        """Set the connection of signals."""
        self.ui.verification_code_edit.textChanged.connect(
            self.validate_form)
        self.next_button.clicked.connect(self.validate_email)

    def validate_form(self):
        """Check the state of the form."""
        code = self.verification_code.strip()
        enabled = len(code) > 0
        self.next_button.setEnabled(enabled)

    def _set_translated_strings(self):
        """Set the different titles."""
        self.header.set_title(VERIFY_EMAIL_TITLE)
        self.header.set_subtitle(VERIFY_EMAIL_CONTENT % {
            "app_name": self.app_name,
            "email": self.email,
        })
        self.ui.label.setText(VERIFICATION_CODE)
        self.ui.next_button.setText(NEXT)

    def set_titles(self, email):
        """This class needs to have a public set_titles.

        Since the subtitle contains data that is only known after SetupAccount
        and _set_translated_strings is only called on initialization.
        """
        self._set_translated_strings()

    def validate_email(self):
        """Call the next action."""
        logger.debug('EmailVerificationController.validate_email for: %s',
            self.email)
        code = compat.text_type(self.ui.verification_code_edit.text())
        args = (self.app_name, self.email, self.password, code)
        self.hide_error()
        self.show_overlay()
        if self.ping_url:
            f = self.backend.validate_email_and_ping
            args = args + (self.ping_url,)
        else:
            f = self.backend.validate_email

        logger.info('Calling validate_email with email %r, password <hidden>, '
                    'app_name %r and email_token %r.', self.email,
                    self.app_name, code)
        error_handler = partial(self._handle_error, f,
                                self.on_email_validation_error)
        f(*args, reply_handler=NO_OP, error_handler=error_handler)

    def on_email_validated(self, app_name, email):
        """Signal thrown after the email is validated."""
        logger.info('EmailVerificationController.on_email_validated for %s, '
                    'email: %s', app_name, email)
        self.hide_overlay()
        self.registrationSuccess.emit(self.email)

    def on_email_validation_error(self, app_name, error):
        """Signal thrown when there's a problem validating the email."""
        logger.error('Got error on email validation %s, error: %s',
            app_name, error)
        self.hide_overlay()
        msg = error.pop(ERROR_EMAIL_TOKEN, '')
        msg += build_general_error_message(error)
        self.show_error(msg)

    # pylint: disable=C0103

    def initializePage(self):
        """Called to prepare the page just before it is shown."""
        logger.debug('initializePage - About to show EmailVerificationPage')
        self.next_button.setDefault(True)
        self.next_button.setEnabled(False)
        self.wizard().setButtonLayout([QtGui.QWizard.Stretch])

    #pylint: enable=C0103
