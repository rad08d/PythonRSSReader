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
"""Some generated constants.

DO NO EDIT! This is a generated file. It will be built at installation time.

"""

import os
import platform
import urllib

from ubuntu_sso import SSO_UONE_BASE_URL

VERSION = '13.10'
PROJECT_NAME = 'ubuntu-sso-client'
PROJECT_DIR = os.path.join('/usr', 'share', PROJECT_NAME)
BIN_DIR = os.path.join('/usr', 'lib', PROJECT_NAME)

# Ubuntu One sso constants
APP_NAME = u"Ubuntu One"
TC_URL = u"%s/terms/" % SSO_UONE_BASE_URL
POLICY_URL = u"%s/privacy/" % SSO_UONE_BASE_URL
BASE_PING_URL = \
    u"%s/oauth/sso-finished-so-get-tokens/{email}" % SSO_UONE_BASE_URL


def platform_data():
    result = {'platform': platform.system(),
              'platform_version': platform.release(),
              'platform_arch': platform.machine(),
              'client_version': VERSION}
    # urlencode will not encode unicode, only bytes
    result = urllib.urlencode(result)
    return result

# the result of platform_data is given by urlencode, encoded with ascii
PING_URL = BASE_PING_URL + u"?" + platform_data().decode('ascii')
