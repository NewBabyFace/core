"""The tests for the trigger helper."""

from unittest.mock import ANY, AsyncMock, MagicMock, call, patch

import pytest
import voluptuous as vol

from menuai.core import Context, menuai, ServiceCall, callback
from menuai.helpers.trigger import (
    DATA_PLUGGABLE_ACTIONS,
    PluggableAction,
    _async_get_trigger_platform,
    async_initialize_triggers,
    async_validate_trigger_config,
)
from menuai.setup import async_setup_component


async def test_bad_trigger_platform(menuai: menuai) -> None:
    """Test bad trigger platform."""
    with pytest.raises(vol.Invalid) as ex:
        await async_validate_trigger_config(menuai, [{"platform": "not_a_platform"}])
    assert "Invalid trigger 'not_a_platform' specified" in str(ex)


async def test_trigger_subtype(menuai: menuai) -> None:
    """Test trigger subtypes."""
    with patch(
        "menuai.helpers.trigger.async_get_integration",
        return_value=MagicMock(async_get_platform=AsyncMock()),
    ) as integration_mock:
        await _async_get_trigger_platform(menuai, {"platform": "test.subtype"})
        assert integration_mock.call_args == call(menuai, "test")


async def test_trigger_variables(menuai: menuai) -> None:
    """Test trigger variables."""


