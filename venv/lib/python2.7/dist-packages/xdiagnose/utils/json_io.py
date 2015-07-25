#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""JsonIO provides a convenient wrapper to load and save JSON data to files"""

import os
import json
import jsonpickle

from debug import ERR
from file_io import load_file

# TODO: Tests

class JsonIO(object):
    def __init__(self, filename):
        self.filename = filename
        jsonpickle.set_encoder_options('simplejson', sort_keys=True, indent=4)

    def convert_from_dict(self):
        '''Provides handling of post-processing of data.

        By default, this just passes through the data unchanged.
        Subclasses can override this routine to define their own
        custom conversion logic.

        This routine must return a function which takes a data dict
        and return a class object.
        '''
        def converter(data):
            return data
        return converter

    def convert_to_dict(self):
        '''Handles conversion of an object to a serializable dict.

        By default, this just passes through the data unchanged.
        Subclasses can override this routine to define their own
        custom conversion logic.

        This routine must return a function that converts a data
        object into a plain dict.
        '''
        def converter(data):
            return data
        return converter

    def read(self):
        lines = load_file(self.filename)
        if not lines:
            return None
        json_data = jsonpickle.decode('\n'.join(lines))
        return json_data

    def write(self, data):
        ftmp = self.filename+'.tmp'
        pathname = os.path.dirname(self.filename)
        if pathname and not os.path.exists(pathname):
            os.makedirs(pathname)

        try:
            if os.path.exists(ftmp):
                os.unlink(ftmp)
            file = open(ftmp, 'w')
            text = jsonpickle.encode(data)
            file.write(text + "\n")
            file.close()
        except IOError:
            ERR("Failed to save %s to file %s" %(type(data), ftmp))
            raise
            return

        try:
            os.rename(ftmp, self.filename)
        except IOError:
            os.unlink(self.filename)
            os.rename(ftmp, self.filename)

# vi:set ts=4 sw=4 expandtab:
