"""Tests for the Sense integration."""

from unittest.mock import patch

from menuai.components.sense.const import DOMAIN
from menuai.const import Platform
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


async def setup_platform(
    menuai: menuai, config_entry: MockConfigEntry, platform: Platform
) -> MockConfigEntry:
    """Set up the Sense platform."""
    config_entry.add_to_menuai(menuai)

    with patch("menuai.components.sense.PLATFORMS", [platform]):
        assert await async_setup_component(menuai, DOMAIN, {})
    await menuai.async_block_till_done()

    return config_entry
