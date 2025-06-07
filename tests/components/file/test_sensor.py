"""The tests for local file sensor platform."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from menuai.components.file import DOMAIN
from menuai.const import STATE_UNKNOWN
from menuai.core import menuai

from tests.common import MockConfigEntry, get_fixture_path


@patch("os.path.isfile", Mock(return_value=True))
@patch("os.access", Mock(return_value=True))
async def test_file_value_entry_setup(
    menuai: menuai, mock_is_allowed_path: MagicMock
) -> None:
    """Test the File sensor from an entry setup."""
    data = {
        "platform": "sensor",
        "name": "file1",
        "file_path": get_fixture_path("file_value.txt", "file"),
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        version=2,
        options={},
        title=f"test [{data['file_path']}]",
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)

    state = menuai.states.get("sensor.file1")
    assert state.state == "21"


@patch("os.path.isfile", Mock(return_value=True))
@patch("os.access", Mock(return_value=True))
async def test_file_value_template(
    menuai: menuai, mock_is_allowed_path: MagicMock
) -> None:
    """Test the File sensor with JSON entries."""
    data = {
        "platform": "sensor",
        "name": "file2",
        "file_path": get_fixture_path("file_value_template.txt", "file"),
    }
    options = {
        "value_template": "{{ value_json.temperature }}",
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        version=2,
        options=options,
        title=f"test [{data['file_path']}]",
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)

    state = menuai.states.get("sensor.file2")
    assert state.state == "26"


@patch("os.path.isfile", Mock(return_value=True))
@patch("os.access", Mock(return_value=True))
async def test_file_empty(menuai: menuai, mock_is_allowed_path: MagicMock) -> None:
    """Test the File sensor with an empty file."""
    data = {
        "platform": "sensor",
        "name": "file3",
        "file_path": get_fixture_path("file_empty.txt", "file"),
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        version=2,
        options={},
        title=f"test [{data['file_path']}]",
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)

    state = menuai.states.get("sensor.file3")
    assert state.state == STATE_UNKNOWN


@patch("os.path.isfile", Mock(return_value=True))
@patch("os.access", Mock(return_value=True))
@pytest.mark.parametrize("is_allowed", [False])
async def test_file_path_invalid(
    menuai: menuai, mock_is_allowed_path: MagicMock
) -> None:
    """Test the File sensor with invalid path."""
    data = {
        "platform": "sensor",
        "name": "file4",
        "file_path": get_fixture_path("file_value.txt", "file"),
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        version=2,
        options={},
        title=f"test [{data['file_path']}]",
    )
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)

    assert len(menuai.states.async_entity_ids("sensor")) == 0
