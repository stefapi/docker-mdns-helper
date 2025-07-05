#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from docker_domains import DockerDomains


class TestDockerDomains(unittest.TestCase):
    """Test cases for DockerDomains class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_docker = Mock()
        self.mock_container = Mock()

    @patch('docker_domains.docker.from_env')
    def test_init(self, mock_docker_from_env):
        """Test DockerDomains initialization."""
        mock_docker_from_env.return_value = self.mock_docker

        # Test with enable=True
        domains = DockerDomains(enable=True)
        self.assertTrue(domains.enable)
        self.assertEqual(domains.domains, {})

        # Test with enable=False
        domains = DockerDomains(enable=False)
        self.assertFalse(domains.enable)

    @patch('docker_domains.docker.from_env')
    def test_len(self, mock_docker_from_env):
        """Test __len__ method."""
        mock_docker_from_env.return_value = self.mock_docker

        domains = DockerDomains(enable=True)

        # Empty domains
        self.assertEqual(len(domains), 0)

        # Add some domains
        domains.domains = {
            'test1.local': ['Docker', True],
            'test2.local': ['Dom', False],
            'test3.local': ['Supp', True]  # Suppressed, shouldn't count
        }
        self.assertEqual(len(domains), 2)  # Only non-suppressed count

    @patch('docker_domains.docker.from_env')
    def test_add_domain(self, mock_docker_from_env):
        """Test add_domain method."""
        mock_docker_from_env.return_value = self.mock_docker

        domains = DockerDomains(enable=True)

        # Add new domain
        domains.add_domain('test.local', 'Docker')
        self.assertIn('test.local', domains.domains)
        self.assertEqual(domains.domains['test.local'], ['Docker', False])

        # Try to add existing domain (should not overwrite)
        domains.add_domain('test.local', 'Dom')
        self.assertEqual(domains.domains['test.local'], ['Docker', False])

    @patch('docker_domains.docker.from_env')
    def test_add_domains(self, mock_docker_from_env):
        """Test add_domains method."""
        mock_docker_from_env.return_value = self.mock_docker

        domains = DockerDomains(enable=True)

        domain_list = ['test1.local', 'test2.local']
        domains.add_domains(domain_list)

        self.assertIn('test1.local', domains.domains)
        self.assertIn('test2.local', domains.domains)
        self.assertEqual(domains.domains['test1.local'], ['Dom', False])
        self.assertEqual(domains.domains['test2.local'], ['Dom', False])

    @patch('docker_domains.docker.from_env')
    def test_suppressed(self, mock_docker_from_env):
        """Test suppressed method."""
        mock_docker_from_env.return_value = self.mock_docker

        domains = DockerDomains(enable=True)

        # No suppressed domains
        self.assertFalse(domains.suppressed())

        # Add suppressed domain
        domains.domains['test.local'] = ['Supp', True]
        self.assertTrue(domains.suppressed())

    @patch('docker_domains.docker.from_env')
    def test_clean(self, mock_docker_from_env):
        """Test clean method."""
        mock_docker_from_env.return_value = self.mock_docker

        domains = DockerDomains(enable=True)
        domains.domains = {
            'test1.local': ['Docker', True],
            'test2.local': ['Supp', True],
            'test3.local': ['Dom', False]
        }

        domains.clean()

        # Only non-suppressed domains should remain
        self.assertIn('test1.local', domains.domains)
        self.assertNotIn('test2.local', domains.domains)
        self.assertIn('test3.local', domains.domains)

    @patch('docker_domains.docker.from_env')
    def test_update_list(self, mock_docker_from_env):
        """Test update_list method."""
        mock_docker_from_env.return_value = self.mock_docker

        domains = DockerDomains(enable=True)
        domains.domains = {
            'test1.local': ['Docker', False],  # Not updated
            'test2.local': ['Docker', True],   # Already updated
            'test3.local': ['Supp', False],    # Suppressed
            'test4.local': ['Dom', False]      # Not updated
        }

        update_list = domains.update_list()

        # Should only include non-updated, non-suppressed domains
        self.assertIn('test1.local', update_list)
        self.assertNotIn('test2.local', update_list)
        self.assertNotIn('test3.local', update_list)
        self.assertIn('test4.local', update_list)

    @patch('docker_domains.docker.from_env')
    def test_parse_traefik_labels(self, mock_docker_from_env):
        """Test parsing of Traefik labels."""
        mock_docker_from_env.return_value = self.mock_docker

        # Mock container with Traefik labels
        mock_container = Mock()
        mock_container.labels = {
            'traefik.http.routers.test.rule': 'Host(`example.local`)',
            'traefik.https.routers.secure.rule': 'Host(`secure.local`, `alt.local`)',
            'docker-mdns.enable': 'true'
        }

        self.mock_docker.containers.list.return_value = [mock_container]

        domains = DockerDomains(enable=False)  # Disabled by default
        domains.parse()

        # Should find domains from Traefik labels
        self.assertIn('example.local', domains.domains)
        self.assertIn('secure.local', domains.domains)
        self.assertIn('alt.local', domains.domains)

    @patch('docker_domains.docker.from_env')
    def test_available(self, mock_docker_from_env):
        """Test available method."""
        mock_docker_from_env.return_value = self.mock_docker

        domains = DockerDomains(enable=True)

        # Test successful connection
        self.mock_docker.ping.return_value = True
        self.assertTrue(domains.available())

        # Test failed connection
        import docker.errors
        self.mock_docker.ping.side_effect = docker.errors.APIError("Connection failed")
        self.assertFalse(domains.available())


if __name__ == '__main__':
    unittest.main()
