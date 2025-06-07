"""The water heater tests for the Airzone Cloud platform."""

from unittest.mock import patch

from aioairzone_cloud.exceptions import AirzoneCloudError
import pytest

from menuai.components.water_heater import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_OPERATION_MODE,
    DOMAIN as WATER_HEATER_DOMAIN,
    SERVICE_SET_OPERATION_MODE,
    SERVICE_SET_TEMPERATURE,
    STATE_ECO,
    STATE_PERFORMANCE,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError

from .util import async_init_integration


async def test_airzone_create_water_heater(menuai: menuai) -> None:
    """Test creation of water heater."""

    await async_init_integration(menuai)

    state = menuai.states.get("water_heater.airzone_cloud_dhw")
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 45.5
    assert state.attributes[ATTR_MAX_TEMP] == 60
    assert state.attributes[ATTR_MIN_TEMP] == 40
    assert state.attributes[ATTR_TEMPERATURE] == 48


async def test_airzone_water_heater_turn_on_off(menuai: menuai) -> None:
    """Test turning on/off."""

    await async_init_integration(menuai)

    with patch(
        "menuai.components.airzone_cloud.AirzoneCloudApi.api_patch_device",
        return_value=None,
    ):
        await menuai.services.async_call(
            WATER_HEATER_DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: "water_heater.airzone_cloud_dhw",
            },
            blocking=True,
        )

    state = menuai.states.get("water_heater.airzone_cloud_dhw")
    assert state.state == STATE_ECO

    with patch(
        "menuai.components.airzone_cloud.AirzoneCloudApi.api_patch_device",
        return_value=None,
    ):
        await menuai.services.async_call(
            WATER_HEATER_DOMAIN,
            SERVICE_TURN_OFF,
            {
                ATTR_ENTITY_ID: "water_heater.airzone_cloud_dhw",
            },
            blocking=True,
        )

    state = menuai.states.get("water_heater.airzone_cloud_dhw")
    assert state.state == STATE_OFF


async def test_airzone_water_heater_set_operation(menuai: menuai) -> None:
    """Test setting the Operation mode."""

    await async_init_integration(menuai)

    with patch(
        "menuai.components.airzone_cloud.AirzoneCloudApi.api_patch_device",
        return_value=None,
    ):
        await menuai.services.async_call(
            WATER_HEATER_DOMAIN,
            SERVICE_SET_OPERATION_MODE,
            {
                ATTR_ENTITY_ID: "water_heater.airzone_cloud_dhw",
                ATTR_OPERATION_MODE: STATE_ECO,
            },
            blocking=True,
        )

    state = menuai.states.get("water_heater.airzone_cloud_dhw")
    assert state.state == STATE_ECO

    with patch(
        "menuai.components.airzone_cloud.AirzoneCloudApi.api_patch_device",
        return_value=None,
    ):
        await menuai.services.async_call(
            WATER_HEATER_DOMAIN,
            SERVICE_SET_OPERATION_MODE,
            {
                ATTR_ENTITY_ID: "water_heater.airzone_cloud_dhw",
                ATTR_OPERATION_MODE: STATE_PERFORMANCE,
            },
            blocking=True,
        )

    state = menuai.states.get("water_heater.airzone_cloud_dhw")
    assert state.state == STATE_PERFORMANCE

    with patch(
        "menuai.components.airzone_cloud.AirzoneCloudApi.api_patch_device",
        return_value=None,
    ):
        await menuai.services.async_call(
            WATER_HEATER_DOMAIN,
            SERVICE_SET_OPERATION_MODE,
            {
                ATTR_ENTITY_ID: "water_heater.airzone_cloud_dhw",
                ATTR_OPERATION_MODE: STATE_OFF,
            },
            blocking=True,
        )

    state = menuai.states.get("water_heater.airzone_cloud_dhw")
    assert state.state == STATE_OFF


async def test_airzone_water_heater_set_temp(menuai: menuai) -> None:
    """Test setting the target temperature."""

    await async_init_integration(menuai)

    with patch(
        "menuai.components.airzone_cloud.AirzoneCloudApi.api_patch_device",
        return_value=None,
    ):
        await menuai.services.async_call(
            WATER_HEATER_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: "water_heater.airzone_cloud_dhw",
                ATTR_TEMPERATURE: 50,
            },
            blocking=True,
        )

    state = menuai.states.get("water_heater.airzone_cloud_dhw")
    assert state.attributes[ATTR_TEMPERATURE] == 50


async def test_airzone_water_heater_set_temp_error(menuai: menuai) -> None:
    """Test error when setting the target temperature."""

    await async_init_integration(menuai)

    with (
        patch(
            "menuai.components.airzone_cloud.AirzoneCloudApi.api_patch_device",
            side_effect=AirzoneCloudError,
        ),
        pytest.raises(menuaiError),
    ):
        await menuai.services.async_call(
            WATER_HEATER_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: "water_heater.airzone_cloud_dhw",
                ATTR_TEMPERATURE: 80,
            },
            blocking=True,
        )

    state = menuai.states.get("water_heater.airzone_cloud_dhw")
    assert state.attributes[ATTR_TEMPERATURE] == 48
