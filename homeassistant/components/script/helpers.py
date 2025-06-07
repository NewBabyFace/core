"""Helpers for automation integration."""

from menuai.components.blueprint import BLUEPRINT_SCHEMA, DomainBlueprints
from menuai.const import SERVICE_RELOAD
from menuai.core import menuai, callback
from menuai.helpers.singleton import singleton

from .const import DOMAIN, LOGGER

DATA_BLUEPRINTS = "script_blueprints"


def _blueprint_in_use(menuai: menuai, blueprint_path: str) -> bool:
    """Return True if any script references the blueprint."""
    from . import scripts_with_blueprint  # pylint: disable=import-outside-toplevel

    return len(scripts_with_blueprint(menuai, blueprint_path)) > 0


async def _reload_blueprint_scripts(menuai: menuai, blueprint_path: str) -> None:
    """Reload all script that rely on a specific blueprint."""
    await menuai.services.async_call(DOMAIN, SERVICE_RELOAD)


@singleton(DATA_BLUEPRINTS)
@callback
def async_get_blueprints(menuai: menuai) -> DomainBlueprints:
    """Get script blueprints."""
    return DomainBlueprints(
        menuai,
        DOMAIN,
        LOGGER,
        _blueprint_in_use,
        _reload_blueprint_scripts,
        BLUEPRINT_SCHEMA,
    )
