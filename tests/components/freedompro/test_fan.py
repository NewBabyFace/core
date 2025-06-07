"""Tests for the Freedompro fan."""

from datetime import timedelta
from unittest.mock import ANY, patch

from menuai.components.fan import (
    ATTR_PERCENTAGE,
    DOMAIN as FAN_DOMAIN,
    SERVICE_SET_PERCENTAGE,
    SERVICE_TURN_ON,
)
from menuai.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.entity_component import async_update_entity
from menuai.util.dt import utcnow

from .conftest import get_states_response_for_uid

from tests.common import MockConfigEntry, async_fire_time_changed

uid = "3WRRJR6RCZQZSND8VP0YTO3YXCSOFPKBMW8T51TU-LQ*ILYH1E3DWZOVMNEUIMDYMNLOW-LFRQFDPWWJOVHVDOS"


async def test_fan_get_state(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test states of the fan."""

    device = device_registry.async_get_device(identifiers={("freedompro", uid)})
    assert device is not None
    assert device.identifiers == {("freedompro", uid)}
    assert device.manufacturer == "Freedompro"
    assert device.name == "bedroom"
    assert device.model == "fan"

    entity_id = "fan.bedroom"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_PERCENTAGE] == 0
    assert state.attributes.get("friendly_name") == "bedroom"

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == uid

    states_response = get_states_response_for_uid(uid)
    states_response[0]["state"]["on"] = True
    states_response[0]["state"]["rotationSpeed"] = 50
    with patch(
        "menuai.components.freedompro.coordinator.get_states",
        return_value=states_response,
    ):
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=2))
        await menuai.async_block_till_done()

        state = menuai.states.get(entity_id)
        assert state
        assert state.attributes.get("friendly_name") == "bedroom"

        entry = entity_registry.async_get(entity_id)
        assert entry
        assert entry.unique_id == uid

        assert state.state == STATE_ON
        assert state.attributes[ATTR_PERCENTAGE] == 50


async def test_fan_set_off(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test turn off the fan."""

    entity_id = "fan.bedroom"

    states_response = get_states_response_for_uid(uid)
    states_response[0]["state"]["on"] = True
    states_response[0]["state"]["rotationSpeed"] = 50
    with patch(
        "menuai.components.freedompro.coordinator.get_states",
        return_value=states_response,
    ):
        await async_update_entity(menuai, entity_id)
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=2))
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_ON
    assert state.attributes[ATTR_PERCENTAGE] == 50
    assert state.attributes.get("friendly_name") == "bedroom"

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == uid

    with patch("menuai.components.freedompro.fan.put_state") as mock_put_state:
        await menuai.services.async_call(
            FAN_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
    mock_put_state.assert_called_once_with(ANY, ANY, ANY, '{"on": false}')

    states_response[0]["state"]["on"] = False
    states_response[0]["state"]["rotationSpeed"] = 0
    with patch(
        "menuai.components.freedompro.coordinator.get_states",
        return_value=states_response,
    ):
        await async_update_entity(menuai, entity_id)
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=2))
        await menuai.async_block_till_done()

    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.attributes[ATTR_PERCENTAGE] == 0
    assert state.state == STATE_OFF


async def test_fan_set_on(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test turn on the fan."""

    entity_id = "fan.bedroom"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_PERCENTAGE] == 0
    assert state.attributes.get("friendly_name") == "bedroom"

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == uid

    with patch("menuai.components.freedompro.fan.put_state") as mock_put_state:
        await menuai.services.async_call(
            FAN_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
    mock_put_state.assert_called_once_with(ANY, ANY, ANY, '{"on": true}')

    states_response = get_states_response_for_uid(uid)
    states_response[0]["state"]["on"] = True
    states_response[0]["state"]["rotationSpeed"] = 50
    with patch(
        "menuai.components.freedompro.coordinator.get_states",
        return_value=states_response,
    ):
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=2))
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.attributes[ATTR_PERCENTAGE] == 50
    assert state.state == STATE_ON


async def test_fan_set_percent(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test turn on the fan."""

    entity_id = "fan.bedroom"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_PERCENTAGE] == 0
    assert state.attributes.get("friendly_name") == "bedroom"

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == uid

    with patch("menuai.components.freedompro.fan.put_state") as mock_put_state:
        await menuai.services.async_call(
            FAN_DOMAIN,
            SERVICE_SET_PERCENTAGE,
            {ATTR_ENTITY_ID: [entity_id], ATTR_PERCENTAGE: 40},
            blocking=True,
        )
    mock_put_state.assert_called_once_with(ANY, ANY, ANY, '{"rotationSpeed": 40}')

    states_response = get_states_response_for_uid(uid)
    states_response[0]["state"]["on"] = True
    states_response[0]["state"]["rotationSpeed"] = 40
    with patch(
        "menuai.components.freedompro.coordinator.get_states",
        return_value=states_response,
    ):
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=2))
        await menuai.async_block_till_done()

    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state.attributes[ATTR_PERCENTAGE] == 40
    assert state.state == STATE_ON
