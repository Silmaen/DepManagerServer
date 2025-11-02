# DepManagerServer

Simple repository server for the DepManager tool.

This server aims to host all the packages built for [DepManager](https://github.com/Silmaen/DepManager).

## Docker

### Docker image

Most parts of the work reside in a docker image can can simply be deployed.

`docker pull registry.argawaen.net/servers/depmanager-server`

### Docker compose

It is possible to use the server directly in Docker compose:

```yaml
---
services:
  depmanager-server:
    image: registry.argawaen.net/servers/depmanager-server
    container_name: depmanager-image
  volume:
    - /srv/data/depman:/data       # Persistent volume for package storage, logs, internal database.
  ports:
    - 80:80                        # Port of the web UI.
  environment:
    - TZ:"Europe/Paris"            # The time zone to use in the container.
    - PUID:1000                    # UID used for file writing.
    - PGID:1000                    # GID used for file writing.
    - DOMAIN_NAME:"example.com"    # The domain of this server (mandatory for correct usage).
    - ADMIN_NAME:"admin"           # login of the first admin.
    - ADMIN_PASSWD:"MyBigPassW0rd" # passwd of the first admin.
networks:
  default:
    name: proxyed_servers
```

## Automated docker-compose in the source

A new approach is to use the `docker-compose.yml` file provided in the sources of this project.
You can use it to build the image and run the server in a single command:

```bash
./docker-compose-up.sh
```

To have a fine setup of environment variables, you can simply create of edit the `.env` file in the root of the project.

## Variable details

### TZ

Define he time zone to use in the container. You can directly define your Time zone by setting this variable.

Another trick to use the host's defined times zone is to not set this variable and set
`/etc/timezone:/etc/timezone:ro` as a volume (works only if the host is unix-like).

### PUID, PGID

Defines user and group ids number used in server run. Thus, all files uploaded will have these ids
as owner.

### DOMAIN_NAME

The domain of this server. This parameter is mandatory because used in CSRF resolution of POST REQUESTS.
By default, '127.0.0.1' and 'localhost' are used. It is also important to add the port if not using
standard http or https ports in request.

If you can access to this server by the url `http://10.15.165.12:7856`
then use `DOMAIN_NAME:"10.15.165.12:7856"`.

If you can access to this server by the url
`https://any.pack.home.lan:785` then use `DOMAIN_NAME:"home.lan:785"` or
`DOMAIN_NAME:"pack.home.lan:785"`

### ADMIN_NAME, ADMIN_PASSWD

Define the first admin user login and password. If an admin user already
exists in the database, these parameters are ignored. The only purpose is
to have an admin defined at the first run of a fresh new instance with no
data.

By default, `admin` will be the login and the password.

After the first initialization, it is strongly recommended to change this
admin password!

## Content and capabilities

This server will provide both links to depmanager client as a remote and a web-based
UI to manage the content of the repository.

### General purpose capabilities

This server will allow control of user access: cli pull(& query)/push and UI read/write.
As 'write' in the UI we mean the possibility to delete a package.

### remote capabilities

As remote, the server will not send a deplist to the client (like for ftp server) that contains
the full content of the repository. Instead, it uses a sql table and each client query will pass
through the server.

### UI capabilities

UI can manager users, set database options, location of a file in the repository.

It can also browse through the packages in the server.

## Roadmap
-

- v0.4.0 (in progress)
    - [ ] UI improvements
        - [ ] Search packages
    - [ ] API improvements
        - [ ] search packages
- v0.3.1 (in progress)
    - [ ] Bug fixes
- v0.3.0 (17-06-2025)
    - [X] User management
        - [x] list users
        - [x] create user
        - [x] delete user
        - [x] change user password
    - [x] Basic server with package upload/download
    - [x] User management
    - [x] Package management in the UI
        - [x] list packages
        - [x] delete packages
