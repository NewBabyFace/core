"""Support for Yale devices."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from aiohttp import ClientResponseError
from yalexs.const import Brand
from yalexs.exceptions import YaleApiError
from yalexs.manager.const import CONF_BRAND
from yalexs.manager.exceptions import CannotConnect, InvalidAuth, RequireValidation
from yalexs.manager.gateway import Config as YaleXSConfig

from menuai.config_entries import ConfigEntry
from menuai.const import EVENT_menuai_STOP
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import config_entry_oauth2_flow, device_registry as dr

from .const import DOMAIN, PLATFORMS
from .data import YaleData
from .gateway import YaleGateway
from .util import async_create_yale_clientsession

type YaleConfigEntry = ConfigEntry[YaleData]


async def async_setup_entry(menuai: menuai, entry: YaleConfigEntry) -> bool:
    """Set up yale from a config entry."""
    session = async_create_yale_clientsession(menuai)
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            menuai, entry
        )
    )
    oauth_session = config_entry_oauth2_flow.OAuth2Session(menuai, entry, implementation)
    yale_gateway = YaleGateway(Path(menuai.config.config_dir), session, oauth_session)
    try:
        await async_setup_yale(menuai, entry, yale_gateway)
    except (RequireValidation, InvalidAuth) as err:
        raise ConfigEntryAuthFailed from err
    except TimeoutError as err:
        raise ConfigEntryNotReady("Timed out connecting to yale api") from err
    except (YaleApiError, ClientResponseError, CannotConnect) as err:
        raise ConfigEntryNotReady from err
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(menuai: menuai, entry: YaleConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_setup_yale(
    menuai: menuai, entry: YaleConfigEntry, yale_gateway: YaleGateway
) -> None:
    """Set up the yale component."""
    config = cast(YaleXSConfig, entry.data)
    await yale_gateway.async_setup({**config, CONF_BRAND: Brand.YALE_GLOBAL})
    await yale_gateway.async_authenticate()
    await yale_gateway.async_refresh_access_token_if_needed()
    data = entry.runtime_data = YaleData(menuai, yale_gateway)
    entry.async_on_unload(
        menuai.bus.async_listen(EVENT_menuai_STOP, data.async_stop)
    )
    entry.async_on_unload(data.async_stop)
    await data.async_setup()


async def async_remove_config_entry_device(
    menuai: menuai, config_entry: YaleConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove yale config entry from a device if its no longer present."""
    return not any(
        identifier
        for identifier in device_entry.identifiers
        if identifier[0] == DOMAIN
        and config_entry.runtime_data.get_device(identifier[1])
    )
