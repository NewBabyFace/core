"""Tests for the samsungtv component."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from menuai.components.samsungtv.const import DOMAIN, METHOD_LEGACY
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_METHOD
from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_samsungtv_entry(
    menuai: menuai, data: Mapping[str, Any]
) -> ConfigEntry:
    """Set up mock Samsung TV from config entry data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        entry_id="123456",
        unique_id=(
            None
            if data[CONF_METHOD] == METHOD_LEGACY
            else "be9554b9-c9fb-41f4-8920-22da015376a4"
        ),
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    return entry
