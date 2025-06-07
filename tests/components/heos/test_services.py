"""Tests for the services module."""

from pyheos import CommandAuthenticationError, HeosError
import pytest

from menuai.components.heos.const import (
    ATTR_PASSWORD,
    ATTR_USERNAME,
    DOMAIN,
    SERVICE_SIGN_IN,
    SERVICE_SIGN_OUT,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError, ServiceValidationError

from . import MockHeos

from tests.common import MockConfigEntry


async def test_sign_in(
    menuai: menuai, config_entry: MockConfigEntry, controller: MockHeos
) -> None:
    """Test the sign-in service."""
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SIGN_IN,
        {ATTR_USERNAME: "test@test.com", ATTR_PASSWORD: "password"},
        blocking=True,
    )

    controller.sign_in.assert_called_once_with("test@test.com", "password")


async def test_sign_in_failed(
    menuai: menuai, config_entry: MockConfigEntry, controller: MockHeos
) -> None:
    """Test sign-in service logs error when not connected."""
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)

    controller.sign_in.side_effect = CommandAuthenticationError(
        "", "Invalid credentials", 6
    )

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SIGN_IN,
            {ATTR_USERNAME: "test@test.com", ATTR_PASSWORD: "password"},
            blocking=True,
        )

    controller.sign_in.assert_called_once_with("test@test.com", "password")


async def test_sign_in_unknown_error(
    menuai: menuai, config_entry: MockConfigEntry, controller: MockHeos
) -> None:
    """Test sign-in service logs error for failure."""
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)

    controller.sign_in.side_effect = HeosError()

    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SIGN_IN,
            {ATTR_USERNAME: "test@test.com", ATTR_PASSWORD: "password"},
            blocking=True,
        )

    controller.sign_in.assert_called_once_with("test@test.com", "password")


async def test_sign_in_not_loaded_raises(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test the sign-in service when entry not loaded raises exception."""
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    assert await menuai.config_entries.async_unload(config_entry.entry_id)

    with pytest.raises(menuaiError, match="The HEOS integration is not loaded"):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SIGN_IN,
            {ATTR_USERNAME: "test@test.com", ATTR_PASSWORD: "password"},
            blocking=True,
        )


async def test_sign_out(
    menuai: menuai, config_entry: MockConfigEntry, controller: MockHeos
) -> None:
    """Test the sign-out service."""
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)

    await menuai.services.async_call(DOMAIN, SERVICE_SIGN_OUT, {}, blocking=True)

    assert controller.sign_out.call_count == 1


async def test_sign_out_not_loaded_raises(
    menuai: menuai, config_entry: MockConfigEntry
) -> None:
    """Test the sign-out service when entry not loaded raises exception."""
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    assert await menuai.config_entries.async_unload(config_entry.entry_id)

    with pytest.raises(menuaiError, match="The HEOS integration is not loaded"):
        await menuai.services.async_call(DOMAIN, SERVICE_SIGN_OUT, {}, blocking=True)


async def test_sign_out_unknown_error(
    menuai: menuai, config_entry: MockConfigEntry, controller: MockHeos
) -> None:
    """Test the sign-out service."""
    config_entry.add_to_menuai(menuai)
    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    controller.sign_out.side_effect = HeosError()

    with pytest.raises(menuaiError):
        await menuai.services.async_call(DOMAIN, SERVICE_SIGN_OUT, {}, blocking=True)

    assert controller.sign_out.call_count == 1
