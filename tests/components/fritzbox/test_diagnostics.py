"""Tests for the AVM Fritz!Box integration."""

from __future__ import annotations

from unittest.mock import Mock

from menuai.components.diagnostics import REDACTED
from menuai.components.fritzbox.const import DOMAIN
from menuai.components.fritzbox.diagnostics import TO_REDACT
from menuai.const import CONF_DEVICES
from menuai.core import menuai

from . import setup_config_entry
from .const import MOCK_CONFIG

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai, menuai_client: ClientSessionGenerator, fritz: Mock
) -> None:
    """Test config entry diagnostics."""
    assert await setup_config_entry(menuai, MOCK_CONFIG[DOMAIN][CONF_DEVICES][0])

    entries = menuai.config_entries.async_entries(DOMAIN)
    entry_dict = entries[0].as_dict()
    for key in TO_REDACT:
        entry_dict["data"][key] = REDACTED

    result = await get_diagnostics_for_config_entry(menuai, menuai_client, entries[0])

    assert result == {"entry": entry_dict | {"discovery_keys": {}}, "data": {}}
