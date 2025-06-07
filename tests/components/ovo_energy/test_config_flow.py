"""Test the OVO Energy config flow."""

from unittest.mock import patch

import aiohttp

from menuai import config_entries
from menuai.components.ovo_energy.const import CONF_ACCOUNT, DOMAIN
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

FIXTURE_REAUTH_INPUT = {CONF_PASSWORD: "something1"}
FIXTURE_USER_INPUT = {
    CONF_USERNAME: "example@example.com",
    CONF_PASSWORD: "something",
    CONF_ACCOUNT: "123456",
}

UNIQUE_ID = "example@example.com"


async def test_show_form(menuai: menuai) -> None:
    """Test that the setup form is served."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_authorization_error(menuai: menuai) -> None:
    """Test we show user form on connection error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with (
        patch(
            "menuai.components.ovo_energy.config_flow.OVOEnergy.authenticate",
            return_value=False,
        ),
        patch(
            "menuai.components.ovo_energy.config_flow.OVOEnergy.bootstrap_accounts",
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            FIXTURE_USER_INPUT,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "user"
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_connection_error(menuai: menuai) -> None:
    """Test we show user form on connection error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "menuai.components.ovo_energy.config_flow.OVOEnergy.authenticate",
        side_effect=aiohttp.ClientError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            FIXTURE_USER_INPUT,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "user"
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_full_flow_implementation(menuai: menuai) -> None:
    """Test registering an integration and finishing flow works."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with (
        patch(
            "menuai.components.ovo_energy.config_flow.OVOEnergy.authenticate",
            return_value=True,
        ),
        patch(
            "menuai.components.ovo_energy.config_flow.OVOEnergy.bootstrap_accounts",
        ),
        patch(
            "menuai.components.ovo_energy.config_flow.OVOEnergy.username",
            "some_name",
        ),
        patch(
            "menuai.components.ovo_energy.async_setup_entry",
            return_value=True,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            FIXTURE_USER_INPUT,
        )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_USERNAME] == FIXTURE_USER_INPUT[CONF_USERNAME]
    assert result2["data"][CONF_PASSWORD] == FIXTURE_USER_INPUT[CONF_PASSWORD]
    assert result2["data"][CONF_ACCOUNT] == FIXTURE_USER_INPUT[CONF_ACCOUNT]


async def test_reauth_authorization_error(menuai: menuai) -> None:
    """Test we show user form on authorization error."""
    mock_config = MockConfigEntry(
        domain=DOMAIN, unique_id=UNIQUE_ID, data=FIXTURE_USER_INPUT
    )
    mock_config.add_to_menuai(menuai)
    result = await mock_config.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    with patch(
        "menuai.components.ovo_energy.config_flow.OVOEnergy.authenticate",
        return_value=False,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            FIXTURE_REAUTH_INPUT,
        )
        await menuai.async_block_till_done()

        assert result2["type"] is FlowResultType.FORM
        assert result2["step_id"] == "reauth_confirm"
        assert result2["errors"] == {"base": "authorization_error"}


async def test_reauth_connection_error(menuai: menuai) -> None:
    """Test we show user form on connection error."""
    mock_config = MockConfigEntry(
        domain=DOMAIN, unique_id=UNIQUE_ID, data=FIXTURE_USER_INPUT
    )
    mock_config.add_to_menuai(menuai)
    result = await mock_config.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {}

    with patch(
        "menuai.components.ovo_energy.config_flow.OVOEnergy.authenticate",
        side_effect=aiohttp.ClientError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            FIXTURE_REAUTH_INPUT,
        )
        await menuai.async_block_till_done()

        assert result2["type"] is FlowResultType.FORM
        assert result2["step_id"] == "reauth_confirm"
        assert result2["errors"] == {"base": "connection_error"}


async def test_reauth_flow(menuai: menuai) -> None:
    """Test reauth works."""
    mock_config = MockConfigEntry(
        domain=DOMAIN, unique_id=UNIQUE_ID, data=FIXTURE_USER_INPUT
    )
    mock_config.add_to_menuai(menuai)
    result = await mock_config.start_reauth_flow(menuai)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {}

    with patch(
        "menuai.components.ovo_energy.config_flow.OVOEnergy.authenticate",
        return_value=False,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            FIXTURE_REAUTH_INPUT,
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"
        assert result["errors"] == {"base": "authorization_error"}

    with (
        patch(
            "menuai.components.ovo_energy.config_flow.OVOEnergy.authenticate",
            return_value=True,
        ),
        patch(
            "menuai.components.ovo_energy.config_flow.OVOEnergy.username",
            return_value=FIXTURE_USER_INPUT[CONF_USERNAME],
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            FIXTURE_REAUTH_INPUT,
        )
        await menuai.async_block_till_done()

        assert result2["type"] is FlowResultType.ABORT
        assert result2["reason"] == "reauth_successful"
