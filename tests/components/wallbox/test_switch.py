"""Test Wallbox Lock component."""

import pytest
import requests_mock

from menuai.components.switch import SERVICE_TURN_OFF, SERVICE_TURN_ON
from menuai.components.wallbox.const import CHARGER_STATUS_ID_KEY
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.exceptions import ConfigEntryAuthFailed

from . import authorisation_response, setup_integration
from .const import MOCK_SWITCH_ENTITY_ID

from tests.common import MockConfigEntry


async def test_wallbox_switch_class(
    menuai: menuai, entry: MockConfigEntry
) -> None:
    """Test wallbox switch class."""

    await setup_integration(menuai, entry)

    state = menuai.states.get(MOCK_SWITCH_ENTITY_ID)
    assert state
    assert state.state == "on"

    with requests_mock.Mocker() as mock_request:
        mock_request.get(
            "https://user-api.wall-box.com/users/signin",
            json=authorisation_response,
            status_code=200,
        )
        mock_request.post(
            "https://api.wall-box.com/v3/chargers/12345/remote-action",
            json={CHARGER_STATUS_ID_KEY: 193},
            status_code=200,
        )

        await menuai.services.async_call(
            "switch",
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: MOCK_SWITCH_ENTITY_ID,
            },
            blocking=True,
        )

        await menuai.services.async_call(
            "switch",
            SERVICE_TURN_OFF,
            {
                ATTR_ENTITY_ID: MOCK_SWITCH_ENTITY_ID,
            },
            blocking=True,
        )


async def test_wallbox_switch_class_connection_error(
    menuai: menuai, entry: MockConfigEntry
) -> None:
    """Test wallbox switch class connection error."""

    await setup_integration(menuai, entry)

    with requests_mock.Mocker() as mock_request:
        mock_request.get(
            "https://user-api.wall-box.com/users/signin",
            json=authorisation_response,
            status_code=200,
        )
        mock_request.post(
            "https://api.wall-box.com/v3/chargers/12345/remote-action",
            json={CHARGER_STATUS_ID_KEY: 193},
            status_code=404,
        )

        with pytest.raises(ConnectionError):
            await menuai.services.async_call(
                "switch",
                SERVICE_TURN_ON,
                {
                    ATTR_ENTITY_ID: MOCK_SWITCH_ENTITY_ID,
                },
                blocking=True,
            )
        with pytest.raises(ConnectionError):
            await menuai.services.async_call(
                "switch",
                SERVICE_TURN_OFF,
                {
                    ATTR_ENTITY_ID: MOCK_SWITCH_ENTITY_ID,
                },
                blocking=True,
            )


async def test_wallbox_switch_class_authentication_error(
    menuai: menuai, entry: MockConfigEntry
) -> None:
    """Test wallbox switch class connection error."""

    await setup_integration(menuai, entry)

    with requests_mock.Mocker() as mock_request:
        mock_request.get(
            "https://user-api.wall-box.com/users/signin",
            json=authorisation_response,
            status_code=200,
        )
        mock_request.post(
            "https://api.wall-box.com/v3/chargers/12345/remote-action",
            json={CHARGER_STATUS_ID_KEY: 193},
            status_code=403,
        )

        with pytest.raises(ConfigEntryAuthFailed):
            await menuai.services.async_call(
                "switch",
                SERVICE_TURN_ON,
                {
                    ATTR_ENTITY_ID: MOCK_SWITCH_ENTITY_ID,
                },
                blocking=True,
            )
        with pytest.raises(ConfigEntryAuthFailed):
            await menuai.services.async_call(
                "switch",
                SERVICE_TURN_OFF,
                {
                    ATTR_ENTITY_ID: MOCK_SWITCH_ENTITY_ID,
                },
                blocking=True,
            )
