"""Test DROP select entities."""

from menuai.components.select import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai

from .common import (
    TEST_DATA_HUB,
    TEST_DATA_HUB_RESET,
    TEST_DATA_HUB_TOPIC,
    config_entry_hub,
)

from tests.common import async_fire_mqtt_message
from tests.typing import MqttMockHAClient


async def test_selects_hub(menuai: menuai, mqtt_mock: MqttMockHAClient) -> None:
    """Test DROP binary sensors for hubs."""
    entry = config_entry_hub()
    entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(entry.entry_id)

    protect_mode_select_name = "select.hub_drop_1_c0ffee_protect_mode"
    protect_mode_select = menuai.states.get(protect_mode_select_name)
    assert protect_mode_select
    assert protect_mode_select.attributes.get(ATTR_OPTIONS) == [
        "away",
        "home",
        "schedule",
    ]

    async_fire_mqtt_message(menuai, TEST_DATA_HUB_TOPIC, TEST_DATA_HUB_RESET)
    await menuai.async_block_till_done()
    protect_mode_select = menuai.states.get(protect_mode_select_name)
    assert protect_mode_select
    assert protect_mode_select.attributes.get(ATTR_OPTIONS) == [
        "away",
        "home",
        "schedule",
    ]

    async_fire_mqtt_message(menuai, TEST_DATA_HUB_TOPIC, TEST_DATA_HUB)
    await menuai.async_block_till_done()

    protect_mode_select = menuai.states.get(protect_mode_select_name)
    assert protect_mode_select
    assert protect_mode_select.state == "home"

    mqtt_mock.async_publish.reset_mock()
    await menuai.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_OPTION: "away", ATTR_ENTITY_ID: protect_mode_select_name},
        blocking=True,
    )
    await menuai.async_block_till_done()
    assert len(mqtt_mock.async_publish.mock_calls) == 1

    # Simulate response of the device
    async_fire_mqtt_message(menuai, TEST_DATA_HUB_TOPIC, TEST_DATA_HUB_RESET)
    await menuai.async_block_till_done()

    protect_mode_select = menuai.states.get(protect_mode_select_name)
    assert protect_mode_select
    assert protect_mode_select.state == "away"
