"""Test the Enigma2 config flow."""

from typing import Any
from unittest.mock import AsyncMock

from aiohttp.client_exceptions import ClientError
from openwebif.error import InvalidAuthError
import pytest

from menuai.components.enigma2.const import DOMAIN
from menuai.config_entries import SOURCE_USER, ConfigEntryState
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .conftest import TEST_FULL, TEST_REQUIRED

from tests.common import MockConfigEntry


@pytest.fixture
async def user_flow(menuai: menuai) -> str:
    """Return a user-initiated flow after filling in host info."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None
    return result["flow_id"]


@pytest.mark.usefixtures("openwebif_device_mock")
@pytest.mark.parametrize(
    ("test_config"),
    [(TEST_FULL), (TEST_REQUIRED)],
)
async def test_form_user(menuai: menuai, test_config: dict[str, Any]) -> None:
    """Test a successful user initiated flow."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], test_config
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == test_config[CONF_HOST]
    assert result["data"] == test_config


@pytest.mark.parametrize(
    ("side_effect", "error_value"),
    [
        (InvalidAuthError, "invalid_auth"),
        (ClientError, "cannot_connect"),
        (Exception, "unknown"),
    ],
)
async def test_form_user_errors(
    menuai: menuai,
    openwebif_device_mock: AsyncMock,
    side_effect: Exception,
    error_value: str,
) -> None:
    """Test we handle errors."""

    openwebif_device_mock.get_about.side_effect = side_effect
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], TEST_FULL
    )
    await menuai.async_block_till_done()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == SOURCE_USER
    assert result["errors"] == {"base": error_value}

    openwebif_device_mock.get_about.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        TEST_FULL,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_FULL[CONF_HOST]
    assert result["data"] == TEST_FULL
    assert result["result"].unique_id == openwebif_device_mock.mac_address


@pytest.mark.usefixtures("openwebif_device_mock")
async def test_duplicate_host(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> None:
    """Test that a duplicate host aborts the config flow."""
    mock_config_entry.add_to_menuai(menuai)

    result2 = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "user"
    result2 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"], TEST_FULL
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


@pytest.mark.usefixtures("openwebif_device_mock")
async def test_options_flow(menuai: menuai) -> None:
    """Test the form options."""

    entry = MockConfigEntry(domain=DOMAIN, data=TEST_FULL, options={}, entry_id="1")
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], user_input={"source_bouquet": "Favourites (TV)"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"source_bouquet": "Favourites (TV)"}

    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
