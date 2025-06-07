"""Tests for rainbird sensor platform."""

from http import HTTPStatus

import pytest

from menuai.components.rainbird import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from .conftest import (
    ACK_ECHO,
    CONFIG_ENTRY_DATA_OLD_FORMAT,
    EMPTY_STATIONS_RESPONSE,
    HOST,
    MAC_ADDRESS,
    PASSWORD,
    RAIN_DELAY_OFF,
    RAIN_SENSOR_OFF,
    ZONE_3_ON_RESPONSE,
    ZONE_5_ON_RESPONSE,
    ZONE_OFF_RESPONSE,
    mock_response,
    mock_response_error,
)

from tests.common import MockConfigEntry
from tests.components.switch import common as switch_common
from tests.test_util.aiohttp import AiohttpClientMocker, AiohttpClientMockResponse


@pytest.fixture
def platforms() -> list[str]:
    """Fixture to specify platforms to test."""
    return [Platform.SWITCH]


@pytest.fixture(autouse=True)
async def setup_config_entry(
    menuai: menuai, config_entry: MockConfigEntry
) -> list[Platform]:
    """Fixture to setup the config entry."""
    await menuai.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.LOADED


@pytest.mark.parametrize(
    "stations_response",
    [EMPTY_STATIONS_RESPONSE],
)
async def test_no_zones(
    menuai: menuai,
) -> None:
    """Test case where listing stations returns no stations."""

    zone = menuai.states.get("switch.rain_bird_sprinkler_1")
    assert zone is None


