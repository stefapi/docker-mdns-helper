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
DEFAULT_PAUSE_TIME = 5

def handle_signals(publisher, signum, frame):
    """Unpublish all mDNS records and exit cleanly."""

    try:
        signame = next((v for v, k in signal.__dict__.items() if k == signum), f"Signal {signum}")
        logging.info("Received %s, shutting down gracefully...", signame)

        if publisher:
            try:
                publisher.__del__()
            except Exception as e:
                logging.error("Error during publisher cleanup: %s", e)

        # Avahi needs time to forget us...
        sleep(1)

        logging.info("Shutdown complete")
        sys.exit(0)
    except Exception as e:
        logging.error("Error during signal handling: %s", e)
        os._exit(1)


def main():
    parser = ArgumentParser( description="Helper container which publishes mDNS records based on Docker container labels and Traefik configuration")
    parser.add_argument('-l', '--log', help='Send log messages into the specified file.', metavar='<filename>')
    parser.add_argument('-D', '--daemon', help='Launch as a daemon.',action='store_true')
    parser.add_argument('-d', '--disable', help='All detected CNAMES are not published if not indicated.',action='store_true')
    parser.add_argument('-r', '--reset', help='Reset publishing if a CNAME is removed', action='store_true')
    parser.add_argument('-t', '--ttl', help='Set the TTL for all published CNAME records.', default=DEFAULT_DNS_TTL, metavar='<ttl>')
    parser.add_argument('-v', '--verbose', help='Produce extra output for debugging purposes.', action='store_true')
    parser.add_argument('-f', '--force', help='Publish all CNAMEs without checking if they are already being published elsewhere on the network. This is much faster, but generally unsafe.', action='store_true')
    parser.add_argument('-w', '--wait', help='waiting time between each analysis loop', default=DEFAULT_PAUSE_TIME, metavar='<seconds>')
    parser.add_argument("cnames", help="List of cnames <hostname.local> to publish in addition to docker", nargs='*')

    res = parser.parse_args(sys.argv[1:])

    # Validate and convert parameters with proper error handling
    try:
        ttl = int(res.ttl)
        if ttl <= 0 or ttl > 86400:  # Max 24 hours
            raise ValueError("TTL must be between 1 and 86400 seconds")
    except ValueError as e:
        print(f"error: invalid TTL value: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        refresh_rate = int(res.wait)
        if refresh_rate <= 0 or refresh_rate > 3600:  # Max 1 hour
            raise ValueError("Wait time must be between 1 and 3600 seconds")
    except ValueError as e:
        print(f"error: invalid wait time: {e}", file=sys.stderr)
        sys.exit(1)

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
    consecutive_errors = 0
    max_consecutive_errors = 5

    try:
        docker_domains = DockerDomains(enable)
        docker_domains.add_domains(cnames_cmd)
    except Exception as e:
        logging.error("Failed to initialize Docker domains: %s", e)
        sys.exit(1)

    while True:
        try:
            if not docker_domains.available():
                logging.info("Docker connection lost, reinitializing...")
                docker_domains = DockerDomains(enable)
                docker_domains.add_domains(cnames_cmd)

            docker_domains.parse()

            if docker_domains.suppressed() and reset and publisher is not None:
                try:
                    publisher.__del__()
                    sleep(1)
                    publisher = None
                    docker_domains.clean()
                    logging.info("Republishing all CNAMEs")
                except Exception as e:
                    logging.error("Error during publisher reset: %s", e)

            if not publisher or not publisher.available():
                try:
                    publisher = AvahiPublisher(ttl)
                    # To make sure records disappear immediately on exit, clean up properly...
                    signal.signal(signal.SIGTERM, functools.partial(handle_signals, publisher))
                    signal.signal(signal.SIGINT, functools.partial(handle_signals, publisher))
                    signal.signal(signal.SIGQUIT, functools.partial(handle_signals, publisher))
                    docker_domains.all_new()
                    logging.info("Avahi publisher initialized")
                except Exception as e:
                    logging.error("Failed to initialize Avahi publisher: %s", e)
                    publisher = None

            if publisher and docker_domains.updated():
                update_list = docker_domains.update_list()
                for cname in update_list:
                    try:
                        status = publisher.publish_cname(cname, force)
                        if not status:
                            logging.error("Failed to publish '%s'", cname)
                            continue
                        else:
                            docker_domains.update(cname)
                    except Exception as e:
                        logging.error("Error publishing '%s': %s", cname, e)

                if publisher.count() == len(docker_domains):
                    logging.info("All CNAMEs published")
                else:
                    logging.warning("%d out of %d CNAMEs published", publisher.count(), len(docker_domains))

            # Reset error counter on successful iteration
            consecutive_errors = 0

        except KeyboardInterrupt:
            logging.info("Received keyboard interrupt, shutting down...")
            break
        except Exception as e:
            consecutive_errors += 1
            logging.error("Unexpected error in main loop (attempt %d/%d): %s",
                         consecutive_errors, max_consecutive_errors, e)

            if consecutive_errors >= max_consecutive_errors:
                logging.error("Too many consecutive errors, shutting down")
                sys.exit(1)

            # Wait longer after errors to avoid rapid failure loops
            sleep(min(refresh_rate * consecutive_errors, 60))
            continue

        # CNAMEs will exist until we renew it within the TTL duration
        sleep(refresh_rate)

    # Clean shutdown
    if publisher:
        try:
            publisher.__del__()
        except Exception as e:
            logging.error("Error during final cleanup: %s", e)


if __name__ == "__main__":
    main()


# vim: set expandtab ts=4 sw=4:
