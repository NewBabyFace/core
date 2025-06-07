"""Unit tests for the OurGroceries integration."""

from unittest.mock import AsyncMock

import pytest

from menuai.components.ourgroceries import ClientError, InvalidLoginException
from menuai.components.ourgroceries.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_load_unload(
    menuai: menuai,
    setup_integration: None,
    ourgroceries_config_entry: MockConfigEntry | None,
) -> None:
    """Test loading and unloading of the config entry."""
    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1

    assert ourgroceries_config_entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(ourgroceries_config_entry.entry_id)
    assert ourgroceries_config_entry.state is ConfigEntryState.NOT_LOADED


@pytest.fixture
def login_with_error(exception, ourgroceries: AsyncMock):
    """Fixture to simulate error on login."""
    ourgroceries.login.side_effect = (exception,)


@pytest.mark.parametrize(
    ("exception", "status"),
    [
        (InvalidLoginException, ConfigEntryState.SETUP_ERROR),
        (ClientError, ConfigEntryState.SETUP_RETRY),
        (TimeoutError, ConfigEntryState.SETUP_RETRY),
    ],
)
async def test_init_failure(
    menuai: menuai,
    login_with_error,
    setup_integration: None,
    status: ConfigEntryState,
    ourgroceries_config_entry: MockConfigEntry | None,
) -> None:
    """Test an initialization error on integration load."""
    assert ourgroceries_config_entry.state == status
