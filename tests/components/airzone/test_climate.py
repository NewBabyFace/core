"""The climate tests for the Airzone platform."""

import copy
from unittest.mock import patch

from aioairzone.const import (
    API_COOL_SET_POINT,
    API_DATA,
    API_HEAT_SET_POINT,
    API_MAX_TEMP,
    API_MIN_TEMP,
    API_ON,
    API_SET_POINT,
    API_SPEED,
    API_SYSTEM_ID,
    API_SYSTEMS,
    API_ZONE_ID,
)
from aioairzone.exceptions import AirzoneError
import pytest

from menuai.components.airzone.const import API_TEMPERATURE_STEP
from menuai.components.airzone.coordinator import SCAN_INTERVAL
from menuai.components.climate import (
    ATTR_CURRENT_HUMIDITY,
    ATTR_CURRENT_TEMPERATURE,
    ATTR_FAN_MODE,
    ATTR_FAN_MODES,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TARGET_TEMP_STEP,
    DOMAIN as CLIMATE_DOMAIN,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACAction,
    HVACMode,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.util.dt import utcnow

from .util import (
    HVAC_DHW_MOCK,
    HVAC_MOCK,
    HVAC_SYSTEMS_MOCK,
    HVAC_WEBSERVER_MOCK,
    async_init_integration,
)

from tests.common import async_fire_time_changed


async def test_airzone_create_climates(menuai: menuai) -> None:
    """Test creation of climates."""

    await async_init_integration(menuai)

    state = menuai.states.get("climate.despacho")
    assert state.state == HVACMode.OFF
    assert state.attributes.get(ATTR_CURRENT_HUMIDITY) == 36
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 21.2
    assert state.attributes.get(ATTR_FAN_MODE) is None
    assert state.attributes.get(ATTR_FAN_MODES) is None
    assert state.attributes.get(ATTR_HVAC_ACTION) == HVACAction.OFF
    assert state.attributes.get(ATTR_HVAC_MODES) == [
        HVACMode.OFF,
        HVACMode.FAN_ONLY,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.DRY,
    ]
    assert state.attributes.get(ATTR_MAX_TEMP) == 30
    assert state.attributes.get(ATTR_MIN_TEMP) == 15
    assert state.attributes.get(ATTR_TARGET_TEMP_STEP) == API_TEMPERATURE_STEP
    assert state.attributes.get(ATTR_TEMPERATURE) == 19.4

    state = menuai.states.get("climate.dorm_1")
    assert state.state == HVACMode.HEAT
    assert state.attributes.get(ATTR_CURRENT_HUMIDITY) == 35
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 20.8
    assert state.attributes.get(ATTR_FAN_MODE) is None
    assert state.attributes.get(ATTR_FAN_MODES) is None
    assert state.attributes.get(ATTR_HVAC_ACTION) == HVACAction.IDLE
    assert state.attributes.get(ATTR_HVAC_MODES) == [
        HVACMode.OFF,
        HVACMode.FAN_ONLY,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.DRY,
    ]
    assert state.attributes.get(ATTR_MAX_TEMP) == 30
    assert state.attributes.get(ATTR_MIN_TEMP) == 15
    assert state.attributes.get(ATTR_TARGET_TEMP_STEP) == API_TEMPERATURE_STEP
    assert state.attributes.get(ATTR_TEMPERATURE) == 19.3

    state = menuai.states.get("climate.dorm_2")
    assert state.state == HVACMode.OFF
    assert state.attributes.get(ATTR_CURRENT_HUMIDITY) == 40
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 20.5
    assert state.attributes.get(ATTR_FAN_MODE) is None
    assert state.attributes.get(ATTR_FAN_MODES) is None
    assert state.attributes.get(ATTR_HVAC_ACTION) == HVACAction.OFF
    assert state.attributes.get(ATTR_HVAC_MODES) == [
        HVACMode.OFF,
        HVACMode.FAN_ONLY,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.DRY,
    ]
    assert state.attributes.get(ATTR_MAX_TEMP) == 30
    assert state.attributes.get(ATTR_MIN_TEMP) == 15
    assert state.attributes.get(ATTR_TARGET_TEMP_STEP) == API_TEMPERATURE_STEP
    assert state.attributes.get(ATTR_TEMPERATURE) == 19.5

    state = menuai.states.get("climate.dorm_ppal")
    assert state.state == HVACMode.HEAT
    assert state.attributes.get(ATTR_CURRENT_HUMIDITY) == 39
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 21.1
    assert state.attributes.get(ATTR_FAN_MODE) == FAN_AUTO
    assert state.attributes.get(ATTR_FAN_MODES) == [
        FAN_AUTO,
        FAN_LOW,
        FAN_HIGH,
    ]
    assert state.attributes.get(ATTR_HVAC_ACTION) == HVACAction.HEATING
    assert state.attributes.get(ATTR_HVAC_MODES) == [
        HVACMode.OFF,
        HVACMode.FAN_ONLY,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.DRY,
    ]
    assert state.attributes.get(ATTR_MAX_TEMP) == 30
    assert state.attributes.get(ATTR_MIN_TEMP) == 15
    assert state.attributes.get(ATTR_TARGET_TEMP_STEP) == API_TEMPERATURE_STEP
    assert state.attributes.get(ATTR_TEMPERATURE) == 19.2

    state = menuai.states.get("climate.salon")
    assert state.state == HVACMode.OFF
    assert state.attributes.get(ATTR_CURRENT_HUMIDITY) == 34
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 19.6
    assert state.attributes.get(ATTR_FAN_MODE) == FAN_AUTO
    assert state.attributes.get(ATTR_FAN_MODES) == [
        FAN_AUTO,
        FAN_LOW,
        FAN_MEDIUM,
        FAN_HIGH,
    ]
    assert state.attributes.get(ATTR_HVAC_ACTION) == HVACAction.OFF
    assert state.attributes.get(ATTR_HVAC_MODES) == [
        HVACMode.OFF,
        HVACMode.FAN_ONLY,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.DRY,
    ]
    assert state.attributes.get(ATTR_MAX_TEMP) == 30
    assert state.attributes.get(ATTR_MIN_TEMP) == 15
    assert state.attributes.get(ATTR_TARGET_TEMP_STEP) == API_TEMPERATURE_STEP
    assert state.attributes.get(ATTR_TEMPERATURE) == 19.1

    state = menuai.states.get("climate.airzone_2_1")
    assert state.state == HVACMode.OFF
    assert state.attributes.get(ATTR_CURRENT_HUMIDITY) == 62
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 22.3
    assert state.attributes.get(ATTR_FAN_MODE) == FAN_AUTO
    assert state.attributes.get(ATTR_FAN_MODES) == [
        FAN_AUTO,
        FAN_LOW,
        FAN_MEDIUM,
        "75%",
        FAN_HIGH,
    ]
    assert state.attributes.get(ATTR_HVAC_ACTION) == HVACAction.OFF
    assert state.attributes.get(ATTR_HVAC_MODES) == [
        HVACMode.HEAT_COOL,
        HVACMode.OFF,
    ]
    assert state.attributes.get(ATTR_MAX_TEMP) == 30
    assert state.attributes.get(ATTR_MIN_TEMP) == 15
    assert state.attributes.get(ATTR_TARGET_TEMP_STEP) == API_TEMPERATURE_STEP
    assert state.attributes.get(ATTR_TEMPERATURE) == 19.0

    state = menuai.states.get("climate.dkn_plus")
    assert state.state == HVACMode.HEAT_COOL
    assert state.attributes.get(ATTR_CURRENT_HUMIDITY) is None
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 21.7
    assert state.attributes.get(ATTR_FAN_MODE) == "40%"
    assert state.attributes.get(ATTR_FAN_MODES) == [
        FAN_AUTO,
        FAN_LOW,
        "40%",
        FAN_MEDIUM,
        "80%",
        FAN_HIGH,
    ]
    assert state.attributes.get(ATTR_HVAC_ACTION) == HVACAction.COOLING
    assert state.attributes.get(ATTR_HVAC_MODES) == [
        HVACMode.FAN_ONLY,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.DRY,
        HVACMode.HEAT_COOL,
        HVACMode.OFF,
    ]
    assert state.attributes.get(ATTR_MAX_TEMP) == 32.2
    assert state.attributes.get(ATTR_MIN_TEMP) == 17.8
    assert state.attributes.get(ATTR_TARGET_TEMP_STEP) == API_TEMPERATURE_STEP
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == 25.0
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == 22.8

    state = menuai.states.get("climate.aux_heat")
    assert state.state == HVACMode.HEAT
    assert state.attributes.get(ATTR_CURRENT_HUMIDITY) is None
    assert state.attributes.get(ATTR_CURRENT_TEMPERATURE) == 22
    assert state.attributes.get(ATTR_HVAC_ACTION) == HVACAction.IDLE
    assert state.attributes.get(ATTR_HVAC_MODES) == [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.FAN_ONLY,
        HVACMode.DRY,
    ]
    assert state.attributes.get(ATTR_MAX_TEMP) == 30
    assert state.attributes.get(ATTR_MIN_TEMP) == 15
    assert state.attributes.get(ATTR_TARGET_TEMP_STEP) == API_TEMPERATURE_STEP
    assert state.attributes.get(ATTR_TEMPERATURE) == 20.0

    HVAC_MOCK_CHANGED = copy.deepcopy(HVAC_MOCK)
    HVAC_MOCK_CHANGED[API_SYSTEMS][0][API_DATA][0][API_MAX_TEMP] = 25
    HVAC_MOCK_CHANGED[API_SYSTEMS][0][API_DATA][0][API_MIN_TEMP] = 10

    with (
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_dhw",
            return_value=HVAC_DHW_MOCK,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_hvac",
            return_value=HVAC_MOCK_CHANGED,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_hvac_systems",
            return_value=HVAC_SYSTEMS_MOCK,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_webserver",
            return_value=HVAC_WEBSERVER_MOCK,
        ),
    ):
        async_fire_time_changed(menuai, utcnow() + SCAN_INTERVAL)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get("climate.salon")
    assert state.attributes.get(ATTR_MAX_TEMP) == 25
    assert state.attributes.get(ATTR_MIN_TEMP) == 10


