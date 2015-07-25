# -*- coding: utf-8 -*-

# Author: Alejandro J. Cura <alecu@canonical.com>
#
# Copyright 2010-2012 Canonical Ltd.
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
"""
Provides a twisted interface to access the system keyring via DBus.
Implements the Secrets Service API Draft:
 * http://code.confuego.org/secrets-xdg-specs/
"""

import dbus

from twisted.internet.defer import Deferred

BUS_NAME = "org.freedesktop.secrets"
SERVICE_IFACE = "org.freedesktop.Secret.Service"
PROMPT_IFACE = "org.freedesktop.Secret.Prompt"
SESSION_IFACE = "org.freedesktop.Secret.Session"
COLLECTION_IFACE = "org.freedesktop.Secret.Collection"
ITEM_IFACE = "org.freedesktop.Secret.Item"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
SECRETS_SERVICE = "/org/freedesktop/secrets"
DEFAULT_COLLECTION = "/org/freedesktop/secrets/aliases/default"
SESSION_COLLECTION = "/org/freedesktop/secrets/collection/session"
SECRET_CONTENT_TYPE = "application/octet-stream"

ALGORITHM = "plain"
ALGORITHM_PARAMS = ""
CLXN_LABEL_PROPERTY = "org.freedesktop.Secret.Collection.Label"
CLXN_LABEL_PROPERTY_OLD = "Label"
ITEM_LABEL_PROPERTY = "org.freedesktop.Secret.Item.Label"
ITEM_LABEL_PROPERTY_OLD = "Label"
ITEM_ATTRIBUTES_PROPERTY = "org.freedesktop.Secret.Item.Attributes"
ITEM_ATTRIBUTES_PROPERTY_OLD = "Attributes"
COLLECTIONS_PROPERTY = "org.freedesktop.Secret.Service.Collections"
COLLECTIONS_PROPERTY_OLD = "Collections"
DEFAULT_LABEL = "default"


class UserCancelled(Exception):
    """The user cancelled a prompt."""


def no_op(*args):
    """Do nothing."""


