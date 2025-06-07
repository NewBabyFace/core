"""Tests for the Agent DVR config flow."""

import pytest

from menuai.components.agent_dvr.const import DOMAIN, SERVER_URL
from menuai.config_entries import SOURCE_USER
from menuai.const import CONF_HOST, CONF_PORT, CONTENT_TYPE_JSON
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import init_integration

from tests.common import async_load_fixture
from tests.test_util.aiohttp import AiohttpClientMocker

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


async def test_show_user_form(menuai: menuai) -> None:
    """Test that the user set up form is served."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM


async def test_user_device_exists_abort(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test we abort flow if Agent device already configured."""
    await init_integration(menuai, aioclient_mock)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_HOST: "example.local", CONF_PORT: 8090},
    )

    assert result["type"] is FlowResultType.ABORT


async def test_connection_error(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test we show user form on Agent connection error."""

    aioclient_mock.get("http://example.local:8090/command.cgi?cmd=getStatus", text="")

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_HOST: "example.local", CONF_PORT: 8090},
    )

    assert result["errors"]["base"] == "cannot_connect"
    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM


async def test_full_user_flow_implementation(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the full manual user flow from start to finish."""
    aioclient_mock.get(
        "http://example.local:8090/command.cgi?cmd=getStatus",
        text=await async_load_fixture(menuai, "status.json", DOMAIN),
        headers={"Content-Type": CONTENT_TYPE_JSON},
    )

    aioclient_mock.get(
        "http://example.local:8090/command.cgi?cmd=getObjects",
        text=await async_load_fixture(menuai, "objects.json", DOMAIN),
        headers={"Content-Type": CONTENT_TYPE_JSON},
    )

    result = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_HOST: "example.local", CONF_PORT: 8090}
    )

    assert result["data"][CONF_HOST] == "example.local"
    assert result["data"][CONF_PORT] == 8090
    assert result["data"][SERVER_URL] == "http://example.local:8090/"
    assert result["title"] == "DESKTOP"
    assert result["type"] is FlowResultType.CREATE_ENTRY

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert entries[0].unique_id == "c0715bba-c2d0-48ef-9e3e-bc81c9ea4447"
