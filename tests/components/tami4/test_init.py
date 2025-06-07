"""Test the Tami4 component."""

import pytest
from Tami4EdgeAPI import exceptions

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from .conftest import create_config_entry


async def test_init_success(mock_api, menuai: menuai) -> None:
    """Test setup and that we can create the entry."""

    entry = await create_config_entry(menuai)
    assert entry.state is ConfigEntryState.LOADED


@pytest.mark.parametrize(
    "mock_get_device", [exceptions.APIRequestFailedException], indirect=True
)
async def test_init_with_api_error(mock_api, menuai: menuai) -> None:
    """Test init with api error."""

    entry = await create_config_entry(menuai)
    assert entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.parametrize(
    ("mock__get_devices_metadata", "expected_state"),
    [
        (
            exceptions.RefreshTokenExpiredException,
            ConfigEntryState.SETUP_ERROR,
        ),
        (
            exceptions.TokenRefreshFailedException,
            ConfigEntryState.SETUP_RETRY,
        ),
    ],
    indirect=["mock__get_devices_metadata"],
)
async def test_init_error_raised(
    mock_api, menuai: menuai, expected_state: ConfigEntryState
) -> None:
    """Test init when an error is raised."""

    entry = await create_config_entry(menuai)
    assert entry.state == expected_state


async def test_load_unload(mock_api, menuai: menuai) -> None:
    """Config entry can be unloaded."""

    entry = await create_config_entry(menuai)

    await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
