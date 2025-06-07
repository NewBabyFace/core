"""The tests for the device tracker component."""

from collections.abc import Generator
from datetime import datetime, timedelta
import json
import logging
import os
from unittest.mock import call, patch

import pytest

from menuai.components import device_tracker, zone
from menuai.components.device_tracker import SourceType, const, legacy
from menuai.const import (
    ATTR_ENTITY_PICTURE,
    ATTR_FRIENDLY_NAME,
    ATTR_GPS_ACCURACY,
    ATTR_ICON,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONF_PLATFORM,
    STATE_HOME,
    STATE_NOT_HOME,
)
from menuai.core import menuai, State, callback
from menuai.exceptions import menuaiError
from menuai.helpers import discovery
from menuai.helpers.json import JSONEncoder
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from . import common
from .common import MockScanner, mock_legacy_device_tracker_setup

from tests.common import (
    RegistryEntryWithDefaults,
    assert_setup_component,
    async_fire_time_changed,
    mock_registry,
    mock_restore_cache,
    patch_yaml_files,
)

TEST_PLATFORM = {device_tracker.DOMAIN: {CONF_PLATFORM: "test"}}

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(name="yaml_devices")
def mock_yaml_devices(menuai: menuai) -> Generator[str]:
    """Get a path for storing yaml devices."""
    yaml_devices = menuai.config.path(legacy.YAML_DEVICES)
    if os.path.isfile(yaml_devices):
        os.remove(yaml_devices)
    yield yaml_devices
    if os.path.isfile(yaml_devices):
        os.remove(yaml_devices)


@pytest.fixture(autouse=True)
def _mock_legacy_device_tracker_setup(
    menuai: menuai, mock_legacy_device_scanner: MockScanner
) -> None:
    """Mock legacy device tracker setup."""
    mock_legacy_device_tracker_setup(menuai, mock_legacy_device_scanner)


async def test_is_on(menuai: menuai) -> None:
    """Test is_on method."""
    entity_id = f"{const.DOMAIN}.test"

    menuai.states.async_set(entity_id, STATE_HOME)

    assert device_tracker.is_on(menuai, entity_id)

    menuai.states.async_set(entity_id, STATE_NOT_HOME)

    assert not device_tracker.is_on(menuai, entity_id)


async def test_reading_broken_yaml_config(menuai: menuai) -> None:
    """Test when known devices contains invalid data."""
    files = {
        "empty.yaml": "",
        "nodict.yaml": "100",
        "badkey.yaml": "@:\n  name: Device",
        "noname.yaml": "my_device:\n",
        "allok.yaml": "My Device:\n  name: Device",
        "oneok.yaml": "My Device!:\n  name: Device\nbad_device:\n  nme: Device",
    }
    args = {"menuai": menuai, "consider_home": timedelta(seconds=60)}
    with patch_yaml_files(files):
        assert await legacy.async_load_config("empty.yaml", **args) == []
        assert await legacy.async_load_config("nodict.yaml", **args) == []
        assert await legacy.async_load_config("noname.yaml", **args) == []
        assert await legacy.async_load_config("badkey.yaml", **args) == []

        res = await legacy.async_load_config("allok.yaml", **args)
        assert len(res) == 1
        assert res[0].name == "Device"
        assert res[0].dev_id == "my_device"

        res = await legacy.async_load_config("oneok.yaml", **args)
        assert len(res) == 1
        assert res[0].name == "Device"
        assert res[0].dev_id == "my_device"


async def test_reading_yaml_config(menuai: menuai, yaml_devices: str) -> None:
    """Test the rendering of the YAML configuration."""
    dev_id = "test"
    device = legacy.Device(
        menuai,
        timedelta(seconds=180),
        True,
        dev_id,
        "AB:CD:EF:GH:IJ",
        "Test name",
        picture="http://test.picture",
        icon="mdi:kettle",
    )
    await menuai.async_add_executor_job(
        legacy.update_config, yaml_devices, dev_id, device
    )
    loaded_config = None
    original_async_load_config = legacy.async_load_config

    async def capture_load_config(*args, **kwargs):
        nonlocal loaded_config
        loaded_config = await original_async_load_config(*args, **kwargs)
        return loaded_config

    with patch(
        "menuai.components.device_tracker.legacy.async_load_config",
        capture_load_config,
    ):
        assert await async_setup_component(menuai, device_tracker.DOMAIN, TEST_PLATFORM)
        await menuai.async_block_till_done()
    config = loaded_config[0]
    assert device.dev_id == config.dev_id
    assert device.track == config.track
    assert device.mac == config.mac
    assert device.config_picture == config.config_picture
    assert device.consider_home == config.consider_home
    assert device.icon == config.icon
    assert f"test.{device_tracker.DOMAIN}" in menuai.config.components


