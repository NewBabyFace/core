"""Test squeezebox binary sensors."""

from copy import deepcopy
from unittest.mock import patch

from menuai.const import Platform
from menuai.core import menuai

from .conftest import FAKE_QUERY_RESPONSE

from tests.common import MockConfigEntry


async def test_binary_sensor(
    menuai: menuai,
    config_entry: MockConfigEntry,
) -> None:
    """Test binary sensor states and attributes."""
    with (
        patch(
            "menuai.components.squeezebox.PLATFORMS",
            [Platform.BINARY_SENSOR],
        ),
        patch(
            "menuai.components.squeezebox.Server.async_query",
            return_value=deepcopy(FAKE_QUERY_RESPONSE),
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get("binary_sensor.fakelib_needs_restart")

    assert state is not None
    assert state.state == "off"
