"""Test the BraviaTV diagnostics."""

from unittest.mock import patch

from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from menuai.components.braviatv.const import CONF_USE_PSK, DOMAIN
from menuai.const import CONF_HOST, CONF_MAC, CONF_PIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator

BRAVIA_SYSTEM_INFO = {
    "product": "TV",
    "region": "XEU",
    "language": "pol",
    "model": "TV-Model",
    "serial": "serial_number",
    "macAddr": "AA:BB:CC:DD:EE:FF",
    "name": "BRAVIA",
    "generation": "5.2.0",
    "area": "POL",
    "cid": "very_unique_string",
}
INPUTS = [
    {
        "uri": "extInput:hdmi?port=1",
        "title": "HDMI 1",
        "connection": False,
        "label": "",
        "icon": "meta:hdmi",
    }
]


async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "localhost",
            CONF_MAC: "AA:BB:CC:DD:EE:FF",
            CONF_USE_PSK: True,
            CONF_PIN: "12345qwerty",
        },
        unique_id="very_unique_string",
        entry_id="3bd2acb0e4f0476d40865546d0d91921",
    )

    config_entry.add_to_menuai(menuai)
    with (
        patch("pybravia.BraviaClient.connect"),
        patch("pybravia.BraviaClient.pair"),
        patch("pybravia.BraviaClient.set_wol_mode"),
        patch("pybravia.BraviaClient.get_system_info", return_value=BRAVIA_SYSTEM_INFO),
        patch("pybravia.BraviaClient.get_power_status", return_value="active"),
        patch("pybravia.BraviaClient.get_external_status", return_value=INPUTS),
        patch("pybravia.BraviaClient.get_volume_info", return_value={}),
        patch("pybravia.BraviaClient.get_playing_info", return_value={}),
        patch("pybravia.BraviaClient.get_app_list", return_value=[]),
        patch("pybravia.BraviaClient.get_content_list_all", return_value=[]),
    ):
        assert await async_setup_component(menuai, DOMAIN, {})
        result = await get_diagnostics_for_config_entry(menuai, menuai_client, config_entry)

    assert result == snapshot(exclude=props("created_at", "modified_at"))
