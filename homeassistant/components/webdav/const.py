"""Constants for the WebDAV integration."""

from collections.abc import Callable

from menuai.util.menuai_dict import menuaiKey

DOMAIN = "webdav"

DATA_BACKUP_AGENT_LISTENERS: menuaiKey[list[Callable[[], None]]] = menuaiKey(
    f"{DOMAIN}.backup_agent_listeners"
)

CONF_BACKUP_PATH = "backup_path"
