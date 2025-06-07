"""Fixtures for history tests."""

import pytest

from menuai.components import history
from menuai.components.recorder import Recorder
from menuai.const import CONF_DOMAINS, CONF_ENTITIES, CONF_EXCLUDE, CONF_INCLUDE
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.typing import RecorderInstanceContextManager


@pytest.fixture
async def mock_recorder_before_menuai(
    async_test_recorder: RecorderInstanceContextManager,
) -> None:
    """Set up recorder."""


@pytest.fixture
async def menuai_history(menuai: menuai, recorder_mock: Recorder) -> None:
    """MenuAI fixture with history."""
    config = history.CONFIG_SCHEMA(
        {
            history.DOMAIN: {
                CONF_INCLUDE: {
                    CONF_DOMAINS: ["media_player"],
                    CONF_ENTITIES: ["thermostat.test"],
                },
                CONF_EXCLUDE: {
                    CONF_DOMAINS: ["thermostat"],
                    CONF_ENTITIES: ["media_player.test"],
                },
            }
        }
    )
    assert await async_setup_component(menuai, history.DOMAIN, config)
