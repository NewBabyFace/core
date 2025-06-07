"""Define tests for the Ambient PWS config flow."""

from unittest.mock import AsyncMock, patch

from aioambient.errors import AmbientError
import pytest

from menuai.components.ambient_station.const import CONF_APP_KEY, DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_API_KEY
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


@pytest.mark.parametrize(
    ("devices_response", "errors"),
    [
        (AsyncMock(side_effect=AmbientError), {"base": "invalid_key"}),
        (AsyncMock(return_value=[]), {"base": "no_devices"}),
    ],
)
async def test_create_entry(
    menuai: menuai, api, config, devices_response, errors, mock_aioambient
) -> None:
    """Test creating an entry."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # Test errors that can arise:
    with patch.object(api, "get_devices", devices_response):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input=config
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == errors

    # Test that we can recover and finish the flow after errors occur:
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input=config
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "67890fghij67"
    assert result["data"] == {
        CONF_API_KEY: "12345abcde12345abcde",
        CONF_APP_KEY: "67890fghij67890fghij",
    }


async def test_duplicate_error(
    menuai: menuai, config, config_entry, setup_config_entry
) -> None:
    """Test that errors are shown when duplicates are added."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=config
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
