"""Test for Template helper."""

from datetime import timedelta
from unittest.mock import patch

import pytest

from menuai import config
from menuai.components.template import DOMAIN
from menuai.const import SERVICE_RELOAD
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import MockConfigEntry, async_fire_time_changed, get_fixture_path


@pytest.mark.parametrize(("count", "domain"), [(1, "sensor")])
@pytest.mark.parametrize(
    "config",
    [
        {
            "sensor": {
                "platform": DOMAIN,
                "sensors": {
                    "state": {
                        "value_template": "{{ states.sensor.test_sensor.state }}"
                    },
                },
            },
            "template": [
                {
                    "trigger": {"platform": "event", "event_type": "event_1"},
                    "sensor": {
                        "name": "top level",
                        "state": "{{ trigger.event.data.source }}",
                    },
                },
                {
                    "sensor": {
                        "name": "top level state",
                        "state": "{{ states.sensor.top_level.state }} + 2",
                    },
                    "binary_sensor": {
                        "name": "top level state",
                        "state": "{{ states.sensor.top_level.state == 'init' }}",
                    },
                },
            ],
        },
    ],
)
@pytest.mark.usefixtures("start_ha")
async def test_reloadable(menuai: menuai) -> None:
    """Test that we can reload."""
    menuai.states.async_set("sensor.test_sensor", "mytest")
    await menuai.async_block_till_done()
    assert menuai.states.get("sensor.top_level_state").state == "unknown + 2"
    assert menuai.states.get("binary_sensor.top_level_state").state == "off"

    menuai.bus.async_fire("event_1", {"source": "init"})
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 5
    assert menuai.states.get("sensor.state").state == "mytest"
    assert menuai.states.get("sensor.top_level").state == "init"
    await menuai.async_block_till_done()
    assert menuai.states.get("sensor.top_level_state").state == "init + 2"
    assert menuai.states.get("binary_sensor.top_level_state").state == "on"

    await async_yaml_patch_helper(menuai, "sensor_configuration.yaml")
    assert len(menuai.states.async_all()) == 4

    menuai.bus.async_fire("event_2", {"source": "reload"})
    await menuai.async_block_till_done()
    assert menuai.states.get("sensor.state") is None
    assert menuai.states.get("sensor.top_level") is None
    assert menuai.states.get("sensor.watching_tv_in_master_bedroom").state == "off"
    assert float(menuai.states.get("sensor.combined_sensor_energy_usage").state) == 0
    assert menuai.states.get("sensor.top_level_2").state == "reload"


@pytest.mark.parametrize(("count", "domain"), [(1, "sensor")])
@pytest.mark.parametrize(
    "config",
    [
        {
            "sensor": {
                "platform": DOMAIN,
                "sensors": {
                    "state": {
                        "value_template": "{{ states.sensor.test_sensor.state }}"
                    },
                },
            },
            "template": {
                "trigger": {"platform": "event", "event_type": "event_1"},
                "sensor": {
                    "name": "top level",
                    "state": "{{ trigger.event.data.source }}",
                },
            },
        },
    ],
)
@pytest.mark.usefixtures("start_ha")
async def test_reloadable_can_remove(menuai: menuai) -> None:
    """Test that we can reload and remove all template sensors."""
    menuai.states.async_set("sensor.test_sensor", "mytest")
    await menuai.async_block_till_done()
    menuai.bus.async_fire("event_1", {"source": "init"})
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 3
    assert menuai.states.get("sensor.state").state == "mytest"
    assert menuai.states.get("sensor.top_level").state == "init"

    await async_yaml_patch_helper(menuai, "empty_configuration.yaml")
    assert len(menuai.states.async_all()) == 1


@pytest.mark.parametrize(("count", "domain"), [(1, "sensor")])
@pytest.mark.parametrize(
    "config",
    [
        {
            "sensor": {
                "platform": DOMAIN,
                "sensors": {
                    "state": {
                        "value_template": "{{ states.sensor.test_sensor.state }}"
                    },
                },
            }
        },
    ],
)
@pytest.mark.usefixtures("start_ha")
async def test_reloadable_stops_on_invalid_config(menuai: menuai) -> None:
    """Test we stop the reload if configuration.yaml is completely broken."""
    menuai.states.async_set("sensor.test_sensor", "mytest")
    await menuai.async_block_till_done()
    assert menuai.states.get("sensor.state").state == "mytest"
    assert len(menuai.states.async_all()) == 2

    await async_yaml_patch_helper(menuai, "configuration.yaml.corrupt")
    assert menuai.states.get("sensor.state").state == "mytest"
    assert len(menuai.states.async_all()) == 2


