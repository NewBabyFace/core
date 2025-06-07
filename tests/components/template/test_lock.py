"""The tests for the Template lock platform."""

from typing import Any

import pytest

from menuai import setup
from menuai.components import lock, template
from menuai.components.lock import LockEntityFeature, LockState
from menuai.const import (
    ATTR_CODE,
    ATTR_ENTITY_ID,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
    STATE_UNAVAILABLE,
)
from menuai.core import menuai, ServiceCall
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component

from .conftest import ConfigurationStyle

from tests.common import assert_setup_component

TEST_OBJECT_ID = "test_template_lock"
TEST_ENTITY_ID = f"lock.{TEST_OBJECT_ID}"
TEST_STATE_ENTITY_ID = "switch.test_state"

LOCK_ACTION = {
    "lock": {
        "service": "test.automation",
        "data_template": {
            "action": "lock",
            "caller": "{{ this.entity_id }}",
            "code": "{{ code if code is defined else None }}",
        },
    },
}
UNLOCK_ACTION = {
    "unlock": {
        "service": "test.automation",
        "data_template": {
            "action": "unlock",
            "caller": "{{ this.entity_id }}",
            "code": "{{ code if code is defined else None }}",
        },
    },
}
OPEN_ACTION = {
    "open": {
        "service": "test.automation",
        "data_template": {
            "action": "open",
            "caller": "{{ this.entity_id }}",
        },
    },
}


OPTIMISTIC_LOCK = {
    **LOCK_ACTION,
    **UNLOCK_ACTION,
}


OPTIMISTIC_LOCK_CONFIG = {
    "platform": "template",
    **LOCK_ACTION,
    **UNLOCK_ACTION,
    **OPEN_ACTION,
}

OPTIMISTIC_CODED_LOCK_CONFIG = {
    "platform": "template",
    **LOCK_ACTION,
    **UNLOCK_ACTION,
}


async def async_setup_legacy_format(
    menuai: menuai, count: int, lock_config: dict[str, Any]
) -> None:
    """Do setup of lock integration via legacy format."""
    config = {"lock": {"platform": "template", "name": TEST_OBJECT_ID, **lock_config}}

    with assert_setup_component(count, lock.DOMAIN):
        assert await async_setup_component(
            menuai,
            lock.DOMAIN,
            config,
        )
    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()


async def async_setup_modern_format(
    menuai: menuai, count: int, lock_config: dict[str, Any]
) -> None:
    """Do setup of lock integration via modern format."""
    config = {"template": {"lock": {"name": TEST_OBJECT_ID, **lock_config}}}

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
async def setup_lock(
    menuai: menuai,
    count: int,
    style: ConfigurationStyle,
    lock_config: dict[str, Any],
) -> None:
    """Do setup of lock integration."""
    if style == ConfigurationStyle.LEGACY:
        await async_setup_legacy_format(menuai, count, lock_config)
    elif style == ConfigurationStyle.MODERN:
        await async_setup_modern_format(menuai, count, lock_config)


@pytest.fixture
async def setup_base_lock(
    menuai: menuai,
    count: int,
    style: ConfigurationStyle,
    state_template: str,
    extra_config: dict,
):
    """Do setup of cover integration using a state template."""
    if style == ConfigurationStyle.LEGACY:
        await async_setup_legacy_format(
            menuai,
            count,
            {"value_template": state_template, **extra_config},
        )
    elif style == ConfigurationStyle.MODERN:
        await async_setup_modern_format(
            menuai,
            count,
            {"state": state_template, **extra_config},
        )


@pytest.fixture
async def setup_state_lock(
    menuai: menuai,
    count: int,
    style: ConfigurationStyle,
    state_template: str,
):
    """Do setup of cover integration using a state template."""
    if style == ConfigurationStyle.LEGACY:
        await async_setup_legacy_format(
            menuai,
            count,
            {
                **OPTIMISTIC_LOCK,
                "value_template": state_template,
            },
        )
    elif style == ConfigurationStyle.MODERN:
        await async_setup_modern_format(
            menuai,
            count,
            {
                **OPTIMISTIC_LOCK,
                "state": state_template,
            },
        )


