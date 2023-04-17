#!/usr/bin/env sh

apk add --no-cache python3 nginx py3-django py3-pillow py3-pip py3-gunicorn py3-mysqlclient
pip install django-markdownx
