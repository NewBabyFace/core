"""Tests for the Ollama integration."""

from unittest.mock import patch

from httpx import ConnectError
import pytest

from menuai.components import ollama
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (ConnectError(message="Connect error"), "Connect error"),
        (RuntimeError("Runtime error"), "Runtime error"),
    ],
)
async def test_init_error(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
    side_effect,
    error,
) -> None:
    """Test initialization errors."""
    with patch(
        "ollama.AsyncClient.list",
        side_effect=side_effect,
    ):
        assert await async_setup_component(menuai, ollama.DOMAIN, {})
        await menuai.async_block_till_done()
        assert error in caplog.text