async def test_if_fires_on_event(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test the firing of events."""
    assert await async_setup_component(
        menuai,
        "automation",
        {
            "automation": {
                "trigger": {
                    "platform": "event",
                    "event_type": "test_event",
                    "variables": {
                        "name": "Paulus",
                        "via_event": "{{ trigger.event.event_type }}",
                    },
                },
                "action": {
                    "service": "test.automation",
                    "data_template": {"hello": "{{ name }} + {{ via_event }}"},
                },
            }
        },
    )

    menuai.bus.async_fire("test_event")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert service_calls[0].data["hello"] == "Paulus + test_event"


async def test_if_disabled_trigger_not_firing(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test disabled triggers don't fire."""
    assert await async_setup_component(
        menuai,
        "automation",
        {
            "automation": {
                "trigger": [
                    {
                        "platform": "event",
                        "event_type": "enabled_trigger_event",
                    },
                    {
                        "enabled": False,
                        "platform": "event",
                        "event_type": "disabled_trigger_event",
                    },
                ],
                "action": {
                    "service": "test.automation",
                },
            }
        },
    )

    menuai.bus.async_fire("disabled_trigger_event")
    await menuai.async_block_till_done()
    assert not service_calls

    menuai.bus.async_fire("enabled_trigger_event")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_trigger_enabled_templates(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test triggers enabled by template."""
    assert await async_setup_component(
        menuai,
        "automation",
        {
            "automation": {
                "trigger": [
                    {
                        "enabled": "{{ 'some text' }}",
                        "platform": "event",
                        "event_type": "truthy_template_trigger_event",
                    },
                    {
                        "enabled": "{{ 3 == 4 }}",
                        "platform": "event",
                        "event_type": "falsy_template_trigger_event",
                    },
                    {
                        "enabled": False,  # eg. from a blueprints input defaulting to `false`
                        "platform": "event",
                        "event_type": "falsy_trigger_event",
                    },
                    {
                        "enabled": "some text",  # eg. from a blueprints input value
                        "platform": "event",
                        "event_type": "truthy_trigger_event",
                    },
                ],
                "action": {
                    "service": "test.automation",
                },
            }
        },
    )

    menuai.bus.async_fire("falsy_template_trigger_event")
    await menuai.async_block_till_done()
    assert not service_calls

    menuai.bus.async_fire("falsy_trigger_event")
    await menuai.async_block_till_done()
    assert not service_calls

    menuai.bus.async_fire("truthy_template_trigger_event")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1

    menuai.bus.async_fire("truthy_trigger_event")
    await menuai.async_block_till_done()
    assert len(service_calls) == 2


async def test_nested_trigger_list(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test triggers within nested list."""

    assert await async_setup_component(
        menuai,
        "automation",
        {
            "automation": {
                "trigger": [
                    {
                        "triggers": {
                            "platform": "event",
                            "event_type": "trigger_1",
                        },
                    },
                    {
                        "platform": "event",
                        "event_type": "trigger_2",
                    },
                    {"triggers": []},
                    {"triggers": None},
                    {
                        "triggers": [
                            {
                                "platform": "event",
                                "event_type": "trigger_3",
                            },
                            {
                                "platform": "event",
                                "event_type": "trigger_4",
                            },
                        ],
                    },
                ],
                "action": {
                    "service": "test.automation",
                },
            }
        },
    )

    menuai.bus.async_fire("trigger_1")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1

    menuai.bus.async_fire("trigger_2")
    await menuai.async_block_till_done()
    assert len(service_calls) == 2

    menuai.bus.async_fire("trigger_none")
    await menuai.async_block_till_done()
    assert len(service_calls) == 2

    menuai.bus.async_fire("trigger_3")
    await menuai.async_block_till_done()
    assert len(service_calls) == 3

    menuai.bus.async_fire("trigger_4")
    await menuai.async_block_till_done()
    assert len(service_calls) == 4


async def test_trigger_enabled_template_limited(
    menuai: menuai,
    service_calls: list[ServiceCall],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test triggers enabled invalid template."""
    assert await async_setup_component(
        menuai,
        "automation",
        {
            "automation": {
                "trigger": [
                    {
                        "enabled": "{{ states('sensor.limited') }}",  # only limited template supported
                        "platform": "event",
                        "event_type": "test_event",
                    },
                ],
                "action": {
                    "service": "test.automation",
                },
            }
        },
    )

    menuai.bus.async_fire("test_event")
    await menuai.async_block_till_done()
    assert not service_calls
    assert "Error rendering enabled template" in caplog.text


async def test_trigger_alias(
    menuai: menuai,
    service_calls: list[ServiceCall],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test triggers support aliases."""
    assert await async_setup_component(
        menuai,
        "automation",
        {
            "automation": {
                "trigger": [
                    {
                        "alias": "My event",
                        "platform": "event",
                        "event_type": "trigger_event",
                    }
                ],
                "action": {
                    "service": "test.automation",
                    "data_template": {"alias": "{{ trigger.alias }}"},
                },
            }
        },
    )

    menuai.bus.async_fire("trigger_event")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert service_calls[0].data["alias"] == "My event"
    assert (
        "Automation trigger 'My event' triggered by event 'trigger_event'"
        in caplog.text
    )


async def test_async_initialize_triggers(
    menuai: menuai,
    service_calls: list[ServiceCall],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test async_initialize_triggers with different action types."""

    log_cb = MagicMock()

    action_calls = []

    trigger_config = await async_validate_trigger_config(
        menuai,
        [
            {
                "platform": "event",
                "event_type": ["trigger_event"],
                "variables": {
                    "name": "Paulus",
                    "via_event": "{{ trigger.event.event_type }}",
                },
            }
        ],
    )

    async def async_action(*args):
        action_calls.append([*args])

    @callback
    def cb_action(*args):
        action_calls.append([*args])

    def non_cb_action(*args):
        action_calls.append([*args])

    for action in (async_action, cb_action, non_cb_action):
        action_calls = []

        unsub = await async_initialize_triggers(
            menuai,
            trigger_config,
            action,
            "test",
            "",
            log_cb,
        )
        await menuai.async_block_till_done()

        menuai.bus.async_fire("trigger_event")
        await menuai.async_block_till_done()
        await menuai.async_block_till_done()

        assert len(action_calls) == 1
        assert action_calls[0][0]["name"] == "Paulus"
        assert action_calls[0][0]["via_event"] == "trigger_event"
        log_cb.assert_called_once_with(ANY, "Initialized trigger")

        log_cb.reset_mock()
        unsub()


async def test_pluggable_action(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test normal behavior of pluggable actions."""
    update_1 = MagicMock()
    update_2 = MagicMock()
    action_1 = AsyncMock()
    action_2 = AsyncMock()
    trigger_1 = {"domain": "test", "device": "1"}
    trigger_2 = {"domain": "test", "device": "2"}
    variables_1 = {"source": "test 1"}
    variables_2 = {"source": "test 2"}
    context_1 = Context()
    context_2 = Context()

    plug_1 = PluggableAction(update_1)
    plug_2 = PluggableAction(update_2)

    # Verify plug is inactive without triggers
    remove_plug_1 = plug_1.async_register(menuai, trigger_1)
    assert not plug_1
    assert not plug_2

    # Verify plug remain inactive with non matching trigger
    remove_attach_2 = PluggableAction.async_attach_trigger(
        menuai, trigger_2, action_2, variables_2
    )
    assert not plug_1
    assert not plug_2
    update_1.assert_not_called()
    update_2.assert_not_called()

    # Verify plug is active, and update when matching trigger attaches
    remove_attach_1 = PluggableAction.async_attach_trigger(
        menuai, trigger_1, action_1, variables_1
    )
    assert plug_1
    assert not plug_2
    update_1.assert_called()
    update_1.reset_mock()
    update_2.assert_not_called()

    # Verify a non registered plug is inactive
    remove_plug_1()
    assert not plug_1
    assert not plug_2

    # Verify a plug registered to existing trigger is true
    remove_plug_1 = plug_1.async_register(menuai, trigger_1)
    assert plug_1
    assert not plug_2

    remove_plug_2 = plug_2.async_register(menuai, trigger_2)
    assert plug_1
    assert plug_2

    # Verify no actions should have been triggered so far
    action_1.assert_not_called()
    action_2.assert_not_called()

    # Verify action is triggered with correct data
    await plug_1.async_run(menuai, context_1)
    await plug_2.async_run(menuai, context_2)
    action_1.assert_called_with(variables_1, context_1)
    action_2.assert_called_with(variables_2, context_2)

    # Verify plug goes inactive if trigger is removed
    remove_attach_1()
    assert not plug_1

    # Verify registry is cleaned when no plugs nor triggers are attached
    assert menuai.data[DATA_PLUGGABLE_ACTIONS]
    remove_plug_1()
    remove_plug_2()
    remove_attach_2()
    assert not menuai.data[DATA_PLUGGABLE_ACTIONS]
    assert not plug_2
