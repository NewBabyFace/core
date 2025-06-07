"""Tests for the Withings component."""

from unittest.mock import AsyncMock

from aiohttp.client_exceptions import ClientResponseError
from aiowithings import NotificationCategory
from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from menuai.core import menuai

from . import call_webhook, prepare_webhook_setup, setup_integration
from .conftest import USER_ID, WEBHOOK_ID

from tests.common import MockConfigEntry
from tests.typing import ClientSessionGenerator


async def test_binary_sensor(
    menuai: menuai,
    withings: AsyncMock,
    webhook_config_entry: MockConfigEntry,
    menuai_client_no_auth: ClientSessionGenerator,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test binary sensor."""
    await setup_integration(menuai, webhook_config_entry)
    await prepare_webhook_setup(menuai, freezer)

    client = await menuai_client_no_auth()

    entity_id = "binary_sensor.henk_in_bed"

    assert menuai.states.get(entity_id) is None

    resp = await call_webhook(
        menuai,
        WEBHOOK_ID,
        {"userid": USER_ID, "appli": NotificationCategory.IN_BED},
        client,
    )
    assert resp.message_code == 0
    await menuai.async_block_till_done()
    assert menuai.states.get(entity_id).state == STATE_ON

    resp = await call_webhook(
        menuai,
        WEBHOOK_ID,
        {"userid": USER_ID, "appli": NotificationCategory.OUT_BED},
        client,
    )
    assert resp.message_code == 0
    await menuai.async_block_till_done()
    assert menuai.states.get(entity_id).state == STATE_OFF

    await menuai.config_entries.async_reload(webhook_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == STATE_UNKNOWN
    assert (
        "Platform withings does not generate unique IDs. ID withings_12345_in_bed "
        "already exists - ignoring binary_sensor.henk_in_bed" not in caplog.text
    )


async def test_polling_binary_sensor(
    menuai: menuai,
    withings: AsyncMock,
    polling_config_entry: MockConfigEntry,
    menuai_client_no_auth: ClientSessionGenerator,
) -> None:
    """Test binary sensor."""
    await setup_integration(menuai, polling_config_entry, False)

    client = await menuai_client_no_auth()

    entity_id = "binary_sensor.henk_in_bed"

    assert menuai.states.get(entity_id) is None

    with pytest.raises(ClientResponseError):
        await call_webhook(
            menuai,
            WEBHOOK_ID,
            {"userid": USER_ID, "appli": NotificationCategory.IN_BED},
            client,
        )