@pytest.fixture
async def setup_state_lock_with_extra_config(
    menuai: menuai,
    count: int,
    style: ConfigurationStyle,
    state_template: str,
    extra_config: dict,
):
    """Do setup of cover integration using a state template."""
    if style == ConfigurationStyle.LEGACY:
        await async_setup_legacy_format(
            menuai,
            count,
            {**OPTIMISTIC_LOCK, "value_template": state_template, **extra_config},
        )
    elif style == ConfigurationStyle.MODERN:
        await async_setup_modern_format(
            menuai,
            count,
            {**OPTIMISTIC_LOCK, "state": state_template, **extra_config},
        )


@pytest.fixture
async def setup_state_lock_with_attribute(
    menuai: menuai,
    count: int,
    style: ConfigurationStyle,
    state_template: str,
    attribute: str,
    attribute_template: str,
):
    """Do setup of cover integration using a state template."""
    extra = {attribute: attribute_template} if attribute else {}
    if style == ConfigurationStyle.LEGACY:
        await async_setup_legacy_format(
            menuai,
            count,
            {
                **OPTIMISTIC_LOCK,
                "value_template": state_template,
                **extra,
            },
        )
    elif style == ConfigurationStyle.MODERN:
        await async_setup_modern_format(
            menuai,
            count,
            {**OPTIMISTIC_LOCK, "state": state_template, **extra},
        )


@pytest.mark.parametrize(
    ("count", "state_template"), [(1, "{{ states.switch.test_state.state }}")]
)
@pytest.mark.parametrize(
    "style", [ConfigurationStyle.LEGACY, ConfigurationStyle.MODERN]
)
@pytest.mark.usefixtures("setup_state_lock")
async def test_template_state(menuai: menuai) -> None:
    """Test template."""
    menuai.states.async_set(TEST_STATE_ENTITY_ID, STATE_ON)
    await menuai.async_block_till_done()

    state = menuai.states.get("lock.test_template_lock")
    assert state.state == LockState.LOCKED

    menuai.states.async_set(TEST_STATE_ENTITY_ID, STATE_OFF)
    await menuai.async_block_till_done()

    state = menuai.states.get("lock.test_template_lock")
    assert state.state == LockState.UNLOCKED

    menuai.states.async_set(TEST_STATE_ENTITY_ID, STATE_OPEN)
    await menuai.async_block_till_done()

    state = menuai.states.get("lock.test_template_lock")
    assert state.state == LockState.OPEN


@pytest.mark.parametrize(
    ("count", "state_template", "extra_config"),
    [(1, "{{ states.switch.test_state.state }}", {"optimistic": True, **OPEN_ACTION})],
)
@pytest.mark.parametrize(
    "style", [ConfigurationStyle.LEGACY, ConfigurationStyle.MODERN]
)
@pytest.mark.usefixtures("setup_state_lock_with_extra_config")
async def test_open_lock_optimistic(
    menuai: menuai, calls: list[ServiceCall]
) -> None:
    """Test optimistic open."""
    menuai.states.async_set(TEST_STATE_ENTITY_ID, STATE_ON)
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == LockState.LOCKED

    await menuai.services.async_call(
        lock.DOMAIN,
        lock.SERVICE_OPEN,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
    )
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data["action"] == "open"
    assert calls[0].data["caller"] == TEST_ENTITY_ID

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == LockState.OPEN


@pytest.mark.parametrize(("count", "state_template"), [(1, "{{ 1 == 1 }}")])
@pytest.mark.parametrize(
    "style", [ConfigurationStyle.LEGACY, ConfigurationStyle.MODERN]
)
@pytest.mark.usefixtures("setup_state_lock")
async def test_template_state_boolean_on(menuai: menuai) -> None:
    """Test the setting of the state with boolean on."""
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == LockState.LOCKED


@pytest.mark.parametrize(("count", "state_template"), [(1, "{{ 1 == 2 }}")])
@pytest.mark.parametrize(
    "style", [ConfigurationStyle.LEGACY, ConfigurationStyle.MODERN]
)
@pytest.mark.usefixtures("setup_state_lock")
async def test_template_state_boolean_off(menuai: menuai) -> None:
    """Test the setting of the state with off."""
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == LockState.UNLOCKED


