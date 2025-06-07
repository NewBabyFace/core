"""Test the menuai Analytics config flow."""

from typing import Any
from unittest.mock import AsyncMock

import pytest
from python_menuai_analytics import menuaiAnalyticsConnectionError

from menuai.components.analytics_insights.const import (
    CONF_TRACKED_ADDONS,
    CONF_TRACKED_CUSTOM_INTEGRATIONS,
    CONF_TRACKED_INTEGRATIONS,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import setup_integration

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("user_input", "expected_options"),
    [
        (
            {
                CONF_TRACKED_ADDONS: ["core_samba"],
                CONF_TRACKED_INTEGRATIONS: ["youtube"],
                CONF_TRACKED_CUSTOM_INTEGRATIONS: ["hacs"],
            },
            {
                CONF_TRACKED_ADDONS: ["core_samba"],
                CONF_TRACKED_INTEGRATIONS: ["youtube"],
                CONF_TRACKED_CUSTOM_INTEGRATIONS: ["hacs"],
            },
        ),
        (
            {
                CONF_TRACKED_INTEGRATIONS: ["youtube"],
            },
            {
                CONF_TRACKED_ADDONS: [],
                CONF_TRACKED_INTEGRATIONS: ["youtube"],
                CONF_TRACKED_CUSTOM_INTEGRATIONS: [],
            },
        ),
        (
            {
                CONF_TRACKED_CUSTOM_INTEGRATIONS: ["hacs"],
            },
            {
                CONF_TRACKED_ADDONS: [],
                CONF_TRACKED_INTEGRATIONS: [],
                CONF_TRACKED_CUSTOM_INTEGRATIONS: ["hacs"],
            },
        ),
    ],
)
async def test_form(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_analytics_client: AsyncMock,
    user_input: dict[str, Any],
    expected_options: dict[str, Any],
) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "MenuAI Analytics Insights"
    assert result["data"] == {}
    assert result["options"] == expected_options
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    "user_input",
    [
        {
            CONF_TRACKED_ADDONS: [],
            CONF_TRACKED_INTEGRATIONS: [],
            CONF_TRACKED_CUSTOM_INTEGRATIONS: [],
        },
        {},
    ],
)
async def test_submitting_empty_form(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_analytics_client: AsyncMock,
    user_input: dict[str, Any],
) -> None:
    """Test we can't submit an empty form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_integrations_selected"}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_TRACKED_ADDONS: ["core_samba"],
            CONF_TRACKED_INTEGRATIONS: ["youtube"],
            CONF_TRACKED_CUSTOM_INTEGRATIONS: ["hacs"],
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "MenuAI Analytics Insights"
    assert result["data"] == {}
    assert result["options"] == {
        CONF_TRACKED_ADDONS: ["core_samba"],
        CONF_TRACKED_INTEGRATIONS: ["youtube"],
        CONF_TRACKED_CUSTOM_INTEGRATIONS: ["hacs"],
    }
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("exception", "reason"),
    [
        (menuaiAnalyticsConnectionError, "cannot_connect"),
        (Exception, "unknown"),
    ],
)
async def test_form_cannot_connect(
    menuai: menuai,
    mock_analytics_client: AsyncMock,
    exception: Exception,
    reason: str,
) -> None:
    """Test we handle cannot connect error."""

    mock_analytics_client.get_integrations.side_effect = exception

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == reason


async def test_form_already_configured(
    menuai: menuai, mock_setup_entry: AsyncMock
) -> None:
    """Test we handle cannot connect error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            CONF_TRACKED_ADDONS: [],
            CONF_TRACKED_INTEGRATIONS: ["youtube", "spotify"],
            CONF_TRACKED_CUSTOM_INTEGRATIONS: [],
        },
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


@pytest.mark.parametrize(
    ("user_input", "expected_options"),
    [
        (
            {
                CONF_TRACKED_ADDONS: ["core_samba"],
                CONF_TRACKED_INTEGRATIONS: ["youtube"],
                CONF_TRACKED_CUSTOM_INTEGRATIONS: ["hacs"],
            },
            {
                CONF_TRACKED_ADDONS: ["core_samba"],
                CONF_TRACKED_INTEGRATIONS: ["youtube"],
                CONF_TRACKED_CUSTOM_INTEGRATIONS: ["hacs"],
            },
        ),
        (
            {
                CONF_TRACKED_ADDONS: ["core_samba"],
            },
            {
                CONF_TRACKED_ADDONS: ["core_samba"],
                CONF_TRACKED_INTEGRATIONS: [],
                CONF_TRACKED_CUSTOM_INTEGRATIONS: [],
            },
        ),
        (
            {
                CONF_TRACKED_INTEGRATIONS: ["youtube"],
            },
            {
                CONF_TRACKED_ADDONS: [],
                CONF_TRACKED_INTEGRATIONS: ["youtube"],
                CONF_TRACKED_CUSTOM_INTEGRATIONS: [],
            },
        ),
        (
            {
                CONF_TRACKED_CUSTOM_INTEGRATIONS: ["hacs"],
            },
            {
                CONF_TRACKED_ADDONS: [],
                CONF_TRACKED_INTEGRATIONS: [],
                CONF_TRACKED_CUSTOM_INTEGRATIONS: ["hacs"],
            },
        ),
    ],
)
async def test_options_flow(
    menuai: menuai,
    mock_analytics_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    user_input: dict[str, Any],
    expected_options: dict[str, Any],
) -> None:
    """Test options flow."""
    await setup_integration(menuai, mock_config_entry)
    result = await menuai.config_entries.options.async_init(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM

    mock_analytics_client.get_integrations.reset_mock()
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == expected_options
    await menuai.async_block_till_done()
    mock_analytics_client.get_integrations.assert_called_once()


@pytest.mark.parametrize(
    "user_input",
    [
        {
            CONF_TRACKED_ADDONS: [],
            CONF_TRACKED_INTEGRATIONS: [],
            CONF_TRACKED_CUSTOM_INTEGRATIONS: [],
        },
        {},
    ],
)
async def test_submitting_empty_options_flow(
    menuai: menuai,
    mock_analytics_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    user_input: dict[str, Any],
) -> None:
    """Test options flow."""
    await setup_integration(menuai, mock_config_entry)
    result = await menuai.config_entries.options.async_init(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_integrations_selected"}

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_TRACKED_ADDONS: ["core_samba"],
            CONF_TRACKED_INTEGRATIONS: ["youtube", "hue"],
            CONF_TRACKED_CUSTOM_INTEGRATIONS: ["hacs"],
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_TRACKED_ADDONS: ["core_samba"],
        CONF_TRACKED_INTEGRATIONS: ["youtube", "hue"],
        CONF_TRACKED_CUSTOM_INTEGRATIONS: ["hacs"],
    }
    await menuai.async_block_till_done()


async def test_options_flow_cannot_connect(
    menuai: menuai,
    mock_analytics_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test we handle cannot connect error."""

    mock_analytics_client.get_integrations.side_effect = (
        menuaiAnalyticsConnectionError
    )
    mock_config_entry.add_to_menuai(menuai)
    result = await menuai.config_entries.options.async_init(mock_config_entry.entry_id)
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"
