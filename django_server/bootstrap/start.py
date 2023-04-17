#!/usr/bin/env python3
"""
Main entry point for the docker image
"""
from pathlib import Path
import os

server_config = Path("/server/config")
server_data = Path("/server/data")
server_scripts = Path("/server/scripts")
fallback_run = False

config = {
    "projectname": "depmanagerserver",
    "appname": "app",
    "puid": 1000,
    "pgid": 1000,
    "production": True,
}


def check_env():
    """
    Environment variable check for config info
    :return: True if everything OK.
    """
    for key, val in os.environ.items():
        print(f"{key}={val}")
        for key_config in config:
            if key.lower() == key_config:
                config[key_config] = val
    # verify the config
    result = True
    if config["projectname"] in [None, ""]:
        result = False
        print("ERROR: Empty project Name")
    if config["appname"] in [None, ""]:
        result = False
        print("ERROR: Empty app Name")
    if config["projectname"] == config["appname"]:
        result = False
        print("ERROR: Same app name and project Name")
    if type(config["puid"]) == str:
        try:
            uid = int(config["puid"])
        except:
            uid = 0
            result = False
            print("ERROR: PUID must be integer")
        config["puid"] = uid
    if type(config["pgid"]) == str:
        try:
            gid = int(config["pgid"])
        except:
            gid = 0
            result = False
            print("ERROR: PGID must be integer")
        config["pgid"] = gid
    if type(config["production"]) != bool:
        if type(config["production"]) == str:
            if config["production"].lower() == "false":
                config["production"] = False
            else:
                config["production"] = True
        else:
            config["production"] = True
        # print config
    for key, val in config.items():
        print(str(key) + "=" + str(val))
    return result

def check_user_exist():
    """
    Check and create user & group as required
    """
    import pwd
    import grp
    try:
        group_info = {"name": "users", "id": config["pgid"]}
        user_info = {"name": "docker_user", "id": config["puid"]}

        # check group info and name
        if config["pgid"] in [it.gr_gid for it in grp.getgrall()]:
            # a group with the needed Id already exists -> using its name
            group_info["name"] = str(grp.getgrgid(config["pgid"]).gr_name)
        else:
            if group_info["name"] in [str(it.gr_name) for it in grp.getgrall()]:
                # a group with the default name already exists -> adapt the name
                group_info["name"] += "_docker"
                while group_info["name"] in [str(it.gr_name) for it in grp.getgrall()]:
                    group_info["name"] += "0"
            exec_cmd("addgroup -g " + str(config["pgid"]) + " " + group_info["name"], True)

        # check user info and name
        if config["puid"] in [it.pw_uid for it in pwd.getpwall()]:
            # a user with the needed id already exists, use its name
            user_info["name"] = str(pwd.getpwuid(user_info["id"]).pw_name)
        else:
            if user_info["name"] in [str(it.pw_name) for it in pwd.getpwall()]:
                # a user with the default name already exists -> adapt the name
                user_info["name"] += "_docker"
                while user_info["name"] in [str(it.pw_name) for it in pwd.getpwall()]:
                    user_info["name"] += "0"
            exec_cmd(
                "adduser -D -H -u " + str(config["puid"]) + " -g " + str(
                    config["pgid"]) + " " + user_info["name"], True)
    except Exception as err:
        print("ERROR: unable to change permission: " + str(err))
        return False
    return True


def correct_permission():
    """
    Check and correct the data permission
    """
    import pwd
    import grp
    import os
    try:
        # check permission
        for folder in [server_config, server_scripts, server_data]:
            uid = pwd.getpwnam(folder.owner()).pw_uid
            gid = grp.getgrnam(folder.group()).gr_gid
            if uid != config["puid"] or gid != config["pgid"]:
                for root, dirs, files in os.walk(folder):
                    for sub_folder in dirs:
                        os.chown(os.path.join(root, sub_folder), config["puid"], config["pgid"])
                    for file in files:
                        os.chown(os.path.join(root, file), config["puid"], config["pgid"])
                os.chown(folder, config["puid"], config["pgid"])
                uid = pwd.getpwnam(folder.owner()).pw_uid
                gid = grp.getgrnam(folder.group()).gr_gid
                print("Changing permission to " + str(uid) + ":" + str(gid))
    except Exception as err:
        print("ERROR: unable to change permission: " + str(err))
        return False
    # test execution
    if not exec_cmd("whoami"):
        return False
    return True

