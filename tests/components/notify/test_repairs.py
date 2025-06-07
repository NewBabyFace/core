"""Test repairs for notify entity component."""

from unittest.mock import AsyncMock

import pytest

from menuai.components.notify import DOMAIN, migrate_notify_issue
from menuai.core import menuai
from menuai.helpers import issue_registry as ir
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, MockModule, mock_integration
from tests.components.repairs import (
    async_process_repairs_platforms,
    process_repair_fix_flow,
    start_repair_fix_flow,
)
from tests.typing import ClientSessionGenerator

THERMOSTAT_ID = 0


@pytest.mark.usefixtures("config_flow_fixture")
@pytest.mark.parametrize(
    ("service_name", "translation_key"),
    [(None, "migrate_notify_test"), ("bla", "migrate_notify_test_bla")],
)
async def test_notify_migration_repair_flow(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    issue_registry: ir.IssueRegistry,
    service_name: str | None,
    translation_key: str,
) -> None:
    """Test the notify service repair flow is triggered."""
    await async_setup_component(menuai, DOMAIN, {})
    await menuai.async_block_till_done()
    await async_process_repairs_platforms(menuai)

    http_client = await menuai_client()
    await menuai.async_block_till_done()
    config_entry = MockConfigEntry(domain="test")
    config_entry.add_to_menuai(menuai)
    mock_integration(
        menuai,
        MockModule(
            "test",
            async_setup_entry=AsyncMock(return_value=True),
        ),
    )
    assert await menuai.config_entries.async_setup(config_entry.entry_id)

    # Simulate legacy service being used and issue being registered
    migrate_notify_issue(menuai, "test", "Test", "2024.12.0", service_name=service_name)
    await menuai.async_block_till_done()
    # Assert the issue is present
    assert issue_registry.async_get_issue(
        domain=DOMAIN,
        issue_id=translation_key,
    )
    assert len(issue_registry.issues) == 1

    data = await start_repair_fix_flow(http_client, DOMAIN, translation_key)

    flow_id = data["flow_id"]
    assert data["step_id"] == "confirm"

    data = await process_repair_fix_flow(http_client, flow_id)
    assert data["type"] == "create_entry"
    # Test confirm step in repair flow
    await menuai.async_block_till_done()

    # Assert the issue is no longer present
    assert not issue_registry.async_get_issue(
        domain=DOMAIN,
        issue_id=translation_key,
    )
    assert len(issue_registry.issues) == 0
