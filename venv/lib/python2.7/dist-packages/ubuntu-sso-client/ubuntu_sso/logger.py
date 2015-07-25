# -*- coding: utf-8 -*-
#
# ubuntu_sso.logger - logging miscellany
#
# Author: Stuart Langridge <stuart.langridge@canonical.com>
# Author: Natalia B. Bidart <natalia.bidart@canonical.com>
#
# Copyright 2009-2012 Canonical Ltd.
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
"""Miscellaneous logging functions."""

import logging
import os
import sys

from dirspec.basedir import xdg_cache_home
from dirspec.utils import unicode_path
from functools import wraps
from logging.handlers import RotatingFileHandler

LOGFOLDER = os.path.join(xdg_cache_home, 'sso')
# create log folder if it doesn't exists
if not os.path.exists(unicode_path(LOGFOLDER)):
    os.makedirs(unicode_path(LOGFOLDER))

if os.environ.get('U1_DEBUG'):
    LOG_LEVEL = logging.DEBUG
else:
    # Only log this level and above
    LOG_LEVEL = logging.INFO

LOG_PATH = os.path.join(LOGFOLDER, 'sso-client.log')
FMT = "%(asctime)s:%(msecs)s - %(name)s - %(levelname)s - %(message)s"

MAIN_HANDLER = RotatingFileHandler(unicode_path(LOG_PATH),
                                   maxBytes=1048576,
                                   backupCount=5)
MAIN_HANDLER.setLevel(LOG_LEVEL)
MAIN_HANDLER.setFormatter(logging.Formatter(fmt=FMT))

GUI_LOG_PATH = os.path.join(LOGFOLDER, 'sso-client-gui.log')
GUI_HANDLER = RotatingFileHandler(unicode_path(GUI_LOG_PATH),
                                  maxBytes=1048576,
                                  backupCount=5)
GUI_HANDLER.setLevel(LOG_LEVEL)
GUI_HANDLER.setFormatter(logging.Formatter(fmt=FMT))


def setup_logging(log_domain, handler=None):
    """Create basic logger to set filename."""
    if handler is None:
        handler = MAIN_HANDLER

    logger = logging.getLogger(log_domain)
    logger.propagate = False
    logger.setLevel(LOG_LEVEL)
    logger.addHandler(handler)
    if os.environ.get('U1_DEBUG'):
        debug_handler = logging.StreamHandler(sys.stderr)
        debug_handler.setFormatter(logging.Formatter(fmt=FMT))
        logger.addHandler(debug_handler)

    return logger


def setup_gui_logging(log_domain):
    """Create basic logger to set filename."""
    return setup_logging(log_domain, GUI_HANDLER)


def log_call(log_func):
    """Decorator to log, using 'log_func', calls to functions."""

    def middle(f):
        """Return a function that will act as 'f' but will log the call."""

        @wraps(f)
        def inner(instance, *a, **kw):
            """Call 'f(*a, **kw)' and return its result. Log that call."""
            log_func('%r: emitting %r with args %r and kwargs %r',
                     instance.__class__.__name__, f.__name__, a, kw)
            result = f(instance, *a, **kw)
            return result

        return inner

    return middle
