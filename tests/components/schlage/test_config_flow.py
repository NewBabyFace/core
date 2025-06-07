"""Test the Schlage config flow."""

from unittest.mock import AsyncMock, Mock

from pyschlage.exceptions import Error as PyschlageError, NotAuthorizedError
import pytest

from menuai import config_entries
from menuai.components.schlage.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import MockSchlageConfigEntry

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


@pytest.mark.parametrize(
    "username",
    [
        "test-username",
        "TEST-USERNAME",
    ],
)
async def test_form(
    menuai: menuai,
    mock_setup_entry: AsyncMock,
    mock_pyschlage_auth: Mock,
    username: str,
) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "username": username,
            "password": "test-password",
        },
    )
    await menuai.async_block_till_done()

    mock_pyschlage_auth.authenticate.assert_called_once_with()
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test-username"
    assert result2["data"] == {
        "username": "test-username",
        "password": "test-password",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_requires_unique_id(
    menuai: menuai,
    mock_added_config_entry: MockConfigEntry,
    mock_pyschlage_auth: Mock,
) -> None:
    """Test entries have unique ids."""
    init_result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert init_result["type"] is FlowResultType.FORM
    assert init_result["errors"] == {}

    create_result = await menuai.config_entries.flow.async_configure(
        init_result["flow_id"],
        {
            "username": "test-username",
            "password": "test-password",
        },
    )
    await menuai.async_block_till_done()

    mock_pyschlage_auth.authenticate.assert_called_once_with()
    assert create_result["type"] is FlowResultType.ABORT
    assert create_result["reason"] == "already_configured"


async def test_form_invalid_auth(
    menuai: menuai, mock_pyschlage_auth: Mock
) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_pyschlage_auth.authenticate.side_effect = NotAuthorizedError
    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "username": "test-username",
            "password": "test-password",
        },
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_unknown(menuai: menuai, mock_pyschlage_auth: Mock) -> None:
    """Test we handle unknown error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    mock_pyschlage_auth.authenticate.side_effect = PyschlageError
    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "username": "test-username",
            "password": "test-password",
        },
    )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_reauth(
    menuai: menuai,
    mock_added_config_entry: MockSchlageConfigEntry,
    mock_pyschlage_auth: Mock,
) -> None:
    """Test reauth flow."""
    mock_added_config_entry.async_start_reauth(menuai)
    await menuai.async_block_till_done()

    flows = menuai.config_entries.flow.async_progress()
    result = flows[-1]
    assert result["step_id"] == "reauth_confirm"

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"password": "new-password"},
    )
    await menuai.async_block_till_done()

    mock_pyschlage_auth.authenticate.assert_called_once_with()
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert mock_added_config_entry.data == {
        "username": "asdf@asdf.com",
        "password": "new-password",
    }


async def test_reauth_invalid_auth(
    menuai: menuai,
    mock_added_config_entry: MockSchlageConfigEntry,
    mock_setup_entry: AsyncMock,
    mock_pyschlage_auth: Mock,
) -> None:
    """Test reauth flow."""
    mock_added_config_entry.async_start_reauth(menuai)
    await menuai.async_block_till_done()

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    [result] = flows
    assert result["step_id"] == "reauth_confirm"

    mock_pyschlage_auth.authenticate.reset_mock()
    mock_pyschlage_auth.authenticate.side_effect = NotAuthorizedError
    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"password": "new-password"},
    )
    await menuai.async_block_till_done()

    mock_pyschlage_auth.authenticate.assert_called_once_with()
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_reauth_wrong_account(
    menuai: menuai,
    mock_added_config_entry: MockSchlageConfigEntry,
    mock_setup_entry: AsyncMock,
    mock_pyschlage_auth: Mock,
) -> None:
    """Test reauth flow."""
    mock_pyschlage_auth.user_id = "bad-user-id"
    mock_added_config_entry.async_start_reauth(menuai)
    await menuai.async_block_till_done()

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1
    [result] = flows
    assert result["step_id"] == "reauth_confirm"

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {"password": "new-password"},
    )
    await menuai.async_block_till_done()

    mock_pyschlage_auth.authenticate.assert_called_once_with()
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "wrong_account"
    assert mock_added_config_entry.data == {
        "username": "asdf@asdf.com",
        "password": "hunter2",
    }
    assert len(mock_setup_entry.mock_calls) == 1