@pytest.mark.parametrize("count", [0])
@pytest.mark.parametrize(
    "style", [ConfigurationStyle.LEGACY, ConfigurationStyle.MODERN]
)
@pytest.mark.parametrize(
    ("state_template", "extra_config"),
    [
        ("{% if rubbish %}", OPTIMISTIC_LOCK),
        ("{{ rubbish }", OPTIMISTIC_LOCK),
        ("Invalid", {}),
        (
            "{{ 1==1 }}",
            {
                "not_value_template": "{{ states.switch.test_state.state }}",
                **OPTIMISTIC_LOCK,
            },
        ),
    ],
)
@pytest.mark.usefixtures("setup_base_lock")
async def test_template_syntax_error(menuai: menuai) -> None:
    """Test templating syntax errors don't create entities."""
    assert menuai.states.async_all("lock") == []


@pytest.mark.parametrize(("count", "state_template"), [(0, "{{ 1==1 }}")])
@pytest.mark.parametrize("attribute_template", ["{{ rubbish }", "{% if rubbish %}"])
@pytest.mark.parametrize(
    ("style", "attribute"),
    [
        (ConfigurationStyle.LEGACY, "code_format_template"),
        (ConfigurationStyle.MODERN, "code_format"),
    ],
)
@pytest.mark.usefixtures("setup_state_lock_with_attribute")
async def test_template_code_template_syntax_error(menuai: menuai) -> None:
    """Test templating code_format syntax errors don't create entities."""
    assert menuai.states.async_all("lock") == []


@pytest.mark.parametrize(("count", "state_template"), [(1, "{{ 1 + 1 }}")])
@pytest.mark.parametrize(
    "style", [ConfigurationStyle.LEGACY, ConfigurationStyle.MODERN]
)
@pytest.mark.usefixtures("setup_state_lock")
async def test_template_static(menuai: menuai) -> None:
    """Test that we allow static templates."""
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == LockState.UNLOCKED

    menuai.states.async_set(TEST_ENTITY_ID, LockState.LOCKED)
    await menuai.async_block_till_done()
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == LockState.LOCKED


@pytest.mark.parametrize("count", [1])
@pytest.mark.parametrize(
    "style", [ConfigurationStyle.LEGACY, ConfigurationStyle.MODERN]
)
@pytest.mark.parametrize(
    ("state_template", "expected"),
    [
        ("{{ True }}", LockState.LOCKED),
        ("{{ False }}", LockState.UNLOCKED),
        ("{{ x - 12 }}", STATE_UNAVAILABLE),
    ],
)
@pytest.mark.usefixtures("setup_state_lock")
async def test_state_template(menuai: menuai, expected: str) -> None:
    """Test state and value_template template."""
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == expected


@pytest.mark.parametrize(("count", "state_template"), [(1, "{{ 1==1 }}")])
@pytest.mark.parametrize(
    "attribute_template",
    ["{% if states.switch.test_state.state %}/local/switch.png{% endif %}"],
)
@pytest.mark.parametrize(
    ("style", "attribute"),
    [
        (ConfigurationStyle.MODERN, "picture"),
    ],
)
@pytest.mark.usefixtures("setup_state_lock_with_attribute")
async def test_picture_template(menuai: menuai) -> None:
    """Test entity_picture template."""
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.attributes.get("entity_picture") in ("", None)

    menuai.states.async_set(TEST_STATE_ENTITY_ID, STATE_ON)
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.attributes["entity_picture"] == "/local/switch.png"


@pytest.mark.parametrize(("count", "state_template"), [(1, "{{ 1==1 }}")])
@pytest.mark.parametrize(
    "attribute_template",
    ["{% if states.switch.test_state.state %}mdi:eye{% endif %}"],
)
@pytest.mark.parametrize(
    ("style", "attribute"),
    [
        (ConfigurationStyle.MODERN, "icon"),
    ],
)
@pytest.mark.usefixtures("setup_state_lock_with_attribute")
async def test_icon_template(menuai: menuai) -> None:
    """Test entity_picture template."""
    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.attributes.get("icon") in ("", None)

    menuai.states.async_set(TEST_STATE_ENTITY_ID, STATE_ON)
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.attributes["icon"] == "mdi:eye"


