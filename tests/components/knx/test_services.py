"""Test KNX services."""

from unittest.mock import patch

import pytest
from xknx.telegram.apci import GroupValueResponse, GroupValueWrite

from menuai.components.knx import async_unload_entry as knx_async_unload_entry
from menuai.components.knx.const import DOMAIN
from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.exceptions import menuaiError

from .conftest import KNXTestKit

from tests.common import async_capture_events


@pytest.mark.parametrize(
    ("service_payload", "expected_telegrams", "expected_apci"),
    [
        # send DPT 1 telegram
        (
            {"address": "1/2/3", "payload": True, "response": True},
            [("1/2/3", True)],
            GroupValueResponse,
        ),
        (
            {"address": "1/2/3", "payload": True, "response": False},
            [("1/2/3", True)],
            GroupValueWrite,
        ),
        # send DPT 5 telegram
        (
            {"address": "1/2/3", "payload": [99], "response": True},
            [("1/2/3", (99,))],
            GroupValueResponse,
        ),
        (
            {"address": "1/2/3", "payload": [99], "response": False},
            [("1/2/3", (99,))],
            GroupValueWrite,
        ),
        # send DPT 5 percent telegram
        (
            {"address": "1/2/3", "payload": 99, "type": "percent", "response": True},
            [("1/2/3", (0xFC,))],
            GroupValueResponse,
        ),
        (
            {"address": "1/2/3", "payload": 99, "type": "percent", "response": False},
            [("1/2/3", (0xFC,))],
            GroupValueWrite,
        ),
        # send temperature DPT 9 telegram
        (
            {
                "address": "1/2/3",
                "payload": 21.0,
                "type": "temperature",
                "response": True,
            },
            [("1/2/3", (0x0C, 0x1A))],
            GroupValueResponse,
        ),
        (
            {
                "address": "1/2/3",
                "payload": 21.0,
                "type": "temperature",
                "response": False,
            },
            [("1/2/3", (0x0C, 0x1A))],
            GroupValueWrite,
        ),
        # send multiple telegrams
        (
            {
                "address": ["1/2/3", "2/2/2", "3/3/3"],
                "payload": 99,
                "type": "percent",
                "response": True,
            },
            [
                ("1/2/3", (0xFC,)),
                ("2/2/2", (0xFC,)),
                ("3/3/3", (0xFC,)),
            ],
            GroupValueResponse,
        ),
        (
            {
                "address": ["1/2/3", "2/2/2", "3/3/3"],
                "payload": 99,
                "type": "percent",
                "response": False,
            },
            [
                ("1/2/3", (0xFC,)),
                ("2/2/2", (0xFC,)),
                ("3/3/3", (0xFC,)),
            ],
            GroupValueWrite,
        ),
    ],
)
async def test_send(
    menuai: menuai,
    knx: KNXTestKit,
    service_payload,
    expected_telegrams,
    expected_apci,
) -> None:
    """Test `knx.send` service."""
    await knx.setup_integration()

    await menuai.services.async_call(
        "knx",
        "send",
        service_payload,
        blocking=True,
    )

    for expected_response in expected_telegrams:
        group_address, payload = expected_response
        await knx.assert_telegram(group_address, payload, expected_apci)


async def test_read(menuai: menuai, knx: KNXTestKit) -> None:
    """Test `knx.read` service."""
    await knx.setup_integration()

    # send read telegram
    await menuai.services.async_call("knx", "read", {"address": "1/1/1"}, blocking=True)
    await knx.assert_read("1/1/1")

    # send multiple read telegrams
    await menuai.services.async_call(
        "knx",
        "read",
        {"address": ["1/1/1", "2/2/2", "3/3/3"]},
        blocking=True,
    )
    await knx.assert_read("1/1/1")
    await knx.assert_read("2/2/2")
    await knx.assert_read("3/3/3")


