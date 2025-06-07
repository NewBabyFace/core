"""The soundtouch component."""

import logging

from libsoundtouch import soundtouch_device
from libsoundtouch.device import SoundTouchDevice
import voluptuous as vol

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_HOST, Platform
from menuai.core import menuai, ServiceCall
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    SERVICE_ADD_ZONE_SLAVE,
    SERVICE_CREATE_ZONE,
    SERVICE_PLAY_EVERYWHERE,
    SERVICE_REMOVE_ZONE_SLAVE,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_PLAY_EVERYWHERE_SCHEMA = vol.Schema({vol.Required("master"): cv.entity_id})
SERVICE_CREATE_ZONE_SCHEMA = vol.Schema(
    {
        vol.Required("master"): cv.entity_id,
        vol.Required("slaves"): cv.entity_ids,
    }
)
SERVICE_ADD_ZONE_SCHEMA = vol.Schema(
    {
        vol.Required("master"): cv.entity_id,
        vol.Required("slaves"): cv.entity_ids,
    }
)
SERVICE_REMOVE_ZONE_SCHEMA = vol.Schema(
    {
        vol.Required("master"): cv.entity_id,
        vol.Required("slaves"): cv.entity_ids,
    }
)

PLATFORMS = [Platform.MEDIA_PLAYER]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


class SoundTouchData:
    """SoundTouch data stored in the MenuAI data object."""

    def __init__(self, device: SoundTouchDevice) -> None:
        """Initialize the SoundTouch data object for a device."""
        self.device = device
        self.media_player = None


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up Bose SoundTouch component."""

    async def service_handle(service: ServiceCall) -> None:
        """Handle the applying of a service."""
        master_id = service.data.get("master")
        slaves_ids = service.data.get("slaves")
        slaves = []
        if slaves_ids:
            slaves = [
                data.media_player
                for data in menuai.data[DOMAIN].values()
                if data.media_player.entity_id in slaves_ids
            ]

        master = next(
            iter(
                [
                    data.media_player
                    for data in menuai.data[DOMAIN].values()
                    if data.media_player.entity_id == master_id
                ]
            ),
            None,
        )

        if master is None:
            _LOGGER.warning("Unable to find master with entity_id: %s", str(master_id))
            return

        if service.service == SERVICE_PLAY_EVERYWHERE:
            slaves = [
                data.media_player
                for data in menuai.data[DOMAIN].values()
                if data.media_player.entity_id != master_id
            ]
            await menuai.async_add_executor_job(master.create_zone, slaves)
        elif service.service == SERVICE_CREATE_ZONE:
            await menuai.async_add_executor_job(master.create_zone, slaves)
        elif service.service == SERVICE_REMOVE_ZONE_SLAVE:
            await menuai.async_add_executor_job(master.remove_zone_slave, slaves)
        elif service.service == SERVICE_ADD_ZONE_SLAVE:
            await menuai.async_add_executor_job(master.add_zone_slave, slaves)

    menuai.services.async_register(
        DOMAIN,
        SERVICE_PLAY_EVERYWHERE,
        service_handle,
        schema=SERVICE_PLAY_EVERYWHERE_SCHEMA,
    )
    menuai.services.async_register(
        DOMAIN,
        SERVICE_CREATE_ZONE,
        service_handle,
        schema=SERVICE_CREATE_ZONE_SCHEMA,
    )
    menuai.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_ZONE_SLAVE,
        service_handle,
        schema=SERVICE_REMOVE_ZONE_SCHEMA,
    )
    menuai.services.async_register(
        DOMAIN,
        SERVICE_ADD_ZONE_SLAVE,
        service_handle,
        schema=SERVICE_ADD_ZONE_SCHEMA,
    )

    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Bose SoundTouch from a config entry."""
    device = await menuai.async_add_executor_job(soundtouch_device, entry.data[CONF_HOST])

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = SoundTouchData(device)

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await menuai.config_entries.async_unload_platforms(entry, PLATFORMS):
        del menuai.data[DOMAIN][entry.entry_id]
    return unload_ok
