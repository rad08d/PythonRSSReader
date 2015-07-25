# -*- coding: utf-8 -*-
# Copyright 2010-2012 Canonical Ltd.  This software is licensed under the
# GNU Lesser General Public License version 3 (see the file LICENSE).

import httplib2

try:
    # ensure we have a version with a fix for
    #  http://code.google.com/p/httplib2/issues/detail?id=38
    # and if not, patch in our own socks with the fix
    from httplib2.socks import PROXY_TYPE_HTTP_NO_TUNNEL
    from httplib2 import socks
except ImportError:
    from piston_mini_client import socks
    httplib2.socks = socks

import errno
import json
import os
import socket
from datetime import datetime
from functools import wraps
try:
    from urlparse import urlparse, urlunparse
except ImportError:
    # Python 3
    from urllib.parse import urlparse, urlunparse
try:
    from urllib import urlencode
except ImportError:
    # Python 3
    from urllib.parse import urlencode

from piston_mini_client.failhandlers import (
    APIError,
    ExceptionFailHandler,
    format_request,
    format_response,
    SocketError,
    TimeoutError,
)
from piston_mini_client.consts import (
    DISABLE_SSL_VALIDATION_ENVVAR,
    LOG_FILENAME_ENVVAR,
    TIMEOUT_ENVVAR,
)

try:
    unicode
    bytes = str
except NameError:
    # Python 3
    basestring = unicode = str


class OfflineModeException(Exception):
    pass


# taken from lazr.restfulclients _browser.py file to work around
# the problem that ecryptfs is very unhappy about long filenames
# upstream commented here:
#   http://code.google.com/p/httplib2/issues/detail?id=92
MAXIMUM_CACHE_FILENAME_LENGTH = 143
from httplib2 import _md5, re_url_scheme, re_slash


def safename(filename):
    """Return a filename suitable for the cache.

    Strips dangerous and common characters to create a filename we
    can use to store the cache in.
    """
    # this is a stock httplib2 copy
    try:
        ufilename = filename
        if isinstance(filename, bytes):
            ufilename = filename.decode('utf-8')
        if re_url_scheme.match(ufilename.encode('utf-8')):
            filename = ufilename.encode('idna')
    except UnicodeError:
        pass
    if isinstance(filename, unicode):
        filename = filename.encode('utf-8')
    filemd5 = _md5(filename).hexdigest()
    filename = re_url_scheme.sub("".encode('utf-8'), filename)
    filename = re_slash.sub(",".encode('utf-8'), filename)

    # This is the part that we changed. In stock httplib2, the
    # filename is trimmed if it's longer than 200 characters, and then
    # a comma and a 32-character md5 sum are appended. This causes
    # problems on eCryptfs filesystems, where the maximum safe
    # filename length is closer to 143 characters.
    #
    # We take a (user-hackable) maximum filename length from
    # RestfulHttp and subtract 33 characters to make room for the comma
    # and the md5 sum.
    #
    # See:
    #  http://code.google.com/p/httplib2/issues/detail?id=92
    #  https://bugs.launchpad.net/bugs/344878
    #  https://bugs.launchpad.net/bugs/545197
    maximum_filename_length = MAXIMUM_CACHE_FILENAME_LENGTH
    maximum_length_before_md5_sum = maximum_filename_length - 32 - 1
    if len(filename) > maximum_length_before_md5_sum:
        filename = filename[:maximum_length_before_md5_sum]
    r = ",".encode('utf-8').join((filename, filemd5.encode('utf-8')))
    return r.decode("utf-8")


def _parse_json(json_data):
    """Return a Python data structure corresponding to ``json_data``.

    Use this rather than ``json.loads`` directly to get a richer error message
    when JSON data cannot be decoded.

    :param json_data: A string containing JSON data.
    :raises ValueError: If the JSON data could not be parsed.
    :return: A Python data structure.
    """
    try:
        return json.loads(json_data)
    except ValueError:
        raise APIError('No JSON object could be decoded', body=json_data)


