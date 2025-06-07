"""Test the Prosegur Alarm config flow."""

from unittest.mock import patch

import pytest

from menuai import config_entries
from menuai.components.prosegur.config_flow import CannotConnect, InvalidAuth
from menuai.components.prosegur.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_form(menuai: menuai, mock_list_contracts) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.prosegur.config_flow.Installation.list",
            return_value=mock_list_contracts,
        ) as mock_retrieve,
        patch(
            "menuai.components.prosegur.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "country": "PT",
            },
        )
        await menuai.async_block_till_done()

        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            {"contract": "123"},
        )
        await menuai.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == "Contract 123"
    assert result3["data"] == {
        "contract": "123",
        "username": "test-username",
        "password": "test-password",
        "country": "PT",
    }
    assert len(mock_setup_entry.mock_calls) == 1

    assert len(mock_retrieve.mock_calls) == 1


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "pyprosegur.installation.Installation.list",
        side_effect=ConnectionRefusedError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "country": "PT",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.prosegur.config_flow.Installation.list",
        side_effect=ConnectionError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "country": "PT",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_unknown_exception(menuai: menuai) -> None:
    """Test we handle unknown exceptions."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "pyprosegur.installation.Installation",
        side_effect=ValueError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
                "country": "PT",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_reauth_flow(menuai: menuai, mock_list_contracts) -> None:
    """Test a reauthentication flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="12345",
        data={
            "username": "test-username",
            "password": "test-password",
            "country": "PT",
        },
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)
    assert result["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.prosegur.config_flow.Installation.list",
            return_value=mock_list_contracts,
        ) as mock_installation,
        patch(
            "menuai.components.prosegur.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "new_password",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert entry.data == {
        "country": "PT",
        "username": "test-username",
        "password": "new_password",
    }

    assert len(mock_installation.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("exception", "base_error"),
    [
        (CannotConnect, "cannot_connect"),
        (InvalidAuth, "invalid_auth"),
        (Exception, "unknown"),
    ],
)
async def test_reauth_flow_error(menuai: menuai, exception, base_error) -> None:
    """Test a reauthentication flow with errors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="12345",
        data={
            "username": "test-username",
            "password": "test-password",
            "country": "PT",
        },
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reauth_flow(menuai)

    with patch(
        "menuai.components.prosegur.config_flow.Installation.list",
        side_effect=exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "new_password",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"]["base"] == base_error
