"""The test for the sensibo switch platform."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.config_entries import ConfigEntry
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    Platform,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from tests.common import async_fire_time_changed, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    "load_platforms",
    [[Platform.SWITCH]],
)
async def test_switch(
    menuai: menuai,
    load_int: ConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the Sensibo switch."""
    await snapshot_platform(menuai, entity_registry, snapshot, load_int.entry_id)


async def test_switch_timer(
    menuai: menuai,
    load_int: ConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the Sensibo switch timer."""

    state = menuai.states.get("switch.hallway_timer")
    assert state.state == STATE_OFF
    assert state.attributes["id"] is None
    assert state.attributes["turn_on"] is None

    mock_client.async_set_timer.return_value = {
        "status": "success",
        "result": {"id": "SzTGE4oZ4D"},
    }

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: state.entity_id,
        },
        blocking=True,
    )

    mock_client.async_get_devices_data.return_value.parsed["ABC999111"].timer_on = True
    mock_client.async_get_devices_data.return_value.parsed[
        "ABC999111"
    ].timer_id = "SzTGE4oZ4D"
    mock_client.async_get_devices_data.return_value.parsed[
        "ABC999111"
    ].timer_state_on = False

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.hallway_timer")
    assert state.state == STATE_ON
    assert state.attributes["id"] == "SzTGE4oZ4D"
    assert state.attributes["turn_on"] is False

    mock_client.async_del_timer.return_value = {
        "status": "success",
        "result": {"id": "SzTGE4oZ4D"},
    }

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {
            ATTR_ENTITY_ID: state.entity_id,
        },
        blocking=True,
    )

    mock_client.async_get_devices_data.return_value.parsed["ABC999111"].timer_on = False

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.hallway_timer")
    assert state.state == STATE_OFF


async def test_switch_pure_boost(
    menuai: menuai,
    load_int: ConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the Sensibo switch pure boost."""

    state = menuai.states.get("switch.kitchen_pure_boost")
    assert state.state == STATE_OFF

    mock_client.async_set_pureboost.return_value = {"status": "success"}

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: state.entity_id,
        },
        blocking=True,
    )

    mock_client.async_get_devices_data.return_value.parsed[
        "AAZZAAZZ"
    ].pure_boost_enabled = True
    mock_client.async_get_devices_data.return_value.parsed[
        "AAZZAAZZ"
    ].pure_measure_integration = None

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.kitchen_pure_boost")
    assert state.state == STATE_ON

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {
            ATTR_ENTITY_ID: state.entity_id,
        },
        blocking=True,
    )

    mock_client.async_get_devices_data.return_value.parsed[
        "AAZZAAZZ"
    ].pure_boost_enabled = False

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.kitchen_pure_boost")
    assert state.state == STATE_OFF


async def test_switch_command_failure(
    menuai: menuai, load_int: ConfigEntry, mock_client: MagicMock
) -> None:
    """Test the Sensibo switch fails commands."""

    state = menuai.states.get("switch.hallway_timer")

    mock_client.async_set_timer.return_value = {"status": "failure"}

    with pytest.raises(
        menuaiError,
    ):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: state.entity_id,
            },
            blocking=True,
        )

    mock_client.async_del_timer.return_value = {"status": "failure"}

    with pytest.raises(
        menuaiError,
    ):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {
                ATTR_ENTITY_ID: state.entity_id,
            },
            blocking=True,
        )


async def test_switch_climate_react(
    menuai: menuai,
    load_int: ConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the Sensibo switch for climate react."""

    state = menuai.states.get("switch.hallway_climate_react")
    assert state.state == STATE_OFF

    mock_client.async_enable_climate_react.return_value = {"status": "success"}

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: state.entity_id,
        },
        blocking=True,
    )

    mock_client.async_get_devices_data.return_value.parsed["ABC999111"].smart_on = True

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.hallway_climate_react")
    assert state.state == STATE_ON

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {
            ATTR_ENTITY_ID: state.entity_id,
        },
        blocking=True,
    )

    mock_client.async_get_devices_data.return_value.parsed["ABC999111"].smart_on = False

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.hallway_climate_react")
    assert state.state == STATE_OFF


async def test_switch_climate_react_no_data(
    menuai: menuai,
    load_int: ConfigEntry,
    mock_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the Sensibo switch for climate react with no data."""

    mock_client.async_get_devices_data.return_value.parsed[
        "ABC999111"
    ].smart_type = None

    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get("switch.hallway_climate_react")
    assert state.state == STATE_OFF

    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: state.entity_id,
            },
            blocking=True,
        )
