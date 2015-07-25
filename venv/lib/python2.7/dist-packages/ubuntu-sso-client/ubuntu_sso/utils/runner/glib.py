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
"""Utility to spawn another program from a GLib mainloop."""

import os

# pylint: disable=E0611,F0401
from gi.repository import GLib
# pylint: enable=E0611,F0401

from ubuntu_sso.logger import setup_logging
from ubuntu_sso.utils import compat

logger = setup_logging("ubuntu_sso.utils.runner.glib")


NO_SUCH_FILE_OR_DIR = '[Errno 2]'


def spawn_program(args, reply_handler, error_handler):
    """Spawn the program specified by 'args' using the GLib mainloop.

    When the program finishes, 'reply_handler' will be called with a single
    argument that will be the porgram status code.

    If there is an error, error_handler will be called with an instance of
    SpawnError.

    """

    def child_watch(pid, status):
        """Handle child termination."""
        # pylint: disable=E1103
        GLib.spawn_close_pid(pid)
        # pylint: enable=E1103

        if os.WIFEXITED(status):
            status = os.WEXITSTATUS(status)
            reply_handler(status)
        else:
            msg = 'Child terminated abnormally, '\
                  'status from waitpid is %r' % status
            error_handler(msg=msg, failed_to_start=False)

    def handle_error(gerror):
        """Handle error when spawning the process."""
        failed_to_start = NO_SUCH_FILE_OR_DIR in gerror.message
        msg = 'GError is: code %r, message %r' % (gerror.code, gerror.message)
        error_handler(msg=msg, failed_to_start=failed_to_start)

    flags = GLib.SpawnFlags.DO_NOT_REAP_CHILD | \
            GLib.SpawnFlags.SEARCH_PATH | \
            GLib.SpawnFlags.STDOUT_TO_DEV_NULL | \
            GLib.SpawnFlags.STDERR_TO_DEV_NULL
    pid = None

    bytes_args = []
    for arg in args:
        if isinstance(arg, compat.text_type):
            arg = arg.encode('utf-8')
        if not isinstance(arg, compat.basestring):
            arg = compat.binary_type(arg)
        bytes_args.append(arg)

    try:
        pid, _, _, _ = GLib.spawn_async(argv=bytes_args, flags=flags)
    except GLib.GError as e:
        handle_error(e)
    else:
        logger.debug('Spawning the program %r with the glib mainloop '
                     '(returned pid is %r).', args, pid)
        GLib.child_watch_add(pid, child_watch)
