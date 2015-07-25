# Copyright (C) 2012 Canonical
#
# Authors:
#  Didier Roche <didrocks@ubuntu.com>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA


import json
import logging
import os

LOG = logging.getLogger(__name__)

def save_json_file_update(file_uri, content):
    '''Save local file in an atomic transaction'''

    if not content:
        LOG.warning("Empty content saved as \"\" for %s" % file_uri)
        content = {}

    LOG.debug("Saving updated %s to disk", file_uri)
    new_file = file_uri + '.new'

    try:
        with open(new_file, 'w') as f:
            json.dump(content, f)
        os.rename(new_file, file_uri)
        return True
    except IOError:
        LOG.error("Can't save update file for %s", file_uri)
        return False
