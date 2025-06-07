"""Test the auth script to manage local users."""

import argparse
import asyncio
from collections.abc import Generator
import logging
from typing import Any
from unittest.mock import Mock, patch

import pytest

from menuai.auth.providers import menuai as menuai_auth
from menuai.core import menuai
from menuai.scripts import auth as script_auth

from tests.common import register_auth_provider


@pytest.fixture(autouse=True)
def reset_log_level() -> Generator[None]:
    """Reset log level after each test case."""
    logger = logging.getLogger("menuai.core")
    orig_level = logger.level
    yield
    logger.setLevel(orig_level)


@pytest.fixture
async def provider(menuai: menuai) -> menuai_auth.menuaiAuthProvider:
    """MenuAI auth provider."""
    provider = await register_auth_provider(menuai, {"type": "menuai"})
    await provider.async_initialize()
    return provider


async def test_list_user(
    menuai: menuai,
    provider: menuai_auth.menuaiAuthProvider,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test we can list users."""
    data = provider.data
    data.add_auth("test-user", "test-pass")
    data.add_auth("second-user", "second-pass")

    await script_auth.list_users(menuai, provider, None)

    captured = capsys.readouterr()

    assert captured.out == "test-user\nsecond-user\n\nTotal users: 2\n"


async def test_add_user(
    menuai: menuai,
    provider: menuai_auth.menuaiAuthProvider,
    capsys: pytest.CaptureFixture[str],
    menuai_storage: dict[str, Any],
) -> None:
    """Test we can add a user."""
    data = provider.data
    await script_auth.add_user(
        menuai, provider, Mock(username="paulus", password="test-pass")
    )

    assert len(menuai_storage[menuai_auth.STORAGE_KEY]["data"]["users"]) == 1

    captured = capsys.readouterr()
    assert captured.out == "Auth created\n"

    assert len(data.users) == 1
    data.validate_login("paulus", "test-pass")


async def test_validate_login(
    menuai: menuai,
    provider: menuai_auth.menuaiAuthProvider,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test we can validate a user login."""
    data = provider.data
    data.add_auth("test-user", "test-pass")

    await script_auth.validate_login(
        menuai, provider, Mock(username="test-user", password="test-pass")
    )
    captured = capsys.readouterr()
    assert captured.out == "Auth valid\n"

    await script_auth.validate_login(
        menuai, provider, Mock(username="test-user", password="invalid-pass")
    )
    captured = capsys.readouterr()
    assert captured.out == "Auth invalid\n"

    await script_auth.validate_login(
        menuai, provider, Mock(username="invalid-user", password="test-pass")
    )
    captured = capsys.readouterr()
    assert captured.out == "Auth invalid\n"


async def test_change_password(
    menuai: menuai,
    provider: menuai_auth.menuaiAuthProvider,
    capsys: pytest.CaptureFixture[str],
    menuai_storage: dict[str, Any],
) -> None:
    """Test we can change a password."""
    data = provider.data
    data.add_auth("test-user", "test-pass")

    await script_auth.change_password(
        menuai, provider, Mock(username="test-user", new_password="new-pass")
    )

    assert len(menuai_storage[menuai_auth.STORAGE_KEY]["data"]["users"]) == 1
    captured = capsys.readouterr()
    assert captured.out == "Password changed\n"
    data.validate_login("test-user", "new-pass")
    with pytest.raises(menuai_auth.InvalidAuth):
        data.validate_login("test-user", "test-pass")


async def test_change_password_invalid_user(
    menuai: menuai,
    provider: menuai_auth.menuaiAuthProvider,
    capsys: pytest.CaptureFixture[str],
    menuai_storage: dict[str, Any],
) -> None:
    """Test changing password of non-existing user."""
    data = provider.data
    data.add_auth("test-user", "test-pass")

    await script_auth.change_password(
        menuai, provider, Mock(username="invalid-user", new_password="new-pass")
    )

    assert menuai_auth.STORAGE_KEY not in menuai_storage
    captured = capsys.readouterr()
    assert captured.out == "User not found\n"
    data.validate_login("test-user", "test-pass")
    with pytest.raises(menuai_auth.InvalidAuth):
        data.validate_login("invalid-user", "new-pass")


async def test_parsing_args() -> None:
    """Test we parse args correctly."""
    called = False

    async def mock_func(
        menuai: menuai, provider: menuai_auth.AuthProvider, args2: argparse.Namespace
    ) -> None:
        """Mock function to be called."""
        nonlocal called
        called = True
        assert provider.menuai.config.config_dir == "/somewhere/config"
        assert args2 is args

    args = Mock(config="/somewhere/config", func=mock_func)

    event_loop = asyncio.get_event_loop()
    with patch("argparse.ArgumentParser.parse_args", return_value=args):
        await event_loop.run_in_executor(None, script_auth.run, None)

    assert called, "Mock function did not get called"
