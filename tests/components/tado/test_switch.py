"""The sensor tests for the tado platform."""

from unittest.mock import patch

import pytest

from menuai.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.const import ATTR_ENTITY_ID, STATE_OFF
from menuai.core import menuai

from .util import async_init_integration

CHILD_LOCK_SWITCH_ENTITY = "switch.baseboard_heater_child_lock"


async def test_child_lock(menuai: menuai) -> None:
    """Test creation of child lock entity."""

    await async_init_integration(menuai)
    state = menuai.states.get(CHILD_LOCK_SWITCH_ENTITY)
    assert state.state == STATE_OFF


@pytest.mark.parametrize(
    ("method", "expected"), [(SERVICE_TURN_ON, True), (SERVICE_TURN_OFF, False)]
)
async def test_set_child_lock(menuai: menuai, method, expected) -> None:
    """Test enable child lock on switch."""

    await async_init_integration(menuai)

    with patch(
        "menuai.components.tado.PyTado.interface.api.Tado.set_child_lock"
    ) as mock_set_state:
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            method,
            {ATTR_ENTITY_ID: CHILD_LOCK_SWITCH_ENTITY},
            blocking=True,
        )

    mock_set_state.assert_called_once()
    assert mock_set_state.call_args[0][1] is expected
