"""The tests for Blue Current buttons."""

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.const import ATTR_ENTITY_ID, STATE_UNKNOWN, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import init_integration

from tests.common import MockConfigEntry, snapshot_platform

charge_point_buttons = ["stop_charge_session", "reset", "reboot"]


async def test_buttons_created(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test if all buttons are created."""
    await init_integration(menuai, config_entry, Platform.BUTTON)

    await snapshot_platform(menuai, entity_registry, snapshot, config_entry.entry_id)


@pytest.mark.freeze_time("2023-01-13 12:00:00+00:00")
async def test_charge_point_buttons(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test the underlying charge point buttons."""
    await init_integration(menuai, config_entry, Platform.BUTTON)

    for button in charge_point_buttons:
        state = menuai.states.get(f"button.101_{button}")
        assert state is not None
        assert state.state == STATE_UNKNOWN

        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: f"button.101_{button}"},
            blocking=True,
        )

        state = menuai.states.get(f"button.101_{button}")
        assert state
        assert state.state == "2023-01-13T12:00:00+00:00"
