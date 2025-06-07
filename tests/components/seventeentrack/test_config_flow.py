"""Define tests for the 17Track config flow."""

from unittest.mock import AsyncMock

from pyseventeentrack.errors import SeventeenTrackError
import pytest

from menuai import config_entries
from menuai.components.seventeentrack import DOMAIN
from menuai.components.seventeentrack.const import (
    CONF_SHOW_ARCHIVED,
    CONF_SHOW_DELIVERED,
)
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

ACCOUNT_ID = "1234"

VALID_CONFIG = {
    CONF_USERNAME: "someemail@gmail.com",
    CONF_PASSWORD: "edc3eee7330e4fdda04489e3fbc283d0",
}

VALID_CONFIG_OLD = {
    CONF_USERNAME: "someemail@gmail.com",
    CONF_PASSWORD: "edc3eee7330e4fdda04489e3fbc283d0",
}


async def test_create_entry(
    menuai: menuai, mock_setup_entry: AsyncMock, mock_seventeentrack: AsyncMock
) -> None:
    """Test that the user step works."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        VALID_CONFIG,
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "someemail@gmail.com"
    assert result2["data"] == {
        CONF_PASSWORD: "edc3eee7330e4fdda04489e3fbc283d0",
        CONF_USERNAME: "someemail@gmail.com",
    }


@pytest.mark.parametrize(
    ("return_value", "side_effect", "error"),
    [
        (
            False,
            None,
            "invalid_auth",
        ),
        (
            True,
            SeventeenTrackError(),
            "cannot_connect",
        ),
    ],
)
async def test_flow_fails(
    menuai: menuai,
    mock_seventeentrack: AsyncMock,
    return_value,
    side_effect,
    error,
) -> None:
    """Test that the user step fails."""
    mock_seventeentrack.return_value.profile.login.return_value = return_value
    mock_seventeentrack.return_value.profile.login.side_effect = side_effect
    failed_result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data=VALID_CONFIG,
    )

    assert failed_result["errors"] == {"base": error}

    mock_seventeentrack.return_value.profile.login.return_value = True
    mock_seventeentrack.return_value.profile.login.side_effect = None

    result = await menuai.config_entries.flow.async_configure(
        failed_result["flow_id"],
        VALID_CONFIG,
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "someemail@gmail.com"
    assert result["data"] == {
        CONF_PASSWORD: "edc3eee7330e4fdda04489e3fbc283d0",
        CONF_USERNAME: "someemail@gmail.com",
    }


async def test_option_flow(menuai: menuai, mock_seventeentrack: AsyncMock) -> None:
    """Test option flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=VALID_CONFIG,
        options={
            CONF_SHOW_ARCHIVED: False,
            CONF_SHOW_DELIVERED: False,
        },
    )
    entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()
    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SHOW_ARCHIVED: True, CONF_SHOW_DELIVERED: False},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SHOW_ARCHIVED]
    assert not result["data"][CONF_SHOW_DELIVERED]
