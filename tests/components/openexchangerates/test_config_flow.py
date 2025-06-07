"""Test the Open Exchange Rates config flow."""

import asyncio
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

from aioopenexchangerates import (
    OpenExchangeRatesAuthError,
    OpenExchangeRatesClientError,
)
import pytest

from menuai import config_entries
from menuai.components.openexchangerates.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


@pytest.fixture(name="currencies", autouse=True)
def currencies_fixture(menuai: menuai) -> Generator[AsyncMock]:
    """Mock currencies."""
    with patch(
        "menuai.components.openexchangerates.config_flow.Client.get_currencies",
        return_value={"USD": "United States Dollar", "EUR": "Euro"},
    ) as mock_currencies:
        yield mock_currencies


async def test_user_create_entry(
    menuai: menuai,
    mock_latest_rates_config_flow: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"api_key": "test-api-key"},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "USD"
    assert result["data"] == {
        "api_key": "test-api-key",
        "base": "USD",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(
    menuai: menuai,
    mock_latest_rates_config_flow: AsyncMock,
) -> None:
    """Test we handle invalid auth."""
    mock_latest_rates_config_flow.side_effect = OpenExchangeRatesAuthError()
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"api_key": "bad-api-key"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(
    menuai: menuai,
    mock_latest_rates_config_flow: AsyncMock,
) -> None:
    """Test we handle cannot connect error."""
    mock_latest_rates_config_flow.side_effect = OpenExchangeRatesClientError()
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"api_key": "test-api-key"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_unknown_error(
    menuai: menuai,
    mock_latest_rates_config_flow: AsyncMock,
) -> None:
    """Test we handle unknown error."""
    mock_latest_rates_config_flow.side_effect = Exception()
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"api_key": "test-api-key"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_already_configured_service(
    menuai: menuai,
    mock_latest_rates_config_flow: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test we abort if the service is already configured."""
    mock_config_entry.add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"api_key": "test-api-key"},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_no_currencies(menuai: menuai, currencies: AsyncMock) -> None:
    """Test we abort if the service fails to retrieve currencies."""
    currencies.side_effect = OpenExchangeRatesClientError()
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_currencies_timeout(menuai: menuai, currencies: AsyncMock) -> None:
    """Test we abort if the service times out retrieving currencies."""

    async def currencies_side_effect():
        await asyncio.sleep(1)
        return {"USD": "United States Dollar", "EUR": "Euro"}

    currencies.side_effect = currencies_side_effect

    with patch(
        "menuai.components.openexchangerates.config_flow.CLIENT_TIMEOUT", 0
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "timeout_connect"


async def test_latest_rates_timeout(
    menuai: menuai,
    mock_latest_rates_config_flow: AsyncMock,
) -> None:
    """Test we abort if the service times out retrieving latest rates."""

    async def latest_rates_side_effect(*args: Any, **kwargs: Any) -> dict[str, float]:
        await asyncio.sleep(1)
        return {"EUR": 1.0}

    mock_latest_rates_config_flow.side_effect = latest_rates_side_effect

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.openexchangerates.config_flow.CLIENT_TIMEOUT", 0
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"api_key": "test-api-key"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "timeout_connect"}


async def test_reauth(
    menuai: menuai,
    mock_latest_rates_config_flow: AsyncMock,
    mock_setup_entry: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test we can reauthenticate the config entry."""
    mock_config_entry.add_to_menuai(menuai)
    result = await mock_config_entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    mock_latest_rates_config_flow.side_effect = OpenExchangeRatesAuthError()

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "api_key": "invalid-test-api-key",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    mock_latest_rates_config_flow.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "api_key": "new-test-api-key",
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert len(mock_setup_entry.mock_calls) == 1
