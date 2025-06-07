"""Test the services for the Flo by Moen integration."""

import pytest
from voluptuous.error import MultipleInvalid

from menuai.components.flo.const import DOMAIN
from menuai.components.flo.switch import (
    ATTR_REVERT_TO_MODE,
    ATTR_SLEEP_MINUTES,
    SERVICE_RUN_HEALTH_TEST,
    SERVICE_SET_AWAY_MODE,
    SERVICE_SET_HOME_MODE,
    SERVICE_SET_SLEEP_MODE,
    SYSTEM_MODE_HOME,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.test_util.aiohttp import AiohttpClientMocker

SWITCH_ENTITY_ID = "switch.smart_water_shutoff_shutoff_valve"


@pytest.mark.usefixtures("aioclient_mock_fixture")
async def test_services(
    menuai: menuai,
    config_entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test Flo services."""
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert aioclient_mock.call_count == 8

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_RUN_HEALTH_TEST,
        {ATTR_ENTITY_ID: SWITCH_ENTITY_ID},
        blocking=True,
    )
    await menuai.async_block_till_done()
    assert aioclient_mock.call_count == 9

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SET_AWAY_MODE,
        {ATTR_ENTITY_ID: SWITCH_ENTITY_ID},
        blocking=True,
    )
    await menuai.async_block_till_done()
    assert aioclient_mock.call_count == 10

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SET_HOME_MODE,
        {ATTR_ENTITY_ID: SWITCH_ENTITY_ID},
        blocking=True,
    )
    await menuai.async_block_till_done()
    assert aioclient_mock.call_count == 11

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SET_SLEEP_MODE,
        {
            ATTR_ENTITY_ID: SWITCH_ENTITY_ID,
            ATTR_REVERT_TO_MODE: SYSTEM_MODE_HOME,
            ATTR_SLEEP_MINUTES: 120,
        },
        blocking=True,
    )
    await menuai.async_block_till_done()
    assert aioclient_mock.call_count == 12

    # test calling with a string value to ensure it is converted to int
    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SET_SLEEP_MODE,
        {
            ATTR_ENTITY_ID: SWITCH_ENTITY_ID,
            ATTR_REVERT_TO_MODE: SYSTEM_MODE_HOME,
            ATTR_SLEEP_MINUTES: "120",
        },
        blocking=True,
    )
    await menuai.async_block_till_done()
    assert aioclient_mock.call_count == 13

    # test calling with a non string -> int value and ensure exception is thrown
    with pytest.raises(MultipleInvalid):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SET_SLEEP_MODE,
            {
                ATTR_ENTITY_ID: SWITCH_ENTITY_ID,
                ATTR_REVERT_TO_MODE: SYSTEM_MODE_HOME,
                ATTR_SLEEP_MINUTES: "test",
            },
            blocking=True,
        )
    assert aioclient_mock.call_count == 13
