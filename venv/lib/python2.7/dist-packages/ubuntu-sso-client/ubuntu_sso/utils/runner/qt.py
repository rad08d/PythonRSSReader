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
"""Utility to spawn another program from a plain Qt mainloop."""

from PyQt4 import QtCore

from ubuntu_sso.logger import setup_logging


logger = setup_logging("ubuntu_sso.utils.runner.qt")

# pylint: disable=C0103
# the set below is a workaround to hold to object references to avoid
# garbage collection before the processes finish executing
_processes = set()


def spawn_program(args, reply_handler, error_handler):
    """Spawn the program specified by 'args' using the Qt mainloop.

    When the program finishes, 'reply_handler' will be called with a single
    argument that will be the porgram status code.

    If there is an error, error_handler will be called with an instance of
    SpawnError.

    """

    process = QtCore.QProcess()
    _processes.add(process)

    def print_pid():
        """Add a debug log message."""
        pid = process.pid()
        logger.debug('Spawning the program %r with the qt mainloop '
                     '(returned pid is %r).', args, pid)

    def child_watch(status):
        """Handle child termination."""
        reply_handler(status)
        _processes.remove(process)

    def handle_error(process_error):
        """Handle error when spawning the process."""
        failed_to_start = (process_error == process.FailedToStart)
        msg = 'ProcessError is %r' % process_error
        error_handler(msg=msg, failed_to_start=failed_to_start)
        _processes.remove(process)

    process.started.connect(print_pid)
    process.finished.connect(child_watch)
    process.error.connect(handle_error)

    args = list(args)
    program = args[0]
    argv = args[1:]
    process.start(program, argv)