async def test_airzone_climate_turn_on_off(menuai: menuai) -> None:
    """Test turning on."""

    await async_init_integration(menuai)

    HVAC_MOCK = {
        API_DATA: [
            {
                API_SYSTEM_ID: 1,
                API_ZONE_ID: 1,
                API_ON: 1,
            }
        ]
    }
    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=HVAC_MOCK,
    ):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: "climate.salon",
            },
            blocking=True,
        )

    state = menuai.states.get("climate.salon")
    assert state.state == HVACMode.HEAT

    HVAC_MOCK = {
        API_DATA: [
            {
                API_SYSTEM_ID: 1,
                API_ZONE_ID: 1,
                API_ON: 0,
            }
        ]
    }
    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=HVAC_MOCK,
    ):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_TURN_OFF,
            {
                ATTR_ENTITY_ID: "climate.salon",
            },
            blocking=True,
        )

    state = menuai.states.get("climate.salon")
    assert state.state == HVACMode.OFF

    HVAC_MOCK = {
        API_DATA: [
            {
                API_SYSTEM_ID: 2,
                API_ZONE_ID: 1,
                API_ON: 1,
            }
        ]
    }
    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=HVAC_MOCK,
    ):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: "climate.airzone_2_1",
            },
            blocking=True,
        )

    state = menuai.states.get("climate.airzone_2_1")
    assert state.state == HVACMode.HEAT_COOL


