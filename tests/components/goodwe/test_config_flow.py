"""Test the Goodwe config flow."""

from unittest.mock import AsyncMock, patch

from goodwe import InverterError

from menuai.components.goodwe.const import (
    CONF_MODEL_FAMILY,
    DEFAULT_NAME,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

TEST_HOST = "1.2.3.4"
TEST_SERIAL = "123456789"


def mock_inverter():
    """Get a mock object of the inverter."""
    goodwe_inverter = AsyncMock()
    goodwe_inverter.serial_number = TEST_SERIAL
    return goodwe_inverter


async def test_manual_setup(menuai: menuai) -> None:
    """Test manually setting up."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    with (
        patch(
            "menuai.components.goodwe.config_flow.connect",
            return_value=mock_inverter(),
        ),
        patch(
            "menuai.components.goodwe.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: TEST_HOST}
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_NAME
    assert result["data"] == {
        CONF_HOST: TEST_HOST,
        CONF_MODEL_FAMILY: "AsyncMock",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_manual_setup_already_exists(menuai: menuai) -> None:
    """Test manually setting up and the device already exists."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: TEST_HOST}, unique_id=TEST_SERIAL
    )
    entry.add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    with (
        patch(
            "menuai.components.goodwe.config_flow.connect",
            return_value=mock_inverter(),
        ),
        patch("menuai.components.goodwe.async_setup_entry", return_value=True),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: TEST_HOST}
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_manual_setup_device_offline(menuai: menuai) -> None:
    """Test manually setting up, device offline."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    with patch(
        "menuai.components.goodwe.config_flow.connect",
        side_effect=InverterError,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: TEST_HOST}
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_HOST: "connection_error"}
