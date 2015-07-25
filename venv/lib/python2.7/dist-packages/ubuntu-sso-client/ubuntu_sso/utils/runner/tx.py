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
"""Utility to spawn another program from a mainloop."""

import os
import sys

from twisted.internet import utils

from ubuntu_sso.logger import setup_logging
from ubuntu_sso.utils import compat


logger = setup_logging("ubuntu_sso.utils.runner.tx")

NO_SUCH_FILE_OR_DIR = 'OSError: [Errno 2]'


EXE_EXT = ''
if sys.platform == 'win32':
    EXE_EXT = '.exe'


def spawn_program(args, reply_handler, error_handler):
    """Spawn the program specified by 'args' using the twisted reactor.

    When the program finishes, 'reply_handler' will be called with a single
    argument that will be the porgram status code.

    If there is an error, error_handler will be called with an instance of
    SpawnError.

    """

    def child_watch(args):
        """Handle child termination."""
        stdout, stderr, exit_code = args
        if stdout:
            logger.debug('Returned stdout is (exit code was %r): %r',
                         exit_code, stdout)
        if stderr:
            logger.warning('Returned stderr is (exit code was %r): %r',
                           exit_code, stderr)

        if OSError.__name__ in stderr:
            failed_to_start = NO_SUCH_FILE_OR_DIR in stderr
            error_handler(msg=stderr, failed_to_start=failed_to_start)
        else:
            reply_handler(exit_code)

    def handle_error(failure):
        """Handle error when spawning the process."""
        error_handler(msg=failure.getErrorMessage())

    args = list(args)
    program = args[0]
    argv = args[1:]

    bytes_args = []
    for arg in argv:
        if isinstance(arg, compat.text_type):
            arg = arg.encode('utf-8')
        if not isinstance(arg, compat.basestring):
            arg = compat.binary_type(arg)
        bytes_args.append(arg)

    if program and not os.access(program, os.X_OK):
        # handle searching the executable in the PATH, since
        # twisted will not solve that for us :-/
        paths = os.environ['PATH'].split(os.pathsep)
        for path in paths:
            target = os.path.join(path, program)
            if not target.endswith(EXE_EXT):
                target += EXE_EXT
            if os.access(target, os.X_OK):
                program = target
                break

    try:
        d = utils.getProcessOutputAndValue(program, bytes_args, env=os.environ)
    except OSError as e:
        error_handler(msg=e, failed_to_start=True)
    except Exception as e:
        error_handler(msg=e, failed_to_start=False)
    else:
        logger.debug('Spawning the program %r with the twisted reactor '
                     '(returned deferred is %r).', repr(args), d)
        d.addCallback(child_watch)
        d.addErrback(handle_error)
