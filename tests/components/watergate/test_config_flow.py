"""Tests for the Watergate config flow."""

from collections.abc import Generator

import pytest
from watergate_local_api import WatergateApiException

from menuai.components.watergate.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_IP_ADDRESS, CONF_WEBHOOK_ID
from menuai.data_entry_flow import FlowResultType

from .const import DEFAULT_DEVICE_STATE, DEFAULT_SERIAL_NUMBER, MOCK_WEBHOOK_ID

from tests.common import AsyncMock, menuai, MockConfigEntry


async def test_step_user_form(
    menuai: menuai,
    mock_watergate_client: Generator[AsyncMock],
    mock_webhook_id_generation: Generator[None],
    user_input: dict[str, str],
) -> None:
    """Test checking if registration form works end to end."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert CONF_IP_ADDRESS in result["data_schema"].schema

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Sonic"
    assert result["data"] == {**user_input, CONF_WEBHOOK_ID: MOCK_WEBHOOK_ID}
    assert result["result"].unique_id == DEFAULT_SERIAL_NUMBER


@pytest.mark.parametrize(
    "client_result",
    [AsyncMock(return_value=None), AsyncMock(side_effect=WatergateApiException)],
)
async def test_step_user_form_with_exception(
    menuai: menuai,
    mock_watergate_client: Generator[AsyncMock],
    user_input: dict[str, str],
    client_result: AsyncMock,
    mock_webhook_id_generation: Generator[None],
) -> None:
    """Test checking if errors will be displayed when Exception is thrown while checking device state."""
    mock_watergate_client.async_get_device_state = client_result

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"][CONF_IP_ADDRESS] == "cannot_connect"

    mock_watergate_client.async_get_device_state = AsyncMock(
        return_value=DEFAULT_DEVICE_STATE
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Sonic"
    assert result["data"] == {**user_input, CONF_WEBHOOK_ID: MOCK_WEBHOOK_ID}


async def test_abort_if_id_is_not_unique(
    menuai: menuai,
    mock_watergate_client: Generator[AsyncMock],
    mock_entry: MockConfigEntry,
    user_input: dict[str, str],
) -> None:
    """Test checking if we will inform user that this entity is already registered."""
    mock_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert CONF_IP_ADDRESS in result["data_schema"].schema

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
