"""Test the Switcher climate platform."""

from unittest.mock import ANY, patch

from aioswitcher.api.messages import SwitcherBaseResponse
from aioswitcher.device import (
    DeviceState,
    ThermostatFanLevel,
    ThermostatMode,
    ThermostatSwing,
)
import pytest

from menuai.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    ATTR_SWING_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_SWING_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACMode,
)
from menuai.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.exceptions import menuaiError, ServiceValidationError
from menuai.util import slugify

from . import init_integration
from .consts import DUMMY_THERMOSTAT_DEVICE as DEVICE

ENTITY_ID = f"{CLIMATE_DOMAIN}.{slugify(DEVICE.name)}"


@pytest.mark.parametrize("mock_bridge", [[DEVICE]], indirect=True)
async def test_climate_hvac_mode(
    menuai: menuai, mock_bridge, mock_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test climate hvac mode service."""
    await init_integration(menuai)
    assert mock_bridge

    # Test initial hvac mode - cool
    state = menuai.states.get(ENTITY_ID)
    assert state.state == HVACMode.COOL

    # Test set hvac mode heat
    with patch(
        "menuai.components.switcher_kis.entity.SwitcherApi.control_breeze_device",
    ) as mock_control_device:
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_HVAC_MODE: HVACMode.HEAT},
            blocking=True,
        )

        monkeypatch.setattr(DEVICE, "mode", ThermostatMode.HEAT)
        mock_bridge.mock_callbacks([DEVICE])
        await menuai.async_block_till_done()

        assert mock_api.call_count == 2
        mock_control_device.assert_called_once_with(
            ANY, state=DeviceState.ON, mode=ThermostatMode.HEAT
        )
        state = menuai.states.get(ENTITY_ID)
        assert state.state == HVACMode.HEAT

    # Test set hvac mode off
    with patch(
        "menuai.components.switcher_kis.entity.SwitcherApi.control_breeze_device",
    ) as mock_control_device:
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_HVAC_MODE: HVACMode.OFF},
            blocking=True,
        )

        monkeypatch.setattr(DEVICE, "device_state", DeviceState.OFF)
        mock_bridge.mock_callbacks([DEVICE])
        await menuai.async_block_till_done()

        assert mock_api.call_count == 4
        mock_control_device.assert_called_once_with(ANY, state=DeviceState.OFF)
        state = menuai.states.get(ENTITY_ID)
        assert state.state == HVACMode.OFF


@pytest.mark.parametrize("mock_bridge", [[DEVICE]], indirect=True)
async def test_climate_temperature(
    menuai: menuai, mock_bridge, mock_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test climate temperature service."""
    await init_integration(menuai)
    assert mock_bridge

    monkeypatch.setattr(DEVICE, "mode", ThermostatMode.HEAT)
    mock_bridge.mock_callbacks([DEVICE])
    await menuai.async_block_till_done()

    # Test initial target temperature
    state = menuai.states.get(ENTITY_ID)
    assert state.attributes["temperature"] == 23

    # Test set target temperature
    with patch(
        "menuai.components.switcher_kis.entity.SwitcherApi.control_breeze_device",
    ) as mock_control_device:
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_TEMPERATURE: 22},
            blocking=True,
        )

        monkeypatch.setattr(DEVICE, "target_temperature", 22)
        mock_bridge.mock_callbacks([DEVICE])
        await menuai.async_block_till_done()

        assert mock_api.call_count == 2
        mock_control_device.assert_called_once_with(ANY, target_temp=22)
        state = menuai.states.get(ENTITY_ID)
        assert state.attributes["temperature"] == 22

    # Test set target temperature - incorrect params
    with patch(
        "menuai.components.switcher_kis.entity.SwitcherApi.control_breeze_device",
    ) as mock_control_device:
        with pytest.raises(ServiceValidationError):
            await menuai.services.async_call(
                CLIMATE_DOMAIN,
                SERVICE_SET_TEMPERATURE,
                {
                    ATTR_ENTITY_ID: ENTITY_ID,
                    ATTR_TARGET_TEMP_LOW: 20,
                    ATTR_TARGET_TEMP_HIGH: 30,
                },
                blocking=True,
            )

        assert mock_api.call_count == 2
        mock_control_device.assert_not_called()