@pytest.mark.parametrize(("count", "domain"), [(1, "sensor")])
@pytest.mark.parametrize(
    "config",
    [
        {
            "sensor": {
                "platform": DOMAIN,
                "sensors": {
                    "state": {
                        "value_template": "{{ states.sensor.test_sensor.state }}"
                    },
                },
            }
        },
    ],
)
@pytest.mark.usefixtures("start_ha")
async def test_reloadable_handles_partial_valid_config(menuai: menuai) -> None:
    """Test we can still setup valid sensors when configuration.yaml has a broken entry."""
    menuai.states.async_set("sensor.test_sensor", "mytest")
    await menuai.async_block_till_done()
    assert menuai.states.get("sensor.state").state == "mytest"
    assert len(menuai.states.async_all("sensor")) == 2

    await async_yaml_patch_helper(menuai, "broken_configuration.yaml")
    assert len(menuai.states.async_all("sensor")) == 3

    assert menuai.states.get("sensor.state") is None
    assert menuai.states.get("sensor.watching_tv_in_master_bedroom").state == "off"
    assert float(menuai.states.get("sensor.combined_sensor_energy_usage").state) == 0


@pytest.mark.parametrize(("count", "domain"), [(1, "sensor")])
@pytest.mark.parametrize(
    "config",
    [
        {
            "sensor": {
                "platform": DOMAIN,
                "sensors": {
                    "state": {
                        "value_template": "{{ states.sensor.test_sensor.state }}"
                    },
                },
            }
        },
    ],
)
@pytest.mark.usefixtures("start_ha")
async def test_reloadable_multiple_platforms(menuai: menuai) -> None:
    """Test that we can reload."""
    menuai.states.async_set("sensor.test_sensor", "mytest")
    await async_setup_component(
        menuai,
        "binary_sensor",
        {
            "binary_sensor": {
                "platform": DOMAIN,
                "sensors": {
                    "state": {
                        "value_template": "{{ states.sensor.test_sensor.state }}"
                    },
                },
            }
        },
    )
    await menuai.async_block_till_done()
    assert menuai.states.get("sensor.state").state == "mytest"
    assert menuai.states.get("binary_sensor.state").state == "off"
    assert len(menuai.states.async_all()) == 3

    await async_yaml_patch_helper(menuai, "sensor_configuration.yaml")
    assert len(menuai.states.async_all()) == 4
    assert menuai.states.get("sensor.state") is None
    assert menuai.states.get("sensor.watching_tv_in_master_bedroom").state == "off"
    assert float(menuai.states.get("sensor.combined_sensor_energy_usage").state) == 0
    assert menuai.states.get("sensor.top_level_2") is not None


@pytest.mark.parametrize(("count", "domain"), [(1, "sensor")])
@pytest.mark.parametrize(
    "config",
    [
        {
            "sensor": {
                "platform": DOMAIN,
                "sensors": {
                    "state": {"value_template": "{{ 1 }}"},
                },
            }
        },
    ],
)
@pytest.mark.usefixtures("start_ha")
async def test_reload_sensors_that_reference_other_template_sensors(
    menuai: menuai,
) -> None:
    """Test that we can reload sensor that reference other template sensors."""
    await async_yaml_patch_helper(menuai, "ref_configuration.yaml")
    assert len(menuai.states.async_all()) == 3
    await menuai.async_block_till_done()

    next_time = dt_util.utcnow() + timedelta(seconds=1.2)
    with patch(
        "menuai.helpers.ratelimit.time.time", return_value=next_time.timestamp()
    ):
        async_fire_time_changed(menuai, next_time)
        await menuai.async_block_till_done()
    assert menuai.states.get("sensor.test1").state == "3"
    assert menuai.states.get("sensor.test2").state == "1"
    assert menuai.states.get("sensor.test3").state == "2"


async def async_yaml_patch_helper(menuai: menuai, filename: str) -> None:
    """Help update configuration.yaml."""
    yaml_path = get_fixture_path(filename, "template")
    with patch.object(config, "YAML_CONFIG_FILE", yaml_path):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await menuai.async_block_till_done()


