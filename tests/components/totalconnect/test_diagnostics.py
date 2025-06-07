"""Test TotalConnect diagnostics."""

from menuai.components.diagnostics import REDACTED
from menuai.core import menuai

from .common import LOCATION_ID, init_integration

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> None:
    """Test config entry diagnostics."""
    entry = await init_integration(menuai)

    result = await get_diagnostics_for_config_entry(menuai, menuai_client, entry)

    client = result["client"]
    assert client["invalid_credentials"] is False

    user = result["user"]
    assert user["master"] is False

    location = result["locations"][0]
    assert location["location_id"] == LOCATION_ID

    device = location["devices"][0]
    assert device["serial_number"] == REDACTED

    partition = location["partitions"][0]
    assert partition["name"] == "Test1"

    zone = location["zones"][0]
    assert zone["zone_id"] == "1"
