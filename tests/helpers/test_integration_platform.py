"""Test integration platform helpers."""

from collections.abc import Callable
from types import ModuleType
from typing import Any
from unittest.mock import Mock, patch

import pytest

from menuai import loader
from menuai.const import EVENT_COMPONENT_LOADED
from menuai.core import menuai, callback
from menuai.exceptions import menuaiError
from menuai.helpers.integration_platform import (
    async_process_integration_platforms,
)
from menuai.setup import ATTR_COMPONENT

from tests.common import mock_platform


async def test_process_integration_platforms_with_wait(menuai: menuai) -> None:
    """Test processing integrations."""
    loaded_platform = Mock()
    mock_platform(menuai, "loaded.platform_to_check", loaded_platform)
    menuai.config.components.add("loaded")

    event_platform = Mock()
    mock_platform(menuai, "event.platform_to_check", event_platform)

    processed = []

    async def _process_platform(
        menuai: menuai, domain: str, platform: Any
    ) -> None:
        """Process platform."""
        processed.append((domain, platform))

    await async_process_integration_platforms(
        menuai, "platform_to_check", _process_platform, wait_for_platforms=True
    )
    # No block till done here, we want to make sure it waits for the platform

    assert len(processed) == 1
    assert processed[0][0] == "loaded"
    assert processed[0][1] == loaded_platform

    menuai.bus.async_fire(EVENT_COMPONENT_LOADED, {ATTR_COMPONENT: "event"})
    await menuai.async_block_till_done()

    assert len(processed) == 2
    assert processed[1][0] == "event"
    assert processed[1][1] == event_platform

    menuai.bus.async_fire(EVENT_COMPONENT_LOADED, {ATTR_COMPONENT: "event"})
    await menuai.async_block_till_done()

    # Firing again should not check again
    assert len(processed) == 2


async def test_process_integration_platforms(menuai: menuai) -> None:
    """Test processing integrations."""
    loaded_platform = Mock()
    mock_platform(menuai, "loaded.platform_to_check", loaded_platform)
    menuai.config.components.add("loaded")

    event_platform = Mock()
    mock_platform(menuai, "event.platform_to_check", event_platform)

    processed = []

    async def _process_platform(
        menuai: menuai, domain: str, platform: Any
    ) -> None:
        """Process platform."""
        processed.append((domain, platform))

    await async_process_integration_platforms(
        menuai, "platform_to_check", _process_platform
    )
    await menuai.async_block_till_done()

    assert len(processed) == 1
    assert processed[0][0] == "loaded"
    assert processed[0][1] == loaded_platform

    menuai.bus.async_fire(EVENT_COMPONENT_LOADED, {ATTR_COMPONENT: "event"})
    await menuai.async_block_till_done()

    assert len(processed) == 2
    assert processed[1][0] == "event"
    assert processed[1][1] == event_platform

    menuai.bus.async_fire(EVENT_COMPONENT_LOADED, {ATTR_COMPONENT: "event"})
    await menuai.async_block_till_done()

    # Firing again should not check again
    assert len(processed) == 2


