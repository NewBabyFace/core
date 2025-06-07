"""Test VoIP repairs."""

import pytest

from menuai.components.voip import repairs
from menuai.core import menuai


async def test_create_fix_flow_raises_on_unknown_issue_id(menuai: menuai) -> None:
    """Test reate_fix_flow raises on unknown issue_id."""

    with pytest.raises(ValueError):
        await repairs.async_create_fix_flow(menuai, "no_such_issue", None)
