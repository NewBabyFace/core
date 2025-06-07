"""The tests for the Template select platform."""

from typing import Any

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai import setup
from menuai.components import select, template
from menuai.components.input_select import (
    ATTR_OPTION as INPUT_SELECT_ATTR_OPTION,
    ATTR_OPTIONS as INPUT_SELECT_ATTR_OPTIONS,
    DOMAIN as INPUT_SELECT_DOMAIN,
    SERVICE_SELECT_OPTION as INPUT_SELECT_SERVICE_SELECT_OPTION,
    SERVICE_SET_OPTIONS,
)
from menuai.components.select import (
    ATTR_OPTION as SELECT_ATTR_OPTION,
    ATTR_OPTIONS as SELECT_ATTR_OPTIONS,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION as SELECT_SERVICE_SELECT_OPTION,
)
from menuai.components.template import DOMAIN
from menuai.const import ATTR_ENTITY_ID, ATTR_ICON, CONF_ENTITY_ID, STATE_UNKNOWN
from menuai.core import Context, menuai, ServiceCall
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.setup import async_setup_component

from .conftest import ConfigurationStyle

from tests.common import MockConfigEntry, assert_setup_component, async_capture_events

_TEST_OBJECT_ID = "template_select"
_TEST_SELECT = f"select.{_TEST_OBJECT_ID}"
# Represent for select's current_option
_OPTION_INPUT_SELECT = "input_select.option"


