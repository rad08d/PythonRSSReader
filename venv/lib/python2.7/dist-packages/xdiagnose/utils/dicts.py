#!/usr/bin/env python
# -*- coding: utf-8 -*-

def dicts_equal(dict_a, dict_b):
    if dict_a is None or dict_b is None:
        return False

    # Check if keys are the same
    if set(dict_a.keys()) != set(dict_b.keys()):
        return False

    # Check if values are the same
    for a,b in zip(dict_a.iteritems(), dict_b.iteritems()):
        if a != b:
            return False

    return True

# vi:set ts=4 sw=4 expandtab:
