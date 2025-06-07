"""Tests for the Gree Integration."""

from unittest.mock import AsyncMock, patch

import pytest

from menuai import config_entries
from menuai.components.gree.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .common import FakeDiscovery

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


@patch("menuai.components.gree.config_flow.DISCOVERY_TIMEOUT", 0)
async def test_creating_entry_sets_up_climate(
    menuai: menuai, mock_setup_entry: AsyncMock
) -> None:
    """Test setting up Gree creates the climate components."""
    with patch(
        "menuai.components.gree.config_flow.Discovery",
        return_value=FakeDiscovery(),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Confirmation form
        assert result["type"] is FlowResultType.FORM

        result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        assert result["type"] is FlowResultType.CREATE_ENTRY

        await menuai.async_block_till_done()

        assert len(mock_setup_entry.mock_calls) == 1


@patch("menuai.components.gree.config_flow.DISCOVERY_TIMEOUT", 0)
async def test_creating_entry_has_no_devices(
    menuai: menuai, mock_setup_entry: AsyncMock
) -> None:
    """Test setting up Gree creates the climate components."""
    with patch(
        "menuai.components.gree.config_flow.Discovery",
        return_value=FakeDiscovery(),
    ) as discovery:
        discovery.return_value.mock_devices = []

        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Confirmation form
        assert result["type"] is FlowResultType.FORM

        result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        assert result["type"] is FlowResultType.ABORT

        await menuai.async_block_till_done()

        assert len(mock_setup_entry.mock_calls) == 0
