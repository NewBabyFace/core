"""Tests for the awair component."""

from unittest.mock import patch

from menuai.components.awair.const import DOMAIN
from menuai.config_entries import ConfigEntry
from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_awair(menuai: menuai, fixtures, unique_id, data) -> ConfigEntry:
    """Add Awair devices to menuai, using specified fixtures for data."""

    entry = MockConfigEntry(domain=DOMAIN, unique_id=unique_id, data=data)
    with patch("python_awair.AwairClient.query", side_effect=fixtures):
        entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    return entry
