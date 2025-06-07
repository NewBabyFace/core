"""Helpers for template integration."""

import logging

from menuai.components import blueprint
from menuai.const import SERVICE_RELOAD
from menuai.core import menuai, callback
from menuai.helpers.entity_platform import async_get_platforms
from menuai.helpers.singleton import singleton

from .const import DOMAIN
from .entity import AbstractTemplateEntity

DATA_BLUEPRINTS = "template_blueprints"

LOGGER = logging.getLogger(__name__)


@callback
def templates_with_blueprint(menuai: menuai, blueprint_path: str) -> list[str]:
    """Return all template entity ids that reference the blueprint."""
    return [
        entity_id
        for platform in async_get_platforms(menuai, DOMAIN)
        for entity_id, template_entity in platform.entities.items()
        if isinstance(template_entity, AbstractTemplateEntity)
        and template_entity.referenced_blueprint == blueprint_path
    ]


@callback
def blueprint_in_template(menuai: menuai, entity_id: str) -> str | None:
    """Return the blueprint the template entity is based on or None."""
    for platform in async_get_platforms(menuai, DOMAIN):
        if isinstance(
            (template_entity := platform.entities.get(entity_id)),
            AbstractTemplateEntity,
        ):
            return template_entity.referenced_blueprint
    return None


def _blueprint_in_use(menuai: menuai, blueprint_path: str) -> bool:
    """Return True if any template references the blueprint."""
    return len(templates_with_blueprint(menuai, blueprint_path)) > 0


async def _reload_blueprint_templates(menuai: menuai, blueprint_path: str) -> None:
    """Reload all templates that rely on a specific blueprint."""
    await menuai.services.async_call(DOMAIN, SERVICE_RELOAD)


@singleton(DATA_BLUEPRINTS)
@callback
def async_get_blueprints(menuai: menuai) -> blueprint.DomainBlueprints:
    """Get template blueprints."""
    # pylint: disable-next=import-outside-toplevel
    from .config import TEMPLATE_BLUEPRINT_SCHEMA

    return blueprint.DomainBlueprints(
        menuai,
        DOMAIN,
        LOGGER,
        _blueprint_in_use,
        _reload_blueprint_templates,
        TEMPLATE_BLUEPRINT_SCHEMA,
    )
