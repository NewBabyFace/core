"""Tests for the Amazon Devices switch platform."""

from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.amazon_devices.coordinator import SCAN_INTERVAL
from menuai.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration
from .conftest import TEST_SERIAL_NUMBER

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_amazon_devices_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.amazon_devices.PLATFORMS", [Platform.SWITCH]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_switch_dnd(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_amazon_devices_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test switching DND."""
    await setup_integration(menuai, mock_config_entry)

    entity_id = "switch.echo_test_do_not_disturb"

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_OFF

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    assert mock_amazon_devices_client.set_do_not_disturb.call_count == 1

    mock_amazon_devices_client.get_devices_data.return_value[
        TEST_SERIAL_NUMBER
    ].do_not_disturb = True

    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_ON

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    mock_amazon_devices_client.get_devices_data.return_value[
        TEST_SERIAL_NUMBER
    ].do_not_disturb = False

    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert mock_amazon_devices_client.set_do_not_disturb.call_count == 2
    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_OFF


async def test_offline_device(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_amazon_devices_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test offline device handling."""

    entity_id = "switch.echo_test_do_not_disturb"

    mock_amazon_devices_client.get_devices_data.return_value[
        TEST_SERIAL_NUMBER
    ].online = False

    await setup_integration(menuai, mock_config_entry)

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_UNAVAILABLE

    mock_amazon_devices_client.get_devices_data.return_value[
        TEST_SERIAL_NUMBER
    ].online = True

    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert (state := menuai.states.get(entity_id))
    assert state.state != STATE_UNAVAILABLE
