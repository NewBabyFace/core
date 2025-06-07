"""Tests for the LaMetric switch platform."""

from unittest.mock import MagicMock

from demetriek import LaMetricConnectionError, LaMetricError
import pytest

from menuai.components.lametric.const import DOMAIN, SCAN_INTERVAL
from menuai.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    STATE_OFF,
    STATE_UNAVAILABLE,
    EntityCategory,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed

pytestmark = pytest.mark.usefixtures("init_integration")


async def test_bluetooth(
    menuai: menuai,
    mock_lametric: MagicMock,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the LaMetric Bluetooth control."""
    state = menuai.states.get("switch.frenck_s_lametric_bluetooth")
    assert state
    assert state.attributes.get(ATTR_DEVICE_CLASS) is None
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "Frenck's LaMetric Bluetooth"
    assert state.state == STATE_OFF

    entry = entity_registry.async_get(state.entity_id)
    assert entry
    assert entry.device_id
    assert entry.entity_category is EntityCategory.CONFIG
    assert entry.unique_id == "SA110405124500W00BS9-bluetooth"

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
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "switch.frenck_s_lametric_bluetooth",
        },
        blocking=True,
    )

    assert len(mock_lametric.bluetooth.mock_calls) == 1
    mock_lametric.bluetooth.assert_called_once_with(active=True)

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {
            ATTR_ENTITY_ID: "switch.frenck_s_lametric_bluetooth",
        },
        blocking=True,
    )

    assert len(mock_lametric.bluetooth.mock_calls) == 2
    mock_lametric.bluetooth.assert_called_with(active=False)

    mock_lametric.device.return_value.bluetooth.available = False
    async_fire_time_changed(menuai, dt_util.utcnow() + SCAN_INTERVAL)
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.frenck_s_lametric_bluetooth")
    assert state
    assert state.state == STATE_UNAVAILABLE


async def test_switch_error(
    menuai: menuai,
    mock_lametric: MagicMock,
) -> None:
    """Test error handling of the LaMetric switches."""
    mock_lametric.bluetooth.side_effect = LaMetricError

    state = menuai.states.get("switch.frenck_s_lametric_bluetooth")
    assert state
    assert state.state == STATE_OFF

    with pytest.raises(
        menuaiError, match="Invalid response from the LaMetric device"
    ):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: "switch.frenck_s_lametric_bluetooth",
            },
            blocking=True,
        )

    state = menuai.states.get("switch.frenck_s_lametric_bluetooth")
    assert state
    assert state.state == STATE_OFF


async def test_switch_connection_error(
    menuai: menuai,
    mock_lametric: MagicMock,
) -> None:
    """Test connection error handling of the LaMetric switches."""
    mock_lametric.bluetooth.side_effect = LaMetricConnectionError

    state = menuai.states.get("switch.frenck_s_lametric_bluetooth")
    assert state
    assert state.state == STATE_OFF

    with pytest.raises(
        menuaiError, match="Error communicating with the LaMetric device"
    ):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: "switch.frenck_s_lametric_bluetooth",
            },
            blocking=True,
        )

    state = menuai.states.get("switch.frenck_s_lametric_bluetooth")
    assert state
    assert state.state == STATE_UNAVAILABLE
