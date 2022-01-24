FROM python:3.9-bullseye
LABEL maintainer="stephane@apiou.org"

RUN \
    apt update \
    && apt install -y -q -q --no-install-recommends libdbus-1-3 libdbus-1-dev \
    && apt-get autoclean \
    && apt-get clean \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/*


RUN \
  pip install -U pip && \
  python --version

WORKDIR /app/

COPY . .
RUN pip install docker dbus-python

ENTRYPOINT ["python", "start.py"]
CMD ["-r"]
