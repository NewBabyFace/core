"""Support for Qwikswitch Relays and Dimmers."""

from __future__ import annotations

from menuai.components.light import ColorMode, LightEntity
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
    """Add lights from the main Qwikswitch component."""
    if discovery_info is None:
        return

    qsusb = menuai.data[DOMAIN]
    devs = [QSLight(qsid, qsusb) for qsid in discovery_info[DOMAIN]]
    add_entities(devs)


class QSLight(QSToggleEntity, LightEntity):
    """Light based on a Qwikswitch relay/dimmer module."""

    @property
    def brightness(self):
        """Return the brightness of this light (0-255)."""
        return self.device.value if self.device.is_dimmer else None

    @property
    def color_mode(self) -> ColorMode:
        """Return the color mode of the light."""
        return ColorMode.BRIGHTNESS if self.device.is_dimmer else ColorMode.ONOFF

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Flag supported color modes."""
        return {self.color_mode}
