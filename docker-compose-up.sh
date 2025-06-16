#!/usr/bin/env bash
set -e

if [[ -e .env ]]; then
  . .env
else
  TZ=Europe/Paris
  PUID=1000
  PGID=1000
  DEBUG=false
  DOMAIN_NAME=example.com
  ADMIN_NAME=admin
  ADMIN_PASSWD=admin
fi

echo "DEBUG=${DEBUG}" > .env
echo "TZ=${TZ}" >> .env
echo "PUID=${PUID}" >> .env
echo "PGID=${PGID}" >> .env
echo "DOMAIN_NAME=${DOMAIN_NAME}" >> .env
echo "ADMIN_NAME=${ADMIN_NAME}" >> .env
echo "ADMIN_PASSWD=${ADMIN_PASSWD}" >> .env
echo "GIT_HASH=$(git rev-parse --short HEAD)" >> .env

docker compose up -d --build