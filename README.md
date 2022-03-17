# Docker-mdns-helper

This service publishes CNAME records pointing to the local host over
[multicast DNS](http://www.multicastdns.org) using the [Avahi](http://www.avahi.org/wiki/AboutAvahi)
daemon found in all major Linux distributions. Useful as a poor-man's service discovery or as a
helper for named virtual-hosts in development environments.

Since Avahi is compatible with Apple's [Bonjour](https://www.apple.com/support/bonjour),
these names are usable from MacOS X and Windows too.

This works well with [Traefik](https://traefik.io/) and [Docker-Dashy-Helper](https://hub.docker.com/repository/docker/stefapi/docker-dashy-helper)

Git repository of the Docker distribution is on [Github Docker-mDNS-Helper](https://github.com/stefapi/docker-mdns-helper)

## TL;DR

It works out of the box, just:
* Check that Avahi is installed on your system. If not, install it as root: `apt install avahi-daemon` for a Debian or Ubuntu system
* Change the configuration in your `/etc/avahi/avahi-daemon.conf` file: uncomment or add `enable-dbus=yes`
* Restart avahi. Type as root: `service avahi-daemon restart`
* Launch docker-mdns-helper:
```
$ docker run -d --name=mdns -v /var/run/dbus/system_bus_socket:/var/run/dbus/system_bus_socket -v /var/run/docker.sock:/var/run/docker.sock stefapi/docker-mdns-helper:latest
```

That's all !


## Configuration

All the configuration is read from container labels (Like Traefik) and the Dashy configuration file is only written if the labels have changed.


### CNAMES definition

CNAMES are defined by the following parameters:

`docker-mdns.enable` label conditions the following labels. If set to `true` the labels defined hereunder will be taken into account. if `docker-mdns.enable` is not specified, the default behavior is to enable the container definition unless the `--disable` parameter is specified when launching.

It reads the same container labels as Traefik to define CNAMES e.g. :

```
-l 'traefik.http.routers.r1.rule=Host(`r1example.local`)'
-l 'traefik.https.routers.r1.rule=Host(`r2example.local`, `alterdomain.local`)'
```

CNAMES may be personalised by using the `docker-mdns.domain` label like this:

````
-l 'docker-mdns.domain=r3example.com'
````

**WARNING**:  Sub domains ( like `sub.example.local` ) seems not to work on all platforms. Use domains instead (like `sub-example.local`)

## Command line arguments

Docker-mdns-helper has no mandatory parameter.

Optional parameter `-d` or `--disable` disables the automatic addition of docker containers to Dashy. You have to put the label `docker-mdns.enable=true` for each container to be added.

Optional parameter `-D` or `--daemon` launches the program as a daemon. Only necessary if using it with systemd on host machine.

Optional parameter `-l` or `--log` defines the filename to use to write logs to.

Optional parameter `-r` or `--reset` when active, all domains which are no more published with a Treafik label or docker-mdns.domain label are removed from avahi. During the reconfiguration no domain published by docker-mdns-helper will be published causing a temporary domain failure

Optional parameter `-t` or `--ttl` defines ttl of CNAMES publication. Default 60 seconds.

Optional parameter `-w` or `--wait` defines pause between CNAMES scans on Docker. Default 5 seconds.

Optional parameter `-v` or `--verbose` increase the level of verbosity of output.

Optional parameter `-f` or `--force` publishes a CNAME without prior existence test. Accelerates the publication of CNAMES but if CNAMES are already published, this may crash Avahi.

Following all theses options you could pass a list of CNAMES to publish

## Installing

`docker pull stefapi/docker-mdns-helper`

Currently there are AMD64 based builds.

## Building

Get git repository:

`git pull https://github.com/stefapi/docker-mdns-helper`

Build Docker file:

`docker build .`

## Running

You have to attach 2 volumes:

` -v /var/run/docker.sock:/var/run/docker.sock`

` -v /var/run/dbus/system_bus_socket:/var/run/dbus/system_bus_socket`

First is used to read docker configuration and the second is used to communicate with Avahi on host system

Free Sample of container lauch:
```
$ docker run -d --name=mdns -v /var/run/dbus/system_bus_socket:/var/run/dbus/system_bus_socket -v /var/run/docker.sock:/var/run/docker.sock stefapi/docker-mdns-helper:latest -r domain.local anotherdomain.local
```


