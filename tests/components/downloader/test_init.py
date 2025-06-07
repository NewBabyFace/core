"""Tests for the downloader component init."""

from unittest.mock import patch

from menuai.components.downloader.const import (
    CONF_DOWNLOAD_DIR,
    DOMAIN,
    SERVICE_DOWNLOAD_FILE,
)
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_initialization(menuai: menuai) -> None:
    """Test the initialization of the downloader component."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_DOWNLOAD_DIR: "/test_dir",
        },
    )
    config_entry.add_to_menuai(menuai)
    with patch("os.path.isdir", return_value=True):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)

    assert menuai.services.has_service(DOMAIN, SERVICE_DOWNLOAD_FILE)
    assert config_entry.state is ConfigEntryState.LOADED
