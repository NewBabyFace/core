"""Test the legacy stt setup."""

from __future__ import annotations

from pathlib import Path

import pytest

from menuai.components.stt import Provider
from menuai.core import menuai
from menuai.helpers.discovery import async_load_platform
from menuai.helpers.typing import ConfigType, DiscoveryInfoType

from .common import mock_stt_platform


async def test_invalid_platform(
    menuai: menuai, caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    """Test platform setup with an invalid platform."""
    await async_load_platform(
        menuai,
        "stt",
        "bad_stt",
        {"stt": [{"platform": "bad_stt"}]},
        menuai_config={"stt": [{"platform": "bad_stt"}]},
    )
    await menuai.async_block_till_done()

    assert "Unknown speech-to-text platform specified" in caplog.text


async def test_platform_setup_with_error(
    menuai: menuai, caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    """Test platform setup with an error during setup."""

    async def async_get_engine(
        menuai: menuai,
        config: ConfigType,
        discovery_info: DiscoveryInfoType | None = None,
    ) -> Provider:
        """Raise exception during platform setup."""
        raise Exception("Setup error")  # noqa: TRY002

    mock_stt_platform(menuai, tmp_path, "bad_stt", async_get_engine=async_get_engine)

    await async_load_platform(
        menuai,
        "stt",
        "bad_stt",
        {},
        menuai_config={"stt": [{"platform": "bad_stt"}]},
    )
    await menuai.async_block_till_done()

    assert "Error setting up platform: bad_stt" in caplog.text
