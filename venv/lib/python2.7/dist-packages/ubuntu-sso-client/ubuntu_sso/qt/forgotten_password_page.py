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
"""Forgotten Password page UI."""

from functools import partial

from PyQt4 import QtCore

from ubuntu_sso import NO_OP
from ubuntu_sso.logger import setup_gui_logging, log_call
from ubuntu_sso.qt.sso_wizard_page import SSOWizardEnhancedEditPage
from ubuntu_sso.qt.ui.forgotten_password_ui import Ui_ForgottenPasswordPage
from ubuntu_sso.utils import compat
from ubuntu_sso.utils.ui import (
    EMAIL_LABEL,
    FORGOTTEN_PASSWORD_TITLE,
    FORGOTTEN_PASSWORD_SUBTITLE,
    is_correct_email,
    RESET_PASSWORD,
    REQUEST_PASSWORD_TOKEN_WRONG_EMAIL,
)


logger = setup_gui_logging('ubuntu_sso.forgotten_password_page')


class ForgottenPasswordPage(SSOWizardEnhancedEditPage):
    """Widget used to deal with users that forgot the password."""

    ui_class = Ui_ForgottenPasswordPage
    passwordResetTokenSent = QtCore.pyqtSignal(compat.text_type)

    @property
    def _signals(self):
        """The signals to connect to the backend."""
        result = {
            'PasswordResetTokenSent':
                self._filter_by_app_name(self.on_password_reset_token_sent),
            'PasswordResetError':
                self._filter_by_app_name(self.on_password_reset_error),
        }
        return result

    @property
    def email_address(self):
        """Return the email address provided by the user."""
        return compat.text_type(self.ui.email_line_edit.text())

    #pylint: disable=C0103

    def initializePage(self):
        """Set the initial state of ForgottenPassword page."""
        logger.debug('initializePage - About to show ForgottenPasswordPage')
        self.ui.send_button.setDefault(True)
        enabled = not self.ui.email_line_edit.text().isEmpty()
        self.ui.send_button.setEnabled(enabled)

    #pylint: enable=C0103

    def _register_fields(self):
        """Register the fields of the wizard page."""
        self.registerField('email_address',
                           self.ui.email_line_edit)

    def _set_translated_strings(self):
        """Set the translated strings in the view."""
        self.setTitle(FORGOTTEN_PASSWORD_TITLE)
        subtitle = FORGOTTEN_PASSWORD_SUBTITLE.format(app_name=self.app_name)
        self.setSubTitle(subtitle)
        self.ui.email_address_label.setText(EMAIL_LABEL)
        self.ui.send_button.setText(RESET_PASSWORD)

    def _set_enhanced_line_edit(self):
        """Set the extra logic to the line edits."""
        self.set_line_edit_validation_rule(self.ui.email_line_edit,
                                           is_correct_email)

    def _connect_ui(self):
        """Connect the diff signals from the Ui."""
        self.ui.email_line_edit.textChanged.connect(self._validate)
        self.ui.send_button.clicked.connect(self.request_new_password)
        self._set_enhanced_line_edit()
        self._register_fields()

    def request_new_password(self):
        """Send the request password operation."""
        self.hide_error()
        args = (self.app_name, self.email_address)
        logger.debug('Sending request new password for %s, email: %s', *args)
        f = self.backend.request_password_reset_token

        error_handler = partial(self._handle_error, f,
            self.on_password_reset_error)

        self.show_overlay()
        f(*args, reply_handler=NO_OP, error_handler=error_handler)

    def _validate(self):
        """Validate that we have an email."""
        email = compat.text_type(self.ui.email_line_edit.text())
        self.ui.send_button.setEnabled(is_correct_email(email))

    def on_password_reset_token_sent(self, app_name, email):
        """Action taken when we managed to get the password reset done."""
        logger.info('ForgottenPasswordPage.on_password_reset_token_sent for '
                    '%s, email: %s', app_name, email)
        # ignore the result and move to the reset page
        self.hide_overlay()
        self.passwordResetTokenSent.emit(email)

    @log_call(logger.error)
    def on_password_reset_error(self, app_name, error):
        """Action taken when there was an error requesting the reset."""
        # set the error message
        self.hide_overlay()
        msg = REQUEST_PASSWORD_TOKEN_WRONG_EMAIL
        self.show_error(msg)
