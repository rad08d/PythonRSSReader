#!/usr/bin/python3
# -*- coding: utf-8 -*-

import urllib2

def readurl(url):
    try:
        fin = urllib2.urlopen(url)
        content = fin.read()
        fin.close()
        return content
    except:
        return None
