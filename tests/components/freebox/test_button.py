"""Tests for the Freebox buttons."""

from unittest.mock import ANY, AsyncMock, Mock, patch

from pytest_unordered import unordered

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai

from .common import setup_platform


async def test_reboot(menuai: menuai, router: Mock) -> None:
    """Test reboot button."""
    entry = await setup_platform(menuai, BUTTON_DOMAIN)

    assert menuai.config_entries.async_entries() == unordered([entry, ANY])

    assert router.call_count == 1
    assert router().open.call_count == 1

    with patch(
        "menuai.components.freebox.router.FreeboxRouter.reboot"
    ) as mock_service:
        mock_service.assert_not_called()
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            service_data={
                ATTR_ENTITY_ID: "button.reboot_freebox",
            },
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_service.assert_called_once()


async def test_mark_calls_as_read(menuai: menuai, router: Mock) -> None:
    """Test mark calls as read button."""
    entry = await setup_platform(menuai, BUTTON_DOMAIN)

    assert menuai.config_entries.async_entries() == unordered([entry, ANY])

    assert router.call_count == 1
    assert router().open.call_count == 1

    with patch(
        "menuai.components.freebox.router.FreeboxRouter.call"
    ) as mock_service:
        mock_service.mark_calls_log_as_read = AsyncMock()
        mock_service.mark_calls_log_as_read.assert_not_called()
        await menuai.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            service_data={
                ATTR_ENTITY_ID: "button.mark_calls_as_read",
            },
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_service.mark_calls_log_as_read.assert_called_once()
