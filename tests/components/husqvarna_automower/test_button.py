"""Tests for button platform."""

import datetime
from unittest.mock import AsyncMock, patch

from aioautomower.exceptions import ApiError
from aioautomower.model import MowerAttributes
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.components.husqvarna_automower.coordinator import SCAN_INTERVAL
from menuai.const import (
    ATTR_ENTITY_ID,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    Platform,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from . import setup_integration
from .const import TEST_MOWER_ID

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


@pytest.mark.freeze_time(datetime.datetime(2023, 6, 5, tzinfo=datetime.UTC))
async def test_button_states_and_commands(
    menuai: menuai,
    mock_automower_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    values: dict[str, MowerAttributes],
) -> None:
    """Test error confirm button command."""
    entity_id = "button.test_mower_1_confirm_error"
    await setup_integration(menuai, mock_config_entry)
    state = menuai.states.get(entity_id)
    assert state.name == "Test Mower 1 Confirm error"
    assert state.state == STATE_UNAVAILABLE

    values[TEST_MOWER_ID].mower.is_error_confirmable = None
    mock_automower_client.get_status.return_value = values
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_UNAVAILABLE

    values[TEST_MOWER_ID].mower.is_error_confirmable = True
    mock_automower_client.get_status.return_value = values
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == STATE_UNKNOWN

    await menuai.services.async_call(
        domain="button",
        service=SERVICE_PRESS,
        target={ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_automower_client.commands.error_confirm.assert_called_once_with(TEST_MOWER_ID)
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == "2023-06-05T00:16:00+00:00"
    mock_automower_client.commands.error_confirm.side_effect = ApiError("Test error")
    with pytest.raises(
        menuaiError,
        match="Failed to send command: Test error",
    ):
        await menuai.services.async_call(
            domain="button",
            service=SERVICE_PRESS,
            target={ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )


@pytest.mark.freeze_time(datetime.datetime(2024, 2, 29, 11, tzinfo=datetime.UTC))
async def test_sync_clock(
    menuai: menuai,
    mock_automower_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    values: dict[str, MowerAttributes],
) -> None:
    """Test sync clock button command."""
    entity_id = "button.test_mower_1_sync_clock"
    await setup_integration(menuai, mock_config_entry)
    state = menuai.states.get(entity_id)
    assert state.name == "Test Mower 1 Sync clock"

    mock_automower_client.get_status.return_value = values

    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_automower_client.commands.set_datetime.assert_called_once_with(TEST_MOWER_ID)
    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.state == "2024-02-29T11:00:00+00:00"
    mock_automower_client.commands.set_datetime.side_effect = ApiError("Test error")
    with pytest.raises(
        menuaiError,
        match="Failed to send command: Test error",
    ):
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_button_snapshot(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_automower_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Snapshot tests of the button entities."""
    with patch(
        "menuai.components.husqvarna_automower.PLATFORMS",
        [Platform.BUTTON],
    ):
        await setup_integration(menuai, mock_config_entry)
        await snapshot_platform(
            menuai, entity_registry, snapshot, mock_config_entry.entry_id
        )
