"""Define tests for the generic (IP camera) integration."""

import pytest

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("fakeimg_png")
async def test_unload_entry(menuai: menuai, setup_entry: MockConfigEntry) -> None:
    """Test unloading the generic IP Camera entry."""
    assert setup_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(setup_entry.entry_id)
    await menuai.async_block_till_done()
    assert setup_entry.state is ConfigEntryState.NOT_LOADED


async def test_reload_on_title_change(
    menuai: menuai, setup_entry: MockConfigEntry
) -> None:
    """Test the integration gets reloaded when the title is updated."""
    assert setup_entry.state is ConfigEntryState.LOADED
    assert (
        menuai.states.get("camera.test_camera").attributes["friendly_name"]
        == "Test Camera"
    )

    menuai.config_entries.async_update_entry(setup_entry, title="New Title")
    assert setup_entry.title == "New Title"
    await menuai.async_block_till_done()

    assert (
        menuai.states.get("camera.test_camera").attributes["friendly_name"] == "New Title"
    )
