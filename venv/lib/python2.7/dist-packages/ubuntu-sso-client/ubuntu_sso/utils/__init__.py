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
"""Utility modules that may find use outside ubuntu_sso."""

from __future__ import unicode_literals

import os
import sys

from dirspec.basedir import load_config_paths
from dirspec.utils import get_program_path

from twisted.internet import defer
from twisted.python import procutils

from ubuntu_sso import (BACKEND_EXECUTABLE,
                        UI_EXECUTABLE_QT,
                        UI_PROXY_CREDS_DIALOG,
                        UI_SSL_DIALOG)
from ubuntu_sso.logger import setup_logging
from ubuntu_sso.utils import compat, webclient


logger = setup_logging("ubuntu_sso.utils")
BIN_SUFFIX = 'bin'
DATA_SUFFIX = 'data'

QSS_MAP = dict(win32=':/windows.qss',
               darwin=':/darwin.qss',
               linux=':/linux.qss')

# Setting linux as default if we don't find the
# platform as a key in the dictionary
PLATFORM_QSS = QSS_MAP.get(sys.platform, ":/linux.qss")

DARWIN_APP_NAMES = {BACKEND_EXECUTABLE: 'Ubuntu SSO Helper.app',
                    UI_EXECUTABLE_QT: 'Ubuntu Single Sign-On.app',
                    UI_SSL_DIALOG: 'Ubuntu SSO SSL Certificate.app',
                    UI_PROXY_CREDS_DIALOG: 'Ubuntu SSO Proxy Credentials.app'
                    }


def _get_dir(dir_name, dir_constant):
    """Return the absolute path to this project's 'dir_name' dir.

    Support symlinks, and priorize local (relative) 'dir_name' dir. If not
    found, return the value of the 'dir_constant'.

    """
    module = os.path.dirname(__file__)
    result = os.path.abspath(os.path.join(module, os.path.pardir,
                                          os.path.pardir, dir_name))
    logger.debug('_get_dir: trying use dir at %r (exists? %s)',
                  result, os.path.exists(result))
    if os.path.exists(result):
        logger.info('_get_dir: returning dir located at %r.', result)
        return result

    # otherwise, try to load 'dir_constant' from installation path
    try:
        __import__('ubuntu_sso.constants', None, None, [''])
        module = sys.modules.get('ubuntu_sso.constants')
        return getattr(module, dir_constant)
    except (ImportError, AttributeError):
        msg = '_get_dir: can not build a valid path. Giving up. ' \
              '__file__ is %r, constants module not available.'
        logger.error(msg, __file__)


def get_project_dir():
    """Return the absolute path to this project's data/ dir.

    Support symlinks, and priorize local (relative) data/ dir. If not
    found, return the value of the PROJECT_DIR.

    """
    result = _get_dir(dir_name=DATA_SUFFIX, dir_constant='PROJECT_DIR')
    assert result is not None, '%r dir can not be None.' % DATA_SUFFIX
    return result


def get_data_file(*args):
    """Return the absolute path to 'args' within project data dir."""
    return os.path.join(get_project_dir(), *args)


def get_bin_dir():
    """Return the absolute path to this project's bin/ dir.

    Support symlinks, and priorize local (relative) bin/ dir. If not
    found, return the value of the BIN_DIR.

    """
    result = _get_dir(dir_name=BIN_SUFFIX, dir_constant='BIN_DIR')
    assert result is not None, '%r dir can not be None.' % BIN_SUFFIX
    logger.info('get_bin_dir: returning dir located at %r.', result)
    return result


def get_bin_cmd(program_name):
    """Return a list of arguments to launch the given executable."""
    path = get_program_path(program_name,
                            fallback_dirs=[get_bin_dir()],
                            app_names=DARWIN_APP_NAMES)
    cmd_args = [path]

    # adjust cmd for platforms using buildout-generated python
    # wrappers
    if getattr(sys, 'frozen', None) is None:
        if sys.platform in ('darwin'):
            cmd_args.insert(0, 'python')
        elif sys.platform in ('win32'):
            cmd_args.insert(0, procutils.which("python.exe")[0])

    logger.debug('get_bin_cmd: returning %r', cmd_args)
    return cmd_args


def get_cert_dir():
    """Return directory containing certificate files."""

    if getattr(sys, "frozen", None) is not None:
        if sys.platform == "win32":
            ssl_cert_location = list(load_config_paths(
                    "ubuntuone"))[1]
        elif sys.platform == "darwin":
                main_app_dir = "".join(__file__.partition(".app")[:-1])
                main_app_resources_dir = os.path.join(main_app_dir,
                                                      "Contents",
                                                      "Resources")
                ssl_cert_location = main_app_resources_dir
    elif any(plat in sys.platform for plat in ("win32", "darwin")):
        pkg_dir = os.path.dirname(__file__)
        src_tree_path = os.path.dirname(os.path.dirname(pkg_dir))
        ssl_cert_location = os.path.join(src_tree_path,
                                         "data")
    else:
        ssl_cert_location = '/etc/ssl/certs'

    return ssl_cert_location


@defer.inlineCallbacks
def ping_url(url, email, credentials):
    """Ping the 'url' with the 'email' attached to it.

    Sign the request with 'credentials'. The url must not be None.

    """
    logger.info('Pinging server using url: %r, email: %r.',
                url, email)
    assert isinstance(url, compat.text_type), 'Url %r must be unicode' % url

    target_url = url
    try:
        target_url = url.format(email=email)
    except IndexError:  # tuple index out of range
        target_url = url.format(email)  # format the first substitution

    if target_url == url:
        logger.debug('Original url (%r) could not be formatted, '
                     'appending email (%r).', url, email)
        assert url.endswith('/'), 'Url %r must end with /.' % url
        target_url = url + email

    wc = webclient.webclient_factory()
    try:
        logger.debug('Opening the url %r with webclient.request.', url)
        response = yield wc.request(target_url, oauth_credentials=credentials)
        logger.debug('Url %r opened. Response content: %r.',
                     url, response.content)
        defer.returnValue(response)
    finally:
        wc.shutdown()