@pytest.mark.parametrize(
    ("count", "state_template"), [(1, "{{ states.switch.test_state.state }}")]
)
@pytest.mark.parametrize(
    "style", [ConfigurationStyle.LEGACY, ConfigurationStyle.MODERN]
)
@pytest.mark.usefixtures("setup_state_lock")
async def test_lock_action(menuai: menuai, calls: list[ServiceCall]) -> None:
    """Test lock action."""
    menuai.states.async_set(TEST_STATE_ENTITY_ID, STATE_OFF)
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == LockState.UNLOCKED

    await menuai.services.async_call(
        lock.DOMAIN,
        lock.SERVICE_LOCK,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
    )
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data["action"] == "lock"
    assert calls[0].data["caller"] == TEST_ENTITY_ID


@pytest.mark.parametrize(
    ("count", "state_template"), [(1, "{{ states.switch.test_state.state }}")]
)
@pytest.mark.parametrize(
    "style", [ConfigurationStyle.LEGACY, ConfigurationStyle.MODERN]
)
@pytest.mark.usefixtures("setup_state_lock")
async def test_unlock_action(menuai: menuai, calls: list[ServiceCall]) -> None:
    """Test unlock action."""
    menuai.states.async_set(TEST_STATE_ENTITY_ID, STATE_ON)
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == LockState.LOCKED

    await menuai.services.async_call(
        lock.DOMAIN,
        lock.SERVICE_UNLOCK,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
    )
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data["action"] == "unlock"
    assert calls[0].data["caller"] == TEST_ENTITY_ID


@pytest.mark.parametrize(
    ("count", "state_template", "extra_config"),
    [(1, "{{ states.switch.test_state.state }}", OPEN_ACTION)],
)
@pytest.mark.parametrize(
    "style", [ConfigurationStyle.LEGACY, ConfigurationStyle.MODERN]
)
@pytest.mark.usefixtures("setup_state_lock_with_extra_config")
async def test_open_action(menuai: menuai, calls: list[ServiceCall]) -> None:
    """Test open action."""
    menuai.states.async_set(TEST_STATE_ENTITY_ID, STATE_ON)
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == LockState.LOCKED

    await menuai.services.async_call(
        lock.DOMAIN,
        lock.SERVICE_OPEN,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
    )
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data["action"] == "open"
    assert calls[0].data["caller"] == TEST_ENTITY_ID


@pytest.mark.parametrize(
    ("count", "state_template", "attribute_template"),
    [
        (
            1,
            "{{ states.switch.test_state.state }}",
            "{{ '.+' }}",
        )
    ],
)
@pytest.mark.parametrize(
    ("style", "attribute"),
    [
        (ConfigurationStyle.LEGACY, "code_format_template"),
        (ConfigurationStyle.MODERN, "code_format"),
    ],
)
@pytest.mark.usefixtures("setup_state_lock_with_attribute")
async def test_lock_action_with_code(
    menuai: menuai, calls: list[ServiceCall]
) -> None:
    """Test lock action with defined code format and supplied lock code."""
    menuai.states.async_set(TEST_STATE_ENTITY_ID, STATE_OFF)
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == LockState.UNLOCKED

    await menuai.services.async_call(
        lock.DOMAIN,
        lock.SERVICE_LOCK,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID, ATTR_CODE: "LOCK_CODE"},
    )
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data["action"] == "lock"
    assert calls[0].data["caller"] == TEST_ENTITY_ID
    assert calls[0].data["code"] == "LOCK_CODE"


