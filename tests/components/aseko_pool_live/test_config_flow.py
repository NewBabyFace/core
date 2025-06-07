"""Test the Aseko Pool Live config flow."""

from unittest.mock import patch

from aioaseko import AsekoAPIError, AsekoInvalidCredentials, User
import pytest

from menuai import config_entries
from menuai.components.aseko_pool_live.const import DOMAIN
from menuai.const import CONF_EMAIL, CONF_PASSWORD
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_async_step_user_form(menuai: menuai) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}


async def test_async_step_user_success(menuai: menuai, user: User) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "menuai.components.aseko_pool_live.config_flow.Aseko.login",
            return_value=user,
        ),
        patch(
            "menuai.components.aseko_pool_live.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "aseko@example.com",
                CONF_PASSWORD: "passw0rd",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "aseko@example.com"
    assert result2["data"] == {
        CONF_EMAIL: "aseko@example.com",
        CONF_PASSWORD: "passw0rd",
    }
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("error_web", "reason"),
    [
        (AsekoAPIError, "cannot_connect"),
        (AsekoInvalidCredentials, "invalid_auth"),
        (Exception, "unknown"),
    ],
)
async def test_async_step_user_exception(
    menuai: menuai, user: User, error_web: Exception, reason: str
) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.aseko_pool_live.config_flow.Aseko.login",
        return_value=user,
        side_effect=error_web,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "aseko@example.com",
                CONF_PASSWORD: "passw0rd",
            },
        )

        assert result2["type"] is FlowResultType.FORM
        assert result2["errors"] == {"base": reason}


@pytest.mark.parametrize(
    ("error_web", "reason"),
    [
        (AsekoAPIError, "cannot_connect"),
        (AsekoInvalidCredentials, "invalid_auth"),
        (Exception, "unknown"),
    ],
)
async def test_get_account_info_exceptions(
    menuai: menuai, user: User, error_web: Exception, reason: str
) -> None:
    """Test we handle config flow exceptions."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.aseko_pool_live.config_flow.Aseko.login",
        return_value=user,
        side_effect=error_web,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "aseko@example.com",
                CONF_PASSWORD: "passw0rd",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": reason}


async def test_async_step_reauth_success(menuai: menuai, user: User) -> None:
    """Test successful reauthentication."""

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="a_user_id",
        data={CONF_EMAIL: "aseko@example.com", CONF_PASSWORD: "passw0rd"},
        version=2,
    )
    mock_entry.add_to_menuai(menuai)

    result = await mock_entry.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.aseko_pool_live.config_flow.Aseko.login",
            return_value=user,
        ),
        patch(
            "menuai.components.aseko_pool_live.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_EMAIL: "aseko@example.com", CONF_PASSWORD: "new_password"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert len(mock_setup_entry.mock_calls) == 1
    assert mock_entry.unique_id == "a_user_id"
    assert dict(mock_entry.data) == {
        CONF_EMAIL: "aseko@example.com",
        CONF_PASSWORD: "new_password",
    }


async def test_async_step_reauth_mismatch(menuai: menuai, user: User) -> None:
    """Test mismatch reauthentication."""

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="UID",
        data={CONF_EMAIL: "aseko@example.com", CONF_PASSWORD: "passw0rd"},
        version=2,
    )
    mock_entry.add_to_menuai(menuai)

    result = await mock_entry.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.aseko_pool_live.config_flow.Aseko.login",
            return_value=user,
        ),
        patch(
            "menuai.components.aseko_pool_live.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_EMAIL: "aseko@example.com", CONF_PASSWORD: "new_password"},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"
    assert len(mock_setup_entry.mock_calls) == 0
    assert mock_entry.unique_id == "UID"
    assert dict(mock_entry.data) == {
        CONF_EMAIL: "aseko@example.com",
        CONF_PASSWORD: "passw0rd",
    }


@pytest.mark.parametrize(
    ("error_web", "reason"),
    [
        (AsekoAPIError, "cannot_connect"),
        (AsekoInvalidCredentials, "invalid_auth"),
        (Exception, "unknown"),
    ],
)
async def test_async_step_reauth_exception(
    menuai: menuai, user: User, error_web: Exception, reason: str
) -> None:
    """Test we get the form."""

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="UID",
        data={CONF_EMAIL: "aseko@example.com"},
    )
    mock_entry.add_to_menuai(menuai)

    result = await mock_entry.start_reauth_flow(menuai)

    with patch(
        "menuai.components.aseko_pool_live.config_flow.Aseko.login",
        return_value=user,
        side_effect=error_web,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_EMAIL: "aseko@example.com",
                CONF_PASSWORD: "passw0rd",
            },
        )

        assert result2["type"] is FlowResultType.FORM
        assert result2["errors"] == {"base": reason}
