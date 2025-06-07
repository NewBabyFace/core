"""Test the Livisi MenuAI config flow."""

from unittest.mock import patch

from livisi import errors as livisi_errors
import pytest

from menuai.components.livisi.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import (
    VALID_CONFIG,
    mocked_livisi_controller,
    mocked_livisi_login,
    mocked_livisi_setup_entry,
)


async def test_create_entry(menuai: menuai) -> None:
    """Test create LIVISI entity."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with mocked_livisi_login(), mocked_livisi_controller(), mocked_livisi_setup_entry():
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            VALID_CONFIG,
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "SHC Classic"
        assert result["data"]["host"] == "1.1.1.1"
        assert result["data"]["password"] == "test"


@pytest.mark.parametrize(
    ("exception", "expected_reason"),
    [
        (livisi_errors.ShcUnreachableException(), "cannot_connect"),
        (livisi_errors.IncorrectIpAddressException(), "wrong_ip_address"),
        (livisi_errors.WrongCredentialException(), "wrong_password"),
    ],
)
async def test_create_entity_after_login_error(
    menuai: menuai, exception: livisi_errors.LivisiException, expected_reason: str
) -> None:
    """Test the LIVISI integration can create an entity after the user had login errors."""
    with patch(
        "menuai.components.livisi.config_flow.AioLivisi.async_set_token",
        side_effect=exception,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
        )
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], VALID_CONFIG
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == expected_reason
    with mocked_livisi_login(), mocked_livisi_controller(), mocked_livisi_setup_entry():
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=VALID_CONFIG,
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
