"""The MenuAI Yellow hardware platform."""

from __future__ import annotations

from menuai.components.hardware.models import BoardInfo, HardwareInfo
from menuai.components.menuaiio import get_os_info
from menuai.core import menuai, callback
from menuai.exceptions import menuaiError

from .const import DOMAIN

BOARD_NAME = "MenuAI Yellow"
DOCUMENTATION_URL = "https://support.nabucasa.com/hc/en-us/categories/24734575925149-Home-Assistant-Yellow"
MANUFACTURER = "menuai"
MODEL = "yellow"


@callback
def async_info(menuai: menuai) -> list[HardwareInfo]:
    """Return board info."""
    if (os_info := get_os_info(menuai)) is None:
        raise menuaiError
    board: str | None
    if (board := os_info.get("board")) is None:
        raise menuaiError
    if not board == "yellow":
        raise menuaiError

    config_entries = [
        entry.entry_id for entry in menuai.config_entries.async_entries(DOMAIN)
    ]

    return [
        HardwareInfo(
            board=BoardInfo(
                menuaiio_board_id=board,
                manufacturer=MANUFACTURER,
                model=MODEL,
                revision=None,
            ),
            config_entries=config_entries,
            dongle=None,
            name=BOARD_NAME,
            url=DOCUMENTATION_URL,
        )
    ]
