"""Constants for the Hardware integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from menuai.util.menuai_dict import menuaiKey

if TYPE_CHECKING:
    from .models import HardwareData

DOMAIN = "hardware"

DATA_HARDWARE: menuaiKey[HardwareData] = menuaiKey(DOMAIN)
