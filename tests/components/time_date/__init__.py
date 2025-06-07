"""Tests for the time_date component."""

from menuai.components.time_date.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_DISPLAY_OPTIONS
from menuai.core import menuai

from tests.common import MockConfigEntry


async def load_int(
    menuai: menuai, display_option: str | None = None
) -> MockConfigEntry:
    """Set up the Time & Date integration in MenuAI."""
    if display_option is None:
        display_option = "time"
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data={},
        options={CONF_DISPLAY_OPTIONS: display_option},
        entry_id=f"1234567890_{display_option}",
    )

    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    return config_entry
