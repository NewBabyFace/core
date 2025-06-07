"""Tests for the refoss Integration."""

from unittest.mock import AsyncMock, patch

from menuai import config_entries
from menuai.components.refoss.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import FakeDiscovery, build_base_device_mock


@patch("menuai.components.refoss.config_flow.DISCOVERY_TIMEOUT", 0)
async def test_creating_entry_sets_up(
    menuai: menuai, mock_setup_entry: AsyncMock
) -> None:
    """Test setting up refoss."""
    with (
        patch(
            "menuai.components.refoss.util.Discovery",
            return_value=FakeDiscovery(),
        ),
        patch(
            "menuai.components.refoss.bridge.async_build_base_device",
            return_value=build_base_device_mock(),
        ),
        patch(
            "menuai.components.refoss.switch.isinstance",
            return_value=True,
        ),
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


@patch("menuai.components.refoss.config_flow.DISCOVERY_TIMEOUT", 0)
async def test_creating_entry_has_no_devices(
    menuai: menuai, mock_setup_entry: AsyncMock
) -> None:
    """Test setting up Refoss no devices."""
    with patch(
        "menuai.components.refoss.util.Discovery",
        return_value=FakeDiscovery(),
    ) as discovery:
        discovery.return_value.mock_devices = {}

        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Confirmation form
        assert result["type"] is FlowResultType.FORM

        result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        assert result["type"] is FlowResultType.ABORT

        await menuai.async_block_till_done()

        assert len(mock_setup_entry.mock_calls) == 0
