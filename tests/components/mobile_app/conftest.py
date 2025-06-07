"""Tests for mobile_app component."""

from http import HTTPStatus
from typing import Any

from aiohttp.test_utils import TestClient
import pytest

from menuai.components.mobile_app.const import DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from .const import REGISTER, REGISTER_CLEARTEXT

from tests.typing import ClientSessionGenerator


@pytest.fixture
async def create_registrations(
    menuai: menuai, webhook_client: TestClient
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return two new registrations."""
    await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    enc_reg = await webhook_client.post("/api/mobile_app/registrations", json=REGISTER)

    assert enc_reg.status == HTTPStatus.CREATED
    enc_reg_json = await enc_reg.json()

    clear_reg = await webhook_client.post(
        "/api/mobile_app/registrations", json=REGISTER_CLEARTEXT
    )

    assert clear_reg.status == HTTPStatus.CREATED
    clear_reg_json = await clear_reg.json()

    await menuai.async_block_till_done()

    return (enc_reg_json, clear_reg_json)


@pytest.fixture
async def push_registration(menuai: menuai, webhook_client: TestClient):
    """Return registration with push notifications enabled."""
    await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})

    enc_reg = await webhook_client.post(
        "/api/mobile_app/registrations",
        json={
            **REGISTER,
            "app_data": {
                "push_url": "http://localhost/mock-push",
                "push_token": "abcd",
            },
        },
    )

    assert enc_reg.status == HTTPStatus.CREATED
    return await enc_reg.json()


@pytest.fixture
async def webhook_client(
    menuai: menuai, menuai_client: ClientSessionGenerator
) -> TestClient:
    """Provide an authenticated client for mobile_app to use."""
    await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()
    return await menuai_client()


@pytest.fixture(autouse=True)
async def setup_ws(menuai: menuai) -> None:
    """Configure the websocket_api component."""
    assert await async_setup_component(menuai, "repairs", {})
    assert await async_setup_component(menuai, "websocket_api", {})
    await menuai.async_block_till_done()
