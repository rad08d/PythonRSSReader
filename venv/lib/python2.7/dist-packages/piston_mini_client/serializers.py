# -*- coding: utf-8 -*-
# Copyright 2010-2012 Canonical Ltd.  This software is licensed under the
# GNU Lesser General Public License version 3 (see the file LICENSE).

"""Classes that define ways for your API methods to serialize arguments
into a request."""

__all__ = [
    'JSONSerializer',
    'FormSerializer',
]

import json
try:
    from urllib import urlencode
except ImportError:
    # Python 3
    from urllib.parse import urlencode

from piston_mini_client import PistonSerializable


class JSONSerializer(object):
    """A serializer that renders JSON.

    This is the default serializer for content type *application/json*.
    """
    class PistonSerializableEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, PistonSerializable):
                return o.as_serializable()
            return json.JSONEncoder.default(self, o)

    def serialize(self, obj):
        """Serialize ``obj`` into JSON.

        As well as the usual basic JSON-encodable types, this serializer knows
        how to serialize ``PistonSerializable`` objects.
        """
        return json.dumps(obj, cls=self.PistonSerializableEncoder)


class FormSerializer(object):
    """A serializer that renders form-urlencoded content.

    This is the default serializer for content type
    *application/x-www-form-urlencoded*.

    .. note:: this serializer doesn't support nested structures.

    It should be initialized with a dictionary, sequence of pairs, or
    ``PistonSerializable``.
    """
    def serialize(self, obj):
        if isinstance(obj, PistonSerializable):
            obj = obj.as_serializable()
        try:
            return urlencode(obj)
        except TypeError:
            raise TypeError("Attempted to serialize invalid object %s" % obj)


serializers = {
    'application/json': JSONSerializer(),
    'application/x-www-form-urlencoded': FormSerializer(),
}


def get_serializer(content_type):
    return serializers.get(content_type)
