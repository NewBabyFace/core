"""Test the UniFi Protect config flow."""

from __future__ import annotations

from dataclasses import asdict
import socket
from unittest.mock import patch

import pytest
from uiprotect import NotAuthorized, NvrError, ProtectApiClient
from uiprotect.data import NVR, Bootstrap, CloudAccount

from menuai import config_entries
from menuai.components.unifiprotect.const import (
    CONF_ALL_UPDATES,
    CONF_DISABLE_RTSP,
    CONF_OVERRIDE_CHOST,
    DOMAIN,
)
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers import device_registry as dr
from menuai.helpers.service_info.dhcp import DhcpServiceInfo
from menuai.helpers.service_info.ssdp import SsdpServiceInfo

from . import (
    DEVICE_HOSTNAME,
    DEVICE_IP_ADDRESS,
    DEVICE_MAC_ADDRESS,
    DIRECT_CONNECT_DOMAIN,
    UNIFI_DISCOVERY,
    UNIFI_DISCOVERY_PARTIAL,
    _patch_discovery,
)
from .conftest import MAC_ADDR

from tests.common import MockConfigEntry

DHCP_DISCOVERY = DhcpServiceInfo(
    hostname=DEVICE_HOSTNAME,
    ip=DEVICE_IP_ADDRESS,
    macaddress=DEVICE_MAC_ADDRESS.lower().replace(":", ""),
)
SSDP_DISCOVERY = (
    SsdpServiceInfo(
        ssdp_usn="mock_usn",
        ssdp_st="mock_st",
        ssdp_location=f"http://{DEVICE_IP_ADDRESS}:41417/rootDesc.xml",
        upnp={
            "friendlyName": "UniFi Dream Machine",
            "modelDescription": "UniFi Dream Machine Pro",
            "serialNumber": DEVICE_MAC_ADDRESS,
        },
    ),
)

UNIFI_DISCOVERY_DICT = asdict(UNIFI_DISCOVERY)
UNIFI_DISCOVERY_DICT_PARTIAL = asdict(UNIFI_DISCOVERY_PARTIAL)


async def test_form(menuai: menuai, bootstrap: Bootstrap, nvr: NVR) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    bootstrap.nvr = nvr
    with (
        patch(
            "menuai.components.unifiprotect.config_flow.ProtectApiClient.get_bootstrap",
            return_value=bootstrap,
        ),
        patch(
            "menuai.components.unifiprotect.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.unifiprotect.async_setup",
            return_value=True,
        ) as mock_setup,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "username": "test-username",
                "password": "test-password",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "UnifiProtect"
    assert result2["data"] == {
        "host": "1.1.1.1",
        "username": "test-username",
        "password": "test-password",
        "id": "UnifiProtect",
        "port": 443,
        "verify_ssl": False,
    }
    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_setup.mock_calls) == 1


