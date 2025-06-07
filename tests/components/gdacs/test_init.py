"""Define tests for the GDACS general setup."""

from unittest.mock import patch

from menuai.core import menuai


async def test_component_unload_config_entry(menuai: menuai, config_entry) -> None:
    """Test that loading and unloading of a config entry works."""
    config_entry.add_to_menuai(menuai)
    with patch("aio_georss_gdacs.GdacsFeedManager.update") as mock_feed_manager_update:
        # Load config entry.
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        assert mock_feed_manager_update.call_count == 1

        # Unload config entry.
        assert await menuai.config_entries.async_unload(config_entry.entry_id)
        await menuai.async_block_till_done()