@pytest.mark.parametrize(
    (
        "config_entry_options",
        "config_user_input",
    ),
    [
        (
            {
                "name": "My template",
                "state": "{{10}}",
                "template_type": "sensor",
            },
            {
                "state": "{{12}}",
            },
        ),
        (
            {
                "template_type": "binary_sensor",
                "name": "My template",
                "state": "{{1 == 1}}",
            },
            {
                "state": "{{1 == 2}}",
            },
        ),
        (
            {
                "template_type": "image",
                "name": "My template",
                "url": "http://example.com",
            },
            {
                "url": "http://example.com",
            },
        ),
        (
            {
                "template_type": "button",
                "name": "My template",
            },
            {},
        ),
        (
            {
                "template_type": "number",
                "name": "My template",
                "state": "{{ 10 }}",
                "min": 0,
                "max": 100,
                "step": 0.1,
                "set_value": {
                    "action": "input_number.set_value",
                    "target": {"entity_id": "input_number.test"},
                    "data": {"value": "{{ value }}"},
                },
            },
            {
                "state": "{{ 11 }}",
                "min": 0,
                "max": 100,
                "step": 0.1,
                "set_value": {
                    "action": "input_number.set_value",
                    "target": {"entity_id": "input_number.test"},
                    "data": {"value": "{{ value }}"},
                },
            },
        ),
        (
            {
                "template_type": "select",
                "name": "My template",
                "state": "{{ 'on' }}",
                "options": "{{ ['off', 'on', 'auto'] }}",
            },
            {
                "state": "{{ 'on' }}",
                "options": "{{ ['off', 'on', 'auto'] }}",
            },
        ),
        (
            {
                "template_type": "switch",
                "name": "My template",
                "value_template": "{{ true }}",
            },
            {
                "value_template": "{{ true }}",
            },
        ),
    ],
)
async def test_change_device(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    config_entry_options: dict[str, str],
    config_user_input: dict[str, str],
) -> None:
    """Test the link between the device and the config entry.

    Test, for each platform, that the device was linked to the
    config entry and the link was removed when the device is
    changed in the integration options.
    """

    # Configure devices registry
    entry_device1 = MockConfigEntry()
    entry_device1.add_to_menuai(menuai)
    device1 = device_registry.async_get_or_create(
        config_entry_id=entry_device1.entry_id,
        identifiers={("test", "identifier_test1")},
        connections={("mac", "20:31:32:33:34:01")},
    )
    entry_device2 = MockConfigEntry()
    entry_device2.add_to_menuai(menuai)
    device2 = device_registry.async_get_or_create(
        config_entry_id=entry_device1.entry_id,
        identifiers={("test", "identifier_test2")},
        connections={("mac", "20:31:32:33:34:02")},
    )
    await menuai.async_block_till_done()

    device_id1 = device1.id
    assert device_id1 is not None

    device_id2 = device2.id
    assert device_id2 is not None

    # Setup the config entry
    template_config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options=config_entry_options | {"device_id": device_id1},
        title="Template",
    )
    template_config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(template_config_entry.entry_id)
    await menuai.async_block_till_done()

    # Confirm that the config entry has been added to the device 1 registry (current)
    current_device = device_registry.async_get(device_id=device_id1)
    assert template_config_entry.entry_id in current_device.config_entries

    # Change config options to use device 2 and reload the integration
    result = await menuai.config_entries.options.async_init(
        template_config_entry.entry_id
    )
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input=config_user_input | {"device_id": device_id2},
    )
    await menuai.async_block_till_done()

    # Confirm that the config entry has been removed from the device 1 registry
    previous_device = device_registry.async_get(device_id=device_id1)
    assert template_config_entry.entry_id not in previous_device.config_entries

    # Confirm that the config entry has been added to the device 2 registry (current)
    current_device = device_registry.async_get(device_id=device_id2)
    assert template_config_entry.entry_id in current_device.config_entries

    # Change the config options to remove the device and reload the integration
    result = await menuai.config_entries.options.async_init(
        template_config_entry.entry_id
    )
    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        user_input=config_user_input,
    )
    await menuai.async_block_till_done()

    # Confirm that the config entry has been removed from the device 2 registry
    previous_device = device_registry.async_get(device_id=device_id2)
    assert template_config_entry.entry_id not in previous_device.config_entries

    # Confirm that there is no device with the helper config entry
    assert (
        dr.async_entries_for_config_entry(
            device_registry, template_config_entry.entry_id
        )
        == []
    )


async def test_fail_non_numerical_number_settings(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that non numerical number options causes config entry setup to fail.

    Support for non numerical max, min and step was added in HA Core 2024.9.0 and
    removed in HA Core 2024.9.1.
    """

    options = {
        "template_type": "number",
        "name": "My template",
        "state": "{{ 10 }}",
        "min": "{{ 0 }}",
        "max": "{{ 100 }}",
        "step": "{{ 0.1 }}",
        "set_value": {
            "action": "input_number.set_value",
            "target": {"entity_id": "input_number.test"},
            "data": {"value": "{{ value }}"},
        },
    }
    # Setup the config entry
    template_config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options=options,
        title="Template",
    )
    template_config_entry.add_to_menuai(menuai)
    assert not await menuai.config_entries.async_setup(template_config_entry.entry_id)
    assert (
        "The 'My template' number template needs to be reconfigured, "
        "max must be a number, got '{{ 100 }}'" in caplog.text
    )
