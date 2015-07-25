#!/usr/bin/python3
# -*- coding: utf-8 -*-

import urllib
import lxml.html

from text import o2str

def tables_from_url(url):
    data = urllib.urlopen(url).read().decode('utf-8', 'replace')
    tree = lxml.html.fromstring(o2str(data))

    tables = []
    for tbl in tree.iterfind('.//table'):
        tele = []
        for tr in tbl.iterfind('.//tr'):
            try:
                text = [e.strip() for e in tr.xpath('.//text()') if
                len(e.strip()) > 0]
                tele.append(text)
            except:
                print(tr)
                raise
        yield tele

def data_from_url(url):
    '''Looks up first non-trivial data table from url'''
    for t in tables_from_url(url):
        if len(t) >= 5:
            return t

    raise Exception("No usable data returned from %s" %(url))


# vi:set ts=4 sw=4 expandtab:
