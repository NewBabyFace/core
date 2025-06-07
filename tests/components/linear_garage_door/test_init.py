"""Test Linear Garage Door init."""

from unittest.mock import AsyncMock

from linear_garage_door import InvalidLoginError
import pytest

from menuai.components.linear_garage_door.const import DOMAIN
from menuai.config_entries import (
    SOURCE_IGNORE,
    ConfigEntryDisabler,
    ConfigEntryState,
)
from menuai.const import CONF_EMAIL, CONF_PASSWORD
from menuai.core import menuai
from menuai.helpers import issue_registry as ir

from . import setup_integration

from tests.common import MockConfigEntry


async def test_unload_entry(
    menuai: menuai, mock_linear: AsyncMock, mock_config_entry: MockConfigEntry
) -> None:
    """Test the unload entry."""

    await setup_integration(menuai, mock_config_entry, [])
    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize(
    ("side_effect", "entry_state"),
    [
        (
            InvalidLoginError(
                "Login provided is invalid, please check the email and password"
            ),
            ConfigEntryState.SETUP_ERROR,
        ),
        (InvalidLoginError("Invalid login"), ConfigEntryState.SETUP_RETRY),
    ],
)
async def test_setup_failure(
    menuai: menuai,
    mock_linear: AsyncMock,
    mock_config_entry: MockConfigEntry,
    side_effect: Exception,
    entry_state: ConfigEntryState,
) -> None:
    """Test reauth trigger setup."""

    mock_linear.login.side_effect = side_effect

    await setup_integration(menuai, mock_config_entry, [])
    assert mock_config_entry.state == entry_state


async def test_repair_issue(
    menuai: menuai,
    mock_linear: AsyncMock,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test the Linear Garage Door configuration entry loading/unloading handles the repair."""
    config_entry_1 = MockConfigEntry(
        domain=DOMAIN,
        entry_id="acefdd4b3a4a0911067d1cf51414201e",
        title="test-site-name",
        data={
            CONF_EMAIL: "test-email",
            CONF_PASSWORD: "test-password",
            "site_id": "test-site-id",
            "device_id": "test-uuid",
        },
    )
    await setup_integration(menuai, config_entry_1, [])
    assert config_entry_1.state is ConfigEntryState.LOADED

    # Add a second one
    config_entry_2 = MockConfigEntry(
        domain=DOMAIN,
        entry_id="acefdd4b3a4a0911067d1cf51414201f",
        title="test-site-name",
        data={
            CONF_EMAIL: "test-email",
            CONF_PASSWORD: "test-password",
            "site_id": "test-site-id",
            "device_id": "test-uuid",
        },
    )
    await setup_integration(menuai, config_entry_2, [])
    assert config_entry_2.state is ConfigEntryState.LOADED
    assert issue_registry.async_get_issue(DOMAIN, DOMAIN)

    # Add an ignored entry
    config_entry_3 = MockConfigEntry(
        source=SOURCE_IGNORE,
        domain=DOMAIN,
    )
    config_entry_3.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry_3.entry_id)
    await menuai.async_block_till_done()

    assert config_entry_3.state is ConfigEntryState.NOT_LOADED

    # Add a disabled entry
    config_entry_4 = MockConfigEntry(
        disabled_by=ConfigEntryDisabler.USER,
        domain=DOMAIN,
    )
    config_entry_4.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry_4.entry_id)
    await menuai.async_block_till_done()

    assert config_entry_4.state is ConfigEntryState.NOT_LOADED

    # Remove the first one
    await menuai.config_entries.async_remove(config_entry_1.entry_id)
    await menuai.async_block_till_done()
    assert config_entry_1.state is ConfigEntryState.NOT_LOADED
    assert config_entry_2.state is ConfigEntryState.LOADED
    assert issue_registry.async_get_issue(DOMAIN, DOMAIN)
    # Remove the second one
    await menuai.config_entries.async_remove(config_entry_2.entry_id)
    await menuai.async_block_till_done()
    assert config_entry_1.state is ConfigEntryState.NOT_LOADED
    assert config_entry_2.state is ConfigEntryState.NOT_LOADED
    assert issue_registry.async_get_issue(DOMAIN, DOMAIN) is None

    # Check the ignored and disabled entries are removed
    assert not menuai.config_entries.async_entries(DOMAIN)
