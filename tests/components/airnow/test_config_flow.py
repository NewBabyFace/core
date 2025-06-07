"""Test the AirNow config flow."""

from typing import Any
from unittest.mock import AsyncMock, patch

from pyairnow.errors import AirNowError, EmptyResponseError, InvalidKeyError
import pytest

from menuai import config_entries
from menuai.components.airnow.const import DOMAIN
from menuai.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE, CONF_RADIUS
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("setup_airnow")
async def test_form(
    menuai: menuai, config: dict[str, Any], options: dict[str, Any]
) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], config)
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == config
    assert result2["options"] == options


@pytest.mark.parametrize("mock_api_get", [AsyncMock(side_effect=InvalidKeyError)])
@pytest.mark.usefixtures("setup_airnow")
async def test_form_invalid_auth(menuai: menuai, config: dict[str, Any]) -> None:
    """Test we handle invalid auth."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], config)
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


@pytest.mark.parametrize("data", [{}])
@pytest.mark.usefixtures("setup_airnow")
async def test_form_invalid_location(
    menuai: menuai, config: dict[str, Any]
) -> None:
    """Test we handle invalid location."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], config)
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_location"}


@pytest.mark.parametrize("mock_api_get", [AsyncMock(side_effect=AirNowError)])
@pytest.mark.usefixtures("setup_airnow")
async def test_form_cannot_connect(menuai: menuai, config: dict[str, Any]) -> None:
    """Test we handle cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], config)
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


@pytest.mark.parametrize("mock_api_get", [AsyncMock(side_effect=EmptyResponseError)])
@pytest.mark.usefixtures("setup_airnow")
async def test_form_empty_result(menuai: menuai, config: dict[str, Any]) -> None:
    """Test we handle empty response error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], config)
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_location"}


@pytest.mark.parametrize("mock_api_get", [AsyncMock(side_effect=RuntimeError)])
@pytest.mark.usefixtures("setup_airnow")
async def test_form_unexpected(menuai: menuai, config: dict[str, Any]) -> None:
    """Test we handle an unexpected error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], config)
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


@pytest.mark.usefixtures("config_entry")
async def test_entry_already_exists(
    menuai: menuai, config: dict[str, Any]
) -> None:
    """Test that the form aborts if the Lat/Lng is already configured."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], config)
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


@pytest.mark.usefixtures("setup_airnow")
async def test_config_migration_v2(menuai: menuai) -> None:
    """Test that the config migration from Version 1 to Version 2 works."""
    config_entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="AirNow",
        data={
            CONF_API_KEY: "1234",
            CONF_LATITUDE: 33.6,
            CONF_LONGITUDE: -118.1,
            CONF_RADIUS: 25,
        },
        source=config_entries.SOURCE_USER,
        options={CONF_RADIUS: 10},
        unique_id="1234",
    )
    config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.version == 2
    assert not config_entry.data.get(CONF_RADIUS)
    assert config_entry.options.get(CONF_RADIUS) == 25


@pytest.mark.usefixtures("setup_airnow")
async def test_options_flow(menuai: menuai) -> None:
    """Test that the options flow works."""
    config_entry = MockConfigEntry(
        version=2,
        domain=DOMAIN,
        title="AirNow",
        data={
            CONF_API_KEY: "1234",
            CONF_LATITUDE: 33.6,
            CONF_LONGITUDE: -118.1,
        },
        source=config_entries.SOURCE_USER,
        options={CONF_RADIUS: 10},
        unique_id="1234",
    )
    config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    with patch(
        "menuai.components.airnow.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input={CONF_RADIUS: 25},
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {
        CONF_RADIUS: 25,
    }
    assert len(mock_setup_entry.mock_calls) == 1
