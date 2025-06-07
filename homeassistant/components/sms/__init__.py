"""The sms component."""

import logging

import voluptuous as vol

from menuai.config_entries import ConfigEntry
from menuai.const import CONF_DEVICE, CONF_NAME, Platform
from menuai.core import DOMAIN as menuai_DOMAIN, menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import config_validation as cv, discovery
from menuai.helpers.issue_registry import (
    IssueSeverity,
    async_create_issue,
    async_delete_issue,
)
from menuai.helpers.typing import ConfigType

from .const import (
    CONF_BAUD_SPEED,
    DEFAULT_BAUD_SPEED,
    DOMAIN,
    GATEWAY,
    menuai_CONFIG,
    NETWORK_COORDINATOR,
    SIGNAL_COORDINATOR,
    SMS_GATEWAY,
)
from .coordinator import NetworkCoordinator, SignalCoordinator
from .gateway import create_sms_gateway

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

SMS_CONFIG_SCHEMA = {vol.Required(CONF_DEVICE): cv.isdevice}

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            vol.All(
                cv.deprecated(CONF_DEVICE),
                SMS_CONFIG_SCHEMA,
            ),
        )
    },
    extra=vol.ALLOW_EXTRA,
)
DEPRECATED_ISSUE_ID = f"deprecated_system_packages_config_flow_integration_{DOMAIN}"


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Configure Gammu state machine."""
    menuai.data.setdefault(DOMAIN, {})
    menuai.data[menuai_CONFIG] = config
    return True


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Configure Gammu state machine."""
    async_create_issue(
        menuai,
        menuai_DOMAIN,
        DEPRECATED_ISSUE_ID,
        breaks_in_ha_version="2025.12.0",
        is_fixable=False,
        issue_domain=DOMAIN,
        severity=IssueSeverity.WARNING,
        translation_key="deprecated_system_packages_config_flow_integration",
        translation_placeholders={
            "integration_title": "SMS notifications via GSM-modem",
        },
    )

    device = entry.data[CONF_DEVICE]
    connection_mode = "at"
    baud_speed = entry.data.get(CONF_BAUD_SPEED, DEFAULT_BAUD_SPEED)
    if baud_speed != DEFAULT_BAUD_SPEED:
        connection_mode += baud_speed
    config = {"Device": device, "Connection": connection_mode}
    _LOGGER.debug("Connecting mode:%s", connection_mode)
    gateway = await create_sms_gateway(config, menuai)
    if not gateway:
        raise ConfigEntryNotReady(f"Cannot find device {device}")

    signal_coordinator = SignalCoordinator(menuai, gateway)
    network_coordinator = NetworkCoordinator(menuai, gateway)

    # Fetch initial data so we have data when entities subscribe
    await signal_coordinator.async_config_entry_first_refresh()
    await network_coordinator.async_config_entry_first_refresh()

    menuai.data.setdefault(DOMAIN, {})
    menuai.data[DOMAIN][SMS_GATEWAY] = {
        SIGNAL_COORDINATOR: signal_coordinator,
        NETWORK_COORDINATOR: network_coordinator,
        GATEWAY: gateway,
    }

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # set up notify platform, no entry support for notify component yet,
    # have to use discovery to load platform.
    menuai.async_create_task(
        discovery.async_load_platform(
            menuai,
            Platform.NOTIFY,
            DOMAIN,
            {CONF_NAME: DOMAIN},
            menuai.data[menuai_CONFIG],
        )
    )
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        gateway = menuai.data[DOMAIN].pop(SMS_GATEWAY)[GATEWAY]
        await gateway.terminate_async()

    if not menuai.config_entries.async_loaded_entries(DOMAIN):
        async_delete_issue(menuai, menuai_DOMAIN, DEPRECATED_ISSUE_ID)

    return unload_ok
