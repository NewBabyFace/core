"""Test the cloud assist pipeline."""

import pytest

from menuai.components.cloud.assist_pipeline import (
    async_migrate_cloud_pipeline_engine,
)
from menuai.const import Platform
from menuai.core import menuai
from menuai.setup import async_setup_component


async def test_migrate_pipeline_invalid_platform(menuai: menuai) -> None:
    """Test migrate pipeline with invalid platform."""
    await async_setup_component(menuai, "assist_pipeline", {})
    with pytest.raises(ValueError):
        await async_migrate_cloud_pipeline_engine(
            menuai, Platform.BINARY_SENSOR, "test-engine-id"
        )
