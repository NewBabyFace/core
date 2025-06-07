"""Test smarttub setup process."""

from unittest.mock import patch

from smarttub import LoginFailed

from menuai.components.smarttub.const import DOMAIN
from menuai.config_entries import SOURCE_REAUTH, ConfigEntryState
from menuai.core import menuai
from menuai.setup import async_setup_component


async def test_setup_with_no_config(
    setup_component, menuai: menuai, smarttub_api
) -> None:
    """Test that we do not discover anything."""

    # No flows started
    assert len(menuai.config_entries.flow.async_progress()) == 0

    smarttub_api.login.assert_not_called()


async def test_setup_entry_not_ready(
    setup_component, menuai: menuai, config_entry, smarttub_api
) -> None:
    """Test setup when the entry is not ready."""
    smarttub_api.login.side_effect = TimeoutError

    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_auth_failed(
    setup_component, menuai: menuai, config_entry, smarttub_api
) -> None:
    """Test setup when the credentials are invalid."""
    smarttub_api.login.side_effect = LoginFailed

    config_entry.add_to_menuai(menuai)
    with patch.object(menuai.config_entries.flow, "async_init") as mock_flow_init:
        await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        assert config_entry.state is ConfigEntryState.SETUP_ERROR
        mock_flow_init.assert_called_with(
            DOMAIN,
            context={
                "source": SOURCE_REAUTH,
                "entry_id": config_entry.entry_id,
                "unique_id": config_entry.unique_id,
                "title_placeholders": {"name": config_entry.title},
            },
            data=config_entry.data,
        )


async def test_config_passed_to_config_entry(
    menuai: menuai, config_entry, config_data
) -> None:
    """Test that configured options are loaded via config entry."""
    config_entry.add_to_menuai(menuai)
    assert await async_setup_component(menuai, DOMAIN, config_data)


async def test_unload_entry(menuai: menuai, config_entry) -> None:
    """Test being able to unload an entry."""
    config_entry.add_to_menuai(menuai)

    assert await async_setup_component(menuai, DOMAIN, {}) is True

    assert await menuai.config_entries.async_unload(config_entry.entry_id)
