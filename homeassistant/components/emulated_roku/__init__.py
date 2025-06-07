"""Support for Roku API emulation."""

import voluptuous as vol

from menuai import config_entries
from menuai.components.network import async_get_source_ip
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_NAME
from menuai.core import menuai
from menuai.helpers import config_validation as cv
from menuai.helpers.typing import ConfigType

from .binding import EmulatedRoku
from .config_flow import configured_servers
from .const import (
    CONF_ADVERTISE_IP,
    CONF_ADVERTISE_PORT,
    CONF_HOST_IP,
    CONF_LISTEN_PORT,
    CONF_SERVERS,
    CONF_UPNP_BIND_MULTICAST,
    DOMAIN,
)

SERVER_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_LISTEN_PORT): cv.port,
        vol.Optional(CONF_HOST_IP): cv.string,
        vol.Optional(CONF_ADVERTISE_IP): cv.string,
        vol.Optional(CONF_ADVERTISE_PORT): cv.port,
        vol.Optional(CONF_UPNP_BIND_MULTICAST): cv.boolean,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_SERVERS): vol.All(
                    cv.ensure_list, [SERVER_CONFIG_SCHEMA]
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

type EmulatedRokuConfigEntry = ConfigEntry[EmulatedRoku]


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the emulated roku component."""
    if (conf := config.get(DOMAIN)) is None:
        return True

    existing_servers = configured_servers(menuai)

    for entry in conf[CONF_SERVERS]:
        if entry[CONF_NAME] not in existing_servers:
            menuai.async_create_task(
                menuai.config_entries.flow.async_init(
                    DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=entry
                )
            )

    return True


async def async_setup_entry(
    menuai: menuai, entry: EmulatedRokuConfigEntry
) -> bool:
    """Set up an emulated roku server from a config entry."""
    config = entry.data
    name: str = config[CONF_NAME]
    listen_port: int = config[CONF_LISTEN_PORT]
    host_ip: str = config.get(CONF_HOST_IP) or await async_get_source_ip(menuai)
    advertise_ip: str | None = config.get(CONF_ADVERTISE_IP)
    advertise_port: int | None = config.get(CONF_ADVERTISE_PORT)
    upnp_bind_multicast: bool | None = config.get(CONF_UPNP_BIND_MULTICAST)

    server = EmulatedRoku(
        menuai,
        entry.entry_id,
        name,
        host_ip,
        listen_port,
        advertise_ip,
        advertise_port,
        upnp_bind_multicast,
    )
    entry.runtime_data = server
    return await server.setup()


async def async_unload_entry(
    menuai: menuai, entry: EmulatedRokuConfigEntry
) -> bool:
    """Unload a config entry."""
    return await entry.runtime_data.unload()
