"""Test Wallbox Lock component."""

import pytest
import requests_mock

from menuai.components.lock import SERVICE_LOCK, SERVICE_UNLOCK
from menuai.components.wallbox.const import CHARGER_LOCKED_UNLOCKED_KEY
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai

from . import (
    authorisation_response,
    setup_integration,
    setup_integration_platform_not_ready,
    setup_integration_read_only,
)
from .const import MOCK_LOCK_ENTITY_ID

from tests.common import MockConfigEntry


async def test_wallbox_lock_class(menuai: menuai, entry: MockConfigEntry) -> None:
    """Test wallbox lock class."""

    await setup_integration(menuai, entry)

    state = menuai.states.get(MOCK_LOCK_ENTITY_ID)
    assert state
    assert state.state == "unlocked"

    with requests_mock.Mocker() as mock_request:
        mock_request.get(
            "https://user-api.wall-box.com/users/signin",
            json=authorisation_response,
            status_code=200,
        )
        mock_request.put(
            "https://api.wall-box.com/v2/charger/12345",
            json={CHARGER_LOCKED_UNLOCKED_KEY: False},
            status_code=200,
        )

        await menuai.services.async_call(
            "lock",
            SERVICE_LOCK,
            {
                ATTR_ENTITY_ID: MOCK_LOCK_ENTITY_ID,
            },
            blocking=True,
        )

        await menuai.services.async_call(
            "lock",
            SERVICE_UNLOCK,
            {
                ATTR_ENTITY_ID: MOCK_LOCK_ENTITY_ID,
            },
            blocking=True,
        )


async def test_wallbox_lock_class_connection_error(
    menuai: menuai, entry: MockConfigEntry
) -> None:
    """Test wallbox lock class connection error."""

    await setup_integration(menuai, entry)

    with requests_mock.Mocker() as mock_request:
        mock_request.get(
            "https://user-api.wall-box.com/users/signin",
            json=authorisation_response,
            status_code=200,
        )
        mock_request.put(
            "https://api.wall-box.com/v2/charger/12345",
            json={CHARGER_LOCKED_UNLOCKED_KEY: False},
            status_code=404,
        )

        with pytest.raises(ConnectionError):
            await menuai.services.async_call(
                "lock",
                SERVICE_LOCK,
                {
                    ATTR_ENTITY_ID: MOCK_LOCK_ENTITY_ID,
                },
                blocking=True,
            )
        with pytest.raises(ConnectionError):
            await menuai.services.async_call(
                "lock",
                SERVICE_UNLOCK,
                {
                    ATTR_ENTITY_ID: MOCK_LOCK_ENTITY_ID,
                },
                blocking=True,
            )


async def test_wallbox_lock_class_authentication_error(
    menuai: menuai, entry: MockConfigEntry
) -> None:
    """Test wallbox lock not loaded on authentication error."""

    await setup_integration_read_only(menuai, entry)

    state = menuai.states.get(MOCK_LOCK_ENTITY_ID)

    assert state is None


async def test_wallbox_lock_class_platform_not_ready(
    menuai: menuai, entry: MockConfigEntry
) -> None:
    """Test wallbox lock not loaded on authentication error."""

    await setup_integration_platform_not_ready(menuai, entry)

    state = menuai.states.get(MOCK_LOCK_ENTITY_ID)

    assert state is None
