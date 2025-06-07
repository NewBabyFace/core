"""Test the Garages Amsterdam config flow."""

from http import HTTPStatus
from unittest.mock import AsyncMock, patch

from aiohttp import ClientResponseError
import pytest

from menuai.components.garages_amsterdam.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


async def test_full_user_flow(
    menuai: menuai,
    mock_garages_amsterdam: AsyncMock,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test the full user configuration flow."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert not result.get("errors")

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"garage_name": "IJDok"},
    )

    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert result.get("title") == "IJDok"
    assert result.get("data") == {"garage_name": "IJDok"}
    assert len(mock_garages_amsterdam.all_garages.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("side_effect", "reason"),
    [
        (RuntimeError, "unknown"),
        (
            ClientResponseError(None, None, status=HTTPStatus.INTERNAL_SERVER_ERROR),
            "cannot_connect",
        ),
    ],
)
async def test_error_handling(
    side_effect: Exception, reason: str, menuai: menuai
) -> None:
    """Test error handling in the config flow."""

    with patch(
        "menuai.components.garages_amsterdam.config_flow.ODPAmsterdam.all_garages",
        side_effect=side_effect,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == reason