@pytest.mark.parametrize(
    ("count", "state_template", "attribute_template"),
    [
        (
            1,
            "{{ states.switch.test_state.state }}",
            "{{ '.+' }}",
        )
    ],
)
@pytest.mark.parametrize(
    ("style", "attribute"),
    [
        (ConfigurationStyle.LEGACY, "code_format_template"),
        (ConfigurationStyle.MODERN, "code_format"),
    ],
)
@pytest.mark.usefixtures("setup_state_lock_with_attribute")
async def test_unlock_action_with_code(
    menuai: menuai, calls: list[ServiceCall]
) -> None:
    """Test unlock action with code format and supplied unlock code."""
    await setup.async_setup_component(menuai, "switch", {})
    menuai.states.async_set(TEST_STATE_ENTITY_ID, STATE_ON)
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == LockState.LOCKED

    await menuai.services.async_call(
        lock.DOMAIN,
        lock.SERVICE_UNLOCK,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID, ATTR_CODE: "UNLOCK_CODE"},
    )
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data["action"] == "unlock"
    assert calls[0].data["caller"] == TEST_ENTITY_ID
    assert calls[0].data["code"] == "UNLOCK_CODE"


@pytest.mark.parametrize(
    ("count", "state_template", "attribute_template"),
    [
        (
            1,
            "{{ 1 == 1 }}",
            "{{ '\\\\d+' }}",
        )
    ],
)
@pytest.mark.parametrize(
    ("style", "attribute"),
    [
        (ConfigurationStyle.LEGACY, "code_format_template"),
        (ConfigurationStyle.MODERN, "code_format"),
    ],
)
@pytest.mark.parametrize(
    "test_action",
    [
        lock.SERVICE_LOCK,
        lock.SERVICE_UNLOCK,
    ],
)
@pytest.mark.usefixtures("setup_state_lock_with_attribute")
async def test_lock_actions_fail_with_invalid_code(
    menuai: menuai, calls: list[ServiceCall], test_action
) -> None:
    """Test invalid lock codes."""
    await menuai.services.async_call(
        lock.DOMAIN,
        test_action,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID, ATTR_CODE: "non-number-value"},
    )
    await menuai.services.async_call(
        lock.DOMAIN,
        test_action,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
    )
    await menuai.async_block_till_done()

    assert len(calls) == 0


@pytest.mark.parametrize(
    ("count", "state_template", "attribute_template"),
    [
        (
            1,
            "{{ 1 == 1 }}",
            "{{ 1/0 }}",
        )
    ],
)
@pytest.mark.parametrize(
    ("style", "attribute"),
    [
        (ConfigurationStyle.LEGACY, "code_format_template"),
        (ConfigurationStyle.MODERN, "code_format"),
    ],
)
@pytest.mark.usefixtures("setup_state_lock_with_attribute")
async def test_lock_actions_dont_execute_with_code_template_rendering_error(
    menuai: menuai, calls: list[ServiceCall]
) -> None:
    """Test lock code format rendering fails block lock/unlock actions."""
    await menuai.services.async_call(
        lock.DOMAIN,
        lock.SERVICE_LOCK,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
    )
    await menuai.services.async_call(
        lock.DOMAIN,
        lock.SERVICE_UNLOCK,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID, ATTR_CODE: "any-value"},
    )
    await menuai.async_block_till_done()

    assert len(calls) == 0


@pytest.mark.parametrize(
    ("count", "state_template", "attribute_template"),
    [
        (
            1,
            "{{ states.switch.test_state.state }}",
            "{{ None }}",
        )
    ],
)
@pytest.mark.parametrize(
    ("style", "attribute"),
    [
        (ConfigurationStyle.LEGACY, "code_format_template"),
        (ConfigurationStyle.MODERN, "code_format"),
    ],
)
@pytest.mark.parametrize("action", [lock.SERVICE_LOCK, lock.SERVICE_UNLOCK])
@pytest.mark.usefixtures("setup_state_lock_with_attribute")
async def test_actions_with_none_as_codeformat_ignores_code(
    menuai: menuai, action, calls: list[ServiceCall]
) -> None:
    """Test lock actions with supplied lock code."""
    menuai.states.async_set(TEST_STATE_ENTITY_ID, STATE_OFF)
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == LockState.UNLOCKED

    await menuai.services.async_call(
        lock.DOMAIN,
        action,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID, ATTR_CODE: "any code"},
    )
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data["action"] == action
    assert calls[0].data["caller"] == TEST_ENTITY_ID
    assert calls[0].data["code"] == "any code"


