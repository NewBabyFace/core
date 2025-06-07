"""The A. O. Smith integration."""

from __future__ import annotations

from py_aosmith import AOSmithAPIClient

from menuai.const import CONF_EMAIL, CONF_PASSWORD, Platform
from menuai.core import menuai
from menuai.helpers import aiohttp_client, device_registry as dr

from .const import DOMAIN
from .coordinator import (
    AOSmithConfigEntry,
    AOSmithData,
    AOSmithEnergyCoordinator,
    AOSmithStatusCoordinator,
)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.WATER_HEATER]


async def async_setup_entry(menuai: menuai, entry: AOSmithConfigEntry) -> bool:
    """Set up A. O. Smith from a config entry."""
    email = entry.data[CONF_EMAIL]
    password = entry.data[CONF_PASSWORD]

    session = aiohttp_client.async_get_clientsession(menuai)
    client = AOSmithAPIClient(email, password, session)

    status_coordinator = AOSmithStatusCoordinator(menuai, entry, client)
    await status_coordinator.async_config_entry_first_refresh()

    device_registry = dr.async_get(menuai)
    for junction_id, aosmith_device in status_coordinator.data.items():
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, junction_id)},
            manufacturer="A. O. Smith",
            name=aosmith_device.name,
            model=aosmith_device.model,
            serial_number=aosmith_device.serial,
            suggested_area=aosmith_device.install_location,
            sw_version=aosmith_device.status.firmware_version,
        )

    energy_coordinator = AOSmithEnergyCoordinator(
        menuai, entry, client, list(status_coordinator.data)
    )
    await energy_coordinator.async_config_entry_first_refresh()

    entry.runtime_data = AOSmithData(
        client,
        status_coordinator,
        energy_coordinator,
    )

    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(menuai: menuai, entry: AOSmithConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
