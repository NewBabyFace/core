"""Constants for the Kitchen Sink integration."""

from __future__ import annotations

from collections.abc import Callable

from menuai.util.menuai_dict import menuaiKey

DOMAIN = "kitchen_sink"
DATA_BACKUP_AGENT_LISTENERS: menuaiKey[list[Callable[[], None]]] = menuaiKey(
    f"{DOMAIN}.backup_agent_listeners"
)
