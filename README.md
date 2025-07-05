# Docker mDNS Helper

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Available-blue.svg)](https://hub.docker.com/r/stefapi/docker-mdns-helper)

This service automatically publishes CNAME records pointing to the local host over
[multicast DNS (mDNS)](http://www.multicastdns.org) using the [Avahi](http://www.avahi.org/wiki/AboutAvahi)
daemon found in all major Linux distributions. It's designed as a service discovery solution and
development helper for named virtual hosts.

Since Avahi is compatible with Apple's [Bonjour](https://www.apple.com/support/bonjour),
these domain names are accessible from macOS, Windows, and other platforms supporting mDNS.

This tool integrates seamlessly with [Traefik](https://traefik.io/) reverse proxy configurations,
automatically detecting container labels and publishing corresponding mDNS records.

## Features

- 🚀 **Automatic Discovery**: Monitors Docker containers and publishes mDNS records based on labels
- 🏷️ **Traefik Integration**: Reads Traefik router labels to automatically create mDNS records
- 🔄 **Dynamic Updates**: Real-time updates when containers start, stop, or change
- 🌐 **Cross-Platform**: Works with macOS (Bonjour), Windows, and Linux
- ⚡ **Lightweight**: Minimal resource usage with efficient monitoring
- 🛡️ **Health Monitoring**: Built-in health checks for reliable operation
- 🔧 **Version Compatibility**: Supports Traefik v1, v2, and v3 label formats
- 🐳 **Docker API Compatibility**: Works with Docker API versions 1.24+ (Docker 17.06+)

## Quick Start

### Prerequisites

- **Linux system** with systemd (Ubuntu, Debian, CentOS, etc.)
- **Avahi daemon** installed and running
- **Docker** installed and running
- **Root/sudo access** for initial setup

### Installation

1. **Install Avahi** (if not already installed):
   ```bash
   # Ubuntu/Debian
   sudo apt install avahi-daemon

   # CentOS/RHEL/Fedora
   sudo yum install avahi-daemon  # or dnf install avahi-daemon
   ```

2. **Configure Avahi** to enable D-Bus:
   ```bash
   sudo sed -i 's/#enable-dbus=yes/enable-dbus=yes/' /etc/avahi/avahi-daemon.conf
   ```

3. **Restart Avahi**:
   ```bash
   sudo systemctl restart avahi-daemon
   sudo systemctl enable avahi-daemon  # Enable auto-start
   ```

4. **Run Docker mDNS Helper**:
   ```bash
   docker run -d \
     --name=mdns \
     --privileged \
     --network=host \
     -v /var/run/dbus/system_bus_socket:/var/run/dbus/system_bus_socket \
     -v /var/run/docker.sock:/var/run/docker.sock \
     stefapi/docker-mdns-helper:latest
   ```

That's it! The service will now automatically publish mDNS records for your Docker containers.


## Configuration

Docker mDNS Helper automatically reads configuration from Docker container labels, similar to how Traefik works. mDNS records are only updated when labels change, ensuring efficient operation.

### Container Labels

#### Enable/Disable Publishing

- **`docker-mdns.enable`**: Controls whether the container should be published via mDNS
  - `true`: Force enable mDNS publishing for this container
  - `false`: Disable mDNS publishing for this container
  - If not specified: Follows the global default (enabled unless `--disable` flag is used)

#### Domain Configuration

**Method 1: Traefik Integration (Recommended)**

The service automatically reads Traefik router labels to create mDNS records:

```yaml
labels:
  - "traefik.http.routers.myapp.rule=Host(`myapp.local`)"
  - "traefik.http.routers.api.rule=Host(`api.local`, `admin.local`)"
```

**Method 2: Direct Domain Specification**

Use the `docker-mdns.domain` label for custom domains:

```yaml
labels:
  - "docker-mdns.domain=custom.local"
```

### Domain Naming Guidelines

- ✅ **Recommended**: `myapp.local`, `api-server.local`, `web-app.local`
- ❌ **Avoid**: `sub.domain.local` (subdomains may not work on all platforms)
- Use hyphens instead of dots for complex names: `my-api-server.local`

### Example Container Configuration

```yaml
version: '3.8'
services:
  webapp:
    image: nginx
    labels:
      - "docker-mdns.enable=true"
      - "traefik.http.routers.webapp.rule=Host(`webapp.local`)"
      # This will create: webapp.local -> localhost
```

## Command Line Options

Docker mDNS Helper supports various command-line options to customize its behavior:

### Basic Options

| Option | Long Form | Description | Default |
|--------|-----------|-------------|---------|
| `-d` | `--disable` | Disable automatic mDNS publishing. Requires `docker-mdns.enable=true` label on containers | Enabled |
| `-D` | `--daemon` | Run as daemon (for systemd integration) | Foreground |
| `-v` | `--verbose` | Enable verbose logging for debugging | Info level |
| `-l <file>` | `--log <file>` | Write logs to specified file instead of stderr | stderr |

### Advanced Options

| Option | Long Form | Description | Default |
|--------|-----------|-------------|---------|
| `-t <seconds>` | `--ttl <seconds>` | Set TTL for published CNAME records | 60 |
| `-w <seconds>` | `--wait <seconds>` | Pause between Docker container scans | 5 |
| `-r` | `--reset` | Remove stale domains when containers are removed | Disabled |
| `-f` | `--force` | Skip collision detection (faster but potentially unsafe) | Disabled |

### Additional Domains

You can specify additional static domains to publish:

```bash
docker run ... stefapi/docker-mdns-helper:latest domain1.local domain2.local
```

### Usage Examples

```bash
# Basic usage with verbose logging
docker run ... stefapi/docker-mdns-helper:latest -v

# Disable auto-discovery, only publish labeled containers
docker run ... stefapi/docker-mdns-helper:latest -d

# Custom TTL and scan interval
docker run ... stefapi/docker-mdns-helper:latest -t 120 -w 10

# Log to file with reset enabled
docker run ... stefapi/docker-mdns-helper:latest -l /var/log/mdns.log -r
```

## Version Compatibility

Docker mDNS Helper is designed to work with various versions of Docker and Traefik:

### Supported Docker Versions

| Component | Minimum Version | Recommended | Notes |
|-----------|----------------|-------------|-------|
| **Docker Engine** | 17.06+ | 20.10+ | API version 1.24+ required |
| **Docker API** | 1.24+ | 1.41+ | Automatic detection and compatibility warnings |
| **Docker Compose** | 1.25+ | 2.0+ | Version 3.8+ compose file format |

### Supported Traefik Versions

The service automatically detects and supports Traefik v1, v2, and v3 label formats:

#### Traefik v3 (Latest)
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.myapp.rule=Host(`myapp.local`)"
  - "traefik.https.routers.myapp-secure.rule=Host(`myapp.local`)"
```

#### Traefik v2 (Recommended)
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.myapp.rule=Host(`myapp.local`)"
  - "traefik.https.routers.myapp-secure.rule=Host(`myapp.local`)"
```

#### Traefik v1 (Legacy Support)
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.frontend.rule=Host:myapp.local"
```

**Note**: Traefik v3 maintains backward compatibility with v2 label formats, so existing v2 configurations work seamlessly with v3.

### Build Customization

You can customize the Python version used in the Docker image:

```bash
# Build with different Python version
docker build --build-arg PYTHON_VERSION=3.11 -t docker-mdns-helper .

# Or using docker-compose with environment variable
PYTHON_VERSION=3.11 docker-compose build
```

**Supported Python Versions**: 3.8, 3.9, 3.10, 3.11

## Installation Methods

### Docker Hub (Recommended)

```bash
docker pull stefapi/docker-mdns-helper:latest
```

**Supported Architectures**: AMD64 (x86_64)

### From Source

1. **Clone the repository**:
   ```bash
   git clone https://github.com/stefapi/docker-mdns-helper.git
   cd docker-mdns-helper
   ```

2. **Build the Docker image**:
   ```bash
   docker build -t docker-mdns-helper .
   ```

3. **Or install as Python package**:
   ```bash
   pip install -r requirements.txt
   python start.py --help
   ```

## Docker Configuration

### Required Volumes

The container requires two essential volume mounts:

| Volume | Purpose | Required |
|--------|---------|----------|
| `/var/run/docker.sock:/var/run/docker.sock` | Monitor Docker containers | ✅ Yes |
| `/var/run/dbus/system_bus_socket:/var/run/dbus/system_bus_socket` | Communicate with Avahi daemon | ✅ Yes |

### Required Permissions

- **`--privileged`**: Required for D-Bus system bus access
- **`--network=host`**: Required for mDNS broadcasting

### Complete Example

```bash
docker run -d \
  --name=mdns \
  --privileged \
  --network=host \
  --restart=unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /var/run/dbus/system_bus_socket:/var/run/dbus/system_bus_socket \
  stefapi/docker-mdns-helper:latest -r
```

## Troubleshooting

### Common Issues

**1. "Failed to connect to Avahi daemon"**
```bash
# Check if Avahi is running
sudo systemctl status avahi-daemon

# Enable D-Bus in Avahi config
sudo sed -i 's/#enable-dbus=yes/enable-dbus=yes/' /etc/avahi/avahi-daemon.conf
sudo systemctl restart avahi-daemon
```

**2. "Permission denied accessing Docker socket"**
```bash
# Ensure Docker socket is accessible
ls -la /var/run/docker.sock

# Container runs as root, so this should work with --privileged
```

**3. "mDNS records not visible on network"**
```bash
# Test mDNS resolution
avahi-resolve -n yourapp.local

# Check if domains are published
avahi-browse -at
```

### Health Check

The container includes a built-in health check that verifies Avahi connectivity:

```bash
# Check container health
docker ps --format "table {{.Names}}\t{{.Status}}"
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

- 📖 **Documentation**: [GitHub Repository](https://github.com/stefapi/docker-mdns-helper)
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/stefapi/docker-mdns-helper/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/stefapi/docker-mdns-helper/discussions)
