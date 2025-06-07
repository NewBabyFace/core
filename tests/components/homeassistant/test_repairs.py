"""Test the menuai repairs module."""

from menuai.components.repairs import DOMAIN as REPAIRS_DOMAIN
from menuai.core import DOMAIN as menuai_DOMAIN, menuai
from menuai.helpers import issue_registry as ir
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry
from tests.components.repairs import (
    async_process_repairs_platforms,
    process_repair_fix_flow,
    start_repair_fix_flow,
)
from tests.typing import ClientSessionGenerator


async def test_integration_not_found_confirm_step(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test the integration_not_found issue confirm step."""
    assert await async_setup_component(menuai, menuai_DOMAIN, {})
    await menuai.async_block_till_done()
    assert await async_setup_component(menuai, REPAIRS_DOMAIN, {REPAIRS_DOMAIN: {}})
    await menuai.async_block_till_done()
    MockConfigEntry(domain="test1").add_to_menuai(menuai)
    assert await async_setup_component(menuai, "test1", {}) is False
    await menuai.async_block_till_done()
    entry1 = MockConfigEntry(domain="test1")
    entry1.add_to_menuai(menuai)
    entry2 = MockConfigEntry(domain="test1")
    entry2.add_to_menuai(menuai)
    issue_id = "integration_not_found.test1"

    await async_process_repairs_platforms(menuai)
    http_client = await menuai_client()

    issue = issue_registry.async_get_issue(menuai_DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_placeholders == {"domain": "test1"}

    data = await start_repair_fix_flow(http_client, menuai_DOMAIN, issue_id)

    flow_id = data["flow_id"]
    assert data["step_id"] == "init"
    assert data["description_placeholders"] == {"domain": "test1"}

    data = await process_repair_fix_flow(http_client, flow_id)

    assert data["type"] == "menu"

    # Apply fix
    data = await process_repair_fix_flow(
        http_client, flow_id, json={"next_step_id": "confirm"}
    )

    assert data["type"] == "create_entry"

    await menuai.async_block_till_done()

    assert menuai.config_entries.async_get_entry(entry1.entry_id) is None
    assert menuai.config_entries.async_get_entry(entry2.entry_id) is None

    # Assert the issue is resolved
    assert not issue_registry.async_get_issue(menuai_DOMAIN, issue_id)


async def test_integration_not_found_ignore_step(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test the integration_not_found issue ignore step."""
    assert await async_setup_component(menuai, menuai_DOMAIN, {})
    await menuai.async_block_till_done()
    assert await async_setup_component(menuai, REPAIRS_DOMAIN, {REPAIRS_DOMAIN: {}})
    await menuai.async_block_till_done()
    MockConfigEntry(domain="test1").add_to_menuai(menuai)
    assert await async_setup_component(menuai, "test1", {}) is False
    await menuai.async_block_till_done()
    entry1 = MockConfigEntry(domain="test1")
    entry1.add_to_menuai(menuai)
    issue_id = "integration_not_found.test1"

    await async_process_repairs_platforms(menuai)
    http_client = await menuai_client()

    issue = issue_registry.async_get_issue(menuai_DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_placeholders == {"domain": "test1"}

    data = await start_repair_fix_flow(http_client, menuai_DOMAIN, issue_id)

    flow_id = data["flow_id"]
    assert data["step_id"] == "init"
    assert data["description_placeholders"] == {"domain": "test1"}

    # Show menu
    data = await process_repair_fix_flow(http_client, flow_id)

    assert data["type"] == "menu"

    # Apply fix
    data = await process_repair_fix_flow(
        http_client, flow_id, json={"next_step_id": "ignore"}
    )

    assert data["type"] == "abort"
    assert data["reason"] == "issue_ignored"

    await menuai.async_block_till_done()

    assert menuai.config_entries.async_get_entry(entry1.entry_id)

    # Assert the issue is resolved
    issue = issue_registry.async_get_issue(menuai_DOMAIN, issue_id)
    assert issue is not None
    assert issue.dismissed_version is not None
