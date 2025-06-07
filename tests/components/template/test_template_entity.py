"""Test template entity."""

import pytest

from menuai.components.template import template_entity
from menuai.core import menuai
from menuai.helpers import template


async def test_template_entity_requires_menuai_set(menuai: menuai) -> None:
    """Test template entity requires menuai to be set before accepting templates."""
    entity = template_entity.TemplateEntity(None)

    with pytest.raises(ValueError, match="^menuai cannot be None"):
        entity.add_template_attribute("_hello", template.Template("Hello"))

    entity.menuai = object()
    with pytest.raises(ValueError, match="^template.menuai cannot be None"):
        entity.add_template_attribute("_hello", template.Template("Hello", None))

    tpl_with_menuai = template.Template("Hello", entity.menuai)
    entity.add_template_attribute("_hello", tpl_with_menuai)

    assert len(entity._template_attrs.get(tpl_with_menuai, [])) == 1
