"""Test the Steamist config flow."""

from unittest.mock import patch

import pytest

from menuai import config_entries
from menuai.components.steamist.const import DOMAIN
from menuai.const import CONF_DEVICE, CONF_HOST
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.dhcp import DhcpServiceInfo

from . import (
    DEFAULT_ENTRY_DATA,
    DEVICE_30303_NOT_STEAMIST,
    DEVICE_HOSTNAME,
    DEVICE_IP_ADDRESS,
    DEVICE_MAC_ADDRESS,
    DEVICE_NAME,
    DISCOVERY_30303,
    FORMATTED_MAC_ADDRESS,
    MOCK_ASYNC_GET_STATUS_INACTIVE,
    _patch_discovery,
    _patch_status,
)

from tests.common import MockConfigEntry

MODULE = "menuai.components.steamist"


DHCP_DISCOVERY = DhcpServiceInfo(
    hostname=DEVICE_HOSTNAME,
    ip=DEVICE_IP_ADDRESS,
    macaddress=DEVICE_MAC_ADDRESS.lower().replace(":", ""),
)


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        _patch_discovery(no_device=True),
        patch(
            "menuai.components.steamist.config_flow.Steamist.async_get_status"
        ),
        patch(
            "menuai.components.steamist.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "127.0.0.1",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "127.0.0.1"
    assert result2["data"] == {
        "host": "127.0.0.1",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_with_discovery(menuai: menuai) -> None:
    """Test we can also discovery the device during manual setup."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        _patch_discovery(),
        patch(
            "menuai.components.steamist.config_flow.Steamist.async_get_status"
        ),
        patch(
            "menuai.components.steamist.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "127.0.0.1",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == DEVICE_NAME
    assert result2["data"] == DEFAULT_ENTRY_DATA
    assert result2["context"]["unique_id"] == FORMATTED_MAC_ADDRESS
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.steamist.config_flow.Steamist.async_get_status",
        side_effect=TimeoutError,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "127.0.0.1",
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
        "menuai.components.steamist.config_flow.Steamist.async_get_status",
        side_effect=Exception,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "127.0.0.1",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_discovery(menuai: menuai) -> None:
    """Test setting up discovery."""
    with _patch_discovery(), _patch_status(MOCK_ASYNC_GET_STATUS_INACTIVE):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await menuai.async_block_till_done()
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert not result["errors"]

        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        await menuai.async_block_till_done()
        assert result2["type"] is FlowResultType.FORM
        assert result2["step_id"] == "pick_device"
        assert not result2["errors"]

        # test we can try again
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"
        assert not result["errors"]

        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        await menuai.async_block_till_done()
        assert result2["type"] is FlowResultType.FORM
        assert result2["step_id"] == "pick_device"
        assert not result2["errors"]

    with (
        _patch_discovery(),
        _patch_status(MOCK_ASYNC_GET_STATUS_INACTIVE),
        patch(f"{MODULE}.async_setup", return_value=True) as mock_setup,
        patch(f"{MODULE}.async_setup_entry", return_value=True) as mock_setup_entry,
    ):
        result3 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_DEVICE: FORMATTED_MAC_ADDRESS},
        )
        await menuai.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == DEVICE_NAME
    assert result3["data"] == DEFAULT_ENTRY_DATA
    mock_setup.assert_called_once()
    mock_setup_entry.assert_called_once()

    # ignore configured devices
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    with _patch_discovery(), _patch_status(MOCK_ASYNC_GET_STATUS_INACTIVE):
        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "no_devices_found"


async def test_discovered_by_discovery_and_dhcp(menuai: menuai) -> None:
    """Test we get the form with discovery and abort for dhcp source when we get both."""

    with _patch_discovery(), _patch_status(MOCK_ASYNC_GET_STATUS_INACTIVE):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=DISCOVERY_30303,
        )
        await menuai.async_block_till_done()
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with _patch_discovery(), _patch_status(MOCK_ASYNC_GET_STATUS_INACTIVE):
        result2 = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=DHCP_DISCOVERY,
        )
        await menuai.async_block_till_done()
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_in_progress"

    with _patch_discovery(), _patch_status(MOCK_ASYNC_GET_STATUS_INACTIVE):
        result3 = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=DhcpServiceInfo(
                hostname="any",
                ip=DEVICE_IP_ADDRESS,
                macaddress="000000000000",
            ),
        )
        await menuai.async_block_till_done()
    assert result3["type"] is FlowResultType.ABORT
    assert result3["reason"] == "already_in_progress"


async def test_discovered_by_discovery(menuai: menuai) -> None:
    """Test we can setup when discovered from discovery."""

    with _patch_discovery(), _patch_status(MOCK_ASYNC_GET_STATUS_INACTIVE):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data=DISCOVERY_30303,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        _patch_discovery(),
        _patch_status(MOCK_ASYNC_GET_STATUS_INACTIVE),
        patch(f"{MODULE}.async_setup", return_value=True) as mock_async_setup,
        patch(
            f"{MODULE}.async_setup_entry", return_value=True
        ) as mock_async_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == DEFAULT_ENTRY_DATA
    assert mock_async_setup.called
    assert mock_async_setup_entry.called


async def test_discovered_by_dhcp(menuai: menuai) -> None:
    """Test we can setup when discovered from dhcp."""

    with _patch_discovery(), _patch_status(MOCK_ASYNC_GET_STATUS_INACTIVE):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=DHCP_DISCOVERY,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        _patch_discovery(),
        _patch_status(MOCK_ASYNC_GET_STATUS_INACTIVE),
        patch(f"{MODULE}.async_setup", return_value=True) as mock_async_setup,
        patch(
            f"{MODULE}.async_setup_entry", return_value=True
        ) as mock_async_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == DEFAULT_ENTRY_DATA
    assert mock_async_setup.called
    assert mock_async_setup_entry.called


async def test_discovered_by_dhcp_discovery_fails(menuai: menuai) -> None:
    """Test we can setup when discovered from dhcp but then we cannot get the device name."""

    with (
        _patch_discovery(no_device=True),
        _patch_status(MOCK_ASYNC_GET_STATUS_INACTIVE),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=DHCP_DISCOVERY,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_discovered_by_dhcp_discovery_finds_non_steamist_device(
    menuai: menuai,
) -> None:
    """Test we can setup when discovered from dhcp but its not a steamist device."""

    with (
        _patch_discovery(device=DEVICE_30303_NOT_STEAMIST),
        _patch_status(MOCK_ASYNC_GET_STATUS_INACTIVE),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_DHCP},
            data=DHCP_DISCOVERY,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_steamist_device"


@pytest.mark.parametrize(
    ("source", "data"),
    [
        (config_entries.SOURCE_DHCP, DHCP_DISCOVERY),
        (config_entries.SOURCE_INTEGRATION_DISCOVERY, DISCOVERY_30303),
    ],
)
async def test_discovered_by_dhcp_or_discovery_adds_missing_unique_id(
    menuai: menuai, source, data
) -> None:
    """Test we can setup when discovered from dhcp or discovery and add a missing unique id."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: DEVICE_IP_ADDRESS})
    config_entry.add_to_menuai(menuai)

    with (
        _patch_discovery(),
        _patch_status(MOCK_ASYNC_GET_STATUS_INACTIVE),
        patch(f"{MODULE}.async_setup", return_value=True) as mock_setup,
        patch(f"{MODULE}.async_setup_entry", return_value=True) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": source}, data=data
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"

    assert config_entry.unique_id == FORMATTED_MAC_ADDRESS
    assert mock_setup.called
    assert mock_setup_entry.called


@pytest.mark.parametrize(
    ("source", "data"),
    [
        (config_entries.SOURCE_DHCP, DHCP_DISCOVERY),
        (config_entries.SOURCE_INTEGRATION_DISCOVERY, DISCOVERY_30303),
    ],
)
async def test_discovered_by_dhcp_or_discovery_existing_unique_id_does_not_reload(
    menuai: menuai, source, data
) -> None:
    """Test we can setup when discovered from dhcp or discovery and it does not reload."""
    config_entry = MockConfigEntry(
        domain=DOMAIN, data=DEFAULT_ENTRY_DATA, unique_id=FORMATTED_MAC_ADDRESS
    )
    config_entry.add_to_menuai(menuai)

    with (
        _patch_discovery(),
        _patch_status(MOCK_ASYNC_GET_STATUS_INACTIVE),
        patch(f"{MODULE}.async_setup", return_value=True) as mock_setup,
        patch(f"{MODULE}.async_setup_entry", return_value=True) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": source}, data=data
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert not mock_setup.called
    assert not mock_setup_entry.called
