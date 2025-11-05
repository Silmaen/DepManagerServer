#!/usr/bin/env bash

set -e
echo "**** Making messages..."
python3 server/scripts/manage.py makemessages -l en -l fr