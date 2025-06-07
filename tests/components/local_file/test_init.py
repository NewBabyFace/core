"""Test Statistics component setup process."""

from __future__ import annotations

from unittest.mock import Mock, patch

from menuai.components.local_file.const import DOMAIN
from menuai.config_entries import SOURCE_USER, ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_unload_entry(menuai: menuai, loaded_entry: MockConfigEntry) -> None:
    """Test unload an entry."""

    assert loaded_entry.state is ConfigEntryState.LOADED
    assert await menuai.config_entries.async_unload(loaded_entry.entry_id)
    await menuai.async_block_till_done()
    assert loaded_entry.state is ConfigEntryState.NOT_LOADED


async def test_file_not_readable_during_startup(
    menuai: menuai,
    get_config: dict[str, str],
) -> None:
    """Test a warning is shown setup when file is not readable."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        options=get_config,
        entry_id="1",
    )
    config_entry.add_to_menuai(menuai)

    with (
        patch("os.path.isfile", Mock(return_value=True)),
        patch("os.access", Mock(return_value=False)),
        patch(
            "menuai.components.local_file.camera.mimetypes.guess_type",
            Mock(return_value=(None, None)),
        ),
    ):
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
