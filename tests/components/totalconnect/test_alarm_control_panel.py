"""Tests for the TotalConnect alarm control panel device."""

from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion
from total_connect_client.exceptions import (
    AuthenticationError,
    ServiceUnavailable,
    TotalConnectError,
)

from menuai.components.alarm_control_panel import (
    DOMAIN as ALARM_DOMAIN,
    AlarmControlPanelState,
)
from menuai.components.totalconnect.alarm_control_panel import (
    SERVICE_ALARM_ARM_AWAY_INSTANT,
    SERVICE_ALARM_ARM_HOME_INSTANT,
)
from menuai.components.totalconnect.const import DOMAIN
from menuai.components.totalconnect.coordinator import SCAN_INTERVAL
from menuai.config_entries import SOURCE_REAUTH, ConfigEntryState
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_ALARM_ARM_AWAY,
    SERVICE_ALARM_ARM_HOME,
    SERVICE_ALARM_ARM_NIGHT,
    SERVICE_ALARM_DISARM,
    STATE_UNAVAILABLE,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError, ServiceValidationError
from menuai.helpers import entity_registry as er
from menuai.helpers.entity_component import async_update_entity

from .common import (
    LOCATION_ID,
    RESPONSE_ARM_FAILURE,
    RESPONSE_ARM_SUCCESS,
    RESPONSE_ARMED_AWAY,
    RESPONSE_ARMED_CUSTOM,
    RESPONSE_ARMED_NIGHT,
    RESPONSE_ARMED_STAY,
    RESPONSE_ARMING,
    RESPONSE_DISARM_FAILURE,
    RESPONSE_DISARM_SUCCESS,
    RESPONSE_DISARMED,
    RESPONSE_DISARMING,
    RESPONSE_SUCCESS,
    RESPONSE_UNKNOWN,
    RESPONSE_USER_CODE_INVALID,
    TOTALCONNECT_REQUEST,
    USERCODES,
    setup_platform,
)

from tests.common import async_fire_time_changed, snapshot_platform

ENTITY_ID = "alarm_control_panel.test"
ENTITY_ID_2 = "alarm_control_panel.test_partition_2"
CODE = "-1"
DATA = {ATTR_ENTITY_ID: ENTITY_ID}
DELAY = timedelta(seconds=10)


async def test_attributes(
    menuai: menuai, entity_registry: er.EntityRegistry, snapshot: SnapshotAssertion
) -> None:
    """Test the alarm control panel attributes are correct."""
    entry = await setup_platform(menuai, ALARM_DOMAIN)
    with patch(
        "menuai.components.totalconnect.TotalConnectClient.request",
        return_value=RESPONSE_DISARMED,
    ) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        mock_request.assert_called_once()

        await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)
        assert mock_request.call_count == 1