class SecretService(object):
    """The Secret Service manages all the sessions and collections."""
    service = None
    properties = None
    session = None
    bus = None
    window_id = None

    def open_session(self, window_id=0):
        """Open a unique session for the caller application."""
        d = Deferred()
        try:
            self.window_id = str(window_id)
            self.bus = dbus.SessionBus()
            service_object = self.bus.get_object(BUS_NAME, SECRETS_SERVICE)
            self.service = dbus.Interface(service_object,
                                          dbus_interface=SERVICE_IFACE)
            self.properties = dbus.Interface(service_object,
                                             dbus_interface=PROPERTIES_IFACE)

            def session_opened(result, session):
                """The session was successfully opened."""
                self.session = self.bus.get_object(BUS_NAME, session)
                d.callback(self)

            parameters = dbus.String(ALGORITHM_PARAMS, variant_level=1)
            self.service.OpenSession(ALGORITHM, parameters,
                                     reply_handler=session_opened,
                                     error_handler=d.errback)
        except dbus.exceptions.DBusException as e:
            d.errback(e)
        return d

    def do_prompt(self, prompt_path):
        """Show a prompt given its path."""
        d = Deferred()
        prompt_object = self.bus.get_object(BUS_NAME, prompt_path)
        prompt = dbus.Interface(prompt_object, dbus_interface=PROMPT_IFACE)

        def prompt_completed(dismissed, result):
            """The prompt was either completed or dismissed."""
            sigcompleted.remove()
            if dismissed:
                d.errback(UserCancelled())
            else:
                d.callback(result)

        sigcompleted = prompt.connect_to_signal("Completed", prompt_completed)
        prompt.Prompt(self.window_id,
                      reply_handler=no_op,
                      error_handler=d.errback)
        return d

    def make_item_list(self, object_path_list):
        """Make a list of items given their paths."""
        return [Item(self, o) for o in object_path_list]

    def search_items(self, attributes):
        """Find items in any collection."""
        d = Deferred()
        result = []

        def prompt_handle(unlocked):
            """Merge the items that were just unlocked."""
            result.extend(unlocked)
            return result

        def unlock_handler(unlocked, prompt):
            """The items were unlocked, or a prompt should be shown first."""
            result.extend(unlocked)
            if prompt != "/":
                d2 = self.do_prompt(prompt)
                d2.addCallback(prompt_handle)
                d2.chainDeferred(d)
            else:
                d.callback(result)

        def items_found(unlocked, locked):
            """Called with two lists of found items."""
            result.extend(unlocked)
            if len(locked) > 0:
                self.service.Unlock(locked,
                                    reply_handler=unlock_handler,
                                    error_handler=d.errback)
            else:
                d.callback(result)

        self.service.SearchItems(attributes,
                                 reply_handler=items_found,
                                 error_handler=d.errback)
        d.addCallback(self.make_item_list)
        return d

    def create_collection(self, label, alias=''):
        """Create a new collection with the specified properties."""
        d = Deferred()

        def createcollection_handler(collection, prompt):
            """A collection was created, or a prompt should be shown first."""
            if prompt != "/":
                self.do_prompt(prompt).chainDeferred(d)
            else:
                d.callback(collection)

        def error_fallback(error):
            """Fall back to using the old property name."""
            properties = {CLXN_LABEL_PROPERTY_OLD: dbus.String(
                    label,
                    variant_level=1)}
            self.service.CreateCollection(
                properties,
                reply_handler=createcollection_handler,
                error_handler=d.errback)

        properties = {CLXN_LABEL_PROPERTY: dbus.String(label,
                                                       variant_level=1)}
        try:
            self.service.CreateCollection(
                properties, alias,
                reply_handler=createcollection_handler,
                error_handler=error_fallback)
        except TypeError:
            error_fallback(None)

        d.addCallback(lambda p: Collection(self, p))
        return d

    def get_collections(self):
        """Return the list of all collections."""
        d = Deferred()

        def propertyget_handler(collection_paths):
            """The list of collection paths was retrieved."""
            result = []
            for path in collection_paths:
                collection = Collection(self, path)
                result.append(collection)
            d.callback(result)

        def error_fallback(error):
            """Fall back to the old property name."""
            self.properties.Get(SERVICE_IFACE, COLLECTIONS_PROPERTY_OLD,
                                reply_handler=propertyget_handler,
                                error_handler=d.errback)

        self.properties.Get(SERVICE_IFACE, COLLECTIONS_PROPERTY,
                            reply_handler=propertyget_handler,
                            error_handler=error_fallback)
        return d

    def get_default_collection(self):
        """The collection where default items should be created."""
        d = Deferred()

        def prompt_handle(unlocked):
            """Handle showing a prompt."""
            collection_path = unlocked[0]
            return Collection(self, collection_path)

        def unlock_handler(unlocked, prompt):
            """The objects were unlocked."""
            if prompt != "/":
                d2 = self.do_prompt(prompt)
                d2.addCallback(prompt_handle)
                d2.chainDeferred(d)
            else:
                d.callback(prompt_handle(unlocked))

        def set_default_alias(collection):
            """Set the newly created collection as the default one."""
            d4 = Deferred()
            alias_set = lambda: d4.callback(collection)
            object_path = dbus.ObjectPath(collection.object_path)
            self.service.SetAlias(DEFAULT_LABEL, object_path,
                                  reply_handler=alias_set,
                                  error_handler=d4.errback)
            return d4

        def readalias_handler(collection_path):
            """ReadAlias returned."""
            if collection_path != "/":
                # The collection was found, make sure it's unlocked
                objects = dbus.Array([collection_path], signature="o")
                self.service.Unlock(objects,
                                    reply_handler=unlock_handler,
                                    error_handler=d.errback)
            else:
                # The collection was not found, so create it
                d3 = self.create_collection(DEFAULT_LABEL)
                d3.addCallback(set_default_alias)
                d3.chainDeferred(d)

        def default_collection_not_found(e):
            """Try the default alias."""
            self.service.ReadAlias(DEFAULT_LABEL,
                                   reply_handler=readalias_handler,
                                   error_handler=d.errback)

        def found_default_collection(label):
            """Make sure the default collection is unlocked."""
            objects = dbus.Array([DEFAULT_COLLECTION], signature="o")
            self.service.Unlock(objects,
                                reply_handler=unlock_handler,
                                error_handler=d.errback)

        collection = Collection(self, DEFAULT_COLLECTION)
        d0 = collection.get_label()
        d0.addCallback(found_default_collection)
        d0.addErrback(default_collection_not_found)

        return d


