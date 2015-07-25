# -*- coding: utf-8 -*-
#
# Copyright 2010-2012 Canonical Ltd.
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
"""Platform specific constants and functions (for Qt/Twisted)."""

from twisted.internet import defer
from PyQt4.QtCore import QThread, QCoreApplication


class DeferredThread(QThread):
    """A thread that runs a given function."""

    def __init__(self, f, *args, **kwargs):
        """Initialize this thread."""
        app = QCoreApplication.instance()
        super(DeferredThread, self).__init__(app)
        self.deferred = defer.Deferred()
        self.f = f
        self.args = args
        self.kwargs = kwargs
        self.succeeded = True
        self.result = None
        self.finished.connect(self.on_finished)

    def run(self):
        """This code runs inside the thread."""
        try:
            self.result = self.f(*self.args, **self.kwargs)
        # pylint: disable=W0703
        except Exception as e:
            self.succeeded = False
            self.result = e

    def on_finished(self):
        """The thread has completed."""
        if self.succeeded:
            self.deferred.callback(self.result)
        else:
            self.deferred.errback(self.result)


# pylint: disable=C0103
def qtDeferToThread(f, *args, **kwargs):
    """A Qt-based implementation of deferToThread."""
    thread = DeferredThread(f, *args, **kwargs)
    thread.start()
    return thread.deferred
