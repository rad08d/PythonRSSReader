#!/usr/bin/python3
# -*- coding: utf-8 -*-

def to_list(value):
    if type(value) is list:
        return value
    if value.endswith(','):
        value = value[:-1].strip()
    return [x.strip() for x in value.split(',')]

# vi:set ts=4 sw=4 expandtab:
