"""Test the UPB Control config flow."""

from asyncio import TimeoutError
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from menuai import config_entries
from menuai.components.upb.const import DOMAIN
from menuai.config_entries import ConfigFlowResult
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


def mocked_upb(sync_complete=True, config_ok=True):
    """Mock UPB lib."""

    def _add_handler(_, callback):
        callback()

    def _dummy_add_handler(_, _callback):
        pass

    upb_mock = AsyncMock()
    type(upb_mock).network_id = PropertyMock(return_value="42")
    type(upb_mock).config_ok = PropertyMock(return_value=config_ok)
    type(upb_mock).disconnect = MagicMock()
    type(upb_mock).add_handler = MagicMock()
    upb_mock.add_handler.side_effect = (
        _add_handler if sync_complete else _dummy_add_handler
    )
    return patch(
        "menuai.components.upb.config_flow.upb_lib.UpbPim", return_value=upb_mock
    )


async def valid_tcp_flow(
    menuai: menuai, sync_complete: bool = True, config_ok: bool = True
) -> ConfigFlowResult:
    """Get result dict that are standard for most tests."""

    with (
        mocked_upb(sync_complete, config_ok),
        patch("menuai.components.upb.async_setup_entry", return_value=True),
    ):
        flow = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        return await menuai.config_entries.flow.async_configure(
            flow["flow_id"],
            {"protocol": "TCP", "address": "1.2.3.4", "file_path": "upb.upe"},
        )


async def test_full_upb_flow_with_serial_port(menuai: menuai) -> None:
    """Test a full UPB config flow with serial port."""

    with (
        mocked_upb(),
        patch(
            "menuai.components.upb.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        flow = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await menuai.config_entries.flow.async_configure(
            flow["flow_id"],
            {
                "protocol": "Serial port",
                "address": "/dev/ttyS0:115200",
                "file_path": "upb.upe",
            },
        )
        await menuai.async_block_till_done()

    assert flow["type"] is FlowResultType.FORM
    assert flow["errors"] == {}
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "UPB"
    assert result["data"] == {
        "host": "serial:///dev/ttyS0:115200",
        "file_path": "upb.upe",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_user_with_tcp_upb(menuai: menuai) -> None:
    """Test we can setup a serial upb."""
    result = await valid_tcp_flow(menuai)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"host": "tcp://1.2.3.4", "file_path": "upb.upe"}
    await menuai.async_block_till_done()


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test we handle cannot connect error."""

    with patch(
        "menuai.components.upb.config_flow.asyncio.timeout",
        side_effect=TimeoutError,
    ):
        result = await valid_tcp_flow(menuai, sync_complete=False)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_form_missing_upb_file(menuai: menuai) -> None:
    """Test we handle cannot connect error."""
    result = await valid_tcp_flow(menuai, config_ok=False)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_upb_file"}


async def test_form_user_with_already_configured(menuai: menuai) -> None:
    """Test we can setup a TCP upb."""
    _ = await valid_tcp_flow(menuai)
    result2 = await valid_tcp_flow(menuai)
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
    await menuai.async_block_till_done()
