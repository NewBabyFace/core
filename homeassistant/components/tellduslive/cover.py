"""Support for Tellstick covers using Tellstick Net."""

from typing import Any

from menuai.components import cover
from menuai.components.cover import CoverEntity
from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.helpers.dispatcher import async_dispatcher_connect
from menuai.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import TelldusLiveClient
from .const import DOMAIN, TELLDUS_DISCOVERY_NEW
from .entity import TelldusLiveEntity


async def async_setup_entry(
    menuai: menuai,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up tellduslive sensors dynamically."""

    async def async_discover_cover(device_id):
        """Discover and add a discovered sensor."""
        client: TelldusLiveClient = menuai.data[DOMAIN]
        async_add_entities([TelldusLiveCover(client, device_id)])

    async_dispatcher_connect(
        menuai,
        TELLDUS_DISCOVERY_NEW.format(cover.DOMAIN, DOMAIN),
        async_discover_cover,
    )


class TelldusLiveCover(TelldusLiveEntity, CoverEntity):
    """Representation of a cover."""

    _attr_name = None

    @property
    def is_closed(self) -> bool:
        """Return the current position of the cover."""
        return self.device.is_down

    def close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        self.device.down()
        self.schedule_update_ha_state()

    def open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        self.device.up()
        self.schedule_update_ha_state()

    def stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        self.device.stop()
        self.schedule_update_ha_state()
