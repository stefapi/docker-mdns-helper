#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Configuration validation and management for docker-mdns-helper.
"""

import os
import re
import logging
from typing import List, Optional, Dict, Any


class ConfigError(Exception):
    """Configuration validation error."""
    pass


class Config:
    """Configuration manager with validation."""

    def __init__(self):
        """Initialize configuration with default values."""
        self.ttl = 60
        self.wait_time = 5
        self.verbose = False
        self.force = False
        self.reset = False
        self.disable = False
        self.log_file = None
        self.daemon = False
        self.domains = []

        # Validation patterns
        self.cname_pattern = re.compile(r"^[a-z0-9-]{1,63}(?:\.[a-z0-9-]{1,63})*\.local$")

    def load_from_env(self) -> None:
        """Load configuration from environment variables."""
        try:
            # TTL configuration
            if 'MDNS_TTL' in os.environ:
                self.ttl = self._parse_int('MDNS_TTL', os.environ['MDNS_TTL'], 1, 86400)

            # Wait time configuration
            if 'MDNS_WAIT' in os.environ:
                self.wait_time = self._parse_int('MDNS_WAIT', os.environ['MDNS_WAIT'], 1, 3600)

            # Boolean configurations
            self.verbose = self._parse_bool('MDNS_VERBOSE', os.environ.get('MDNS_VERBOSE', 'false'))
            self.force = self._parse_bool('MDNS_FORCE', os.environ.get('MDNS_FORCE', 'false'))
            self.reset = self._parse_bool('MDNS_RESET', os.environ.get('MDNS_RESET', 'true'))
            self.disable = self._parse_bool('MDNS_DISABLE', os.environ.get('MDNS_DISABLE', 'false'))
            self.daemon = self._parse_bool('MDNS_DAEMON', os.environ.get('MDNS_DAEMON', 'false'))

            # Log file configuration
            if 'MDNS_LOG_FILE' in os.environ:
                self.log_file = os.environ['MDNS_LOG_FILE']
                self._validate_log_file(self.log_file)

            # Domains configuration
            if 'MDNS_DOMAINS' in os.environ:
                domains_str = os.environ['MDNS_DOMAINS'].strip()
                if domains_str:
                    self.domains = [d.strip().lower() for d in domains_str.split() if d.strip()]
                    self._validate_domains(self.domains)

        except (ValueError, ConfigError) as e:
            raise ConfigError(f"Environment configuration error: {e}")

    def update_from_args(self, args) -> None:
        """Update configuration from command line arguments."""
        try:
            if hasattr(args, 'ttl') and args.ttl is not None:
                self.ttl = self._parse_int('ttl', str(args.ttl), 1, 86400)

            if hasattr(args, 'wait') and args.wait is not None:
                self.wait_time = self._parse_int('wait', str(args.wait), 1, 3600)

            if hasattr(args, 'verbose'):
                self.verbose = bool(args.verbose)

            if hasattr(args, 'force'):
                self.force = bool(args.force)

            if hasattr(args, 'reset'):
                self.reset = bool(args.reset)

            if hasattr(args, 'disable'):
                self.disable = bool(args.disable)

            if hasattr(args, 'daemon'):
                self.daemon = bool(args.daemon)

            if hasattr(args, 'log') and args.log:
                self.log_file = args.log
                self._validate_log_file(self.log_file)

            if hasattr(args, 'cnames') and args.cnames:
                domains = [d.lower() for d in args.cnames]
                self._validate_domains(domains)
                self.domains.extend(domains)

        except (ValueError, ConfigError) as e:
            raise ConfigError(f"Command line argument error: {e}")

    def validate(self) -> None:
        """Validate the complete configuration."""
        # Check for conflicting options
        if self.force and self.verbose:
            logging.warning("Using --force with --verbose may produce confusing output")

        # Validate TTL range
        if not (1 <= self.ttl <= 86400):
            raise ConfigError(f"TTL must be between 1 and 86400 seconds, got {self.ttl}")

        # Validate wait time
        if not (1 <= self.wait_time <= 3600):
            raise ConfigError(f"Wait time must be between 1 and 3600 seconds, got {self.wait_time}")

        # Validate domains
        if self.domains:
            self._validate_domains(self.domains)

    def _parse_int(self, name: str, value: str, min_val: int, max_val: int) -> int:
        """Parse and validate integer configuration value."""
        try:
            int_val = int(value)
            if not (min_val <= int_val <= max_val):
                raise ConfigError(f"{name} must be between {min_val} and {max_val}, got {int_val}")
            return int_val
        except ValueError:
            raise ConfigError(f"{name} must be a valid integer, got '{value}'")

    def _parse_bool(self, name: str, value: str) -> bool:
        """Parse boolean configuration value."""
        if isinstance(value, bool):
            return value

        value_lower = value.lower().strip()
        if value_lower in ('true', '1', 'yes', 'on'):
            return True
        elif value_lower in ('false', '0', 'no', 'off'):
            return False
        else:
            raise ConfigError(f"{name} must be a boolean value (true/false), got '{value}'")

    def _validate_log_file(self, log_file: str) -> None:
        """Validate log file path."""
        if not log_file:
            return

        # Check if directory exists and is writable
        log_dir = os.path.dirname(os.path.abspath(log_file))
        if not os.path.exists(log_dir):
            raise ConfigError(f"Log directory does not exist: {log_dir}")

        if not os.access(log_dir, os.W_OK):
            raise ConfigError(f"Log directory is not writable: {log_dir}")

    def _validate_domains(self, domains: List[str]) -> None:
        """Validate domain names."""
        for domain in domains:
            if not self.cname_pattern.match(domain):
                raise ConfigError(f"Invalid domain format: {domain}. Must be in format 'name.local'")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'ttl': self.ttl,
            'wait_time': self.wait_time,
            'verbose': self.verbose,
            'force': self.force,
            'reset': self.reset,
            'disable': self.disable,
            'daemon': self.daemon,
            'log_file': self.log_file,
            'domains': self.domains,
        }

    def __str__(self) -> str:
        """String representation of configuration."""
        config_dict = self.to_dict()
        # Hide sensitive information if any
        return f"Config({', '.join(f'{k}={v}' for k, v in config_dict.items())})"
