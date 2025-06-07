"""Tests for the diagnostics data provided by the Google Assistant SDK integration."""

from freezegun import freeze_time
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.google_assistant_sdk.const import CONF_LANGUAGE_CODE
from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


@pytest.fixture(autouse=True)
def freeze_the_time():
    """Freeze the time."""
    with freeze_time("2024-05-30 12:00:00", tz_offset=0):
        yield


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test diagnostics."""
    config_entry.add_to_menuai(menuai)
    menuai.config_entries.async_update_entry(
        config_entry,
        options={CONF_LANGUAGE_CODE: "en-US"},
    )
    await menuai.config_entries.async_setup(config_entry.entry_id)
    assert (
        await get_diagnostics_for_config_entry(menuai, menuai_client, config_entry)
        == snapshot
    )
