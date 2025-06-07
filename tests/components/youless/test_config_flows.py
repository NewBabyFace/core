"""Test the youless config flow."""

from unittest.mock import MagicMock, patch
from urllib.error import URLError

from menuai.components.youless import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


def _get_mock_youless_api(initialize=None):
    mock_youless = MagicMock()
    if isinstance(initialize, Exception):
        type(mock_youless).initialize = MagicMock(side_effect=initialize)
    else:
        type(mock_youless).initialize = MagicMock(return_value=initialize)

    type(mock_youless).mac_address = None
    return mock_youless


async def test_full_flow(menuai: menuai) -> None:
    """Check setup."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {}
    assert result.get("step_id") == "user"

    mock_youless = _get_mock_youless_api(
        initialize={"homes": [{"id": 1, "name": "myhome"}]}
    )
    with patch(
        "menuai.components.youless.config_flow.YoulessAPI",
        return_value=mock_youless,
    ) as mocked_youless:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "localhost"},
        )

    assert result2.get("type") is FlowResultType.CREATE_ENTRY
    assert result2.get("title") == "localhost"
    assert len(mocked_youless.mock_calls) == 1


async def test_not_found(menuai: menuai) -> None:
    """Check setup."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") is FlowResultType.FORM
    assert result.get("errors") == {}
    assert result.get("step_id") == "user"

    mock_youless = _get_mock_youless_api(initialize=URLError(""))
    with patch(
        "menuai.components.youless.config_flow.YoulessAPI",
        return_value=mock_youless,
    ) as mocked_youless:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "localhost"},
        )

    assert result2.get("type") is FlowResultType.FORM
    assert len(mocked_youless.mock_calls) == 1
