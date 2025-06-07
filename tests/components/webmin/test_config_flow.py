"""Test the Webmin config flow."""

from __future__ import annotations

from http import HTTPStatus
from unittest.mock import AsyncMock, patch
from xmlrpc.client import Fault

from aiohttp.client_exceptions import ClientConnectionError, ClientResponseError
import pytest

from menuai import config_entries
from menuai.components.webmin.const import DOMAIN
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .conftest import TEST_USER_INPUT

from tests.common import async_load_json_object_fixture

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


@pytest.fixture
async def user_flow(menuai: menuai) -> str:
    """Return a user-initiated flow after filling in host info."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None
    return result["flow_id"]


@pytest.mark.parametrize(
    "fixture", ["webmin_update_without_mac.json", "webmin_update.json"]
)
async def test_form_user(
    menuai: menuai, user_flow: str, mock_setup_entry: AsyncMock, fixture: str
) -> None:
    """Test a successful user initiated flow."""
    with patch(
        "menuai.components.webmin.helpers.WebminInstance.update",
        return_value=await async_load_json_object_fixture(menuai, fixture, DOMAIN),
    ):
        result = await menuai.config_entries.flow.async_configure(
            user_flow, TEST_USER_INPUT
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_USER_INPUT[CONF_HOST]
    assert result["options"] == TEST_USER_INPUT

    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("exception", "error_type"),
    [
        (
            ClientResponseError(
                request_info=None, history=None, status=HTTPStatus.UNAUTHORIZED
            ),
            "invalid_auth",
        ),
        (
            ClientResponseError(
                request_info=None, history=None, status=HTTPStatus.BAD_REQUEST
            ),
            "cannot_connect",
        ),
        (ClientConnectionError, "cannot_connect"),
        (Exception, "unknown"),
        (
            Fault("5", "Webmin module net does not exist"),
            "unknown",
        ),
    ],
)
async def test_form_user_errors(
    menuai: menuai, user_flow: str, exception: Exception, error_type: str
) -> None:
    """Test we handle errors."""
    with patch(
        "menuai.components.webmin.helpers.WebminInstance.update",
        side_effect=exception,
    ):
        result = await menuai.config_entries.flow.async_configure(
            user_flow, TEST_USER_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": error_type}

    with patch(
        "menuai.components.webmin.helpers.WebminInstance.update",
        return_value=await async_load_json_object_fixture(
            menuai, "webmin_update.json", DOMAIN
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_USER_INPUT
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_USER_INPUT[CONF_HOST]
    assert result["options"] == TEST_USER_INPUT


async def test_duplicate_entry(
    menuai: menuai,
    user_flow: str,
    mock_setup_entry: AsyncMock,
) -> None:
    """Test a successful user initiated flow."""
    with patch(
        "menuai.components.webmin.helpers.WebminInstance.update",
        return_value=await async_load_json_object_fixture(
            menuai, "webmin_update.json", DOMAIN
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            user_flow, TEST_USER_INPUT
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_USER_INPUT[CONF_HOST]
    assert result["options"] == TEST_USER_INPUT

    with patch(
        "menuai.components.webmin.helpers.WebminInstance.update",
        return_value=await async_load_json_object_fixture(
            menuai, "webmin_update.json", DOMAIN
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], TEST_USER_INPUT
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
