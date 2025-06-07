"""Kuler Sky lights integration."""

import logging

from menuai.components.bluetooth import async_ble_device_from_address
from menuai.config_entries import SOURCE_INTEGRATION_DISCOVERY, ConfigEntry
from menuai.const import CONF_ADDRESS, Platform
from menuai.core import menuai
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import device_registry as dr

from .const import DOMAIN

PLATFORMS = [Platform.LIGHT]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up Kuler Sky from a config entry."""
    ble_device = async_ble_device_from_address(
        menuai, entry.data[CONF_ADDRESS], connectable=True
    )
    if not ble_device:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="cannot_connect",
        )
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(menuai: menuai, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    # Version 1 was a single entry instance that started a bluetooth discovery
    # thread to add devices. Version 2 has one config entry per device, and
    # supports core bluetooth discovery
    if config_entry.version == 1:
        dev_reg = dr.async_get(menuai)
        devices = dev_reg.devices.get_devices_for_config_entry_id(config_entry.entry_id)

        if len(devices) == 0:
            _LOGGER.error("Unable to migrate; No devices registered")
            return False

        first_device = devices[0]
        domain_identifiers = [i for i in first_device.identifiers if i[0] == DOMAIN]
        address = next(iter(domain_identifiers))[1]
        menuai.config_entries.async_update_entry(
            config_entry,
            title=first_device.name or address,
            data={CONF_ADDRESS: address},
            unique_id=address,
            version=2,
        )

        # Create new config flows for the remaining devices
        for device in devices[1:]:
            domain_identifiers = [i for i in device.identifiers if i[0] == DOMAIN]
            address = next(iter(domain_identifiers))[1]

            menuai.async_create_task(
                menuai.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": SOURCE_INTEGRATION_DISCOVERY},
                    data={CONF_ADDRESS: address},
                )
            )

    _LOGGER.debug("Migration to version %s successful", config_entry.version)

    return True
