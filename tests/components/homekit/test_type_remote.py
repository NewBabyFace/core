"""Test different accessory types: Remotes."""

from unittest.mock import patch

import pytest

from menuai.components.homekit.accessories import HomeDriver
from menuai.components.homekit.const import (
    ATTR_KEY_NAME,
    ATTR_VALUE,
    EVENT_HOMEKIT_TV_REMOTE_KEY_PRESSED,
    KEY_ARROW_RIGHT,
)
from menuai.components.homekit.type_remotes import ActivityRemote
from menuai.components.remote import (
    ATTR_ACTIVITY,
    ATTR_ACTIVITY_LIST,
    ATTR_CURRENT_ACTIVITY,
    DOMAIN as REMOTE_DOMAIN,
    RemoteEntityFeature,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    STATE_OFF,
    STATE_ON,
    STATE_STANDBY,
)
from menuai.core import Event, menuai

from tests.common import async_mock_service


async def test_activity_remote(
    menuai: menuai, hk_driver: HomeDriver, events: list[Event]
) -> None:
    """Test if remote accessory and HA are updated accordingly."""
    entity_id = "remote.harmony"
    base_attrs = {
        ATTR_SUPPORTED_FEATURES: RemoteEntityFeature.ACTIVITY,
        ATTR_CURRENT_ACTIVITY: "Apple TV",
        ATTR_ACTIVITY_LIST: ["TV", "Apple TV"],
    }
    menuai.states.async_set(
        entity_id,
        None,
        base_attrs,
    )
    await menuai.async_block_till_done()
    acc = ActivityRemote(menuai, hk_driver, "ActivityRemote", entity_id, 2, None)
    acc.run()
    await menuai.async_block_till_done()

    assert acc.aid == 2
    assert acc.category == 31  # Television

    assert acc.char_active.value == 0
    assert acc.char_remote_key.value == 0
    assert acc.char_input_source.value == 1

    menuai.states.async_set(
        entity_id,
        STATE_ON,
        base_attrs,
    )
    await menuai.async_block_till_done()
    assert acc.char_active.value == 1

    menuai.states.async_set(entity_id, STATE_OFF, base_attrs)
    await menuai.async_block_till_done()
    assert acc.char_active.value == 0

    menuai.states.async_set(entity_id, STATE_ON, base_attrs)
    await menuai.async_block_till_done()
    assert acc.char_active.value == 1

    menuai.states.async_set(entity_id, STATE_STANDBY, base_attrs)
    await menuai.async_block_till_done()
    assert acc.char_active.value == 0

    menuai.states.async_set(
        entity_id, STATE_ON, {**base_attrs, ATTR_CURRENT_ACTIVITY: "TV"}
    )
    await menuai.async_block_till_done()
    assert acc.char_input_source.value == 0

    menuai.states.async_set(
        entity_id, STATE_ON, {**base_attrs, ATTR_CURRENT_ACTIVITY: "Apple TV"}
    )
    await menuai.async_block_till_done()
    assert acc.char_input_source.value == 1

    # Set from HomeKit
    call_turn_on = async_mock_service(menuai, REMOTE_DOMAIN, "turn_on")
    call_turn_off = async_mock_service(menuai, REMOTE_DOMAIN, "turn_off")

    acc.char_active.client_update_value(1)
    await menuai.async_block_till_done()
    assert call_turn_on
    assert call_turn_on[0].data[ATTR_ENTITY_ID] == entity_id
    assert len(events) == 1
    assert events[-1].data[ATTR_VALUE] is None

    acc.char_active.client_update_value(0)
    await menuai.async_block_till_done()
    assert call_turn_off
    assert call_turn_off[0].data[ATTR_ENTITY_ID] == entity_id
    assert len(events) == 2
    assert events[-1].data[ATTR_VALUE] is None

    acc.char_input_source.client_update_value(1)
    await menuai.async_block_till_done()
    assert call_turn_on
    assert call_turn_on[1].data[ATTR_ENTITY_ID] == entity_id
    assert call_turn_on[1].data[ATTR_ACTIVITY] == "Apple TV"
    assert len(events) == 3
    assert events[-1].data[ATTR_VALUE] is None

    acc.char_input_source.client_update_value(0)
    await menuai.async_block_till_done()
    assert call_turn_on
    assert call_turn_on[2].data[ATTR_ENTITY_ID] == entity_id
    assert call_turn_on[2].data[ATTR_ACTIVITY] == "TV"
    assert len(events) == 4
    assert events[-1].data[ATTR_VALUE] is None

    events = []

    def listener(event):
        events.append(event)

    menuai.bus.async_listen(EVENT_HOMEKIT_TV_REMOTE_KEY_PRESSED, listener)

    with pytest.raises(ValueError):
        acc.char_remote_key.client_update_value(20)

    acc.char_remote_key.client_update_value(7)
    await menuai.async_block_till_done()

    assert len(events) == 1
    assert events[0].data[ATTR_KEY_NAME] == KEY_ARROW_RIGHT

    # A wild source appears - The accessory should reload itself
    with patch.object(acc, "async_reload") as mock_reload:
        menuai.states.async_set(
            entity_id,
            STATE_ON,
            {
                **base_attrs,
                ATTR_CURRENT_ACTIVITY: "Amazon TV",
                ATTR_ACTIVITY_LIST: ["TV", "Apple TV", "Amazon TV"],
            },
        )
        await menuai.async_block_till_done()
        assert mock_reload.called


async def test_activity_remote_bad_names(
    menuai: menuai,
    hk_driver,
    events: list[Event],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test if remote accessory with invalid names works as expected."""
    entity_id = "remote.harmony"
    menuai.states.async_set(
        entity_id,
        None,
        {
            ATTR_SUPPORTED_FEATURES: RemoteEntityFeature.ACTIVITY,
            ATTR_CURRENT_ACTIVITY: "Apple TV",
            ATTR_ACTIVITY_LIST: ["TV", "Apple TV", "[[[--Special--]]]", "Super"],
        },
    )
    await menuai.async_block_till_done()
    acc = ActivityRemote(menuai, hk_driver, "ActivityRemote", entity_id, 2, None)
    acc.run()
    await menuai.async_block_till_done()

    assert acc.aid == 2
    assert acc.category == 31  # Television

    assert acc.char_active.value == 0
    assert acc.char_remote_key.value == 0
    assert acc.char_input_source.value == 1

    menuai.states.async_set(
        entity_id,
        STATE_ON,
        {
            ATTR_SUPPORTED_FEATURES: RemoteEntityFeature.ACTIVITY,
            ATTR_CURRENT_ACTIVITY: "[[[--Special--]]]",
            ATTR_ACTIVITY_LIST: ["TV", "Apple TV", "[[[--Special--]]]", "Super"],
        },
    )
    await menuai.async_block_till_done()
    assert acc.char_active.value == 1
    assert acc.char_input_source.value == 2
