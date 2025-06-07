"""Tests for IPMA config flow."""

from collections.abc import Generator
from unittest.mock import patch

from pyipma import IPMAException
import pytest

from menuai.components.ipma.const import DOMAIN
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import MockLocation

from tests.common import MockConfigEntry


@pytest.fixture(name="ipma_setup", autouse=True)
def ipma_setup_fixture() -> Generator[None]:
    """Patch ipma setup entry."""
    with patch("menuai.components.ipma.async_setup_entry", return_value=True):
        yield


async def test_config_flow(menuai: menuai) -> None:
    """Test configuration form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    test_data = {
        CONF_LONGITUDE: 0,
        CONF_LATITUDE: 0,
    }
    with patch(
        "pyipma.location.Location.get",
        return_value=MockLocation(),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            test_data,
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "HomeTown"
    assert result["data"] == {
        CONF_LONGITUDE: 0,
        CONF_LATITUDE: 0,
    }


async def test_config_flow_failures(menuai: menuai) -> None:
    """Test config flow with failures."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    test_data = {
        CONF_LONGITUDE: 0,
        CONF_LATITUDE: 0,
    }
    with patch(
        "pyipma.location.Location.get",
        side_effect=IPMAException(),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            test_data,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}
    with patch(
        "pyipma.location.Location.get",
        return_value=MockLocation(),
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            test_data,
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "HomeTown"
    assert result["data"] == {
        CONF_LONGITUDE: 0,
        CONF_LATITUDE: 0,
    }


async def test_flow_entry_already_exists(
    menuai: menuai, init_integration: MockConfigEntry
) -> None:
    """Test user input for config_entry that already exists.

    Test when the form should show when user puts existing location
    in the config gui. Then the form should show with error.
    """
    test_data = {
        CONF_NAME: "Home",
        CONF_LONGITUDE: 0,
        CONF_LATITUDE: 0,
    }

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}, data=test_data
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
