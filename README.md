# DepManagerServer

Simple repository server for the DepManager tool.

This server aim to host all the packages built for [DepManager](https://github.com/Silmaen/DepManager).

## Docker

### Docker image
Most parts of the work reside in a docker image can can simply be deployed.

`docker pull registry.argawaen.net/depmanager-server`

### Docker compose

It is possible to use the server directly in Docker compose:

```yaml
version: 3.8
services:
  depmanager-server:
    image: registry.argawaen.net/depmanager-server
    container_name: depmanager-image
  volume:
    - /srv/data/depman:/srv/data
  ports:
    - 80:80
networks:
  default:
    name: proxyed_servers
```

## Content and capabilities

This server will provide both link to depmanager client as a remote and a web-based
UI to manage the content of the repository.

### General purpose capabilities

This server will allow control of user access: cli pull(& query)/push and UI read/write. 
As 'write' in the UI we mean the possibility to delete a package.

### remote capabilities

As remote, the server will not send a deplist to the client (like for ftp server) that contains
the full content of the repository. Instead, it uses a sql table and each client query will pass 
through the server.

### UI capabilities

UI can manager users, set database options, location of file of the repository.

It can also browse through the packages in the server.
