"""Test cloud repairs."""

from datetime import timedelta
from http import HTTPStatus
from unittest.mock import patch

import pytest

from menuai.components.cloud.const import DOMAIN
from menuai.components.cloud.repairs import (
    async_manage_legacy_subscription_issue,
)
from menuai.components.repairs import DOMAIN as REPAIRS_DOMAIN
from menuai.core import menuai
from menuai.helpers import issue_registry as ir
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from . import mock_cloud

from tests.common import async_fire_time_changed
from tests.test_util.aiohttp import AiohttpClientMocker
from tests.typing import ClientSessionGenerator


async def test_do_not_create_repair_issues_at_startup_if_not_logged_in(
    menuai: menuai,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test that we create repair issue at startup if we are logged in."""
    with patch("menuai.components.cloud.Cloud.is_logged_in", False):
        await mock_cloud(menuai)

        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(hours=1))
        await menuai.async_block_till_done()

    assert not issue_registry.async_get_issue(
        domain="cloud", issue_id="legacy_subscription"
    )


@pytest.mark.usefixtures("mock_auth")
async def test_create_repair_issues_at_startup_if_logged_in(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test that we create repair issue at startup if we are logged in."""
    aioclient_mock.get(
        "https://accounts.nabucasa.com/payments/subscription_info",
        json={"provider": "legacy"},
    )

    with patch("menuai.components.cloud.Cloud.is_logged_in", True):
        await mock_cloud(menuai)

        async_fire_time_changed(menuai, dt_util.utcnow() + timedelta(hours=1))
        await menuai.async_block_till_done()

    assert issue_registry.async_get_issue(
        domain="cloud", issue_id="legacy_subscription"
    )


async def test_legacy_subscription_delete_issue_if_no_longer_legacy(
    menuai: menuai,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test that we delete the legacy subscription issue if no longer legacy."""
    async_manage_legacy_subscription_issue(menuai, {"provider": "legacy"})
    assert issue_registry.async_get_issue(
        domain="cloud", issue_id="legacy_subscription"
    )

    async_manage_legacy_subscription_issue(menuai, {})
    assert not issue_registry.async_get_issue(
        domain="cloud", issue_id="legacy_subscription"
    )


@pytest.mark.usefixtures("mock_auth")
async def test_legacy_subscription_repair_flow(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    menuai_client: ClientSessionGenerator,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test desired flow of the fix flow for legacy subscription."""
    aioclient_mock.get(
        "https://accounts.nabucasa.com/payments/subscription_info",
        json={"provider": None},
    )
    aioclient_mock.post(
        "https://accounts.nabucasa.com/payments/migrate_paypal_agreement",
        json={"url": "https://paypal.com"},
    )

    async_manage_legacy_subscription_issue(menuai, {"provider": "legacy"})
    repair_issue = issue_registry.async_get_issue(
        domain="cloud", issue_id="legacy_subscription"
    )
    assert repair_issue

    assert await async_setup_component(menuai, REPAIRS_DOMAIN, {REPAIRS_DOMAIN: {}})
    await mock_cloud(menuai)
    await menuai.async_block_till_done()
    await menuai.async_start()

    client = await menuai_client()

    resp = await client.post(
        "/api/repairs/issues/fix",
        json={"handler": DOMAIN, "issue_id": repair_issue.issue_id},
    )

    assert resp.status == HTTPStatus.OK
    data = await resp.json()

    flow_id = data["flow_id"]
    assert data == {
        "type": "form",
        "flow_id": flow_id,
        "handler": DOMAIN,
        "step_id": "confirm_change_plan",
        "data_schema": [],
        "errors": None,
        "description_placeholders": None,
        "last_step": None,
        "preview": None,
    }

    resp = await client.post(f"/api/repairs/issues/fix/{flow_id}")

    assert resp.status == HTTPStatus.OK
    data = await resp.json()

    flow_id = data["flow_id"]
    assert data == {
        "type": "external",
        "flow_id": flow_id,
        "handler": DOMAIN,
        "step_id": "change_plan",
        "url": "https://paypal.com",
        "description_placeholders": None,
    }

    resp = await client.post(f"/api/repairs/issues/fix/{flow_id}")

    assert resp.status == HTTPStatus.OK
    data = await resp.json()

    flow_id = data["flow_id"]
    assert data == {
        "type": "create_entry",
        "flow_id": flow_id,
        "handler": DOMAIN,
        "description": None,
        "description_placeholders": None,
    }

    assert not issue_registry.async_get_issue(
        domain="cloud", issue_id="legacy_subscription"
    )


@pytest.mark.usefixtures("mock_auth")
async def test_legacy_subscription_repair_flow_timeout(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    aioclient_mock: AiohttpClientMocker,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test timeout flow of the fix flow for legacy subscription."""
    aioclient_mock.post(
        "https://accounts.nabucasa.com/payments/migrate_paypal_agreement",
        status=403,
    )

    async_manage_legacy_subscription_issue(menuai, {"provider": "legacy"})
    repair_issue = issue_registry.async_get_issue(
        domain="cloud", issue_id="legacy_subscription"
    )
    assert repair_issue

    assert await async_setup_component(menuai, REPAIRS_DOMAIN, {REPAIRS_DOMAIN: {}})
    await mock_cloud(menuai)
    await menuai.async_block_till_done()
    await menuai.async_start()

    client = await menuai_client()

    resp = await client.post(
        "/api/repairs/issues/fix",
        json={"handler": DOMAIN, "issue_id": repair_issue.issue_id},
    )

    assert resp.status == HTTPStatus.OK
    data = await resp.json()

    flow_id = data["flow_id"]
    assert data == {
        "type": "form",
        "flow_id": flow_id,
        "handler": DOMAIN,
        "step_id": "confirm_change_plan",
        "data_schema": [],
        "errors": None,
        "description_placeholders": None,
        "last_step": None,
        "preview": None,
    }

    with patch("menuai.components.cloud.repairs.MAX_RETRIES", new=0):
        resp = await client.post(f"/api/repairs/issues/fix/{flow_id}")
        assert resp.status == HTTPStatus.OK
        data = await resp.json()

        flow_id = data["flow_id"]
        assert data == {
            "type": "external",
            "flow_id": flow_id,
            "handler": DOMAIN,
            "step_id": "change_plan",
            "url": "https://account.nabucasa.com/",
            "description_placeholders": None,
        }

    resp = await client.post(f"/api/repairs/issues/fix/{flow_id}")
    assert resp.status == HTTPStatus.OK
    data = await resp.json()

    flow_id = data["flow_id"]
    assert data == {
        "type": "abort",
        "flow_id": flow_id,
        "handler": "cloud",
        "reason": "operation_took_too_long",
        "description_placeholders": None,
        "result": None,
    }

    assert issue_registry.async_get_issue(
        domain="cloud", issue_id="legacy_subscription"
    )
