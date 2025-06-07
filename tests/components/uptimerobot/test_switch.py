"""Test UptimeRobot switch."""

from unittest.mock import patch

import pytest
from pyuptimerobot import UptimeRobotAuthenticationException, UptimeRobotException

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError

from .common import (
    MOCK_UPTIMEROBOT_CONFIG_ENTRY_DATA,
    MOCK_UPTIMEROBOT_MONITOR,
    MOCK_UPTIMEROBOT_MONITOR_PAUSED,
    UPTIMEROBOT_SWITCH_TEST_ENTITY,
    MockApiResponseKey,
    mock_uptimerobot_api_response,
    setup_uptimerobot_integration,
)

from tests.common import MockConfigEntry


async def test_presentation(menuai: menuai) -> None:
    """Test the presentation of UptimeRobot switches."""
    await setup_uptimerobot_integration(menuai)

    entity = menuai.states.get(UPTIMEROBOT_SWITCH_TEST_ENTITY)

    assert entity.state == STATE_ON
    assert entity.attributes["target"] == MOCK_UPTIMEROBOT_MONITOR["url"]


async def test_switch_off(menuai: menuai) -> None:
    """Test entity unavailable on update failure."""

    mock_entry = MockConfigEntry(**MOCK_UPTIMEROBOT_CONFIG_ENTRY_DATA)
    mock_entry.add_to_menuai(menuai)

    with (
        patch(
            "pyuptimerobot.UptimeRobot.async_get_monitors",
            return_value=mock_uptimerobot_api_response(
                data=[MOCK_UPTIMEROBOT_MONITOR_PAUSED]
            ),
        ),
        patch(
            "pyuptimerobot.UptimeRobot.async_edit_monitor",
            return_value=mock_uptimerobot_api_response(),
        ),
    ):
        assert await menuai.config_entries.async_setup(mock_entry.entry_id)
        await menuai.async_block_till_done()

        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: UPTIMEROBOT_SWITCH_TEST_ENTITY},
            blocking=True,
        )

    entity = menuai.states.get(UPTIMEROBOT_SWITCH_TEST_ENTITY)
    assert entity.state == STATE_OFF


async def test_switch_on(menuai: menuai) -> None:
    """Test entity unaviable on update failure."""

    mock_entry = MockConfigEntry(**MOCK_UPTIMEROBOT_CONFIG_ENTRY_DATA)
    mock_entry.add_to_menuai(menuai)

    with (
        patch(
            "pyuptimerobot.UptimeRobot.async_get_monitors",
            return_value=mock_uptimerobot_api_response(data=[MOCK_UPTIMEROBOT_MONITOR]),
        ),
        patch(
            "pyuptimerobot.UptimeRobot.async_edit_monitor",
            return_value=mock_uptimerobot_api_response(),
        ),
    ):
        assert await menuai.config_entries.async_setup(mock_entry.entry_id)
        await menuai.async_block_till_done()

        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: UPTIMEROBOT_SWITCH_TEST_ENTITY},
            blocking=True,
        )

        entity = menuai.states.get(UPTIMEROBOT_SWITCH_TEST_ENTITY)
        assert entity.state == STATE_ON


async def test_authentication_error(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test authentication error turning switch on/off."""
    await setup_uptimerobot_integration(menuai)

    entity = menuai.states.get(UPTIMEROBOT_SWITCH_TEST_ENTITY)
    assert entity.state == STATE_ON

    with (
        patch(
            "pyuptimerobot.UptimeRobot.async_edit_monitor",
            side_effect=UptimeRobotAuthenticationException,
        ),
        patch(
            "menuai.config_entries.ConfigEntry.async_start_reauth"
        ) as config_entry_reauth,
    ):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: UPTIMEROBOT_SWITCH_TEST_ENTITY},
            blocking=True,
        )

        assert config_entry_reauth.assert_called


async def test_action_execution_failure(menuai: menuai) -> None:
    """Test turning switch on/off failure."""
    await setup_uptimerobot_integration(menuai)

    entity = menuai.states.get(UPTIMEROBOT_SWITCH_TEST_ENTITY)
    assert entity.state == STATE_ON

    with (
        patch(
            "pyuptimerobot.UptimeRobot.async_edit_monitor",
            side_effect=UptimeRobotException,
        ),
        pytest.raises(menuaiError) as exc_info,
    ):
        await menuai.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: UPTIMEROBOT_SWITCH_TEST_ENTITY},
            blocking=True,
        )

    assert exc_info.value.translation_domain == "uptimerobot"
    assert exc_info.value.translation_key == "api_exception"
    assert exc_info.value.translation_placeholders == {
        "error": "UptimeRobotException()"
    }


async def test_switch_api_failure(menuai: menuai) -> None:
    """Test general exception turning switch on/off."""
    await setup_uptimerobot_integration(menuai)

    entity = menuai.states.get(UPTIMEROBOT_SWITCH_TEST_ENTITY)
    assert entity.state == STATE_ON

    with patch(
        "pyuptimerobot.UptimeRobot.async_edit_monitor",
        return_value=mock_uptimerobot_api_response(key=MockApiResponseKey.ERROR),
    ):
        with pytest.raises(menuaiError) as exc_info:
            await menuai.services.async_call(
                SWITCH_DOMAIN,
                SERVICE_TURN_OFF,
                {ATTR_ENTITY_ID: UPTIMEROBOT_SWITCH_TEST_ENTITY},
                blocking=True,
            )

        assert exc_info.value.translation_domain == "uptimerobot"
        assert exc_info.value.translation_key == "api_exception"
        assert exc_info.value.translation_placeholders == {
            "error": "test error from API."
        }
