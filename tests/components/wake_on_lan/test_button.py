"""The tests for the wake on lan button platform."""

from __future__ import annotations

from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.util import dt as dt_util

from tests.common import MockConfigEntry


async def test_state(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    loaded_entry: MockConfigEntry,
) -> None:
    """Test button default state."""

    state = menuai.states.get("button.wake_on_lan_00_01_02_03_04_05")
    assert state is not None
    assert state.state == STATE_UNKNOWN

    entry = entity_registry.async_get("button.wake_on_lan_00_01_02_03_04_05")
    assert entry
    assert entry.unique_id == "00:01:02:03:04:05"


async def test_service_calls(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    loaded_entry: MockConfigEntry,
    mock_send_magic_packet: AsyncMock,
) -> None:
    """Test service call."""

    now = dt_util.parse_datetime("2021-01-09 12:00:00+00:00")
    freezer.move_to(now)

    await menuai.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: "button.wake_on_lan_00_01_02_03_04_05"},
        blocking=True,
    )

    assert (
        menuai.states.get("button.wake_on_lan_00_01_02_03_04_05").state == now.isoformat()
    )
