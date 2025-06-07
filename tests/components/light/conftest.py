"""Light conftest."""

from unittest.mock import AsyncMock, patch

import pytest

from menuai.components.light import Profiles
from menuai.core import menuai


@pytest.fixture(autouse=True)
def mock_light_profiles():
    """Mock loading of profiles."""
    data = {}

    def mock_profiles_class(menuai: menuai) -> Profiles:
        profiles = Profiles(menuai)
        profiles.data = data
        profiles.async_initialize = AsyncMock()
        return profiles

    with patch(
        "menuai.components.light.Profiles",
        side_effect=mock_profiles_class,
    ):
        yield data
