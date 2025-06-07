"""Test Brottsplatskartan component setup process."""

from __future__ import annotations

from unittest.mock import patch

from menuai.components.brottsplatskartan.const import DOMAIN
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_load_unload_entry(menuai: menuai) -> None:
    """Test load and unload entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "latitude": menuai.config.latitude,
            "longitude": menuai.config.longitude,
            "area": None,
            "app_id": "ha-1234567890",
        },
        title="BPK-HOME",
    )
    entry.add_to_menuai(menuai)
    with patch(
        "menuai.components.brottsplatskartan.sensor.BrottsplatsKartan",
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.bpk_home")
    assert state

    await menuai.config_entries.async_remove(entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.bpk_home")
    assert not state
