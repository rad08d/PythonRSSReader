# -*- coding: utf-8 -*-
#
# Copyright 2011-2013 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# In addition, as a special exception, the copyright holders give
# permission to link the code of portions of this program with the
# OpenSSL library under certain conditions as described in each
# individual source file, and distribute linked combinations
# including the two.
# You must obey the GNU General Public License in all respects
# for all of the code used other than OpenSSL.  If you modify
# file(s) with this exception, you may extend this exception to your
# version of the file(s), but you are not obligated to do so.  If you
# do not wish to do so, delete this exception statement from your
# version.  If you delete this exception statement from all source
# files in the program, then also delete it here.
"""A webclient backend that uses QtNetwork."""

from __future__ import unicode_literals

import glob
import os
import sys
from io import StringIO

# pylint: disable=E0611
from PyQt4.QtCore import (
    QBuffer,
    QCoreApplication,
    QUrl,
)
# pylint: enable=E0611
from PyQt4.QtNetwork import (
    QNetworkAccessManager,
    QNetworkProxy,
    QNetworkProxyFactory,
    QNetworkReply,
    QNetworkRequest,
    QSslCertificate,
    QSslConfiguration,
    QSslSocket,
)
from twisted.internet import defer

from ubuntu_sso.logger import setup_logging
from ubuntu_sso.utils import get_cert_dir
from ubuntu_sso.utils.webclient.common import (
    BaseWebClient,
    HeaderDict,
    ProxyUnauthorizedError,
    Response,
    UnauthorizedError,
    WebClientError,
)
from ubuntu_sso.utils.webclient import gsettings

logger = setup_logging("ubuntu_sso.utils.webclient.qtnetwork")


def build_proxy(settings_groups):
    """Create a QNetworkProxy from these settings."""
    proxy_groups = [
        ("socks", QNetworkProxy.Socks5Proxy),
        ("https", QNetworkProxy.HttpProxy),
        ("http", QNetworkProxy.HttpProxy),
    ]
    for group, proxy_type in proxy_groups:
        if group not in settings_groups:
            continue
        settings = settings_groups[group]
        if "host" in settings and "port" in settings:
            return QNetworkProxy(proxy_type,
                                 hostName=settings.get("host", ""),
                                 port=settings.get("port", 0),
                                 user=settings.get("username", ""),
                                 password=settings.get("password", ""))
    logger.error("No proxy correctly configured.")
    return QNetworkProxy(QNetworkProxy.DefaultProxy)


