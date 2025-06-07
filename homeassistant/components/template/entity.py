"""Template entity base class."""

from collections.abc import Sequence
from typing import Any

from menuai.core import Context, menuai, callback
from menuai.helpers.entity import Entity
from menuai.helpers.script import Script, _VarsType
from menuai.helpers.template import TemplateStateFromEntityId


class AbstractTemplateEntity(Entity):
    """Actions linked to a template entity."""

    def __init__(self, menuai: menuai) -> None:
        """Initialize the entity."""

        self.menuai = menuai
        self._action_scripts: dict[str, Script] = {}

    @property
    def referenced_blueprint(self) -> str | None:
        """Return referenced blueprint or None."""
        raise NotImplementedError

    @callback
    def _render_script_variables(self) -> dict:
        """Render configured variables."""
        raise NotImplementedError

    def add_script(
        self,
        script_id: str,
        config: Sequence[dict[str, Any]],
        name: str,
        domain: str,
    ):
        """Add an action script."""

        self._action_scripts[script_id] = Script(
            self.menuai,
            config,
            f"{name} {script_id}",
            domain,
        )

    async def async_run_script(
        self,
        script: Script,
        *,
        run_variables: _VarsType | None = None,
        context: Context | None = None,
    ) -> None:
        """Run an action script."""
        if run_variables is None:
            run_variables = {}
        await script.async_run(
            run_variables={
                "this": TemplateStateFromEntityId(self.menuai, self.entity_id),
                **self._render_script_variables(),
                **run_variables,
            },
            context=context,
        )
