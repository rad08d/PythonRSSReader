#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2010-2012 Bryce Harrington <bryce@canonical.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


from __future__ import absolute_import, print_function, unicode_literals

'''High level package information'''
PROGNAME = 'xdiagnose'
VERSION = '3.0'
URL = 'http://launchpad.net/xdiagnose'
EMAIL = 'bryce@canonical.com'
DATE_STARTED = '2010-11-04'
DATE_COPYRIGHT = '2011'
LICENSE_URL = 'http://www.gnu.org/copyleft/gpl.html'

SHORT_DESCRIPTION = 'Analysis tools for troubleshooting X.org problems'

DESCRIPTION = """
This package is a friendly GUI application for diagnosing several
common X.org problems.
"""

class _contributor:
    '''Information about a person contributing to this project'''
    def __init__(self, name, email, started=None, roles=None, translating=None):
        self.name = name
        self.email = email
        self.started = started
        if roles is None:
            self.roles = []
        elif type(roles) is not list:
            self.roles = [roles]
        else:
            self.roles = roles
        self.translation_languages = translating
        return

    def to_dict(self):
        '''Returns the object in a dict suitable for json'''
        return self.__dict__

    @property
    def display_email(self):
        '''Formatted string version of email address'''
        if self.email:
            return '<%s>' % self.email
        else:
            return ''

    @property
    def display_roles(self):
        '''Formatted string version of roles list'''
        if self.roles:
            return '[%s]' % ','.join(self.roles)
        else:
            return ''

LEAD_DEVELOPER = _contributor(
    'Bryce Harrington', 'bryce@canonical.com', started='2010-11-04',
    roles=['lead', 'developer'], translating=None,
    )

CONTRIBUTORS = [
    _contributor(
        'Gabor Kelemen', 'kelemeng@ubuntu.com', started='2012-01-21',
        roles=['developer', 'translator'], translating=None),
    _contributor(
        'Jeff Lane', 'jeffrey.lane@canonical.com', started='2012-08-10',
        roles=['developer'], translating=None),
]


if __name__ == "__main__":
    print(PROGNAME, VERSION, URL)
    print("Copyright (C) %s %s <%s>" % (
        DATE_COPYRIGHT, LEAD_DEVELOPER.name, LEAD_DEVELOPER.email))
    print()
    for contributor in CONTRIBUTORS:
        print("%s %s %s" % (
            contributor.name,
            contributor.display_email,
            contributor.display_roles))
