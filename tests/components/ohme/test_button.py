"""Tests for sensors."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from freezegun.api import FrozenDateTimeFactory
from ohme import ChargerStatus
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


async def test_buttons(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test the Ohme buttons."""
    with patch("menuai.components.ohme.PLATFORMS", [Platform.BUTTON]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_button_available(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test that button shows as unavailable when a charge is not pending approval."""
    mock_client.status = ChargerStatus.PENDING_APPROVAL
    await setup_integration(menuai, mock_config_entry)

    state = menuai.states.get("button.ohme_home_pro_approve_charge")
    assert state.state == STATE_UNKNOWN

    mock_client.status = ChargerStatus.PLUGGED_IN
    freezer.tick(timedelta(seconds=60))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get("button.ohme_home_pro_approve_charge")
    assert state.state == STATE_UNAVAILABLE


async def test_button_press(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test the button press action."""
    mock_client.status = ChargerStatus.PENDING_APPROVAL
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {
            ATTR_ENTITY_ID: "button.ohme_home_pro_approve_charge",
        },
        blocking=True,
    )

    assert len(mock_client.async_approve_charge.mock_calls) == 1
