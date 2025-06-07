"""Provide configuration end points for scripts."""

from __future__ import annotations

from typing import Any

from menuai.components.script import DOMAIN as SCRIPT_DOMAIN
from menuai.components.script.config import async_validate_config_item
from menuai.config import SCRIPT_CONFIG_PATH
from menuai.const import SERVICE_RELOAD
from menuai.core import menuai, callback
from menuai.helpers import config_validation as cv, entity_registry as er

from .const import ACTION_DELETE
from .view import EditKeyBasedConfigView


@callback
def async_setup(menuai: menuai) -> bool:
    """Set up the script config API."""

    async def hook(action: str, config_key: str) -> None:
        """post_write_hook for Config View that reloads scripts."""
        if action != ACTION_DELETE:
            await menuai.services.async_call(SCRIPT_DOMAIN, SERVICE_RELOAD)
            return

        ent_reg = er.async_get(menuai)

        entity_id = ent_reg.async_get_entity_id(
            SCRIPT_DOMAIN, SCRIPT_DOMAIN, config_key
        )

        if entity_id is None:
            return

        ent_reg.async_remove(entity_id)

    menuai.http.register_view(
        EditScriptConfigView(
            SCRIPT_DOMAIN,
            "config",
            SCRIPT_CONFIG_PATH,
            cv.slug,
            post_write_hook=hook,
            data_validator=async_validate_config_item,
        )
    )
    return True


class EditScriptConfigView(EditKeyBasedConfigView):
    """Edit script config."""

    def _write_value(
        self,
        menuai: menuai,
        data: dict[str, dict[str, Any]],
        config_key: str,
        new_value: dict[str, Any],
    ) -> None:
        """Set value."""
        data[config_key] = new_value
