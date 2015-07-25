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

from exceptions import Exception
from time import sleep
from subprocess import (Popen, PIPE)

from debug import (stderr_msg, dbg, ERR)

# TODO: Make *_with_input be aliases calling the base routines
# TODO: Integrate use of dbg and ERR from utils

class ReturnCode(Exception):
    def __init__(self, code, errors=None):
        self.code = code
        if type(errors) in (list, tuple):
            self.errors = errors
        else:
            self.errors = [errors]

    def __str__(self):
        text = '\n'.join(self.errors)
        return "%sReturned error code %d" %(text, self.code)


def shell(command):
    """Executes command in a shell, returns stdout; prints errors to stderr"""
    dbg("shell: %s" %(' '.join(command)))
    p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
    output = "\n".join(p.stdout.readlines())
    if p.returncode:
        raise ReturnCode(p.returncode, p.stderr.readlines())
    return output

def shell_with_input(command, in_text):
    dbg("shell_with_input: %s" %(' '.join(command)))
    p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, stdin=PIPE)
    output, stderr = p.communicate(input=in_text)
    if p.returncode:
        raise ReturnCode(p.returncode, stderr)
    return output

def execute(command, in_text=None):
    """Executes command, returns stdout; prints errors to stderr"""
    dbg("execute: `%s`" %(' '.join(command)))
    if in_text is None:
        p = Popen(command, shell=False, stdout=PIPE, stderr=PIPE)
    else:
        p = Popen(command, shell=False, stdout=PIPE, stderr=PIPE, stdin=PIPE)
        dbg("execute: polling (%s)..." %(in_text))
        while p.poll() is None and p.stdin is not None:
            dbg("execute: Sending to process stdin")
            p.stdin.write(in_text)
            dbg("execute: sleeping")
            sleep(0.01)
    output = p.stdout.read()
    if p.returncode:
        dbg("Received return code %d" %(p.returncode))
        raise ReturnCode(p.returncode, p.stderr.readlines())
    return output

def execute_with_input(command, in_text):
    """Executes command, passing in_text to stdin if provided"""
    execute(command, in_text)

def is_X_running():
    # TODO: Reuse one of the above commands
    p = Popen(["xset", "-q"], stdout=PIPE, stderr=PIPE)
    p.communicate()
    if p.returncode != 0:
        print("Error")
    return p.returncode == 0
