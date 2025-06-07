"""Test the NextBus config flow."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from menuai import config_entries, setup
from menuai.components.nextbus.const import CONF_AGENCY, CONF_ROUTE, DOMAIN
from menuai.const import CONF_STOP
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


@pytest.fixture
def mock_setup_entry() -> Generator[MagicMock]:
    """Create a mock for the nextbus component setup."""
    with patch(
        "menuai.components.nextbus.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_nextbus() -> Generator[MagicMock]:
    """Create a mock py_nextbus module."""
    with patch("menuai.components.nextbus.config_flow.NextBusClient") as client:
        yield client


async def test_user_config(
    menuai: menuai, mock_setup_entry: MagicMock, mock_nextbus_lists: MagicMock
) -> None:
    """Test we get the form."""
    await setup.async_setup_component(menuai, "persistent_notification", {})
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "agency"

    # Select agency
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_AGENCY: "sfmta-cis",
        },
    )
    await menuai.async_block_till_done()

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "route"

    # Select route
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_ROUTE: "F",
        },
    )
    await menuai.async_block_till_done()

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "stop"

    # Select stop
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_STOP: "5184",
        },
    )
    await menuai.async_block_till_done()

    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert result.get("data") == {
        "agency": "sfmta-cis",
        "route": "F",
        "stop": "5184",
    }

    assert len(mock_setup_entry.mock_calls) == 1
