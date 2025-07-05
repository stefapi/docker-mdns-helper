#!/usr/bin/env python3
"""
Test version compatibility features for Docker mDNS Helper.
Tests Traefik v1, v2, and v3 label parsing compatibility.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path to import docker_domains
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from docker_domains import DockerDomains


class TestVersionCompatibility(unittest.TestCase):
    """Test version compatibility features."""

    def setUp(self):
        """Set up test fixtures."""
        with patch('docker.from_env') as mock_docker:
            mock_docker.return_value.version.return_value = {
                'ApiVersion': '1.41',
                'Version': '20.10.0'
            }
            self.parser = DockerDomains(enable=True)

    def test_traefik_v2_label_parsing(self):
        """Test parsing of Traefik v2 labels."""
        # Mock container with Traefik v2 labels
        mock_container = Mock()
        mock_container.labels = {
            'traefik.enable': 'true',
            'traefik.http.routers.webapp.rule': 'Host(`webapp.local`)',
            'traefik.https.routers.webapp-secure.rule': 'Host(`webapp.local`, `app.local`)',
            'docker-mdns.enable': 'true'
        }

        # Mock Docker client
        with patch.object(self.parser.docker, 'containers') as mock_containers:
            mock_containers.list.return_value = [mock_container]

            # Parse containers
            self.parser.parse()

            # Check that domains were extracted
            self.assertIn('webapp.local', self.parser.domains)
            self.assertIn('app.local', self.parser.domains)
            self.assertEqual(len(self.parser.domains), 2)

    def test_traefik_v3_label_parsing(self):
        """Test parsing of Traefik v3 labels."""
        # Mock container with Traefik v3 labels (same format as v2)
        mock_container = Mock()
        mock_container.labels = {
            'traefik.enable': 'true',
            'traefik.http.routers.v3app.rule': 'Host(`v3app.local`)',
            'traefik.https.routers.v3app-secure.rule': 'Host(`v3app.local`, `v3-alt.local`)',
            'docker-mdns.enable': 'true'
        }

        # Mock Docker client
        with patch.object(self.parser.docker, 'containers') as mock_containers:
            mock_containers.list.return_value = [mock_container]

            # Parse containers
            self.parser.parse()

            # Check that domains were extracted
            self.assertIn('v3app.local', self.parser.domains)
            self.assertIn('v3-alt.local', self.parser.domains)
            self.assertEqual(len(self.parser.domains), 2)

    def test_traefik_v1_label_parsing(self):
        """Test parsing of Traefik v1 labels."""
        # Mock container with Traefik v1 labels
        mock_container = Mock()
        mock_container.labels = {
            'traefik.enable': 'true',
            'traefik.frontend.rule': 'Host:oldapp.local,legacy.local',
            'docker-mdns.enable': 'true'
        }

        # Mock Docker client
        with patch.object(self.parser.docker, 'containers') as mock_containers:
            mock_containers.list.return_value = [mock_container]

            # Parse containers
            self.parser.parse()

            # Check that domains were extracted
            self.assertIn('oldapp.local', self.parser.domains)
            self.assertIn('legacy.local', self.parser.domains)
            self.assertEqual(len(self.parser.domains), 2)

    def test_mixed_traefik_versions(self):
        """Test parsing containers with mixed Traefik v1, v2, and v3 labels."""
        # Mock containers with different Traefik versions
        mock_container_v1 = Mock()
        mock_container_v1.labels = {
            'traefik.enable': 'true',
            'traefik.frontend.rule': 'Host:v1app.local',
            'docker-mdns.enable': 'true'
        }

        mock_container_v2 = Mock()
        mock_container_v2.labels = {
            'traefik.enable': 'true',
            'traefik.http.routers.v2app.rule': 'Host(`v2app.local`)',
            'docker-mdns.enable': 'true'
        }

        mock_container_v3 = Mock()
        mock_container_v3.labels = {
            'traefik.enable': 'true',
            'traefik.https.routers.v3app.rule': 'Host(`v3app.local`)',
            'docker-mdns.enable': 'true'
        }

        # Mock Docker client
        with patch.object(self.parser.docker, 'containers') as mock_containers:
            mock_containers.list.return_value = [mock_container_v1, mock_container_v2, mock_container_v3]

            # Parse containers
            self.parser.parse()

            # Check that domains from all versions were extracted
            self.assertIn('v1app.local', self.parser.domains)
            self.assertIn('v2app.local', self.parser.domains)
            self.assertIn('v3app.local', self.parser.domains)
            self.assertEqual(len(self.parser.domains), 3)

    def test_docker_version_logging(self):
        """Test Docker version detection and logging."""
        with patch('docker.from_env') as mock_docker:
            mock_client = Mock()
            mock_client.version.return_value = {
                'ApiVersion': '1.41',
                'Version': '20.10.0'
            }
            mock_docker.return_value = mock_client

            with patch('logging.info') as mock_log_info:
                parser = DockerDomains(enable=True)

                # Check that version info was logged
                mock_log_info.assert_called_with(
                    "Docker API Version: %s, Docker Version: %s",
                    '1.41',
                    '20.10.0'
                )

    def test_old_docker_version_warning(self):
        """Test warning for old Docker API versions."""
        with patch('docker.from_env') as mock_docker:
            mock_client = Mock()
            mock_client.version.return_value = {
                'ApiVersion': '1.23',
                'Version': '17.05.0'
            }
            mock_docker.return_value = mock_client

            with patch('logging.warning') as mock_log_warning:
                parser = DockerDomains(enable=True)

                # Check that warning was logged for old version
                mock_log_warning.assert_called_with(
                    "Docker API version %s is quite old. Consider upgrading for better compatibility.",
                    '1.23'
                )

    def test_explicit_domain_label(self):
        """Test explicit domain specification via docker-mdns.domain label."""
        # Mock container with explicit domain label
        mock_container = Mock()
        mock_container.labels = {
            'docker-mdns.domain': 'custom.local',
            'docker-mdns.enable': 'true'
        }

        # Mock Docker client
        with patch.object(self.parser.docker, 'containers') as mock_containers:
            mock_containers.list.return_value = [mock_container]

            # Parse containers
            self.parser.parse()

            # Check that explicit domain was extracted
            self.assertIn('custom.local', self.parser.domains)
            self.assertEqual(len(self.parser.domains), 1)


if __name__ == '__main__':
    unittest.main()
