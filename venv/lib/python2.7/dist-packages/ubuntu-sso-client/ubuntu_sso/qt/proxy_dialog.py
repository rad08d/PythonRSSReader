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
"""Qt implementation of proxy UI."""

import argparse
import sys

from PyQt4.QtGui import QApplication, QDialog, QIcon
from twisted.internet import defer

from ubuntu_sso import EXCEPTION_RAISED, USER_SUCCESS, USER_CANCELLATION
from ubuntu_sso.logger import setup_gui_logging
from ubuntu_sso.keyring import Keyring
from ubuntu_sso.qt.ui.proxy_credentials_dialog_ui import Ui_ProxyCredsDialog
from ubuntu_sso.utils import compat
from ubuntu_sso.utils.ui import (
    CANCEL_BUTTON,
    PROXY_CREDS_DIALOG_TITLE,
    PROXY_CREDS_HEADER,
    PROXY_CREDS_EXPLANATION,
    PROXY_CREDS_CONNECTION,
    PROXY_CREDS_ERROR,
    PROXY_CREDS_USER_LABEL,
    PROXY_CREDS_PSWD_LABEL,
    PROXY_CREDS_HELP_BUTTON,
    PROXY_CREDS_SAVE_BUTTON,
)

logger = setup_gui_logging("ubuntu_sso.qt.proxy_dialog")


class ProxyCredsDialog(QDialog):
    """Dialog used to require the proxy credentials."""

    def __init__(self, retry=False, domain=None):
        """Create a new instance."""
        super(ProxyCredsDialog, self).__init__()

        if domain is None:
            logger.debug('Domain passed as None.')
            domain = ''
        self.domain = domain
        self.keyring = Keyring()
        self.ui = Ui_ProxyCredsDialog()
        self.ui.setupUi(self)
        # lets set the different basic contents for the ui
        self._set_labels()
        self._set_buttons()
        self._set_icon()
        if retry:
            self._load_creds()
            self.ui.error_label.setVisible(True)
        else:
            self.ui.error_label.setVisible(False)

    @defer.inlineCallbacks
    def _load_creds(self):
        """Tries to load the creds in a retry event."""
        # pylint: disable=W0703
        try:
            creds = yield self.keyring.get_credentials(self.domain)
            if creds is not None:
                logger.debug('Go no empty credentials.')
                # lets set the text for the inputs
                self.ui.username_entry.setText(creds['username'])
                self.ui.password_entry.setText(creds['password'])
        except Exception:
            logger.error('Problem getting old creds.')
        # pylint: enable=W0703

    def _set_labels(self):
        """Set the labels translations."""
        self.setWindowTitle(PROXY_CREDS_DIALOG_TITLE)
        self.ui.title_label.setText(PROXY_CREDS_HEADER)
        self.ui.explanation_label.setText(PROXY_CREDS_EXPLANATION)
        self.ui.connection_label.setText(PROXY_CREDS_CONNECTION)
        # HACK: later this should be set using qss
        self.ui.error_label.setText("<font color='#a62626'><b>%s</b></font>"
                                     % PROXY_CREDS_ERROR)
        self.ui.username_label.setText(PROXY_CREDS_USER_LABEL)
        self.ui.password_label.setText(PROXY_CREDS_PSWD_LABEL)
        self.ui.domain_label.setText(self.domain)

    @defer.inlineCallbacks
    def _on_save_clicked(self, *args):
        """Save the new credentials."""
        username = compat.text_type(
                        self.ui.username_entry.text()).encode('utf8')
        password = compat.text_type(
                        self.ui.password_entry.text()).encode('utf8')
        creds = dict(username=username, password=password)
        try:
            logger.debug('Save credentials as for domain %s.', self.domain)
            yield self.keyring.set_credentials(self.domain, creds)
        except Exception as e:
            logger.exception('Could not set credentials: %s', e)
            self.done(EXCEPTION_RAISED)
        logger.debug('Stored creds')
        self.done(USER_SUCCESS)

    def _on_cancel_clicked(self, *args):
        """End the dialog."""
        logger.debug('User canceled credentials dialog.')
        self.done(USER_CANCELLATION)

    def _set_buttons(self):
        """Set the labels of the buttons."""
        self.ui.help_button.setText(PROXY_CREDS_HELP_BUTTON)
        self.ui.cancel_button.setText(CANCEL_BUTTON)
        self.ui.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.ui.save_button.setText(PROXY_CREDS_SAVE_BUTTON)
        self.ui.save_button.clicked.connect(self._on_save_clicked)

    def _set_icon(self):
        """Set the icon used in the dialog."""
        icon = QIcon.fromTheme('gtk-dialog-authentication')
        self.ui.logo_label.setText('')
        self.ui.logo_label.setPixmap(icon.pixmap(48, 48))


def parse_args():
    """Parse sys.arg options."""
    parser = argparse.ArgumentParser(
            description='Open the Qt Proxy Credentials UI.')
    parser.add_argument('--domain', required=True,
        help='the domain whose credentials are going to be stored.')
    parser.add_argument('--retry', action='store_true', default=False,
        help='whether we are retrying to get the creds.')
    return parser.parse_args()


def exit_code(return_code):
    """Use the window result code and the sys.exit."""
    logger.debug('exit %s', return_code)
    QApplication.instance().exit(return_code)
    if sys.platform == 'win32':
        logger.debug('Stop qt reactor')
        from twisted.internet import reactor
        reactor.stop()


def main():
    """Main method used to show the creds dialog."""
    if sys.platform == 'win32':
        import qt4reactor
        qt4reactor.install()
        logger.debug('Qt reactor installed.')

    app = QApplication(sys.argv)
    app
    args = parse_args()
    win = ProxyCredsDialog(domain=args.domain,
                           retry=args.retry)

    if sys.platform == 'win32':
        win.show()
        win.finished.connect(exit_code)

        logger.debug('Starting reactor')
        from twisted.internet import reactor
        logger.debug('QApp is %s', reactor.qApp)
        reactor.run()
    else:
        return_code = win.exec_()
        sys.exit(return_code)
