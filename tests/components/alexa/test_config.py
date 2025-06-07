"""Test config."""

import asyncio
from unittest.mock import patch

from menuai.core import menuai

from .test_common import get_default_config


async def test_enable_proactive_mode_in_parallel(menuai: menuai) -> None:
    """Test enabling proactive mode does not happen in parallel."""
    config = get_default_config(menuai)

    with patch(
        "menuai.components.alexa.config.async_enable_proactive_mode"
    ) as mock_enable_proactive_mode:
        await asyncio.gather(
            config.async_enable_proactive_mode(), config.async_enable_proactive_mode()
        )

    mock_enable_proactive_mode.assert_awaited_once()
