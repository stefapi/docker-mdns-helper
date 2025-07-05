#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# mpublisher.py - Avahi/mDNS name publisher.
#
# Copyright (c) 2014, SAPO
#


from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import

import logging
from encodings.idna import ToASCII

import dbus


# If the system-provided library isn't available, use a bundled copy instead.
# Necessary for CentOS 6/7 where there's no available "avahi-python" package.
try:
    import avahi
except ImportError:
    import _avahi as avahi


# From "/usr/include/avahi-common/defs.h"
AVAHI_DNS_CLASS_IN = 0x01
AVAHI_DNS_TYPE_CNAME = 0x05


class AvahiPublisher(object):
    """Publish mDNS records to Avahi, using D-BUS."""

    def __init__(self, record_ttl=60):
        """Initialize the publisher with fixed record TTL value (in seconds)."""

        # Validate TTL parameter
        if not isinstance(record_ttl, int) or record_ttl <= 0 or record_ttl > 86400:
            raise ValueError("TTL must be a positive integer between 1 and 86400 seconds")

        try:
            self.bus = dbus.SystemBus()
        except dbus.exceptions.DBusException as e:
            logging.error("Failed to connect to system D-Bus: %s", e)
            raise

        try:
            path_server_proxy = self.bus.get_object(avahi.DBUS_NAME, avahi.DBUS_PATH_SERVER)
            self.server = dbus.Interface(path_server_proxy, avahi.DBUS_INTERFACE_SERVER)
        except dbus.exceptions.DBusException as e:
            logging.error("Failed to connect to Avahi daemon: %s", e)
            raise

        try:
            self.hostname = self.server.GetHostNameFqdn()
        except dbus.exceptions.DBusException as e:
            logging.error("Failed to get hostname from Avahi: %s", e)
            raise

        self.record_ttl = record_ttl
        self.published = {}

        logging.debug("Avahi mDNS publisher initialized for: %s", self.hostname)


    def __del__(self):
        """Remove all published records from mDNS."""

        try:
            # Check if published attribute exists (in case __init__ failed)
            if hasattr(self, 'published') and self.published:
                for group in self.published.values():
                    group.Reset()
        except dbus.exceptions.DBusException as e:  # ...don't spam on broken connection.
            if e.get_dbus_name() != "org.freedesktop.DBus.Error.ServiceUnknown":
                raise
        except Exception:
            # Ignore any other exceptions during cleanup
            pass


    def _fqdn_to_rdata(self, fqdn):
        """Convert an FQDN into the mDNS data record format."""

        data = []
        for part in fqdn.split("."):
            if part:
                data.append(bytes([len(part)]))
                data.append(part.encode("ascii"))

        return b"".join(data) + b"\0"


    def count(self):
        """Return the number of records currently being published."""

        return len(self.published)


    def resolve(self, name):
        """Lookup the current owner for "name", using mDNS."""

        try:
            # TODO: Find out if it's possible to manipulate (shorten) the timeout...
            response = self.server.ResolveHostName(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC,
                                                   name.encode("ascii"), avahi.PROTO_UNSPEC,
                                                   dbus.UInt32(0))
            #return response[2].decode("ascii")
            return response[2]
        except (NameError, dbus.exceptions.DBusException):
            return None


    def publish_cname(self, cname, force=False):
        """Publish a CNAME record."""

        # Validate input parameters
        if not isinstance(cname, str) or not cname.strip():
            logging.error("Invalid CNAME: must be a non-empty string")
            return False

        cname = cname.strip().lower()

        # Check if already published
        if cname in self.published:
            logging.debug("CNAME '%s' is already published", cname)
            return True

        if not force:
            # Unfortunately, this takes a few seconds in the expected case...
            logging.info("Checking for '%s' availability...", cname)
            try:
                current_owner = self.resolve(cname)

                if current_owner:
                    if current_owner != self.hostname:
                        logging.error("DNS entry '%s' is already owned by '%s'", cname, current_owner)
                        return False

                    # We may have discovered ourselves, but this is not a fatal problem...
                    logging.warning("DNS entry '%s' is already being published by this machine", cname)
                    return True
            except Exception as e:
                logging.error("Error checking CNAME availability for '%s': %s", cname, e)
                return False

        try:
            entry_group_proxy = self.bus.get_object(avahi.DBUS_NAME, self.server.EntryGroupNew())
            group = dbus.Interface(entry_group_proxy, avahi.DBUS_INTERFACE_ENTRY_GROUP)

            group.AddRecord(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, dbus.UInt32(0), cname.encode("ascii"),
                            AVAHI_DNS_CLASS_IN, AVAHI_DNS_TYPE_CNAME, self.record_ttl,
                            self._fqdn_to_rdata(self.hostname))
            group.Commit()
            self.published[cname] = group

            logging.debug("Successfully published CNAME '%s'", cname)
            return True

        except dbus.exceptions.DBusException as e:
            logging.error("D-Bus error publishing CNAME '%s': %s", cname, e)
            return False
        except Exception as e:
            logging.error("Unexpected error publishing CNAME '%s': %s", cname, e)
            return False

    def unpublish(self, name):
        """Remove a published record from mDNS."""

        if not isinstance(name, str) or not name.strip():
            logging.error("Invalid name for unpublish: must be a non-empty string")
            return False

        name = name.strip().lower()

        if name not in self.published:
            logging.warning("Cannot unpublish '%s': not currently published", name)
            return False

        try:
            self.published[name].Reset()
            del self.published[name]
            logging.debug("Successfully unpublished '%s'", name)
            return True
        except dbus.exceptions.DBusException as e:
            logging.error("D-Bus error unpublishing '%s': %s", name, e)
            # Remove from our tracking even if D-Bus call failed
            if name in self.published:
                del self.published[name]
            return False
        except Exception as e:
            logging.error("Unexpected error unpublishing '%s': %s", name, e)
            # Remove from our tracking even if operation failed
            if name in self.published:
                del self.published[name]
            return False


    def available(self):
        """Check if the connection to Avahi is still available."""

        try:
            # This is just a dummy call to test the connection...
            self.server.GetVersionString()
        except dbus.exceptions.DBusException as e:
            if e.get_dbus_name() != "org.freedesktop.DBus.Error.ServiceUnknown":
                raise

            logging.error("Lost Connection to Dbus")
            return False

        return True


# vim: set expandtab ts=4 sw=4:
