"""The lock tests for the august platform."""

import datetime
from unittest.mock import Mock

from aiohttp import ClientResponseError
from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion
from yalexs.manager.activity import INITIAL_LOCK_RESYNC_TIME
from yalexs.pubnub_async import AugustPubNub

from menuai.components.lock import DOMAIN as LOCK_DOMAIN, LockState
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_LOCK,
    SERVICE_OPEN,
    SERVICE_UNLOCK,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from menuai.core import menuai
from menuai.exceptions import ServiceNotSupported
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from .mocks import (
    _create_august_with_devices,
    _mock_activities_from_fixture,
    _mock_doorsense_enabled_august_lock_detail,
    _mock_lock_from_fixture,
    _mock_lock_with_unlatch,
    _mock_operative_august_lock_detail,
)

from tests.common import async_fire_time_changed


async def test_lock_device_registry(
    menuai: menuai, device_registry: dr.DeviceRegistry, snapshot: SnapshotAssertion
) -> None:
    """Test creation of a lock with doorsense and bridge ands up in the registry."""
    lock_one = await _mock_doorsense_enabled_august_lock_detail(menuai)
    await _create_august_with_devices(menuai, [lock_one])

    reg_device = device_registry.async_get_device(
        identifiers={("august", "online_with_doorsense")}
    )
    assert reg_device == snapshot


async def test_lock_changed_by(menuai: menuai) -> None:
    """Test creation of a lock with doorsense and bridge."""
    lock_one = await _mock_doorsense_enabled_august_lock_detail(menuai)

    activities = await _mock_activities_from_fixture(menuai, "get_activity.lock.json")
    await _create_august_with_devices(menuai, [lock_one], activities=activities)

    lock_state = menuai.states.get("lock.online_with_doorsense_name")

    assert lock_state.state == LockState.LOCKED
    assert lock_state.attributes["changed_by"] == "Your favorite elven princess"


async def test_state_locking(menuai: menuai) -> None:
    """Test creation of a lock with doorsense and bridge that is locking."""
    lock_one = await _mock_doorsense_enabled_august_lock_detail(menuai)

    activities = await _mock_activities_from_fixture(menuai, "get_activity.locking.json")
    await _create_august_with_devices(menuai, [lock_one], activities=activities)

    assert menuai.states.get("lock.online_with_doorsense_name").state == LockState.LOCKING


async def test_state_unlocking(menuai: menuai) -> None:
    """Test creation of a lock with doorsense and bridge that is unlocking."""
    lock_one = await _mock_doorsense_enabled_august_lock_detail(menuai)

    activities = await _mock_activities_from_fixture(
        menuai, "get_activity.unlocking.json"
    )
    await _create_august_with_devices(menuai, [lock_one], activities=activities)

    assert (
        menuai.states.get("lock.online_with_doorsense_name").state == LockState.UNLOCKING
    )


async def test_state_jammed(menuai: menuai) -> None:
    """Test creation of a lock with doorsense and bridge that is jammed."""
    lock_one = await _mock_doorsense_enabled_august_lock_detail(menuai)

    activities = await _mock_activities_from_fixture(menuai, "get_activity.jammed.json")
    await _create_august_with_devices(menuai, [lock_one], activities=activities)

    assert menuai.states.get("lock.online_with_doorsense_name").state == LockState.JAMMED


