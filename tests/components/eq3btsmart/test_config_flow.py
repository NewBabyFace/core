"""Test the eq3btsmart config flow."""

from unittest.mock import patch

from menuai import config_entries
from menuai.components.bluetooth import BluetoothServiceInfoBleak
from menuai.components.eq3btsmart.const import DOMAIN
from menuai.const import CONF_MAC
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.helpers.device_registry import format_mac
from menuai.util import slugify

from .const import MAC

from tests.common import MockConfigEntry


async def test_user_flow(menuai: menuai) -> None:
    """Test we can handle a regular successflow setup flow."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.eq3btsmart.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_MAC: MAC},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == slugify(MAC)
    assert result["data"] == {}
    assert result["context"]["unique_id"] == MAC
    assert len(mock_setup_entry.mock_calls) == 1


async def test_user_flow_invalid_mac(menuai: menuai) -> None:
    """Test we handle invalid mac address."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.eq3btsmart.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_MAC: "invalid"},
        )
        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {CONF_MAC: "invalid_mac_address"}
        assert len(mock_setup_entry.mock_calls) == 0

        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_MAC: MAC},
        )
        await menuai.async_block_till_done()

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == slugify(MAC)
        assert result["data"] == {}
        assert result["context"]["unique_id"] == MAC
        assert len(mock_setup_entry.mock_calls) == 1


async def test_bluetooth_flow(
    menuai: menuai, fake_service_info: BluetoothServiceInfoBleak
) -> None:
    """Test we can handle a bluetooth discovery flow."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=fake_service_info,
    )

    with patch(
        "menuai.components.eq3btsmart.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == slugify(MAC)
    assert result["data"] == {}
    assert result["context"]["unique_id"] == MAC
    assert len(mock_setup_entry.mock_calls) == 1


async def test_duplicate_entry(menuai: menuai) -> None:
    """Test duplicate setup handling."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MAC: MAC,
        },
        unique_id=format_mac(MAC),
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "menuai.components.eq3btsmart.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_MAC: MAC,
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_setup_entry.call_count == 0
