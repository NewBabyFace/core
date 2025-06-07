"""Velbus services tests."""

from unittest.mock import AsyncMock

import pytest
import voluptuous as vol

from menuai.components.velbus.const import (
    CONF_CONFIG_ENTRY,
    CONF_INTERFACE,
    CONF_MEMO_TEXT,
    DOMAIN,
    SERVICE_CLEAR_CACHE,
    SERVICE_SCAN,
    SERVICE_SET_MEMO_TEXT,
    SERVICE_SYNC,
)
from menuai.const import CONF_ADDRESS
from menuai.core import menuai
from menuai.exceptions import ServiceValidationError
from menuai.helpers import issue_registry as ir

from . import init_integration

from tests.common import MockConfigEntry


async def test_global_services_with_interface(
    menuai: menuai,
    config_entry: MockConfigEntry,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test services directed at the bus with an interface parameter."""
    await init_integration(menuai, config_entry)

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SCAN,
        {CONF_INTERFACE: config_entry.data["port"]},
        blocking=True,
    )
    config_entry.runtime_data.controller.scan.assert_called_once_with()
    assert issue_registry.async_get_issue(DOMAIN, "deprecated_interface_parameter")

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SYNC,
        {CONF_INTERFACE: config_entry.data["port"]},
        blocking=True,
    )
    config_entry.runtime_data.controller.sync_clock.assert_called_once_with()

    # Test invalid interface
    with pytest.raises(vol.error.MultipleInvalid):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SCAN,
            {CONF_INTERFACE: "nonexistent"},
            blocking=True,
        )

    # Test missing interface
    with pytest.raises(vol.error.MultipleInvalid):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SCAN,
            {},
            blocking=True,
        )


async def test_global_survices_with_config_entry(
    menuai: menuai,
    config_entry: MockConfigEntry,
) -> None:
    """Test services directed at the bus with a config_entry."""
    await init_integration(menuai, config_entry)

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SCAN,
        {CONF_CONFIG_ENTRY: config_entry.entry_id},
        blocking=True,
    )
    config_entry.runtime_data.controller.scan.assert_called_once_with()

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SYNC,
        {CONF_CONFIG_ENTRY: config_entry.entry_id},
        blocking=True,
    )
    config_entry.runtime_data.controller.sync_clock.assert_called_once_with()

    # Test invalid interface
    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SCAN,
            {CONF_CONFIG_ENTRY: "nonexistent"},
            blocking=True,
        )

    # Test missing interface
    with pytest.raises(vol.error.MultipleInvalid):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SCAN,
            {},
            blocking=True,
        )


async def test_set_memo_text(
    menuai: menuai,
    config_entry: MockConfigEntry,
    controller: AsyncMock,
) -> None:
    """Test the set_memo_text service."""
    await init_integration(menuai, config_entry)

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SET_MEMO_TEXT,
        {
            CONF_CONFIG_ENTRY: config_entry.entry_id,
            CONF_MEMO_TEXT: "Test",
            CONF_ADDRESS: 1,
        },
        blocking=True,
    )
    config_entry.runtime_data.controller.get_module(
        1
    ).set_memo_text.assert_called_once_with("Test")

    # Test with unfound module
    controller.return_value.get_module.return_value = None
    with pytest.raises(ServiceValidationError, match="Module not found"):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_SET_MEMO_TEXT,
            {
                CONF_CONFIG_ENTRY: config_entry.entry_id,
                CONF_MEMO_TEXT: "Test",
                CONF_ADDRESS: 2,
            },
            blocking=True,
        )


async def test_clear_cache(
    menuai: menuai,
    config_entry: MockConfigEntry,
) -> None:
    """Test the clear_cache service."""
    await init_integration(menuai, config_entry)

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_CLEAR_CACHE,
        {CONF_CONFIG_ENTRY: config_entry.entry_id},
        blocking=True,
    )
    config_entry.runtime_data.controller.scan.assert_called_once_with()

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_CLEAR_CACHE,
        {CONF_CONFIG_ENTRY: config_entry.entry_id, CONF_ADDRESS: 1},
        blocking=True,
    )
    assert config_entry.runtime_data.controller.scan.call_count == 2
