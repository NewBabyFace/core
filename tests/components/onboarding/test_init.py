"""Tests for the init."""

from typing import Any
from unittest.mock import Mock, patch

from menuai.components import onboarding
from menuai.core import menuai
from menuai.setup import async_setup_component

from . import mock_storage

from tests.common import MockUser

# Temporarily: if auth not active, always set onboarded=True


async def test_not_setup_views_if_onboarded(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test if onboarding is done, we don't setup views."""
    mock_storage(menuai_storage, {"done": onboarding.STEPS})

    with patch("menuai.components.onboarding.views.async_setup") as mock_setup:
        assert await async_setup_component(menuai, "onboarding", {})

    assert len(mock_setup.mock_calls) == 0
    assert onboarding.DOMAIN not in menuai.data
    assert onboarding.async_is_onboarded(menuai)


async def test_setup_views_if_not_onboarded(menuai: menuai) -> None:
    """Test if onboarding is not done, we setup views."""
    with patch(
        "menuai.components.onboarding.views.async_setup",
    ) as mock_setup:
        assert await async_setup_component(menuai, "onboarding", {})

    assert len(mock_setup.mock_calls) == 1
    assert onboarding.DOMAIN in menuai.data

    assert not onboarding.async_is_onboarded(menuai)


async def test_is_onboarded() -> None:
    """Test the is onboarded function."""
    menuai = Mock()
    menuai.data = {}

    assert onboarding.async_is_onboarded(menuai)

    menuai.data[onboarding.DOMAIN] = onboarding.OnboardingData([], True, {"done": []})
    assert onboarding.async_is_onboarded(menuai)

    menuai.data[onboarding.DOMAIN] = onboarding.OnboardingData([], False, {"done": []})
    assert not onboarding.async_is_onboarded(menuai)


async def test_is_user_onboarded() -> None:
    """Test the is onboarded function."""
    menuai = Mock()
    menuai.data = {}

    assert onboarding.async_is_user_onboarded(menuai)

    menuai.data[onboarding.DOMAIN] = onboarding.OnboardingData([], True, {"done": []})
    assert onboarding.async_is_user_onboarded(menuai)

    menuai.data[onboarding.DOMAIN] = onboarding.OnboardingData(
        [], False, {"done": ["user"]}
    )
    assert onboarding.async_is_user_onboarded(menuai)

    menuai.data[onboarding.DOMAIN] = onboarding.OnboardingData([], False, {"done": []})
    assert not onboarding.async_is_user_onboarded(menuai)


async def test_having_owner_finishes_user_step(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """If owner user already exists, mark user step as complete."""
    MockUser(is_owner=True).add_to_menuai(menuai)

    with (
        patch("menuai.components.onboarding.views.async_setup") as mock_setup,
        patch.object(onboarding, "STEPS", [onboarding.STEP_USER]),
    ):
        assert await async_setup_component(menuai, "onboarding", {})

    assert len(mock_setup.mock_calls) == 0
    assert onboarding.DOMAIN not in menuai.data
    assert onboarding.async_is_onboarded(menuai)

    done = menuai_storage[onboarding.STORAGE_KEY]["data"]["done"]
    assert onboarding.STEP_USER in done


async def test_migration(menuai: menuai, menuai_storage: dict[str, Any]) -> None:
    """Test migrating onboarding to new version."""
    menuai_storage[onboarding.STORAGE_KEY] = {"version": 1, "data": {"done": ["user"]}}
    assert await async_setup_component(menuai, "onboarding", {})
    assert onboarding.async_is_onboarded(menuai)