@pytest.mark.parametrize("mock_bridge", [[DEVICE]], indirect=True)
async def test_climate_fan_level(
    menuai: menuai, mock_bridge, mock_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test climate fan level service."""
    await init_integration(menuai)
    assert mock_bridge

    # Test initial fan level - low
    state = menuai.states.get(ENTITY_ID)
    assert state.attributes["fan_mode"] == "low"

    # Test set fan level to high
    with patch(
        "menuai.components.switcher_kis.entity.SwitcherApi.control_breeze_device",
    ) as mock_control_device:
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_FAN_MODE,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_FAN_MODE: "high"},
            blocking=True,
        )

        monkeypatch.setattr(DEVICE, "fan_level", ThermostatFanLevel.HIGH)
        mock_bridge.mock_callbacks([DEVICE])
        await menuai.async_block_till_done()

        assert mock_api.call_count == 2
        mock_control_device.assert_called_once_with(
            ANY, fan_level=ThermostatFanLevel.HIGH
        )
        state = menuai.states.get(ENTITY_ID)
        assert state.attributes["fan_mode"] == "high"


@pytest.mark.parametrize("mock_bridge", [[DEVICE]], indirect=True)
async def test_climate_swing(
    menuai: menuai, mock_bridge, mock_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test climate swing service."""
    await init_integration(menuai)
    assert mock_bridge

    # Test initial swing mode
    state = menuai.states.get(ENTITY_ID)
    assert state.attributes["swing_mode"] == "off"

    # Test set swing mode on
    with patch(
        "menuai.components.switcher_kis.entity.SwitcherApi.control_breeze_device",
    ) as mock_control_device:
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_SWING_MODE,
            {
                ATTR_ENTITY_ID: ENTITY_ID,
                ATTR_SWING_MODE: "vertical",
            },
            blocking=True,
        )

        monkeypatch.setattr(DEVICE, "swing", ThermostatSwing.ON)
        mock_bridge.mock_callbacks([DEVICE])
        await menuai.async_block_till_done()

        assert mock_api.call_count == 2
        mock_control_device.assert_called_once_with(ANY, swing=ThermostatSwing.ON)
        state = menuai.states.get(ENTITY_ID)
        assert state.attributes["swing_mode"] == "vertical"

    # Test set swing mode off
    with patch(
        "menuai.components.switcher_kis.entity.SwitcherApi.control_breeze_device",
    ) as mock_control_device:
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_SWING_MODE,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_SWING_MODE: "off"},
            blocking=True,
        )

        monkeypatch.setattr(DEVICE, "swing", ThermostatSwing.OFF)
        mock_bridge.mock_callbacks([DEVICE])
        await menuai.async_block_till_done()

        assert mock_api.call_count == 4
        mock_control_device.assert_called_once_with(ANY, swing=ThermostatSwing.OFF)
        state = menuai.states.get(ENTITY_ID)
        assert state.attributes["swing_mode"] == "off"


@pytest.mark.parametrize("mock_bridge", [[DEVICE]], indirect=True)
async def test_control_device_fail(menuai: menuai, mock_bridge, mock_api) -> None:
    """Test control device fail."""
    await init_integration(menuai)
    assert mock_bridge

    # Test initial hvac mode - cool
    state = menuai.states.get(ENTITY_ID)
    assert state.state == HVACMode.COOL

    # Test exception during set hvac mode
    with patch(
        "menuai.components.switcher_kis.entity.SwitcherApi.control_breeze_device",
        side_effect=RuntimeError("fake error"),
    ) as mock_control_device:
        with pytest.raises(menuaiError):
            await menuai.services.async_call(
                CLIMATE_DOMAIN,
                SERVICE_SET_HVAC_MODE,
                {ATTR_ENTITY_ID: ENTITY_ID, ATTR_HVAC_MODE: HVACMode.HEAT},
                blocking=True,
            )

        assert mock_api.call_count == 2
        mock_control_device.assert_called_once_with(
            ANY, state=DeviceState.ON, mode=ThermostatMode.HEAT
        )
        state = menuai.states.get(ENTITY_ID)
        assert state.state == STATE_UNAVAILABLE

    # Make device available again
    mock_bridge.mock_callbacks([DEVICE])
    await menuai.async_block_till_done()

    state = menuai.states.get(ENTITY_ID)
    assert state.state == HVACMode.COOL

    # Test error response during turn on
    with patch(
        "menuai.components.switcher_kis.entity.SwitcherApi.control_breeze_device",
        return_value=SwitcherBaseResponse(None),
    ) as mock_control_device:
        with pytest.raises(menuaiError):
            await menuai.services.async_call(
                CLIMATE_DOMAIN,
                SERVICE_SET_HVAC_MODE,
                {ATTR_ENTITY_ID: ENTITY_ID, ATTR_HVAC_MODE: HVACMode.HEAT},
                blocking=True,
            )

        assert mock_api.call_count == 4
        mock_control_device.assert_called_once_with(
            ANY, state=DeviceState.ON, mode=ThermostatMode.HEAT
        )
        state = menuai.states.get(ENTITY_ID)
        assert state.state == STATE_UNAVAILABLE


@pytest.mark.parametrize("mock_bridge", [[DEVICE]], indirect=True)
async def test_bad_update_discard(
    menuai: menuai, mock_bridge, mock_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that a bad update from device is discarded."""
    await init_integration(menuai)
    assert mock_bridge

    # Test initial hvac mode - cool
    state = menuai.states.get(ENTITY_ID)
    assert state.state == HVACMode.COOL

    # Device send target temperature with 0 to indicate it doesn't have data
    monkeypatch.setattr(DEVICE, "target_temperature", 0)
    monkeypatch.setattr(DEVICE, "mode", ThermostatMode.HEAT)
    mock_bridge.mock_callbacks([DEVICE])
    await menuai.async_block_till_done()

    # Validate state did not change
    state = menuai.states.get(ENTITY_ID)
    assert state.state == HVACMode.COOL


@pytest.mark.parametrize("mock_bridge", [[DEVICE]], indirect=True)
async def test_climate_control_errors(
    menuai: menuai, mock_bridge, mock_api, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test control with settings not supported by device."""
    await init_integration(menuai)
    assert mock_bridge

    # Dry mode does not support setting fan, temperature, swing
    monkeypatch.setattr(DEVICE, "mode", ThermostatMode.DRY)
    mock_bridge.mock_callbacks([DEVICE])
    await menuai.async_block_till_done()

    # Test exception when trying set temperature
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_TEMPERATURE: 24},
            blocking=True,
        )
    # Test exception when trying set fan level
    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_FAN_MODE,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_FAN_MODE: "high"},
            blocking=True,
        )

    # Test exception when trying set swing mode
    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_SWING_MODE,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_SWING_MODE: "off"},
            blocking=True,
        )
