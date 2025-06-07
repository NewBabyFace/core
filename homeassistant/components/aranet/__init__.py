"""The Aranet integration."""

from __future__ import annotations

import logging

from aranet4.client import Aranet4Advertisement

from menuai.components.bluetooth import BluetoothScanningMode
from menuai.components.bluetooth.models import BluetoothServiceInfoBleak
from menuai.components.bluetooth.passive_update_processor import (
    PassiveBluetoothProcessorCoordinator,
)
from menuai.config_entries import ConfigEntry
from menuai.const import Platform
from menuai.core import menuai

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

type AranetConfigEntry = ConfigEntry[
    PassiveBluetoothProcessorCoordinator[Aranet4Advertisement]
]


def _service_info_to_adv(
    service_info: BluetoothServiceInfoBleak,
) -> Aranet4Advertisement:
    return Aranet4Advertisement(service_info.device, service_info.advertisement)


async def async_setup_entry(menuai: menuai, entry: AranetConfigEntry) -> bool:
    """Set up Aranet from a config entry."""

    address = entry.unique_id
    assert address is not None
    coordinator = PassiveBluetoothProcessorCoordinator(
        menuai,
        _LOGGER,
        address=address,
        mode=BluetoothScanningMode.PASSIVE,
        update_method=_service_info_to_adv,
    )
    entry.runtime_data = coordinator
    await menuai.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # only start after all platforms have had a chance to subscribe
    entry.async_on_unload(coordinator.async_start())
    return True


async def async_unload_entry(menuai: menuai, entry: AranetConfigEntry) -> bool:
    """Unload a config entry."""
    return await menuai.config_entries.async_unload_platforms(entry, PLATFORMS)
