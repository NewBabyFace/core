"""Tests for the epson integration."""

from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory

from menuai.components.epson.const import CONF_CONNECTION_TYPE, DOMAIN, HTTP
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_set_unique_id(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the unique id is set on runtime."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Epson",
        data={CONF_CONNECTION_TYPE: HTTP, CONF_HOST: "1.1.1.1"},
        entry_id="1cb78c095906279574a0442a1f0003ef",
    )
    entry.add_to_menuai(menuai)
    with patch("menuai.components.epson.Projector.get_power"):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
        assert entry.unique_id is None
        entity_entry = entity_registry.async_get("media_player.epson")
        assert entity_entry
        assert entity_entry.unique_id == entry.entry_id
    with (
        patch("menuai.components.epson.Projector.get_power", return_value="01"),
        patch(
            "menuai.components.epson.Projector.get_serial_number",
            return_value="123",
        ),
        patch(
            "menuai.components.epson.Projector.get_property",
        ),
    ):
        freezer.tick(timedelta(seconds=30))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()
        entity_entry = entity_registry.async_get("media_player.epson")
        assert entity_entry
        assert entity_entry.unique_id == "123"
        assert entry.unique_id == "123"
