"""Tests for the Music Player Daemon config flow."""

from socket import gaierror
from unittest.mock import AsyncMock

import mpd
import pytest

from menuai.components.mpd.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_full_flow(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_mpd_client: AsyncMock,
) -> None:
    """Test the happy flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.0.1", CONF_PORT: 6600, CONF_PASSWORD: "test123"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Music Player Daemon"
    assert result["data"] == {
        CONF_HOST: "192.168.0.1",
        CONF_PORT: 6600,
        CONF_PASSWORD: "test123",
    }
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (TimeoutError, "cannot_connect"),
        (gaierror, "cannot_connect"),
        (mpd.ConnectionError, "cannot_connect"),
        (OSError, "cannot_connect"),
        (Exception, "unknown"),
    ],
)
async def test_errors(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_mpd_client: AsyncMock,
    exception: Exception,
    error: str,
) -> None:
    """Test we handle errors correctly."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    mock_mpd_client.password.side_effect = exception

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.0.1", CONF_PORT: 6600, CONF_PASSWORD: "test123"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_mpd_client.password.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.0.1", CONF_PORT: 6600, CONF_PASSWORD: "test123"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_existing_entry(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> None:
    """Test we abort if an entry already exists."""
    mock_config_entry.add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.0.1", CONF_PORT: 6600, CONF_PASSWORD: "test123"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
