"""Test MenuAI config flow for BleBox devices."""

from ipaddress import ip_address
from unittest.mock import DEFAULT, AsyncMock, PropertyMock, patch

import blebox_uniapi
import pytest

from menuai import config_entries
from menuai.components.blebox import config_flow
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_IP_ADDRESS
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.service_info.zeroconf import ZeroconfServiceInfo
from menuai.setup import async_setup_component

from .conftest import mock_config, mock_feature, mock_only_feature, setup_product_mock

from tests.common import MockConfigEntry


def create_valid_feature_mock(path="menuai.components.blebox.Products"):
    """Return a valid, complete BleBox feature mock."""
    feature = mock_only_feature(
        blebox_uniapi.cover.Cover,
        unique_id="BleBox-gateBox-1afe34db9437-0.position",
        full_name="gateBox-0.position",
        device_class="gate",
        state=0,
        async_update=AsyncMock(),
        current=None,
    )

    product = setup_product_mock("covers", [feature], path)

    type(product).name = PropertyMock(return_value="My gate controller")
    type(product).model = PropertyMock(return_value="gateController")
    type(product).type = PropertyMock(return_value="gateBox")
    type(product).brand = PropertyMock(return_value="BleBox")
    type(product).firmware_version = PropertyMock(return_value="1.23")
    type(product).unique_id = PropertyMock(return_value="abcd0123ef5678")

    return feature


@pytest.fixture(name="valid_feature_mock")
def valid_feature_mock_fixture():
    """Return a valid, complete BleBox feature mock."""
    return create_valid_feature_mock()


@pytest.fixture(name="flow_feature_mock")
def flow_feature_mock_fixture():
    """Return a mocked user flow feature."""
    return create_valid_feature_mock(
        "menuai.components.blebox.config_flow.Products"
    )


