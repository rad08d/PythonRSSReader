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

from datetime import (
    datetime,
    timedelta
    )


def week_start(dt=None):
    """
    Calculates the ISO week start datetime for the given time
    @param dt: Datetime to calculate from (defaults to now)
    @returns: datetime of week start
    """
    if dt is None:
        dt = datetime.today()
    week_days = datetime.isoweekday(dt) % 7
    week_start = dt - timedelta(days=week_days)
    return week_start.replace(hour=0, minute=0, second=0, microsecond=0)

def utc_date_to_local_datetime(dt):
    if dt is None:
        return None
    utc_offset = datetime.utcnow() - datetime.now()
    return datetime.strptime(dt, "%Y%m%dT%H%M%SZ") - utc_offset

def utc_date_to_isocalendar(timestamp):
    """Converts '20120216T025651Z' into (year, week, weekday) tuple"""
    if timestamp is None:
        return None
    elif type(timestamp) is tuple:
        # Assume already in tuple form, just pass-thru
        return timestamp
    dt = utc_date_to_local_datetime(timestamp)
    if dt is None:
        return None
    return dt.isocalendar()

def total_seconds(td):
    tsec = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6)/10**6
    return tsec

if __name__ == '__main__':
    print(week_start())

    td = timedelta(days=10, seconds=2.999)
    dt = datetime.today() - td
    print(week_start(dt))

    print("%d == %d\n" %(total_seconds(td), td.total_seconds()))
