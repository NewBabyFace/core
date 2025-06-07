"""Tests for the Filesize integration."""

from pathlib import Path

from menuai.components.filesize.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_FILE_PATH
from menuai.core import menuai

from . import async_create_file

from tests.common import MockConfigEntry


async def test_load_unload_config_entry(
    menuai: menuai, mock_config_entry: MockConfigEntry, tmp_path: Path
) -> None:
    """Test the Filesize configuration entry loading/unloading."""
    testfile = str(tmp_path.joinpath("file.txt"))
    await async_create_file(menuai, testfile)
    menuai.config.allowlist_external_dirs = {tmp_path}
    mock_config_entry.add_to_menuai(menuai)
    menuai.config_entries.async_update_entry(
        mock_config_entry, unique_id=testfile, data={CONF_FILE_PATH: testfile}
    )
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert not menuai.data.get(DOMAIN)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_cannot_access_file(
    menuai: menuai, mock_config_entry: MockConfigEntry, tmp_path: Path
) -> None:
    """Test that an file not exist is caught."""
    mock_config_entry.add_to_menuai(menuai)
    testfile = str(tmp_path.joinpath("file_not_exist.txt"))
    menuai.config.allowlist_external_dirs = {tmp_path}
    menuai.config_entries.async_update_entry(
        mock_config_entry, unique_id=testfile, data={CONF_FILE_PATH: testfile}
    )

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_not_valid_path_to_file(
    menuai: menuai, mock_config_entry: MockConfigEntry, tmp_path: Path
) -> None:
    """Test that an invalid path is caught."""
    testfile = str(tmp_path.joinpath("file.txt"))
    await async_create_file(menuai, testfile)
    mock_config_entry.add_to_menuai(menuai)
    menuai.config_entries.async_update_entry(
        mock_config_entry, unique_id=testfile, data={CONF_FILE_PATH: testfile}
    )

    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY
