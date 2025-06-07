"""The tests for the demo text component."""

from collections.abc import Generator
from unittest.mock import patch

import pytest

from menuai.components.text import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_PATTERN,
    ATTR_VALUE,
    DOMAIN as TEXT_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.const import (
    ATTR_ENTITY_ID,
    ATTR_MODE,
    MAX_LENGTH_STATE_STATE,
    Platform,
)
from menuai.core import menuai
from menuai.setup import async_setup_component

ENTITY_TEXT = "text.text"


@pytest.fixture
def text_only() -> Generator[None]:
    """Enable only the text platform."""
    with patch(
        "menuai.components.demo.COMPONENTS_WITH_CONFIG_ENTRY_DEMO_PLATFORM",
        [Platform.TEXT],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_demo_text(menuai: menuai, text_only: None) -> None:
    """Initialize setup demo text."""
    assert await async_setup_component(
        menuai, TEXT_DOMAIN, {"text": {"platform": "demo"}}
    )
    await menuai.async_block_till_done()


def test_setup_params(menuai: menuai) -> None:
    """Test the initial parameters."""
    state = menuai.states.get(ENTITY_TEXT)
    assert state.state == "Hello world"
    assert state.attributes[ATTR_MIN] == 0
    assert state.attributes[ATTR_MAX] == MAX_LENGTH_STATE_STATE
    assert state.attributes[ATTR_PATTERN] is None
    assert state.attributes[ATTR_MODE] == "text"


async def test_set_value(menuai: menuai) -> None:
    """Test set value service."""
    await menuai.services.async_call(
        TEXT_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: ENTITY_TEXT, ATTR_VALUE: "new"},
        blocking=True,
    )
    state = menuai.states.get(ENTITY_TEXT)
    assert state.state == "new"
