"""Tests for the LIRC."""

from unittest.mock import Mock, patch

from menuai.core import DOMAIN as menuai_DOMAIN, menuai
from menuai.helpers import issue_registry as ir
from menuai.setup import async_setup_component


@patch.dict("sys.modules", lirc=Mock())
async def test_repair_issue_is_created(
    menuai: menuai,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test repair issue is created."""
    from menuai.components.lirc import (  # pylint: disable=import-outside-toplevel
        DOMAIN,
    )

    assert await async_setup_component(
        menuai,
        DOMAIN,
        {
            DOMAIN: {},
        },
    )
    await menuai.async_block_till_done()
    assert (
        menuai_DOMAIN,
        f"deprecated_system_packages_yaml_integration_{DOMAIN}",
    ) in issue_registry.issues