async def test_form_version_too_old(
    menuai: menuai, bootstrap: Bootstrap, old_nvr: NVR
) -> None:
    """Test we handle the version being too old."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    bootstrap.nvr = old_nvr
    with patch(
        "menuai.components.unifiprotect.config_flow.ProtectApiClient.get_bootstrap",
        return_value=bootstrap,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "username": "test-username",
                "password": "test-password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "protect_version"}


async def test_form_invalid_auth(menuai: menuai) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.unifiprotect.config_flow.ProtectApiClient.get_bootstrap",
        side_effect=NotAuthorized,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "username": "test-username",
                "password": "test-password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"password": "invalid_auth"}


async def test_form_cloud_user(
    menuai: menuai, bootstrap: Bootstrap, cloud_account: CloudAccount
) -> None:
    """Test we handle cloud users."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    user = bootstrap.users[bootstrap.auth_user_id]
    user.cloud_account = cloud_account
    bootstrap.users[bootstrap.auth_user_id] = user
    with patch(
        "menuai.components.unifiprotect.config_flow.ProtectApiClient.get_bootstrap",
        return_value=bootstrap,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "username": "test-username",
                "password": "test-password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cloud_user"}


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.unifiprotect.config_flow.ProtectApiClient.get_bootstrap",
        side_effect=NvrError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "username": "test-username",
                "password": "test-password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_reauth_auth(
    menuai: menuai, bootstrap: Bootstrap, nvr: NVR
) -> None:
    """Test we handle reauth auth."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "1.1.1.1",
            "username": "test-username",
            "password": "test-password",
            "id": "UnifiProtect",
            "port": 443,
            "verify_ssl": False,
        },
        unique_id=dr.format_mac(MAC_ADDR),
    )
    mock_config.add_to_menuai(menuai)

    result = await mock_config.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]
    flows = menuai.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert flows[0]["context"]["title_placeholders"] == {
        "ip_address": "1.1.1.1",
        "name": "Mock Title",
    }

    with patch(
        "menuai.components.unifiprotect.config_flow.ProtectApiClient.get_bootstrap",
        side_effect=NotAuthorized,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "test-username",
                "password": "test-password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"password": "invalid_auth"}
    assert result2["step_id"] == "reauth_confirm"

    bootstrap.nvr = nvr
    with (
        patch(
            "menuai.components.unifiprotect.config_flow.ProtectApiClient.get_bootstrap",
            return_value=bootstrap,
        ),
        patch(
            "menuai.components.unifiprotect.async_setup",
            return_value=True,
        ) as mock_setup,
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                "username": "test-username",
                "password": "new-password",
            },
        )
        await menuai.async_block_till_done()

    assert result3["type"] is FlowResultType.ABORT
    assert result3["reason"] == "reauth_successful"
    assert len(mock_setup.mock_calls) == 1


async def test_form_options(menuai: menuai, ufp_client: ProtectApiClient) -> None:
    """Test we handle options flows."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "1.1.1.1",
            "username": "test-username",
            "password": "test-password",
            "id": "UnifiProtect",
            "port": 443,
            "verify_ssl": False,
            "max_media": 1000,
        },
        version=2,
        unique_id=dr.format_mac(MAC_ADDR),
    )
    mock_config.add_to_menuai(menuai)

    with (
        _patch_discovery(),
        patch(
            "menuai.components.unifiprotect.utils.ProtectApiClient"
        ) as mock_api,
    ):
        mock_api.return_value = ufp_client

        await menuai.config_entries.async_setup(mock_config.entry_id)
        await menuai.async_block_till_done()
        assert mock_config.state is ConfigEntryState.LOADED

        result = await menuai.config_entries.options.async_init(mock_config.entry_id)
        assert result["type"] is FlowResultType.FORM
        assert not result["errors"]
        assert result["step_id"] == "init"

        result2 = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_DISABLE_RTSP: True,
                CONF_ALL_UPDATES: True,
                CONF_OVERRIDE_CHOST: True,
            },
        )

        assert result2["type"] is FlowResultType.CREATE_ENTRY
        assert result2["data"] == {
            "all_updates": True,
            "disable_rtsp": True,
            "override_connection_host": True,
            "max_media": 1000,
            "allow_ea_channel": False,
        }
        await menuai.async_block_till_done()
        await menuai.config_entries.async_unload(mock_config.entry_id)


@pytest.mark.parametrize(
    ("source", "data"),
    [
        (config_entries.SOURCE_DHCP, DHCP_DISCOVERY),
        (config_entries.SOURCE_SSDP, SSDP_DISCOVERY),
    ],
)
async def test_discovered_by_ssdp_or_dhcp(
    menuai: menuai, source: str, data: DhcpServiceInfo | SsdpServiceInfo
) -> None:
    """Test we handoff to unifi-discovery when discovered via ssdp or dhcp."""

    with _patch_discovery():
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": source},
            data=data,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "discovery_started"


async def test_discovered_by_unifi_discovery_direct_connect(
    menuai: menuai, bootstrap: Bootstrap, nvr: NVR
) -> None:
    """Test a discovery from unifi-discovery."""

    with _patch_discovery():
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=UNIFI_DISCOVERY_DICT,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"
    flows = menuai.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert flows[0]["context"]["title_placeholders"] == {
        "ip_address": DEVICE_IP_ADDRESS,
        "name": DEVICE_HOSTNAME,
    }

    assert not result["errors"]

    bootstrap.nvr = nvr
    with (
        patch(
            "menuai.components.unifiprotect.config_flow.ProtectApiClient.get_bootstrap",
            return_value=bootstrap,
        ),
        patch(
            "menuai.components.unifiprotect.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.unifiprotect.async_setup",
            return_value=True,
        ) as mock_setup,
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
    assert result2["title"] == "UnifiProtect"
    assert result2["data"] == {
        "host": DIRECT_CONNECT_DOMAIN,
        "username": "test-username",
        "password": "test-password",
        "id": "UnifiProtect",
        "port": 443,
        "verify_ssl": True,
    }
    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_setup.mock_calls) == 1