@pytest.mark.parametrize(
    "zone_state_response",
    [ZONE_5_ON_RESPONSE],
)
async def test_zones(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test switch platform with fake data that creates 7 zones with one enabled."""

    zone = menuai.states.get("switch.rain_bird_sprinkler_1")
    assert zone is not None
    assert zone.state == "off"
    assert zone.attributes == {
        "friendly_name": "Rain Bird Sprinkler 1",
        "zone": 1,
    }

    zone = menuai.states.get("switch.rain_bird_sprinkler_2")
    assert zone is not None
    assert zone.state == "off"
    assert zone.attributes == {
        "friendly_name": "Rain Bird Sprinkler 2",
        "zone": 2,
    }

    zone = menuai.states.get("switch.rain_bird_sprinkler_3")
    assert zone is not None
    assert zone.state == "off"

    zone = menuai.states.get("switch.rain_bird_sprinkler_4")
    assert zone is not None
    assert zone.state == "off"

    zone = menuai.states.get("switch.rain_bird_sprinkler_5")
    assert zone is not None
    assert zone.state == "on"

    zone = menuai.states.get("switch.rain_bird_sprinkler_6")
    assert zone is not None
    assert zone.state == "off"

    zone = menuai.states.get("switch.rain_bird_sprinkler_7")
    assert zone is not None
    assert zone.state == "off"

    assert not menuai.states.get("switch.rain_bird_sprinkler_8")

    # Verify unique id for one of the switches
    entity_entry = entity_registry.async_get("switch.rain_bird_sprinkler_3")
    assert entity_entry.unique_id == "4c:a1:61:00:11:22-3"


async def test_switch_on(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    responses: list[AiohttpClientMockResponse],
) -> None:
    """Test turning on irrigation switch."""

    # Initially all zones are off. Pick zone3 as an arbitrary to assert
    # state, then update below as a switch.
    zone = menuai.states.get("switch.rain_bird_sprinkler_3")
    assert zone is not None
    assert zone.state == "off"

    aioclient_mock.mock_calls.clear()
    responses.extend(
        [
            mock_response(ACK_ECHO),  # Switch on response
            # API responses when state is refreshed
            mock_response(ZONE_3_ON_RESPONSE),
            mock_response(RAIN_SENSOR_OFF),
            mock_response(RAIN_DELAY_OFF),
        ]
    )
    await switch_common.async_turn_on(menuai, "switch.rain_bird_sprinkler_3")
    await menuai.async_block_till_done()

    # Verify switch state is updated
    zone = menuai.states.get("switch.rain_bird_sprinkler_3")
    assert zone is not None
    assert zone.state == "on"


@pytest.mark.parametrize(
    ("zone_state_response", "start_state"),
    [
        (ZONE_3_ON_RESPONSE, "on"),
        (ZONE_OFF_RESPONSE, "off"),  # Already off
    ],
)
async def test_switch_off(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    responses: list[AiohttpClientMockResponse],
    start_state: str,
) -> None:
    """Test turning off irrigation switch."""

    # Initially the test zone is on
    zone = menuai.states.get("switch.rain_bird_sprinkler_3")
    assert zone is not None
    assert zone.state == start_state

    aioclient_mock.mock_calls.clear()
    responses.extend(
        [
            mock_response(ACK_ECHO),  # Switch off response
            mock_response(ZONE_OFF_RESPONSE),  # Updated zone state
            mock_response(RAIN_SENSOR_OFF),
            mock_response(RAIN_DELAY_OFF),
        ]
    )
    await switch_common.async_turn_off(menuai, "switch.rain_bird_sprinkler_3")
    await menuai.async_block_till_done()

    # Verify switch state is updated
    zone = menuai.states.get("switch.rain_bird_sprinkler_3")
    assert zone is not None
    assert zone.state == "off"


async def test_irrigation_service(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    responses: list[AiohttpClientMockResponse],
    api_responses: list[str],
) -> None:
    """Test calling the irrigation service."""

    zone = menuai.states.get("switch.rain_bird_sprinkler_3")
    assert zone is not None
    assert zone.state == "off"

    aioclient_mock.mock_calls.clear()
    responses.extend(
        [
            mock_response(ACK_ECHO),
            # API responses when state is refreshed
            mock_response(ZONE_3_ON_RESPONSE),
            mock_response(RAIN_SENSOR_OFF),
            mock_response(RAIN_DELAY_OFF),
        ]
    )

    await menuai.services.async_call(
        DOMAIN,
        "start_irrigation",
        {ATTR_ENTITY_ID: "switch.rain_bird_sprinkler_3", "duration": 30},
        blocking=True,
    )

    zone = menuai.states.get("switch.rain_bird_sprinkler_3")
    assert zone is not None
    assert zone.state == "on"


@pytest.mark.parametrize(
    ("config_entry_data"),
    [
        (
            {
                "host": HOST,
                "password": PASSWORD,
                "trigger_time": 360,
                "serial_number": "0x1263613994342",
                "imported_names": {
                    "1": "Garden Sprinkler",
                    "2": "Back Yard",
                },
                "mac": MAC_ADDRESS,
            }
        )
    ],
)
async def test_yaml_imported_config(
    menuai: menuai,
    responses: list[AiohttpClientMockResponse],
) -> None:
    """Test a config entry that was previously imported from yaml."""

    assert menuai.states.get("switch.garden_sprinkler")
    assert not menuai.states.get("switch.rain_bird_sprinkler_1")
    assert menuai.states.get("switch.back_yard")
    assert not menuai.states.get("switch.rain_bird_sprinkler_2")
    assert menuai.states.get("switch.rain_bird_sprinkler_3")


@pytest.mark.parametrize(
    ("status", "expected_msg"),
    [
        (HTTPStatus.SERVICE_UNAVAILABLE, "Rain Bird device is busy"),
        (HTTPStatus.INTERNAL_SERVER_ERROR, "Rain Bird device failure"),
    ],
)
async def test_switch_error(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    responses: list[AiohttpClientMockResponse],
    status: HTTPStatus,
    expected_msg: str,
) -> None:
    """Test an error talking to the device."""

    aioclient_mock.mock_calls.clear()
    responses.append(mock_response_error(status=status))

    with pytest.raises(menuaiError, match=expected_msg):
        await switch_common.async_turn_on(menuai, "switch.rain_bird_sprinkler_3")

    responses.append(mock_response_error(status=status))

    with pytest.raises(menuaiError, match=expected_msg):
        await switch_common.async_turn_off(menuai, "switch.rain_bird_sprinkler_3")


@pytest.mark.parametrize(
    ("config_entry_data", "config_entry_unique_id", "setup_config_entry"),
    [
        (CONFIG_ENTRY_DATA_OLD_FORMAT, None, None),
    ],
)
async def test_no_unique_id(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    responses: list[AiohttpClientMockResponse],
    entity_registry: er.EntityRegistry,
    config_entry: MockConfigEntry,
) -> None:
    """Test an irrigation switch with no unique id due to migration failure."""

    # Failure to migrate config entry to a unique id
    responses.insert(0, mock_response_error(HTTPStatus.SERVICE_UNAVAILABLE))

    await menuai.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.LOADED

    zone = menuai.states.get("switch.rain_bird_sprinkler_3")
    assert zone is not None
    assert zone.attributes.get("friendly_name") == "Rain Bird Sprinkler 3"
    assert zone.state == "off"

    entity_entry = entity_registry.async_get("switch.rain_bird_sprinkler_3")
    assert entity_entry is None
