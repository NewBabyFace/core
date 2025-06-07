"""Decora component tests."""

from unittest.mock import Mock, patch

from menuai.components.decora import DOMAIN
from menuai.components.light import DOMAIN as PLATFORM_DOMAIN
from menuai.const import CONF_PLATFORM
from menuai.core import DOMAIN as menuai_DOMAIN, menuai
from menuai.helpers import issue_registry as ir
from menuai.setup import async_setup_component


@patch.dict("sys.modules", {"bluepy": Mock(), "bluepy.btle": Mock(), "decora": Mock()})
async def test_repair_issue_is_created(
    menuai: menuai,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test repair issue is created."""
    assert await async_setup_component(
        menuai,
        PLATFORM_DOMAIN,
        {
            PLATFORM_DOMAIN: [
                {
                    CONF_PLATFORM: DOMAIN,
                }
            ],
        },
    )
    await menuai.async_block_till_done()
    assert (
        menuai_DOMAIN,
        f"deprecated_system_packages_yaml_integration_{DOMAIN}",
    ) in issue_registry.issues