@patch("menuai.components.device_tracker.const.LOGGER.warning")
async def test_duplicate_mac_dev_id(mock_warning, menuai: menuai) -> None:
    """Test adding duplicate MACs or device IDs to DeviceTracker."""
    devices = [
        legacy.Device(
            menuai, True, True, "my_device", "AB:01", "My device", None, None, False
        ),
        legacy.Device(
            menuai, True, True, "your_device", "AB:01", "Your device", None, None, False
        ),
    ]
    legacy.DeviceTracker(menuai, False, True, {}, devices)
    _LOGGER.debug(mock_warning.call_args_list)
    assert mock_warning.call_count == 1, (
        "The only warning call should be duplicates (check DEBUG)"
    )
    args, _ = mock_warning.call_args
    assert "Duplicate device MAC" in args[0], "Duplicate MAC warning expected"

    mock_warning.reset_mock()
    devices = [
        legacy.Device(
            menuai, True, True, "my_device", "AB:01", "My device", None, None, False
        ),
        legacy.Device(
            menuai, True, True, "my_device", None, "Your device", None, None, False
        ),
    ]
    legacy.DeviceTracker(menuai, False, True, {}, devices)

    _LOGGER.debug(mock_warning.call_args_list)
    assert mock_warning.call_count == 1, (
        "The only warning call should be duplicates (check DEBUG)"
    )
    args, _ = mock_warning.call_args
    assert "Duplicate device IDs" in args[0], "Duplicate device IDs warning expected"


async def test_setup_without_yaml_file(menuai: menuai, yaml_devices: str) -> None:
    """Test with no YAML file."""
    with assert_setup_component(1, device_tracker.DOMAIN):
        assert await async_setup_component(menuai, device_tracker.DOMAIN, TEST_PLATFORM)
        await menuai.async_block_till_done()


async def test_gravatar(menuai: menuai) -> None:
    """Test the Gravatar generation."""
    dev_id = "test"
    device = legacy.Device(
        menuai,
        timedelta(seconds=180),
        True,
        dev_id,
        "AB:CD:EF:GH:IJ",
        "Test name",
        gravatar="test@example.com",
    )
    gravatar_url = (
        "https://www.gravatar.com/avatar/"
        "55502f40dc8b7c769880b10874abc9d0.jpg?s=80&d=wavatar"
    )
    assert device.config_picture == gravatar_url


async def test_gravatar_and_picture(menuai: menuai) -> None:
    """Test that Gravatar overrides picture."""
    dev_id = "test"
    device = legacy.Device(
        menuai,
        timedelta(seconds=180),
        True,
        dev_id,
        "AB:CD:EF:GH:IJ",
        "Test name",
        picture="http://test.picture",
        gravatar="test@example.com",
    )
    gravatar_url = (
        "https://www.gravatar.com/avatar/"
        "55502f40dc8b7c769880b10874abc9d0.jpg?s=80&d=wavatar"
    )
    assert device.config_picture == gravatar_url


@patch("menuai.components.device_tracker.legacy.DeviceTracker.see")
@patch("menuai.components.demo.device_tracker.setup_scanner", autospec=True)
async def test_discover_platform(
    mock_demo_setup_scanner, mock_see, menuai: menuai
) -> None:
    """Test discovery of device_tracker demo platform."""
    await async_setup_component(menuai, "menuai", {})
    await async_setup_component(menuai, device_tracker.DOMAIN, {})
    # async_block_till_done is intentionally missing here so we
    # can verify async_load_platform still works without it
    with patch("menuai.components.device_tracker.legacy.update_config"):
        await discovery.async_load_platform(
            menuai, device_tracker.DOMAIN, "demo", {"test_key": "test_val"}, {"bla": {}}
        )
        await menuai.async_block_till_done()
    assert device_tracker.DOMAIN in menuai.config.components
    assert mock_demo_setup_scanner.called
    assert mock_demo_setup_scanner.call_args[0] == (
        menuai,
        {},
        mock_see,
        {"test_key": "test_val"},
    )


