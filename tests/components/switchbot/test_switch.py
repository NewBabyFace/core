"""Test the switchbot switches."""

from collections.abc import Callable
from unittest.mock import AsyncMock, patch

import pytest
from switchbot.devices.device import SwitchbotOperationError

from menuai.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai, State
from menuai.exceptions import menuaiError

from . import WOHAND_SERVICE_INFO

from tests.common import MockConfigEntry, mock_restore_cache
from tests.components.bluetooth import inject_bluetooth_service_info


async def test_switchbot_switch_with_restore_state(
    menuai: menuai,
    mock_entry_factory: Callable[[str], MockConfigEntry],
) -> None:
    """Test that Switchbot Switch restores state correctly after reboot."""
    inject_bluetooth_service_info(menuai, WOHAND_SERVICE_INFO)

    entry = mock_entry_factory(sensor_type="bot")
    entity_id = "switch.test_name"

    mock_restore_cache(
        menuai,
        [
            State(
                entity_id,
                STATE_ON,
                {"last_run_success": True},
            )
        ],
    )

    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.switchbot.switch.switchbot.Switchbot.switch_mode",
        return_value=False,
    ):
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        state = menuai.states.get(entity_id)
        assert state.state == STATE_ON
        assert state.attributes["last_run_success"] is True


@pytest.mark.parametrize(
    ("exception", "error_message"),
    [
        (
            SwitchbotOperationError("Operation failed"),
            "An error occurred while performing the action: Operation failed",
        ),
    ],
)
@pytest.mark.parametrize(
    ("service", "mock_method"),
    [
        (SERVICE_TURN_ON, "turn_on"),
        (SERVICE_TURN_OFF, "turn_off"),
    ],
)
async def test_exception_handling_switch(
    menuai: menuai,
    mock_entry_factory: Callable[[str], MockConfigEntry],
    service: str,
    mock_method: str,
    exception: Exception,
    error_message: str,
) -> None:
    """Test exception handling for switch service with exception."""
    inject_bluetooth_service_info(menuai, WOHAND_SERVICE_INFO)

    entry = mock_entry_factory(sensor_type="bot")
    entry.add_to_menuai(menuai)
    entity_id = "switch.test_name"

    patch_target = (
        f"menuai.components.switchbot.switch.switchbot.Switchbot.{mock_method}"
    )

    with patch(patch_target, new=AsyncMock(side_effect=exception)):
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        with pytest.raises(menuaiError, match=error_message):
            await menuai.services.async_call(
                SWITCH_DOMAIN,
                service,
                {ATTR_ENTITY_ID: entity_id},
                blocking=True,
            )
