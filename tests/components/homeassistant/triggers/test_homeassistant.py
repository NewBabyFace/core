"""The tests for the Event automation."""

from unittest.mock import patch

import pytest

from menuai.components import automation
from menuai.core import CoreState, menuai
from menuai.helpers.typing import ConfigType
from menuai.setup import async_setup_component

from tests.common import async_mock_service


@pytest.mark.parametrize(
    "menuai_config",
    [
        {
            automation.DOMAIN: {
                "alias": "hello",
                "trigger": {"platform": "menuai", "event": "start"},
                "action": {
                    "service": "test.automation",
                    "data_template": {"id": "{{ trigger.id}}"},
                },
            }
        }
    ],
)
@pytest.mark.usefixtures("mock_menuai_config")
async def test_if_fires_on_menuai_start(
    menuai: menuai, menuai_config: ConfigType
) -> None:
    """Test the firing when MenuAI starts."""
    calls = async_mock_service(menuai, "test", "automation")
    menuai.set_state(CoreState.not_running)

    assert await async_setup_component(menuai, automation.DOMAIN, menuai_config)
    assert automation.is_on(menuai, "automation.hello")
    assert len(calls) == 0

    await menuai.async_start()
    await menuai.async_block_till_done()
    assert automation.is_on(menuai, "automation.hello")
    assert len(calls) == 1

    await menuai.services.async_call(
        automation.DOMAIN, automation.SERVICE_RELOAD, blocking=True
    )

    assert automation.is_on(menuai, "automation.hello")
    assert len(calls) == 1
    assert calls[0].data["id"] == 0


async def test_if_fires_on_menuai_shutdown(menuai: menuai) -> None:
    """Test the firing when MenuAI shuts down."""
    calls = async_mock_service(menuai, "test", "automation")
    menuai.set_state(CoreState.not_running)

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "alias": "hello",
                "trigger": {"platform": "menuai", "event": "shutdown"},
                "action": {
                    "service": "test.automation",
                    "data_template": {"id": "{{ trigger.id}}"},
                },
            }
        },
    )
    assert automation.is_on(menuai, "automation.hello")
    assert len(calls) == 0

    await menuai.async_start()
    assert automation.is_on(menuai, "automation.hello")
    await menuai.async_block_till_done()
    assert len(calls) == 0

    with patch.object(menuai.loop, "stop"):
        await menuai.async_stop()
    assert len(calls) == 1
    assert calls[0].data["id"] == 0
