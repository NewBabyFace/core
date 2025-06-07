"""The tests for the Demo component."""

from collections.abc import Generator
import json
from unittest.mock import patch

import pytest

from menuai.components.demo import DOMAIN
from menuai.core import menuai
from menuai.helpers.json import JSONEncoder
from menuai.setup import async_setup_component


@pytest.fixture
def mock_history(menuai: menuai) -> None:
    """Mock history component loaded."""
    menuai.config.components.add("history")


@pytest.fixture(autouse=True)
def mock_device_tracker_update_config() -> Generator[None]:
    """Prevent device tracker from creating known devices file."""
    with patch("menuai.components.device_tracker.legacy.update_config"):
        yield


async def test_setting_up_demo(mock_history: None, menuai: menuai) -> None:
    """Test if we can set up the demo and dump it to JSON."""
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()
    await menuai.async_start()

    # This is done to make sure entity components don't accidentally store
    # non-JSON-serializable data in the state machine.
    try:
        json.dumps(menuai.states.async_all(), cls=JSONEncoder)
    except Exception:  # noqa: BLE001
        pytest.fail(
            "Unable to convert all demo entities to JSON. Wrong data in state machine!"
        )
