"""Test singleton helper."""

from typing import Any
from unittest.mock import Mock

import pytest

from menuai.core import menuai
from menuai.helpers import singleton


@pytest.fixture
def mock_menuai():
    """Mock menuai fixture."""
    return Mock(data={})


@pytest.mark.parametrize("result", [object(), {}, []])
async def test_singleton_async(mock_menuai: menuai, result: Any) -> None:
    """Test singleton with async function."""

    @singleton.singleton("test_key")
    async def something(menuai: menuai) -> Any:
        return result

    result1 = await something(mock_menuai)
    result2 = await something(mock_menuai)
    assert result1 is result
    assert result1 is result2
    assert "test_key" in mock_menuai.data
    assert mock_menuai.data["test_key"] is result1


@pytest.mark.parametrize("result", [object(), {}, []])
def test_singleton(mock_menuai: menuai, result: Any) -> None:
    """Test singleton with function."""

    @singleton.singleton("test_key")
    def something(menuai: menuai) -> Any:
        return result

    result1 = something(mock_menuai)
    result2 = something(mock_menuai)
    assert result1 is result
    assert result1 is result2
    assert "test_key" in mock_menuai.data
    assert mock_menuai.data["test_key"] is result1