@pytest.mark.parametrize(
    ("count", "state_template", "attribute_template"),
    [
        (
            1,
            "{{ states.switch.test_state.state }}",
            "[12]{1",
        )
    ],
)
@pytest.mark.parametrize(
    ("style", "attribute"),
    [
        (ConfigurationStyle.LEGACY, "code_format_template"),
        (ConfigurationStyle.MODERN, "code_format"),
    ],
)
@pytest.mark.parametrize("action", [lock.SERVICE_LOCK, lock.SERVICE_UNLOCK])
@pytest.mark.usefixtures("setup_state_lock_with_attribute")
async def test_actions_with_invalid_regexp_as_codeformat_never_execute(
    menuai: menuai, action, calls: list[ServiceCall]
) -> None:
    """Test lock actions don't execute with invalid regexp."""
    menuai.states.async_set(TEST_STATE_ENTITY_ID, STATE_OFF)
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == LockState.UNLOCKED

    await menuai.services.async_call(
        lock.DOMAIN,
        action,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID, ATTR_CODE: "1"},
    )
    await menuai.services.async_call(
        lock.DOMAIN,
        action,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID, ATTR_CODE: "x"},
    )
    await menuai.services.async_call(
        lock.DOMAIN,
        action,
        {ATTR_ENTITY_ID: TEST_ENTITY_ID},
    )
    await menuai.async_block_till_done()

    assert len(calls) == 0


@pytest.mark.parametrize(
    ("count", "state_template"), [(1, "{{ states.input_select.test_state.state }}")]
)
@pytest.mark.parametrize(
    "style", [ConfigurationStyle.LEGACY, ConfigurationStyle.MODERN]
)
@pytest.mark.parametrize(
    "test_state", [LockState.UNLOCKING, LockState.LOCKING, LockState.JAMMED]
)
@pytest.mark.usefixtures("setup_state_lock")
async def test_lock_state(menuai: menuai, test_state) -> None:
    """Test value template."""
    menuai.states.async_set("input_select.test_state", test_state)
    await menuai.async_block_till_done()

    state = menuai.states.get(TEST_ENTITY_ID)
    assert state.state == test_state


@pytest.mark.parametrize(
    ("count", "state_template", "attribute_template"),
    [
        (
            1,
            "{{ states('switch.test_state') }}",
            "{{ is_state('availability_state.state', 'on') }}",
        )
    ],
)
@pytest.mark.parametrize(
    ("style", "attribute"),
    [
        (ConfigurationStyle.LEGACY, "availability_template"),
        (ConfigurationStyle.MODERN, "availability"),
    ],
)
@pytest.mark.usefixtures("setup_state_lock_with_attribute")
async def test_available_template_with_entities(menuai: menuai) -> None:
    """Test availability templates with values from other entities."""
    # When template returns true..
    menuai.states.async_set("availability_state.state", STATE_ON)
    await menuai.async_block_till_done()

    # Device State should not be unavailable
    assert menuai.states.get(TEST_ENTITY_ID).state != STATE_UNAVAILABLE

    # When Availability template returns false
    menuai.states.async_set("availability_state.state", STATE_OFF)
    await menuai.async_block_till_done()

    # device state should be unavailable
    assert menuai.states.get(TEST_ENTITY_ID).state == STATE_UNAVAILABLE


@pytest.mark.parametrize(
    ("count", "state_template", "attribute_template"),
    [
        (
            1,
            "{{ 1 + 1 }}",
            "{{ x - 12 }}",
        )
    ],
)
@pytest.mark.parametrize(
    ("style", "attribute"),
    [
        (ConfigurationStyle.LEGACY, "availability_template"),
        (ConfigurationStyle.MODERN, "availability"),
    ],
)
@pytest.mark.usefixtures("setup_state_lock_with_attribute")
async def test_invalid_availability_template_keeps_component_available(
    menuai: menuai, caplog_setup_text
) -> None:
    """Test that an invalid availability keeps the device available."""
    assert menuai.states.get(TEST_ENTITY_ID).state != STATE_UNAVAILABLE
    assert ("UndefinedError: 'x' is undefined") in caplog_setup_text


