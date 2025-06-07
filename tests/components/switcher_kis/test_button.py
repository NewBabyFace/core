"""Tests for Switcher button platform."""

from unittest.mock import ANY, patch

from aioswitcher.api.messages import SwitcherBaseResponse
from aioswitcher.device import DeviceState, ThermostatSwing
import pytest

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.util import slugify

from . import init_integration
from .consts import DUMMY_THERMOSTAT_DEVICE as DEVICE

BASE_ENTITY_ID = f"{BUTTON_DOMAIN}.{slugify(DEVICE.name)}"
ASSUME_ON_EID = BASE_ENTITY_ID + "_assume_on"
ASSUME_OFF_EID = BASE_ENTITY_ID + "_assume_off"
SWING_ON_EID = BASE_ENTITY_ID + "_vertical_swing_on"
SWING_OFF_EID = BASE_ENTITY_ID + "_vertical_swing_off"


@pytest.mark.parametrize(
    ("entity", "state"),
    [
        (ASSUME_ON_EID, DeviceState.ON),
        (ASSUME_OFF_EID, DeviceState.OFF),
    ],
)
@pytest.mark.parametrize("mock_bridge", [[DEVICE]], indirect=True)
async def test_assume_button(
    menuai: menuai, entity, state, mock_bridge, mock_api
) -> None:
    """Test assume on/off button."""
    await init_integration(menuai)
    assert mock_bridge

    assert menuai.states.get(ASSUME_ON_EID) is not None
    assert menuai.states.get(ASSUME_OFF_EID) is not None
    assert menuai.states.get(SWING_ON_EID) is None
    assert menuai.states.get(SWING_OFF_EID) is None

    with patch(
        "menuai.components.switcher_kis.entity.SwitcherApi.control_breeze_device",
    ) as mock_control_device:
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity},
            blocking=True,
        )
        assert mock_api.call_count == 2
        mock_control_device.assert_called_once_with(ANY, state=state, update_state=True)


@pytest.mark.parametrize(
    ("entity", "swing"),
    [
        (SWING_ON_EID, ThermostatSwing.ON),
        (SWING_OFF_EID, ThermostatSwing.OFF),
    ],
)
@pytest.mark.parametrize("mock_bridge", [[DEVICE]], indirect=True)
async def test_swing_button(
    menuai: menuai,
    entity,
    swing,
    mock_bridge,
    mock_api,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test vertical swing on/off button."""
    monkeypatch.setattr(DEVICE, "remote_id", "ELEC7022")
    await init_integration(menuai)
    assert mock_bridge

    assert menuai.states.get(SWING_ON_EID) is not None
    assert menuai.states.get(SWING_OFF_EID) is not None

    with patch(
        "menuai.components.switcher_kis.entity.SwitcherApi.control_breeze_device",
    ) as mock_control_device:
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity},
            blocking=True,
        )
        assert mock_api.call_count == 2
        mock_control_device.assert_called_once_with(ANY, swing=swing)


@pytest.mark.parametrize("mock_bridge", [[DEVICE]], indirect=True)
async def test_control_device_fail(
    menuai: menuai, mock_bridge, mock_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test control device fail."""
    await init_integration(menuai)
    assert mock_bridge

    assert menuai.states.get(ASSUME_ON_EID) is not None

    # Test exception during set hvac mode
    with patch(
        "menuai.components.switcher_kis.entity.SwitcherApi.control_breeze_device",
        side_effect=RuntimeError("fake error"),
    ) as mock_control_device:
        with pytest.raises(menuaiError):
            await menuai.services.async_call(
                BUTTON_DOMAIN,
                SERVICE_PRESS,
                {ATTR_ENTITY_ID: ASSUME_ON_EID},
                blocking=True,
            )

        assert mock_api.call_count == 2
        mock_control_device.assert_called_once_with(
            ANY, state=DeviceState.ON, update_state=True
        )

        state = menuai.states.get(ASSUME_ON_EID)
        assert state.state == STATE_UNAVAILABLE

    # Make device available again
    mock_bridge.mock_callbacks([DEVICE])
    await menuai.async_block_till_done()

    assert menuai.states.get(ASSUME_ON_EID) is not None

    # Test error response during turn on
    with patch(
        "menuai.components.switcher_kis.entity.SwitcherApi.control_breeze_device",
        return_value=SwitcherBaseResponse(None),
    ) as mock_control_device:
        with pytest.raises(menuaiError):
            await menuai.services.async_call(
                BUTTON_DOMAIN,
                SERVICE_PRESS,
                {ATTR_ENTITY_ID: ASSUME_ON_EID},
                blocking=True,
            )

        assert mock_api.call_count == 4
        mock_control_device.assert_called_once_with(
            ANY, state=DeviceState.ON, update_state=True
        )

        state = menuai.states.get(ASSUME_ON_EID)
        assert state.state == STATE_UNAVAILABLE
