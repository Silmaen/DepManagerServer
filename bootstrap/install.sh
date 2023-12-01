#!/usr/bin/env sh

set -e

apk add --no-cache tzdata
apk add --no-cache nginx nginx-mod-http-upload nginx-mod-stream nginx-mod-http-upload-progress nginx-mod-http-encrypted-session
apk add --no-cache python3 py3-django py3-pillow py3-gunicorn
chmod 777 -R /server
chmod 777 /bootstrap/start.py
