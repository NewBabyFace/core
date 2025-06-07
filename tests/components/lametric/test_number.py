"""Tests for the LaMetric number platform."""

from unittest.mock import MagicMock

from demetriek import LaMetricConnectionError, LaMetricError
import pytest

from menuai.components.lametric.const import DOMAIN
from menuai.components.number import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_STEP,
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    EntityCategory,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import device_registry as dr, entity_registry as er

pytestmark = pytest.mark.usefixtures("init_integration")


async def test_brightness(
    menuai: menuai,
    mock_lametric: MagicMock,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the LaMetric display brightness controls."""
    state = menuai.states.get("number.frenck_s_lametric_brightness")
    assert state
    assert state.attributes.get(ATTR_DEVICE_CLASS) is None
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Frenck's LaMetric Brightness"
    assert state.attributes.get(ATTR_MAX) == 100
    assert state.attributes.get(ATTR_MIN) == 2
    assert state.attributes.get(ATTR_STEP) == 1
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == PERCENTAGE
    assert state.state == "100"

    entry = entity_registry.async_get(state.entity_id)
    assert entry
    assert entry.device_id
    assert entry.entity_category is EntityCategory.CONFIG
    assert entry.unique_id == "SA110405124500W00BS9-brightness"

    device = device_registry.async_get(entry.device_id)
    assert device
    assert device.configuration_url is None
    assert device.connections == {(dr.CONNECTION_NETWORK_MAC, "aa:bb:cc:dd:ee:ff")}
    assert device.entry_type is None
    assert device.hw_version is None
    assert device.identifiers == {(DOMAIN, "SA110405124500W00BS9")}
    assert device.manufacturer == "LaMetric Inc."
    assert device.name == "Frenck's LaMetric"
    assert device.serial_number == "SA110405124500W00BS9"
    assert device.sw_version == "2.2.2"

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {
            ATTR_ENTITY_ID: "number.frenck_s_lametric_brightness",
            ATTR_VALUE: 21,
        },
        blocking=True,
    )
    await menuai.async_block_till_done()

    assert len(mock_lametric.display.mock_calls) == 1
    mock_lametric.display.assert_called_once_with(brightness=21)


async def test_volume(
    menuai: menuai,
    mock_lametric: MagicMock,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the LaMetric volume controls."""
    state = menuai.states.get("number.frenck_s_lametric_volume")
    assert state
    assert state.attributes.get(ATTR_DEVICE_CLASS) is None
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Frenck's LaMetric Volume"
    assert state.attributes.get(ATTR_MAX) == 100
    assert state.attributes.get(ATTR_MIN) == 0
    assert state.attributes.get(ATTR_STEP) == 1
    assert state.state == "100"

    entry = entity_registry.async_get(state.entity_id)
    assert entry
    assert entry.device_id
    assert entry.entity_category is EntityCategory.CONFIG
    assert entry.unique_id == "SA110405124500W00BS9-volume"

    device = device_registry.async_get(entry.device_id)
    assert device
    assert device.configuration_url is None
    assert device.connections == {(dr.CONNECTION_NETWORK_MAC, "aa:bb:cc:dd:ee:ff")}
    assert device.entry_type is None
    assert device.hw_version is None
    assert device.identifiers == {(DOMAIN, "SA110405124500W00BS9")}
    assert device.manufacturer == "LaMetric Inc."
    assert device.name == "Frenck's LaMetric"
    assert device.sw_version == "2.2.2"

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {
            ATTR_ENTITY_ID: "number.frenck_s_lametric_volume",
            ATTR_VALUE: 42,
        },
        blocking=True,
    )
    await menuai.async_block_till_done()

    assert len(mock_lametric.audio.mock_calls) == 1
    mock_lametric.audio.assert_called_once_with(volume=42)


async def test_number_error(
    menuai: menuai,
    mock_lametric: MagicMock,
) -> None:
    """Test error handling of the LaMetric numbers."""
    mock_lametric.audio.side_effect = LaMetricError

    state = menuai.states.get("number.frenck_s_lametric_volume")
    assert state
    assert state.state == "100"

    with pytest.raises(
        menuaiError, match="Invalid response from the LaMetric device"
    ):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {
                ATTR_ENTITY_ID: "number.frenck_s_lametric_volume",
                ATTR_VALUE: 42,
            },
            blocking=True,
        )

    state = menuai.states.get("number.frenck_s_lametric_volume")
    assert state
    assert state.state == "100"


async def test_number_connection_error(
    menuai: menuai,
    mock_lametric: MagicMock,
) -> None:
    """Test connection error handling of the LaMetric numbers."""
    mock_lametric.audio.side_effect = LaMetricConnectionError

    state = menuai.states.get("number.frenck_s_lametric_volume")
    assert state
    assert state.state == "100"

    with pytest.raises(
        menuaiError, match="Error communicating with the LaMetric device"
    ):
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {
                ATTR_ENTITY_ID: "number.frenck_s_lametric_volume",
                ATTR_VALUE: 42,
            },
            blocking=True,
        )

    state = menuai.states.get("number.frenck_s_lametric_volume")
    assert state
    assert state.state == STATE_UNAVAILABLE


@pytest.mark.parametrize("device_fixture", ["computer_powered"])
async def test_computer_powered_devices(
    menuai: menuai,
    mock_lametric: MagicMock,
) -> None:
    """Test Brightness is properly limited for computer powered devices."""
    state = menuai.states.get("number.time_brightness")
    assert state
    assert state.state == "75"
    assert state.attributes[ATTR_MIN] == 2
    assert state.attributes[ATTR_MAX] == 76
