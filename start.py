#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# publish-cname.py - publish CNAMEs pointing to the local host over Avahi/mDNS.
#
# Copyright (c) 2014, SAPO
#


from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals
from __future__ import absolute_import

import sys
import os, os.path
import logging
import logging.handlers
import re
import signal
import functools

from time import sleep

from daemonize import daemonize
from avahi_publisher import AvahiPublisher
from argparse import ArgumentParser
from docker_domains import DockerDomains


# Default Time-to-Live for mDNS records, in seconds...
DEFAULT_DNS_TTL = 60

def handle_signals(publisher, signum, frame):
    """Unpublish all mDNS records and exit cleanly."""

    signame = next(v for v, k in signal.__dict__.items() if k == signum)
    logging.debug("Cleaning up on %s...", signame)
    publisher.__del__()

    # Avahi needs time to forget us...
    sleep(1)

    os._exit(0)


def main():
    parser = ArgumentParser( description="Helper container which updates Dashy configuration based on Docker or Traefik configuration")
    parser.add_argument('-l', '--log', help='Send log messages into the specified file.', nargs=1, metavar='<filename>')
    parser.add_argument('-D', '--daemon', help='Lauch as a daemon.',action='store_true')
    parser.add_argument('-d', '--disable', help='All detected CNAMES are not published if not indicated.',action='store_true')
    parser.add_argument('-r', '--reset', help='Reset publishing if a CNAME is removed', action='store_true')
    parser.add_argument('-t', '--ttl', help='Set the TTL for all published CNAME records.', nargs=1, default=DEFAULT_DNS_TTL, metavar='<ttl>')
    parser.add_argument('-v', '--verbose', help='Produce extra output for debugging purposes.', action='store_true')
    parser.add_argument('-f', '--force', help='Publish all CNAMEs without checking if they are already being published elsewhere on the network. This is much faster, but generally unsafe.', action='store_true')
    parser.add_argument("cnames", help="List of cnames <hostname.local> to publish in addition to docker", nargs='*')

    res = parser.parse_args(sys.argv[1:])
    ttl = int(res.ttl)
    force = res.force
    verbose = res.verbose
    log = res.log
    daemon = res.daemon
    enable = not res.disable
    reset = res.reset
    cnames_cmd = [ cname.lower() for cname in res.cnames ]

    cname_re = re.compile(r"^[a-z0-9-]{1,63}(?:\.[a-z0-9-]{1,63})*\.local$")

    for cname in cnames_cmd:
        if not cname_re.match(cname):
            print("error: malformed hostname: %s" % cname, file=sys.stderr)
            parser.print_usage()
            sys.exit(1)

    # Since an eventual log file must support external log rotation, we must do this the hard way...
    format = logging.Formatter("%(asctime)s: %(levelname)s [%(process)d]: %(message)s")
    handler = logging.handlers.WatchedFileHandler(log) if log else logging.StreamHandler(sys.stderr)
    handler.setFormatter(format)
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # This must be done after initializing the logger, so that an eventual log file gets created in
    # the right place (the user will assume that relative paths start from the current directory)...
    if daemon:
        daemonize()

    logging.info("Avahi/mDNS publisher starting...")

    if force:
        logging.info("Forcing CNAME publishing without collision checks")

    # The publisher needs to be initialized in the loop, to handle disconnects...
    publisher = None

    docker_domains = DockerDomains(enable)
    docker_domains.add_domains(cnames_cmd)

    while True:
        if not docker_domains.available():
            docker_domains = DockerDomains(enable)
            docker_domains.add_domains(cnames_cmd)

        docker_domains.parse()

        if docker_domains.suppressed() and reset and publisher is not None:
            publisher.__del__()
            sleep(1)
            publisher = None
            docker_domains.clean()
            logging.info("Republishing all CNAMEs")

        if not publisher or not publisher.available():
            publisher = AvahiPublisher(ttl)
            # To make sure records disappear immediately on exit, clean up properly...
            signal.signal(signal.SIGTERM, functools.partial(handle_signals, publisher))
            signal.signal(signal.SIGINT, functools.partial(handle_signals, publisher))
            signal.signal(signal.SIGQUIT, functools.partial(handle_signals, publisher))
            docker_domains.all_new()

        if docker_domains.updated():
            list = docker_domains.update_list()
            for cname in list:
                status = publisher.publish_cname(cname, force)
                if not status:
                    logging.error("Failed to publish '%s'", cname)
                    continue
                else:
                    docker_domains.update(cname)

            if publisher.count() == len(docker_domains):
                logging.info("All CNAMEs published")
            else:
                logging.warning("%d out of %d CNAMEs published", publisher.count(), len(docker_domains))

        # CNAMEs will exist until we renew it within the TTL duration
        sleep(1)


if __name__ == "__main__":
    main()


# vim: set expandtab ts=4 sw=4:
