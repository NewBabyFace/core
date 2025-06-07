"""Test the OctoPrint config flow."""

from ipaddress import ip_address
from unittest.mock import patch

from pyoctoprintapi import ApiError, DiscoverySettings

from menuai import config_entries
from menuai.components.octoprint.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.ssdp import SsdpServiceInfo
from menuai.helpers.service_info.zeroconf import ZeroconfServiceInfo

from tests.common import MockConfigEntry


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    with patch(
        "pyoctoprintapi.OctoprintClient.request_app_key", return_value="test-key"
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "testuser",
                "host": "1.1.1.1",
                "name": "Printer",
                "port": 81,
                "ssl": True,
                "path": "/",
            },
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.SHOW_PROGRESS

    with (
        patch(
            "pyoctoprintapi.OctoprintClient.get_server_info",
            return_value=True,
        ),
        patch(
            "pyoctoprintapi.OctoprintClient.get_discovery_info",
            return_value=DiscoverySettings({"upnpUuid": "uuid"}),
        ),
        patch(
            "menuai.components.octoprint.async_setup", return_value=True
        ) as mock_setup,
        patch(
            "menuai.components.octoprint.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "1.1.1.1"
    assert result2["data"] == {
        "username": "testuser",
        "host": "1.1.1.1",
        "api_key": "test-key",
        "name": "Printer",
        "port": 81,
        "ssl": True,
        "path": "/",
        "verify_ssl": True,
    }
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "username": "testuser",
            "host": "1.1.1.1",
            "name": "Printer",
            "port": 81,
            "ssl": True,
            "path": "/",
        },
    )
    assert result["type"] is FlowResultType.SHOW_PROGRESS

    with patch(
        "pyoctoprintapi.OctoprintClient.request_app_key", return_value="test-key"
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.SHOW_PROGRESS

    with patch(
        "pyoctoprintapi.OctoprintClient.get_discovery_info",
        side_effect=ApiError,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "testuser",
                "host": "1.1.1.1",
                "name": "Printer",
                "port": 81,
                "ssl": True,
                "verify_ssl": True,
                "path": "/",
                "api_key": "test-key",
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"


async def test_form_unknown_exception(menuai: menuai) -> None:
    """Test we handle a random error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "username": "testuser",
            "host": "1.1.1.1",
            "name": "Printer",
            "port": 81,
            "ssl": True,
            "path": "/",
        },
    )
    assert result["type"] is FlowResultType.SHOW_PROGRESS

    with patch(
        "pyoctoprintapi.OctoprintClient.request_app_key", return_value="test-key"
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.SHOW_PROGRESS

    with patch(
        "pyoctoprintapi.OctoprintClient.get_discovery_info",
        side_effect=Exception,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "testuser",
                "host": "1.1.1.1",
                "name": "Printer",
                "port": 81,
                "ssl": True,
                "path": "/",
                "api_key": "test-key",
                "verify_ssl": True,
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"]["base"] == "unknown"


async def test_show_zerconf_form(menuai: menuai) -> None:
    """Test that the zeroconf confirmation form is served."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=ZeroconfServiceInfo(
            ip_address=ip_address("192.168.1.123"),
            ip_addresses=[ip_address("192.168.1.123")],
            hostname="example.local.",
            name="mock_name",
            port=80,
            properties={"uuid": "83747482", "path": "/foo/"},
            type="mock_type",
        ),
    )
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "username": "testuser",
        },
    )
    assert result["type"] is FlowResultType.SHOW_PROGRESS

    with patch(
        "pyoctoprintapi.OctoprintClient.request_app_key", return_value="test-key"
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.SHOW_PROGRESS

    with (
        patch(
            "pyoctoprintapi.OctoprintClient.get_server_info",
            return_value=True,
        ),
        patch(
            "pyoctoprintapi.OctoprintClient.get_discovery_info",
            return_value=DiscoverySettings({"upnpUuid": "uuid"}),
        ),
        patch("menuai.components.octoprint.async_setup", return_value=True),
        patch(
            "menuai.components.octoprint.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "testuser",
                "host": "1.1.1.1",
                "name": "Printer",
                "port": 81,
                "ssl": True,
                "path": "/",
                "api_key": "test-key",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_show_ssdp_form(menuai: menuai) -> None:
    """Test that the zeroconf confirmation form is served."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_SSDP},
        data=SsdpServiceInfo(
            ssdp_usn="mock_usn",
            ssdp_st="mock_st",
            upnp={
                "presentationURL": "http://192.168.1.123:80/discovery/device.xml",
                "port": 80,
                "UDN": "uuid:83747482",
            },
        ),
    )
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "username": "testuser",
        },
    )
    assert result["type"] is FlowResultType.SHOW_PROGRESS

    with patch(
        "pyoctoprintapi.OctoprintClient.request_app_key", return_value="test-key"
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.SHOW_PROGRESS

    with (
        patch(
            "pyoctoprintapi.OctoprintClient.get_server_info",
            return_value=True,
        ),
        patch(
            "pyoctoprintapi.OctoprintClient.get_discovery_info",
            return_value=DiscoverySettings({"upnpUuid": "uuid"}),
        ),
        patch("menuai.components.octoprint.async_setup", return_value=True),
        patch(
            "menuai.components.octoprint.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "testuser",
                "host": "1.1.1.1",
                "name": "Printer",
                "port": 81,
                "ssl": True,
                "path": "/",
                "api_key": "test-key",
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_import_yaml(menuai: menuai) -> None:
    """Test that the yaml import works."""
    with (
        patch(
            "pyoctoprintapi.OctoprintClient.get_server_info",
            return_value=True,
        ),
        patch(
            "pyoctoprintapi.OctoprintClient.get_discovery_info",
            return_value=DiscoverySettings({"upnpUuid": "uuid"}),
        ),
        patch(
            "pyoctoprintapi.OctoprintClient.request_app_key", return_value="test-key"
        ),
        patch("menuai.components.octoprint.async_setup", return_value=True),
        patch(
            "menuai.components.octoprint.async_setup_entry",
            return_value=True,
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={
                "host": "1.1.1.1",
                "api_key": "test-key",
                "name": "Printer",
                "port": 81,
                "ssl": True,
                "path": "/",
            },
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "errors" not in result


async def test_import_duplicate_yaml(menuai: menuai) -> None:
    """Test that the yaml import works."""
    MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.1.123"},
        source=config_entries.SOURCE_IMPORT,
        unique_id="uuid",
    ).add_to_menuai(menuai)

    with (
        patch(
            "pyoctoprintapi.OctoprintClient.get_discovery_info",
            return_value=DiscoverySettings({"upnpUuid": "uuid"}),
        ),
        patch(
            "pyoctoprintapi.OctoprintClient.request_app_key", return_value="test-key"
        ) as request_app_key,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={
                "host": "1.1.1.1",
                "api_key": "test-key",
                "name": "Printer",
                "port": 81,
                "ssl": True,
                "path": "/",
            },
        )
        await menuai.async_block_till_done()
        assert len(request_app_key.mock_calls) == 0

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_failed_auth(menuai: menuai) -> None:
    """Test we handle a random error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "username": "testuser",
            "host": "1.1.1.1",
            "name": "Printer",
            "port": 81,
            "ssl": True,
            "path": "/",
        },
    )
    assert result["type"] is FlowResultType.SHOW_PROGRESS

    with patch("pyoctoprintapi.OctoprintClient.request_app_key", side_effect=ApiError):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.SHOW_PROGRESS

    result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "auth_failed"


async def test_failed_auth_unexpected_error(menuai: menuai) -> None:
    """Test we handle a random error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "username": "testuser",
            "host": "1.1.1.1",
            "name": "Printer",
            "port": 81,
            "ssl": True,
            "path": "/",
        },
    )
    assert result["type"] is FlowResultType.SHOW_PROGRESS

    with patch("pyoctoprintapi.OctoprintClient.request_app_key", side_effect=Exception):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.SHOW_PROGRESS

    result = await menuai.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "auth_failed"


async def test_user_duplicate_entry(menuai: menuai) -> None:
    """Test that duplicate entries abort."""
    MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.1.123"},
        source=config_entries.SOURCE_IMPORT,
        unique_id="uuid",
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    with patch(
        "pyoctoprintapi.OctoprintClient.request_app_key", return_value="test-key"
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "testuser",
                "host": "1.1.1.1",
                "name": "Printer",
                "port": 81,
                "ssl": True,
                "path": "/",
            },
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.SHOW_PROGRESS

    with (
        patch(
            "pyoctoprintapi.OctoprintClient.get_server_info",
            return_value=True,
        ),
        patch(
            "pyoctoprintapi.OctoprintClient.get_discovery_info",
            return_value=DiscoverySettings({"upnpUuid": "uuid"}),
        ),
        patch(
            "menuai.components.octoprint.async_setup", return_value=True
        ) as mock_setup,
        patch(
            "menuai.components.octoprint.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
    assert len(mock_setup.mock_calls) == 0
    assert len(mock_setup_entry.mock_calls) == 0


async def test_duplicate_zerconf_ignored(menuai: menuai) -> None:
    """Test that the duplicate zeroconf isn't shown."""
    MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.1.123"},
        source=config_entries.SOURCE_IMPORT,
        unique_id="83747482",
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=ZeroconfServiceInfo(
            ip_address=ip_address("192.168.1.123"),
            ip_addresses=[ip_address("192.168.1.123")],
            hostname="example.local.",
            name="mock_name",
            port=80,
            properties={"uuid": "83747482", "path": "/foo/"},
            type="mock_type",
        ),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_duplicate_ssdp_ignored(menuai: menuai) -> None:
    """Test that duplicate ssdp form is note shown."""
    MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.1.123"},
        source=config_entries.SOURCE_IMPORT,
        unique_id="83747482",
    ).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_SSDP},
        data=SsdpServiceInfo(
            ssdp_usn="mock_usn",
            ssdp_st="mock_st",
            upnp={
                "presentationURL": "http://192.168.1.123:80/discovery/device.xml",
                "port": 80,
                "UDN": "uuid:83747482",
            },
        ),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_form(menuai: menuai) -> None:
    """Test we get the form."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "username": "testuser",
            "host": "1.1.1.1",
            "name": "Printer",
            "port": 81,
            "ssl": True,
            "path": "/",
        },
        unique_id="1234",
    )
    entry.add_to_menuai(menuai)
    result = await entry.start_reauth_flow(menuai)
    assert result["type"] is FlowResultType.FORM
    assert not result["errors"]

    with patch(
        "pyoctoprintapi.OctoprintClient.request_app_key", return_value="test-key"
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "username": "testuser",
            },
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.SHOW_PROGRESS

    with patch(
        "menuai.components.octoprint.async_setup_entry",
        return_value=True,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