async def test_event_register(menuai: menuai, knx: KNXTestKit) -> None:
    """Test `knx.event_register` service."""
    events = async_capture_events(menuai, "knx_event")
    test_address = "1/2/3"

    await knx.setup_integration()

    # no event registered
    await knx.receive_write(test_address, True)
    assert len(events) == 0

    # register event with `type`
    await menuai.services.async_call(
        "knx",
        "event_register",
        {"address": test_address, "type": "2byte_unsigned"},
        blocking=True,
    )
    await knx.receive_write(test_address, (0x04, 0xD2))
    assert len(events) == 1
    typed_event = events.pop()
    assert typed_event.data["data"] == (0x04, 0xD2)
    assert typed_event.data["value"] == 1234

    # remove event registration - no event added
    await menuai.services.async_call(
        "knx",
        "event_register",
        {"address": test_address, "remove": True},
        blocking=True,
    )
    await knx.receive_write(test_address, True)
    assert len(events) == 0

    # register event without `type`
    await menuai.services.async_call(
        "knx", "event_register", {"address": test_address}, blocking=True
    )
    await knx.receive_write(test_address, True)
    await knx.receive_write(test_address, False)
    assert len(events) == 2
    untyped_event_2 = events.pop()
    assert untyped_event_2.data["data"] is False
    assert untyped_event_2.data["value"] is None
    untyped_event_1 = events.pop()
    assert untyped_event_1.data["data"] is True
    assert untyped_event_1.data["value"] is None


async def test_exposure_register(menuai: menuai, knx: KNXTestKit) -> None:
    """Test `knx.exposure_register` service."""
    test_address = "1/2/3"
    test_entity = "fake.entity"
    test_attribute = "fake_attribute"

    await knx.setup_integration()

    # no exposure registered
    menuai.states.async_set(test_entity, STATE_ON, {})
    await menuai.async_block_till_done()
    await knx.assert_no_telegram()

    # register exposure
    await menuai.services.async_call(
        "knx",
        "exposure_register",
        {"address": test_address, "entity_id": test_entity, "type": "binary"},
        blocking=True,
    )
    menuai.states.async_set(test_entity, STATE_OFF, {})
    await menuai.async_block_till_done()
    await knx.assert_write(test_address, False)

    # register exposure
    await menuai.services.async_call(
        "knx",
        "exposure_register",
        {"address": test_address, "remove": True},
        blocking=True,
    )
    menuai.states.async_set(test_entity, STATE_ON, {})
    await menuai.async_block_till_done()
    await knx.assert_no_telegram()

    # register exposure for attribute with default
    await menuai.services.async_call(
        "knx",
        "exposure_register",
        {
            "address": test_address,
            "entity_id": test_entity,
            "attribute": test_attribute,
            "type": "percentU8",
            "default": 0,
        },
        blocking=True,
    )
    # no attribute on first change wouldn't work because no attribute change since last test
    menuai.states.async_set(test_entity, STATE_ON, {test_attribute: 30})
    await menuai.async_block_till_done()
    await knx.assert_write(test_address, (30,))
    menuai.states.async_set(test_entity, STATE_OFF, {})
    await menuai.async_block_till_done()
    await knx.assert_write(test_address, (0,))
    # don't send same value sequentially
    menuai.states.async_set(test_entity, STATE_ON, {test_attribute: 25})
    menuai.states.async_set(test_entity, STATE_ON, {test_attribute: 25})
    menuai.states.async_set(test_entity, STATE_ON, {test_attribute: 25, "unrelated": 2})
    menuai.states.async_set(test_entity, STATE_OFF, {test_attribute: 25})
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()
    await knx.assert_telegram_count(1)
    await knx.assert_write(test_address, (25,))


async def test_reload_service(
    menuai: menuai,
    knx: KNXTestKit,
) -> None:
    """Test reload service."""
    await knx.setup_integration()

    with (
        patch(
            "menuai.components.knx.async_unload_entry",
            wraps=knx_async_unload_entry,
        ) as mock_unload_entry,
        patch("menuai.components.knx.async_setup_entry") as mock_setup_entry,
    ):
        await menuai.services.async_call(
            "knx",
            "reload",
            blocking=True,
        )
        mock_unload_entry.assert_called_once()
        mock_setup_entry.assert_called_once()


async def test_service_setup_failed(menuai: menuai, knx: KNXTestKit) -> None:
    """Test service setup failed."""
    await knx.setup_integration()
    await menuai.config_entries.async_unload(knx.mock_config_entry.entry_id)

    with pytest.raises(menuaiError) as exc_info:
        await menuai.services.async_call(
            "knx",
            "send",
            {"address": "1/2/3", "payload": True, "response": False},
            blocking=True,
        )
    assert exc_info.value.translation_domain == DOMAIN
    assert exc_info.value.translation_key == "integration_not_loaded"
