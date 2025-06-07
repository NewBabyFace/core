"""Test the Firmata config flow."""

from unittest.mock import patch

from pymata_express.pymata_express_serial import serial

from menuai import config_entries
from menuai.components.firmata.const import CONF_SERIAL_PORT, DOMAIN
from menuai.const import CONF_NAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


async def test_import_cannot_connect_pymata(menuai: menuai) -> None:
    """Test we fail with an invalid board."""

    with patch(
        "menuai.components.firmata.board.PymataExpress.start_aio",
        side_effect=RuntimeError,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={CONF_SERIAL_PORT: "/dev/nonExistent"},
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "cannot_connect"


async def test_import_cannot_connect_serial(menuai: menuai) -> None:
    """Test we fail with an invalid board."""

    with patch(
        "menuai.components.firmata.board.PymataExpress.start_aio",
        side_effect=serial.SerialException,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={CONF_SERIAL_PORT: "/dev/nonExistent"},
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "cannot_connect"


async def test_import_cannot_connect_serial_timeout(menuai: menuai) -> None:
    """Test we fail with an invalid board."""

    with patch(
        "menuai.components.firmata.board.PymataExpress.start_aio",
        side_effect=serial.SerialTimeoutException,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={CONF_SERIAL_PORT: "/dev/nonExistent"},
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "cannot_connect"


async def test_import(menuai: menuai) -> None:
    """Test we create an entry from config."""

    with (
        patch("menuai.components.firmata.board.PymataExpress", autospec=True),
        patch(
            "menuai.components.firmata.async_setup", return_value=True
        ) as mock_setup,
        patch(
            "menuai.components.firmata.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={CONF_SERIAL_PORT: "/dev/nonExistent"},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "serial-/dev/nonExistent"
        assert result["data"] == {
            CONF_NAME: "serial-/dev/nonExistent",
            CONF_SERIAL_PORT: "/dev/nonExistent",
        }
        await menuai.async_block_till_done()
        assert len(mock_setup.mock_calls) == 1
        assert len(mock_setup_entry.mock_calls) == 1