def returns_json(func):
    """The response data will be deserialized using a simple JSON decoder"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        body = func(*args, **kwargs)
        if not isinstance(body, basestring):
            return body
        return _parse_json(body)
    return wrapper


def returns(cls, none_allowed=False):
    """The response data will be deserialized into an instance of ``cls``.

    The provided class should be a descendant of ``PistonResponseObject``,
    or some other class that provides a ``from_response`` method.

    ``none_allowed``, defaulting to ``False``, specifies whether or not
    ``None`` is a valid response. If ``True`` then the api can return ``None``
    instead of a ``PistonResponseObject``.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            body = func(self, *args, **kwargs)
            if not isinstance(body, basestring):
                return body
            return cls.from_response(body, none_allowed)
        return wrapper
    return decorator


def returns_list_of(cls):
    """The response data will be deserialized into a list of ``cls``.

    The provided class should be a descendant of ``PistonResponseObject``,
    or some other class that provides a ``from_response`` method.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            body = func(self, *args, **kwargs)
            if not isinstance(body, basestring):
                return body
            data = _parse_json(body)
            items = []
            for datum in data:
                items.append(cls.from_dict(datum))
            return items
        return wrapper
    return decorator


class PistonResponseObject(object):
    """Base class for objects that are returned from api calls."""
    @classmethod
    def from_response(cls, body, none_allowed=False):
        data = _parse_json(body)
        if none_allowed and data is None:
            return data
        obj = cls.from_dict(data)
        return obj

    @classmethod
    def from_dict(cls, data):
        obj = cls()
        for key, value in data.items():
            setattr(obj, key, value)
        return obj


class PistonSerializable(object):
    """Base class for objects that want to be used as api call arguments.

    Children classes should at least redefine ``_atts`` to state the list of
    attributes that will be serialized into each request.
    """
    _atts = ()

    def __init__(self, **kwargs):
        for (key, value) in kwargs.items():
            setattr(self, key, value)

    def as_serializable(self):
        """Return a serializable representation of this object."""
        data = {}
        for att in self._atts:
            if not hasattr(self, att):
                raise ValueError(
                    "Attempted to serialize attribute '%s'" % att)
            data[att] = getattr(self, att)
        return data

    def _as_serializable(self):
        """_as_serializable is deprecated; use as_serializable() instead."""
        import warnings
        warnings.warn("_as_serializable is deprecated; "
                      "use as_serializable instead", DeprecationWarning)
        return self.as_serializable()


class PistonRequester(object):
    """This class provides methods to make http requests slightly easier.

    It's a wrapper around ``httplib2`` that takes care of a few common tasks
    around making HTTP requests: authentication, proxies, serialization,
    timeouts, etc.

    To use it, just instantiate it and call ``get``, ``post``, ``put`` or
    ``delete`` to do various requests.

    If you want to wrap an HTTP API, you probably want to make a subclass of
    ``PistonAPI``, which uses this class.
    """

    SUPPORTED_SCHEMAS = ("http", "https")

    def __init__(self, cachedir=None, auth=None,
                 offline_mode=False, disable_ssl_validation=False,
                 log_filename=None, timeout=None, fail_handler=None,
                 extra_headers=None, serializers=None,
                 default_content_type='application/json'):
        """Initialize a ``PistonRequester``.

        ``cachedir`` will be used as ``httplib2``'s cache directory if
        provided.

        ``auth`` can be an instance of ``BasicAuthorizer`` or
        ``OAuthAuthorizer`` or any object that provides a ``sign_request``
        method.  If ``auth`` is ``None`` you'll only be able to make public
        API calls.  See :ref:`authentication` for details.

        ``disable_ssl_validation`` will skip server SSL certificate
        validation when using secure connections.  ``httplib2`` < 0.7.0
        doesn't support certificate validation anyway, so if you're using an
        older ``httplib2`` this will have no effect.

        ``offline_mode`` will not touch the network.  In this case only cached
        results will be available.

        If you pass in a ``log_filename``, all requests and responses
        including headers will be logged to this file.
        """
        if cachedir:
            self._create_dir_if_needed(cachedir)
            self._httplib2_cache = httplib2.FileCache(cachedir, safe=safename)
        else:
            self._httplib2_cache = None
        self._auth = auth
        self._offline_mode = offline_mode
        self._disable_ssl_validation = disable_ssl_validation
        self._timeout = timeout
        # create one httplib2.Http object per scheme so that we can
        # have per-scheme proxy settings (see also Issue 26
        #   http://code.google.com/p/httplib2/issues/detail?id=26)
        self._http = {}
        for scheme in self.SUPPORTED_SCHEMAS:
            self._http[scheme] = self._get_http_obj_for_scheme(scheme)
        if serializers is None:
            serializers = {}
        self._serializers = {}
        self._log_filename = log_filename
        self._default_content_type = default_content_type
        if fail_handler is None:
            fail_handler = ExceptionFailHandler
        self._fail_handler = fail_handler
        self._extra_headers = extra_headers

    def _create_dir_if_needed(self, path):
        """ helper that checks/creates path if it does not exists
        """
        try:
            os.makedirs(path)
        except OSError as e:
            # fixes race LP: #803280
            if e.errno != errno.EEXIST:
                raise

    def _get_http_obj_for_scheme(self, scheme):
        proxy_info = self._get_proxy_info(scheme)
        http = None
        check_disabled_in_env = os.environ.get(DISABLE_SSL_VALIDATION_ENVVAR)
        if self._disable_ssl_validation or check_disabled_in_env:
            try:
                http = httplib2.Http(
                    cache=self._httplib2_cache,
                    timeout=self._timeout,
                    disable_ssl_certificate_validation=True,
                    proxy_info=proxy_info)
            except TypeError:
                # httplib2 < 0.7.0 doesn't support cert validation anyway
                pass
        if http is None:
            http = httplib2.Http(cache=self._httplib2_cache,
                                 timeout=self._timeout, proxy_info=proxy_info)
        return http

    def _get_proxy_info(self, scheme):
        envvar = "%s_proxy" % scheme
        if envvar in os.environ:
            url = urlparse(os.environ[envvar])
            user_pass, sep, host_and_port = url.netloc.rpartition("@")
            user, sep, passw = user_pass.partition(":")
            host, sep, port = host_and_port.partition(":")
            if port:
                port = int(port)
            proxy_type = socks.PROXY_TYPE_HTTP
            if scheme == "http":
                # this will not require the CONNECT acl from squid and
                # is good enough for http connections
                proxy_type = socks.PROXY_TYPE_HTTP_NO_TUNNEL
            proxy_info = httplib2.ProxyInfo(
                proxy_type=proxy_type,
                proxy_host=host,
                proxy_port=port or 8080,
                proxy_user=user or None,
                proxy_pass=passw or None)
            return proxy_info
        return None

    def _prepare_request(self, data=None, content_type=None,
                         extra_headers=None):
        """Put together a set of headers and a body for a request.

        If ``content_type`` is not provided, ``self._default_content_type``
        will be assumed.

        You probably never need to call this method directly.
        """
        if content_type is None:
            content_type = self._default_content_type
        body = self._prepare_body(data, content_type)
        headers = self._prepare_headers(content_type, extra_headers)
        return body, headers

    def _prepare_headers(self, content_type=None, extra_headers=None):
        """Put together and return a complete set of headers.

        If ``content_type`` is provided, it will be added as
        the Content-type header.

        Any provided ``extra_headers`` will be added last.

        You probably never need to call this method directly.
        """
        headers = {}
        if content_type:
            headers['Content-Type'] = content_type
        if self._extra_headers is not None:
            headers.update(self._extra_headers)
        if extra_headers is not None:
            headers.update(extra_headers)
        return headers

    def _prepare_body(self, data=None, content_type=None):
        """Serialize data into a request body.

        ``data`` will be serialized into a string, according to
        ``content_type``.

        You probably never need to call this method directly.
        """
        body = data
        if not isinstance(data, basestring):
            serializer = self._get_serializer(content_type)
            body = serializer.serialize(data)
        return body

    def request_url(self, url, method, body='', headers=None):
        """Perform an HTTP request.

        You probably want to call one of the ``get``, ``post``, ``put``
        methods instead.
        """
        if headers is None:
            headers = {}

        # in offline mode either get it from the cache or return None
        if self._offline_mode:
            if method in ('POST', 'PUT'):
                err = "method '%s' not allowed in offline-mode" % method
                raise OfflineModeException(err)
            return self._get_from_cache(url)

        scheme = urlparse(url).scheme

        if self._auth:
            self._auth.sign_request(url, method, body, headers)
        if self._log_filename:
            self._dump_request(url, method, body, headers)
        try:
            response, response_body = self._http[scheme].request(
                url, method=method, body=body, headers=headers)
        except AttributeError as e:
            # Special case out httplib2's way of telling us unable to connect
            if e.args[0] == "'NoneType' object has no attribute 'makefile'":
                raise APIError('Unable to connect to %s' % (url,))
            else:
                raise
        except socket.timeout as e:
            raise TimeoutError('Timed out attempting to connect to %s' %
                               (url,))
        except socket.error as e:
            msg = 'connecting to %s: %s' % (url, e.strerror)
            raise SocketError(msg)
        if self._log_filename:
            self._dump_response(response, response_body)
        handler = self._fail_handler(url, method, body, headers)
        body = handler.handle(response, response_body)
        return body

    def _dump_request(self, url, method, body, headers):
        try:
            with open(self._log_filename, 'a') as f:
                formatted = format_request(url, method, body, headers)
                f.write("{0}: {1}".format(datetime.now(), formatted))
        except IOError:
            pass

    def _dump_response(self, response, body):
        try:
            with open(self._log_filename, 'a') as f:
                formatted = format_response(response, body)
                f.write("{0}: {1}".format(datetime.now(), formatted))
        except IOError:
            pass

    def _get_from_cache(self, url):
        """ get a given url from the cachedir even if its expired
            or return None if no data is available
        """
        scheme = urlparse(url).scheme
        if self._http[scheme].cache:
            cached_value = self._http[scheme].cache.get(
                httplib2.urlnorm(url)[-1])
            if cached_value:
                info, content = cached_value.decode("utf-8").split(
                    '\r\n\r\n', 1)
                return content

    def _get_serializer(self, content_type=None):
        # Import here to avoid a circular import
        from piston_mini_client.serializers import get_serializer
        if content_type is None:
            content_type = self._default_content_type
        default_serializer = get_serializer(content_type)
        return self._serializers.get(content_type, default_serializer)

    def get(self, url, args=None, extra_headers=None):
        """Perform an HTTP GET request from ``url``.

        If provided, ``args`` should be a dict specifying additional GET
        arguments that will be encoded on to the end of the url.

        ``extra_headers`` is an optional dictionary of header key/values that
        will be added to the http request.
        """
        if args is not None:
            if '?' in url:
                url += '&'
            else:
                url += '?'
            url += urlencode(args)
        headers = self._prepare_headers(extra_headers=extra_headers)
        return self.request_url(url, method='GET', headers=headers)

    def post(self, url, data=None, content_type=None, extra_headers=None):
        """Perform an HTTP POST request to ``url``.

        ``data`` should be:

         - A string, in which case it will be used directly as the request's
           body, or
         - A ``list``, ``dict``, ``int``, ``bool`` or ``PistonSerializable``
           (something with an ``as_serializable`` method) or even ``None``,
           in which case it will be serialized into a string according to
           ``content_type``.

        If ``content_type`` is ``None``, ``self._default_content_type`` will
        be used.

        ``extra_headers`` is an optional dictionary of header key/values that
        will be added to the http request.
        """
        body, headers = self._prepare_request(
            data, content_type, extra_headers=extra_headers)
        return self.request_url(
            url, method='POST', body=body, headers=headers)

    def put(self, url, data=None, content_type=None, extra_headers=None):
        """Perform an HTTP PUT request to ``url``.

        ``data`` should be:

         - A string, in which case it will be used directly as the request's
           body, or
         - A ``list``, ``dict``, ``int``, ``bool`` or ``PistonSerializable``
           (something with an ``as_serializable`` method) or even ``None``,
           in which case it will be serialized into a string according to
           ``content_type``.

        If ``content_type`` is ``None``, ``self._default_content_type`` will
        be used.

        ``extra_headers`` is an optional dictionary of header key/values that
        will be added to the http request.
        """
        body, headers = self._prepare_request(
            data, content_type, extra_headers=extra_headers)
        return self.request_url(
            url, method='PUT', body=body, headers=headers)

    def delete(self, url, extra_headers=None):
        """Perform an HTTP DELETE request on ``url``.

        ``extra_headers`` is an optional dictionary of header key/values that
        will be added to the http request.
        """
        headers = self._prepare_headers(extra_headers=extra_headers)
        return self.request_url(url, method='DELETE', headers=headers)


class _DeprecatedRequesterDecorator(object):

    __DEPRECATED_ATTRIBUTES = {
        '_httplib2_cache': '_httplib2_cache',
        '_auth': '_auth',
        '_offline_mode': '_offline_mode',
        '_disable_ssl_validation': '_disable_ssl_validation',
        '_timeout': '_timeout',
        '_http': '_http',
    }

    def __warn(self, name):
        import warnings
        warnings.warn(
            "PistonAPI.%s is deprecated; Use PistonAPI._requester.%s "
            "instead.  Both are likely to break in the future.  Please "
            "file a bug if you'd like them not to" % (name, name),
            DeprecationWarning,
            stacklevel=4)

    def __getattr__(self, name):
        if name in self.__DEPRECATED_ATTRIBUTES:
            self.__warn(name)
            return getattr(self._requester, self.__DEPRECATED_ATTRIBUTES[name])
        raise AttributeError(
            '%r object has no attribute %r'
            % (self.__class__.__name__, name))

    def __setattr__(self, name, value):
        if name in self.__DEPRECATED_ATTRIBUTES:
            self.__warn(name)
            setattr(self._requester, self.__DEPRECATED_ATTRIBUTES[name], value)
        else:
            super(_DeprecatedRequesterDecorator, self).__setattr__(name, value)

    def __deprecated_call(self, method_name, *args, **kwargs):
        self.__warn(method_name)
        method = getattr(self._requester, method_name)
        return method(*args, **kwargs)

    def _create_dir_if_needed(self, path):
        """ helper that checks/creates path if it does not exists
        """
        return self.__deprecated_call('_create_dir_if_needed', path)

    def _get_http_obj_for_scheme(self, scheme):
        return self.__deprecated_call('_get_http_obj_for_scheme', scheme)

    def _get_proxy_info(self, scheme):
        return self.__deprecated_call('_get_proxy_info', scheme)

    def _prepare_request(self, data=None, content_type=None,
                         extra_headers=None):
        """Put together a set of headers and a body for a request.

        If ``content_type`` is not provided, ``self.default_content_type``
        will be assumed.

        You probably never need to call this method directly.
        """
        return self.__deprecated_call(
            '_prepare_request', data=data, content_type=content_type,
            extra_headers=extra_headers)

    def _prepare_headers(self, content_type=None, extra_headers=None):
        """Put together and return a complete set of headers.

        If ``content_type`` is provided, it will be added as
        the Content-type header.

        Any provided ``extra_headers`` will be added last.

        You probably never need to call this method directly.
        """
        return self.__deprecated_call(
            '_prepare_headers', content_type=content_type,
            extra_headers=extra_headers)

    def _prepare_body(self, data=None, content_type=None):
        """Serialize data into a request body.

        ``data`` will be serialized into a string, according to
        ``content_type``.

        You probably never need to call this method directly.
        """
        return self.__deprecated_call(
            '_prepare_body', data=data, content_type=content_type)

    def _dump_request(self, url, method, body, headers):
        return self.__deprecated_call(
            '_dump_request', url, method, body, headers)

    def _dump_response(self, response, body):
        return self.__deprecated_call('_dump_response', response, body)

    def _get_from_cache(self, url):
        """ get a given url from the cachedir even if its expired
            or return None if no data is available
        """
        return self.__deprecated_call('_get_from_cache', url)

    def _get_serializer(self, content_type=None):
        return self.__deprecated_call(
            '_get_serializer', content_type=content_type)


class PistonAPI(_DeprecatedRequesterDecorator):
    """This class provides methods to make http requests slightly easier.

    It's a wrapper around ``httplib2`` to allow for a bit of state to
    be stored (like the service root) so that you don't need to repeat
    yourself as much.

    It's not intended to be used directly.  Children classes should implement
    methods that actually call out to the api methods.

    When you define your API's methods you'll
    want to just call out to the ``_get``, ``_post``, ``_put`` or ``_delete``
    methods provided by this class.
    """

    SUPPORTED_SCHEMAS = PistonRequester.SUPPORTED_SCHEMAS
    default_service_root = ''
    default_timeout = None
    fail_handler = ExceptionFailHandler
    extra_headers = None
    serializers = None
    default_content_type = 'application/json'

    # Attributes that are forwarded to PistonRequester for backwards
    # compatibility reasons, but are not deprecated.
    #
    # Should only have attributes that users are expected to set on
    # constructed PistonAPI instances.
    __FORWARDED_ATTRIBUTES = {
        'serializers': '_serializers',
        'log_filename': '_log_filename',
        'default_content_type': '_default_content_type',
        'fail_handler': '_fail_handler',
        'extra_headers': '_extra_headers',
    }

    def __init__(self, service_root=None, cachedir=None, auth=None,
                 offline_mode=False, disable_ssl_validation=False,
                 log_filename=None, timeout=None):
        """Initialize a ``PistonAPI``.

        ``service_root`` is the url to the server's service root.
        Children classes can provide a ``default_service_root`` class
        attribute that will be used if ``service_root`` is ``None``.

        ``timeout`` will be used as a socket timeout for all calls this
        instance makes.  To explicitly set no timeout, set timeout=0.  The
        default timeout=None will first check for an environment variable
        ``PISTON_MINI_CLIENT_DEFAULT_TIMEOUT`` and try to use that. If this
        environment variable is not found or it is an invalid float, the
        class's ``default_timeout`` will be used.  Finally, if the class's
        default is also None, Python's default timeout for sockets will be
        used.  All these should be in seconds.

        For all other arguments, see ``PistonRequester``.
        """
        if timeout is None:
            try:
                timeout = float(os.environ.get(TIMEOUT_ENVVAR))
            except (TypeError, ValueError):
                timeout = self.default_timeout
        if log_filename is None:
            log_filename = os.environ.get(LOG_FILENAME_ENVVAR)
        self._requester = PistonRequester(
            cachedir=cachedir,
            auth=auth,
            offline_mode=offline_mode,
            disable_ssl_validation=disable_ssl_validation,
            log_filename=log_filename,
            timeout=timeout,
            fail_handler=self.fail_handler,
            extra_headers=self.extra_headers,
            default_content_type=self.default_content_type,
            serializers=self.serializers)
        if service_root is None:
            service_root = self.default_service_root
        if not service_root:
            raise ValueError("No service_root provided, and no default found")
        parsed_service_root = urlparse(service_root)
        scheme = parsed_service_root.scheme
        if scheme not in self.SUPPORTED_SCHEMAS:
            raise ValueError("service_root's scheme must be http or https")
        self._service_root = service_root
        self._parsed_service_root = list(parsed_service_root)

    def __getattr__(self, name):
        if name in self.__FORWARDED_ATTRIBUTES:
            return getattr(self._requester, self.__FORWARDED_ATTRIBUTES[name])
        return super(PistonAPI, self).__getattr__(name)

    def __setattr__(self, name, value):
        if name in self.__FORWARDED_ATTRIBUTES:
            setattr(self._requester, self.__FORWARDED_ATTRIBUTES[name], value)
        super(PistonAPI, self).__setattr__(name, value)

    def _request(self, path, method, body='', headers=None, scheme=None):
        """Perform an HTTP request.

        You probably want to call one of the ``_get``, ``_post``, ``_put``
        methods instead.
        """
        url = self._path2url(path, scheme)
        return self._requester.request_url(
            url, method, body=body, headers=headers)

    def _path2url(self, path, scheme=None):
        if scheme is None:
            service_root = self._service_root
        else:
            parts = [scheme] + self._parsed_service_root[1:]
            service_root = urlunparse(parts)
        return (service_root.strip('/') + '/' + path.lstrip('/'))

    def _get(self, path, args=None, scheme=None, extra_headers=None):
        """Perform an HTTP GET request.

        The provided ``path`` is appended to this resource's ``_service_root``
        attribute to obtain the absolute URL that will be requested.

        If provided, ``args`` should be a dict specifying additional GET
        arguments that will be encoded on to the end of the url.

        ``scheme`` must be one of *http* or *https*, and will determine the
        scheme used for this particular request.  If not provided the
        service_root's scheme will be used.

        ``extra_headers`` is an optional dictionary of header key/values that
        will be added to the http request.
        """
        return self._requester.get(
            self._path2url(path, scheme), args=args,
            extra_headers=extra_headers)

    def _post(self, path, data=None, content_type=None, scheme=None,
              extra_headers=None):
        """Perform an HTTP POST request.

        The provided ``path`` is appended to this api's ``_service_root``
        attribute to obtain the absolute URL that will be requested.  ``data``
        should be:

         - A string, in which case it will be used directly as the request's
           body, or
         - A ``list``, ``dict``, ``int``, ``bool`` or ``PistonSerializable``
           (something with an ``as_serializable`` method) or even ``None``,
           in which case it will be serialized into a string according to
           ``content_type``.

        If ``content_type`` is ``None``, ``self.default_content_type`` will
        be used.

        ``scheme`` must be one of *http* or *https*, and will determine the
        scheme used for this particular request.  If not provided the
        service_root's scheme will be used.

        ``extra_headers`` is an optional dictionary of header key/values that
        will be added to the http request.
        """
        return self._requester.post(
            self._path2url(path, scheme), data=data,
            content_type=content_type, extra_headers=extra_headers)

    def _put(self, path, data=None, content_type=None, scheme=None,
             extra_headers=None):
        """Perform an HTTP PUT request.

        The provided ``path`` is appended to this api's ``_service_root``
        attribute to obtain the absolute URL that will be requested.  ``data``
        should be:

         - A string, in which case it will be used directly as the request's
           body, or
         - A ``list``, ``dict``, ``int``, ``bool`` or ``PistonSerializable``
           (something with an ``as_serializable`` method) or even ``None``,
           in which case it will be serialized into a string according to
           ``content_type``.

        If ``content_type`` is ``None``, ``self.default_content_type`` will be
        used.

        ``scheme`` must be one of *http* or *https*, and will determine the
        scheme used for this particular request.  If not provided the
        service_root's scheme will be used.

        ``extra_headers`` is an optional dictionary of header key/values that
        will be added to the http request.
        """
        return self._requester.put(
            self._path2url(path, scheme), data=data,
            content_type=content_type, extra_headers=extra_headers)

    def _delete(self, path, scheme=None, extra_headers=None):
        """Perform an HTTP DELETE request.

        The provided ``path`` is appended to this resource's ``_service_root``
        attribute to obtain the absolute URL that will be requested.

        ``scheme`` must be one of *http* or *https*, and will determine the
        scheme used for this particular request.  If not provided the
        service_root's scheme will be used.

        ``extra_headers`` is an optional dictionary of header key/values that
        will be added to the http request.
        """
        return self._requester.delete(
            self._path2url(path, scheme), extra_headers=extra_headers)


__version__ = '0.7.4'
