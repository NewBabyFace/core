"""Trigger entity."""

from __future__ import annotations

from typing import Any

from menuai.const import CONF_STATE
from menuai.core import menuai, callback
from menuai.helpers.template import _SENTINEL
from menuai.helpers.trigger_template_entity import TriggerBaseEntity
from menuai.helpers.update_coordinator import CoordinatorEntity

from . import TriggerUpdateCoordinator
from .entity import AbstractTemplateEntity


class TriggerEntity(  # pylint: disable=menuai-enforce-class-module
    TriggerBaseEntity,
    CoordinatorEntity[TriggerUpdateCoordinator],
    AbstractTemplateEntity,
):
    """Template entity based on trigger data."""

    def __init__(
        self,
        menuai: menuai,
        coordinator: TriggerUpdateCoordinator,
        config: dict,
    ) -> None:
        """Initialize the entity."""
        CoordinatorEntity.__init__(self, coordinator)
        TriggerBaseEntity.__init__(self, menuai, config)
        AbstractTemplateEntity.__init__(self, menuai)

        self._state_render_error = False

    async def async_added_to_menuai(self) -> None:
        """Handle being added to MenuAI."""
        await super().async_added_to_menuai()
        if self.coordinator.data is not None:
            self._process_data()

    def _set_unique_id(self, unique_id: str | None) -> None:
        """Set unique id."""
        if unique_id and self.coordinator.unique_id:
            self._unique_id = f"{self.coordinator.unique_id}-{unique_id}"
        else:
            self._unique_id = unique_id

    @property
    def referenced_blueprint(self) -> str | None:
        """Return referenced blueprint or None."""
        return self.coordinator.referenced_blueprint

    @property
    def available(self) -> bool:
        """Return availability of the entity."""
        if self._state_render_error:
            return False

        return super().available

    @callback
    def _render_script_variables(self) -> dict:
        """Render configured variables."""
        if self.coordinator.data is None:
            return {}
        return self.coordinator.data["run_variables"] or {}

    def _render_templates(self, variables: dict[str, Any]) -> None:
        """Render templates."""
        self._state_render_error = False
        rendered = dict(self._static_rendered)

        # If state fails to render, the entity should go unavailable. Render the
        # state as a simple template because the result should always be a string or None.
        if CONF_STATE in self._to_render_simple:
            if (
                result := self._render_single_template(CONF_STATE, variables)
            ) is _SENTINEL:
                self._rendered = self._static_rendered
                self._state_render_error = True
                return

            rendered[CONF_STATE] = result

        self._render_single_templates(rendered, variables, [CONF_STATE])
        self._render_attributes(rendered, variables)
        self._rendered = rendered

    @callback
    def _process_data(self) -> None:
        """Process new data."""

        variables = self._template_variables(self.coordinator.data["run_variables"])
        if self._render_availability_template(variables):
            self._render_templates(variables)

        self.async_set_context(self.coordinator.data["context"])

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._process_data()
        self.async_write_ha_state()
