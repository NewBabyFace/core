"""Define tests for the ReCollect Waste config flow."""

from unittest.mock import AsyncMock, patch

from aiorecollect.errors import RecollectError
import pytest

from menuai.components.recollect_waste import (
    CONF_PLACE_ID,
    CONF_SERVICE_ID,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_FRIENDLY_NAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .conftest import TEST_PLACE_ID, TEST_SERVICE_ID


@pytest.mark.parametrize(
    ("get_pickup_events_mock", "get_pickup_events_errors"),
    [
        (
            AsyncMock(side_effect=RecollectError),
            {"base": "invalid_place_or_service_id"},
        ),
    ],
)
async def test_create_entry(
    menuai: menuai,
    client,
    config,
    get_pickup_events_errors,
    get_pickup_events_mock,
    mock_aiorecollect,
) -> None:
    """Test creating an entry."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # Test errors that can arise when checking the API key:
    with patch.object(client, "async_get_pickup_events", get_pickup_events_mock):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input=config
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == get_pickup_events_errors

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=config
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"{TEST_PLACE_ID}, {TEST_SERVICE_ID}"
    assert result["data"] == {
        CONF_PLACE_ID: TEST_PLACE_ID,
        CONF_SERVICE_ID: TEST_SERVICE_ID,
    }


async def test_duplicate_error(menuai: menuai, config, setup_config_entry) -> None:
    """Test that errors are shown when duplicates are added."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=config
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(
    menuai: menuai, config, config_entry, setup_config_entry
) -> None:
    """Test config flow options."""
    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_FRIENDLY_NAME: True}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {CONF_FRIENDLY_NAME: True}
