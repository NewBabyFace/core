"""Test the Tessie config flow."""

from unittest.mock import patch

import pytest

from menuai import config_entries
from menuai.components.tessie.const import DOMAIN
from menuai.const import CONF_ACCESS_TOKEN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .common import (
    ERROR_AUTH,
    ERROR_CONNECTION,
    ERROR_UNKNOWN,
    TEST_CONFIG,
    TEST_STATE_OF_ALL_VEHICLES,
)

from tests.common import MockConfigEntry


@pytest.fixture(autouse=True)
def mock_config_flow_get_state_of_all_vehicles():
    """Mock get_state_of_all_vehicles in config flow."""
    with patch(
        "menuai.components.tessie.config_flow.get_state_of_all_vehicles",
        return_value=TEST_STATE_OF_ALL_VEHICLES,
    ) as mock_config_flow_get_state_of_all_vehicles:
        yield mock_config_flow_get_state_of_all_vehicles


@pytest.fixture(autouse=True)
def mock_async_setup_entry():
    """Mock async_setup_entry."""
    with patch(
        "menuai.components.tessie.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry:
        yield mock_async_setup_entry


async def test_form(
    menuai: menuai,
    mock_config_flow_get_state_of_all_vehicles,
    mock_async_setup_entry,
) -> None:
    """Test we get the form."""

    result1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result1["type"] is FlowResultType.FORM
    assert not result1["errors"]

    result2 = await menuai.config_entries.flow.async_configure(
        result1["flow_id"],
        TEST_CONFIG,
    )
    await menuai.async_block_till_done()
    assert len(mock_async_setup_entry.mock_calls) == 1
    assert len(mock_config_flow_get_state_of_all_vehicles.mock_calls) == 1

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Tessie"
    assert result2["data"] == TEST_CONFIG


async def test_abort(
    menuai: menuai,
    mock_config_flow_get_state_of_all_vehicles,
    mock_async_setup_entry,
) -> None:
    """Test a duplicate entry aborts."""

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data=TEST_CONFIG,
    )
    mock_entry.add_to_menuai(menuai)

    result1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await menuai.config_entries.flow.async_configure(
        result1["flow_id"],
        TEST_CONFIG,
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (ERROR_AUTH, {CONF_ACCESS_TOKEN: "invalid_access_token"}),
        (ERROR_UNKNOWN, {"base": "unknown"}),
        (ERROR_CONNECTION, {"base": "cannot_connect"}),
    ],
)
async def test_form_errors(
    menuai: menuai, side_effect, error, mock_config_flow_get_state_of_all_vehicles
) -> None:
    """Test errors are handled."""

    result1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_config_flow_get_state_of_all_vehicles.side_effect = side_effect
    result2 = await menuai.config_entries.flow.async_configure(
        result1["flow_id"],
        TEST_CONFIG,
    )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == error

    # Complete the flow
    mock_config_flow_get_state_of_all_vehicles.side_effect = None
    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"],
        TEST_CONFIG,
    )
    assert "errors" not in result3
    assert result3["type"] is FlowResultType.CREATE_ENTRY


async def test_reauth(
    menuai: menuai,
    mock_config_flow_get_state_of_all_vehicles,
    mock_async_setup_entry,
) -> None:
    """Test reauth flow."""

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data=TEST_CONFIG,
    )
    mock_entry.add_to_menuai(menuai)

    result1 = await mock_entry.start_reauth_flow(menuai)

    assert result1["type"] is FlowResultType.FORM
    assert result1["step_id"] == "reauth_confirm"
    assert not result1["errors"]

    result2 = await menuai.config_entries.flow.async_configure(
        result1["flow_id"],
        TEST_CONFIG,
    )
    await menuai.async_block_till_done()
    assert len(mock_async_setup_entry.mock_calls) == 1
    assert len(mock_config_flow_get_state_of_all_vehicles.mock_calls) == 1

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert mock_entry.data == TEST_CONFIG


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (ERROR_AUTH, {CONF_ACCESS_TOKEN: "invalid_access_token"}),
        (ERROR_UNKNOWN, {"base": "unknown"}),
        (ERROR_CONNECTION, {"base": "cannot_connect"}),
    ],
)
async def test_reauth_errors(
    menuai: menuai,
    mock_config_flow_get_state_of_all_vehicles,
    mock_async_setup_entry,
    side_effect,
    error,
) -> None:
    """Test reauth flows that fail."""

    mock_config_flow_get_state_of_all_vehicles.side_effect = side_effect

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data=TEST_CONFIG,
    )
    mock_entry.add_to_menuai(menuai)

    result1 = await mock_entry.start_reauth_flow(menuai)

    result2 = await menuai.config_entries.flow.async_configure(
        result1["flow_id"],
        TEST_CONFIG,
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == error

    # Complete the flow
    mock_config_flow_get_state_of_all_vehicles.side_effect = None
    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"],
        TEST_CONFIG,
    )
    assert "errors" not in result3
    assert result3["type"] is FlowResultType.ABORT
    assert result3["reason"] == "reauth_successful"
    assert mock_entry.data == TEST_CONFIG
    assert len(mock_async_setup_entry.mock_calls) == 1