async def test_airzone_climate_set_hvac_mode(menuai: menuai) -> None:
    """Test setting the HVAC mode."""

    await async_init_integration(menuai)

    HVAC_MOCK_1 = {
        API_DATA: [
            {
                API_SYSTEM_ID: 1,
                API_ZONE_ID: 1,
                API_ON: 1,
            }
        ]
    }
    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=HVAC_MOCK_1,
    ):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {
                ATTR_ENTITY_ID: "climate.salon",
                ATTR_HVAC_MODE: HVACMode.COOL,
            },
            blocking=True,
        )

    state = menuai.states.get("climate.salon")
    assert state.state == HVACMode.COOL

    HVAC_MOCK_2 = {
        API_DATA: [
            {
                API_SYSTEM_ID: 1,
                API_ZONE_ID: 1,
                API_ON: 0,
            }
        ]
    }
    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=HVAC_MOCK_2,
    ):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {
                ATTR_ENTITY_ID: "climate.salon",
                ATTR_HVAC_MODE: HVACMode.OFF,
            },
            blocking=True,
        )

    state = menuai.states.get("climate.salon")
    assert state.state == HVACMode.OFF

    HVAC_MOCK_3 = {
        API_DATA: [
            {
                API_SYSTEM_ID: 2,
                API_ZONE_ID: 1,
                API_ON: 1,
            }
        ]
    }
    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=HVAC_MOCK_3,
    ):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {
                ATTR_ENTITY_ID: "climate.airzone_2_1",
                ATTR_HVAC_MODE: HVACMode.HEAT_COOL,
            },
            blocking=True,
        )

    state = menuai.states.get("climate.airzone_2_1")
    assert state.state == HVACMode.HEAT_COOL

    HVAC_MOCK_4 = {
        API_DATA: [
            {
                API_SYSTEM_ID: 1,
                API_ZONE_ID: 1,
                API_ON: 1,
            }
        ]
    }
    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=HVAC_MOCK_4,
    ):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {
                ATTR_ENTITY_ID: "climate.salon",
                ATTR_HVAC_MODE: HVACMode.FAN_ONLY,
            },
            blocking=True,
        )

    state = menuai.states.get("climate.salon")
    assert state.state == HVACMode.FAN_ONLY

    HVAC_MOCK_NO_SET_POINT = copy.deepcopy(HVAC_MOCK)
    del HVAC_MOCK_NO_SET_POINT[API_SYSTEMS][0][API_DATA][0][API_SET_POINT]

    with (
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_dhw",
            return_value=HVAC_DHW_MOCK,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_hvac",
            return_value=HVAC_MOCK_NO_SET_POINT,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_hvac_systems",
            return_value=HVAC_SYSTEMS_MOCK,
        ),
        patch(
            "menuai.components.airzone.AirzoneLocalApi.get_webserver",
            return_value=HVAC_WEBSERVER_MOCK,
        ),
    ):
        async_fire_time_changed(menuai, utcnow() + SCAN_INTERVAL)
        await menuai.async_block_till_done()

    state = menuai.states.get("climate.salon")
    assert state.attributes.get(ATTR_TEMPERATURE) == 19.1


