"""Tests for the jellyfin integration."""

import json
from typing import Any

from menuai.core import menuai

from tests.common import load_fixture


def load_json_fixture(filename: str) -> Any:
    """Load JSON fixture on-demand."""
    return json.loads(load_fixture(f"jellyfin/{filename}"))


async def async_load_json_fixture(menuai: menuai, filename: str) -> Any:
    """Load JSON fixture on-demand asynchronously."""
    return await menuai.async_add_executor_job(load_json_fixture, filename)