async def test_discover_platform_missing_platform(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test discovery of device_tracker missing platform."""
    await async_setup_component(menuai, "menuai", {})
    await async_setup_component(menuai, device_tracker.DOMAIN, {})
    # async_block_till_done is intentionally missing here so we
    # can verify async_load_platform still works without it
    with patch("menuai.components.device_tracker.legacy.update_config"):
        await discovery.async_load_platform(
            menuai,
            device_tracker.DOMAIN,
            "its_not_there",
            {"test_key": "test_val"},
            {"bla": {}},
        )
        await menuai.async_block_till_done()
    assert device_tracker.DOMAIN in menuai.config.components
    assert (
        "Unable to prepare setup for platform 'its_not_there.device_tracker'"
        in caplog.text
    )
    # This test should not generate an unhandled exception


async def test_update_stale(
    menuai: menuai,
    mock_device_tracker_conf: list[legacy.Device],
    mock_legacy_device_scanner: MockScanner,
) -> None:
    """Test stalled update."""
    mock_legacy_device_scanner.reset()
    mock_legacy_device_scanner.come_home("DEV1")

    now = dt_util.utcnow()
    register_time = datetime(now.year + 1, 9, 15, 23, tzinfo=dt_util.UTC)
    scan_time = datetime(now.year + 1, 9, 15, 23, 1, tzinfo=dt_util.UTC)

    with (
        patch(
            "menuai.components.device_tracker.legacy.dt_util.utcnow",
            return_value=register_time,
        ),
        assert_setup_component(1, device_tracker.DOMAIN),
    ):
        assert await async_setup_component(
            menuai,
            device_tracker.DOMAIN,
            {
                device_tracker.DOMAIN: {
                    CONF_PLATFORM: "test",
                    device_tracker.CONF_CONSIDER_HOME: 59,
                }
            },
        )
        await menuai.async_block_till_done()

    assert menuai.states.get("device_tracker.dev1").state == STATE_HOME

    mock_legacy_device_scanner.leave_home("DEV1")

    with patch(
        "menuai.components.device_tracker.legacy.dt_util.utcnow",
        return_value=scan_time,
    ):
        async_fire_time_changed(menuai, scan_time)
        await menuai.async_block_till_done()

    assert menuai.states.get("device_tracker.dev1").state == STATE_NOT_HOME


async def test_entity_attributes(
    menuai: menuai,
    mock_device_tracker_conf: list[legacy.Device],
) -> None:
    """Test the entity attributes."""
    devices = mock_device_tracker_conf
    dev_id = "test_entity"
    entity_id = f"{const.DOMAIN}.{dev_id}"
    friendly_name = "Paulus"
    picture = "http://placehold.it/200x200"
    icon = "mdi:kettle"

    device = legacy.Device(
        menuai,
        timedelta(seconds=180),
        True,
        dev_id,
        None,
        friendly_name,
        picture,
        icon=icon,
    )
    devices.append(device)

    with assert_setup_component(1, device_tracker.DOMAIN):
        assert await async_setup_component(menuai, device_tracker.DOMAIN, TEST_PLATFORM)
        await menuai.async_block_till_done()

    attrs = menuai.states.get(entity_id).attributes

    assert friendly_name == attrs.get(ATTR_FRIENDLY_NAME)
    assert icon == attrs.get(ATTR_ICON)
    assert picture == attrs.get(ATTR_ENTITY_PICTURE)


@patch("menuai.components.device_tracker.legacy.DeviceTracker.async_see")
async def test_see_service(mock_see, menuai: menuai) -> None:
    """Test the see service with a unicode dev_id and NO MAC."""
    with assert_setup_component(1, device_tracker.DOMAIN):
        assert await async_setup_component(menuai, device_tracker.DOMAIN, TEST_PLATFORM)
        await menuai.async_block_till_done()
    params = {
        "dev_id": "some_device",
        "host_name": "example.com",
        "location_name": "Work",
        "gps": [0.3, 0.8],
        "attributes": {"test": "test"},
    }
    common.async_see(menuai, **params)
    await menuai.async_block_till_done()
    assert mock_see.call_count == 1
    assert mock_see.call_count == 1
    assert mock_see.call_args == call(**params)

    mock_see.reset_mock()
    params["dev_id"] += chr(233)  # e' acute accent from icloud

    common.async_see(menuai, **params)
    await menuai.async_block_till_done()
    assert mock_see.call_count == 1
    assert mock_see.call_count == 1
    assert mock_see.call_args == call(**params)


async def test_see_service_guard_config_entry(
    menuai: menuai,
    mock_device_tracker_conf: list[legacy.Device],
) -> None:
    """Test the guard if the device is registered in the entity registry."""
    dev_id = "test"
    entity_id = f"{const.DOMAIN}.{dev_id}"
    mock_registry(
        menuai,
        {
            entity_id: RegistryEntryWithDefaults(
                entity_id=entity_id, unique_id=1, platform=const.DOMAIN
            )
        },
    )
    devices = mock_device_tracker_conf
    assert await async_setup_component(menuai, device_tracker.DOMAIN, TEST_PLATFORM)
    await menuai.async_block_till_done()
    params = {"dev_id": dev_id, "gps": [0.3, 0.8]}

    common.async_see(menuai, **params)
    await menuai.async_block_till_done()

    assert not devices


async def test_new_device_event_fired(
    menuai: menuai,
    mock_device_tracker_conf: list[legacy.Device],
) -> None:
    """Test that the device tracker will fire an event."""
    with assert_setup_component(1, device_tracker.DOMAIN):
        assert await async_setup_component(menuai, device_tracker.DOMAIN, TEST_PLATFORM)
        await menuai.async_block_till_done()
    test_events = []

    @callback
    def listener(event):
        """Record that our event got called."""
        test_events.append(event)

    menuai.bus.async_listen("device_tracker_new_device", listener)

    common.async_see(menuai, "mac_1", host_name="hello")
    common.async_see(menuai, "mac_1", host_name="hello")

    await menuai.async_block_till_done()

    assert len(test_events) == 1

    # Assert we can serialize the event
    json.dumps(test_events[0].as_dict(), cls=JSONEncoder)

    assert test_events[0].data == {
        "entity_id": "device_tracker.hello",
        "host_name": "hello",
        "mac": "MAC_1",
    }


async def test_duplicate_yaml_keys(
    menuai: menuai,
    mock_device_tracker_conf: list[legacy.Device],
) -> None:
    """Test that the device tracker will not generate invalid YAML."""
    devices = mock_device_tracker_conf
    with assert_setup_component(1, device_tracker.DOMAIN):
        assert await async_setup_component(menuai, device_tracker.DOMAIN, TEST_PLATFORM)
        await menuai.async_block_till_done()

    common.async_see(menuai, "mac_1", host_name="hello")
    common.async_see(menuai, "mac_2", host_name="hello")

    await menuai.async_block_till_done()

    assert len(devices) == 2
    assert devices[0].dev_id != devices[1].dev_id


async def test_invalid_dev_id(
    menuai: menuai,
    mock_device_tracker_conf: list[legacy.Device],
) -> None:
    """Test that the device tracker will not allow invalid dev ids."""
    devices = mock_device_tracker_conf
    with assert_setup_component(1, device_tracker.DOMAIN):
        assert await async_setup_component(menuai, device_tracker.DOMAIN, TEST_PLATFORM)
        await menuai.async_block_till_done()

    common.async_see(menuai, dev_id="hello-world")
    await menuai.async_block_till_done()

    assert not devices


async def test_see_state(menuai: menuai, yaml_devices: str) -> None:
    """Test device tracker see records state correctly."""
    assert await async_setup_component(menuai, device_tracker.DOMAIN, TEST_PLATFORM)
    await menuai.async_block_till_done()

    params = {
        "mac": "AA:BB:CC:DD:EE:FF",
        "dev_id": "some_device",
        "host_name": "example.com",
        "location_name": "Work",
        "gps": [0.3, 0.8],
        "gps_accuracy": 1,
        "battery": 100,
        "attributes": {"test": "test", "number": 1},
    }

    common.async_see(menuai, **params)
    await menuai.async_block_till_done()

    config = await legacy.async_load_config(yaml_devices, menuai, timedelta(seconds=0))
    assert len(config) == 1

    state = menuai.states.get("device_tracker.example_com")
    attrs = state.attributes
    assert state.state == "Work"
    assert state.object_id == "example_com"
    assert state.name == "example.com"
    assert attrs["friendly_name"] == "example.com"
    assert attrs["battery"] == 100
    assert attrs["latitude"] == 0.3
    assert attrs["longitude"] == 0.8
    assert attrs["test"] == "test"
    assert attrs["gps_accuracy"] == 1
    assert attrs["source_type"] == "gps"
    assert attrs["number"] == 1


async def test_see_passive_zone_state(
    menuai: menuai,
    mock_device_tracker_conf: list[legacy.Device],
    mock_legacy_device_scanner: MockScanner,
) -> None:
    """Test that the device tracker sets gps for passive trackers."""
    now = dt_util.utcnow()

    register_time = datetime(now.year + 1, 9, 15, 23, tzinfo=dt_util.UTC)
    scan_time = datetime(now.year + 1, 9, 15, 23, 1, tzinfo=dt_util.UTC)

    with assert_setup_component(1, zone.DOMAIN):
        zone_info = {
            "name": "Home",
            "latitude": 1,
            "longitude": 2,
            "radius": 250,
            "passive": False,
        }

        await async_setup_component(menuai, zone.DOMAIN, {"zone": zone_info})
        await menuai.async_block_till_done()

    mock_legacy_device_scanner.reset()
    mock_legacy_device_scanner.come_home("dev1")

    with (
        patch(
            "menuai.components.device_tracker.legacy.dt_util.utcnow",
            return_value=register_time,
        ),
        assert_setup_component(1, device_tracker.DOMAIN),
    ):
        assert await async_setup_component(
            menuai,
            device_tracker.DOMAIN,
            {
                device_tracker.DOMAIN: {
                    CONF_PLATFORM: "test",
                    device_tracker.CONF_CONSIDER_HOME: 59,
                }
            },
        )
        await menuai.async_block_till_done()

    state = menuai.states.get("device_tracker.dev1")
    attrs = state.attributes
    assert state.state == STATE_HOME
    assert state.object_id == "dev1"
    assert state.name == "dev1"
    assert attrs.get("friendly_name") == "dev1"
    assert attrs.get("latitude") == 1
    assert attrs.get("longitude") == 2
    assert attrs.get("gps_accuracy") == 0
    assert attrs.get("source_type") == SourceType.ROUTER

    mock_legacy_device_scanner.leave_home("dev1")

    with patch(
        "menuai.components.device_tracker.legacy.dt_util.utcnow",
        return_value=scan_time,
    ):
        async_fire_time_changed(menuai, scan_time)
        await menuai.async_block_till_done()

    state = menuai.states.get("device_tracker.dev1")
    attrs = state.attributes
    assert state.state == STATE_NOT_HOME
    assert state.object_id == "dev1"
    assert state.name == "dev1"
    assert attrs.get("friendly_name") == "dev1"
    assert attrs.get("latitude") is None
    assert attrs.get("longitude") is None
    assert attrs.get("gps_accuracy") is None
    assert attrs.get("source_type") == SourceType.ROUTER


@patch("menuai.components.device_tracker.const.LOGGER.warning")
async def test_see_failures(
    mock_warning, menuai: menuai, mock_device_tracker_conf: list[legacy.Device]
) -> None:
    """Test that the device tracker see failures."""
    devices = mock_device_tracker_conf
    tracker = legacy.DeviceTracker(menuai, timedelta(seconds=60), 0, {}, [])

    # MAC is not a string (but added)
    await tracker.async_see(mac=567, host_name="Number MAC")

    # No device id or MAC(not added)
    with pytest.raises(menuaiError):
        await tracker.async_see()
    assert mock_warning.call_count == 0

    # Ignore gps on invalid GPS (both added & warnings)
    await tracker.async_see(mac="mac_1_bad_gps", gps=1)
    await tracker.async_see(mac="mac_2_bad_gps", gps=[1])
    await tracker.async_see(mac="mac_3_bad_gps", gps="gps")
    await menuai.async_block_till_done()

    assert mock_warning.call_count == 3
    assert len(devices) == 4


async def test_async_added_to_menuai(menuai: menuai) -> None:
    """Test restoring state."""
    attr = {
        ATTR_LONGITUDE: 18,
        ATTR_LATITUDE: -33,
        const.ATTR_SOURCE_TYPE: "gps",
        ATTR_GPS_ACCURACY: 2,
        const.ATTR_BATTERY: 100,
    }
    mock_restore_cache(menuai, [State("device_tracker.jk", "home", attr)])

    path = menuai.config.path(legacy.YAML_DEVICES)

    files = {path: "jk:\n  name: JK Phone\n  track: True"}
    with patch_yaml_files(files):
        assert await async_setup_component(menuai, device_tracker.DOMAIN, {})
        await menuai.async_block_till_done()

    state = menuai.states.get("device_tracker.jk")
    assert state
    assert state.state == "home"

    for key, val in attr.items():
        atr = state.attributes.get(key)
        assert atr == val, f"{key}={atr} expected: {val}"


async def test_bad_platform(menuai: menuai) -> None:
    """Test bad platform."""
    config = {"device_tracker": [{"platform": "bad_platform"}]}
    with assert_setup_component(0, device_tracker.DOMAIN):
        assert await async_setup_component(menuai, device_tracker.DOMAIN, config)
        await menuai.async_block_till_done()

    assert f"bad_platform.{device_tracker.DOMAIN}" not in menuai.config.components


async def test_adding_unknown_device_to_config(
    mock_device_tracker_conf: list[legacy.Device],
    menuai: menuai,
    mock_legacy_device_scanner: MockScanner,
) -> None:
    """Test the adding of unknown devices to configuration file."""
    mock_legacy_device_scanner.reset()
    mock_legacy_device_scanner.come_home("DEV1")

    await async_setup_component(
        menuai, device_tracker.DOMAIN, {device_tracker.DOMAIN: {CONF_PLATFORM: "test"}}
    )

    await menuai.async_block_till_done()

    assert len(mock_device_tracker_conf) == 1
    device = mock_device_tracker_conf[0]
    assert device.dev_id == "dev1"
    assert device.track


async def test_picture_and_icon_on_see_discovery(
    mock_device_tracker_conf: list[legacy.Device], menuai: menuai
) -> None:
    """Test that picture and icon are set in initial see."""
    tracker = legacy.DeviceTracker(menuai, timedelta(seconds=60), False, {}, [])
    await tracker.async_see(dev_id=11, picture="pic_url", icon="mdi:icon")
    await menuai.async_block_till_done()
    assert len(mock_device_tracker_conf) == 1
    assert mock_device_tracker_conf[0].icon == "mdi:icon"
    assert mock_device_tracker_conf[0].entity_picture == "pic_url"


async def test_backward_compatibility_for_track_new(
    mock_device_tracker_conf: list[legacy.Device], menuai: menuai
) -> None:
    """Test backward compatibility for track new."""
    tracker = legacy.DeviceTracker(
        menuai, timedelta(seconds=60), False, {device_tracker.CONF_TRACK_NEW: True}, []
    )
    await tracker.async_see(dev_id=13)
    await menuai.async_block_till_done()
    assert len(mock_device_tracker_conf) == 1
    assert mock_device_tracker_conf[0].track is False


async def test_old_style_track_new_is_skipped(
    mock_device_tracker_conf: list[legacy.Device], menuai: menuai
) -> None:
    """Test old style config is skipped."""
    tracker = legacy.DeviceTracker(
        menuai, timedelta(seconds=60), None, {device_tracker.CONF_TRACK_NEW: False}, []
    )
    await tracker.async_see(dev_id=14)
    await menuai.async_block_till_done()
    assert len(mock_device_tracker_conf) == 1
    assert mock_device_tracker_conf[0].track is False


def test_see_schema_allowing_ios_calls() -> None:
    """Test SEE service schema allows extra keys.

    Temp work around because the iOS app sends incorrect data.
    """
    device_tracker.SERVICE_SEE_PAYLOAD_SCHEMA(
        {
            "dev_id": "Test",
            "battery": 35,
            "battery_status": "Not Charging",
            "gps": [10.0, 10.0],
            "gps_accuracy": 300,
            "hostname": "beer",
        }
    )
