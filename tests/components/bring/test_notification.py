"""Test todo entity notification action of the Bring! integration."""

import re
from unittest.mock import AsyncMock

from bring_api import BringNotificationType, BringRequestException
import pytest

from menuai.components.bring.const import (
    ATTR_ITEM_NAME,
    ATTR_NOTIFICATION_TYPE,
    DOMAIN,
    SERVICE_PUSH_NOTIFICATION,
)
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.exceptions import menuaiError

from tests.common import MockConfigEntry


async def test_send_notification(
    menuai: menuai,
    bring_config_entry: MockConfigEntry,
    mock_bring_client: AsyncMock,
) -> None:
    """Test send bring push notification."""

    bring_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(bring_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert bring_config_entry.state is ConfigEntryState.LOADED

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_PUSH_NOTIFICATION,
        service_data={
            ATTR_NOTIFICATION_TYPE: "GOING_SHOPPING",
        },
        target={ATTR_ENTITY_ID: "todo.einkauf"},
        blocking=True,
    )

    mock_bring_client.notify.assert_called_once_with(
        "e542eef6-dba7-4c31-a52c-29e6ab9d83a5",
        BringNotificationType.GOING_SHOPPING,
        None,
    )


async def test_send_notification_exception(
    menuai: menuai,
    bring_config_entry: MockConfigEntry,
    mock_bring_client: AsyncMock,
) -> None:
    """Test send bring push notification with exception."""

    bring_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(bring_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert bring_config_entry.state is ConfigEntryState.LOADED
    mock_bring_client.notify.side_effect = BringRequestException
    with pytest.raises(
        menuaiError,
        match="Failed to send push notification for Bring! due to a connection error, try again later",
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_PUSH_NOTIFICATION,
            service_data={
                ATTR_NOTIFICATION_TYPE: "GOING_SHOPPING",
            },
            target={ATTR_ENTITY_ID: "todo.einkauf"},
            blocking=True,
        )


async def test_send_notification_service_validation_error(
    menuai: menuai,
    bring_config_entry: MockConfigEntry,
    mock_bring_client: AsyncMock,
) -> None:
    """Test send bring push notification."""

    bring_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(bring_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert bring_config_entry.state is ConfigEntryState.LOADED
    mock_bring_client.notify.side_effect = ValueError
    with pytest.raises(
        menuaiError,
        match=re.escape(
            "This action requires field item, please enter a valid value for item"
        ),
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_PUSH_NOTIFICATION,
            service_data={ATTR_NOTIFICATION_TYPE: "URGENT_MESSAGE", ATTR_ITEM_NAME: ""},
            target={ATTR_ENTITY_ID: "todo.einkauf"},
            blocking=True,
        )
