"""Tests for the Nettigo Air Monitor integration."""

from unittest.mock import AsyncMock, Mock, patch

from menuai.components.nam.const import DOMAIN
from menuai.core import menuai

from tests.common import MockConfigEntry, async_load_json_object_fixture

INCOMPLETE_NAM_DATA = {
    "software_version": "NAMF-2020-36",
    "sensordatavalues": [],
}


async def init_integration(
    menuai: menuai, co2_sensor: bool = True
) -> MockConfigEntry:
    """Set up the Nettigo Air Monitor integration in MenuAI."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="10.10.2.3",
        unique_id="aa:bb:cc:dd:ee:ff",
        data={"host": "10.10.2.3"},
    )

    nam_data = await async_load_json_object_fixture(menuai, "nam_data.json", DOMAIN)

    if not co2_sensor:
        # Remove conc_co2_ppm value
        nam_data["sensordatavalues"].pop(6)

    update_response = Mock(json=AsyncMock(return_value=nam_data))

    with (
        patch("menuai.components.nam.NettigoAirMonitor.initialize"),
        patch(
            "menuai.components.nam.NettigoAirMonitor._async_http_request",
            return_value=update_response,
        ),
    ):
        entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    return entry
