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
"""Qt implementation of the SSL ui."""

import argparse
import sys

from PyQt4.QtGui import (
    QApplication,
    QDialog,
    QScrollArea,
    QStyle,
    QTextEdit,
)

from ubuntu_sso import USER_CANCELLATION, USER_SUCCESS
from ubuntu_sso.logger import setup_gui_logging
from ubuntu_sso.qt.ui import resources_rc
from ubuntu_sso.qt.expander import QExpander
from ubuntu_sso.qt.ui.ssl_dialog_ui import Ui_SSLDialog
from ubuntu_sso.utils.ui import (
    CANCEL_BUTTON,
    SSL_APPNAME_HELP,
    SSL_DETAILS_HELP,
    SSL_DIALOG_TITLE,
    SSL_DESCRIPTION,
    SSL_DOMAIN_HELP,
    SSL_HEADER,
    SSL_EXPLANATION,
    SSL_FIRST_REASON,
    SSL_SECOND_REASON,
    SSL_THIRD_REASON,
    SSL_CERT_DETAILS,
    SSL_NOT_SURE,
    SSL_REMEMBER_DECISION,
    SSL_HELP_BUTTON,
    SSL_CONNECT_BUTTON,
)

REASONS_TEMPLATE = ('<p>%(explanation)s</p>'
                    '<ul style="margin-left:-10px">'
                    '<li style="margin-bottom:5px;">%(first_reason)s</li>'
                    '<li style="margin-bottom:5px;">%(second_reason)s</li>'
                    '<li>%(third_reason)s</li>'
                    '</ul>')

logger = setup_gui_logging("ubuntu_sso.qt.proxy_dialog")
assert(resources_rc)


class SSLDialog(QDialog):
    """"Dialog used to show SSL exceptions."""

    def __init__(self, app_name, domain=None, details=None, parent=None):
        """Create a new instance."""
        super(SSLDialog, self).__init__()
        if domain is None:
            logger.debug('Domain passed as None.')
            domain = ''
        self.domain = domain
        if details is None:
            logger.debug('Details passed as None.')
            details = ''
        self.details = details
        self.app_name = app_name
        self.ssl_text = None
        self.expander = None
        self.ui = Ui_SSLDialog()
        self.ui.setupUi(self)
        self.setWindowTitle(SSL_DIALOG_TITLE)
        self._set_expander()
        self._set_labels()
        self._set_buttons()
        self._set_icon()

    def _set_labels(self):
        """Set the labels translations."""
        self.ui.title_label.setText(SSL_HEADER)
        explanation = SSL_EXPLANATION % dict(domain=self.domain)
        intro = REASONS_TEMPLATE % dict(explanation=explanation,
                                        first_reason=SSL_FIRST_REASON,
                                        second_reason=SSL_SECOND_REASON,
                                        third_reason=SSL_THIRD_REASON)
        self.ui.intro_label.setText(intro)
        self.ui.not_sure_label.setText(SSL_NOT_SURE %
                                       {'app_name': self.app_name})
        self.ui.remember_checkbox.setText(SSL_REMEMBER_DECISION)

    def _on_cancel_clicked(self):
        """Cancel was cliked."""
        logger.debug('User canceled the ssl dialog.')
        self.done(USER_CANCELLATION)

    def _on_connect_clicked(self):
        """Connect was clicked."""
        logger.debug('User accepted the ssl certificate.')
        self.done(USER_SUCCESS)

    def _set_buttons(self):
        """Set the labels of the buttons."""
        self.ui.help_button.setText(SSL_HELP_BUTTON)
        self.ui.cancel_button.setText(CANCEL_BUTTON)
        self.ui.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.ui.connect_button.setText(SSL_CONNECT_BUTTON)
        self.ui.connect_button.clicked.connect(self._on_connect_clicked)

    def _set_expander(self):
        """Set the expander widget."""
        self.ssl_text = QTextEdit()
        self.ssl_text.setText(self.details)
        scroll_area = QScrollArea()
        scroll_area.setViewport(self.ssl_text)
        scroll_area.setFixedHeight(50)

        self.expander = QExpander(SSL_CERT_DETAILS)
        self.expander.addWidget(scroll_area)
        self.ui.expander_layout.insertWidget(2, self.expander)

    def _set_icon(self):
        """Set the icon used in the dialog."""
        icon = self.style().standardIcon(QStyle.SP_MessageBoxWarning)
        self.ui.logo_label.setText('')
        self.ui.logo_label.setPixmap(icon.pixmap(48, 48))


def parse_args():
    """Parse sys.arg options."""
    parser = argparse.ArgumentParser(
            description=SSL_DESCRIPTION)
    parser.add_argument('--domain', required=True,
        help=SSL_DOMAIN_HELP)
    parser.add_argument('--details', required=True,
        help=SSL_DETAILS_HELP)
    parser.add_argument('--appname', required=True,
        help=SSL_APPNAME_HELP)
    return parser.parse_args()


def main():
    """Main method used to show the creds dialog."""
    app = QApplication(sys.argv)
    assert(app)
    args = parse_args()
    win = SSLDialog(args.appname, domain=args.domain, details=args.details)
    return_code = win.exec_()
    sys.exit(return_code)
