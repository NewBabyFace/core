"""Support for Qwikswitch relays."""

from __future__ import annotations

from menuai.components.switch import SwitchEntity
from menuai.core import menuai
from menuai.helpers.entity_platform import AddEntitiesCallback
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN
from .entity import QSToggleEntity


async def async_setup_platform(
    menuai: menuai,
    _: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Add switches from the main Qwikswitch component."""
    if discovery_info is None:
        return

    qsusb = menuai.data[DOMAIN]
    devs = [QSSwitch(qsid, qsusb) for qsid in discovery_info[DOMAIN]]
    add_entities(devs)


class QSSwitch(QSToggleEntity, SwitchEntity):
    """Switch based on a Qwikswitch relay module."""
