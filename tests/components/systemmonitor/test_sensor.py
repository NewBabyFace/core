"""Test System Monitor sensor."""

from datetime import timedelta
import socket
from unittest.mock import Mock, patch

from freezegun.api import FrozenDateTimeFactory
from psutil._common import sdiskpart, sdiskusage, shwtemp, snetio, snicaddr
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.components.systemmonitor.const import DOMAIN
from menuai.components.systemmonitor.coordinator import VirtualMemory
from menuai.components.systemmonitor.sensor import get_cpu_icon
from menuai.config_entries import ConfigEntry
from menuai.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor(
    menuai: menuai,
    mock_psutil: Mock,
    mock_os: Mock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the sensor."""
    mock_config_entry = MockConfigEntry(
        title="System Monitor",
        domain=DOMAIN,
        data={},
        options={
            "binary_sensor": {"process": ["python3", "pip"]},
            "resources": [
                "disk_use_percent_/",
                "disk_use_percent_/home/notexist/",
                "memory_free_",
                "network_out_eth0",
                "process_python3",
            ],
        },
    )
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    memory_sensor = menuai.states.get("sensor.system_monitor_memory_free")
    assert memory_sensor is not None
    assert memory_sensor.state == "40.0"
    assert memory_sensor.attributes == {
        "state_class": "measurement",
        "unit_of_measurement": "MiB",
        "device_class": "data_size",
        "friendly_name": "System Monitor Memory free",
    }

    for entity in er.async_entries_for_config_entry(
        entity_registry, mock_config_entry.entry_id
    ):
        if entity.domain == SENSOR_DOMAIN:
            state = menuai.states.get(entity.entity_id)
            assert state.state == snapshot(name=f"{state.name} - state")
            assert state.attributes == snapshot(name=f"{state.name} - attributes")


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_process_sensor_not_loaded(
    menuai: menuai,
    mock_psutil: Mock,
    mock_os: Mock,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the process sensor is not loaded once migrated."""
    mock_config_entry = MockConfigEntry(
        title="System Monitor",
        domain=DOMAIN,
        data={},
        options={
            "binary_sensor": {"process": ["python3", "pip"]},
            "resources": [
                "disk_use_percent_/",
                "disk_use_percent_/home/notexist/",
                "memory_free_",
                "network_out_eth0",
                "process_python3",
            ],
        },
    )
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    process_sensor = menuai.states.get("sensor.system_monitor_process_python3")
    assert process_sensor is None


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor_not_loading_veth_networks(
    menuai: menuai,
    mock_added_config_entry: ConfigEntry,
) -> None:
    """Test the sensor."""
    network_sensor_1 = menuai.states.get("sensor.system_monitor_network_out_eth1")
    network_sensor_2 = menuai.states.get(
        "sensor.sensor.system_monitor_network_out_vethxyzxyz"
    )
    assert network_sensor_1 is not None
    assert network_sensor_1.state == "200.0"
    assert network_sensor_2 is None


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor_icon(
    menuai: menuai,
    mock_psutil: Mock,
    mock_os: Mock,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the sensor icon for 32bit/64bit system."""

    get_cpu_icon.cache_clear()
    with patch("sys.maxsize", 2**32):
        assert get_cpu_icon() == "mdi:cpu-32-bit"
    get_cpu_icon.cache_clear()
    with patch("sys.maxsize", 2**64):
        assert get_cpu_icon() == "mdi:cpu-64-bit"


async def test_sensor_updating(
    menuai: menuai,
    mock_psutil: Mock,
    mock_os: Mock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the sensor."""
    mock_config_entry = MockConfigEntry(
        title="System Monitor",
        domain=DOMAIN,
        data={},
        options={
            "binary_sensor": {"process": ["python3", "pip"]},
            "resources": [
                "disk_use_percent_/",
                "disk_use_percent_/home/notexist/",
                "memory_free_",
                "network_out_eth0",
                "process_python3",
            ],
        },
    )
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    memory_sensor = menuai.states.get("sensor.system_monitor_memory_free")
    assert memory_sensor is not None
    assert memory_sensor.state == "40.0"

    mock_psutil.virtual_memory.side_effect = Exception("Failed to update")
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    memory_sensor = menuai.states.get("sensor.system_monitor_memory_free")
    assert memory_sensor is not None
    assert memory_sensor.state == STATE_UNAVAILABLE

    mock_psutil.virtual_memory.side_effect = None
    mock_psutil.virtual_memory.return_value = VirtualMemory(
        100 * 1024**2,
        25 * 1024**2,
        25.0,
        60 * 1024**2,
        30 * 1024**2,
    )
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    memory_sensor = menuai.states.get("sensor.system_monitor_memory_free")
    assert memory_sensor is not None
    assert memory_sensor.state == "25.0"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor_network_sensors(
    freezer: FrozenDateTimeFactory,
    menuai: menuai,
    mock_added_config_entry: ConfigEntry,
    mock_psutil: Mock,
) -> None:
    """Test process not exist failure."""
    network_out_sensor = menuai.states.get("sensor.system_monitor_network_out_eth1")
    packets_out_sensor = menuai.states.get("sensor.system_monitor_packets_out_eth1")
    throughput_network_out_sensor = menuai.states.get(
        "sensor.system_monitor_network_throughput_out_eth1"
    )

    assert network_out_sensor is not None
    assert packets_out_sensor is not None
    assert throughput_network_out_sensor is not None
    assert network_out_sensor.state == "200.0"
    assert packets_out_sensor.state == "150"
    assert throughput_network_out_sensor.state == STATE_UNKNOWN

    mock_psutil.net_io_counters.return_value = {
        "eth0": snetio(200 * 1024**2, 200 * 1024**2, 100, 100, 0, 0, 0, 0),
        "eth1": snetio(400 * 1024**2, 400 * 1024**2, 300, 300, 0, 0, 0, 0),
    }

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    network_out_sensor = menuai.states.get("sensor.system_monitor_network_out_eth1")
    packets_out_sensor = menuai.states.get("sensor.system_monitor_packets_out_eth1")
    throughput_network_out_sensor = menuai.states.get(
        "sensor.system_monitor_network_throughput_out_eth1"
    )

    assert network_out_sensor is not None
    assert packets_out_sensor is not None
    assert throughput_network_out_sensor is not None
    assert network_out_sensor.state == "400.0"
    assert packets_out_sensor.state == "300"
    assert float(throughput_network_out_sensor.state) == pytest.approx(3.493, rel=0.1)

    mock_psutil.net_io_counters.return_value = {
        "eth0": snetio(100 * 1024**2, 100 * 1024**2, 50, 50, 0, 0, 0, 0),
    }
    mock_psutil.net_if_addrs.return_value = {
        "eth0": [
            snicaddr(
                socket.AF_INET,
                "192.168.1.1",
                "255.255.255.0",
                "255.255.255.255",
                None,
            )
        ],
    }

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    network_out_sensor = menuai.states.get("sensor.system_monitor_network_out_eth1")
    packets_out_sensor = menuai.states.get("sensor.system_monitor_packets_out_eth1")
    throughput_network_out_sensor = menuai.states.get(
        "sensor.system_monitor_network_throughput_out_eth1"
    )

    assert network_out_sensor is not None
    assert packets_out_sensor is not None
    assert throughput_network_out_sensor is not None
    assert network_out_sensor.state == STATE_UNKNOWN
    assert packets_out_sensor.state == STATE_UNKNOWN
    assert throughput_network_out_sensor.state == STATE_UNKNOWN


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_missing_cpu_temperature(
    menuai: menuai,
    mock_psutil: Mock,
    mock_os: Mock,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the sensor when temperature missing."""
    mock_psutil.sensors_temperatures.return_value = {
        "not_exist": [shwtemp("not_exist", 50.0, 60.0, 70.0)]
    }
    mock_psutil.sensors_temperatures.return_value = {
        "not_exist": [shwtemp("not_exist", 50.0, 60.0, 70.0)]
    }
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    # assert "Cannot read CPU / processor temperature information" in caplog.text
    temp_sensor = menuai.states.get("sensor.system_monitor_processor_temperature")
    assert temp_sensor is None


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_processor_temperature(
    menuai: menuai,
    mock_psutil: Mock,
    mock_os: Mock,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the disk failures."""

    with patch("sys.platform", "linux"):
        mock_psutil.sensors_temperatures.return_value = {
            "cpu0-thermal": [shwtemp("cpu0-thermal", 50.0, 60.0, 70.0)]
        }
        mock_psutil.sensors_temperatures.side_effect = None
        mock_config_entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()
        temp_entity = menuai.states.get("sensor.system_monitor_processor_temperature")
        assert temp_entity.state == "50.0"
        assert await menuai.config_entries.async_unload(mock_config_entry.entry_id)
        await menuai.async_block_till_done()

    with patch("sys.platform", "nt"):
        mock_psutil.sensors_temperatures.return_value = None
        mock_psutil.sensors_temperatures.side_effect = AttributeError(
            "sensors_temperatures not exist"
        )
        mock_config_entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()
        temp_entity = menuai.states.get("sensor.system_monitor_processor_temperature")
        assert temp_entity.state == STATE_UNAVAILABLE
        assert await menuai.config_entries.async_unload(mock_config_entry.entry_id)
        await menuai.async_block_till_done()

    with patch("sys.platform", "darwin"):
        mock_psutil.sensors_temperatures.return_value = {
            "cpu0-thermal": [shwtemp("cpu0-thermal", 50.0, 60.0, 70.0)]
        }
        mock_psutil.sensors_temperatures.side_effect = None
        mock_config_entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(mock_config_entry.entry_id)
        await menuai.async_block_till_done()
        temp_entity = menuai.states.get("sensor.system_monitor_processor_temperature")
        assert temp_entity.state == "50.0"
        assert await menuai.config_entries.async_unload(mock_config_entry.entry_id)
        await menuai.async_block_till_done()


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_exception_handling_disk_sensor(
    menuai: menuai,
    mock_psutil: Mock,
    mock_added_config_entry: ConfigEntry,
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the sensor."""
    disk_sensor = menuai.states.get("sensor.system_monitor_disk_free")
    assert disk_sensor is not None
    assert disk_sensor.state == "200.0"  # GiB

    mock_psutil.disk_usage.return_value = None
    mock_psutil.disk_usage.side_effect = OSError("Could not update /")

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert "OS error for /" in caplog.text

    disk_sensor = menuai.states.get("sensor.system_monitor_disk_free")
    assert disk_sensor is not None
    assert disk_sensor.state == STATE_UNAVAILABLE

    mock_psutil.disk_usage.return_value = None
    mock_psutil.disk_usage.side_effect = PermissionError("No access to /")

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert "OS error for /" in caplog.text

    disk_sensor = menuai.states.get("sensor.system_monitor_disk_free")
    assert disk_sensor is not None
    assert disk_sensor.state == STATE_UNAVAILABLE

    mock_psutil.disk_usage.return_value = sdiskusage(
        500 * 1024**3, 350 * 1024**3, 150 * 1024**3, 70.0
    )
    mock_psutil.disk_usage.side_effect = None

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    disk_sensor = menuai.states.get("sensor.system_monitor_disk_free")
    assert disk_sensor is not None
    assert disk_sensor.state == "150.0"
    assert disk_sensor.attributes["unit_of_measurement"] == "GiB"

    disk_sensor = menuai.states.get("sensor.system_monitor_disk_usage")
    assert disk_sensor is not None
    assert disk_sensor.state == "70.0"
    assert disk_sensor.attributes["unit_of_measurement"] == "%"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_cpu_percentage_is_zero_returns_unknown(
    menuai: menuai,
    mock_psutil: Mock,
    mock_added_config_entry: ConfigEntry,
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the sensor."""
    cpu_sensor = menuai.states.get("sensor.system_monitor_processor_use")
    assert cpu_sensor is not None
    assert cpu_sensor.state == "10"

    mock_psutil.cpu_percent.return_value = 0.0

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    cpu_sensor = menuai.states.get("sensor.system_monitor_processor_use")
    assert cpu_sensor is not None
    assert cpu_sensor.state == STATE_UNKNOWN

    mock_psutil.cpu_percent.return_value = 15.0

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    cpu_sensor = menuai.states.get("sensor.system_monitor_processor_use")
    assert cpu_sensor is not None
    assert cpu_sensor.state == "15"


async def test_remove_obsolete_entities(
    menuai: menuai,
    mock_psutil: Mock,
    mock_added_config_entry: ConfigEntry,
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test we remove sensors that are not actual and disabled."""
    cpu_sensor = menuai.states.get("sensor.system_monitor_processor_use")
    assert cpu_sensor is None
    cpu_sensor_entity = entity_registry.async_get("sensor.system_monitor_processor_use")
    assert cpu_sensor_entity.disabled is True

    assert (
        len(
            entity_registry.entities.get_entries_for_config_entry_id(
                mock_added_config_entry.entry_id
            )
        )
        == 37
    )

    entity_registry.async_update_entity(
        "sensor.system_monitor_processor_use", disabled_by=None
    )
    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done(wait_background_tasks=True)

    # Fake an entity which should be removed as not supported and disabled
    entity_registry.async_get_or_create(
        SENSOR_DOMAIN,
        DOMAIN,
        "network_out_veth12345",
        disabled_by=er.RegistryEntryDisabler.INTEGRATION,
        config_entry=mock_added_config_entry,
        has_entity_name=True,
        device_id=cpu_sensor_entity.device_id,
        translation_key="network_out",
    )
    # Fake an entity which should not be removed as not supported but not disabled
    entity_registry.async_get_or_create(
        SENSOR_DOMAIN,
        DOMAIN,
        "network_out_veth54321",
        disabled_by=None,
        config_entry=mock_added_config_entry,
        has_entity_name=True,
        device_id=cpu_sensor_entity.device_id,
        translation_key="network_out",
    )
    await menuai.config_entries.async_reload(mock_added_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert (
        len(
            entity_registry.entities.get_entries_for_config_entry_id(
                mock_added_config_entry.entry_id
            )
        )
        == 38
    )

    assert (
        entity_registry.async_get("sensor.systemmonitor_network_out_veth12345") is None
    )
    assert (
        entity_registry.async_get("sensor.systemmonitor_network_out_veth54321")
        is not None
    )


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_no_duplicate_disk_entities(
    menuai: menuai,
    mock_psutil: Mock,
    mock_os: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the sensor."""
    mock_psutil.disk_usage.return_value = sdiskusage(
        500 * 1024**3, 300 * 1024**3, 200 * 1024**3, 60.0
    )
    mock_psutil.disk_partitions.return_value = [
        sdiskpart("test", "/", "ext4", ""),
        sdiskpart("test2", "/media/share", "ext4", ""),
        sdiskpart("test3", "/incorrect", "", ""),
        sdiskpart("test4", "/media/frigate", "ext4", ""),
        sdiskpart("test4", "/media/FRIGATE", "ext4", ""),
        sdiskpart("hosts", "/etc/hosts", "bind", ""),
        sdiskpart("proc", "/proc/run", "proc", ""),
    ]

    mock_config_entry = MockConfigEntry(
        title="System Monitor",
        domain=DOMAIN,
        data={},
        options={
            "binary_sensor": {"process": ["python3", "pip"]},
        },
    )
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    disk_sensor = menuai.states.get("sensor.system_monitor_disk_usage_media_frigate")
    assert disk_sensor is not None
    assert disk_sensor.state == "60.0"

    assert "Platform systemmonitor does not generate unique IDs." not in caplog.text
