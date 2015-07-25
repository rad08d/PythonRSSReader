# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'data/qt/ssl_dialog.ui'
#
# Created: Sat Apr  5 11:38:08 2014
#      by: PyQt4 UI code generator 4.10.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_SSLDialog(object):
    def setupUi(self, SSLDialog):
        SSLDialog.setObjectName(_fromUtf8("SSLDialog"))
        SSLDialog.resize(550, 402)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(SSLDialog.sizePolicy().hasHeightForWidth())
        SSLDialog.setSizePolicy(sizePolicy)
        SSLDialog.setMinimumSize(QtCore.QSize(550, 0))
        SSLDialog.setWindowTitle(_fromUtf8("Dialog"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(SSLDialog)
        self.verticalLayout_2.setSpacing(24)
        self.verticalLayout_2.setSizeConstraint(QtGui.QLayout.SetFixedSize)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setSpacing(12)
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.verticalLayout_7 = QtGui.QVBoxLayout()
        self.verticalLayout_7.setSpacing(0)
        self.verticalLayout_7.setSizeConstraint(QtGui.QLayout.SetDefaultConstraint)
        self.verticalLayout_7.setObjectName(_fromUtf8("verticalLayout_7"))
        self.logo_label = QtGui.QLabel(SSLDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.logo_label.sizePolicy().hasHeightForWidth())
        self.logo_label.setSizePolicy(sizePolicy)
        self.logo_label.setMinimumSize(QtCore.QSize(48, 48))
        self.logo_label.setMaximumSize(QtCore.QSize(48, 48))
        self.logo_label.setText(_fromUtf8("TextLabel"))
        self.logo_label.setObjectName(_fromUtf8("logo_label"))
        self.verticalLayout_7.addWidget(self.logo_label)
        spacerItem = QtGui.QSpacerItem(0, 20, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_7.addItem(spacerItem)
        self.horizontalLayout_3.addLayout(self.verticalLayout_7)
        self.expander_layout = QtGui.QVBoxLayout()
        self.expander_layout.setSpacing(24)
        self.expander_layout.setObjectName(_fromUtf8("expander_layout"))
        self.title_label = QtGui.QLabel(SSLDialog)
        self.title_label.setText(_fromUtf8("Do you want to connect to this server"))
        self.title_label.setObjectName(_fromUtf8("title_label"))
        self.expander_layout.addWidget(self.title_label)
        self.intro_label = QtGui.QLabel(SSLDialog)
        self.intro_label.setText(_fromUtf8("<style type=\"text/css\" media=\"all\">\n"
"ul {margin-left: -10px;}\n"
"li {padding-top: 2px;}\n"
"</style>\n"
"<p>You are trying to connect to a proxy server on 192.168.1.111. This server uses a secure connection, but the SSL certificate is not valid because:</p>\n"
"<ul>\n"
"<li>The certificate has not been verified.</li>\n"
"<li>The name on the certificate isn\'t valid or doesn\'t match the name of the site.</li>\n"
"<li>The certificate has expired.</li>\n"
"</ul>"))
        self.intro_label.setWordWrap(True)
        self.intro_label.setIndent(-1)
        self.intro_label.setObjectName(_fromUtf8("intro_label"))
        self.expander_layout.addWidget(self.intro_label)
        self.not_sure_label = QtGui.QLabel(SSLDialog)
        self.not_sure_label.setText(_fromUtf8("<p>If you are not sure about this server, do not use it to connect to Ubuntu One. <a href=\'#\'>Review your proxy settings.</a>"))
        self.not_sure_label.setWordWrap(True)
        self.not_sure_label.setObjectName(_fromUtf8("not_sure_label"))
        self.expander_layout.addWidget(self.not_sure_label)
        self.remember_checkbox = QtGui.QCheckBox(SSLDialog)
        self.remember_checkbox.setText(_fromUtf8("Remember my settings for this certificate."))
        self.remember_checkbox.setChecked(False)
        self.remember_checkbox.setObjectName(_fromUtf8("remember_checkbox"))
        self.expander_layout.addWidget(self.remember_checkbox)
        self.horizontalLayout_3.addLayout(self.expander_layout)
        self.verticalLayout_2.addLayout(self.horizontalLayout_3)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.help_button = QtGui.QPushButton(SSLDialog)
        self.help_button.setText(_fromUtf8("Get Help With SSL"))
        self.help_button.setObjectName(_fromUtf8("help_button"))
        self.horizontalLayout_2.addWidget(self.help_button)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem1)
        self.cancel_button = QtGui.QPushButton(SSLDialog)
        self.cancel_button.setText(_fromUtf8("Cancel and Close"))
        self.cancel_button.setObjectName(_fromUtf8("cancel_button"))
        self.horizontalLayout_2.addWidget(self.cancel_button)
        self.connect_button = QtGui.QPushButton(SSLDialog)
        self.connect_button.setText(_fromUtf8("Connect"))
        self.connect_button.setDefault(True)
        self.connect_button.setObjectName(_fromUtf8("connect_button"))
        self.horizontalLayout_2.addWidget(self.connect_button)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)

        self.retranslateUi(SSLDialog)
        QtCore.QMetaObject.connectSlotsByName(SSLDialog)
        SSLDialog.setTabOrder(self.connect_button, self.cancel_button)
        SSLDialog.setTabOrder(self.cancel_button, self.help_button)
        SSLDialog.setTabOrder(self.help_button, self.remember_checkbox)

    def retranslateUi(self, SSLDialog):
        pass

