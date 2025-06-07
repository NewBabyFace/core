"""Test reproduce state for input boolean."""

from menuai.core import menuai, State
from menuai.helpers.state import async_reproduce_state
from menuai.setup import async_setup_component


async def test_reproducing_states(menuai: menuai) -> None:
    """Test reproducing input_boolean states."""
    assert await async_setup_component(
        menuai,
        "input_boolean",
        {
            "input_boolean": {
                "initial_on": {"initial": True},
                "initial_off": {"initial": False},
            }
        },
    )
    await async_reproduce_state(
        menuai,
        [
            State("input_boolean.initial_on", "off"),
            State("input_boolean.initial_off", "on"),
            # Should not raise
            State("input_boolean.non_existing", "on"),
        ],
    )
    assert menuai.states.get("input_boolean.initial_off").state == "on"
    assert menuai.states.get("input_boolean.initial_on").state == "off"

    await async_reproduce_state(
        menuai,
        [
            # Test invalid state
            State("input_boolean.initial_on", "invalid_state"),
            # Set to state it already is.
            State("input_boolean.initial_off", "on"),
        ],
    )

    assert menuai.states.get("input_boolean.initial_on").state == "off"
    assert menuai.states.get("input_boolean.initial_off").state == "on"
