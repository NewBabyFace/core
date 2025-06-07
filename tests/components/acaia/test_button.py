"""Tests for the acaia buttons."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from freezegun.api import FrozenDateTimeFactory
from syrupy.assertion import SnapshotAssertion

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.const import (
    ATTR_ENTITY_ID,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform

BUTTONS = (
    "tare",
    "reset_timer",
    "start_stop_timer",
)


async def test_buttons(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_scale: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the acaia buttons."""

    with patch("menuai.components.acaia.PLATFORMS", [Platform.BUTTON]):
        await setup_integration(menuai, mock_config_entry)
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_button_presses(
    menuai: menuai,
    mock_scale: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the acaia button presses."""

    await setup_integration(menuai, mock_config_entry)

    for button in BUTTONS:
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {
                ATTR_ENTITY_ID: f"button.lunar_ddeeff_{button}",
            },
            blocking=True,
        )

        function = getattr(mock_scale, button)
        function.assert_called_once()


async def test_buttons_unavailable_on_disconnected_scale(
    menuai: menuai,
    mock_scale: MagicMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the acaia buttons are unavailable when the scale is disconnected."""

    await setup_integration(menuai, mock_config_entry)

    for button in BUTTONS:
        state = menuai.states.get(f"button.lunar_ddeeff_{button}")
        assert state
        assert state.state == STATE_UNKNOWN

    mock_scale.connected = False
    freezer.tick(timedelta(minutes=10))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    for button in BUTTONS:
        state = menuai.states.get(f"button.lunar_ddeeff_{button}")
        assert state
        assert state.state == STATE_UNAVAILABLE
