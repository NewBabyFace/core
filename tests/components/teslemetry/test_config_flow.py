"""Test the Teslemetry config flow."""

from unittest.mock import AsyncMock, patch

from aiohttp import ClientConnectionError
import pytest
from tesla_fleet_api.exceptions import (
    InvalidToken,
    SubscriptionRequired,
    TeslaFleetError,
)

from menuai import config_entries
from menuai.components.teslemetry.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_ACCESS_TOKEN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .const import CONFIG, METADATA

from tests.common import MockConfigEntry

BAD_CONFIG = {CONF_ACCESS_TOKEN: "bad_access_token"}


async def test_form(
    menuai: menuai,
) -> None:
    """Test we get the form."""

    result1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result1["type"] is FlowResultType.FORM
    assert not result1["errors"]

    with patch(
        "menuai.components.teslemetry.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await menuai.config_entries.flow.async_configure(
            result1["flow_id"],
            CONFIG,
        )
        await menuai.async_block_till_done()
        assert len(mock_setup_entry.mock_calls) == 1

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == CONFIG


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (InvalidToken, {CONF_ACCESS_TOKEN: "invalid_access_token"}),
        (SubscriptionRequired, {"base": "subscription_required"}),
        (ClientConnectionError, {"base": "cannot_connect"}),
        (TeslaFleetError, {"base": "unknown"}),
    ],
)
async def test_form_errors(
    menuai: menuai,
    side_effect: TeslaFleetError,
    error: dict[str, str],
    mock_metadata: AsyncMock,
) -> None:
    """Test errors are handled."""

    result1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_metadata.side_effect = side_effect
    result2 = await menuai.config_entries.flow.async_configure(
        result1["flow_id"],
        CONFIG,
    )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == error

    # Complete the flow
    mock_metadata.side_effect = None
    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"],
        CONFIG,
    )
    assert result3["type"] is FlowResultType.CREATE_ENTRY


async def test_reauth(menuai: menuai, mock_metadata: AsyncMock) -> None:
    """Test reauth flow."""

    mock_entry = MockConfigEntry(
        domain=DOMAIN, data=BAD_CONFIG, minor_version=2, unique_id="abc-123"
    )
    mock_entry.add_to_menuai(menuai)

    result1 = await mock_entry.start_reauth_flow(menuai)

    assert result1["type"] is FlowResultType.FORM
    assert result1["step_id"] == "reauth_confirm"
    assert not result1["errors"]

    with patch(
        "menuai.components.teslemetry.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await menuai.config_entries.flow.async_configure(
            result1["flow_id"],
            CONFIG,
        )
        await menuai.async_block_till_done()
        assert len(mock_setup_entry.mock_calls) == 1
        assert len(mock_metadata.mock_calls) == 1

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert mock_entry.data == CONFIG


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (InvalidToken, {CONF_ACCESS_TOKEN: "invalid_access_token"}),
        (SubscriptionRequired, {"base": "subscription_required"}),
        (ClientConnectionError, {"base": "cannot_connect"}),
        (TeslaFleetError, {"base": "unknown"}),
    ],
)
async def test_reauth_errors(
    menuai: menuai,
    mock_metadata: AsyncMock,
    side_effect: TeslaFleetError,
    error: dict[str, str],
) -> None:
    """Test reauth flows that fail."""

    # Start the reauth
    mock_entry = MockConfigEntry(
        domain=DOMAIN, data=BAD_CONFIG, minor_version=2, unique_id="abc-123"
    )
    mock_entry.add_to_menuai(menuai)

    result = await mock_entry.start_reauth_flow(menuai)

    mock_metadata.side_effect = side_effect
    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        BAD_CONFIG,
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == error

    # Complete the flow
    mock_metadata.side_effect = None
    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"],
        CONFIG,
    )
    assert "errors" not in result3
    assert result3["type"] is FlowResultType.ABORT
    assert result3["reason"] == "reauth_successful"
    assert mock_entry.data == CONFIG


async def test_unique_id_abort(
    menuai: menuai,
) -> None:
    """Test duplicate unique ID in config."""

    result1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=CONFIG
    )
    assert result1["type"] is FlowResultType.CREATE_ENTRY

    # Setup a duplicate
    result2 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=CONFIG
    )
    assert result2["type"] is FlowResultType.ABORT


async def test_migrate_from_1_1(menuai: menuai, mock_metadata: AsyncMock) -> None:
    """Test config migration."""

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=1,
        unique_id=None,
        data=CONFIG,
    )

    mock_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    entry = menuai.config_entries.async_get_entry(mock_entry.entry_id)
    assert entry.version == 1
    assert entry.minor_version == 2
    assert entry.unique_id == METADATA["uid"]


async def test_migrate_error_from_1_1(
    menuai: menuai, mock_metadata: AsyncMock
) -> None:
    """Test config migration handles errors."""

    mock_metadata.side_effect = TeslaFleetError

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=1,
        unique_id=None,
        data=CONFIG,
    )

    mock_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    entry = menuai.config_entries.async_get_entry(mock_entry.entry_id)
    assert entry.state is ConfigEntryState.MIGRATION_ERROR


async def test_migrate_error_from_future(
    menuai: menuai, mock_metadata: AsyncMock
) -> None:
    """Test a future version isn't migrated."""

    mock_metadata.side_effect = TeslaFleetError

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        minor_version=1,
        unique_id="abc-123",
        data=CONFIG,
    )

    mock_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    entry = menuai.config_entries.async_get_entry(mock_entry.entry_id)
    assert entry.state is ConfigEntryState.MIGRATION_ERROR
