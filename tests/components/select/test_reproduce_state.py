"""Test reproduce state for select entities."""

import pytest

from menuai.components.select.const import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    DOMAIN,
    SERVICE_SELECT_OPTION,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai, State
from menuai.helpers.state import async_reproduce_state

from tests.common import async_mock_service


async def test_reproducing_states(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test reproducing select states."""
    calls = async_mock_service(menuai, DOMAIN, SERVICE_SELECT_OPTION)
    menuai.states.async_set(
        "select.test",
        "option_one",
        {ATTR_OPTIONS: ["option_one", "option_two", "option_three"]},
    )

    await async_reproduce_state(
        menuai,
        [
            State("select.test", "option_two"),
        ],
    )

    assert len(calls) == 1
    assert calls[0].domain == DOMAIN
    assert calls[0].data == {ATTR_ENTITY_ID: "select.test", ATTR_OPTION: "option_two"}

    # Calling it again should not do anything
    await async_reproduce_state(
        menuai,
        [
            State("select.test", "option_one"),
        ],
    )
    assert len(calls) == 1

    # Restoring an invalid state should not work either
    await async_reproduce_state(menuai, [State("select.test", "option_four")])
    assert len(calls) == 1
    assert "Invalid state specified" in caplog.text

    # Restoring an state for an invalid entity ID logs a warning
    await async_reproduce_state(menuai, [State("select.non_existing", "option_three")])
    assert len(calls) == 1
    assert "Unable to find entity" in caplog.text
