from collections import deque
from functools import partial
from itertools import imap
from sys import version

if version[0] == "2":
    from itertools import imap as map

from fabric.api import run
from fabric.context_managers import shell_env, cd
from fabric.contrib.files import exists
from fabric.operations import sudo, _run_command
from offregister_fab_utils.apt import apt_depends
from offregister_fab_utils.python import pip_depends
from six import string_types


def install_venv0(python3=False, venv=None, *args, **kwargs):
    run_cmd = partial(_run_command, sudo=kwargs.get("use_sudo", False))

    ensure_pip_version = lambda: kwargs.get("pip_version") and sudo(
        "pip install pip ".format(
            "== {}".format(kwargs["pip_version"] if "pip_version" in kwargs else "-U")
        )
    )

    venv_dir = kwargs.get("VENV_DIR", run("echo $HOME/venvs", quiet=True))
    venv = venv or "{venv_dir}/{venv_name}".format(
        venv_dir=venv_dir, venv_name=kwargs.get("VENV_NAME", "venv")
    )

    if exists("{}/bin/python".format(venv)):
        return
    elif python3:
        apt_depends("python3-dev", "python3-pip", "python3-wheel", "python3-venv")
    else:
        apt_depends(
            "python-dev", "python-pip", "python-wheel", "python2.7", "python2.7-dev"
        )  # 'python-apt'
        sudo("pip install virtualenv")

    virtual_env_bin = "{venv}/bin".format(venv=venv)
    if not exists(virtual_env_bin):
        sudo('mkdir -p "{venv_dir}"'.format(venv_dir=venv_dir), shell_escape=False)
        if python3:
            sudo('python3 -m venv "{venv}"'.format(venv=venv), shell_escape=False)
        else:
            sudo('virtualenv "{venv}"'.format(venv=venv), shell_escape=False)

    if not exists(virtual_env_bin):
        raise ReferenceError("Virtualenv does not exist")

    if not kwargs.get("use_sudo"):
        user_group = run("echo $(id -un):$(id -gn)", quiet=True)
        sudo(
            "chown -R {user_group} {venv} $HOME/.cache".format(
                user_group=user_group, venv=venv
            )
        )

    with shell_env(VIRTUAL_ENV=venv, PATH="{}/bin:$PATH".format(venv)):
        ensure_pip_version()
        run_cmd("pip install -U wheel setuptools")
        return "Installed: {} {}".format(
            run_cmd("pip --version; python --version"),
            pip_depends(
                "{}/bin/python".format(venv),
                kwargs.get("use_sudo", False),
                kwargs.get("PACKAGES", tuple()),
            ),
        )


def run_inside1(package_directory=None, venv=None, requirements=True, *args, **kwargs):
    if package_directory is None or not exists(package_directory):
        return
    run_cmd = partial(_run_command, sudo=kwargs.get("use_sudo"))
    venv = venv or "{venv_dir}/{venv_name}".format(
        venv_dir=kwargs.get("VENV_DIR", run("echo $HOME/venvs", quiet=True)),
        venv_name=kwargs.get("VENV_NAME", "venv"),
    )
    with shell_env(VIRTUAL_ENV=venv, PATH="{}/bin:$PATH".format(venv)), cd(
        package_directory
    ):
        requirements = "requirements.txt" if requirements is True else requirements
        if requirements:
            if isinstance(requirements, list):
                deque(
                    map(
                        lambda req: run_cmd('pip install -r "{}"'.format(req)),
                        requirements,
                    ),
                    maxlen=0,
                )
            else:
                run_cmd('pip install -r "{}"'.format(requirements))

        return run_cmd('pip uninstall -y "${PWD##*/}"; pip install .;')


def run_within_venv2(venv=None, venv_execute=None, *args, **kwargs):
    if venv_execute is None:
        venv_execute = kwargs.get("VENV_EXECUTE")
        if venv_execute is None:
            return

    run_cmd = partial(_run_command, sudo=kwargs.get("use_sudo"))
    venv = venv or "{venv_dir}/{venv_name}".format(
        venv_dir=kwargs.get("VENV_DIR", run("echo $HOME/venvs", quiet=True)),
        venv_name=kwargs.get("VENV_NAME", "venv"),
    )
    with shell_env(VIRTUAL_ENV=venv, PATH="{}/bin:$PATH".format(venv)):
        if isinstance(venv_execute, string_types):
            return run_cmd(venv_execute)

        return tuple(imap(run_cmd, venv_execute))
