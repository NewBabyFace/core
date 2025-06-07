"""Test the Fjäråskupan config flow."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from menuai import config_entries
from menuai.components.fjaraskupan.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import COOKER_SERVICE_INFO


@pytest.fixture(name="mock_setup_entry", autouse=True)
def fixture_mock_setup_entry() -> Generator[AsyncMock]:
    """Fixture for config entry."""

    with patch(
        "menuai.components.fjaraskupan.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


async def test_configure(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    with patch(
        "menuai.components.fjaraskupan.config_flow.async_discovered_service_info",
        return_value=[COOKER_SERVICE_INFO],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        assert result["type"] is FlowResultType.FORM
        result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "Fjäråskupan"
        assert result["data"] == {}

        await menuai.async_block_till_done()
        assert len(mock_setup_entry.mock_calls) == 1


async def test_scan_no_devices(menuai: menuai) -> None:
    """Test we get the form."""

    with patch(
        "menuai.components.fjaraskupan.config_flow.async_discovered_service_info",
        return_value=[],
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        assert result["type"] is FlowResultType.FORM
        result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "no_devices_found"