async def test_discovered_by_unifi_discovery_direct_connect_updated(
    menuai: menuai,
) -> None:
    """Test a discovery from unifi-discovery updates the direct connect host."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "y.ui.direct",
            "username": "test-username",
            "password": "test-password",
            "id": "UnifiProtect",
            "port": 443,
            "verify_ssl": True,
        },
        version=2,
        unique_id=DEVICE_MAC_ADDRESS.replace(":", "").upper(),
    )
    mock_config.add_to_menuai(menuai)

    with _patch_discovery():
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=UNIFI_DISCOVERY_DICT,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config.data[CONF_HOST] == DIRECT_CONNECT_DOMAIN


async def test_discovered_by_unifi_discovery_direct_connect_updated_but_not_using_direct_connect(
    menuai: menuai,
) -> None:
    """Test a discovery from unifi-discovery updates the host but not direct connect if its not in use."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "1.2.2.2",
            "username": "test-username",
            "password": "test-password",
            "id": "UnifiProtect",
            "port": 443,
            "verify_ssl": False,
        },
        version=2,
        unique_id=DEVICE_MAC_ADDRESS.replace(":", "").upper(),
    )
    mock_config.add_to_menuai(menuai)

    with (
        _patch_discovery(),
        patch(
            "menuai.components.unifiprotect.config_flow.async_console_is_alive",
            return_value=False,
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=UNIFI_DISCOVERY_DICT,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config.data[CONF_HOST] == "127.0.0.1"


async def test_discovered_by_unifi_discovery_does_not_update_ip_when_console_is_still_online(
    menuai: menuai,
) -> None:
    """Test a discovery from unifi-discovery does not update the ip unless the console at the old ip is offline."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "1.2.2.2",
            "username": "test-username",
            "password": "test-password",
            "id": "UnifiProtect",
            "port": 443,
            "verify_ssl": False,
        },
        version=2,
        unique_id=DEVICE_MAC_ADDRESS.replace(":", "").upper(),
    )
    mock_config.add_to_menuai(menuai)

    with (
        _patch_discovery(),
        patch(
            "menuai.components.unifiprotect.config_flow.async_console_is_alive",
            return_value=True,
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=UNIFI_DISCOVERY_DICT,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config.data[CONF_HOST] == "1.2.2.2"


async def test_discovered_host_not_updated_if_existing_is_a_hostname(
    menuai: menuai,
) -> None:
    """Test we only update the host if its an ip address from discovery."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "a.hostname",
            "username": "test-username",
            "password": "test-password",
            "id": "UnifiProtect",
            "port": 443,
            "verify_ssl": True,
        },
        unique_id=DEVICE_MAC_ADDRESS.upper().replace(":", ""),
    )
    mock_config.add_to_menuai(menuai)

    with _patch_discovery():
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=UNIFI_DISCOVERY_DICT,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config.data[CONF_HOST] == "a.hostname"


async def test_discovered_by_unifi_discovery(
    menuai: menuai, bootstrap: Bootstrap, nvr: NVR
) -> None:
    """Test a discovery from unifi-discovery."""

    with _patch_discovery():
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=UNIFI_DISCOVERY_DICT,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"
    flows = menuai.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert flows[0]["context"]["title_placeholders"] == {
        "ip_address": DEVICE_IP_ADDRESS,
        "name": DEVICE_HOSTNAME,
    }

    assert not result["errors"]

    bootstrap.nvr = nvr
    with (
        patch(
            "menuai.components.unifiprotect.config_flow.ProtectApiClient.get_bootstrap",
            side_effect=[NotAuthorized, bootstrap],
        ),
        patch(
            "menuai.components.unifiprotect.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.unifiprotect.async_setup",
            return_value=True,
        ) as mock_setup,
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
    assert result2["title"] == "UnifiProtect"
    assert result2["data"] == {
        "host": DEVICE_IP_ADDRESS,
        "username": "test-username",
        "password": "test-password",
        "id": "UnifiProtect",
        "port": 443,
        "verify_ssl": False,
    }
    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_setup.mock_calls) == 1


async def test_discovered_by_unifi_discovery_partial(
    menuai: menuai, bootstrap: Bootstrap, nvr: NVR
) -> None:
    """Test a discovery from unifi-discovery partial."""

    with _patch_discovery():
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=UNIFI_DISCOVERY_DICT_PARTIAL,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"
    flows = menuai.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert flows[0]["context"]["title_placeholders"] == {
        "ip_address": DEVICE_IP_ADDRESS,
        "name": "NVR DDEEFF",
    }

    assert not result["errors"]

    bootstrap.nvr = nvr
    with (
        patch(
            "menuai.components.unifiprotect.config_flow.ProtectApiClient.get_bootstrap",
            return_value=bootstrap,
        ),
        patch(
            "menuai.components.unifiprotect.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.unifiprotect.async_setup",
            return_value=True,
        ) as mock_setup,
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
    assert result2["title"] == "UnifiProtect"
    assert result2["data"] == {
        "host": DEVICE_IP_ADDRESS,
        "username": "test-username",
        "password": "test-password",
        "id": "UnifiProtect",
        "port": 443,
        "verify_ssl": False,
    }
    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_setup.mock_calls) == 1


