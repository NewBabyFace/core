"""Test the AWS S3 config flow."""

from unittest.mock import AsyncMock, patch

from botocore.exceptions import (
    ClientError,
    EndpointConnectionError,
    ParamValidationError,
)
import pytest

from menuai import config_entries
from menuai.components.aws_s3.const import CONF_BUCKET, CONF_ENDPOINT_URL, DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .const import USER_INPUT

from tests.common import MockConfigEntry


async def _async_start_flow(
    menuai: menuai,
    user_input: dict[str, str] | None = None,
) -> FlowResultType:
    """Initialize the config flow."""
    if user_input is None:
        user_input = USER_INPUT

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    return await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input,
    )


async def test_flow(menuai: menuai) -> None:
    """Test config flow."""
    result = await _async_start_flow(menuai)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test"
    assert result["data"] == USER_INPUT


@pytest.mark.parametrize(
    ("exception", "errors"),
    [
        (
            ParamValidationError(report="Invalid bucket name"),
            {CONF_BUCKET: "invalid_bucket_name"},
        ),
        (ValueError(), {CONF_ENDPOINT_URL: "invalid_endpoint_url"}),
        (
            EndpointConnectionError(endpoint_url="http://example.com"),
            {CONF_ENDPOINT_URL: "cannot_connect"},
        ),
    ],
)
async def test_flow_create_client_errors(
    menuai: menuai,
    exception: Exception,
    errors: dict[str, str],
) -> None:
    """Test config flow errors."""
    with patch(
        "aiobotocore.session.AioSession.create_client",
        side_effect=exception,
    ):
        result = await _async_start_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == errors

    # Fix and finish the test
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test"
    assert result["data"] == USER_INPUT


async def test_flow_head_bucket_error(
    menuai: menuai,
    mock_client: AsyncMock,
) -> None:
    """Test setup_entry error when calling head_bucket."""
    mock_client.head_bucket.side_effect = ClientError(
        error_response={"Error": {"Code": "InvalidAccessKeyId"}},
        operation_name="head_bucket",
    )
    result = await _async_start_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_credentials"}

    # Fix and finish the test
    mock_client.head_bucket.side_effect = None
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test"
    assert result["data"] == USER_INPUT


async def test_abort_if_already_configured(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test we abort if the account is already configured."""
    mock_config_entry.add_to_menuai(menuai)
    result = await _async_start_flow(menuai)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_flow_create_not_aws_endpoint(
    menuai: menuai,
) -> None:
    """Test config flow with a not aws endpoint should raise an error."""
    result = await _async_start_flow(
        menuai, USER_INPUT | {CONF_ENDPOINT_URL: "http://example.com"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_ENDPOINT_URL: "invalid_endpoint_url"}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        USER_INPUT,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "test"
    assert result["data"] == USER_INPUT
