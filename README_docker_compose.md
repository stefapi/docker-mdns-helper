# Docker Compose Setup

This Docker Compose configuration demonstrates a complete setup with:
- **Docker mDNS Helper**: Automatic mDNS record publishing
- **Traefik**: Reverse proxy with automatic service discovery
- **Watchtower**: Automatic container updates
- **Whoami**: Sample web service for testing

## What You'll Get

After setup, you'll have these domains automatically available:
- `whoami.local` → Sample web service
- `test.local:8080` → Traefik dashboard

All domains are configured dynamically through container labels - no manual DNS configuration needed!

## Prerequisites

- Docker and Docker Compose installed
- Avahi daemon running on the host (see main README for setup)
- Linux host system

## Quick Setup

### 1. Create the Docker Compose file

```bash
touch docker-compose.yml
```

### 2. Add the configuration

Copy the following content into your `docker-compose.yml` file:
```yaml
version: "3.8"
services:
  # Docker mDNS Helper - Publishes container domains via Avahi/mDNS
  mdns:
    container_name: mdns
    image: stefapi/docker-mdns-helper:latest
    labels:
      - "traefik.enable=false"  # Don't expose through Traefik
    volumes:
      - /var/run/dbus/system_bus_socket:/var/run/dbus/system_bus_socket  # Avahi communication
      - /var/run/docker.sock:/var/run/docker.sock  # Docker API access
    network_mode: "host"  # Required for mDNS broadcasting
    privileged: true      # Required for D-Bus system access
    restart: unless-stopped
    command: ["-r"]       # Enable reset mode for clean domain management

  # Traefik Reverse Proxy - Routes traffic based on domain names
  # Note: Works with Traefik v2.x and v3.x (use traefik:v3.0 for latest v3)
  traefik:
    container_name: traefik
    image: traefik:v2.10
    command:
      - "--api.insecure=true"                           # Enable dashboard (dev only!)
      - "--api.dashboard=true"                          # Enable web UI
      - "--providers.docker=true"                       # Enable Docker provider
      - "--providers.docker.exposedbydefault=false"     # Require explicit enable
      - "--log.level=INFO"                              # Logging level
      - "--entrypoints.web.address=:80"                 # HTTP entrypoint
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.dashboard.rule=Host(`test.local`)"
      - "traefik.http.routers.dashboard.entrypoints=web"
      - "traefik.http.routers.dashboard.service=api@internal"
    ports:
      - "80:80"    # HTTP traffic
      - "8080:8080"  # Dashboard (alternative access)
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro  # Docker API (read-only)
    restart: unless-stopped

  # Watchtower - Automatic container updates
  watchtower:
    container_name: watchtower
    image: containrrr/watchtower:latest
    command:
      - "--cleanup"           # Remove old images after update
      - "--interval"          # Check every 24 hours
      - "86400"
    labels:
      - "traefik.enable=false"  # Don't expose through Traefik
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # Docker API access
    restart: unless-stopped

  # Sample Web Service - Demonstrates the setup
  whoami:
    image: "traefik/whoami:latest"  # Updated image
    container_name: "whoami-service"
    labels:
      - "traefik.enable=true"  # Enable Traefik routing
      - "traefik.http.routers.whoami.rule=Host(`whoami.local`)"  # Domain routing
      - "traefik.http.routers.whoami.entrypoints=web"            # Use HTTP entrypoint
      - "traefik.http.services.whoami.loadbalancer.server.port=80"  # Backend port
    ports:
      - "6000:80"  # Direct access (optional)
    restart: unless-stopped
```

### 3. Start the services

```bash
# Start all services in the background
docker-compose up -d

# Check that all services are running
docker-compose ps
```

### 4. Test the setup

Once all containers are running, test the mDNS domains:

```bash
# Test domain resolution (if avahi-utils is installed)
avahi-resolve -n whoami.local
avahi-resolve -n test.local

# Or simply open in your browser:
```

**Available URLs:**
- 🌐 **http://whoami.local** - Sample web service (via Traefik)
- 🌐 **http://whoami.local:6000** - Sample web service (direct access)
- 📊 **http://test.local** - Traefik dashboard (via mDNS)
- 📊 **http://localhost:8080** - Traefik dashboard (direct access)

## Service Explanations

### Docker mDNS Helper
- **Purpose**: Automatically publishes mDNS records for containers with Traefik labels
- **How it works**: Monitors Docker events and creates `*.local` domains pointing to localhost
- **Configuration**: Uses the `-r` flag to clean up stale domains

### Traefik
- **Purpose**: Reverse proxy that routes HTTP traffic based on domain names
- **Configuration**: Automatically discovers services via Docker labels
- **Version Support**: Compatible with Traefik v2.x and v3.x (v3 maintains backward compatibility)
- **Dashboard**: Accessible at `test.local` (thanks to mDNS Helper!)

### Watchtower
- **Purpose**: Automatically updates containers when new images are available
- **Schedule**: Checks for updates every 24 hours
- **Cleanup**: Removes old images after successful updates

### Whoami Service
- **Purpose**: Simple web service that displays request information
- **Access**: Available via `whoami.local` domain and direct port `6000`
- **Use case**: Perfect for testing the mDNS + Traefik integration

## Troubleshooting

### Domains not resolving
```bash
# Check if mDNS helper is running and healthy
docker logs mdns

# Verify Avahi is working on the host
sudo systemctl status avahi-daemon

# Check if domains are being published
avahi-browse -at | grep whoami
```

### Traefik not routing traffic
```bash
# Check Traefik logs
docker logs traefik

# Verify container labels
docker inspect whoami-service | grep -A 10 Labels

# Check Traefik dashboard for registered services
# Visit: http://test.local or http://localhost:8080
```

### Services not starting
```bash
# Check service status
docker-compose ps

# View logs for specific service
docker-compose logs mdns
docker-compose logs traefik

# Restart specific service
docker-compose restart mdns
```

## Adding Your Own Services

To add your own service with automatic mDNS publishing:

```yaml
  myapp:
    image: "your-app:latest"
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.myapp.rule=Host(`myapp.local`)"
      - "traefik.http.routers.myapp.entrypoints=web"
      - "traefik.http.services.myapp.loadbalancer.server.port=8080"
    restart: unless-stopped
```

The mDNS Helper will automatically create `myapp.local` → `localhost` mapping!

## Cleanup

To stop and remove all services:

```bash
# Stop services
docker-compose down

# Remove volumes and networks (optional)
docker-compose down -v --remove-orphans
```
