FROM python:3.9-alpine
LABEL maintainer="stephane@apiou.org"

RUN apk add dbus-glib-dev libc-dev gcc make --no-cache

WORKDIR /app/

COPY . .

RUN pip install docker dbus-python

ENTRYPOINT ["python", "start.py"]
CMD ["-r"]
