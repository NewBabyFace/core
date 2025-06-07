"""Define tests for the Luftdaten config flow."""

from unittest.mock import MagicMock

from luftdaten.exceptions import LuftdatenConnectionError
import pytest

from menuai.components.luftdaten import DOMAIN
from menuai.components.luftdaten.const import CONF_SENSOR_ID
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_SHOW_ON_MAP
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


async def test_duplicate_error(
    menuai: menuai, mock_config_entry: MockConfigEntry
) -> None:
    """Test that errors are shown when duplicates are added."""
    mock_config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_SENSOR_ID: 12345},
    )

    assert result2.get("type") is FlowResultType.ABORT
    assert result2.get("reason") == "already_configured"


async def test_communication_error(
    menuai: menuai, mock_luftdaten: MagicMock
) -> None:
    """Test that no sensor is added while unable to communicate with API."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"

    mock_luftdaten.get_data.side_effect = LuftdatenConnectionError
    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_SENSOR_ID: 12345},
    )

    assert result2.get("type") is FlowResultType.FORM
    assert result2.get("step_id") == "user"
    assert result2.get("errors") == {CONF_SENSOR_ID: "cannot_connect"}

    mock_luftdaten.get_data.side_effect = None
    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={CONF_SENSOR_ID: 12345},
    )

    assert result3.get("type") is FlowResultType.CREATE_ENTRY
    assert result3.get("title") == "12345"
    assert result3.get("data") == {
        CONF_SENSOR_ID: 12345,
        CONF_SHOW_ON_MAP: False,
    }


async def test_invalid_sensor(menuai: menuai, mock_luftdaten: MagicMock) -> None:
    """Test that an invalid sensor throws an error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"

    mock_luftdaten.validate_sensor.return_value = False
    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_SENSOR_ID: 11111},
    )

    assert result2.get("type") is FlowResultType.FORM
    assert result2.get("step_id") == "user"
    assert result2.get("errors") == {CONF_SENSOR_ID: "invalid_sensor"}

    mock_luftdaten.validate_sensor.return_value = True
    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={CONF_SENSOR_ID: 12345},
    )

    assert result3.get("type") is FlowResultType.CREATE_ENTRY
    assert result3.get("title") == "12345"
    assert result3.get("data") == {
        CONF_SENSOR_ID: 12345,
        CONF_SHOW_ON_MAP: False,
    }


@pytest.mark.usefixtures("mock_setup_entry", "mock_luftdaten")
async def test_step_user(
    menuai: menuai,
) -> None:
    """Test that the user step works."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("step_id") == "user"

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_SENSOR_ID: 12345,
            CONF_SHOW_ON_MAP: True,
        },
    )

    assert result2.get("type") is FlowResultType.CREATE_ENTRY
    assert result2.get("title") == "12345"
    assert result2.get("data") == {
        CONF_SENSOR_ID: 12345,
        CONF_SHOW_ON_MAP: True,
    }
