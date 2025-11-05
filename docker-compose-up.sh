#!/usr/bin/env bash
set -e

if [[ -e .env ]]; then
  . .env
else
  TZ=Europe/Paris
  PUID=1000
  PGID=1000
  DEBUG=false
  DOMAIN_NAME="example.com"
  ADMIN_NAME="admin"
  ADMIN_PASSWD="admin"
fi

# (re)create .env file
{
  echo "DEBUG=${DEBUG}";
  echo "TZ=${TZ}";
  echo "PUID=${PUID}";
  echo "PGID=${PGID}";
  echo "DOMAIN_NAME=${DOMAIN_NAME}";
  echo "ADMIN_NAME=${ADMIN_NAME}";
  echo "ADMIN_PASSWD=${ADMIN_PASSWD}";
} > .env

# Write version info
cat VERSION > server/VERSION
echo "hash: $(git rev-parse --short HEAD)" >> server/VERSION

export DOCKER_BUILDKIT=0
docker compose down --rmi local --volumes --remove-orphans
docker compose build --no-cache=false
docker compose up -d