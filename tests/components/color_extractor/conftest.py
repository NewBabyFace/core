"""Common fixtures for the Color extractor tests."""

import pytest

from menuai.components.color_extractor.const import DOMAIN
from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.fixture
async def config_entry() -> MockConfigEntry:
    """Mock config entry."""
    return MockConfigEntry(domain=DOMAIN, data={})


@pytest.fixture
async def setup_integration(menuai: menuai, config_entry: MockConfigEntry) -> None:
    """Add config entry for color extractor."""
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
