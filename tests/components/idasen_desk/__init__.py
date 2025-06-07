"""Tests for the IKEA Idasen Desk integration."""

from menuai.components.bluetooth import BluetoothServiceInfoBleak
from menuai.components.idasen_desk.const import DOMAIN
from menuai.const import CONF_ADDRESS
from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.bluetooth import generate_advertisement_data, generate_ble_device

IDASEN_DISCOVERY_INFO = BluetoothServiceInfoBleak(
    name="Desk 1234",
    address="AA:BB:CC:DD:EE:FF",
    rssi=-60,
    manufacturer_data={},
    service_uuids=["99fa0001-338a-1024-8a49-009c0215f78a"],
    service_data={},
    source="local",
    device=generate_ble_device(address="AA:BB:CC:DD:EE:FF", name="Desk 1234"),
    advertisement=generate_advertisement_data(),
    time=0,
    connectable=True,
    tx_power=-127,
)

NOT_IDASEN_DISCOVERY_INFO = BluetoothServiceInfoBleak(
    name="Not Desk",
    address="AA:BB:CC:DD:EE:FF",
    rssi=-60,
    manufacturer_data={},
    service_uuids=[],
    service_data={},
    source="local",
    device=generate_ble_device(address="AA:BB:CC:DD:EE:FF", name="Not Desk"),
    advertisement=generate_advertisement_data(),
    time=0,
    connectable=True,
    tx_power=-127,
)


async def init_integration(menuai: menuai) -> MockConfigEntry:
    """Set up the IKEA Idasen Desk integration in MenuAI."""
    entry = MockConfigEntry(
        title="Test",
        domain=DOMAIN,
        data={CONF_ADDRESS: "AA:BB:CC:DD:EE:FF"},
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    return entry
