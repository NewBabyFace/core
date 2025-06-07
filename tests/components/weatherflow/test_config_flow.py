"""Tests for WeatherFlow."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from pyweatherflowudp.errors import AddressInUseError

from menuai import config_entries
from menuai.components.weatherflow.const import (
    DOMAIN,
    ERROR_MSG_ADDRESS_IN_USE,
    ERROR_MSG_CANNOT_CONNECT,
    ERROR_MSG_NO_DEVICE_FOUND,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_single_instance(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_has_devices: AsyncMock,
) -> None:
    """Test more than one instance."""
    mock_config_entry.add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_devices_with_mocks(
    menuai: menuai,
    mock_start: AsyncMock,
    mock_stop: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test getting user input."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {}


@pytest.mark.parametrize(
    ("exception", "error_msg"),
    [
        (TimeoutError, ERROR_MSG_NO_DEVICE_FOUND),
        (asyncio.exceptions.CancelledError, ERROR_MSG_CANNOT_CONNECT),
        (AddressInUseError, ERROR_MSG_ADDRESS_IN_USE),
    ],
)
async def test_devices_with_various_mocks_errors(
    menuai: menuai,
    mock_start: AsyncMock,
    mock_stop: AsyncMock,
    mock_setup_entry: AsyncMock,
    exception: Exception,
    error_msg: str,
) -> None:
    """Test the various on error states - then finally complete the test."""

    with patch(
        "menuai.components.weatherflow.config_flow.WeatherFlowListener.on",
        side_effect=exception,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )

        await menuai.async_block_till_done()
        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == error_msg
        assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(result["flow_id"])

    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {}
