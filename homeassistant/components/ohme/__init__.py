"""Set up ohme integration."""

from ohme import ApiException, AuthException, OhmeApiClient

from menuai.const import CONF_EMAIL, CONF_PASSWORD
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from menuai.helpers import config_validation as cv
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .coordinator import (
    OhmeAdvancedSettingsCoordinator,
    OhmeChargeSessionCoordinator,
    OhmeConfigEntry,
    OhmeDeviceInfoCoordinator,
    OhmeRuntimeData,
)
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up Ohme integration."""
    async_setup_services(menuai)

    return True


async def async_setup_entry(menuai: menuai, entry: OhmeConfigEntry) -> bool:
    """Set up Ohme from a config entry."""

    client = OhmeApiClient(
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        session=async_get_clientsession(menuai),
    )

    try:
        await client.async_login()

        if not await client.async_update_device_info():
            raise ConfigEntryNotReady(
                translation_key="device_info_failed", translation_domain=DOMAIN
            )
    except AuthException as e:
        raise ConfigEntryAuthFailed(
            translation_key="auth_failed", translation_domain=DOMAIN
        ) from e
    except ApiException as e:
        raise ConfigEntryNotReady(
            translation_key="api_failed", translation_domain=DOMAIN
        ) from e

    coordinators = (
        OhmeChargeSessionCoordinator(menuai, entry, client),
        OhmeAdvancedSettingsCoordinator(menuai, entry, client),
        OhmeDeviceInfoCoordinator(menuai, entry, client),
    )

    for coordinator in coordinators:
        await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = OhmeRuntimeData(*coordinators)

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: OhmeConfigEntry) -> bool:
    """Unload a config entry."""

    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
