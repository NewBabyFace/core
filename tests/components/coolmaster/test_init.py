"""The test for the Coolmaster integration."""

from menuai.config_entries import ConfigEntry, ConfigEntryState
from menuai.core import menuai


async def test_load_entry(
    menuai: menuai,
    load_int: ConfigEntry,
) -> None:
    """Test Coolmaster initial load."""
    # 2 units times 4 entities (climate, binary_sensor, sensor, button).
    assert menuai.states.async_entity_ids_count() == 8
    assert load_int.state is ConfigEntryState.LOADED


async def test_unload_entry(
    menuai: menuai,
    load_int: ConfigEntry,
) -> None:
    """Test Coolmaster unloading an entry."""
    await menuai.config_entries.async_unload(load_int.entry_id)
    await menuai.async_block_till_done()
    assert load_int.state is ConfigEntryState.NOT_LOADED