@pytest.mark.parametrize(("count", "domain"), [(1, lock.DOMAIN)])
@pytest.mark.parametrize(
    "config",
    [
        {
            lock.DOMAIN: {
                **OPTIMISTIC_LOCK_CONFIG,
                "name": "test_template_lock_01",
                "unique_id": "not-so-unique-anymore",
                "value_template": "{{ true }}",
            }
        },
    ],
)
@pytest.mark.usefixtures("start_ha")
async def test_legacy_unique_id(menuai: menuai) -> None:
    """Test unique_id option only creates one lock per id."""
    await setup.async_setup_component(
        menuai,
        lock.DOMAIN,
        {
            "lock": {
                **OPTIMISTIC_LOCK_CONFIG,
                "name": "test_template_lock_02",
                "unique_id": "not-so-unique-anymore",
                "value_template": "{{ false }}",
            },
        },
    )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all("lock")) == 1


async def test_modern_unique_id(menuai: menuai) -> None:
    """Test unique_id option only creates one cover per id."""
    config = {
        "template": {
            "lock": [
                {
                    "name": "test_template_lock_01",
                    "unique_id": "not-so-unique-anymore",
                    "state": "{{ false }}",
                    **OPTIMISTIC_LOCK,
                },
                {
                    "name": "test_template_lock_02",
                    "unique_id": "not-so-unique-anymore",
                    "state": "{{ false }}",
                    **OPTIMISTIC_LOCK,
                },
            ]
        }
    }

    with assert_setup_component(1, template.DOMAIN):
        assert await async_setup_component(
            menuai,
            template.DOMAIN,
            config,
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 1


async def test_nested_unique_id(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test a template unique_id propagates to lock unique_ids."""
    with assert_setup_component(1, template.DOMAIN):
        assert await async_setup_component(
            menuai,
            template.DOMAIN,
            {
                "template": {
                    "unique_id": "x",
                    "lock": [
                        {
                            **OPTIMISTIC_LOCK,
                            "name": "test_a",
                            "unique_id": "a",
                            "state": "{{ true }}",
                        },
                        {
                            **OPTIMISTIC_LOCK,
                            "name": "test_b",
                            "unique_id": "b",
                            "state": "{{ true }}",
                        },
                    ],
                },
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all("lock")) == 2

    entry = entity_registry.async_get("lock.test_a")
    assert entry
    assert entry.unique_id == "x-a"

    entry = entity_registry.async_get("lock.test_b")
    assert entry
    assert entry.unique_id == "x-b"


async def test_emtpy_action_config(menuai: menuai) -> None:
    """Test configuration with empty script."""
    with assert_setup_component(1, lock.DOMAIN):
        assert await setup.async_setup_component(
            menuai,
            lock.DOMAIN,
            {
                lock.DOMAIN: {
                    "platform": "template",
                    "value_template": "{{ 0 == 1 }}",
                    "lock": [],
                    "unlock": [],
                    "open": [],
                    "name": "test_template_lock",
                    "optimistic": True,
                },
            },
        )

    await menuai.async_block_till_done()
    await menuai.async_start()
    await menuai.async_block_till_done()

    state = menuai.states.get("lock.test_template_lock")
    assert state.attributes["supported_features"] == LockEntityFeature.OPEN

    await menuai.services.async_call(
        lock.DOMAIN,
        lock.SERVICE_UNLOCK,
        {ATTR_ENTITY_ID: "lock.test_template_lock"},
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("lock.test_template_lock")
    assert state.state == LockState.UNLOCKED

    await menuai.services.async_call(
        lock.DOMAIN,
        lock.SERVICE_LOCK,
        {ATTR_ENTITY_ID: "lock.test_template_lock"},
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("lock.test_template_lock")
    assert state.state == LockState.LOCKED
