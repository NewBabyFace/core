"""Test reproduce state for Lock."""

import pytest

from menuai.core import menuai, State
from menuai.helpers.state import async_reproduce_state

from tests.common import async_mock_service


async def test_reproducing_states(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test reproducing Lock states."""
    menuai.states.async_set("lock.entity_locked", "locked", {})
    menuai.states.async_set("lock.entity_unlocked", "unlocked", {})
    menuai.states.async_set("lock.entity_opened", "open", {})

    lock_calls = async_mock_service(menuai, "lock", "lock")
    unlock_calls = async_mock_service(menuai, "lock", "unlock")
    open_calls = async_mock_service(menuai, "lock", "open")

    # These calls should do nothing as entities already in desired state
    await async_reproduce_state(
        menuai,
        [
            State("lock.entity_locked", "locked"),
            State("lock.entity_unlocked", "unlocked", {}),
            State("lock.entity_opened", "open", {}),
        ],
    )

    assert len(lock_calls) == 0
    assert len(unlock_calls) == 0
    assert len(open_calls) == 0

    # Test invalid state is handled
    await async_reproduce_state(menuai, [State("lock.entity_locked", "not_supported")])

    assert "not_supported" in caplog.text
    assert len(lock_calls) == 0
    assert len(unlock_calls) == 0
    assert len(open_calls) == 0

    # Make sure correct services are called
    await async_reproduce_state(
        menuai,
        [
            State("lock.entity_locked", "open"),
            State("lock.entity_unlocked", "locked"),
            State("lock.entity_opened", "unlocked"),
            # Should not raise
            State("lock.non_existing", "on"),
        ],
    )

    assert len(lock_calls) == 1
    assert lock_calls[0].domain == "lock"
    assert lock_calls[0].data == {"entity_id": "lock.entity_unlocked"}

    assert len(unlock_calls) == 1
    assert unlock_calls[0].domain == "lock"
    assert unlock_calls[0].data == {"entity_id": "lock.entity_opened"}

    assert len(open_calls) == 1
    assert open_calls[0].domain == "lock"
    assert open_calls[0].data == {"entity_id": "lock.entity_locked"}
