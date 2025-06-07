"""Test the IOmeter binary sensors."""

from datetime import timedelta
from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import STATE_OFF, STATE_ON, STATE_UNKNOWN, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_platform

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_binary_sensors(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_iometer_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test binary sensors."""
    await setup_platform(menuai, mock_config_entry, [Platform.BINARY_SENSOR])

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_connection_status_sensors(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_iometer_client: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test connection status sensor."""
    await setup_platform(menuai, mock_config_entry, [Platform.BINARY_SENSOR])

    assert (
        menuai.states.get(
            "binary_sensor.iometer_1isk0000000000_core_bridge_connection_status"
        ).state
        == STATE_ON
    )

    freezer.tick(delta=timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    mock_iometer_client.get_current_status.return_value.device.core.connection_status = "disconnected"

    freezer.tick(delta=timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert (
        menuai.states.get(
            "binary_sensor.iometer_1isk0000000000_core_bridge_connection_status"
        ).state
        == STATE_OFF
    )


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_attachment_status_sensors(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_iometer_client: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test connection status sensor."""
    await setup_platform(menuai, mock_config_entry, [Platform.BINARY_SENSOR])

    assert (
        menuai.states.get(
            "binary_sensor.iometer_1isk0000000000_core_attachment_status"
        ).state
        == STATE_ON
    )

    freezer.tick(delta=timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    mock_iometer_client.get_current_status.return_value.device.core.attachment_status = "detached"

    freezer.tick(delta=timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert (
        menuai.states.get(
            "binary_sensor.iometer_1isk0000000000_core_attachment_status"
        ).state
        == STATE_OFF
    )


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_attachment_status_sensors_unkown(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_iometer_client: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test connection status sensor."""
    await setup_platform(menuai, mock_config_entry, [Platform.BINARY_SENSOR])

    assert (
        menuai.states.get(
            "binary_sensor.iometer_1isk0000000000_core_attachment_status"
        ).state
        == STATE_ON
    )

    freezer.tick(delta=timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    mock_iometer_client.get_current_status.return_value.device.core.attachment_status = None

    freezer.tick(delta=timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert (
        menuai.states.get(
            "binary_sensor.iometer_1isk0000000000_core_attachment_status"
        ).state
        == STATE_UNKNOWN
    )