async def test_one_lock_operation(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test creation of a lock with doorsense and bridge."""
    lock_one = await _mock_doorsense_enabled_august_lock_detail(menuai)
    await _create_august_with_devices(menuai, [lock_one])
    states = menuai.states

    lock_state = states.get("lock.online_with_doorsense_name")

    assert lock_state.state == LockState.LOCKED

    assert lock_state.attributes["battery_level"] == 92
    assert lock_state.attributes["friendly_name"] == "online_with_doorsense Name"

    data = {ATTR_ENTITY_ID: "lock.online_with_doorsense_name"}
    await menuai.services.async_call(LOCK_DOMAIN, SERVICE_UNLOCK, data, blocking=True)

    lock_state = states.get("lock.online_with_doorsense_name")
    assert lock_state.state == LockState.UNLOCKED

    assert lock_state.attributes["battery_level"] == 92
    assert lock_state.attributes["friendly_name"] == "online_with_doorsense Name"

    await menuai.services.async_call(LOCK_DOMAIN, SERVICE_LOCK, data, blocking=True)

    assert states.get("lock.online_with_doorsense_name").state == LockState.LOCKED

    # No activity means it will be unavailable until the activity feed has data
    lock_operator_sensor = entity_registry.async_get(
        "sensor.online_with_doorsense_name_operator"
    )
    assert lock_operator_sensor
    assert (
        states.get("sensor.online_with_doorsense_name_operator").state == STATE_UNKNOWN
    )


async def test_open_lock_operation(menuai: menuai) -> None:
    """Test open lock operation using the open service."""
    lock_with_unlatch = await _mock_lock_with_unlatch(menuai)
    await _create_august_with_devices(menuai, [lock_with_unlatch])

    lock_online_with_unlatch_name = menuai.states.get("lock.online_with_unlatch_name")
    assert lock_online_with_unlatch_name.state == LockState.LOCKED

    data = {ATTR_ENTITY_ID: "lock.online_with_unlatch_name"}
    await menuai.services.async_call(LOCK_DOMAIN, SERVICE_OPEN, data, blocking=True)

    lock_online_with_unlatch_name = menuai.states.get("lock.online_with_unlatch_name")
    assert lock_online_with_unlatch_name.state == LockState.UNLOCKED


async def test_open_lock_operation_pubnub_connected(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test open lock operation using the open service when pubnub is connected."""
    lock_with_unlatch = await _mock_lock_with_unlatch(menuai)
    assert lock_with_unlatch.pubsub_channel == "pubsub"

    pubnub = AugustPubNub()
    await _create_august_with_devices(menuai, [lock_with_unlatch], pubnub=pubnub)
    pubnub.connected = True

    assert menuai.states.get("lock.online_with_unlatch_name").state == LockState.LOCKED

    data = {ATTR_ENTITY_ID: "lock.online_with_unlatch_name"}
    await menuai.services.async_call(LOCK_DOMAIN, SERVICE_OPEN, data, blocking=True)

    pubnub.message(
        pubnub,
        Mock(
            channel=lock_with_unlatch.pubsub_channel,
            timetoken=(dt_util.utcnow().timestamp() + 2) * 10000000,
            message={
                "status": "kAugLockState_Unlocked",
            },
        ),
    )
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    assert menuai.states.get("lock.online_with_unlatch_name").state == LockState.UNLOCKED
    await menuai.async_block_till_done()


async def test_one_lock_operation_pubnub_connected(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test lock and unlock operations are async when pubnub is connected."""
    lock_one = await _mock_doorsense_enabled_august_lock_detail(menuai)
    assert lock_one.pubsub_channel == "pubsub"

    pubnub = AugustPubNub()
    await _create_august_with_devices(menuai, [lock_one], pubnub=pubnub)
    pubnub.connected = True

    lock_state = menuai.states.get("lock.online_with_doorsense_name")

    assert lock_state.state == LockState.LOCKED

    assert lock_state.attributes["battery_level"] == 92
    assert lock_state.attributes["friendly_name"] == "online_with_doorsense Name"

    data = {ATTR_ENTITY_ID: "lock.online_with_doorsense_name"}
    await menuai.services.async_call(LOCK_DOMAIN, SERVICE_UNLOCK, data, blocking=True)

    pubnub.message(
        pubnub,
        Mock(
            channel=lock_one.pubsub_channel,
            timetoken=(dt_util.utcnow().timestamp() + 1) * 10000000,
            message={
                "status": "kAugLockState_Unlocked",
            },
        ),
    )
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    lock_state = menuai.states.get("lock.online_with_doorsense_name")
    assert lock_state.state == LockState.UNLOCKED

    assert lock_state.attributes["battery_level"] == 92
    assert lock_state.attributes["friendly_name"] == "online_with_doorsense Name"

    await menuai.services.async_call(LOCK_DOMAIN, SERVICE_LOCK, data, blocking=True)

    pubnub.message(
        pubnub,
        Mock(
            channel=lock_one.pubsub_channel,
            timetoken=(dt_util.utcnow().timestamp() + 2) * 10000000,
            message={
                "status": "kAugLockState_Locked",
            },
        ),
    )
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    lock_state = menuai.states.get("lock.online_with_doorsense_name")
    assert lock_state.state == LockState.LOCKED

    # No activity means it will be unavailable until the activity feed has data
    lock_operator_sensor = entity_registry.async_get(
        "sensor.online_with_doorsense_name_operator"
    )
    assert lock_operator_sensor
    assert (
        menuai.states.get("sensor.online_with_doorsense_name_operator").state
        == STATE_UNKNOWN
    )

    freezer.tick(INITIAL_LOCK_RESYNC_TIME)

    pubnub.message(
        pubnub,
        Mock(
            channel=lock_one.pubsub_channel,
            timetoken=(dt_util.utcnow().timestamp() + 2) * 10000000,
            message={
                "status": "kAugLockState_Unlocked",
            },
        ),
    )
    await menuai.async_block_till_done()

    lock_state = menuai.states.get("lock.online_with_doorsense_name")
    assert lock_state.state == LockState.UNLOCKED


async def test_lock_jammed(menuai: menuai) -> None:
    """Test lock gets jammed on unlock."""

    def _unlock_return_activities_side_effect(access_token, device_id):
        raise ClientResponseError(None, None, status=531)

    lock_one = await _mock_doorsense_enabled_august_lock_detail(menuai)
    await _create_august_with_devices(
        menuai,
        [lock_one],
        api_call_side_effects={
            "unlock_return_activities": _unlock_return_activities_side_effect
        },
    )

    lock_state = menuai.states.get("lock.online_with_doorsense_name")

    assert lock_state.state == LockState.LOCKED

    assert lock_state.attributes["battery_level"] == 92
    assert lock_state.attributes["friendly_name"] == "online_with_doorsense Name"

    data = {ATTR_ENTITY_ID: "lock.online_with_doorsense_name"}
    await menuai.services.async_call(LOCK_DOMAIN, SERVICE_UNLOCK, data, blocking=True)

    lock_state = menuai.states.get("lock.online_with_doorsense_name")
    assert lock_state.state == LockState.JAMMED


async def test_lock_throws_exception_on_unknown_status_code(
    menuai: menuai,
) -> None:
    """Test lock throws exception."""

    def _unlock_return_activities_side_effect(access_token, device_id):
        raise ClientResponseError(None, None, status=500)

    lock_one = await _mock_doorsense_enabled_august_lock_detail(menuai)
    await _create_august_with_devices(
        menuai,
        [lock_one],
        api_call_side_effects={
            "unlock_return_activities": _unlock_return_activities_side_effect
        },
    )

    lock_state = menuai.states.get("lock.online_with_doorsense_name")

    assert lock_state.state == LockState.LOCKED

    assert lock_state.attributes["battery_level"] == 92
    assert lock_state.attributes["friendly_name"] == "online_with_doorsense Name"

    data = {ATTR_ENTITY_ID: "lock.online_with_doorsense_name"}
    with pytest.raises(ClientResponseError):
        await menuai.services.async_call(LOCK_DOMAIN, SERVICE_UNLOCK, data, blocking=True)


async def test_one_lock_unknown_state(menuai: menuai) -> None:
    """Test creation of a lock with doorsense and bridge."""
    lock_one = await _mock_lock_from_fixture(
        menuai,
        "get_lock.online.unknown_state.json",
    )
    await _create_august_with_devices(menuai, [lock_one])

    assert menuai.states.get("lock.brokenid_name").state == STATE_UNKNOWN


async def test_lock_bridge_offline(menuai: menuai) -> None:
    """Test creation of a lock with doorsense and bridge that goes offline."""
    lock_one = await _mock_doorsense_enabled_august_lock_detail(menuai)

    activities = await _mock_activities_from_fixture(
        menuai, "get_activity.bridge_offline.json"
    )
    await _create_august_with_devices(menuai, [lock_one], activities=activities)

    assert menuai.states.get("lock.online_with_doorsense_name").state == STATE_UNAVAILABLE


async def test_lock_bridge_online(menuai: menuai) -> None:
    """Test creation of a lock with doorsense and bridge that goes offline."""
    lock_one = await _mock_doorsense_enabled_august_lock_detail(menuai)

    activities = await _mock_activities_from_fixture(
        menuai, "get_activity.bridge_online.json"
    )
    await _create_august_with_devices(menuai, [lock_one], activities=activities)

    assert menuai.states.get("lock.online_with_doorsense_name").state == LockState.LOCKED


async def test_lock_update_via_pubnub(menuai: menuai) -> None:
    """Test creation of a lock with doorsense and bridge."""
    lock_one = await _mock_doorsense_enabled_august_lock_detail(menuai)
    states = menuai.states
    assert lock_one.pubsub_channel == "pubsub"
    pubnub = AugustPubNub()

    activities = await _mock_activities_from_fixture(menuai, "get_activity.lock.json")
    config_entry = await _create_august_with_devices(
        menuai, [lock_one], activities=activities, pubnub=pubnub
    )
    pubnub.connected = True

    assert states.get("lock.online_with_doorsense_name").state == LockState.LOCKED

    pubnub.message(
        pubnub,
        Mock(
            channel=lock_one.pubsub_channel,
            timetoken=dt_util.utcnow().timestamp() * 10000000,
            message={
                "status": "kAugLockState_Unlocking",
            },
        ),
    )

    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    assert states.get("lock.online_with_doorsense_name").state == LockState.UNLOCKING

    pubnub.message(
        pubnub,
        Mock(
            channel=lock_one.pubsub_channel,
            timetoken=(dt_util.utcnow().timestamp() + 1) * 10000000,
            message={
                "status": "kAugLockState_Locking",
            },
        ),
    )

    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    assert states.get("lock.online_with_doorsense_name").state == LockState.LOCKING

    async_fire_time_changed(menuai, dt_util.utcnow() + datetime.timedelta(seconds=30))
    await menuai.async_block_till_done()
    assert menuai.states.get("lock.online_with_doorsense_name").state == LockState.LOCKING

    pubnub.connected = True
    async_fire_time_changed(menuai, dt_util.utcnow() + datetime.timedelta(seconds=30))
    await menuai.async_block_till_done()
    assert states.get("lock.online_with_doorsense_name").state == LockState.LOCKING

    # Ensure pubnub status is always preserved
    async_fire_time_changed(menuai, dt_util.utcnow() + datetime.timedelta(hours=2))
    await menuai.async_block_till_done()
    assert states.get("lock.online_with_doorsense_name").state == LockState.LOCKING

    pubnub.message(
        pubnub,
        Mock(
            channel=lock_one.pubsub_channel,
            timetoken=(dt_util.utcnow().timestamp() + 2) * 10000000,
            message={
                "status": "kAugLockState_Unlocking",
            },
        ),
    )
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    assert states.get("lock.online_with_doorsense_name").state == LockState.UNLOCKING

    async_fire_time_changed(menuai, dt_util.utcnow() + datetime.timedelta(hours=4))
    await menuai.async_block_till_done()
    assert states.get("lock.online_with_doorsense_name").state == LockState.UNLOCKING

    await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()


async def test_open_throws_menuai_service_not_supported_error(
    menuai: menuai,
) -> None:
    """Test open throws correct error on entity does not support this service error."""
    await async_setup_component(menuai, "menuai", {})
    mocked_lock_detail = await _mock_operative_august_lock_detail(menuai)
    await _create_august_with_devices(menuai, [mocked_lock_detail])
    data = {ATTR_ENTITY_ID: "lock.a6697750d607098bae8d6baa11ef8063_name"}
    with pytest.raises(ServiceNotSupported, match="does not support action"):
        await menuai.services.async_call(LOCK_DOMAIN, SERVICE_OPEN, data, blocking=True)
