"""Test flux_led diagnostics."""

from menuai.components.flux_led.const import DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from . import (
    _mock_config_entry_for_bulb,
    _mocked_bulb,
    _patch_discovery,
    _patch_wifibulb,
)

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> None:
    """Test generating diagnostics for a config entry."""
    entry = _mock_config_entry_for_bulb(menuai)
    bulb = _mocked_bulb()
    with _patch_discovery(), _patch_wifibulb(device=bulb):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
        await menuai.async_block_till_done()
    diag = await get_diagnostics_for_config_entry(menuai, menuai_client, entry)
    assert diag == {
        "data": {"mock_diag": "mock_diag"},
        "entry": {
            "data": {
                "host": "127.0.0.1",
                "minor_version": 4,
                "model": "AK001-ZJ2149",
                "model_description": "Bulb RGBCW",
                "model_info": "AK001-ZJ2149",
                "model_num": 53,
                "name": "Bulb RGBCW DDEEFF",
                "remote_access_enabled": True,
                "remote_access_host": "the.cloud",
                "remote_access_port": 8816,
            },
            "title": "Mock Title",
        },
    }
