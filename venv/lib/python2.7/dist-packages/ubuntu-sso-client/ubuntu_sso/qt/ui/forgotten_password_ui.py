# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'data/qt/forgotten_password.ui'
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

class Ui_ForgottenPasswordPage(object):
    def setupUi(self, ForgottenPasswordPage):
        ForgottenPasswordPage.setObjectName(_fromUtf8("ForgottenPasswordPage"))
        ForgottenPasswordPage.resize(148, 148)
        self.verticalLayout_2 = QtGui.QVBoxLayout(ForgottenPasswordPage)
        self.verticalLayout_2.setSpacing(15)
        self.verticalLayout_2.setMargin(0)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setSpacing(3)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.email_address_label = QtGui.QLabel(ForgottenPasswordPage)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.email_address_label.sizePolicy().hasHeightForWidth())
        self.email_address_label.setSizePolicy(sizePolicy)
        self.email_address_label.setText(_fromUtf8(""))
        self.email_address_label.setObjectName(_fromUtf8("email_address_label"))
        self.verticalLayout.addWidget(self.email_address_label)
        self.email_line_edit = QtGui.QLineEdit(ForgottenPasswordPage)
        self.email_line_edit.setMinimumSize(QtCore.QSize(300, 0))
        self.email_line_edit.setObjectName(_fromUtf8("email_line_edit"))
        self.verticalLayout.addWidget(self.email_line_edit)
        self.verticalLayout_2.addLayout(self.verticalLayout)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.send_button = QtGui.QPushButton(ForgottenPasswordPage)
        self.send_button.setEnabled(False)
        self.send_button.setText(_fromUtf8(""))
        self.send_button.setObjectName(_fromUtf8("send_button"))
        self.horizontalLayout.addWidget(self.send_button)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem1)

        self.retranslateUi(ForgottenPasswordPage)
        QtCore.QObject.connect(self.email_line_edit, QtCore.SIGNAL(_fromUtf8("returnPressed()")), self.send_button.click)
        QtCore.QMetaObject.connectSlotsByName(ForgottenPasswordPage)

    def retranslateUi(self, ForgottenPasswordPage):
        pass

