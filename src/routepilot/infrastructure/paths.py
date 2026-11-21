"""Filesystem locations used by RoutePilot (XDG aware, pkexec aware)."""

import os
import pwd
from pathlib import Path

APP_DIR_NAME = "routepilot"
SYSTEM_RUNTIME_DIR = Path("/run/routepilot")


def invoking_user_home() -> Path:
    """Home of the desktop user, even when running as root through pkexec or sudo."""
    for variable in ("PKEXEC_UID", "SUDO_UID"):
        uid = os.environ.get(variable)
        if uid and uid.isdigit():
            try:
                return Path(pwd.getpwuid(int(uid)).pw_dir)
            except KeyError:
                break
    return Path.home()


def config_dir() -> Path:
    """``$XDG_CONFIG_HOME/routepilot`` (``~/.config/routepilot`` by default)."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg and not _elevated():
        return Path(xdg) / APP_DIR_NAME
    return invoking_user_home() / ".config" / APP_DIR_NAME


def policy_file() -> Path:
    return config_dir() / "policy.json"


def settings_file() -> Path:
    return config_dir() / "settings.json"


def runtime_dir() -> Path:
    """Where the apply journal lives; tmpfs, so it vanishes with kernel state on reboot."""
    if os.geteuid() == 0:
        return SYSTEM_RUNTIME_DIR
    return Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / APP_DIR_NAME


def _elevated() -> bool:
    return os.geteuid() == 0 and ("PKEXEC_UID" in os.environ or "SUDO_UID" in os.environ)
