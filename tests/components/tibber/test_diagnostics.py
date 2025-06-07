"""Test the Netatmo diagnostics."""

from unittest.mock import patch

from menuai.components.recorder import Recorder
from menuai.core import menuai
from menuai.setup import async_setup_component

from .test_common import mock_get_homes

from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_entry_diagnostics(
    recorder_mock: Recorder,
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    config_entry,
) -> None:
    """Test config entry diagnostics."""
    with patch(
        "tibber.Tibber.update_info",
        return_value=None,
    ):
        assert await async_setup_component(menuai, "tibber", {})

    await menuai.async_block_till_done()

    with patch(
        "tibber.Tibber.get_homes",
        return_value=[],
    ):
        result = await get_diagnostics_for_config_entry(menuai, menuai_client, config_entry)

    assert result == {
        "homes": [],
    }

    with patch(
        "tibber.Tibber.get_homes",
        side_effect=mock_get_homes,
    ):
        result = await get_diagnostics_for_config_entry(menuai, menuai_client, config_entry)

    assert result == {
        "homes": [
            {
                "last_data_timestamp": "2016-01-01T12:48:57",
                "has_active_subscription": True,
                "has_real_time_consumption": False,
                "last_cons_data_timestamp": "2016-01-01T12:44:57",
                "country": "NO",
            }
        ],
    }
