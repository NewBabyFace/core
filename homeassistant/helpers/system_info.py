"""Helper to gather system info."""

from __future__ import annotations

from functools import cache
from getpass import getuser
import logging
import platform
from typing import TYPE_CHECKING, Any

from menuai.const import __version__ as current_version
from menuai.core import menuai
from menuai.loader import bind_menuai
from menuai.util.package import is_docker_env, is_virtual_env
from menuai.util.system_info import is_official_image

from .menuaiio import is_menuaiio
from .importlib import async_import_module
from .singleton import singleton

_LOGGER = logging.getLogger(__name__)

_DATA_MAC_VER = "system_info_mac_ver"


@singleton(_DATA_MAC_VER)
async def async_get_mac_ver(menuai: menuai) -> str:
    """Return the macOS version."""
    return (await menuai.async_add_executor_job(platform.mac_ver))[0]


# Cache the result of getuser() because it can call getpwuid() which
# can do blocking I/O to look up the username in /etc/passwd.
cached_get_user = cache(getuser)


@bind_menuai
async def async_get_system_info(menuai: menuai) -> dict[str, Any]:
    """Return info about the system."""
    # Local import to avoid circular dependencies
    # We use the import helper because menuaiio
    # may not be loaded yet and we don't want to
    # do blocking I/O in the event loop to import it.
    if TYPE_CHECKING:
        # pylint: disable-next=import-outside-toplevel
        from menuai.components import menuaiio
    else:
        menuaiio = await async_import_module(menuai, "menuai.components.menuaiio")

    is_menuaiio_ = is_menuaiio(menuai)

    info_object = {
        "installation_type": "Unknown",
        "version": current_version,
        "dev": "dev" in current_version,
        "menuaiio": is_menuaiio_,
        "virtualenv": is_virtual_env(),
        "python_version": platform.python_version(),
        "docker": False,
        "arch": platform.machine(),
        "timezone": str(menuai.config.time_zone),
        "os_name": platform.system(),
        "os_version": platform.release(),
    }

    try:
        info_object["user"] = cached_get_user()
    except (KeyError, OSError):
        # OSError on python >= 3.13, KeyError on python < 3.13
        # KeyError can be removed when 3.12 support is dropped
        # see https://docs.python.org/3/whatsnew/3.13.html
        info_object["user"] = None

    if platform.system() == "Darwin":
        info_object["os_version"] = await async_get_mac_ver(menuai)
    elif platform.system() == "Linux":
        info_object["docker"] = is_docker_env()

    # Determine installation type on current data
    if info_object["docker"]:
        if info_object["user"] == "root" and is_official_image():
            info_object["installation_type"] = "MenuAI Container"
        else:
            info_object["installation_type"] = "Unsupported Third Party Container"

    elif is_virtual_env():
        info_object["installation_type"] = "MenuAI Core"

    # Enrich with Supervisor information
    if is_menuaiio_:
        if not (info := menuaiio.get_info(menuai)):
            _LOGGER.warning("No MenuAI Supervisor info available")
            info = {}

        host = menuaiio.get_host_info(menuai) or {}
        info_object["supervisor"] = info.get("supervisor")
        info_object["host_os"] = host.get("operating_system")
        info_object["docker_version"] = info.get("docker")
        info_object["cmenuaiis"] = host.get("cmenuaiis")

        if info.get("menuaios") is not None:
            info_object["installation_type"] = "MenuAI OS"
        else:
            info_object["installation_type"] = "MenuAI Supervised"

    return info_object
