#!/bin/env python3
import logging
import re
import docker
import string

class DockerDomains(object):
    """Parse Docker labels to select Domain names to publish"""

    def __init__(self, enable):
        """Initialize the Parser"""

        self.docker = docker.from_env()

        self.enable = enable
        self.domains = {}

    def __len__(self):
        cnt = 0
        for value in self.domains.values():
            if value[0] != "Supp":
                cnt += 1
        return cnt

    def parse(self):

        cnames = {}
        r = re.compile("^traefik\.https?\.routers\..+\.rule$")
        hst = re.compile("Host\(\s*(`(?:[^`]+)`(?:\s*,\s*`(?:[^`]+)`)*)\s*\)")

        for container in self.docker.containers.list():
            labels = container.labels

            if (self.enable == False and "docker-mdns.enable" in labels and labels[
                "docker-mdns.enable"].lower() == "true") or (self.enable == True and not (
                    "docker-mdns.enable" in labels and labels["docker-mdns.enable"].lower() == "false")):
                res = list(filter(r.match, list(labels.keys())))
                if len(res) > 0:
                    for val in res:
                        for match in hst.finditer(labels[val]):
                            string_lst = [s.strip() for s in re.split(",(?=\s*`)", match.group(1))]
                            for domain in string_lst:
                                match1 = re.match("`(.*)`",domain)
                                if match1:
                                    cnames[match1.group(1)] = True
                if "docker-mdns.domain" in labels:
                    cnames[labels["docker-mdns.domain"]] = True

        for key in cnames.keys():
            if key not in self.domains:
                self.add_domain(key, "Docker")

        for key,value in self.domains.items():
            if key not in cnames and value[0] == "Docker":
                self.domains[key][0] = "Supp"

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

        try:
            return self.docker.ping()
        except docker.errors.APIError as e:
            logging.error("Lost Connection to Docker")
            return False
