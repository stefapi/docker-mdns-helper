### docker-compose

this docker compose launchs: docker-mdns-helper, docker-dashy-helper, traefik, watchtower, dashy and a sample service: Whoami.
2 domains are created: test.local and whoami.local.
Everything is defined dynamically by labels.

Actions to perform:
* Create an empty `dashy-conf.yml` file. Type:
```
touch dashy-conf.yml
```
* Create a `docker-compose.yml` file. Type
```
touch docker-compose.yml
```
* edit this file and put into the following text:
```yaml
version: "3.8"
services:

#Docker-mDns-Helper
  mdns:
    container_name: mdns
    image: stefapi/docker-mdns-helper:latest
    labels:
      - "docker-dashy.enable=false"
      - "traefik.enable=false"
    volumes:
      - /var/run/dbus/system_bus_socket:/var/run/dbus/system_bus_socket
      - /var/run/docker.sock:/var/run/docker.sock
    network_mode: "host"
    privileged: true
    restart: unless-stopped

#Reverse Proxy
  traefik:
    container_name: traefik
    image: traefik
    command:
      - "--api.insecure=true"
      - "--api.dashboard=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--log.level=DEBUG"
      - "--entrypoints.web.address=:80"
    labels:
      - "docker-dashy.enable=false"
      - "traefik.enable=false"
      - "docker-dashy.navlink.board.link=Url(`Dashboard`,`http://test.local:8080`)"
    ports:
      - "80:80"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    restart: unless-stopped

#Docker-dashy-Helper
  docker-dashy:
    container_name: docker-dashy
    image: stefapi/docker-dashy-helper:latest
    command:
      - "-n test.local"
      - "-l fr"
      - "-r"
      - "/app/conf.yml"
    labels:
      - "docker-dashy.enable=false"
      - "traefik.enable=false"
    volumes:
      - ./dashy-conf.yml:/app/conf.yml
      - /var/run/docker.sock:/var/run/docker.sock
    network_mode: "host"
    privileged: true
    restart: unless-stopped

#Watchtower
  watchtower:
    container_name: watchtower
    image: containrrr/watchtower 
    command:
      - "--cleanup"
    labels:
      - "docker-dashy.enable=false"
      - "traefik.enable=false"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    network_mode: "host"
    restart: unless-stopped

#Dashy
  dashy:
    container_name: dashy
    image: lissy93/dashy:latest
    labels:
      - "traefik.enable=true"
      - "docker-dashy.enable=true"
      - "docker-dashy.site=true"
      - "traefik.http.routers.test.rule=Host(`test.local`)"
      - "traefik.http.services.test.loadbalancer.server.port=80"
      - "traefik.http.routers.test.entrypoints=web"
      - "docker-dashy.comment=Test Site"
      - "docker-dashy.footer=Powered by Dashy and docker-dashy-helper"
      - "docker-dashy.icon=https://dashy.to/img/dashy.png"
    volumes:
      - ./dashy-conf.yml:/app/public/conf.yml
      - /var/run/docker.sock:/var/run/docker.sock
    ports:
      - "5000:80"
    restart: unless-stopped


#Basic Web Service
  whoami:
    image: "containous/whoami"
    container_name: "simple-service"
    labels:
      - "traefik.enable=true"
      - "docker-dashy.enable=true"
      - "traefik.http.routers.whoami.rule=Host(`whoami.local`)"
      - "traefik.http.routers.whoami.entrypoints=web"
      - "traefik.http.services.whoami.loadbalancer.server.port=80"
      - "docker-dashy.icon=far fa-question-circle"
      - "docker-dashy.label=Wo am I"
      - "docker-dashy.group=tools"
      - "docker-dashy.grp-icon=fas fa-tools"
    ports:
      - "6000:80"
    restart: unless-stopped
```
* Save the file and Start the composition:
```
docker-compose up -d
```
* Point your browser to http://test.local or http://whoami.local or http://test.local:5000 or http://test.local:6000 or http://test.local:8080
* Enjoy !