async def test_arm_home_success(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test arm home method success."""
    responses = [RESPONSE_DISARMED, RESPONSE_ARM_SUCCESS, RESPONSE_ARMED_STAY]
    await setup_platform(menuai, ALARM_DOMAIN)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert menuai.states.get(ENTITY_ID_2).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 1

        await menuai.services.async_call(
            ALARM_DOMAIN, SERVICE_ALARM_ARM_HOME, DATA, blocking=True
        )
        assert mock_request.call_count == 2

        freezer.tick(DELAY)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()
        assert mock_request.call_count == 3
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.ARMED_HOME
        # second partition should not be armed
        assert menuai.states.get(ENTITY_ID_2).state == AlarmControlPanelState.DISARMED


async def test_arm_home_failure(menuai: menuai) -> None:
    """Test arm home method failure."""
    responses = [RESPONSE_DISARMED, RESPONSE_ARM_FAILURE, RESPONSE_USER_CODE_INVALID]
    await setup_platform(menuai, ALARM_DOMAIN)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 1

        with pytest.raises(menuaiError) as err:
            await menuai.services.async_call(
                ALARM_DOMAIN, SERVICE_ALARM_ARM_HOME, DATA, blocking=True
            )
        await menuai.async_block_till_done()
        assert f"{err.value}" == "Failed to arm home test"
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 2

        # config entry usercode is invalid
        with pytest.raises(menuaiError) as err:
            await menuai.services.async_call(
                ALARM_DOMAIN, SERVICE_ALARM_ARM_HOME, DATA, blocking=True
            )
        await menuai.async_block_till_done()
        assert f"{err.value}" == "Usercode is invalid, did not arm home"
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        # should have started a re-auth flow
        assert len(menuai.config_entries.flow.async_progress_by_handler(DOMAIN)) == 1
        assert mock_request.call_count == 3


async def test_arm_home_instant_success(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test arm home instant method success."""
    responses = [RESPONSE_DISARMED, RESPONSE_ARM_SUCCESS, RESPONSE_ARMED_STAY]
    await setup_platform(menuai, ALARM_DOMAIN)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert menuai.states.get(ENTITY_ID_2).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 1

        await menuai.services.async_call(
            DOMAIN, SERVICE_ALARM_ARM_HOME_INSTANT, DATA, blocking=True
        )
        assert mock_request.call_count == 2

        freezer.tick(DELAY)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()
        assert mock_request.call_count == 3
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.ARMED_HOME


async def test_arm_home_instant_failure(menuai: menuai) -> None:
    """Test arm home instant method failure."""
    responses = [RESPONSE_DISARMED, RESPONSE_ARM_FAILURE, RESPONSE_USER_CODE_INVALID]
    await setup_platform(menuai, ALARM_DOMAIN)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 1

        with pytest.raises(menuaiError) as err:
            await menuai.services.async_call(
                DOMAIN, SERVICE_ALARM_ARM_HOME_INSTANT, DATA, blocking=True
            )
        await menuai.async_block_till_done()
        assert f"{err.value}" == "Failed to arm home instant test"
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 2

        # usercode is invalid
        with pytest.raises(menuaiError) as err:
            await menuai.services.async_call(
                DOMAIN, SERVICE_ALARM_ARM_HOME_INSTANT, DATA, blocking=True
            )
        await menuai.async_block_till_done()
        assert str(err.value) == "Usercode is invalid, did not arm home instant"
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        # should have started a re-auth flow
        assert len(menuai.config_entries.flow.async_progress_by_handler(DOMAIN)) == 1
        assert mock_request.call_count == 3


async def test_arm_away_instant_success(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test arm home instant method success."""
    responses = [RESPONSE_DISARMED, RESPONSE_ARM_SUCCESS, RESPONSE_ARMED_AWAY]
    await setup_platform(menuai, ALARM_DOMAIN)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert menuai.states.get(ENTITY_ID_2).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 1

        await menuai.services.async_call(
            DOMAIN, SERVICE_ALARM_ARM_AWAY_INSTANT, DATA, blocking=True
        )
        assert mock_request.call_count == 2

        freezer.tick(DELAY)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()
        assert mock_request.call_count == 3
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.ARMED_AWAY


async def test_arm_away_instant_failure(menuai: menuai) -> None:
    """Test arm home instant method failure."""
    responses = [RESPONSE_DISARMED, RESPONSE_ARM_FAILURE, RESPONSE_USER_CODE_INVALID]
    await setup_platform(menuai, ALARM_DOMAIN)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 1

        with pytest.raises(menuaiError) as err:
            await menuai.services.async_call(
                DOMAIN, SERVICE_ALARM_ARM_AWAY_INSTANT, DATA, blocking=True
            )
        await menuai.async_block_till_done()
        assert f"{err.value}" == "Failed to arm away instant test"
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 2

        # usercode is invalid
        with pytest.raises(menuaiError) as err:
            await menuai.services.async_call(
                DOMAIN, SERVICE_ALARM_ARM_AWAY_INSTANT, DATA, blocking=True
            )
        await menuai.async_block_till_done()
        assert f"{err.value}" == "Usercode is invalid, did not arm away instant"
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        # should have started a re-auth flow
        assert len(menuai.config_entries.flow.async_progress_by_handler(DOMAIN)) == 1
        assert mock_request.call_count == 3


async def test_arm_away_success(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test arm away method success."""
    responses = [RESPONSE_DISARMED, RESPONSE_ARM_SUCCESS, RESPONSE_ARMED_AWAY]
    await setup_platform(menuai, ALARM_DOMAIN)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 1

        await menuai.services.async_call(
            ALARM_DOMAIN, SERVICE_ALARM_ARM_AWAY, DATA, blocking=True
        )
        assert mock_request.call_count == 2

        freezer.tick(DELAY)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()
        assert mock_request.call_count == 3
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.ARMED_AWAY


async def test_arm_away_failure(menuai: menuai) -> None:
    """Test arm away method failure."""
    responses = [RESPONSE_DISARMED, RESPONSE_ARM_FAILURE, RESPONSE_USER_CODE_INVALID]
    await setup_platform(menuai, ALARM_DOMAIN)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 1

        with pytest.raises(menuaiError) as err:
            await menuai.services.async_call(
                ALARM_DOMAIN, SERVICE_ALARM_ARM_AWAY, DATA, blocking=True
            )
        await menuai.async_block_till_done()
        assert f"{err.value}" == "Failed to arm away test"
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 2

        # usercode is invalid
        with pytest.raises(menuaiError) as err:
            await menuai.services.async_call(
                ALARM_DOMAIN, SERVICE_ALARM_ARM_AWAY, DATA, blocking=True
            )
        await menuai.async_block_till_done()
        assert f"{err.value}" == "Usercode is invalid, did not arm away"
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        # should have started a re-auth flow
        assert len(menuai.config_entries.flow.async_progress_by_handler(DOMAIN)) == 1
        assert mock_request.call_count == 3


async def test_disarm_success(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test disarm method success."""
    responses = [RESPONSE_ARMED_AWAY, RESPONSE_DISARM_SUCCESS, RESPONSE_DISARMED]
    await setup_platform(menuai, ALARM_DOMAIN)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.ARMED_AWAY
        assert mock_request.call_count == 1

        await menuai.services.async_call(
            ALARM_DOMAIN, SERVICE_ALARM_DISARM, DATA, blocking=True
        )
        assert mock_request.call_count == 2

        freezer.tick(DELAY)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()
        assert mock_request.call_count == 3
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED


async def test_disarm_failure(menuai: menuai) -> None:
    """Test disarm method failure."""
    responses = [
        RESPONSE_ARMED_AWAY,
        RESPONSE_DISARM_FAILURE,
        RESPONSE_USER_CODE_INVALID,
    ]
    await setup_platform(menuai, ALARM_DOMAIN)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.ARMED_AWAY
        assert mock_request.call_count == 1

        with pytest.raises(menuaiError) as err:
            await menuai.services.async_call(
                ALARM_DOMAIN, SERVICE_ALARM_DISARM, DATA, blocking=True
            )
        await menuai.async_block_till_done()
        assert f"{err.value}" == "Failed to disarm test"
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.ARMED_AWAY
        assert mock_request.call_count == 2

        # usercode is invalid
        with pytest.raises(menuaiError) as err:
            await menuai.services.async_call(
                ALARM_DOMAIN, SERVICE_ALARM_DISARM, DATA, blocking=True
            )
        await menuai.async_block_till_done()
        assert f"{err.value}" == "Usercode is invalid, did not disarm"
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.ARMED_AWAY
        # should have started a re-auth flow
        assert len(menuai.config_entries.flow.async_progress_by_handler(DOMAIN)) == 1
        assert mock_request.call_count == 3


async def test_disarm_code_required(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test disarm with code."""
    responses = [RESPONSE_ARMED_AWAY, RESPONSE_DISARM_SUCCESS, RESPONSE_DISARMED]
    await setup_platform(menuai, ALARM_DOMAIN, code_required=True)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.ARMED_AWAY
        assert mock_request.call_count == 1

        # runtime user entered code is bad
        DATA_WITH_CODE = DATA.copy()
        DATA_WITH_CODE["code"] = "666"
        with pytest.raises(ServiceValidationError, match="Incorrect code entered"):
            await menuai.services.async_call(
                ALARM_DOMAIN, SERVICE_ALARM_DISARM, DATA_WITH_CODE, blocking=True
            )
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.ARMED_AWAY
        # code check means the call to total_connect never happens
        assert mock_request.call_count == 1

        # runtime user entered code that is in config
        DATA_WITH_CODE["code"] = USERCODES[LOCATION_ID]
        await menuai.services.async_call(
            ALARM_DOMAIN, SERVICE_ALARM_DISARM, DATA_WITH_CODE, blocking=True
        )
        await menuai.async_block_till_done()
        assert mock_request.call_count == 2

        freezer.tick(DELAY)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()
        assert mock_request.call_count == 3
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED


async def test_arm_night_success(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test arm night method success."""
    responses = [RESPONSE_DISARMED, RESPONSE_ARM_SUCCESS, RESPONSE_ARMED_NIGHT]
    await setup_platform(menuai, ALARM_DOMAIN)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 1

        await menuai.services.async_call(
            ALARM_DOMAIN, SERVICE_ALARM_ARM_NIGHT, DATA, blocking=True
        )
        assert mock_request.call_count == 2

        freezer.tick(DELAY)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()
        assert mock_request.call_count == 3
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.ARMED_NIGHT


async def test_arm_night_failure(menuai: menuai) -> None:
    """Test arm night method failure."""
    responses = [RESPONSE_DISARMED, RESPONSE_ARM_FAILURE, RESPONSE_USER_CODE_INVALID]
    await setup_platform(menuai, ALARM_DOMAIN)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 1

        with pytest.raises(menuaiError) as err:
            await menuai.services.async_call(
                ALARM_DOMAIN, SERVICE_ALARM_ARM_NIGHT, DATA, blocking=True
            )
        await menuai.async_block_till_done()
        assert f"{err.value}" == "Failed to arm night test"
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 2

        # usercode is invalid
        with pytest.raises(menuaiError) as err:
            await menuai.services.async_call(
                ALARM_DOMAIN, SERVICE_ALARM_ARM_NIGHT, DATA, blocking=True
            )
        await menuai.async_block_till_done()
        assert f"{err.value}" == "Usercode is invalid, did not arm night"
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        # should have started a re-auth flow
        assert len(menuai.config_entries.flow.async_progress_by_handler(DOMAIN)) == 1
        assert mock_request.call_count == 3


async def test_arming(menuai: menuai, freezer: FrozenDateTimeFactory) -> None:
    """Test arming."""
    responses = [RESPONSE_DISARMED, RESPONSE_SUCCESS, RESPONSE_ARMING]
    await setup_platform(menuai, ALARM_DOMAIN)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 1

        await menuai.services.async_call(
            ALARM_DOMAIN, SERVICE_ALARM_ARM_NIGHT, DATA, blocking=True
        )
        assert mock_request.call_count == 2

        freezer.tick(DELAY)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()
        assert mock_request.call_count == 3
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.ARMING


async def test_disarming(menuai: menuai, freezer: FrozenDateTimeFactory) -> None:
    """Test disarming."""
    responses = [RESPONSE_ARMED_AWAY, RESPONSE_SUCCESS, RESPONSE_DISARMING]
    await setup_platform(menuai, ALARM_DOMAIN)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.ARMED_AWAY
        assert mock_request.call_count == 1

        await menuai.services.async_call(
            ALARM_DOMAIN, SERVICE_ALARM_DISARM, DATA, blocking=True
        )
        assert mock_request.call_count == 2

        freezer.tick(DELAY)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()
        assert mock_request.call_count == 3
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMING


async def test_armed_custom(menuai: menuai) -> None:
    """Test armed custom."""
    responses = [RESPONSE_ARMED_CUSTOM]
    await setup_platform(menuai, ALARM_DOMAIN)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert (
            menuai.states.get(ENTITY_ID).state
            == AlarmControlPanelState.ARMED_CUSTOM_BYPASS
        )
        assert mock_request.call_count == 1


async def test_unknown(menuai: menuai) -> None:
    """Test unknown arm status."""
    responses = [RESPONSE_UNKNOWN]
    await setup_platform(menuai, ALARM_DOMAIN)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert menuai.states.get(ENTITY_ID).state == STATE_UNAVAILABLE
        assert mock_request.call_count == 1


async def test_other_update_failures(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test other failures seen during updates."""
    responses = [
        RESPONSE_DISARMED,
        ServiceUnavailable,
        RESPONSE_DISARMED,
        TotalConnectError,
        RESPONSE_DISARMED,
        ValueError,
    ]
    await setup_platform(menuai, ALARM_DOMAIN)
    with patch(TOTALCONNECT_REQUEST, side_effect=responses) as mock_request:
        # first things work as planned
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 1

        # then an error: ServiceUnavailable --> UpdateFailed
        freezer.tick(SCAN_INTERVAL)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert menuai.states.get(ENTITY_ID).state == STATE_UNAVAILABLE
        assert mock_request.call_count == 2

        # works again
        freezer.tick(SCAN_INTERVAL)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 3

        # then an error: TotalConnectError --> UpdateFailed
        freezer.tick(SCAN_INTERVAL)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert menuai.states.get(ENTITY_ID).state == STATE_UNAVAILABLE
        assert mock_request.call_count == 4

        # works again
        freezer.tick(SCAN_INTERVAL)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert menuai.states.get(ENTITY_ID).state == AlarmControlPanelState.DISARMED
        assert mock_request.call_count == 5

        # unknown TotalConnect status via ValueError
        freezer.tick(SCAN_INTERVAL)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done(wait_background_tasks=True)
        assert menuai.states.get(ENTITY_ID).state == STATE_UNAVAILABLE
        assert mock_request.call_count == 6


async def test_authentication_error(menuai: menuai) -> None:
    """Test other failures seen during updates."""
    entry = await setup_platform(menuai, ALARM_DOMAIN)

    with patch(TOTALCONNECT_REQUEST, side_effect=AuthenticationError):
        await async_update_entity(menuai, ENTITY_ID)
        await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    flows = menuai.config_entries.flow.async_progress()
    assert len(flows) == 1

    flow = flows[0]
    assert flow.get("step_id") == "reauth_confirm"
    assert flow.get("handler") == DOMAIN

    assert "context" in flow
    assert flow["context"].get("source") == SOURCE_REAUTH
    assert flow["context"].get("entry_id") == entry.entry_id
