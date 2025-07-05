#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from avahi_publisher import AvahiPublisher


class TestAvahiPublisher(unittest.TestCase):
    """Test cases for AvahiPublisher class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_bus = Mock()
        self.mock_server = Mock()
        self.mock_server.GetHostNameFqdn.return_value = "test-host.local"

    @patch('avahi_publisher.dbus.SystemBus')
    @patch('avahi_publisher.dbus.Interface')
    def test_init(self, mock_interface, mock_system_bus):
        """Test AvahiPublisher initialization."""
        mock_system_bus.return_value = self.mock_bus
        mock_interface.return_value = self.mock_server

        publisher = AvahiPublisher(record_ttl=120)

        self.assertEqual(publisher.record_ttl, 120)
        self.assertEqual(publisher.hostname, "test-host.local")
        self.assertEqual(publisher.published, {})
        mock_system_bus.assert_called_once()

    def test_fqdn_to_rdata(self):
        """Test FQDN to record data conversion."""
        with patch('avahi_publisher.dbus.SystemBus'), \
             patch('avahi_publisher.dbus.Interface') as mock_interface:

            mock_server = Mock()
            mock_server.GetHostNameFqdn.return_value = "test-host.local"
            mock_interface.return_value = mock_server

            publisher = AvahiPublisher()

            # Test normal FQDN
            result = publisher._fqdn_to_rdata("example.local")
            expected = b'\x07example\x05local\x00'
            self.assertEqual(result, expected)

            # Test empty parts are skipped
            result = publisher._fqdn_to_rdata("example..local")
            expected = b'\x07example\x05local\x00'
            self.assertEqual(result, expected)

    def test_count(self):
        """Test count method."""
        with patch('avahi_publisher.dbus.SystemBus'), \
             patch('avahi_publisher.dbus.Interface') as mock_interface:

            mock_server = Mock()
            mock_server.GetHostNameFqdn.return_value = "test-host.local"
            mock_interface.return_value = mock_server

            publisher = AvahiPublisher()

            # Initially empty
            self.assertEqual(publisher.count(), 0)

            # Add some mock published records
            publisher.published['test1.local'] = Mock()
            publisher.published['test2.local'] = Mock()
            self.assertEqual(publisher.count(), 2)

    @patch('avahi_publisher.dbus.SystemBus')
    @patch('avahi_publisher.dbus.Interface')
    def test_available(self, mock_interface, mock_system_bus):
        """Test availability check."""
        mock_system_bus.return_value = self.mock_bus
        mock_interface.return_value = self.mock_server

        publisher = AvahiPublisher()

        # Test successful connection
        self.mock_server.GetVersionString.return_value = "0.8"
        self.assertTrue(publisher.available())

        # Test failed connection
        from dbus.exceptions import DBusException
        self.mock_server.GetVersionString.side_effect = DBusException("org.freedesktop.DBus.Error.ServiceUnknown")
        self.assertFalse(publisher.available())

    def test_encode_dns(self):
        """Test DNS encoding method."""
        with patch('avahi_publisher.dbus.SystemBus'), \
             patch('avahi_publisher.dbus.Interface') as mock_interface:

            mock_server = Mock()
            mock_server.GetHostNameFqdn.return_value = "test-host.local"
            mock_interface.return_value = mock_server

            publisher = AvahiPublisher()

            # Test normal domain
            result = publisher.encode_dns("example.local")
            self.assertEqual(result, "example.local")

            # Test domain with empty parts
            result = publisher.encode_dns("example..local.")
            self.assertEqual(result, "example.local")


if __name__ == '__main__':
    unittest.main()
