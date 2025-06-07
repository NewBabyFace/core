"""Tests for TP-Link Omada sensor entities."""

from datetime import timedelta
import json
from unittest.mock import MagicMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion
from tplink_omada_client.definitions import DeviceStatus, DeviceStatusCategory
from tplink_omada_client.devices import OmadaGatewayPortStatus, OmadaListDevice

from menuai.components.tplink_omada.const import DOMAIN
from menuai.components.tplink_omada.coordinator import POLL_DEVICES
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
    load_fixture,
    snapshot_platform,
)

POLL_INTERVAL = timedelta(seconds=POLL_DEVICES)


@pytest.fixture
async def init_integration(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_omada_client: MagicMock,
) -> MockConfigEntry:
    """Set up the TP-Link Omada integration for testing."""
    mock_config_entry.add_to_menuai(menuai)

    with patch("menuai.components.tplink_omada.PLATFORMS", ["sensor"]):
        assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()

    return mock_config_entry


async def test_entities(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the creation of the TP-Link Omada sensor entities."""
    await snapshot_platform(menuai, entity_registry, snapshot, init_integration.entry_id)


async def test_device_specific_status(
    menuai: menuai,
    init_integration: MockConfigEntry,
    mock_omada_site_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a connection status is reported from known detailed status."""
    entity_id = "sensor.test_poe_switch_device_status"
    entity = menuai.states.get(entity_id)
    assert entity is not None
    assert entity.state == "connected"

    _set_test_device_status(
        mock_omada_site_client,
        DeviceStatus.ADOPT_FAILED.value,
        DeviceStatusCategory.CONNECTED.value,
    )

    freezer.tick(POLL_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    entity = menuai.states.get(entity_id)
    assert entity.state == "adopt_failed"


async def test_device_category_status(
    menuai: menuai,
    init_integration: MockConfigEntry,
    mock_omada_site_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a connection status is reported, with fallback to status category."""
    entity_id = "sensor.test_poe_switch_device_status"
    entity = menuai.states.get(entity_id)
    assert entity is not None
    assert entity.state == "connected"

    _set_test_device_status(
        mock_omada_site_client,
        DeviceStatus.PENDING_WIRELESS,
        DeviceStatusCategory.PENDING.value,
    )

    freezer.tick(POLL_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    entity = menuai.states.get(entity_id)
    assert entity.state == "pending"


def _set_test_device_status(
    mock_omada_site_client: MagicMock,
    status: int,
    status_category: int,
) -> OmadaGatewayPortStatus:
    devices_data = json.loads(load_fixture("devices.json", DOMAIN))
    devices_data[1]["status"] = status
    devices_data[1]["statusCategory"] = status_category
    devices = [OmadaListDevice(d) for d in devices_data]

    mock_omada_site_client.get_devices.reset_mock()
    mock_omada_site_client.get_devices.return_value = devices
