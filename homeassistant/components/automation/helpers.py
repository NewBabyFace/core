"""Helpers for automation integration."""

from menuai.components import blueprint
from menuai.const import SERVICE_RELOAD
from menuai.core import menuai, callback
from menuai.helpers.singleton import singleton

from .const import DOMAIN, LOGGER

DATA_BLUEPRINTS = "automation_blueprints"


def _blueprint_in_use(menuai: menuai, blueprint_path: str) -> bool:
    """Return True if any automation references the blueprint."""
    from . import automations_with_blueprint  # pylint: disable=import-outside-toplevel

    return len(automations_with_blueprint(menuai, blueprint_path)) > 0


async def _reload_blueprint_automations(
    menuai: menuai, blueprint_path: str
) -> None:
    """Reload all automations that rely on a specific blueprint."""
    await menuai.services.async_call(DOMAIN, SERVICE_RELOAD)


@singleton(DATA_BLUEPRINTS)
@callback
def async_get_blueprints(menuai: menuai) -> blueprint.DomainBlueprints:
    """Get automation blueprints."""
    # pylint: disable-next=import-outside-toplevel
    from .config import AUTOMATION_BLUEPRINT_SCHEMA

    return blueprint.DomainBlueprints(
        menuai,
        DOMAIN,
        LOGGER,
        _blueprint_in_use,
        _reload_blueprint_automations,
        AUTOMATION_BLUEPRINT_SCHEMA,
    )
