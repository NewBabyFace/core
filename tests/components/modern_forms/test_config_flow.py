"""Tests for the Modern Forms config flow."""

from ipaddress import ip_address
from unittest.mock import MagicMock, patch

import aiohttp
from aiomodernforms import ModernFormsConnectionError

from menuai.components.modern_forms.const import DOMAIN
from menuai.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from menuai.const import CONF_HOST, CONF_MAC, CONF_NAME, CONTENT_TYPE_JSON
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.zeroconf import ZeroconfServiceInfo

from . import init_integration

from tests.common import async_load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker


async def test_full_user_flow_implementation(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the full manual user flow from start to finish."""
    aioclient_mock.post(
        "http://192.168.1.123:80/mf",
        text=await async_load_fixture(menuai, "device_info.json", DOMAIN),
        headers={"Content-Type": CONTENT_TYPE_JSON},
    )

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result.get("step_id") == "user"
    assert result.get("type") is FlowResultType.FORM

    with patch(
        "menuai.components.modern_forms.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_HOST: "192.168.1.123"}
        )

    assert result2.get("title") == "ModernFormsFan"
    assert "data" in result2
    assert result2.get("type") is FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_HOST] == "192.168.1.123"
    assert result2["data"][CONF_MAC] == "AA:BB:CC:DD:EE:FF"
    assert len(mock_setup_entry.mock_calls) == 1


async def test_full_zeroconf_flow_implementation(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the full manual user flow from start to finish."""
    aioclient_mock.post(
        "http://192.168.1.123:80/mf",
        text=await async_load_fixture(menuai, "device_info.json", DOMAIN),
        headers={"Content-Type": CONTENT_TYPE_JSON},
    )

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=ZeroconfServiceInfo(
            ip_address=ip_address("192.168.1.123"),
            ip_addresses=[ip_address("192.168.1.123")],
            hostname="example.local.",
            name="mock_name",
            port=None,
            properties={},
            type="mock_type",
        ),
    )

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1

    assert result.get("description_placeholders") == {CONF_NAME: "example"}
    assert result.get("step_id") == "zeroconf_confirm"
    assert result.get("type") is FlowResultType.FORM

    flow = menuai.config_entries.flow._progress[flows[0]["flow_id"]]
    assert flow.host == "192.168.1.123"
    assert flow.name == "example"

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )

    assert result2.get("title") == "example"
    assert result2.get("type") is FlowResultType.CREATE_ENTRY

    assert "data" in result2
    assert result2["data"][CONF_HOST] == "192.168.1.123"
    assert result2["data"][CONF_MAC] == "AA:BB:CC:DD:EE:FF"


@patch(
    "menuai.components.modern_forms.coordinator.ModernFormsDevice.update",
    side_effect=ModernFormsConnectionError,
)
async def test_connection_error(
    update_mock: MagicMock, menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test we show user form on Modern Forms connection error."""
    aioclient_mock.post("http://example.com/mf", exc=aiohttp.ClientError)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HOST: "example.com"},
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert result.get("errors") == {"base": "cannot_connect"}


@patch(
    "menuai.components.modern_forms.coordinator.ModernFormsDevice.update",
    side_effect=ModernFormsConnectionError,
)
async def test_zeroconf_connection_error(
    update_mock: MagicMock, menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test we abort zeroconf flow on Modern Forms connection error."""
    aioclient_mock.post("http://192.168.1.123/mf", exc=aiohttp.ClientError)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=ZeroconfServiceInfo(
            ip_address=ip_address("192.168.1.123"),
            ip_addresses=[ip_address("192.168.1.123")],
            hostname="example.local.",
            name="mock_name",
            port=None,
            properties={},
            type="mock_type",
        ),
    )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "cannot_connect"


@patch(
    "menuai.components.modern_forms.coordinator.ModernFormsDevice.update",
    side_effect=ModernFormsConnectionError,
)
async def test_zeroconf_confirm_connection_error(
    update_mock: MagicMock, menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test we abort zeroconf flow on Modern Forms connection error."""
    aioclient_mock.post("http://192.168.1.123:80/mf", exc=aiohttp.ClientError)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": SOURCE_ZEROCONF,
            CONF_HOST: "example.com",
            CONF_NAME: "test",
        },
        data=ZeroconfServiceInfo(
            ip_address=ip_address("192.168.1.123"),
            ip_addresses=[ip_address("192.168.1.123")],
            hostname="example.com.",
            name="mock_name",
            port=None,
            properties={},
            type="mock_type",
        ),
    )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "cannot_connect"


async def test_user_device_exists_abort(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test we abort zeroconf flow if Modern Forms device already configured."""
    aioclient_mock.post(
        "http://192.168.1.123:80/mf",
        text=await async_load_fixture(menuai, "device_info.json", DOMAIN),
        headers={"Content-Type": CONTENT_TYPE_JSON},
    )

    await init_integration(menuai, aioclient_mock, skip_setup=True)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HOST: "192.168.1.123"},
    )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "already_configured"


async def test_zeroconf_with_mac_device_exists_abort(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test we abort zeroconf flow if a Modern Forms device already configured."""
    await init_integration(menuai, aioclient_mock, skip_setup=True)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=ZeroconfServiceInfo(
            ip_address=ip_address("192.168.1.123"),
            ip_addresses=[ip_address("192.168.1.123")],
            hostname="example.local.",
            name="mock_name",
            port=None,
            properties={CONF_MAC: "AA:BB:CC:DD:EE:FF"},
            type="mock_type",
        ),
    )

    assert result.get("type") is FlowResultType.ABORT
    assert result.get("reason") == "already_configured"
