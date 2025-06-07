"""Test trigger template entity."""

import pytest

from menuai.components.template import trigger_entity
from menuai.components.template.coordinator import TriggerUpdateCoordinator
from menuai.const import CONF_ICON, CONF_NAME, CONF_STATE, STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.helpers import template
from menuai.helpers.trigger_template_entity import CONF_PICTURE

_ICON_TEMPLATE = 'mdi:o{{ "n" if value=="on" else "ff" }}'
_PICTURE_TEMPLATE = '/local/picture_o{{ "n" if value=="on" else "ff" }}'


class TestEntity(trigger_entity.TriggerEntity):
    """Test entity class."""

    __test__ = False
    extra_template_keys = (CONF_STATE,)

    @property
    def state(self) -> bool | None:
        """Return extra attributes."""
        return self._rendered.get(CONF_STATE)


async def test_reference_blueprints_is_none(menuai: menuai) -> None:
    """Test template entity requires menuai to be set before accepting templates."""
    coordinator = TriggerUpdateCoordinator(menuai, {})
    entity = trigger_entity.TriggerEntity(menuai, coordinator, {})

    assert entity.referenced_blueprint is None


async def test_template_state(menuai: menuai) -> None:
    """Test manual trigger template entity with a state."""
    config = {
        CONF_NAME: template.Template("test_entity", menuai),
        CONF_ICON: template.Template(_ICON_TEMPLATE, menuai),
        CONF_PICTURE: template.Template(_PICTURE_TEMPLATE, menuai),
        CONF_STATE: template.Template("{{ value == 'on' }}", menuai),
    }

    coordinator = TriggerUpdateCoordinator(menuai, {})
    entity = TestEntity(menuai, coordinator, config)
    entity.entity_id = "test.entity"

    coordinator._execute_update({"value": STATE_ON})
    entity._handle_coordinator_update()
    await menuai.async_block_till_done()

    assert entity.state == "True"
    assert entity.icon == "mdi:on"
    assert entity.entity_picture == "/local/picture_on"

    coordinator._execute_update({"value": STATE_OFF})
    entity._handle_coordinator_update()
    await menuai.async_block_till_done()

    assert entity.state == "False"
    assert entity.icon == "mdi:off"
    assert entity.entity_picture == "/local/picture_off"


async def test_bad_template_state(menuai: menuai) -> None:
    """Test manual trigger template entity with a state."""
    config = {
        CONF_NAME: template.Template("test_entity", menuai),
        CONF_ICON: template.Template(_ICON_TEMPLATE, menuai),
        CONF_PICTURE: template.Template(_PICTURE_TEMPLATE, menuai),
        CONF_STATE: template.Template("{{ x - 1 }}", menuai),
    }
    coordinator = TriggerUpdateCoordinator(menuai, {})
    entity = TestEntity(menuai, coordinator, config)
    entity.entity_id = "test.entity"

    coordinator._execute_update({"x": 1})
    entity._handle_coordinator_update()
    await menuai.async_block_till_done()

    assert entity.available is True
    assert entity.state == "0"
    assert entity.icon == "mdi:off"
    assert entity.entity_picture == "/local/picture_off"

    coordinator._execute_update({"value": STATE_OFF})
    entity._handle_coordinator_update()
    await menuai.async_block_till_done()

    assert entity.available is False
    assert entity.state is None
    assert entity.icon is None
    assert entity.entity_picture is None


async def test_template_state_syntax_error(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test manual trigger template entity when state render fails."""
    config = {
        CONF_NAME: template.Template("test_entity", menuai),
        CONF_ICON: template.Template(_ICON_TEMPLATE, menuai),
        CONF_PICTURE: template.Template(_PICTURE_TEMPLATE, menuai),
        CONF_STATE: template.Template("{{ incorrect ", menuai),
    }

    coordinator = TriggerUpdateCoordinator(menuai, {})
    entity = TestEntity(menuai, coordinator, config)
    entity.entity_id = "test.entity"

    coordinator._execute_update({"value": STATE_ON})
    entity._handle_coordinator_update()
    await menuai.async_block_till_done()

    assert f"Error rendering {CONF_STATE} template for test.entity" in caplog.text

    assert entity.state is None
    assert entity.icon is None
    assert entity.entity_picture is None


async def test_script_variables_from_coordinator(menuai: menuai) -> None:
    """Test script variables."""
    coordinator = TriggerUpdateCoordinator(menuai, {})
    entity = TestEntity(menuai, coordinator, {})

    assert entity._render_script_variables() == {}

    coordinator.data = {"run_variables": None}

    assert entity._render_script_variables() == {}

    coordinator._execute_update({"value": STATE_ON})

    assert entity._render_script_variables() == {"value": STATE_ON}
