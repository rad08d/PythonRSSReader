#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2011-2012 Bryce Harrington <bryce@bryceharrington.org>
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

'''Command line options'''

import os.path
from optparse import OptionParser

class OptionHandler(OptionParser):
    '''Subclass of OptionParser that also tracks descriptions'''
    def __init__(self, info, app_name=None, arg_names=''):
        '''Creates an OptionParser instance for the options in this module'''
        prog = info.PROGNAME
        usage = None
        if app_name:
            app_name = os.path.basename(app_name)
            prog = "%s %s" %(app_name, info.PROGNAME)
            usage = "%s %s" %(app_name, arg_names)
        version = info.VERSION or "(UNRELEASED)"
        OptionParser.__init__(
            self,
            usage=usage,
            version="%s %s" %(prog, version),
            epilog="%s - %s" %(info.PROGNAME, info.SHORT_DESCRIPTION)
            )
        self.descriptions = []

    def add(self, short_opt, long_opt, **kwargs):
        '''Adds an option.

        Example::

          opt_hand.add("-d", "--debug",
                       help="Enable debug output",
                       action="store_true", default=False, dest="debug",
                       desc="Turns on verbose debugging output")
        '''
        item = {
            'opts': [short_opt, long_opt],
            'text': kwargs.get('desc', ''),
            }
        self.descriptions.append(item)
        del kwargs['desc']
        self.add_option(short_opt, long_opt, **kwargs)

