"""Define tests for the GDACS config flow."""

from unittest.mock import patch

import pytest

from menuai import config_entries
from menuai.components.gdacs.const import CONF_CATEGORIES, DOMAIN
from menuai.const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_RADIUS,
    CONF_SCAN_INTERVAL,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType


@pytest.fixture(name="gdacs_setup", autouse=True)
def gdacs_setup_fixture():
    """Mock gdacs entry setup."""
    with patch("menuai.components.gdacs.async_setup_entry", return_value=True):
        yield


async def test_duplicate_error(menuai: menuai, config_entry) -> None:
    """Test that errors are shown when duplicates are added."""
    conf = {CONF_LATITUDE: -41.2, CONF_LONGITUDE: 174.7, CONF_RADIUS: 25}
    config_entry.add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=conf
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_show_form(menuai: menuai) -> None:
    """Test that the form is served with no input."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_step_user(menuai: menuai) -> None:
    """Test that the user step works."""
    menuai.config.latitude = -41.2
    menuai.config.longitude = 174.7
    conf = {CONF_RADIUS: 25}

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=conf
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "-41.2, 174.7"
    assert result["data"] == {
        CONF_LATITUDE: -41.2,
        CONF_LONGITUDE: 174.7,
        CONF_RADIUS: 25,
        CONF_SCAN_INTERVAL: 300.0,
        CONF_CATEGORIES: [],
    }
