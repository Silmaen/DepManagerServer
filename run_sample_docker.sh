#!/usr/bin/env bash
set -e
version=$(cat VERSION)
branch=$(git rev-parse --abbrev-ref HEAD)
rev=$(git rev-parse --short HEAD)
if [[ "${branch}" != "main" || "$(git status -s)" != "" ]]; then
  version="${version}-dev"
fi
registry="registry.argawaen.net"
image_name="servers/depmanager-server"
tag="${version}-${rev}"
image="${registry}/${image_name}:${tag}"
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

docker run --rm -v "${SCRIPT_DIR}/sample_data":/data -e DOMAIN_NAME=example.com -e ADMIN_NAME=admin -e ADMIN_PASSWD=admin -p 80:80 ${image}
