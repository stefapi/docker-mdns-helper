ARG PYTHON_VERSION=3.9
FROM python:${PYTHON_VERSION}-alpine
LABEL maintainer="stephane@apiou.org"
LABEL org.opencontainers.image.title="Docker mDNS Helper"
LABEL org.opencontainers.image.description="Publishes Docker container domains via Avahi/mDNS"
LABEL org.opencontainers.image.source="https://github.com/stefapi/docker-mdns-helper"
LABEL org.opencontainers.image.licenses="Apache-2.0"

# Install system dependencies
RUN apk add --no-cache \
    dbus \
    dbus-glib-dev \
    libc-dev \
    gcc \
    make \
    && rm -rf /var/cache/apk/*

WORKDIR /app/

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Health check to ensure the service is running properly
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import dbus; dbus.SystemBus().get_object('org.freedesktop.Avahi', '/').GetVersionString()" || exit 1

# Note: This application requires privileged access to D-Bus and Docker sockets
# Running as root is necessary for proper functionality

ENTRYPOINT ["python", "start.py"]
CMD ["-r"]
