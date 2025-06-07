"""Tests for the Nextcloud integration."""

from unittest.mock import Mock, patch

from menuai.components.nextcloud.const import DOMAIN
from menuai.const import CONF_URL
from menuai.core import menuai

from .const import MOCKED_ENTRY_ID

from tests.common import MockConfigEntry


def mock_config_entry(config: dict) -> MockConfigEntry:
    """Return a mocked config entry."""
    return MockConfigEntry(
        domain=DOMAIN, title=config[CONF_URL], data=config, entry_id=MOCKED_ENTRY_ID
    )


async def init_integration(
    menuai: menuai, config: dict, data: dict
) -> MockConfigEntry:
    """Set up the nextcloud integration."""
    entry = mock_config_entry(config)
    entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.nextcloud.NextcloudMonitor",
        ) as mock_nextcloud_monitor,
    ):
        mock_nextcloud_monitor.update = Mock(return_value=True)
        mock_nextcloud_monitor.return_value.data = data
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    return entry
