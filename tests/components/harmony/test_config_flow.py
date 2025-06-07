"""Test the Logitech Harmony Hub config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from menuai import config_entries
from menuai.components.harmony.config_flow import CannotConnect
from menuai.components.harmony.const import DOMAIN, PREVIOUS_ACTIVE_ACTIVITY
from menuai.const import CONF_HOST, CONF_NAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.ssdp import SsdpServiceInfo

from tests.common import MockConfigEntry


def _get_mock_harmonyapi(connect=None, close=None):
    harmonyapi_mock = MagicMock()
    type(harmonyapi_mock).connect = AsyncMock(return_value=connect)
    type(harmonyapi_mock).close = AsyncMock(return_value=close)

    return harmonyapi_mock


async def test_user_form(menuai: menuai) -> None:
    """Test we get the user form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    harmonyapi = _get_mock_harmonyapi(connect=True)
    with (
        patch(
            "menuai.components.harmony.util.HarmonyAPI",
            return_value=harmonyapi,
        ),
        patch(
            "menuai.components.harmony.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "1.2.3.4", "name": "friend"},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "friend"
    assert result2["data"] == {"host": "1.2.3.4", "name": "friend"}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_ssdp(menuai: menuai) -> None:
    """Test we get the form with ssdp source."""

    with patch(
        "menuai.components.harmony.config_flow.HubConnector.get_remote_id",
        return_value=1234,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_SSDP},
            data=SsdpServiceInfo(
                ssdp_usn="mock_usn",
                ssdp_st="mock_st",
                ssdp_location="http://192.168.1.12:8088/description",
                upnp={
                    "friendlyName": "Harmony Hub",
                },
            ),
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "link"
    assert result["errors"] == {}
    assert result["description_placeholders"] == {
        "host": "Harmony Hub",
        "name": "192.168.1.12",
    }
    progress = menuai.config_entries.flow.async_progress()
    assert len(progress) == 1
    assert progress[0]["flow_id"] == result["flow_id"]
    assert progress[0]["context"]["confirm_only"] is True

    harmonyapi = _get_mock_harmonyapi(connect=True)

    with (
        patch(
            "menuai.components.harmony.util.HarmonyAPI",
            return_value=harmonyapi,
        ),
        patch(
            "menuai.components.harmony.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Harmony Hub"
    assert result2["data"] == {"host": "192.168.1.12", "name": "Harmony Hub"}
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_ssdp_fails_to_get_remote_id(menuai: menuai) -> None:
    """Test we abort if we cannot get the remote id."""

    with patch(
        "menuai.components.harmony.config_flow.HubConnector.get_remote_id",
        side_effect=aiohttp.ClientError,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_SSDP},
            data=SsdpServiceInfo(
                ssdp_usn="mock_usn",
                ssdp_st="mock_st",
                ssdp_location="http://192.168.1.12:8088/description",
                upnp={
                    "friendlyName": "Harmony Hub",
                },
            ),
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_form_ssdp_aborts_before_checking_remoteid_if_host_known(
    menuai: menuai,
) -> None:
    """Test we abort without connecting if the host is already known."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "2.2.2.2", "name": "any"},
    )
    config_entry.add_to_menuai(menuai)

    config_entry_without_host = MockConfigEntry(
        domain=DOMAIN,
        data={"name": "other"},
    )
    config_entry_without_host.add_to_menuai(menuai)

    harmonyapi = _get_mock_harmonyapi(connect=True)

    with patch(
        "menuai.components.harmony.util.HarmonyAPI",
        return_value=harmonyapi,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_SSDP},
            data=SsdpServiceInfo(
                ssdp_usn="mock_usn",
                ssdp_st="mock_st",
                ssdp_location="http://2.2.2.2:8088/description",
                upnp={
                    "friendlyName": "Harmony Hub",
                },
            ),
        )
    assert result["type"] is FlowResultType.ABORT


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.harmony.util.HarmonyAPI",
        side_effect=CannotConnect,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.2.3.4",
                "name": "friend",
                "activity": "Watch TV",
                "delay_secs": 0.2,
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_options_flow(menuai: menuai, mock_hc, mock_write_config) -> None:
    """Test config flow options."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="abcde12345",
        data={CONF_HOST: "1.2.3.4", CONF_NAME: "Guest Room"},
        options={"activity": "Watch TV", "delay_secs": 0.5},
    )

    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"activity": PREVIOUS_ACTIVE_ACTIVITY, "delay_secs": 0.4},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {
        "activity": PREVIOUS_ACTIVE_ACTIVITY,
        "delay_secs": 0.4,
    }
