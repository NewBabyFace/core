"""Tests for iZone."""

from collections.abc import Callable
from typing import Any
from unittest.mock import Mock, patch

import pytest

from menuai import config_entries
from menuai.components.izone.const import DISPATCH_CONTROLLER_DISCOVERED, IZONE
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.dispatcher import async_dispatcher_send


@pytest.fixture
def mock_disco() -> Mock:
    """Mock discovery service."""
    disco = Mock()
    disco.pi_disco = Mock()
    disco.pi_disco.controllers = {}
    return disco


def _mock_start_discovery(menuai: menuai, mock_disco: Mock) -> Callable[..., Mock]:
    def do_disovered(*args: Any) -> Mock:
        async_dispatcher_send(menuai, DISPATCH_CONTROLLER_DISCOVERED, True)
        return mock_disco

    return do_disovered


async def test_not_found(menuai: menuai, mock_disco: Mock) -> None:
    """Test not finding iZone controller."""

    with (
        patch(
            "menuai.components.izone.config_flow.async_start_discovery_service"
        ) as start_disco,
        patch(
            "menuai.components.izone.config_flow.async_stop_discovery_service",
            return_value=None,
        ) as stop_disco,
    ):
        start_disco.side_effect = _mock_start_discovery(menuai, mock_disco)
        result = await menuai.config_entries.flow.async_init(
            IZONE, context={"source": config_entries.SOURCE_USER}
        )

        # Confirmation form
        assert result["type"] is FlowResultType.FORM

        result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        assert result["type"] is FlowResultType.ABORT

        await menuai.async_block_till_done()

    stop_disco.assert_called_once()


async def test_found(menuai: menuai, mock_disco: Mock) -> None:
    """Test not finding iZone controller."""
    mock_disco.pi_disco.controllers["blah"] = object()

    with (
        patch(
            "menuai.components.izone.climate.async_setup_entry",
            return_value=True,
        ) as mock_setup,
        patch(
            "menuai.components.izone.config_flow.async_start_discovery_service"
        ) as start_disco,
        patch(
            "menuai.components.izone.async_start_discovery_service",
            return_value=None,
        ),
    ):
        start_disco.side_effect = _mock_start_discovery(menuai, mock_disco)
        result = await menuai.config_entries.flow.async_init(
            IZONE, context={"source": config_entries.SOURCE_USER}
        )

        # Confirmation form
        assert result["type"] is FlowResultType.FORM

        result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        assert result["type"] is FlowResultType.CREATE_ENTRY

        await menuai.async_block_till_done()

    mock_setup.assert_called_once()
