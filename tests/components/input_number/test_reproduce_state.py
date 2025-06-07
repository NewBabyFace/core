"""Test reproduce state for Input number."""

import pytest

from menuai.core import menuai, State
from menuai.helpers.state import async_reproduce_state
from menuai.setup import async_setup_component

VALID_NUMBER1 = "19.0"
VALID_NUMBER2 = "99.9"


async def test_reproducing_states(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test reproducing Input number states."""

    assert await async_setup_component(
        menuai,
        "input_number",
        {
            "input_number": {
                "test_number": {"min": "5", "max": "100", "initial": VALID_NUMBER1}
            }
        },
    )

    # These calls should do nothing as entities already in desired state
    await async_reproduce_state(
        menuai,
        [
            State("input_number.test_number", VALID_NUMBER1),
            # Should not raise
            State("input_number.non_existing", "234"),
        ],
    )

    assert menuai.states.get("input_number.test_number").state == VALID_NUMBER1

    # Test reproducing with different state
    await async_reproduce_state(
        menuai,
        [
            State("input_number.test_number", VALID_NUMBER2),
            # Should not raise
            State("input_number.non_existing", "234"),
        ],
    )

    assert menuai.states.get("input_number.test_number").state == VALID_NUMBER2

    # Test setting state to number out of range
    await async_reproduce_state(menuai, [State("input_number.test_number", "150")])

    # The entity states should be unchanged after trying to set them to out-of-range number
    assert menuai.states.get("input_number.test_number").state == VALID_NUMBER2

    await async_reproduce_state(
        menuai,
        [
            # Test invalid state
            State("input_number.test_number", "invalid_state"),
            # Set to state it already is.
            State("input_number.test_number", VALID_NUMBER2),
        ],
    )
