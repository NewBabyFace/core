"""Test Environment Canada diagnostics."""

from typing import Any

from syrupy.assertion import SnapshotAssertion

from menuai.components.environment_canada.const import CONF_STATION
from menuai.const import CONF_LANGUAGE, CONF_LATITUDE, CONF_LONGITUDE
from menuai.core import menuai

from . import init_integration

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator

FIXTURE_USER_INPUT = {
    CONF_LATITUDE: 55.55,
    CONF_LONGITUDE: 42.42,
    CONF_STATION: "XX/1234567",
    CONF_LANGUAGE: "Gibberish",
}


async def test_entry_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    snapshot: SnapshotAssertion,
    ec_data: dict[str, Any],
) -> None:
    """Test config entry diagnostics."""

    config_entry = await init_integration(menuai, ec_data)
    diagnostics = await get_diagnostics_for_config_entry(
        menuai, menuai_client, config_entry
    )

    assert diagnostics == snapshot
