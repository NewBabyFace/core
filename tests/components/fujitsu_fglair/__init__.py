"""Tests for the Fujitsu HVAC (based on Ayla IOT) integration."""

from ayla_iot_unofficial.fujitsu_hvac import FujitsuHVAC

from menuai.const import Platform
from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_integration(menuai: menuai, config_entry: MockConfigEntry) -> None:
    """Fixture for setting up the component."""
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()


def entity_id(device: FujitsuHVAC) -> str:
    """Generate the entity id for the given serial."""
    return f"{Platform.CLIMATE}.{device.device_serial_number}"
