#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

docker run -d -p 8080:80 -e PUID=2000 -e APPNAME=pack -e TZ=Europe/Paris -v ${SCRIPT_DIR}/server/config:/server/config -v ${SCRIPT_DIR}/server/data:/server/data -v ${SCRIPT_DIR}/server/scripts:/server/scripts registry.argawaen.net/argawaen/django_server
