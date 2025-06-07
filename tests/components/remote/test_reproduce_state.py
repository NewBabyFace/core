"""Test reproduce state for Remote."""

import pytest

from menuai.core import menuai, State
from menuai.helpers.state import async_reproduce_state

from tests.common import async_mock_service


async def test_reproducing_states(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test reproducing Remote states."""
    menuai.states.async_set("remote.entity_off", "off", {})
    menuai.states.async_set("remote.entity_on", "on", {})

    turn_on_calls = async_mock_service(menuai, "remote", "turn_on")
    turn_off_calls = async_mock_service(menuai, "remote", "turn_off")

    # These calls should do nothing as entities already in desired state
    await async_reproduce_state(
        menuai,
        [State("remote.entity_off", "off"), State("remote.entity_on", "on")],
    )

    assert len(turn_on_calls) == 0
    assert len(turn_off_calls) == 0

    # Test invalid state is handled
    await async_reproduce_state(menuai, [State("remote.entity_off", "not_supported")])

    assert "not_supported" in caplog.text
    assert len(turn_on_calls) == 0
    assert len(turn_off_calls) == 0

    # Make sure correct services are called
    await async_reproduce_state(
        menuai,
        [
            State("remote.entity_on", "off"),
            State("remote.entity_off", "on", {}),
            # Should not raise
            State("remote.non_existing", "on"),
        ],
    )

    assert len(turn_on_calls) == 1
    assert turn_on_calls[0].domain == "remote"
    assert turn_on_calls[0].data == {
        "entity_id": "remote.entity_off",
    }

    assert len(turn_off_calls) == 1
    assert turn_off_calls[0].domain == "remote"
    assert turn_off_calls[0].data == {"entity_id": "remote.entity_on"}
