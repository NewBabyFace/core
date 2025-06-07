"""The tests for the text component."""

from typing import Any

import pytest

from menuai.components.text import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_MODE,
    ATTR_PATTERN,
    ATTR_VALUE,
    DOMAIN,
    SERVICE_SET_VALUE,
    TextMode,
    _async_set_value,
)
from menuai.const import MAX_LENGTH_STATE_STATE
from menuai.core import menuai, ServiceCall, State
from menuai.helpers.restore_state import STORAGE_KEY as RESTORE_STATE_KEY
from menuai.setup import async_setup_component

from .common import MockRestoreText, MockTextEntity

from tests.common import (
    async_mock_restore_state_shutdown_restart,
    mock_restore_cache_with_extra_data,
    setup_test_component_platform,
)


async def test_text_default(menuai: menuai) -> None:
    """Test text entity with defaults."""
    text = MockTextEntity()
    text.menuai = menuai

    assert text.capability_attributes == {
        ATTR_MIN: 0,
        ATTR_MAX: MAX_LENGTH_STATE_STATE,
        ATTR_MODE: TextMode.TEXT,
        ATTR_PATTERN: None,
    }
    assert text.pattern is None
    assert text.state == "test"


async def test_text_new_min_max_pattern(menuai: menuai) -> None:
    """Test text entity with new min, max, and pattern."""
    text = MockTextEntity(native_min=-1, native_max=500, pattern=r"[a-z]")
    text.menuai = menuai

    assert text.capability_attributes == {
        ATTR_MIN: 0,
        ATTR_MAX: MAX_LENGTH_STATE_STATE,
        ATTR_MODE: TextMode.TEXT,
        ATTR_PATTERN: r"[a-z]",
    }


async def test_text_set_value(menuai: menuai) -> None:
    """Test text entity with set_value service."""
    text = MockTextEntity(native_min=1, native_max=5, pattern=r"[a-z]")
    text.menuai = menuai

    with pytest.raises(ValueError):
        await _async_set_value(
            text, ServiceCall(menuai, DOMAIN, SERVICE_SET_VALUE, {ATTR_VALUE: ""})
        )

    with pytest.raises(ValueError):
        await _async_set_value(
            text,
            ServiceCall(menuai, DOMAIN, SERVICE_SET_VALUE, {ATTR_VALUE: "hello world!"}),
        )

    with pytest.raises(ValueError):
        await _async_set_value(
            text, ServiceCall(menuai, DOMAIN, SERVICE_SET_VALUE, {ATTR_VALUE: "HELLO"})
        )

    await _async_set_value(
        text, ServiceCall(menuai, DOMAIN, SERVICE_SET_VALUE, {ATTR_VALUE: "test2"})
    )

    assert text.state == "test2"


async def test_text_value_outside_bounds(menuai: menuai) -> None:
    """Test text entity with value that is outside min and max."""
    with pytest.raises(ValueError):
        _ = MockTextEntity(
            "hello world", native_min=2, native_max=5, pattern=r"[a-z]"
        ).state
    with pytest.raises(ValueError):
        _ = MockTextEntity(
            "hello world", native_min=15, native_max=20, pattern=r"[a-z]"
        ).state


RESTORE_DATA = {
    "native_max": 5,
    "native_min": 1,
    # "mode": TextMode.TEXT,
    # "pattern": r"[A-Za-z0-9]",
    "native_value": "Hello",
}


async def test_restore_number_save_state(
    menuai: menuai,
    menuai_storage: dict[str, Any],
) -> None:
    """Test RestoreNumber."""
    entity0 = MockRestoreText(
        name="Test",
        native_max=5,
        native_min=1,
        native_value="Hello",
    )
    setup_test_component_platform(menuai, DOMAIN, [entity0])

    assert await async_setup_component(menuai, "text", {"text": {"platform": "test"}})
    await menuai.async_block_till_done()

    # Trigger saving state
    await async_mock_restore_state_shutdown_restart(menuai)

    assert len(menuai_storage[RESTORE_STATE_KEY]["data"]) == 1
    state = menuai_storage[RESTORE_STATE_KEY]["data"][0]["state"]
    assert state["entity_id"] == entity0.entity_id
    extra_data = menuai_storage[RESTORE_STATE_KEY]["data"][0]["extra_data"]
    assert extra_data == RESTORE_DATA
    assert isinstance(extra_data["native_value"], str)


@pytest.mark.parametrize(
    ("native_max", "native_min", "native_value", "native_value_type", "extra_data"),
    [
        (5, 1, "Hello", str, RESTORE_DATA),
        (255, 1, None, type(None), None),
        (255, 1, None, type(None), {}),
        (255, 1, None, type(None), {"beer": 123}),
        (255, 1, None, type(None), {"native_value": {}}),
    ],
)
async def test_restore_number_restore_state(
    menuai: menuai,
    menuai_storage: dict[str, Any],
    native_max,
    native_min,
    native_value,
    native_value_type,
    extra_data,
) -> None:
    """Test RestoreNumber."""
    mock_restore_cache_with_extra_data(menuai, ((State("text.test", ""), extra_data),))

    entity0 = MockRestoreText(
        native_max=native_max,
        native_min=native_min,
        name="Test",
        native_value=None,
    )
    setup_test_component_platform(menuai, DOMAIN, [entity0])

    assert await async_setup_component(menuai, "text", {"text": {"platform": "test"}})
    await menuai.async_block_till_done()

    assert menuai.states.get(entity0.entity_id)

    assert entity0.native_max == native_max
    assert entity0.native_min == native_min
    assert entity0.mode == TextMode.TEXT
    assert entity0.pattern is None
    assert entity0.native_value == native_value
    assert isinstance(entity0.native_value, native_value_type)
