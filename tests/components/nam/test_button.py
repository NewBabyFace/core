"""Test button of Nettigo Air Monitor integration."""

from unittest.mock import patch

from aiohttp.client_exceptions import ClientError
from nettigo_air_monitor import ApiError, AuthFailedError
import pytest

from menuai.components.button import (
    DOMAIN as BUTTON_DOMAIN,
    SERVICE_PRESS,
    ButtonDeviceClass,
)
from menuai.components.nam import DOMAIN
from menuai.config_entries import SOURCE_REAUTH, ConfigEntryState
from menuai.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID, STATE_UNKNOWN
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er
from menuai.util import dt as dt_util

from . import init_integration


async def test_button(menuai: menuai, entity_registry: er.EntityRegistry) -> None:
    """Test states of the button."""
    await init_integration(menuai)

    state = menuai.states.get("button.nettigo_air_monitor_restart")
    assert state
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_DEVICE_CLASS) == ButtonDeviceClass.RESTART

    entry = entity_registry.async_get("button.nettigo_air_monitor_restart")
    assert entry
    assert entry.unique_id == "aa:bb:cc:dd:ee:ff-restart"


async def test_button_press(menuai: menuai) -> None:
    """Test button press."""
    await init_integration(menuai)

    now = dt_util.utcnow()
    with (
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_restart"
        ) as mock_restart,
        patch("menuai.core.dt_util.utcnow", return_value=now),
    ):
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.nettigo_air_monitor_restart"},
            blocking=True,
        )
        await menuai.async_block_till_done()

    mock_restart.assert_called_once()

    state = menuai.states.get("button.nettigo_air_monitor_restart")
    assert state
    assert state.state == now.isoformat()


@pytest.mark.parametrize(("exc"), [ApiError("API Error"), ClientError])
async def test_button_press_exc(menuai: menuai, exc: Exception) -> None:
    """Test button press when exception occurs."""
    await init_integration(menuai)

    with (
        patch(
            "menuai.components.nam.NettigoAirMonitor.async_restart",
            side_effect=exc,
        ),
        pytest.raises(
            menuaiError,
            match="An error occurred while calling action for button.nettigo_air_monitor_restart",
        ),
    ):
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.nettigo_air_monitor_restart"},
            blocking=True,
        )


async def test_button_press_auth_error(menuai: menuai) -> None:
    """Test button press when auth error occurs."""
    entry = await init_integration(menuai)

    with patch(
        "menuai.components.nam.NettigoAirMonitor.async_restart",
        side_effect=AuthFailedError("auth error"),
    ):
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: "button.nettigo_air_monitor_restart"},
            blocking=True,
        )

    assert entry.state is ConfigEntryState.LOADED

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1

    flow = flows[0]
    assert flow.get("step_id") == "reauth_confirm"
    assert flow.get("handler") == DOMAIN

    assert "context" in flow
    assert flow["context"].get("source") == SOURCE_REAUTH
    assert flow["context"].get("entry_id") == entry.entry_id
