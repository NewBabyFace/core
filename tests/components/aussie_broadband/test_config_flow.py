"""Test the Aussie Broadband config flow."""

from unittest.mock import patch

from aiohttp import ClientConnectionError
from aussiebb.asyncio import AuthenticationException

from menuai import config_entries
from menuai.components.aussie_broadband.const import DOMAIN
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .common import FAKE_DATA, FAKE_SERVICES

from tests.common import MockConfigEntry

TEST_USERNAME = FAKE_DATA[CONF_USERNAME]
TEST_PASSWORD = FAKE_DATA[CONF_PASSWORD]


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""
    result1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result1["type"] is FlowResultType.FORM
    assert result1["errors"] is None

    with (
        patch("aussiebb.asyncio.AussieBB.__init__", return_value=None),
        patch("aussiebb.asyncio.AussieBB.login", return_value=True),
        patch("aussiebb.asyncio.AussieBB.get_services", return_value=FAKE_SERVICES),
        patch(
            "menuai.components.aussie_broadband.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result1["flow_id"],
            FAKE_DATA,
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == TEST_USERNAME
    assert result2["data"] == FAKE_DATA
    assert len(mock_setup_entry.mock_calls) == 1


async def test_already_configured(menuai: menuai) -> None:
    """Test already configured."""
    # Setup an entry
    result1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch("aussiebb.asyncio.AussieBB.__init__", return_value=None),
        patch("aussiebb.asyncio.AussieBB.login", return_value=True),
        patch(
            "aussiebb.asyncio.AussieBB.get_services", return_value=[FAKE_SERVICES[0]]
        ),
        patch(
            "menuai.components.aussie_broadband.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        await menuai.config_entries.flow.async_configure(
            result1["flow_id"],
            FAKE_DATA,
        )
        await menuai.async_block_till_done()

    # Test Already configured
    result3 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with (
        patch("aussiebb.asyncio.AussieBB.__init__", return_value=None),
        patch("aussiebb.asyncio.AussieBB.login", return_value=True),
        patch(
            "aussiebb.asyncio.AussieBB.get_services", return_value=[FAKE_SERVICES[0]]
        ),
        patch(
            "menuai.components.aussie_broadband.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result4 = await menuai.config_entries.flow.async_configure(
            result3["flow_id"],
            FAKE_DATA,
        )
        await menuai.async_block_till_done()

    assert result4["type"] is FlowResultType.ABORT
    assert len(mock_setup_entry.mock_calls) == 0


async def test_no_services(menuai: menuai) -> None:
    """Test when there are no services."""
    result1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result1["type"] is FlowResultType.FORM
    assert result1["errors"] is None

    with (
        patch("aussiebb.asyncio.AussieBB.__init__", return_value=None),
        patch("aussiebb.asyncio.AussieBB.login", return_value=True),
        patch("aussiebb.asyncio.AussieBB.get_services", return_value=[]),
        patch(
            "menuai.components.aussie_broadband.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result1["flow_id"],
            FAKE_DATA,
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "no_services_found"
    assert len(mock_setup_entry.mock_calls) == 0


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test invalid auth is handled."""
    result1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch("aussiebb.asyncio.AussieBB.__init__", return_value=None),
        patch("aussiebb.asyncio.AussieBB.login", side_effect=AuthenticationException()),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result1["flow_id"],
            FAKE_DATA,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_network_issue(menuai: menuai) -> None:
    """Test network issues are handled."""
    result1 = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch("aussiebb.asyncio.AussieBB.__init__", return_value=None),
        patch("aussiebb.asyncio.AussieBB.login", side_effect=ClientConnectionError()),
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result1["flow_id"],
            FAKE_DATA,
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_reauth(menuai: menuai) -> None:
    """Test reauth flow."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        data=FAKE_DATA,
        unique_id=FAKE_DATA[CONF_USERNAME],
    )
    mock_entry.add_to_menuai(menuai)

    # Test failed reauth
    result5 = await mock_entry.start_reauth_flow(menuai)
    assert result5["step_id"] == "reauth_confirm"

    with (
        patch("aussiebb.asyncio.AussieBB.__init__", return_value=None),
        patch("aussiebb.asyncio.AussieBB.login", side_effect=AuthenticationException()),
        patch(
            "aussiebb.asyncio.AussieBB.get_services", return_value=[FAKE_SERVICES[0]]
        ),
    ):
        result6 = await menuai.config_entries.flow.async_configure(
            result5["flow_id"],
            {
                CONF_PASSWORD: "test-wrongpassword",
            },
        )
        await menuai.async_block_till_done()

        assert result6["step_id"] == "reauth_confirm"

    # Test successful reauth
    with (
        patch("aussiebb.asyncio.AussieBB.__init__", return_value=None),
        patch("aussiebb.asyncio.AussieBB.login", return_value=True),
        patch(
            "aussiebb.asyncio.AussieBB.get_services", return_value=[FAKE_SERVICES[0]]
        ),
    ):
        result7 = await menuai.config_entries.flow.async_configure(
            result6["flow_id"],
            {
                CONF_PASSWORD: "test-newpassword",
            },
        )
        await menuai.async_block_till_done()

        assert result7["type"] is FlowResultType.ABORT
        assert result7["reason"] == "reauth_successful"
