"""Tensorflow test."""

from unittest.mock import Mock, patch

from menuai.components.image_processing import DOMAIN as IMAGE_PROCESSING_DOMAINN
from menuai.components.tensorflow import CONF_GRAPH, DOMAIN
from menuai.const import CONF_ENTITY_ID, CONF_MODEL, CONF_PLATFORM, CONF_SOURCE
from menuai.core import DOMAIN as menuai_DOMAIN, menuai
from menuai.helpers import issue_registry as ir
from menuai.setup import async_setup_component


@patch.dict("sys.modules", tensorflow=Mock())
async def test_repair_issue_is_created(
    menuai: menuai,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test repair issue is created."""
    assert await async_setup_component(
        menuai,
        IMAGE_PROCESSING_DOMAINN,
        {
            IMAGE_PROCESSING_DOMAINN: [
                {
                    CONF_PLATFORM: DOMAIN,
                    CONF_SOURCE: [
                        {CONF_ENTITY_ID: "camera.test_camera"},
                    ],
                    CONF_MODEL: {
                        CONF_GRAPH: ".",
                    },
                }
            ],
        },
    )
    await menuai.async_block_till_done()
    assert (
        menuai_DOMAIN,
        f"deprecated_system_packages_yaml_integration_{DOMAIN}",
    ) in issue_registry.issues
