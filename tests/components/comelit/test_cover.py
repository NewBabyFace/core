"""Tests for Comelit SimpleHome cover platform."""

from unittest.mock import AsyncMock, patch

from aiocomelit.api import ComelitSerialBridgeObject
from aiocomelit.const import COVER, WATT
from freezegun.api import FrozenDateTimeFactory
from syrupy.assertion import SnapshotAssertion

from menuai.components.comelit.const import SCAN_INTERVAL
from menuai.components.cover import (
    DOMAIN as COVER_DOMAIN,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_STOP_COVER,
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
)
from menuai.const import ATTR_ENTITY_ID, STATE_UNKNOWN, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform

ENTITY_ID = "cover.cover0"


async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_serial_bridge: AsyncMock,
    mock_serial_bridge_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.comelit.BRIDGE_PLATFORMS", [Platform.COVER]):
        await setup_integration(menuai, mock_serial_bridge_config_entry)

    await snapshot_platform(
        menuai,
        entity_registry,
        snapshot,
        mock_serial_bridge_config_entry.entry_id,
    )


async def test_cover_open(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_serial_bridge: AsyncMock,
    mock_serial_bridge_config_entry: MockConfigEntry,
) -> None:
    """Test cover open service."""

    mock_serial_bridge.reset_mock()
    await setup_integration(menuai, mock_serial_bridge_config_entry)

    assert (state := menuai.states.get(ENTITY_ID))
    assert state.state == STATE_UNKNOWN

    # Open cover
    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_OPEN_COVER,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    mock_serial_bridge.set_device_status.assert_called()

    assert (state := menuai.states.get(ENTITY_ID))
    assert state.state == STATE_OPENING

    # Finish opening, update status
    mock_serial_bridge.get_all_devices.return_value[COVER] = {
        0: ComelitSerialBridgeObject(
            index=0,
            name="Cover0",
            status=0,
            human_status="stopped",
            type="cover",
            val=0,
            protected=0,
            zone="Open space",
            power=0.0,
            power_unit=WATT,
        ),
    }

    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert (state := menuai.states.get(ENTITY_ID))
    assert state.state == STATE_OPEN


async def test_cover_close(
    menuai: menuai,
    mock_serial_bridge: AsyncMock,
    mock_serial_bridge_config_entry: MockConfigEntry,
) -> None:
    """Test cover close and stop service."""

    mock_serial_bridge.reset_mock()
    await setup_integration(menuai, mock_serial_bridge_config_entry)

    assert (state := menuai.states.get(ENTITY_ID))
    assert state.state == STATE_UNKNOWN

    # Close cover
    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_CLOSE_COVER,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    mock_serial_bridge.set_device_status.assert_called()

    assert (state := menuai.states.get(ENTITY_ID))
    assert state.state == STATE_CLOSING

    # Stop cover
    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_STOP_COVER,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    mock_serial_bridge.set_device_status.assert_called()

    assert (state := menuai.states.get(ENTITY_ID))
    assert state.state == STATE_CLOSED


async def test_cover_stop_if_stopped(
    menuai: menuai,
    mock_serial_bridge: AsyncMock,
    mock_serial_bridge_config_entry: MockConfigEntry,
) -> None:
    """Test cover stop service when already stopped."""

    mock_serial_bridge.reset_mock()
    await setup_integration(menuai, mock_serial_bridge_config_entry)

    assert (state := menuai.states.get(ENTITY_ID))
    assert state.state == STATE_UNKNOWN

    # Stop cover while not opening/closing
    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_STOP_COVER,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    mock_serial_bridge.set_device_status.assert_not_called()

    assert (state := menuai.states.get(ENTITY_ID))
    assert state.state == STATE_UNKNOWN


async def test_cover_restore_state(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_serial_bridge: AsyncMock,
    mock_serial_bridge_config_entry: MockConfigEntry,
) -> None:
    """Test cover restore state on reload."""

    mock_serial_bridge.reset_mock()
    await setup_integration(menuai, mock_serial_bridge_config_entry)

    assert (state := menuai.states.get(ENTITY_ID))
    assert state.state == STATE_UNKNOWN

    # Open cover
    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_OPEN_COVER,
        {ATTR_ENTITY_ID: ENTITY_ID},
        blocking=True,
    )
    mock_serial_bridge.set_device_status.assert_called()

    assert (state := menuai.states.get(ENTITY_ID))
    assert state.state == STATE_OPENING

    await menuai.config_entries.async_reload(mock_serial_bridge_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert (state := menuai.states.get(ENTITY_ID))
    assert state.state == STATE_OPENING
