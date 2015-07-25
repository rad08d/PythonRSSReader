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

import sys

from twisted.internet import defer

from ubuntu_sso.logger import setup_logging


logger = setup_logging("ubuntu_sso.utils.runner")


class SpawnError(Exception):
    """Generic error when spawning processes."""


class FailedToStartError(SpawnError):
    """The process could not be spawned."""


def is_qt4_main_loop_installed():
    """Check if the Qt4 main loop is installed."""
    result = False

    if not 'PyQt4' in sys.modules:
        return result

    try:
        from PyQt4.QtCore import QCoreApplication
        result = QCoreApplication.instance() is not None
    except ImportError:
        pass

    return result


def spawn_program(args, use_reactor=False):
    """Spawn the program specified by 'args'.

    - 'args' should be a sequence of program arguments, the program to execute
    is normally the first item in 'args'.

    Return a deferred that will be fired when the execution of 'args' finishes,
    passing as the deferred result code the program return code.

    On error, the returned deferred will be errback'd.

    """
    logger.debug('spawn_program: requested to spawn %r.', repr(args))
    d = defer.Deferred()

    # HACK: The qt runner does have problem in mac os x and does not raise the
    # finish signal
    if use_reactor or sys.platform == 'darwin':
        from ubuntu_sso.utils.runner import tx
        source = tx
    elif is_qt4_main_loop_installed():
        from ubuntu_sso.utils.runner import qt
        source = qt
    else:
        from ubuntu_sso.utils.runner import glib
        source = glib

    logger.debug('Spawn source is %r.', source)

    def reply_handler(status):
        """Callback the returned deferred."""
        logger.debug('The program %r finished with status %r.', args, status)
        d.callback(status)

    def error_handler(msg, failed_to_start=False):
        """Errback the returned deferred."""
        if failed_to_start:
            msg = 'Process %r could not be started (%r).' % (args, msg)
            exc = FailedToStartError(msg)
        else:
            exc = SpawnError('Unspecified error (%r).' % msg)

        logger.error('The program %r could not be run: %r', args, exc)
        d.errback(exc)

    source.spawn_program(args, reply_handler, error_handler)
    return d