async def test_airzone_climate_set_hvac_slave_error(menuai: menuai) -> None:
    """Test setting the HVAC mode for a slave zone."""

    HVAC_MOCK = {
        API_DATA: [
            {
                API_SYSTEM_ID: 1,
                API_ZONE_ID: 5,
                API_ON: 1,
            }
        ]
    }

    await async_init_integration(menuai)

    with (
        patch(
            "menuai.components.airzone.AirzoneLocalApi.put_hvac",
            return_value=HVAC_MOCK,
        ),
        pytest.raises(menuaiError),
    ):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {
                ATTR_ENTITY_ID: "climate.dorm_2",
                ATTR_HVAC_MODE: HVACMode.COOL,
            },
            blocking=True,
        )

    state = menuai.states.get("climate.dorm_2")
    assert state.state == HVACMode.HEAT


async def test_airzone_climate_set_fan_mode(menuai: menuai) -> None:
    """Test setting the target temperature."""

    HVAC_MOCK = {
        API_DATA: [
            {
                API_SYSTEM_ID: 1,
                API_ZONE_ID: 1,
                API_SPEED: 2,
            }
        ]
    }

    await async_init_integration(menuai)

    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=HVAC_MOCK,
    ):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_FAN_MODE,
            {
                ATTR_ENTITY_ID: "climate.salon",
                ATTR_FAN_MODE: FAN_MEDIUM,
            },
            blocking=True,
        )

    state = menuai.states.get("climate.salon")
    assert state.attributes.get(ATTR_FAN_MODE) == FAN_MEDIUM


async def test_airzone_climate_set_temp(menuai: menuai) -> None:
    """Test setting the target temperature."""

    HVAC_MOCK = {
        API_DATA: [
            {
                API_SYSTEM_ID: 1,
                API_ZONE_ID: 5,
                API_SET_POINT: 20.5,
                API_ON: 1,
            }
        ]
    }

    await async_init_integration(menuai)

    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=HVAC_MOCK,
    ):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: "climate.dorm_2",
                ATTR_HVAC_MODE: HVACMode.HEAT,
                ATTR_TEMPERATURE: 20.5,
            },
            blocking=True,
        )

    state = menuai.states.get("climate.dorm_2")
    assert state.state == HVACMode.HEAT
    assert state.attributes.get(ATTR_TEMPERATURE) == 20.5


async def test_airzone_climate_set_temp_error(menuai: menuai) -> None:
    """Test error when setting the target temperature."""

    await async_init_integration(menuai)

    with (
        patch(
            "menuai.components.airzone.AirzoneLocalApi.put_hvac",
            side_effect=AirzoneError,
        ),
        pytest.raises(menuaiError),
    ):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: "climate.dorm_2",
                ATTR_TEMPERATURE: 20.5,
            },
            blocking=True,
        )

    state = menuai.states.get("climate.dorm_2")
    assert state.attributes.get(ATTR_TEMPERATURE) == 19.5


async def test_airzone_climate_set_temp_range(menuai: menuai) -> None:
    """Test setting the target temperature range."""

    HVAC_MOCK = {
        API_DATA: [
            {
                API_SYSTEM_ID: 3,
                API_ZONE_ID: 1,
                API_COOL_SET_POINT: 77.0,
                API_HEAT_SET_POINT: 68.0,
            }
        ]
    }

    await async_init_integration(menuai)

    with patch(
        "menuai.components.airzone.AirzoneLocalApi.put_hvac",
        return_value=HVAC_MOCK,
    ):
        await menuai.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: "climate.dkn_plus",
                ATTR_TARGET_TEMP_HIGH: 25.0,
                ATTR_TARGET_TEMP_LOW: 20.0,
            },
            blocking=True,
        )

    state = menuai.states.get("climate.dkn_plus")
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == 25.0
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == 20.0