async def test_flow_works(
    menuai: menuai, valid_feature_mock, flow_feature_mock
) -> None:
    """Test that config flow works."""

    result = await menuai.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await menuai.config_entries.flow.async_init(
        config_flow.DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={config_flow.CONF_HOST: "172.2.3.4", config_flow.CONF_PORT: 80},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "My gate controller"
    assert result["data"] == {
        config_flow.CONF_HOST: "172.2.3.4",
        config_flow.CONF_PORT: 80,
    }


@pytest.fixture(name="product_class_mock")
def product_class_mock_fixture():
    """Return a mocked feature."""
    path = "menuai.components.blebox.config_flow.Box"
    return patch(path, DEFAULT, blebox_uniapi.box.Box, True, True)


async def test_flow_with_connection_failure(
    menuai: menuai, product_class_mock
) -> None:
    """Test that config flow works."""
    with product_class_mock as products_class:
        products_class.async_from_host = AsyncMock(
            side_effect=blebox_uniapi.error.ConnectionError
        )

        result = await menuai.config_entries.flow.async_init(
            config_flow.DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={config_flow.CONF_HOST: "172.2.3.4", config_flow.CONF_PORT: 80},
        )
        assert result["errors"] == {"base": "cannot_connect"}


async def test_flow_with_api_failure(menuai: menuai, product_class_mock) -> None:
    """Test that config flow works."""
    with product_class_mock as products_class:
        products_class.async_from_host = AsyncMock(
            side_effect=blebox_uniapi.error.Error
        )

        result = await menuai.config_entries.flow.async_init(
            config_flow.DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={config_flow.CONF_HOST: "172.2.3.4", config_flow.CONF_PORT: 80},
        )
        assert result["errors"] == {"base": "cannot_connect"}


async def test_flow_with_unknown_failure(
    menuai: menuai, product_class_mock
) -> None:
    """Test that config flow works."""
    with product_class_mock as products_class:
        products_class.async_from_host = AsyncMock(side_effect=RuntimeError)
        result = await menuai.config_entries.flow.async_init(
            config_flow.DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={config_flow.CONF_HOST: "172.2.3.4", config_flow.CONF_PORT: 80},
        )
        assert result["errors"] == {"base": "unknown"}


async def test_flow_with_unsupported_version(
    menuai: menuai, product_class_mock
) -> None:
    """Test that config flow works."""
    with product_class_mock as products_class:
        products_class.async_from_host = AsyncMock(
            side_effect=blebox_uniapi.error.UnsupportedBoxVersion
        )

        result = await menuai.config_entries.flow.async_init(
            config_flow.DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={config_flow.CONF_HOST: "172.2.3.4", config_flow.CONF_PORT: 80},
        )
        assert result["errors"] == {"base": "unsupported_version"}


async def test_flow_with_auth_failure(menuai: menuai, product_class_mock) -> None:
    """Test that config flow works."""
    with product_class_mock as products_class:
        products_class.async_from_host = AsyncMock(
            side_effect=blebox_uniapi.error.UnauthorizedRequest
        )

        result = await menuai.config_entries.flow.async_init(
            config_flow.DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={config_flow.CONF_HOST: "172.2.3.4", config_flow.CONF_PORT: 80},
        )
        assert result["errors"] == {"base": "cannot_connect"}


async def test_async_setup(menuai: menuai) -> None:
    """Test async_setup (for coverage)."""
    assert await async_setup_component(menuai, "blebox", {"host": "172.2.3.4"})
    await menuai.async_block_till_done()


async def test_already_configured(menuai: menuai, valid_feature_mock) -> None:
    """Test that same device cannot be added twice."""

    config = mock_config("172.2.3.4")
    config.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.flow.async_init(
        config_flow.DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data={config_flow.CONF_HOST: "172.2.3.4", config_flow.CONF_PORT: 80},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "address_already_configured"


async def test_async_setup_entry(menuai: menuai, valid_feature_mock) -> None:
    """Test async_setup_entry (for coverage)."""

    config = mock_config()
    config.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(config.entry_id)
    await menuai.async_block_till_done()

    assert menuai.config_entries.async_entries() == [config]
    assert config.state is ConfigEntryState.LOADED


async def test_async_remove_entry(menuai: menuai, valid_feature_mock) -> None:
    """Test async_setup_entry (for coverage)."""

    config = mock_config()
    config.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(config.entry_id)
    await menuai.async_block_till_done()

    assert await menuai.config_entries.async_remove(config.entry_id)
    await menuai.async_block_till_done()

    assert menuai.config_entries.async_entries() == []
    assert config.state is ConfigEntryState.NOT_LOADED


async def test_flow_with_zeroconf(menuai: menuai) -> None:
    """Test setup from zeroconf discovery."""
    result = await menuai.config_entries.flow.async_init(
        config_flow.DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=ZeroconfServiceInfo(
            ip_address=ip_address("172.100.123.4"),
            ip_addresses=[ip_address("172.100.123.4")],
            port=80,
            hostname="bbx-bbtest123456.local.",
            type="_bbxsrv._tcp.local.",
            name="bbx-bbtest123456._bbxsrv._tcp.local.",
            properties={"_raw": {}},
        ),
    )

    assert result["type"] is FlowResultType.FORM

    with patch("menuai.components.blebox.async_setup_entry", return_value=True):
        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == {"host": "172.100.123.4", "port": 80}


async def test_flow_with_zeroconf_when_already_configured(menuai: menuai) -> None:
    """Test behaviour if device already configured."""
    entry = MockConfigEntry(
        domain=config_flow.DOMAIN,
        data={CONF_IP_ADDRESS: "172.100.123.4"},
        unique_id="abcd0123ef5678",
    )
    entry.add_to_menuai(menuai)
    feature: AsyncMock = mock_feature(
        "sensors",
        blebox_uniapi.sensor.Temperature,
    )
    with patch(
        "menuai.components.blebox.config_flow.Box.async_from_host",
        return_value=feature.product,
    ):
        result2 = await menuai.config_entries.flow.async_init(
            config_flow.DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=ZeroconfServiceInfo(
                ip_address=ip_address("172.100.123.4"),
                ip_addresses=[ip_address("172.100.123.4")],
                port=80,
                hostname="bbx-bbtest123456.local.",
                type="_bbxsrv._tcp.local.",
                name="bbx-bbtest123456._bbxsrv._tcp.local.",
                properties={"_raw": {}},
            ),
        )

        assert result2["type"] is FlowResultType.ABORT
        assert result2["reason"] == "already_configured"


async def test_flow_with_zeroconf_when_device_unsupported(menuai: menuai) -> None:
    """Test behaviour when device is not supported."""
    with patch(
        "menuai.components.blebox.config_flow.Box.async_from_host",
        side_effect=blebox_uniapi.error.UnsupportedBoxVersion,
    ):
        result = await menuai.config_entries.flow.async_init(
            config_flow.DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=ZeroconfServiceInfo(
                ip_address=ip_address("172.100.123.4"),
                ip_addresses=[ip_address("172.100.123.4")],
                port=80,
                hostname="bbx-bbtest123456.local.",
                type="_bbxsrv._tcp.local.",
                name="bbx-bbtest123456._bbxsrv._tcp.local.",
                properties={"_raw": {}},
            ),
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "unsupported_device_version"


async def test_flow_with_zeroconf_when_device_response_unsupported(
    menuai: menuai,
) -> None:
    """Test behaviour when device returned unsupported response."""

    with patch(
        "menuai.components.blebox.config_flow.Box.async_from_host",
        side_effect=blebox_uniapi.error.UnsupportedBoxResponse,
    ):
        result = await menuai.config_entries.flow.async_init(
            config_flow.DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=ZeroconfServiceInfo(
                ip_address=ip_address("172.100.123.4"),
                ip_addresses=[ip_address("172.100.123.4")],
                port=80,
                hostname="bbx-bbtest123456.local.",
                type="_bbxsrv._tcp.local.",
                name="bbx-bbtest123456._bbxsrv._tcp.local.",
                properties={"_raw": {}},
            ),
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "unsupported_device_response"
