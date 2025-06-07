"""Test cases around the demo fan platform."""

from unittest.mock import patch

import pytest

from menuai.components import fan
from menuai.components.demo.fan import (
    PRESET_MODE_AUTO,
    PRESET_MODE_ON,
    PRESET_MODE_SLEEP,
    PRESET_MODE_SMART,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    ENTITY_MATCH_ALL,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    Platform,
)
from menuai.core import menuai
from menuai.setup import async_setup_component

FULL_FAN_ENTITY_IDS = ["fan.living_room_fan", "fan.percentage_full_fan"]
FANS_WITH_PRESET_MODE_ONLY = ["fan.preset_only_limited_fan"]
LIMITED_AND_FULL_FAN_ENTITY_IDS = [
    *FULL_FAN_ENTITY_IDS,
    "fan.ceiling_fan",
    "fan.percentage_limited_fan",
]
FANS_WITH_PRESET_MODES = [*FULL_FAN_ENTITY_IDS, "fan.percentage_limited_fan"]
PERCENTAGE_MODEL_FANS = ["fan.percentage_full_fan", "fan.percentage_limited_fan"]


@pytest.fixture
async def fan_only() -> None:
    """Enable only the datetime platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.FAN],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_comp(menuai: menuai, fan_only: None):
    """Initialize components."""
    assert await async_setup_component(menuai, fan.DOMAIN, {"fan": {"platform": "demo"}})
    await menuai.async_block_till_done()


@pytest.mark.parametrize("fan_entity_id", LIMITED_AND_FULL_FAN_ENTITY_IDS)
async def test_turn_on(menuai: menuai, fan_entity_id) -> None:
    """Test turning on the device."""
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await menuai.services.async_call(
        fan.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_ON


@pytest.mark.parametrize("fan_entity_id", FULL_FAN_ENTITY_IDS)
async def test_turn_on_with_speed_and_percentage(
    menuai: menuai, fan_entity_id
) -> None:
    """Test turning on the device."""
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    await menuai.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 100},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 100

    await menuai.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 66},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 66

    await menuai.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 33},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 33

    await menuai.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 100},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 100

    await menuai.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 66},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 66

    await menuai.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 33},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 33

    await menuai.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 0},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[fan.ATTR_PERCENTAGE] == 0


@pytest.mark.parametrize("fan_entity_id", FANS_WITH_PRESET_MODE_ONLY)
async def test_turn_on_with_preset_mode_only(
    menuai: menuai, fan_entity_id
) -> None:
    """Test turning on the device with a preset_mode and no speed setting."""
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    await menuai.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: PRESET_MODE_AUTO},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PRESET_MODE] == PRESET_MODE_AUTO
    assert state.attributes[fan.ATTR_PRESET_MODES] == [
        PRESET_MODE_AUTO,
        PRESET_MODE_SMART,
        PRESET_MODE_SLEEP,
        PRESET_MODE_ON,
    ]

    await menuai.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: PRESET_MODE_SMART},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PRESET_MODE] == PRESET_MODE_SMART

    await menuai.services.async_call(
        fan.DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[fan.ATTR_PRESET_MODE] is None

    with pytest.raises(fan.NotValidPresetModeError) as exc:
        await menuai.services.async_call(
            fan.DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: "invalid"},
            blocking=True,
        )
    assert exc.value.translation_domain == fan.DOMAIN
    assert exc.value.translation_key == "not_valid_preset_mode"
    assert exc.value.translation_placeholders == {
        "preset_mode": "invalid",
        "preset_modes": "auto, smart, sleep, on",
    }

    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[fan.ATTR_PRESET_MODE] is None


@pytest.mark.parametrize("fan_entity_id", FANS_WITH_PRESET_MODES)
async def test_turn_on_with_preset_mode_and_speed(
    menuai: menuai, fan_entity_id
) -> None:
    """Test turning on the device with a preset_mode and speed."""
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    await menuai.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: PRESET_MODE_AUTO},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] is None
    assert state.attributes[fan.ATTR_PRESET_MODE] == PRESET_MODE_AUTO
    assert state.attributes[fan.ATTR_PRESET_MODES] == [
        PRESET_MODE_AUTO,
        PRESET_MODE_SMART,
        PRESET_MODE_SLEEP,
        PRESET_MODE_ON,
    ]

    await menuai.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 100},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] == 100
    assert state.attributes[fan.ATTR_PRESET_MODE] is None

    await menuai.services.async_call(
        fan.DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: PRESET_MODE_SMART},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] is None
    assert state.attributes[fan.ATTR_PRESET_MODE] == PRESET_MODE_SMART

    await menuai.services.async_call(
        fan.DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[fan.ATTR_PERCENTAGE] == 0
    assert state.attributes[fan.ATTR_PRESET_MODE] is None

    with pytest.raises(fan.NotValidPresetModeError) as exc:
        await menuai.services.async_call(
            fan.DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: "invalid"},
            blocking=True,
        )
    assert exc.value.translation_domain == fan.DOMAIN
    assert exc.value.translation_key == "not_valid_preset_mode"
    assert exc.value.translation_placeholders == {
        "preset_mode": "invalid",
        "preset_modes": "auto, smart, sleep, on",
    }

    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[fan.ATTR_PERCENTAGE] == 0
    assert state.attributes[fan.ATTR_PRESET_MODE] is None


@pytest.mark.parametrize("fan_entity_id", LIMITED_AND_FULL_FAN_ENTITY_IDS)
async def test_turn_off(menuai: menuai, fan_entity_id) -> None:
    """Test turning off the device."""
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await menuai.services.async_call(
        fan.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_ON

    await menuai.services.async_call(
        fan.DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF


@pytest.mark.parametrize("fan_entity_id", LIMITED_AND_FULL_FAN_ENTITY_IDS)
async def test_turn_off_without_entity_id(menuai: menuai, fan_entity_id) -> None:
    """Test turning off all fans."""
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await menuai.services.async_call(
        fan.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_ON

    await menuai.services.async_call(
        fan.DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: ENTITY_MATCH_ALL}, blocking=True
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF


@pytest.mark.parametrize("fan_entity_id", FULL_FAN_ENTITY_IDS)
async def test_set_direction(menuai: menuai, fan_entity_id) -> None:
    """Test setting the direction of the device."""
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_SET_DIRECTION,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_DIRECTION: fan.DIRECTION_REVERSE},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_DIRECTION] == fan.DIRECTION_REVERSE


@pytest.mark.parametrize("fan_entity_id", FANS_WITH_PRESET_MODES)
async def test_set_preset_mode(menuai: menuai, fan_entity_id) -> None:
    """Test setting the preset mode of the device."""
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: PRESET_MODE_AUTO},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_ON
    assert state.attributes[fan.ATTR_PERCENTAGE] is None
    assert state.attributes[fan.ATTR_PRESET_MODE] == PRESET_MODE_AUTO


@pytest.mark.parametrize("fan_entity_id", LIMITED_AND_FULL_FAN_ENTITY_IDS)
async def test_set_preset_mode_invalid(menuai: menuai, fan_entity_id) -> None:
    """Test setting a invalid preset mode for the device."""
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    with pytest.raises(fan.NotValidPresetModeError) as exc:
        await menuai.services.async_call(
            fan.DOMAIN,
            fan.SERVICE_SET_PRESET_MODE,
            {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: "invalid"},
            blocking=True,
        )
    assert exc.value.translation_domain == fan.DOMAIN
    assert exc.value.translation_key == "not_valid_preset_mode"

    with pytest.raises(fan.NotValidPresetModeError) as exc:
        await menuai.services.async_call(
            fan.DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PRESET_MODE: "invalid"},
            blocking=True,
        )
    assert exc.value.translation_domain == fan.DOMAIN
    assert exc.value.translation_key == "not_valid_preset_mode"


@pytest.mark.parametrize("fan_entity_id", FULL_FAN_ENTITY_IDS)
async def test_set_percentage(menuai: menuai, fan_entity_id) -> None:
    """Test setting the percentage speed of the device."""
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_SET_PERCENTAGE,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE: 33},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 33


@pytest.mark.parametrize("fan_entity_id", LIMITED_AND_FULL_FAN_ENTITY_IDS)
async def test_increase_decrease_speed(menuai: menuai, fan_entity_id) -> None:
    """Test increasing and decreasing the percentage speed of the device."""
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert state.attributes[fan.ATTR_PERCENTAGE_STEP] == 100 / 3

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_INCREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 33

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_INCREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 66

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_INCREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 100

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_INCREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 100

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_DECREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 66

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_DECREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 33

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_DECREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 0

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_DECREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 0


@pytest.mark.parametrize("fan_entity_id", PERCENTAGE_MODEL_FANS)
async def test_increase_decrease_speed_with_percentage_step(
    menuai: menuai, fan_entity_id
) -> None:
    """Test increasing speed with a percentage step."""
    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_INCREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE_STEP: 25},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 25

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_INCREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE_STEP: 25},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 50

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_INCREASE_SPEED,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_PERCENTAGE_STEP: 25},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_PERCENTAGE] == 75


@pytest.mark.parametrize("fan_entity_id", FULL_FAN_ENTITY_IDS)
async def test_oscillate(menuai: menuai, fan_entity_id) -> None:
    """Test oscillating the fan."""
    state = menuai.states.get(fan_entity_id)
    assert state.state == STATE_OFF
    assert not state.attributes.get(fan.ATTR_OSCILLATING)

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_OSCILLATE,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_OSCILLATING: True},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_OSCILLATING] is True

    await menuai.services.async_call(
        fan.DOMAIN,
        fan.SERVICE_OSCILLATE,
        {ATTR_ENTITY_ID: fan_entity_id, fan.ATTR_OSCILLATING: False},
        blocking=True,
    )
    state = menuai.states.get(fan_entity_id)
    assert state.attributes[fan.ATTR_OSCILLATING] is False


@pytest.mark.parametrize("fan_entity_id", LIMITED_AND_FULL_FAN_ENTITY_IDS)
async def test_is_on(menuai: menuai, fan_entity_id) -> None:
    """Test is on service call."""
    assert not fan.is_on(menuai, fan_entity_id)

    await menuai.services.async_call(
        fan.DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: fan_entity_id}, blocking=True
    )
    assert fan.is_on(menuai, fan_entity_id)
