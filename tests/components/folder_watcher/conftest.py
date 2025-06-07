"""Fixtures for Folder Watcher integration tests."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components.folder_watcher.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai

from tests.common import MockConfigEntry


@pytest.fixture
def mock_setup_entry() -> Generator[None]:
    """Mock setting up a config entry."""
    with patch(
        "menuai.components.folder_watcher.async_setup_entry", return_value=True
    ):
        yield


@pytest.fixture
async def load_int(
    menuai: menuai, tmp_path: Path, freezer: FrozenDateTimeFactory
) -> MockConfigEntry:
    """Set up the Folder watcher integration in MenuAI."""
    freezer.move_to("2022-04-19 10:31:02+00:00")
    path = tmp_path.as_posix()
    menuai.config.allowlist_external_dirs = {path}
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        title=f"Folder Watcher {tmp_path.parts[-1]!s}",
        data={},
        options={"folder": str(path), "patterns": ["*"]},
        entry_id="1",
    )

    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    return config_entry