def exec_cmd(cmd: str, as_root=False):
    """
    Execute a command in shell with right ID.
    :param cmd: The command to run.
    :param as_root: if must be run as root.
    :return:
    """
    import subprocess
    def demote():
        """
        Change the exec credential.
        """
        def setId():
            """
            Define the user id.
            """
            import os
            os.setgid(config["pgid"])
            os.setuid(config["puid"])

        return setId

    try:
        if as_root:
            p = subprocess.run(str(cmd), shell=True)
        else:
            p = subprocess.run(str(cmd), shell=True, preexec_fn=demote())
        return p.returncode == 0
    except Exception as err:
        print("ERROR Executing " + str(cmd) + " : " + str(err))
    return False

def fall_back():
    """
    If something goes wrong fall back to console
    """
    global fallback_run
    if fallback_run:
        return
    fallback_run = True
    shell = Path("/bin/bash")
    if not shell.exists():
        shell = Path("/bin/sh")
    try:
        exec_cmd(str(shell), True)
    except Exception as err:
        print("ERROR Executing shell fallback : " + str(err))


def initialize_server():
    """
    Server initialization
    """
    import pwd, grp, shutil
    print("Initializing a new server")
    # nginx part
    username = str(pwd.getpwuid(config["puid"]).pw_name)
    groupname = str(grp.getgrgid(config["pgid"]).gr_name)
    if not (server_config / "nginx.conf").exists():
        print("Copy Nginx configuration")
        with open("/bootstrap/nginx.conf") as f:
            lines = f.readlines();
        outlines = []
        for line in lines:
            line = line.replace("%USER%", username)
            line = line.replace("%GROUP%", groupname)
            outlines.append(line)
        with open(server_config / "nginx.conf", "w") as f:
            f.writelines(outlines)
        shutil.copytree("/bootstrap/http.d", server_config / "http.d")
    # check data folders
    (server_data / "static").mkdir(parents=True, exist_ok=True)
    (server_data / "media").mkdir(parents=True, exist_ok=True)
    (server_data / "log").mkdir(parents=True, exist_ok=True)
    # django part
    if not (server_scripts / "manage.py").exists():
        os.chdir(server_scripts)
        if not exec_cmd("django-admin startproject " + config["projectname"] + " ."):
            return False
        return exec_cmd("python manage.py startapp " + config["appname"])
    # default: nothing to do
    return True


def do_migrations():
    """
    Execute the migrations
    """
    print("Checking migrations")
    os.chdir(server_scripts)
    if not exec_cmd("python manage.py makemigrations"):
        return False
    return exec_cmd("python manage.py migrate")


def start_server():
    """
    Start of the Server
    """
    import time
    print("Starting server")
    os.chdir(server_scripts)
    if config["production"]:
        print("Starting Nginx:")
        if not exec_cmd("/usr/sbin/nginx -c /server/config/nginx.conf", True):
            fall_back()
        print("Starting Gunicorn:")
        os.chdir(server_scripts)
        if not (server_scripts / config["projectname"] / "wsgi.py").exists():
            print("ERROR: no project named '" + config["projectname"] + "' is configured.")
            return False
        cmd = "gunicorn " + config["projectname"] + ".wsgi" + \
              " --bind=0.0.0.0:8000" + \
              " --reload" + \
              " --daemon" + \
              " --log-level info" + \
              " --log-file /server/data/log/gunicorn.log"
        if not exec_cmd(cmd, True):
            return False
        print("Server Successfully started")
        while True:
            time.sleep(10)  # wait 10 seconds
            # TODO: polling the file content for reload
    else:
        return exec_cmd("python3 manage.py runserver 0.0.0.0:80")
    return True


def main():
    """
    Main Entrypoint
    """
    print("Django webserver starting")
    if check_env():
        if not check_user_exist():
            fall_back()
            return
        if not initialize_server():
            fall_back()
            return
        if not correct_permission():
            fall_back()
            return
        if not do_migrations():
            fall_back()
            return
        if not start_server():
            fall_back()
            return
    else:
        print("ERROR in environment, fall back to bash")
        fall_back()


if __name__ == "__main__":
    main()
