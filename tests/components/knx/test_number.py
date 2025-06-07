"""Test KNX number."""

import pytest

from menuai.components.knx.const import CONF_RESPOND_TO_READ, KNX_ADDRESS
from menuai.components.knx.schema import NumberSchema
from menuai.const import CONF_NAME, CONF_TYPE
from menuai.core import menuai, State
from menuai.exceptions import ServiceValidationError

from .conftest import KNXTestKit

from tests.common import mock_restore_cache_with_extra_data


async def test_number_set_value(menuai: menuai, knx: KNXTestKit) -> None:
    """Test KNX number with passive_address and respond_to_read restoring state."""
    test_address = "1/1/1"
    await knx.setup_integration(
        {
            NumberSchema.PLATFORM: {
                CONF_NAME: "test",
                KNX_ADDRESS: test_address,
                CONF_TYPE: "percent",
            }
        }
    )
    # set value
    await menuai.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.test", "value": 4.0},
        blocking=True,
    )
    await knx.assert_write(test_address, (0x0A,))
    state = menuai.states.get("number.test")
    assert state.state == "4"
    assert state.attributes.get("unit_of_measurement") == "%"

    # set value out of range
    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.test", "value": 101.0},
            blocking=True,
        )
    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.test", "value": -1},
            blocking=True,
        )
    await knx.assert_no_telegram()
    state = menuai.states.get("number.test")
    assert state.state == "4"

    # update from KNX
    await knx.receive_write(test_address, (0xE6,))
    state = menuai.states.get("number.test")
    assert state.state == "90"


async def test_number_restore_and_respond(menuai: menuai, knx: KNXTestKit) -> None:
    """Test KNX number with passive_address and respond_to_read restoring state."""
    test_address = "1/1/1"
    test_passive_address = "3/3/3"

    RESTORE_DATA = {
        "native_max_value": None,  # Ignored by KNX number
        "native_min_value": None,  # Ignored by KNX number
        "native_step": None,  # Ignored by KNX number
        "native_unit_of_measurement": None,  # Ignored by KNX number
        "native_value": 160.0,
    }

    mock_restore_cache_with_extra_data(
        menuai, ((State("number.test", "abc"), RESTORE_DATA),)
    )
    await knx.setup_integration(
        {
            NumberSchema.PLATFORM: {
                CONF_NAME: "test",
                KNX_ADDRESS: [test_address, test_passive_address],
                CONF_RESPOND_TO_READ: True,
                CONF_TYPE: "illuminance",
            }
        }
    )
    # restored state - doesn't send telegram
    state = menuai.states.get("number.test")
    assert state.state == "160.0"
    assert state.attributes.get("unit_of_measurement") == "lx"
    await knx.assert_telegram_count(0)

    # respond with restored state
    await knx.receive_read(test_address)
    await knx.assert_response(test_address, (0x1F, 0xD0))

    # don't respond to passive address
    await knx.receive_read(test_passive_address)
    await knx.assert_no_telegram()

    # update from KNX passive address
    await knx.receive_write(test_passive_address, (0x4E, 0xDE))
    state = menuai.states.get("number.test")
    assert state.state == "9000.96"
