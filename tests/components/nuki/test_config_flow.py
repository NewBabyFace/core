"""Test the nuki config flow."""

from unittest.mock import patch

from pynuki.bridge import InvalidCredentialsException
from requests.exceptions import RequestException

from menuai import config_entries
from menuai.components.nuki.const import DOMAIN
from menuai.const import CONF_HOST, CONF_PORT, CONF_TOKEN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.dhcp import DhcpServiceInfo

from .mock import DHCP_FORMATTED_MAC, HOST, MOCK_INFO, NAME, setup_nuki_integration


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.nuki.config_flow.NukiBridge.info",
            return_value=MOCK_INFO,
        ),
        patch(
            "menuai.components.nuki.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_PORT: 8080,
                CONF_TOKEN: "test-token",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "BC614E"
    assert result2["data"] == {
        CONF_HOST: "1.1.1.1",
        CONF_PORT: 8080,
        CONF_TOKEN: "test-token",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.nuki.config_flow.NukiBridge.info",
        side_effect=InvalidCredentialsException,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_PORT: 8080,
                CONF_TOKEN: "test-token",
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
        "menuai.components.nuki.config_flow.NukiBridge.info",
        side_effect=RequestException,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_PORT: 8080,
                CONF_TOKEN: "test-token",
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
        "menuai.components.nuki.config_flow.NukiBridge.info",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_PORT: 8080,
                CONF_TOKEN: "test-token",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_form_already_configured(menuai: menuai) -> None:
    """Test we get the form."""
    await setup_nuki_integration(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.nuki.config_flow.NukiBridge.info",
        return_value=MOCK_INFO,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_PORT: 8080,
                CONF_TOKEN: "test-token",
            },
        )

        assert result2["type"] is FlowResultType.ABORT
        assert result2["reason"] == "already_configured"


async def test_dhcp_flow(menuai: menuai) -> None:
    """Test that DHCP discovery for new bridge works."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        data=DhcpServiceInfo(hostname=NAME, ip=HOST, macaddress=DHCP_FORMATTED_MAC),
        context={"source": config_entries.SOURCE_DHCP},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == config_entries.SOURCE_USER

    with (
        patch(
            "menuai.components.nuki.config_flow.NukiBridge.info",
            return_value=MOCK_INFO,
        ),
        patch(
            "menuai.components.nuki.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "1.1.1.1",
                CONF_PORT: 8080,
                CONF_TOKEN: "test-token",
            },
        )

        assert result2["type"] is FlowResultType.CREATE_ENTRY
        assert result2["title"] == "BC614E"
        assert result2["data"] == {
            CONF_HOST: "1.1.1.1",
            CONF_PORT: 8080,
            CONF_TOKEN: "test-token",
        }

        await menuai.async_block_till_done()
        assert len(mock_setup_entry.mock_calls) == 1


async def test_dhcp_flow_already_configured(menuai: menuai) -> None:
    """Test that DHCP doesn't setup already configured devices."""
    await setup_nuki_integration(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        data=DhcpServiceInfo(hostname=NAME, ip=HOST, macaddress=DHCP_FORMATTED_MAC),
        context={"source": config_entries.SOURCE_DHCP},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_success(menuai: menuai) -> None:
    """Test starting a reauthentication flow."""
    entry = await setup_nuki_integration(menuai)

    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with (
        patch(
            "menuai.components.nuki.config_flow.NukiBridge.info",
            return_value=MOCK_INFO,
        ),
        patch(
            "menuai.components.nuki.async_setup_entry",
            return_value=True,
        ),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_TOKEN: "new-token"},
        )
        await menuai.async_block_till_done()

        assert result2["type"] is FlowResultType.ABORT
        assert result2["reason"] == "reauth_successful"
        assert entry.data[CONF_TOKEN] == "new-token"


async def test_reauth_invalid_auth(menuai: menuai) -> None:
    """Test starting a reauthentication flow with invalid auth."""
    entry = await setup_nuki_integration(menuai)

    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "menuai.components.nuki.config_flow.NukiBridge.info",
        side_effect=InvalidCredentialsException,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_TOKEN: "new-token"},
        )

        assert result2["type"] is FlowResultType.FORM
        assert result2["step_id"] == "reauth_confirm"
        assert result2["errors"] == {"base": "invalid_auth"}


async def test_reauth_cannot_connect(menuai: menuai) -> None:
    """Test starting a reauthentication flow with cannot connect."""
    entry = await setup_nuki_integration(menuai)

    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "menuai.components.nuki.config_flow.NukiBridge.info",
        side_effect=RequestException,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_TOKEN: "new-token"},
        )

        assert result2["type"] is FlowResultType.FORM
        assert result2["step_id"] == "reauth_confirm"
        assert result2["errors"] == {"base": "cannot_connect"}


async def test_reauth_unknown_exception(menuai: menuai) -> None:
    """Test starting a reauthentication flow with an unknown exception."""
    entry = await setup_nuki_integration(menuai)

    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "menuai.components.nuki.config_flow.NukiBridge.info",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_TOKEN: "new-token"},
        )

        assert result2["type"] is FlowResultType.FORM
        assert result2["step_id"] == "reauth_confirm"
        assert result2["errors"] == {"base": "unknown"}
