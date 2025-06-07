"""Test the duotecno config flow."""

from unittest.mock import AsyncMock, patch

from duotecno.exceptions import InvalidPassword
import pytest

from menuai import config_entries
from menuai.components.duotecno.const import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_form(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "duotecno.controller.PyDuotecno.connect",
        return_value=None,
    ):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "port": 1234,
                "password": "test-password",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "1.1.1.1"
    assert result2["data"] == {
        "host": "1.1.1.1",
        "port": 1234,
        "password": "test-password",
    }
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("test_side_effect", "test_error"),
    [
        (InvalidPassword, "invalid_auth"),
        (ConnectionError, "cannot_connect"),
        (Exception, "unknown"),
    ],
)
async def test_invalid(
    menuai: menuai, test_side_effect: Exception, test_error: str
) -> None:
    """Test all side_effects on the controller.connect via parameters."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("duotecno.controller.PyDuotecno.connect", side_effect=test_side_effect):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "port": 1234,
                "password": "test-password",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": test_error}

    with patch("duotecno.controller.PyDuotecno.connect"):
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "port": 1234,
                "password": "test-password2",
            },
        )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "1.1.1.1"
    assert result2["data"] == {
        "host": "1.1.1.1",
        "port": 1234,
        "password": "test-password2",
    }


async def test_already_setup(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test duoteco flow - already setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="duotecno_1234",
        data={},
    )
    entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
