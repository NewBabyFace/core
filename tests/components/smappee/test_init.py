"""Tests for the Smappee component init module."""

from unittest.mock import patch

from menuai.components.smappee.const import DOMAIN
from menuai.config_entries import SOURCE_ZEROCONF
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_unload_config_entry(menuai: menuai) -> None:
    """Test unload config entry flow."""
    with (
        patch("pysmappee.api.SmappeeLocalApi.logon", return_value={}),
        patch(
            "pysmappee.api.SmappeeLocalApi.load_advanced_config",
            return_value=[{"key": "mdnsHostName", "value": "Smappee1006000212"}],
        ),
        patch(
            "pysmappee.api.SmappeeLocalApi.load_command_control_config", return_value=[]
        ),
        patch(
            "pysmappee.api.SmappeeLocalApi.load_instantaneous",
            return_value=[{"key": "phase0ActivePower", "value": 0}],
        ),
    ):
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={"host": "1.2.3.4"},
            unique_id="smappee1006000212",
            source=SOURCE_ZEROCONF,
        )
        config_entry.add_to_menuai(menuai)
        assert len(menuai.config_entries.async_entries(DOMAIN)) == 1

        entry = menuai.config_entries.async_entries(DOMAIN)[0]
        await menuai.config_entries.async_unload(entry.entry_id)
        await menuai.async_block_till_done()
        assert not menuai.data.get(DOMAIN)
