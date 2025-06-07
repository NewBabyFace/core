"""Tests for the Freedompro switch."""

from datetime import timedelta
from unittest.mock import ANY, patch

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN, SERVICE_TURN_ON
from menuai.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.helpers.entity_component import async_update_entity
from menuai.util.dt import utcnow

from .conftest import get_states_response_for_uid

from tests.common import MockConfigEntry, async_fire_time_changed

uid = "3WRRJR6RCZQZSND8VP0YTO3YXCSOFPKBMW8T51TU-LQ*1JKU1MVWHQL-Z9SCUS85VFXMRGNDCDNDDUVVDKBU31W"


async def test_switch_get_state(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test states of the switch."""

    entity_id = "switch.irrigation_switch"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_OFF
    assert state.attributes.get("friendly_name") == "Irrigation switch"

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == uid

    states_response = get_states_response_for_uid(uid)
    states_response[0]["state"]["on"] = True
    with patch(
        "menuai.components.freedompro.coordinator.get_states",
        return_value=states_response,
    ):
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=2))
        await menuai.async_block_till_done()

        state = menuai.states.get(entity_id)
        assert state
        assert state.attributes.get("friendly_name") == "Irrigation switch"

        entry = entity_registry.async_get(entity_id)
        assert entry
        assert entry.unique_id == uid

        assert state.state == STATE_ON


async def test_switch_set_off(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test set off of the switch."""

    entity_id = "switch.irrigation_switch"

    states_response = get_states_response_for_uid(uid)
    states_response[0]["state"]["on"] = True
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
    assert state.attributes.get("friendly_name") == "Irrigation switch"

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == uid

    with patch(
        "menuai.components.freedompro.switch.put_state"
    ) as mock_put_state:
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
    mock_put_state.assert_called_once_with(ANY, ANY, ANY, '{"on": false}')

    states_response = get_states_response_for_uid(uid)
    states_response[0]["state"]["on"] = False
    with patch(
        "menuai.components.freedompro.coordinator.get_states",
        return_value=states_response,
    ):
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=2))
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == STATE_OFF


async def test_switch_set_on(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
) -> None:
    """Test set on of the switch."""

    entity_id = "switch.irrigation_switch"
    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_OFF
    assert state.attributes.get("friendly_name") == "Irrigation switch"

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.unique_id == uid

    with patch(
        "menuai.components.freedompro.switch.put_state"
    ) as mock_put_state:
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: [entity_id]},
            blocking=True,
        )
    mock_put_state.assert_called_once_with(ANY, ANY, ANY, '{"on": true}')

    states_response = get_states_response_for_uid(uid)
    states_response[0]["state"]["on"] = True
    with patch(
        "menuai.components.freedompro.coordinator.get_states",
        return_value=states_response,
    ):
        async_fire_time_changed(menuai, utcnow() + timedelta(hours=2))
        await menuai.async_block_till_done()

    state = menuai.states.get(entity_id)
    assert state.state == STATE_ON