async def async_setup_modern_format(
    menuai: menuai, count: int, select_config: dict[str, Any]
) -> None:
    """Do setup of select integration via new format."""
    config = {"template": {"select": select_config}}

    with assert_setup_component(count, template.DOMAIN):
        assert await async_setup_component(
            menuai,
            template.DOMAIN,
            config,
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()


@pytest.fixture
async def setup_select(
    menuai: menuai,
    count: int,
    style: ConfigurationStyle,
    select_config: dict[str, Any],
) -> None:
    """Do setup of select integration."""
    if style == ConfigurationStyle.MODERN:
        await async_setup_modern_format(
            menuai, count, {"name": _TEST_OBJECT_ID, **select_config}
        )


async def test_setup_config_entry(
    menuai: menuai,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the config flow."""

    template_config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "name": "My template",
            "template_type": "select",
            "state": "{{ 'on' }}",
            "options": "{{ ['off', 'on', 'auto'] }}",
        },
        title="My template",
    )
    template_config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(template_config_entry.entry_id)
    await menuai.async_block_till_done()

    state = menuai.states.get("select.my_template")
    assert state is not None
    assert state == snapshot


async def test_missing_optional_config(menuai: menuai) -> None:
    """Test: missing optional template is ok."""
    with assert_setup_component(1, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {
                "template": {
                    "select": {
                        "state": "{{ 'a' }}",
                        "select_option": {"service": "script.select_option"},
                        "options": "{{ ['a', 'b'] }}",
                    }
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    _verify(menuai, "a", ["a", "b"])


async def test_multiple_configs(menuai: menuai) -> None:
    """Test: multiple select entities get created."""
    with assert_setup_component(1, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {
                "template": {
                    "select": [
                        {
                            "state": "{{ 'a' }}",
                            "select_option": {"service": "script.select_option"},
                            "options": "{{ ['a', 'b'] }}",
                        },
                        {
                            "state": "{{ 'a' }}",
                            "select_option": {"service": "script.select_option"},
                            "options": "{{ ['a', 'b'] }}",
                        },
                    ]
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    _verify(menuai, "a", ["a", "b"])
    _verify(menuai, "a", ["a", "b"], f"{_TEST_SELECT}_2")


async def test_missing_required_keys(menuai: menuai) -> None:
    """Test: missing required fields will fail."""
    with assert_setup_component(0, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {
                "template": {
                    "select": {
                        "select_option": {"service": "script.select_option"},
                        "options": "{{ ['a', 'b'] }}",
                    }
                }
            },
        )

    with assert_setup_component(0, "select"):
        assert await setup.async_setup_component(
            menuai,
            "select",
            {
                "template": {
                    "select": {
                        "state": "{{ 'a' }}",
                        "select_option": {"service": "script.select_option"},
                    }
                }
            },
        )

    with assert_setup_component(0, "select"):
        assert await setup.async_setup_component(
            menuai,
            "select",
            {
                "template": {
                    "select": {
                        "state": "{{ 'a' }}",
                        "options": "{{ ['a', 'b'] }}",
                    }
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    assert menuai.states.async_all("select") == []


async def test_templates_with_entities(
    menuai: menuai, entity_registry: er.EntityRegistry, calls: list[ServiceCall]
) -> None:
    """Test templates with values from other entities."""
    with assert_setup_component(1, "input_select"):
        assert await setup.async_setup_component(
            menuai,
            "input_select",
            {
                "input_select": {
                    "option": {
                        "options": ["a", "b"],
                        "initial": "a",
                        "name": "Option",
                    },
                }
            },
        )

    with assert_setup_component(1, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {
                "template": {
                    "unique_id": "b",
                    "select": {
                        "state": f"{{{{ states('{_OPTION_INPUT_SELECT}') }}}}",
                        "options": f"{{{{ state_attr('{_OPTION_INPUT_SELECT}', '{INPUT_SELECT_ATTR_OPTIONS}') }}}}",
                        "select_option": [
                            {
                                "service": "input_select.select_option",
                                "data_template": {
                                    "entity_id": _OPTION_INPUT_SELECT,
                                    "option": "{{ option }}",
                                },
                            },
                            {
                                "service": "test.automation",
                                "data_template": {
                                    "action": "select_option",
                                    "caller": "{{ this.entity_id }}",
                                    "option": "{{ option }}",
                                },
                            },
                        ],
                        "optimistic": True,
                        "unique_id": "a",
                    },
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    entry = entity_registry.async_get(_TEST_SELECT)
    assert entry
    assert entry.unique_id == "b-a"

    _verify(menuai, "a", ["a", "b"])

    await menuai.services.async_call(
        INPUT_SELECT_DOMAIN,
        INPUT_SELECT_SERVICE_SELECT_OPTION,
        {CONF_ENTITY_ID: _OPTION_INPUT_SELECT, INPUT_SELECT_ATTR_OPTION: "b"},
        blocking=True,
    )
    await menuai.async_block_till_done()
    _verify(menuai, "b", ["a", "b"])

    await menuai.services.async_call(
        INPUT_SELECT_DOMAIN,
        SERVICE_SET_OPTIONS,
        {
            CONF_ENTITY_ID: _OPTION_INPUT_SELECT,
            INPUT_SELECT_ATTR_OPTIONS: ["a", "b", "c"],
        },
        blocking=True,
    )
    await menuai.async_block_till_done()
    _verify(menuai, "b", ["a", "b", "c"])

    await menuai.services.async_call(
        SELECT_DOMAIN,
        SELECT_SERVICE_SELECT_OPTION,
        {CONF_ENTITY_ID: _TEST_SELECT, SELECT_ATTR_OPTION: "c"},
        blocking=True,
    )
    _verify(menuai, "c", ["a", "b", "c"])

    # Check this variable can be used in set_value script
    assert len(calls) == 1
    assert calls[-1].data["action"] == "select_option"
    assert calls[-1].data["caller"] == _TEST_SELECT
    assert calls[-1].data["option"] == "c"


async def test_trigger_select(menuai: menuai) -> None:
    """Test trigger based template select."""
    events = async_capture_events(menuai, "test_number_event")
    action_events = async_capture_events(menuai, "action_event")
    assert await setup.async_setup_component(
        menuai,
        "template",
        {
            "template": [
                {"invalid": "config"},
                # Config after invalid should still be set up
                {
                    "unique_id": "listening-test-event",
                    "trigger": {"platform": "event", "event_type": "test_event"},
                    "variables": {"beer": "{{ trigger.event.data.beer }}"},
                    "action": [
                        {"event": "action_event", "event_data": {"beer": "{{ beer }}"}}
                    ],
                    "select": [
                        {
                            "name": "Hello Name",
                            "unique_id": "hello_name-id",
                            "state": "{{ trigger.event.data.beer }}",
                            "options": "{{ trigger.event.data.beers }}",
                            "select_option": {
                                "event": "test_number_event",
                                "event_data": {
                                    "entity_id": "{{ this.entity_id }}",
                                    "beer": "{{ beer }}",
                                },
                            },
                            "optimistic": True,
                        },
                    ],
                },
            ],
        },
    )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    state = menuai.states.get("select.hello_name")
    assert state is not None
    assert state.state == STATE_UNKNOWN

    context = Context()
    menuai.bus.async_fire(
        "test_event", {"beer": "duff", "beers": ["duff", "alamo"]}, context=context
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("select.hello_name")
    assert state is not None
    assert state.state == "duff"
    assert state.attributes["options"] == ["duff", "alamo"]

    assert len(action_events) == 1
    assert action_events[0].event_type == "action_event"
    beer = action_events[0].data.get("beer")
    assert beer is not None
    assert beer == "duff"

    await menuai.services.async_call(
        SELECT_DOMAIN,
        SELECT_SERVICE_SELECT_OPTION,
        {CONF_ENTITY_ID: "select.hello_name", SELECT_ATTR_OPTION: "alamo"},
        blocking=True,
    )
    assert len(events) == 1
    assert events[0].event_type == "test_number_event"
    entity_id = events[0].data.get("entity_id")
    assert entity_id is not None
    assert entity_id == "select.hello_name"

    beer = events[0].data.get("beer")
    assert beer is not None
    assert beer == "duff"


def _verify(
    menuai: menuai,
    expected_current_option: str,
    expected_options: list[str],
    entity_name: str = _TEST_SELECT,
) -> None:
    """Verify select's state."""
    state = menuai.states.get(entity_name)
    attributes = state.attributes
    assert state.state == str(expected_current_option)
    assert attributes.get(SELECT_ATTR_OPTIONS) == expected_options


async def test_template_icon_with_entities(menuai: menuai) -> None:
    """Test templates with values from other entities."""
    with assert_setup_component(1, "input_select"):
        assert await setup.async_setup_component(
            menuai,
            "input_select",
            {
                "input_select": {
                    "option": {
                        "options": ["a", "b"],
                        "initial": "a",
                        "name": "Option",
                    },
                }
            },
        )

    with assert_setup_component(1, "template"):
        assert await setup.async_setup_component(
            menuai,
            "template",
            {
                "template": {
                    "unique_id": "b",
                    "select": {
                        "state": f"{{{{ states('{_OPTION_INPUT_SELECT}') }}}}",
                        "options": f"{{{{ state_attr('{_OPTION_INPUT_SELECT}', '{INPUT_SELECT_ATTR_OPTIONS}') }}}}",
                        "select_option": {
                            "service": "input_select.select_option",
                            "data": {
                                "entity_id": _OPTION_INPUT_SELECT,
                                "option": "{{ option }}",
                            },
                        },
                        "optimistic": True,
                        "unique_id": "a",
                        "icon": f"{{% if (states('{_OPTION_INPUT_SELECT}') == 'a') %}}mdi:greater{{% else %}}mdi:less{{% endif %}}",
                    },
                }
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    state = menuai.states.get(_TEST_SELECT)
    assert state.state == "a"
    assert state.attributes[ATTR_ICON] == "mdi:greater"

    await menuai.services.async_call(
        INPUT_SELECT_DOMAIN,
        INPUT_SELECT_SERVICE_SELECT_OPTION,
        {CONF_ENTITY_ID: _OPTION_INPUT_SELECT, INPUT_SELECT_ATTR_OPTION: "b"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(_TEST_SELECT)
    assert state.state == "b"
    assert state.attributes[ATTR_ICON] == "mdi:less"


async def test_template_icon_with_trigger(menuai: menuai) -> None:
    """Test trigger based template select."""
    with assert_setup_component(1, "input_select"):
        assert await setup.async_setup_component(
            menuai,
            "input_select",
            {
                "input_select": {
                    "option": {
                        "options": ["a", "b"],
                        "initial": "a",
                        "name": "Option",
                    },
                }
            },
        )

    assert await setup.async_setup_component(
        menuai,
        "template",
        {
            "template": {
                "trigger": {"platform": "state", "entity_id": _OPTION_INPUT_SELECT},
                "select": {
                    "unique_id": "b",
                    "state": "{{ trigger.to_state.state }}",
                    "options": f"{{{{ state_attr('{_OPTION_INPUT_SELECT}', '{INPUT_SELECT_ATTR_OPTIONS}') }}}}",
                    "select_option": {
                        "service": "input_select.select_option",
                        "data": {
                            "entity_id": _OPTION_INPUT_SELECT,
                            "option": "{{ option }}",
                        },
                    },
                    "optimistic": True,
                    "icon": "{% if (trigger.to_state.state or '') == 'a' %}mdi:greater{% else %}mdi:less{% endif %}",
                },
            },
        },
    )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        INPUT_SELECT_DOMAIN,
        INPUT_SELECT_SERVICE_SELECT_OPTION,
        {CONF_ENTITY_ID: _OPTION_INPUT_SELECT, INPUT_SELECT_ATTR_OPTION: "b"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(_TEST_SELECT)
    assert state is not None
    assert state.state == "b"
    assert state.attributes[ATTR_ICON] == "mdi:less"

    await menuai.services.async_call(
        INPUT_SELECT_DOMAIN,
        INPUT_SELECT_SERVICE_SELECT_OPTION,
        {CONF_ENTITY_ID: _OPTION_INPUT_SELECT, INPUT_SELECT_ATTR_OPTION: "a"},
        blocking=True,
    )
    await menuai.async_block_till_done()

    state = menuai.states.get(_TEST_SELECT)
    assert state.state == "a"
    assert state.attributes[ATTR_ICON] == "mdi:greater"


async def test_device_id(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test for device for select template."""

    device_config_entry = MockConfigEntry()
    device_config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=device_config_entry.entry_id,
        identifiers={("test", "identifier_test")},
        connections={("mac", "30:31:32:33:34:35")},
    )
    await menuai.async_block_till_done()
    assert device_entry is not None
    assert device_entry.id is not None

    template_config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "name": "My template",
            "template_type": "select",
            "state": "{{ 'on' }}",
            "options": "{{ ['off', 'on', 'auto'] }}",
            "device_id": device_entry.id,
        },
        title="My template",
    )
    template_config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(template_config_entry.entry_id)
    await menuai.async_block_till_done()

    template_entity = entity_registry.async_get("select.my_template")
    assert template_entity is not None
    assert template_entity.device_id == device_entry.id


@pytest.mark.parametrize(
    ("count", "select_config"),
    [
        (
            1,
            {
                "state": "{{ 'b' }}",
                "select_option": [],
                "options": "{{ ['a', 'b'] }}",
                "optimistic": True,
            },
        )
    ],
)
@pytest.mark.parametrize(
    "style",
    [
        ConfigurationStyle.MODERN,
    ],
)
async def test_empty_action_config(menuai: menuai, setup_select) -> None:
    """Test configuration with empty script."""
    await menuai.services.async_call(
        select.DOMAIN,
        select.SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: _TEST_SELECT, "option": "a"},
        blocking=True,
    )

    state = menuai.states.get(_TEST_SELECT)
    assert state.state == "a"
