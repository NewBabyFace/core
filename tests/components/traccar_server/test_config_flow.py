"""Test the Traccar Server config flow."""

from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from pytraccar import TraccarException

from menuai import config_entries
from menuai.components.traccar_server.const import (
    CONF_CUSTOM_ATTRIBUTES,
    CONF_EVENTS,
    CONF_MAX_ACCURACY,
    CONF_SKIP_ACCURACY_FILTER_FOR,
    DOMAIN,
)
from menuai.config_entries import ConfigEntryState
from menuai.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form(
    menuai: menuai,
    mock_traccar_api_client: Generator[AsyncMock],
) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "1.1.1.1",
            CONF_USERNAME: "test-username",
            CONF_PASSWORD: "test-password",
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "1.1.1.1:8082"
    assert result["data"] == {
        CONF_HOST: "1.1.1.1",
        CONF_PORT: "8082",
        CONF_USERNAME: "test-username",
        CONF_PASSWORD: "test-password",
        CONF_SSL: False,
        CONF_VERIFY_SSL: True,
    }
    assert result["result"].state is ConfigEntryState.LOADED


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (TraccarException, "cannot_connect"),
        (Exception, "unknown"),
    ],
)
async def test_form_cannot_connect(
    menuai: menuai,
    side_effect: Exception,
    error: str,
    mock_traccar_api_client: Generator[AsyncMock],
) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_traccar_api_client.get_server.side_effect = side_effect

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "1.1.1.1",
            CONF_USERNAME: "test-username",
            CONF_PASSWORD: "test-password",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_traccar_api_client.get_server.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "1.1.1.1",
            CONF_USERNAME: "test-username",
            CONF_PASSWORD: "test-password",
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "1.1.1.1:8082"
    assert result["data"] == {
        CONF_HOST: "1.1.1.1",
        CONF_PORT: "8082",
        CONF_USERNAME: "test-username",
        CONF_PASSWORD: "test-password",
        CONF_SSL: False,
        CONF_VERIFY_SSL: True,
    }

    assert result["result"].state is ConfigEntryState.LOADED


async def test_options(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_traccar_api_client: Generator[AsyncMock],
) -> None:
    """Test options flow."""
    mock_config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)

    assert mock_config_entry.options.get(CONF_MAX_ACCURACY) == 5.0

    result = await menuai.config_entries.options.async_init(mock_config_entry.entry_id)

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_MAX_ACCURACY: 2.0},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options == {
        CONF_MAX_ACCURACY: 2.0,
        CONF_EVENTS: [],
        CONF_CUSTOM_ATTRIBUTES: [],
        CONF_SKIP_ACCURACY_FILTER_FOR: [],
    }


async def test_abort_already_configured(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_traccar_api_client: Generator[AsyncMock],
) -> None:
    """Test abort for existing server."""
    mock_config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "1.1.1.1",
            CONF_PORT: "8082",
            CONF_USERNAME: "test-username",
            CONF_PASSWORD: "test-password",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