async def test_discovered_by_unifi_discovery_direct_connect_on_different_interface(
    menuai: menuai,
) -> None:
    """Test a discovery from unifi-discovery from an alternate interface."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": DIRECT_CONNECT_DOMAIN,
            "username": "test-username",
            "password": "test-password",
            "id": "UnifiProtect",
            "port": 443,
            "verify_ssl": True,
        },
        unique_id="FFFFFFAAAAAA",
    )
    mock_config.add_to_menuai(menuai)

    with _patch_discovery():
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=UNIFI_DISCOVERY_DICT,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_discovered_by_unifi_discovery_direct_connect_on_different_interface_ip_matches(
    menuai: menuai,
) -> None:
    """Test a discovery from unifi-discovery from an alternate interface when the ip matches."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "127.0.0.1",
            "username": "test-username",
            "password": "test-password",
            "id": "UnifiProtect",
            "port": 443,
            "verify_ssl": True,
        },
        unique_id="FFFFFFAAAAAA",
    )
    mock_config.add_to_menuai(menuai)

    with _patch_discovery():
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=UNIFI_DISCOVERY_DICT,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_discovered_by_unifi_discovery_direct_connect_on_different_interface_resolver(
    menuai: menuai,
) -> None:
    """Test a discovery from unifi-discovery from an alternate interface when direct connect domain resolves to host ip."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "y.ui.direct",
            "username": "test-username",
            "password": "test-password",
            "id": "UnifiProtect",
            "port": 443,
            "verify_ssl": True,
        },
        unique_id="FFFFFFAAAAAA",
    )
    mock_config.add_to_menuai(menuai)

    other_ip_dict = UNIFI_DISCOVERY_DICT.copy()
    other_ip_dict["source_ip"] = "127.0.0.1"
    other_ip_dict["direct_connect_domain"] = "nomatchsameip.ui.direct"

    with (
        _patch_discovery(),
        patch.object(
            menuai.loop,
            "getaddrinfo",
            return_value=[(socket.AF_INET, None, None, None, ("127.0.0.1", 443))],
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=other_ip_dict,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_discovered_by_unifi_discovery_direct_connect_on_different_interface_resolver_fails(
    menuai: menuai, bootstrap: Bootstrap, nvr: NVR
) -> None:
    """Test we can still configure if the resolver fails."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "y.ui.direct",
            "username": "test-username",
            "password": "test-password",
            "id": "UnifiProtect",
            "port": 443,
            "verify_ssl": True,
        },
        unique_id="FFFFFFAAAAAA",
    )
    mock_config.add_to_menuai(menuai)

    other_ip_dict = UNIFI_DISCOVERY_DICT.copy()
    other_ip_dict["source_ip"] = "127.0.0.2"
    other_ip_dict["direct_connect_domain"] = "nomatchsameip.ui.direct"

    with (
        _patch_discovery(),
        patch.object(menuai.loop, "getaddrinfo", side_effect=OSError),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=other_ip_dict,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"
    flows = menuai.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert flows[0]["context"]["title_placeholders"] == {
        "ip_address": "127.0.0.2",
        "name": "unvr",
    }

    assert not result["errors"]

    bootstrap.nvr = nvr
    with (
        patch(
            "menuai.components.unifiprotect.config_flow.ProtectApiClient.get_bootstrap",
            return_value=bootstrap,
        ),
        patch(
            "menuai.components.unifiprotect.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.unifiprotect.async_setup",
            return_value=True,
        ) as mock_setup,
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
    assert result2["title"] == "UnifiProtect"
    assert result2["data"] == {
        "host": "nomatchsameip.ui.direct",
        "username": "test-username",
        "password": "test-password",
        "id": "UnifiProtect",
        "port": 443,
        "verify_ssl": True,
    }
    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_setup.mock_calls) == 1


async def test_discovered_by_unifi_discovery_direct_connect_on_different_interface_resolver_no_result(
    menuai: menuai,
) -> None:
    """Test a discovery from unifi-discovery from an alternate interface when direct connect domain resolve has no result."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data={
            "host": "y.ui.direct",
            "username": "test-username",
            "password": "test-password",
            "id": "UnifiProtect",
            "port": 443,
            "verify_ssl": True,
        },
        unique_id="FFFFFFAAAAAA",
    )
    mock_config.add_to_menuai(menuai)

    other_ip_dict = UNIFI_DISCOVERY_DICT.copy()
    other_ip_dict["source_ip"] = "127.0.0.2"
    other_ip_dict["direct_connect_domain"] = "y.ui.direct"

    with _patch_discovery(), patch.object(menuai.loop, "getaddrinfo", return_value=[]):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=other_ip_dict,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_discovery_can_be_ignored(menuai: menuai) -> None:
    """Test a discovery can be ignored."""
    mock_config = MockConfigEntry(
        domain=DOMAIN,
        data={},
        unique_id=DEVICE_MAC_ADDRESS.upper().replace(":", ""),
        source=config_entries.SOURCE_IGNORE,
    )
    mock_config.add_to_menuai(menuai)
    with _patch_discovery():
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=UNIFI_DISCOVERY_DICT,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
