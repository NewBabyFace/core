"""Tests for the Abode module."""

from http import HTTPStatus
from unittest.mock import patch

from jaraco.abode.exceptions import (
    AuthenticationException as AbodeAuthenticationException,
    Exception as AbodeException,
)

from menuai.components.abode.const import DOMAIN
from menuai.components.abode.services import SERVICE_SETTINGS
from menuai.components.alarm_control_panel import DOMAIN as ALARM_DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_USERNAME
from menuai.core import menuai

from .common import setup_platform


async def test_change_settings(menuai: menuai) -> None:
    """Test change_setting service."""
    await setup_platform(menuai, ALARM_DOMAIN)

    with patch("jaraco.abode.client.Client.set_setting") as mock_set_setting:
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SETTINGS,
            {"setting": "confirm_snd", "value": "loud"},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_setting.assert_called_once()


async def test_add_unique_id(menuai: menuai) -> None:
    """Test unique_id is set to Abode username."""
    mock_entry = await setup_platform(menuai, ALARM_DOMAIN)
    # Set unique_id to None to match previous config entries
    menuai.config_entries.async_update_entry(entry=mock_entry, unique_id=None)
    await menuai.async_block_till_done()

    assert mock_entry.unique_id is None

    await menuai.config_entries.async_reload(mock_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_entry.unique_id == mock_entry.data[CONF_USERNAME]


async def test_unload_entry(menuai: menuai) -> None:
    """Test unloading the Abode entry."""
    mock_entry = await setup_platform(menuai, ALARM_DOMAIN)

    with (
        patch("jaraco.abode.client.Client.logout") as mock_logout,
        patch("jaraco.abode.event_controller.EventController.stop") as mock_events_stop,
    ):
        assert await menuai.config_entries.async_unload(mock_entry.entry_id)
    mock_logout.assert_called_once()
    mock_events_stop.assert_called_once()


async def test_invalid_credentials(menuai: menuai) -> None:
    """Test Abode credentials changing."""
    with patch(
        "menuai.components.abode.Abode",
        side_effect=AbodeAuthenticationException(
            (HTTPStatus.BAD_REQUEST, "auth error")
        ),
    ):
        config_entry = await setup_platform(menuai, ALARM_DOMAIN)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["step_id"] == "reauth_confirm"

    menuai.config_entries.flow.async_abort(flows[0]["flow_id"])
    assert not menuai.config_entries.flow.async_progress()


async def test_raise_config_entry_not_ready_when_offline(menuai: menuai) -> None:
    """Config entry state is SETUP_RETRY when abode is offline."""
    with patch(
        "menuai.components.abode.Abode",
        side_effect=AbodeException("any"),
    ):
        config_entry = await setup_platform(menuai, ALARM_DOMAIN)
        await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY

    assert menuai.config_entries.flow.async_progress() == []
