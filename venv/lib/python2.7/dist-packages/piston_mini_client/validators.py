# -*- coding: utf-8 -*-
# Copyright 2010-2012 Canonical Ltd.  This software is licensed under the
# GNU Lesser General Public License version 3 (see the file LICENSE).

"""These decorators can be applied to your ``PistonAPI`` methods to control
how your method arguments are validated."""

import re
from functools import wraps

from .auth import BasicAuthorizer, OAuthAuthorizer
try:
    unicode
except NameError:
    # Python 3
    basestring = unicode = str


class ValidationException(Exception):
    pass


def validate_pattern(varname, pattern, required=True):
    """Validate argument ``varname`` against regex pattern ``pattern``.

    The provided argument for ``varname`` will need to inherit from
    ``basestring``.

    If ``required`` is ``False`` then the argument can be omitted entirely.
    Your method signature will need to provide a default value in this case.
    """
    if not pattern.endswith('$'):
        pattern = pattern + '$'

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if varname in kwargs:
                if not isinstance(kwargs[varname], basestring):
                    raise ValidationException(
                        "Argument '%s' must be a string" % varname)
                if not re.match(pattern, kwargs[varname]):
                    raise ValidationException(
                        "Argument '%s' must match pattern '%s'" %
                        (varname, pattern))
            elif required:
                raise ValidationException(
                    "Required named argument '%s' missing" % varname)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate(varname, cls, required=True):
    """Check that argument ``varname`` is of class ``cls``.

    If ``required`` is ``False`` then the argument can be omitted entirely.
    Your method signature will need to provide a default value in this case.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if varname in kwargs:
                if not isinstance(kwargs[varname], cls):
                    raise ValidationException(
                        "Argument '%s' must be a %s instead of %s" % (
                            varname, cls, type(kwargs[varname])))
            elif required:
                raise ValidationException(
                    "Required named argument '%s' missing" % varname)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_integer(varname, min=None, max=None, required=True):
    """Check that argument ``varname`` is between ``min`` and ``max``.

    The provided argument for ``varname`` will need to be of type ``int``.

    If ``required`` is ``False`` then the argument can be omitted entirely.
    Your method signature will need to provide a default value in this case.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if varname in kwargs:
                var = kwargs[varname]
                if not isinstance(var, int):
                    raise ValidationException(
                        "Argument '%s' must be an int" % varname)
                elif min is not None and var < min:
                    raise ValidationException(
                        "Argument '%s' must be at least %s" % (varname, min))
                elif max is not None and var > max:
                    raise ValidationException(
                        "Argument '%s' must be at most %s" % (varname, max))
            elif required:
                raise ValidationException(
                    "Required named argument '%s' missing" % varname)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def oauth_protected(func):
    """Only allow a method to be called with an ``OAuthAuthorizer`` available.

    To be able to call the method you've decorated you'll need to instantiate
    the ``PistonAPI`` providing a valid ``OAuthAuthorizer``.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, '_auth') or self._auth is None:
            raise ValidationException(
                "This method is OAuth protected.  "
                "Pass in an 'auth' argument to the constructor.")
        if not isinstance(self._auth, OAuthAuthorizer):
            raise ValidationException("self.auth must be an OAuthAuthorizer.")
        return func(self, *args, **kwargs)
    return wrapper


def basic_protected(func):
    """Only allow a method to be called with an ``BasicAuthorizer`` available.

    To be able to call the method you've decorated you'll need to instantiate
    the ``PistonAPI`` providing a valid ``BasicAuthorizer``.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, '_auth') or self._auth is None:
            raise ValidationException(
                "This method uses Basic auth.  "
                "Pass in an 'auth' argument to the constructor.")
        if not isinstance(self._auth, BasicAuthorizer):
            raise ValidationException("self.auth must be a BasicAuthorizer.")
        return func(self, *args, **kwargs)
    return wrapper
