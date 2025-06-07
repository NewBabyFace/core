"""The tests for the Time & Date component."""

from menuai.core import menuai

from . import load_int


async def test_setup_and_remove_config_entry(menuai: menuai) -> None:
    """Test setting up and removing a config entry."""
    entry = await load_int(menuai)

    state = menuai.states.get("sensor.time")
    assert state is not None

    assert await menuai.config_entries.async_remove(entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.states.get("sensor.time") is None
