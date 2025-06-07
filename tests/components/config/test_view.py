"""Test config HTTP views."""

from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext as does_not_raise

import pytest

from menuai.components.config import view
from menuai.core import menuai


async def _mock_validator(menuai: menuai, key: str, data: dict) -> dict:
    """Mock data validator."""
    return data


@pytest.mark.parametrize(
    ("data_schema", "data_validator", "expected_result"),
    [
        (None, None, pytest.raises(ValueError)),
        (None, _mock_validator, does_not_raise()),
        (lambda x: x, None, does_not_raise()),
        (lambda x: x, _mock_validator, pytest.raises(ValueError)),
    ],
)
async def test_view_requires_data_schema_or_validator(
    menuai: menuai,
    data_schema: Callable | None,
    data_validator: Callable | None,
    expected_result: AbstractContextManager,
) -> None:
    """Test the view base class requires a schema or validator."""
    with expected_result:
        view.BaseEditConfigView(
            "test",
            "test",
            "test",
            lambda x: "",
            data_schema=data_schema,
            data_validator=data_validator,
        )