class WebClient(BaseWebClient):
    """A webclient with a qtnetwork backend."""

    proxy_instance = None

    def __init__(self, *args, **kwargs):
        """Initialize this instance."""
        super(WebClient, self).__init__(*args, **kwargs)
        self.nam = QNetworkAccessManager(QCoreApplication.instance())
        self.nam.finished.connect(self._handle_finished)
        self.nam.authenticationRequired.connect(self._handle_authentication)
        self.nam.proxyAuthenticationRequired.connect(self.handle_proxy_auth)
        self.nam.sslErrors.connect(self._handle_ssl_errors)
        self.replies = {}
        self.proxy_retry = False
        self.setup_proxy()

        # Force Qt to load the system certificates
        QSslSocket.setDefaultCaCertificates(QSslSocket.systemCaCertificates())
        # Apply our local certificates as the SSL configuration to be used
        # for all QNetworkRequest calls.
        self.ssl_config = QSslConfiguration.defaultConfiguration()
        ca_certs = self.ssl_config.caCertificates()
        try:
            for path in glob.glob(os.path.join(get_cert_dir(),
                                               "UbuntuOne*.pem")):
                with open(path) as f:
                    cert = QSslCertificate(f.read())
                    if cert.isValid():
                        ca_certs.append(cert)
                    else:
                        logger.error("invalid certificate: {}".format(path))
        except (IndexError, IOError) as err:
            raise WebClientError(
                    "Unable to configure SSL certificates: {}".format(err))

        self.ssl_config.setCaCertificates(ca_certs)

    def _set_proxy(self, proxy):
        """Set the proxy to be used."""
        QNetworkProxy.setApplicationProxy(proxy)
        self.nam.setProxy(proxy)

    def setup_proxy(self):
        """Setup the proxy settings if needed."""
        # QtNetwork knows how to use the system settings on both Win and Mac
        if sys.platform.startswith("linux"):
            settings = gsettings.get_proxy_settings()
            enabled = len(settings) > 0
            if enabled and WebClient.proxy_instance is None:
                proxy = build_proxy(settings)
                self._set_proxy(proxy)
                WebClient.proxy_instance = proxy
            elif enabled and WebClient.proxy_instance:
                logger.info("Proxy already in use.")
            else:
                logger.info("Proxy is disabled.")
        else:
            if WebClient.proxy_instance is None:
                logger.info("Querying OS for proxy.")
                QNetworkProxyFactory.setUseSystemConfiguration(True)

    def handle_proxy_auth(self, proxy, authenticator):
        """Proxy authentication is required."""
        logger.info("auth_required %r, %r", self.proxy_username,
                                            proxy.hostName())
        if (self.proxy_username is not None and
                self.proxy_username != str(authenticator.user())):
            authenticator.setUser(self.proxy_username)
            WebClient.proxy_instance.setUser(self.proxy_username)
        if (self.proxy_password is not None and
                self.proxy_password != str(authenticator.password())):
            authenticator.setPassword(self.proxy_password)
            WebClient.proxy_instance.setPassword(self.proxy_password)

    def _perform_request(self, request, method, post_buffer):
        """Return a deferred that will be fired with a Response object."""
        d = defer.Deferred()
        if method == "GET":
            reply = self.nam.get(request)
        elif method == "HEAD":
            reply = self.nam.head(request)
        else:
            reply = self.nam.sendCustomRequest(request, method, post_buffer)
        self.replies[reply] = d
        return d

    @defer.inlineCallbacks
    def request(self, iri, method="GET", extra_headers=None,
                oauth_credentials=None, post_content=None):
        """Return a deferred that will be fired with a Response object."""
        uri = self.iri_to_uri(iri)
        request = QNetworkRequest(QUrl(uri))
        request.setSslConfiguration(self.ssl_config)
        headers = yield self.build_request_headers(uri, method, extra_headers,
                                                   oauth_credentials)

        for key, value in headers.items():
            request.setRawHeader(key, value)

        post_buffer = QBuffer()
        post_buffer.setData(post_content)
        try:
            result = yield self._perform_request(request, method, post_buffer)
        except ProxyUnauthorizedError as e:
            app_proxy = QNetworkProxy.applicationProxy()
            proxy_host = app_proxy.hostName() if app_proxy else "proxy server"
            got_creds = yield self.request_proxy_auth_credentials(
                                            proxy_host, self.proxy_retry)
            if got_creds:
                self.proxy_retry = True
                result = yield self.request(iri, method, extra_headers,
                                            oauth_credentials, post_content)
            else:
                excp = WebClientError('Proxy creds needed.', e)
                defer.returnValue(excp)
        defer.returnValue(result)

    def _handle_authentication(self, reply, authenticator):
        """The reply needs authentication."""
        if authenticator.user() != self.username:
            authenticator.setUser(self.username)
        if authenticator.password() != self.password:
            authenticator.setPassword(self.password)

    def _handle_finished(self, reply):
        """The reply has finished processing."""
        assert reply in self.replies
        d = self.replies.pop(reply)
        error = reply.error()
        content = reply.readAll()
        if not error:
            headers = HeaderDict()
            for key, value in reply.rawHeaderPairs():
                headers[str(key)].append(str(value))
            response = Response(bytes(content), headers)
            d.callback(response)
        else:
            content = unicode(content)
            error_string = unicode(reply.errorString())
            logger.debug('_handle_finished error (%s,%s).', error,
                         error_string)
            if error == QNetworkReply.AuthenticationRequiredError:
                exception = UnauthorizedError(error_string, content)
            elif error == QNetworkReply.ProxyAuthenticationRequiredError:
                # we are going thru a proxy and we did not auth
                exception = ProxyUnauthorizedError(error_string, content)
            else:
                exception = WebClientError(error_string, content)
            d.errback(exception)

    def _get_certificate_details(self, cert):
        """Return an string with the details of the certificate."""
        detail_titles = {QSslCertificate.Organization: 'organization',
                         QSslCertificate.CommonName: 'common_name',
                         QSslCertificate.LocalityName: 'locality_name',
                         QSslCertificate.OrganizationalUnitName: 'unit',
                         QSslCertificate.CountryName: 'country_name',
                         QSslCertificate.StateOrProvinceName: 'state_name'}
        details = {}
        for info, title in detail_titles.items():
            details[title] = str(cert.issuerInfo(info))
        return self.format_ssl_details(details)

    def _get_certificate_host(self, cert):
        """Return the host of the cert."""
        return str(cert.issuerInfo(QSslCertificate.CommonName))

    def _handle_ssl_errors(self, reply, errors):
        """Handle the case in which we got an ssl error."""
        msg = StringIO()
        msg.write('SSL errors found; url: %s\n' %
                  reply.request().url().toString())
        for error in errors:
            msg.write('========Error=============\n%s (%s)\n' %
                     (error.errorString(), error.error()))
            msg.write('--------Cert Details------\n%s\n' %
                      self._get_certificate_details(error.certificate()))
            msg.write('==========================\n')
        logger.error(msg.getvalue())

    def force_use_proxy(self, https_settings):
        """Setup this webclient to use the given proxy settings."""
        settings = {"https": https_settings}
        proxy = build_proxy(settings)
        self._set_proxy(proxy)
        WebClient.proxy_instance = proxy

    def shutdown(self):
        """Shut down all pending requests (if possible)."""
        self.nam.deleteLater()
