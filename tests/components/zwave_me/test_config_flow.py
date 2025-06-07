"""Test the zwave_me config flow."""

from ipaddress import ip_address
from unittest.mock import patch

from menuai import config_entries
from menuai.components.zwave_me.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResult, FlowResultType
from menuai.helpers.service_info.zeroconf import ZeroconfServiceInfo

from tests.common import MockConfigEntry

MOCK_ZEROCONF_DATA = ZeroconfServiceInfo(
    ip_address=ip_address("192.168.1.14"),
    ip_addresses=[ip_address("192.168.1.14")],
    hostname="mock_hostname",
    name="mock_name",
    port=1234,
    properties={
        "deviceid": "aa:bb:cc:dd:ee:ff",
        "manufacturer": "fake_manufacturer",
        "model": "fake_model",
        "serialNumber": "fake_serial",
    },
    type="mock_type",
)


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""
    with (
        patch(
            "menuai.components.zwave_me.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.zwave_me.helpers.get_uuid",
            return_value="test_uuid",
        ),
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {}
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "url": "192.168.1.14",
                "token": "test-token",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "ws://192.168.1.14"
    assert result2["data"] == {
        "url": "ws://192.168.1.14",
        "token": "test-token",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_zeroconf(menuai: menuai) -> None:
    """Test starting a flow from zeroconf."""
    with (
        patch(
            "menuai.components.zwave_me.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
        patch(
            "menuai.components.zwave_me.helpers.get_uuid",
            return_value="test_uuid",
        ),
    ):
        result: FlowResult = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=MOCK_ZEROCONF_DATA,
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "token": "test-token",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "ws://192.168.1.14"
    assert result2["data"] == {
        "url": "ws://192.168.1.14",
        "token": "test-token",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_error_handling_zeroconf(menuai: menuai) -> None:
    """Test getting proper errors from no uuid."""
    with patch("menuai.components.zwave_me.helpers.get_uuid", return_value=None):
        result: FlowResult = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=MOCK_ZEROCONF_DATA,
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "no_valid_uuid_set"


async def test_handle_error_user(menuai: menuai) -> None:
    """Test getting proper errors from no uuid."""
    with patch("menuai.components.zwave_me.helpers.get_uuid", return_value=None):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {}
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "url": "192.168.1.15",
                "token": "test-token",
            },
        )
        assert result2["errors"] == {"base": "no_valid_uuid_set"}


async def test_duplicate_user(menuai: menuai) -> None:
    """Test getting proper errors from duplicate uuid."""
    entry: MockConfigEntry = MockConfigEntry(
        domain=DOMAIN,
        title="ZWave_me",
        data={
            "url": "ws://192.168.1.15",
            "token": "test-token",
        },
        unique_id="test_uuid",
    )
    entry.add_to_menuai(menuai)
    with patch(
        "menuai.components.zwave_me.helpers.get_uuid",
        return_value="test_uuid",
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {}
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "url": "192.168.1.15",
                "token": "test-token",
            },
        )
        assert result2["type"] is FlowResultType.ABORT
        assert result2["reason"] == "already_configured"


async def test_duplicate_zeroconf(menuai: menuai) -> None:
    """Test getting proper errors from duplicate uuid."""
    entry: MockConfigEntry = MockConfigEntry(
        domain=DOMAIN,
        title="ZWave_me",
        data={
            "url": "ws://192.168.1.14",
            "token": "test-token",
        },
        unique_id="test_uuid",
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.zwave_me.helpers.get_uuid",
        return_value="test_uuid",
    ):
        result: FlowResult = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=MOCK_ZEROCONF_DATA,
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"
