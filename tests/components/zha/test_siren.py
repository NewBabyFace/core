"""Test zha siren."""

from datetime import timedelta
from unittest.mock import ANY, call, patch

import pytest
from zha.application.const import (
    WARNING_DEVICE_MODE_EMERGENCY_PANIC,
    WARNING_DEVICE_SOUND_MEDIUM,
)
from zigpy.const import SIG_EP_INPUT, SIG_EP_OUTPUT, SIG_EP_PROFILE, SIG_EP_TYPE
from zigpy.profiles import zha
import zigpy.zcl
from zigpy.zcl.clusters import general, security
import zigpy.zcl.foundation as zcl_f

from menuai.components.siren import (
    ATTR_DURATION,
    ATTR_TONE,
    ATTR_VOLUME_LEVEL,
    DOMAIN as SIREN_DOMAIN,
)
from menuai.components.zha.helpers import (
    ZHADeviceProxy,
    ZHAGatewayProxy,
    get_zha_gateway,
    get_zha_gateway_proxy,
)
from menuai.const import STATE_OFF, STATE_ON, Platform
from menuai.core import menuai
from menuai.util import dt as dt_util

from .common import find_entity_id

from tests.common import async_fire_time_changed


@pytest.fixture(autouse=True)
def siren_platform_only():
    """Only set up the siren and required base platforms to speed up tests."""
    with patch(
        "menuai.components.zha.PLATFORMS",
        (
            Platform.DEVICE_TRACKER,
            Platform.NUMBER,
            Platform.SENSOR,
            Platform.SELECT,
            Platform.SIREN,
        ),
    ):
        yield


async def test_siren(menuai: menuai, setup_zha, zigpy_device_mock) -> None:
    """Test zha siren platform."""

    await setup_zha()
    gateway = get_zha_gateway(menuai)
    gateway_proxy: ZHAGatewayProxy = get_zha_gateway_proxy(menuai)

    zigpy_device = zigpy_device_mock(
        {
            1: {
                SIG_EP_INPUT: [general.Basic.cluster_id, security.IasWd.cluster_id],
                SIG_EP_OUTPUT: [],
                SIG_EP_TYPE: zha.DeviceType.IAS_WARNING_DEVICE,
                SIG_EP_PROFILE: zha.PROFILE_ID,
            }
        }
    )

    gateway.get_or_create_device(zigpy_device)
    await gateway.async_device_initialized(zigpy_device)
    await menuai.async_block_till_done(wait_background_tasks=True)

    zha_device_proxy: ZHADeviceProxy = gateway_proxy.get_device_proxy(zigpy_device.ieee)
    entity_id = find_entity_id(Platform.SIREN, zha_device_proxy, menuai)
    cluster = zigpy_device.endpoints[1].ias_wd
    assert entity_id is not None

    assert menuai.states.get(entity_id).state == STATE_OFF

    # turn on from HA
    with (
        patch(
            "zigpy.device.Device.request",
            return_value=[0x00, zcl_f.Status.SUCCESS],
        ),
        patch(
            "zigpy.zcl.Cluster.request",
            side_effect=zigpy.zcl.Cluster.request,
            autospec=True,
        ),
    ):
        # turn on via UI
        await menuai.services.async_call(
            SIREN_DOMAIN, "turn_on", {"entity_id": entity_id}, blocking=True
        )
        assert cluster.request.mock_calls == [
            call(
                cluster,
                False,
                0,
                ANY,
                50,  # bitmask for default args
                5,  # duration in seconds
                0,
                2,
                manufacturer=None,
                expect_reply=True,
                tsn=None,
            )
        ]

    # test that the state has changed to on
    assert menuai.states.get(entity_id).state == STATE_ON

    # turn off from HA
    with (
        patch(
            "zigpy.device.Device.request",
            return_value=[0x01, zcl_f.Status.SUCCESS],
        ),
        patch(
            "zigpy.zcl.Cluster.request",
            side_effect=zigpy.zcl.Cluster.request,
            autospec=True,
        ),
    ):
        # turn off via UI
        await menuai.services.async_call(
            SIREN_DOMAIN, "turn_off", {"entity_id": entity_id}, blocking=True
        )
        assert cluster.request.mock_calls == [
            call(
                cluster,
                False,
                0,
                ANY,
                2,  # bitmask for default args
                5,  # duration in seconds
                0,
                2,
                manufacturer=None,
                expect_reply=True,
                tsn=None,
            )
        ]

    # test that the state has changed to off
    assert menuai.states.get(entity_id).state == STATE_OFF

    # turn on from HA
    with (
        patch(
            "zigpy.device.Device.request",
            return_value=[0x00, zcl_f.Status.SUCCESS],
        ),
        patch(
            "zigpy.zcl.Cluster.request",
            side_effect=zigpy.zcl.Cluster.request,
            autospec=True,
        ),
    ):
        # turn on via UI
        await menuai.services.async_call(
            SIREN_DOMAIN,
            "turn_on",
            {
                "entity_id": entity_id,
                ATTR_DURATION: 10,
                ATTR_TONE: WARNING_DEVICE_MODE_EMERGENCY_PANIC,
                ATTR_VOLUME_LEVEL: WARNING_DEVICE_SOUND_MEDIUM,
            },
            blocking=True,
        )
        assert cluster.request.mock_calls == [
            call(
                cluster,
                False,
                0,
                ANY,
                97,  # bitmask for passed args
                10,  # duration in seconds
                0,
                2,
                manufacturer=None,
                expect_reply=True,
                tsn=None,
            )
        ]
        # test that the state has changed to on
    assert menuai.states.get(entity_id).state == STATE_ON

    now = dt_util.utcnow() + timedelta(seconds=15)
    async_fire_time_changed(menuai, now)
    await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == STATE_OFF
