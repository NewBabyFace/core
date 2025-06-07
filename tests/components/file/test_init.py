"""The tests for local file init."""

from unittest.mock import MagicMock, Mock, patch

from menuai.components.file import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry, get_fixture_path


@patch("os.path.isfile", Mock(return_value=True))
@patch("os.access", Mock(return_value=True))
async def test_migration_to_version_2(
    menuai: menuai, mock_is_allowed_path: MagicMock
) -> None:
    """Test the File sensor with JSON entries."""
    data = {
        "platform": "sensor",
        "name": "file2",
        "file_path": get_fixture_path("file_value_template.txt", "file"),
        "value_template": "{{ value_json.temperature }}",
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data=data,
        title=f"test [{data['file_path']}]",
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.LOADED
    assert entry.version == 2
    assert entry.data == {
        "platform": "sensor",
        "name": "file2",
        "file_path": get_fixture_path("file_value_template.txt", "file"),
    }
    assert entry.options == {
        "value_template": "{{ value_json.temperature }}",
    }


@patch("os.path.isfile", Mock(return_value=True))
@patch("os.access", Mock(return_value=True))
async def test_migration_from_future_version(
    menuai: menuai, mock_is_allowed_path: MagicMock
) -> None:
    """Test the File sensor with JSON entries."""
    data = {
        "platform": "sensor",
        "name": "file2",
        "file_path": get_fixture_path("file_value_template.txt", "file"),
        "value_template": "{{ value_json.temperature }}",
    }

    entry = MockConfigEntry(
        domain=DOMAIN, version=3, data=data, title=f"test [{data['file_path']}]"
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.MIGRATION_ERROR
