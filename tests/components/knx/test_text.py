"""Test KNX number."""

from menuai.components.knx.const import CONF_RESPOND_TO_READ, KNX_ADDRESS
from menuai.components.knx.schema import TextSchema
from menuai.const import CONF_NAME
from menuai.core import menuai, State

from .conftest import KNXTestKit

from tests.common import mock_restore_cache


async def test_text(menuai: menuai, knx: KNXTestKit) -> None:
    """Test KNX text."""
    test_address = "1/1/1"
    await knx.setup_integration(
        {
            TextSchema.PLATFORM: {
                CONF_NAME: "test",
                KNX_ADDRESS: test_address,
            }
        }
    )
    # set value
    await menuai.services.async_call(
        "text",
        "set_value",
        {"entity_id": "text.test", "value": "hello world"},
        blocking=True,
    )
    await knx.assert_write(
        test_address,
        (
            0x68,
            0x65,
            0x6C,
            0x6C,
            0x6F,
            0x20,
            0x77,
            0x6F,
            0x72,
            0x6C,
            0x64,
            0x0,
            0x0,
            0x0,
        ),
    )
    state = menuai.states.get("text.test")
    assert state.state == "hello world"

    # update from KNX
    await knx.receive_write(
        test_address,
        (0x68, 0x61, 0x6C, 0x6C, 0x6F, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0),
    )
    state = menuai.states.get("text.test")
    assert state.state == "hallo"


async def test_text_restore_and_respond(menuai: menuai, knx: KNXTestKit) -> None:
    """Test KNX text with passive_address, restoring state and respond_to_read."""
    test_address = "1/1/1"
    test_passive_address = "3/3/3"

    fake_state = State("text.test", "test test")
    mock_restore_cache(menuai, (fake_state,))

    await knx.setup_integration(
        {
            TextSchema.PLATFORM: {
                CONF_NAME: "test",
                KNX_ADDRESS: [test_address, test_passive_address],
                CONF_RESPOND_TO_READ: True,
            }
        }
    )
    # restored state - doesn't send telegram
    state = menuai.states.get("text.test")
    assert state.state == "test test"
    await knx.assert_telegram_count(0)

    # respond with restored state
    await knx.receive_read(test_address)
    await knx.assert_response(
        test_address,
        (0x74, 0x65, 0x73, 0x74, 0x20, 0x74, 0x65, 0x73, 0x74, 0x0, 0x0, 0x0, 0x0, 0x0),
    )

    # don't respond to passive address
    await knx.receive_read(test_passive_address)
    await knx.assert_no_telegram()

    # update from KNX passive address
    await knx.receive_write(
        test_passive_address,
        (0x68, 0x61, 0x6C, 0x6C, 0x6F, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0),
    )
    state = menuai.states.get("text.test")
    assert state.state == "hallo"