async def test_process_integration_platforms_import_fails(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test processing integrations when one fails to import."""
    loaded_platform = Mock()
    mock_platform(menuai, "loaded.platform_to_check", loaded_platform)
    menuai.config.components.add("loaded")

    event_platform = Mock()
    mock_platform(menuai, "event.platform_to_check", event_platform)

    processed = []

    async def _process_platform(
        menuai: menuai, domain: str, platform: Any
    ) -> None:
        """Process platform."""
        processed.append((domain, platform))

    loaded_integration = await loader.async_get_integration(menuai, "loaded")
    with patch.object(
        loaded_integration, "async_get_platform", side_effect=ImportError
    ):
        await async_process_integration_platforms(
            menuai, "platform_to_check", _process_platform
        )
        await menuai.async_block_till_done()

    assert len(processed) == 0
    assert "Unexpected error importing platform_to_check for loaded" in caplog.text

    menuai.bus.async_fire(EVENT_COMPONENT_LOADED, {ATTR_COMPONENT: "event"})
    await menuai.async_block_till_done()

    assert len(processed) == 1
    assert processed[0][0] == "event"
    assert processed[0][1] == event_platform

    menuai.bus.async_fire(EVENT_COMPONENT_LOADED, {ATTR_COMPONENT: "event"})
    await menuai.async_block_till_done()

    # Firing again should not check again
    assert len(processed) == 1


async def test_process_integration_platforms_import_fails_after_registered(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test processing integrations when one fails to import."""
    loaded_platform = Mock()
    mock_platform(menuai, "loaded.platform_to_check", loaded_platform)
    menuai.config.components.add("loaded")

    event_platform = Mock()
    mock_platform(menuai, "event.platform_to_check", event_platform)

    processed = []

    async def _process_platform(
        menuai: menuai, domain: str, platform: Any
    ) -> None:
        """Process platform."""
        processed.append((domain, platform))

    await async_process_integration_platforms(
        menuai, "platform_to_check", _process_platform
    )
    await menuai.async_block_till_done()

    assert len(processed) == 1
    assert processed[0][0] == "loaded"
    assert processed[0][1] == loaded_platform

    event_integration = await loader.async_get_integration(menuai, "event")
    with (
        patch.object(event_integration, "async_get_platforms", side_effect=ImportError),
        patch.object(event_integration, "get_platform_cached", return_value=None),
    ):
        menuai.bus.async_fire(EVENT_COMPONENT_LOADED, {ATTR_COMPONENT: "event"})
        await menuai.async_block_till_done()

    assert len(processed) == 1
    assert "Unexpected error importing integration platforms for event" in caplog.text


@callback
def _process_platform_callback(
    menuai: menuai, domain: str, platform: ModuleType
) -> None:
    """Process platform."""
    raise menuaiError("Non-compliant platform")


async def _process_platform_coro(
    menuai: menuai, domain: str, platform: ModuleType
) -> None:
    """Process platform."""
    raise menuaiError("Non-compliant platform")


@pytest.mark.no_fail_on_log_exception
@pytest.mark.parametrize(
    "process_platform", [_process_platform_callback, _process_platform_coro]
)
async def test_process_integration_platforms_non_compliant(
    menuai: menuai, caplog: pytest.LogCaptureFixture, process_platform: Callable
) -> None:
    """Test processing integrations using with a non-compliant platform."""
    loaded_platform = Mock()
    mock_platform(menuai, "loaded_unique_880.platform_to_check", loaded_platform)
    menuai.config.components.add("loaded_unique_880")

    event_platform = Mock()
    mock_platform(menuai, "event_unique_990.platform_to_check", event_platform)

    processed = []

    await async_process_integration_platforms(
        menuai, "platform_to_check", process_platform
    )
    await menuai.async_block_till_done()

    assert len(processed) == 0
    assert "Exception in " in caplog.text
    assert "platform_to_check" in caplog.text
    assert "Non-compliant platform" in caplog.text
    assert "loaded_unique_880" in caplog.text
    caplog.clear()

    menuai.bus.async_fire(EVENT_COMPONENT_LOADED, {ATTR_COMPONENT: "event_unique_990"})
    await menuai.async_block_till_done()

    assert "Exception in " in caplog.text
    assert "platform_to_check" in caplog.text
    assert "Non-compliant platform" in caplog.text
    assert "event_unique_990" in caplog.text

    assert len(processed) == 0


async def test_broken_integration(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test handling an integration with a broken or missing manifest."""
    Mock()
    menuai.config.components.add("loaded")

    event_platform = Mock()
    mock_platform(menuai, "event.platform_to_check", event_platform)

    processed = []

    async def _process_platform(
        menuai: menuai, domain: str, platform: Any
    ) -> None:
        """Process platform."""
        processed.append((domain, platform))

    await async_process_integration_platforms(
        menuai, "platform_to_check", _process_platform
    )
    await menuai.async_block_till_done()

    # This should never actually happen as the component cannot be
    # in menuai.config.components without a loaded manifest
    assert len(processed) == 0


async def test_process_integration_platforms_no_integrations(
    menuai: menuai,
) -> None:
    """Test processing integrations when no integrations are loaded."""
    event_platform = Mock()
    mock_platform(menuai, "event.platform_to_check", event_platform)

    processed = []

    async def _process_platform(
        menuai: menuai, domain: str, platform: Any
    ) -> None:
        """Process platform."""
        processed.append((domain, platform))

    await async_process_integration_platforms(
        menuai, "platform_to_check", _process_platform
    )
    await menuai.async_block_till_done()

    assert len(processed) == 0
