#!/bin/env python3
import logging
import re
import docker
import time

class DockerDomains(object):
    """Parse Docker labels to select Domain names to publish"""

    def __init__(self, enable):
        """Initialize the Parser"""

        try:
            self.docker = docker.from_env()
            # Log Docker API version for debugging
            self._log_docker_version()
        except Exception as e:
            logging.error("Failed to initialize Docker client: %s", e)
            raise

        self.enable = enable
        self.domains = {}

        # Cache compiled regular expressions for better performance
        # Traefik v2/v3 format: traefik.http.routers.*.rule or traefik.https.routers.*.rule
        # Note: Traefik v3 maintains backward compatibility with v2 label formats
        self._traefik_v2v3_rule_re = re.compile(r"^traefik\.https?\.routers\..+\.rule$")
        # Traefik v1 format: traefik.frontend.rule
        self._traefik_v1_rule_re = re.compile(r"^traefik\.frontend\.rule$")
        # Host patterns for different versions
        self._host_v2v3_re = re.compile(r"Host\(\s*(`(?:[^`]+)`(?:\s*,\s*`(?:[^`]+)`)*)\s*\)")
        self._host_v1_re = re.compile(r"Host:\s*([^,;]+(?:\s*,\s*[^,;]+)*)")
        self._domain_re = re.compile(r"`(.*)`")
        self._domain_v1_re = re.compile(r"([a-zA-Z0-9.-]+)")

        # Connection retry parameters
        self._last_connection_check = 0
        self._connection_check_interval = 30  # seconds

    def _log_docker_version(self):
        """Log Docker API version information for debugging."""
        try:
            version_info = self.docker.version()
            api_version = version_info.get('ApiVersion', 'Unknown')
            docker_version = version_info.get('Version', 'Unknown')
            logging.info("Docker API Version: %s, Docker Version: %s", api_version, docker_version)

            # Check for potential compatibility issues
            if api_version and api_version.startswith('1.'):
                major, minor = api_version.split('.')[:2]
                if int(major) == 1 and int(minor) < 24:
                    logging.warning("Docker API version %s is quite old. Consider upgrading for better compatibility.", api_version)
        except Exception as e:
            logging.warning("Could not retrieve Docker version information: %s", e)

    def __len__(self):
        cnt = 0
        for value in self.domains.values():
            if value[0] != "Supp":
                cnt += 1
        return cnt

    def parse(self):
        """Parse Docker container labels to extract domain names."""

        cnames = {}

        try:
            containers = self.docker.containers.list()
        except docker.errors.APIError as e:
            logging.error("Docker API error while listing containers: %s", e)
            return
        except Exception as e:
            logging.error("Unexpected error while listing containers: %s", e)
            return

        for container in containers:
            try:
                labels = container.labels or {}

                # Check if mDNS is enabled for this container
                mdns_enabled = self._is_mdns_enabled(labels)

                if mdns_enabled:
                    # Extract domains from Traefik router rules (v2/v3 format)
                    traefik_v2v3_rules = [key for key in labels.keys() if self._traefik_v2v3_rule_re.match(key)]

                    for rule_key in traefik_v2v3_rules:
                        rule_value = labels.get(rule_key, "")
                        for match in self._host_v2v3_re.finditer(rule_value):
                            host_list = [s.strip() for s in re.split(r",(?=\s*`)", match.group(1))]
                            for domain in host_list:
                                domain_match = self._domain_re.match(domain)
                                if domain_match:
                                    domain_name = domain_match.group(1)
                                    if self._is_valid_domain(domain_name):
                                        cnames[domain_name] = True
                                    else:
                                        logging.warning("Invalid domain name extracted (v2/v3): %s", domain_name)

                    # Extract domains from Traefik frontend rules (v1 format)
                    traefik_v1_rules = [key for key in labels.keys() if self._traefik_v1_rule_re.match(key)]

                    for rule_key in traefik_v1_rules:
                        rule_value = labels.get(rule_key, "")
                        for match in self._host_v1_re.finditer(rule_value):
                            host_list = [s.strip() for s in match.group(1).split(',')]
                            for domain in host_list:
                                domain_match = self._domain_v1_re.match(domain.strip())
                                if domain_match:
                                    domain_name = domain_match.group(1)
                                    if self._is_valid_domain(domain_name):
                                        cnames[domain_name] = True
                                    else:
                                        logging.warning("Invalid domain name extracted (v1): %s", domain_name)

                    # Extract explicit domain from docker-mdns.domain label
                    if "docker-mdns.domain" in labels:
                        explicit_domain = labels["docker-mdns.domain"]
                        if self._is_valid_domain(explicit_domain):
                            cnames[explicit_domain] = True
                        else:
                            logging.warning("Invalid explicit domain: %s", explicit_domain)

            except Exception as e:
                logging.error("Error processing container %s: %s", getattr(container, 'name', 'unknown'), e)
                continue

        # Add new domains
        for domain_name in cnames.keys():
            if domain_name not in self.domains:
                self.add_domain(domain_name, "Docker")

        # Mark removed domains as suppressed
        for domain_name, domain_info in self.domains.items():
            if domain_name not in cnames and domain_info[0] == "Docker":
                self.domains[domain_name][0] = "Supp"

    def _is_mdns_enabled(self, labels):
        """Check if mDNS is enabled for a container based on labels."""
        if not self.enable:
            # mDNS disabled by default, check for explicit enable
            return "docker-mdns.enable" in labels and labels["docker-mdns.enable"].lower() == "true"
        else:
            # mDNS enabled by default, check for explicit disable
            return not ("docker-mdns.enable" in labels and labels["docker-mdns.enable"].lower() == "false")

    def _is_valid_domain(self, domain):
        """Validate domain name format."""
        if not domain or len(domain) > 253:
            return False

        # Basic domain validation - could be enhanced
        domain_pattern = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$")
        return domain_pattern.match(domain) is not None

    def add_domain(self, domain, type):
        if domain not in self.domains:
            self.domains[domain] = [type, False]

    def add_domains(self, list):
        for domain in list:
            self.add_domain(domain, "Dom")

    def suppressed(self ):
        for key,value in self.domains.items():
            if value[0] == "Supp":
                return True
        return False

    def clean(self):
        domains= {}
        for key,value in self.domains.items():
            if value[0] != "Supp":
                domains[key] = value
        self.domains = domains

    def update_list(self):
        list = []
        for key,value in self.domains.items():
            if not value[1] and value[0] != "Supp":
                list.append(key)
        return list

    def updated(self):
        self.parse()
        return not all(value[1] for value in self.domains.values())

    def all_new(self):
        for keys in self.domains.keys():
            if self.domains[keys][0] != "Supp":
                self.domains[keys][1] = False

    def update(self, domain):
        if domain in self.domains:
            self.domains[domain][1] = True

    def available(self):
        """Check if the connection to Docker is still available."""

        # Use cached result if recent check was successful
        current_time = time.time()
        if (current_time - self._last_connection_check) < self._connection_check_interval:
            return True

        try:
            result = self.docker.ping()
            if result:
                self._last_connection_check = current_time
            return result
        except docker.errors.APIError as e:
            logging.error("Docker API error during connection check: %s", e)
            return False
        except docker.errors.DockerException as e:
            logging.error("Docker connection error: %s", e)
            return False
        except Exception as e:
            logging.error("Unexpected error during Docker connection check: %s", e)
            return False
