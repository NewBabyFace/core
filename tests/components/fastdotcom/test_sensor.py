"""Test the FastdotcomDataUpdateCoordindator."""

from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory

from menuai.components.fastdotcom.const import DEFAULT_NAME, DOMAIN
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_fastdotcom_data_update_coordinator(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test the update coordinator."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="UNIQUE_TEST_ID",
        title=DEFAULT_NAME,
    )
    config_entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.fastdotcom.coordinator.fast_com", return_value=5.0
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.fast_com_download")
    assert state is not None
    assert state.state == "5.0"
