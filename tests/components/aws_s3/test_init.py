"""Test the AWS S3 storage integration."""

from unittest.mock import AsyncMock, patch

from botocore.exceptions import (
    ClientError,
    EndpointConnectionError,
    ParamValidationError,
)
import pytest

from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry


async def test_load_unload_config_entry(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test loading and unloading the integration."""
    await setup_integration(menuai, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize(
    ("exception", "state"),
    [
        (
            ParamValidationError(report="Invalid bucket name"),
            ConfigEntryState.SETUP_ERROR,
        ),
        (ValueError(), ConfigEntryState.SETUP_ERROR),
        (
            EndpointConnectionError(endpoint_url="https://example.com"),
            ConfigEntryState.SETUP_RETRY,
        ),
    ],
)
async def test_setup_entry_create_client_errors(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    exception: Exception,
    state: ConfigEntryState,
) -> None:
    """Test various setup errors."""
    with patch(
        "aiobotocore.session.AioSession.create_client",
        side_effect=exception,
    ):
        await setup_integration(menuai, mock_config_entry)
        assert mock_config_entry.state is state


async def test_setup_entry_head_bucket_error(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_client: AsyncMock,
) -> None:
    """Test setup_entry error when calling head_bucket."""
    mock_client.head_bucket.side_effect = ClientError(
        error_response={"Error": {"Code": "InvalidAccessKeyId"}},
        operation_name="head_bucket",
    )
    await setup_integration(menuai, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR
