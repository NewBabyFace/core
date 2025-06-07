"""The binary_sensor tests for the august platform."""

import datetime
from unittest.mock import Mock

from freezegun.api import FrozenDateTimeFactory
from syrupy.assertion import SnapshotAssertion
from yalexs.pubnub_async import AugustPubNub

from menuai.components.lock import DOMAIN as LOCK_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_LOCK,
    SERVICE_UNLOCK,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.util import dt as dt_util

from .mocks import (
    _create_august_with_devices,
    _mock_activities_from_fixture,
    _mock_doorbell_from_fixture,
    _mock_doorsense_enabled_august_lock_detail,
    _mock_lock_from_fixture,
    _timetoken,
)

from tests.common import async_fire_time_changed


async def test_doorsense(menuai: menuai) -> None:
    """Test creation of a lock with doorsense and bridge."""
    lock_one = await _mock_lock_from_fixture(
        menuai, "get_lock.online_with_doorsense.json"
    )
    await _create_august_with_devices(menuai, [lock_one])
    states = menuai.states

    assert states.get("binary_sensor.online_with_doorsense_name_door").state == STATE_ON

    data = {ATTR_ENTITY_ID: "lock.online_with_doorsense_name"}
    await menuai.services.async_call(LOCK_DOMAIN, SERVICE_UNLOCK, data, blocking=True)

    assert states.get("binary_sensor.online_with_doorsense_name_door").state == STATE_ON

    await menuai.services.async_call(LOCK_DOMAIN, SERVICE_LOCK, data, blocking=True)

    assert (
        states.get("binary_sensor.online_with_doorsense_name_door").state == STATE_OFF
    )


async def test_lock_bridge_offline(menuai: menuai) -> None:
    """Test creation of a lock with doorsense and bridge that goes offline."""
    lock_one = await _mock_lock_from_fixture(
        menuai, "get_lock.online_with_doorsense.json"
    )
    activities = await _mock_activities_from_fixture(
        menuai, "get_activity.bridge_offline.json"
    )
    await _create_august_with_devices(menuai, [lock_one], activities=activities)
    states = menuai.states
    assert (
        states.get("binary_sensor.online_with_doorsense_name_door").state
        == STATE_UNAVAILABLE
    )


async def test_create_doorbell(menuai: menuai) -> None:
    """Test creation of a doorbell."""
    doorbell_one = await _mock_doorbell_from_fixture(menuai, "get_doorbell.json")
    await _create_august_with_devices(menuai, [doorbell_one])
    states = menuai.states

    assert states.get("binary_sensor.k98gidt45gul_name_motion").state == STATE_OFF
    assert (
        states.get("binary_sensor.k98gidt45gul_name_image_capture").state == STATE_OFF
    )
    assert states.get("binary_sensor.k98gidt45gul_name_connectivity").state == STATE_ON
    assert (
        states.get("binary_sensor.k98gidt45gul_name_doorbell_ding").state == STATE_OFF
    )
    assert states.get("binary_sensor.k98gidt45gul_name_motion").state == STATE_OFF
    assert (
        states.get("binary_sensor.k98gidt45gul_name_image_capture").state == STATE_OFF
    )


async def test_create_doorbell_offline(menuai: menuai) -> None:
    """Test creation of a doorbell that is offline."""
    doorbell_one = await _mock_doorbell_from_fixture(menuai, "get_doorbell.offline.json")
    await _create_august_with_devices(menuai, [doorbell_one])
    states = menuai.states

    assert states.get("binary_sensor.tmt100_name_motion").state == STATE_UNAVAILABLE
    assert states.get("binary_sensor.tmt100_name_connectivity").state == STATE_OFF
    assert (
        states.get("binary_sensor.tmt100_name_doorbell_ding").state == STATE_UNAVAILABLE
    )


async def test_create_doorbell_with_motion(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test creation of a doorbell."""
    doorbell_one = await _mock_doorbell_from_fixture(menuai, "get_doorbell.json")
    activities = await _mock_activities_from_fixture(
        menuai, "get_activity.doorbell_motion.json"
    )
    await _create_august_with_devices(menuai, [doorbell_one], activities=activities)
    states = menuai.states

    assert states.get("binary_sensor.k98gidt45gul_name_motion").state == STATE_ON
    assert states.get("binary_sensor.k98gidt45gul_name_connectivity").state == STATE_ON
    assert (
        states.get("binary_sensor.k98gidt45gul_name_doorbell_ding").state == STATE_OFF
    )
    freezer.tick(40)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    assert states.get("binary_sensor.k98gidt45gul_name_motion").state == STATE_OFF


async def test_doorbell_update_via_pubnub(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test creation of a doorbell that can be updated via pubnub."""
    doorbell_one = await _mock_doorbell_from_fixture(menuai, "get_doorbell.json")
    pubnub = AugustPubNub()

    await _create_august_with_devices(menuai, [doorbell_one], pubnub=pubnub)
    assert doorbell_one.pubsub_channel == "7c7a6672-59c8-3333-ffff-dcd98705cccc"
    states = menuai.states
    assert states.get("binary_sensor.k98gidt45gul_name_motion").state == STATE_OFF
    assert (
        states.get("binary_sensor.k98gidt45gul_name_doorbell_ding").state == STATE_OFF
    )

    pubnub.message(
        pubnub,
        Mock(
            channel=doorbell_one.pubsub_channel,
            timetoken=_timetoken(),
            message={
                "status": "imagecapture",
                "data": {
                    "result": {
                        "created_at": "2021-03-16T01:07:08.817Z",
                        "secure_url": (
                            "https://dyu7azbnaoi74.cloudfront.net/zip/images/zip.jpeg"
                        ),
                    },
                },
            },
        ),
    )

    await menuai.async_block_till_done()

    assert states.get("binary_sensor.k98gidt45gul_name_image_capture").state == STATE_ON

    pubnub.message(
        pubnub,
        Mock(
            channel=doorbell_one.pubsub_channel,
            timetoken=_timetoken(),
            message={
                "status": "doorbell_motion_detected",
                "data": {
                    "event": "doorbell_motion_detected",
                    "image": {
                        "height": 640,
                        "width": 480,
                        "format": "jpg",
                        "created_at": "2021-03-16T02:36:26.886Z",
                        "bytes": 14061,
                        "secure_url": (
                            "https://dyu7azbnaoi74.cloudfront.net/images/1f8.jpeg"
                        ),
                        "url": "https://dyu7azbnaoi74.cloudfront.net/images/1f8.jpeg",
                        "etag": "09e839331c4ea59eef28081f2caa0e90",
                    },
                    "doorbellName": "Front Door",
                    "callID": None,
                    "origin": "mars-api",
                    "mutableContent": True,
                },
            },
        ),
    )

    await menuai.async_block_till_done()

    assert states.get("binary_sensor.k98gidt45gul_name_motion").state == STATE_ON

    assert (
        states.get("binary_sensor.k98gidt45gul_name_doorbell_ding").state == STATE_OFF
    )

    freezer.tick(40)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert (
        states.get("binary_sensor.k98gidt45gul_name_image_capture").state == STATE_OFF
    )

    pubnub.message(
        pubnub,
        Mock(
            channel=doorbell_one.pubsub_channel,
            timetoken=_timetoken(),
            message={
                "status": "buttonpush",
            },
        ),
    )
    await menuai.async_block_till_done()

    assert states.get("binary_sensor.k98gidt45gul_name_doorbell_ding").state == STATE_ON
    freezer.tick(40)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert (
        states.get("binary_sensor.k98gidt45gul_name_doorbell_ding").state == STATE_OFF
    )


async def test_doorbell_device_registry(
    menuai: menuai, device_registry: dr.DeviceRegistry, snapshot: SnapshotAssertion
) -> None:
    """Test creation of a lock with doorsense and bridge ands up in the registry."""
    doorbell_one = await _mock_doorbell_from_fixture(menuai, "get_doorbell.offline.json")
    await _create_august_with_devices(menuai, [doorbell_one])

    reg_device = device_registry.async_get_device(identifiers={("august", "tmt100")})
    assert reg_device == snapshot


async def test_door_sense_update_via_pubnub(menuai: menuai) -> None:
    """Test creation of a lock with doorsense and bridge."""
    lock_one = await _mock_doorsense_enabled_august_lock_detail(menuai)
    assert lock_one.pubsub_channel == "pubsub"
    pubnub = AugustPubNub()

    activities = await _mock_activities_from_fixture(menuai, "get_activity.lock.json")
    config_entry = await _create_august_with_devices(
        menuai, [lock_one], activities=activities, pubnub=pubnub
    )
    states = menuai.states

    assert states.get("binary_sensor.online_with_doorsense_name_door").state == STATE_ON

    pubnub.message(
        pubnub,
        Mock(
            channel=lock_one.pubsub_channel,
            timetoken=_timetoken(),
            message={"status": "kAugLockState_Unlocking", "doorState": "closed"},
        ),
    )

    await menuai.async_block_till_done()
    assert (
        states.get("binary_sensor.online_with_doorsense_name_door").state == STATE_OFF
    )

    pubnub.message(
        pubnub,
        Mock(
            channel=lock_one.pubsub_channel,
            timetoken=_timetoken(),
            message={"status": "kAugLockState_Locking", "doorState": "open"},
        ),
    )
    await menuai.async_block_till_done()
    assert states.get("binary_sensor.online_with_doorsense_name_door").state == STATE_ON

    async_fire_time_changed(menuai, dt_util.utcnow() + datetime.timedelta(seconds=30))
    await menuai.async_block_till_done()
    assert states.get("binary_sensor.online_with_doorsense_name_door").state == STATE_ON

    pubnub.connected = True
    async_fire_time_changed(menuai, dt_util.utcnow() + datetime.timedelta(seconds=30))
    await menuai.async_block_till_done()
    assert states.get("binary_sensor.online_with_doorsense_name_door").state == STATE_ON

    # Ensure pubnub status is always preserved
    async_fire_time_changed(menuai, dt_util.utcnow() + datetime.timedelta(hours=2))
    await menuai.async_block_till_done()

    assert states.get("binary_sensor.online_with_doorsense_name_door").state == STATE_ON

    pubnub.message(
        pubnub,
        Mock(
            channel=lock_one.pubsub_channel,
            timetoken=_timetoken(),
            message={"status": "kAugLockState_Unlocking", "doorState": "open"},
        ),
    )
    await menuai.async_block_till_done()
    assert states.get("binary_sensor.online_with_doorsense_name_door").state == STATE_ON

    async_fire_time_changed(menuai, dt_util.utcnow() + datetime.timedelta(hours=4))
    await menuai.async_block_till_done()
    assert states.get("binary_sensor.online_with_doorsense_name_door").state == STATE_ON

    await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()


async def test_create_lock_with_doorbell(menuai: menuai) -> None:
    """Test creation of a lock with a doorbell."""
    lock_one = await _mock_lock_from_fixture(menuai, "lock_with_doorbell.online.json")
    await _create_august_with_devices(menuai, [lock_one])

    states = menuai.states
    assert (
        states.get(
            "binary_sensor.a6697750d607098bae8d6baa11ef8063_name_doorbell_ding"
        ).state
        == STATE_OFF
    )