class Collection(object):
    """A collection of items containing secrets."""

    def __init__(self, service, object_path):
        """Initialize a new collection."""
        self.service = service
        self.object_path = object_path
        collection_object = service.bus.get_object(BUS_NAME, object_path,
                                                   introspect=False)
        self.collection_iface = dbus.Interface(collection_object,
                                               dbus_interface=COLLECTION_IFACE)
        self.properties = dbus.Interface(collection_object,
                                         dbus_interface=PROPERTIES_IFACE)

    def get_label(self):
        """Return the label for this collection from the keyring."""
        d = Deferred()

        def error_fallback(error):
            """Fall back to the old property name."""
            self.properties.Get(COLLECTION_IFACE, CLXN_LABEL_PROPERTY_OLD,
                                reply_handler=d.callback,
                                error_handler=d.errback)

        self.properties.Get(COLLECTION_IFACE, CLXN_LABEL_PROPERTY,
                            reply_handler=d.callback,
                            error_handler=error_fallback)
        return d

    def create_item(self, label, attr, value, replace=True):
        """Create an item with the given attributes, secret and label.

        If replace is set, then it replaces an item already present with the
        same values for the attributes.
        """
        d = Deferred()

        def createitem_handler(item, prompt):
            """An item was created, or a prompt should be shown first."""
            if prompt != "/":
                self.service.do_prompt(prompt).chainDeferred(d)
            else:
                d.callback(item)

        properties = dbus.Dictionary(signature="sv")
        properties[ITEM_LABEL_PROPERTY] = label
        attributes = dbus.Dictionary(attr, signature="ss")
        properties[ITEM_ATTRIBUTES_PROPERTY] = attributes
        parameters = dbus.ByteArray(ALGORITHM_PARAMS)
        value_bytes = dbus.ByteArray(value)
        secret = (self.service.session, parameters, value_bytes,
                  SECRET_CONTENT_TYPE)

        def error_fallback(error):
            """A fallback for using old property names and signature."""
            oldprops = dbus.Dictionary(signature="sv")
            oldprops[ITEM_LABEL_PROPERTY_OLD] = label
            oldprops[ITEM_ATTRIBUTES_PROPERTY_OLD] = attributes
            secret = (self.service.session, parameters, value_bytes)
            self.collection_iface.CreateItem(oldprops, secret, replace,
                                             reply_handler=createitem_handler,
                                             error_handler=d.errback)

        self.collection_iface.CreateItem(properties, secret, replace,
                                         reply_handler=createitem_handler,
                                         error_handler=error_fallback)
        return d


class Item(object):
    """An item contains a secret, lookup attributes and has a label."""

    def __init__(self, service, object_path):
        """Initialize this new Item."""
        self.service = service
        self.object_path = object_path
        item_object = service.bus.get_object(BUS_NAME, object_path)
        self.item_iface = dbus.Interface(item_object,
                                         dbus_interface=ITEM_IFACE)

    def get_value(self):
        """Retrieve the secret for this item."""
        d = Deferred()

        def getsecret_handler(secret):
            """The secret for this item was found."""
            # pylint: disable=W0612
            value = secret[2]
            d.callback(value)

        self.item_iface.GetSecret(self.service.session, byte_arrays=True,
                                  reply_handler=getsecret_handler,
                                  error_handler=d.errback)
        return d

    def delete(self):
        """Delete this item."""
        d = Deferred()

        def delete_handler(prompt):
            """The item was deleted, or a prompt should be shown first."""
            if prompt != "/":
                self.service.do_prompt(prompt).chainDeferred(d)
            else:
                d.callback(True)

        self.item_iface.Delete(reply_handler=delete_handler,
                               error_handler=d.errback)
        return d
