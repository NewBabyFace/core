"""The Ondilo ICO integration."""

from menuai.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import config_entry_oauth2_flow, config_validation as cv
from menuai.helpers.typing import ConfigType

from .api import OndiloClient
from .const import DOMAIN, OAUTH2_CLIENT_ID, OAUTH2_CLIENT_SECRET
from .coordinator import OndiloIcoPoolsCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.SENSOR]


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up the Ondilo ICO integration."""
    # Import the default client credential.
    await async_import_client_credential(
        menuai,
        DOMAIN,
        ClientCredential(OAUTH2_CLIENT_ID, OAUTH2_CLIENT_SECRET, name="Ondilo ICO"),
    )

    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Ondilo ICO from a config entry."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            menuai, entry
        )
    )

    coordinator = OndiloIcoPoolsCoordinator(
        menuai, entry, OndiloClient(menuai, entry, implementation)
    )

    await coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        menuai.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
