"""Tests for iAqualink integration utility functions."""

from iaqualink.exception import AqualinkServiceException
import pytest

from menuai.components.iaqualink.utils import await_or_reraise
from menuai.core import menuai
from menuai.exceptions import menuaiError

from .conftest import async_raises, async_returns


async def test_await_or_reraise(menuai: menuai) -> None:
    """Test await_or_reraise for all values of awaitable."""
    async_noop = async_returns(None)
    await await_or_reraise(async_noop())

    with pytest.raises(Exception) as exc_info:
        await await_or_reraise(async_raises(Exception("Test exception"))())
    assert str(exc_info.value) == "Test exception"

    async_ex = async_raises(AqualinkServiceException)
    with pytest.raises(menuaiError):
        await await_or_reraise(async_ex())
