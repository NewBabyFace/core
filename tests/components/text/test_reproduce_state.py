"""Test reproduce state for Text entities."""

import pytest

from menuai.components.text.const import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_MODE,
    ATTR_PATTERN,
    DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.core import menuai, State
from menuai.helpers.state import async_reproduce_state

from tests.common import async_mock_service

VALID_TEXT1 = "Hello"
VALID_TEXT2 = "World"


async def test_reproducing_states(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test reproducing Text states."""

    menuai.states.async_set(
        "text.test_text",
        VALID_TEXT1,
        {ATTR_MIN: 1, ATTR_MAX: 5, ATTR_MODE: "text", ATTR_PATTERN: None},
    )

    # These calls should do nothing as entities already in desired state
    await async_reproduce_state(
        menuai,
        [
            State("text.test_text", VALID_TEXT1),
            # Should not raise
            State("text.non_existing", "234"),
        ],
    )

    assert menuai.states.get("text.test_text").state == VALID_TEXT1

    # Test reproducing with different state
    calls = async_mock_service(menuai, DOMAIN, SERVICE_SET_VALUE)
    await async_reproduce_state(
        menuai,
        [
            State("text.test_text", VALID_TEXT2),
            # Should not raise
            State("text.non_existing", "234"),
        ],
    )

    assert len(calls) == 1
    assert calls[0].domain == DOMAIN
    assert calls[0].data == {"entity_id": "text.test_text", "value": VALID_TEXT2}
