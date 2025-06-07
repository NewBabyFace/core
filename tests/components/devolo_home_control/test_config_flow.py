"""Test the devolo_home_control config flow."""

from unittest.mock import patch

import pytest

from menuai import config_entries
from menuai.components.devolo_home_control.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResult, FlowResultType

from .const import (
    DISCOVERY_INFO,
    DISCOVERY_INFO_WRONG_DEVICE,
    DISCOVERY_INFO_WRONG_DEVOLO_DEVICE,
)

from tests.common import MockConfigEntry


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    await _setup(menuai, result)


@pytest.mark.parametrize("credentials_valid", [False])
async def test_form_invalid_credentials_user(menuai: menuai) -> None:
    """Test if we get the error message on invalid credentials."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"username": "test-username", "password": "test-password"},
    )

    assert result["errors"] == {"base": "invalid_auth"}


async def test_form_already_configured(menuai: menuai) -> None:
    """Test if we get the error message on already configured."""
    with patch(
        "menuai.components.devolo_home_control.Mydevolo.uuid",
        return_value="123456",
    ):
        MockConfigEntry(domain=DOMAIN, unique_id="123456", data={}).add_to_menuai(menuai)
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={"username": "test-username", "password": "test-password"},
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_form_advanced_options(menuai: menuai) -> None:
    """Test if we get the advanced options if user has enabled it."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER, "show_advanced_options": True},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.devolo_home_control.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.devolo_home_control.Mydevolo.uuid",
            return_value="123456",
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "devolo Home Control"
    assert result2["data"] == {
        "username": "test-username",
        "password": "test-password",
    }

    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_zeroconf(menuai: menuai) -> None:
    """Test that the zeroconf confirmation form is served."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=DISCOVERY_INFO,
    )

    assert result["step_id"] == "zeroconf_confirm"
    assert result["type"] is FlowResultType.FORM

    await _setup(menuai, result)


@pytest.mark.parametrize("credentials_valid", [False])
async def test_form_invalid_credentials_zeroconf(menuai: menuai) -> None:
    """Test if we get the error message on invalid credentials."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=DISCOVERY_INFO,
    )

    assert result["step_id"] == "zeroconf_confirm"
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"username": "test-username", "password": "test-password"},
    )

    assert result["errors"] == {"base": "invalid_auth"}


async def test_zeroconf_wrong_device(menuai: menuai) -> None:
    """Test that the zeroconf ignores wrong devices."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=DISCOVERY_INFO_WRONG_DEVOLO_DEVICE,
    )

    assert result["reason"] == "Not a devolo Home Control gateway."
    assert result["type"] is FlowResultType.ABORT

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=DISCOVERY_INFO_WRONG_DEVICE,
    )

    assert result["reason"] == "Not a devolo Home Control gateway."
    assert result["type"] is FlowResultType.ABORT


async def test_form_reauth(menuai: menuai) -> None:
    """Test that the reauth confirmation form is served."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        unique_id="123456",
        data={
            "username": "test-username",
            "password": "test-password",
        },
    )
    mock_config.add_to_menuai(menuai)
    result = await mock_config.start_reauth_flow(menuai)
    assert result["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM

    with (
        patch(
            "menuai.components.devolo_home_control.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.devolo_home_control.Mydevolo.uuid",
            return_value="123456",
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test-username-new", "password": "test-password-new"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize("credentials_valid", [False])
async def test_form_invalid_credentials_reauth(menuai: menuai) -> None:
    """Test if we get the error message on invalid credentials."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        unique_id="123456",
        data={
            "username": "test-username",
            "password": "test-password",
        },
    )
    mock_config.add_to_menuai(menuai)
    result = await mock_config.start_reauth_flow(menuai)

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"username": "test-username", "password": "test-password"},
    )

    assert result["errors"] == {"base": "invalid_auth"}


async def test_form_uuid_change_reauth(menuai: menuai) -> None:
    """Test that the reauth confirmation form is served."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        unique_id="123456",
        data={
            "username": "test-username",
            "password": "test-password",
        },
    )
    mock_config.add_to_menuai(menuai)
    result = await mock_config.start_reauth_flow(menuai)

    assert result["step_id"] == "reauth_confirm"
    assert result["type"] is FlowResultType.FORM

    with (
        patch(
            "menuai.components.devolo_home_control.async_setup_entry",
            return_value=True,
        ),
        patch(
            "menuai.components.devolo_home_control.Mydevolo.uuid",
            return_value="789123",
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test-username-new", "password": "test-password-new"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "reauth_failed"}


async def _setup(menuai: menuai, result: FlowResult) -> None:
    """Finish configuration steps."""
    with (
        patch(
            "menuai.components.devolo_home_control.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.devolo_home_control.Mydevolo.uuid",
            return_value="123456",
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test-username", "password": "test-password"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "devolo Home Control"
    assert result2["data"] == {
        "username": "test-username",
        "password": "test-password",
    }

    assert len(mock_setup_entry.mock_calls) == 1
