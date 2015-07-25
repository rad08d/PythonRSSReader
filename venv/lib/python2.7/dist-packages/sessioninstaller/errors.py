#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Exception classes"""
# Copyright (C) 2010 Sebastian Heinlein <devel@glatzor.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

__author__  = "Sebastian Heinlein <devel@glatzor.de>"

import dbus
from functools import wraps
import inspect
import sys
import types

__all__ = ["convert_dbus_exception", "get_native_exception"]

# Create the exception classes on the fly
def _declare_module():
    module = types.ModuleType("_errors")
    for err in ["Failed", "Cancelled", "NoPackagesFound", "InternalError",
                "Forbidden"]:
        for interface in ["Query", "Modify"]:
            name = "%s%s" % (interface, err)
            cls = type(name, (dbus.DBusException,),
                       {"_dbus_error_name": \
                        "org.freedesktop.Packagekit.%s.%s" % (interface, err)})
            setattr(module, name, cls)
            __all__.append(name)
    return module
_errors = _declare_module()
sys.modules["_errors"] = _errors
from _errors import *

def convert_dbus_exception(func):
    """A decorator which maps a raised DBbus exception to a native one."""
    argnames, varargs, kwargs, defaults = inspect.getargspec(func)
    @wraps(func)
    def _convert_dbus_exception(*args, **kwargs):
        try:
            error_handler = kwargs["error_handler"]
        except KeyError:
            _args = list(args)
            try:
                index = argnames.index("error_handler")
                error_handler = _args[index]
            except ValueError:
                pass
            else:
                _args[index] = \
                        lambda err: error_handler(get_native_exception(err))
                args = tuple(_args)
        else:
            kwargs["error_handler"] = \
                    lambda err: error_handler(get_native_exception(err))
        try:
            return func(*args, **kwargs)
        except dbus.exceptions.DBusException, error:
            raise get_native_exception(error)
    return _convert_dbus_exception

def get_native_exception(error):
    """Map a DBus exception to a native one. This allows to make use of
    try/except on the client side without having to check for the error name.
    """
    dbus_name = error.get_dbus_name()
    dbus_msg = error.get_dbus_message()
    for attr in _errors.__dict__.values():
        try:
            if dbus_name == attr._dbus_error_name:
                return attr(dbus_msg)
        except AttributeError:
            continue
    return error

# vim:ts=4:sw=4:et
