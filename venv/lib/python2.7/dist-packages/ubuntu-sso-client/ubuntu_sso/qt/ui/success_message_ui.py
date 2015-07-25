# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'data/qt/success_message.ui'
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

class Ui_SuccessPage(object):
    def setupUi(self, SuccessPage):
        SuccessPage.setObjectName(_fromUtf8("SuccessPage"))
        SuccessPage.resize(94, 58)
        self.verticalLayout = QtGui.QVBoxLayout(SuccessPage)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.image_label = QtGui.QLabel(SuccessPage)
        self.image_label.setText(_fromUtf8("TextLabel"))
        self.image_label.setObjectName(_fromUtf8("image_label"))
        self.verticalLayout.addWidget(self.image_label)
        self.success_message_body = QtGui.QLabel(SuccessPage)
        self.success_message_body.setText(_fromUtf8("TextLabel"))
        self.success_message_body.setObjectName(_fromUtf8("success_message_body"))
        self.verticalLayout.addWidget(self.success_message_body)

        self.retranslateUi(SuccessPage)
        QtCore.QMetaObject.connectSlotsByName(SuccessPage)

    def retranslateUi(self, SuccessPage):
        pass

