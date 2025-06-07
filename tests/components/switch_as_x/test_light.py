"""Tests for the Switch as X Light platform."""

from menuai.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_MODE,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_EFFECT_LIST,
    ATTR_HS_COLOR,
    ATTR_SUPPORTED_COLOR_MODES,
    DOMAIN as LIGHT_DOMAIN,
    ColorMode,
)
from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.components.switch_as_x.config_flow import SwitchAsXConfigFlowHandler
from menuai.components.switch_as_x.const import (
    CONF_INVERT,
    CONF_TARGET_DOMAIN,
    DOMAIN,
)
from menuai.const import (
    CONF_ENTITY_ID,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    Platform,
)
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


async def test_default_state(menuai: menuai) -> None:
    """Test light switch default state."""
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            CONF_ENTITY_ID: "switch.test",
            CONF_INVERT: False,
            CONF_TARGET_DOMAIN: Platform.LIGHT,
        },
        title="Christmas Tree Lights",
        version=SwitchAsXConfigFlowHandler.VERSION,
        minor_version=SwitchAsXConfigFlowHandler.MINOR_VERSION,
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get("light.christmas_tree_lights")
    assert state is not None
    assert state.state == "unavailable"
    assert state.attributes["supported_features"] == 0
    assert state.attributes.get(ATTR_BRIGHTNESS) is None
    assert state.attributes.get(ATTR_HS_COLOR) is None
    assert state.attributes.get(ATTR_COLOR_TEMP_KELVIN) is None
    assert state.attributes.get(ATTR_EFFECT_LIST) is None
    assert state.attributes.get(ATTR_EFFECT) is None
    assert state.attributes.get(ATTR_SUPPORTED_COLOR_MODES) == [ColorMode.ONOFF]
    assert state.attributes.get(ATTR_COLOR_MODE) is None


async def test_light_service_calls(menuai: menuai) -> None:
    """Test service calls to light."""
    await async_setup_component(menuai, "switch", {"switch": [{"platform": "demo"}]})
    await menuai.async_block_till_done()
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            CONF_ENTITY_ID: "switch.decorative_lights",
            CONF_INVERT: False,
            CONF_TARGET_DOMAIN: Platform.LIGHT,
        },
        title="decorative_lights",
        version=SwitchAsXConfigFlowHandler.VERSION,
        minor_version=SwitchAsXConfigFlowHandler.MINOR_VERSION,
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.states.get("light.decorative_lights").state == STATE_ON

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TOGGLE,
        {CONF_ENTITY_ID: "light.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_OFF
    assert menuai.states.get("light.decorative_lights").state == STATE_OFF

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {CONF_ENTITY_ID: "light.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_ON
    assert menuai.states.get("light.decorative_lights").state == STATE_ON
    assert (
        menuai.states.get("light.decorative_lights").attributes.get(ATTR_COLOR_MODE)
        == ColorMode.ONOFF
    )

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_OFF,
        {CONF_ENTITY_ID: "light.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_OFF
    assert menuai.states.get("light.decorative_lights").state == STATE_OFF


async def test_switch_service_calls(menuai: menuai) -> None:
    """Test service calls to switch."""
    await async_setup_component(menuai, "switch", {"switch": [{"platform": "demo"}]})
    await menuai.async_block_till_done()
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            CONF_ENTITY_ID: "switch.decorative_lights",
            CONF_INVERT: False,
            CONF_TARGET_DOMAIN: Platform.LIGHT,
        },
        title="Title is ignored",
        version=SwitchAsXConfigFlowHandler.VERSION,
        minor_version=SwitchAsXConfigFlowHandler.MINOR_VERSION,
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.states.get("light.decorative_lights").state == STATE_ON

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {CONF_ENTITY_ID: "switch.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_OFF
    assert menuai.states.get("light.decorative_lights").state == STATE_OFF

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {CONF_ENTITY_ID: "switch.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_ON
    assert menuai.states.get("light.decorative_lights").state == STATE_ON


async def test_light_service_calls_inverted(menuai: menuai) -> None:
    """Test service calls to light."""
    await async_setup_component(menuai, "switch", {"switch": [{"platform": "demo"}]})
    await menuai.async_block_till_done()
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            CONF_ENTITY_ID: "switch.decorative_lights",
            CONF_INVERT: True,
            CONF_TARGET_DOMAIN: Platform.LIGHT,
        },
        title="decorative_lights",
        version=SwitchAsXConfigFlowHandler.VERSION,
        minor_version=SwitchAsXConfigFlowHandler.MINOR_VERSION,
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.states.get("light.decorative_lights").state == STATE_ON

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TOGGLE,
        {CONF_ENTITY_ID: "light.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_OFF
    assert menuai.states.get("light.decorative_lights").state == STATE_OFF

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_ON,
        {CONF_ENTITY_ID: "light.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_ON
    assert menuai.states.get("light.decorative_lights").state == STATE_ON
    assert (
        menuai.states.get("light.decorative_lights").attributes.get(ATTR_COLOR_MODE)
        == ColorMode.ONOFF
    )

    await menuai.services.async_call(
        LIGHT_DOMAIN,
        SERVICE_TURN_OFF,
        {CONF_ENTITY_ID: "light.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_OFF
    assert menuai.states.get("light.decorative_lights").state == STATE_OFF


async def test_switch_service_calls_inverted(menuai: menuai) -> None:
    """Test service calls to switch."""
    await async_setup_component(menuai, "switch", {"switch": [{"platform": "demo"}]})
    await menuai.async_block_till_done()
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            CONF_ENTITY_ID: "switch.decorative_lights",
            CONF_INVERT: True,
            CONF_TARGET_DOMAIN: Platform.LIGHT,
        },
        title="Title is ignored",
        version=SwitchAsXConfigFlowHandler.VERSION,
        minor_version=SwitchAsXConfigFlowHandler.MINOR_VERSION,
    )
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.states.get("light.decorative_lights").state == STATE_ON

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {CONF_ENTITY_ID: "switch.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_OFF
    assert menuai.states.get("light.decorative_lights").state == STATE_OFF

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {CONF_ENTITY_ID: "switch.decorative_lights"},
        blocking=True,
    )

    assert menuai.states.get("switch.decorative_lights").state == STATE_ON
    assert menuai.states.get("light.decorative_lights").state == STATE_ON
