"""Test the wiffi integration config flow."""

import errno
from unittest.mock import patch

import pytest

from menuai import config_entries
from menuai.components.wiffi.const import DOMAIN
from menuai.const import CONF_PORT, CONF_TIMEOUT
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

MOCK_CONFIG = {CONF_PORT: 8765}

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


@pytest.fixture(name="dummy_tcp_server")
def mock_dummy_tcp_server():
    """Mock a valid WiffiTcpServer."""

    class Dummy:
        async def start_server(self):
            pass

        async def close_server(self):
            pass

    server = Dummy()
    with patch(
        "menuai.components.wiffi.config_flow.WiffiTcpServer", return_value=server
    ):
        yield server


@pytest.fixture(name="addr_in_use")
def mock_addr_in_use_server():
    """Mock a WiffiTcpServer with addr_in_use."""

    class Dummy:
        async def start_server(self):
            raise OSError(errno.EADDRINUSE, "")

        async def close_server(self):
            pass

    server = Dummy()
    with patch(
        "menuai.components.wiffi.config_flow.WiffiTcpServer", return_value=server
    ):
        yield server


@pytest.fixture(name="start_server_failed")
def mock_start_server_failed():
    """Mock a WiffiTcpServer with start_server_failed."""

    class Dummy:
        async def start_server(self):
            raise OSError(errno.EACCES, "")

        async def close_server(self):
            pass

    server = Dummy()
    with patch(
        "menuai.components.wiffi.config_flow.WiffiTcpServer", return_value=server
    ):
        yield server


async def test_form(menuai: menuai, dummy_tcp_server) -> None:
    """Test how we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == config_entries.SOURCE_USER

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_CONFIG,
    )
    assert result2["type"] is FlowResultType.CREATE_ENTRY


async def test_form_addr_in_use(menuai: menuai, addr_in_use) -> None:
    """Test how we handle addr_in_use error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_CONFIG,
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "addr_in_use"


async def test_form_start_server_failed(
    menuai: menuai, start_server_failed
) -> None:
    """Test how we handle start_server_failed error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_CONFIG,
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "start_server_failed"


async def test_option_flow(menuai: menuai) -> None:
    """Test option flow."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG)
    entry.add_to_menuai(menuai)

    assert not entry.options

    result = await menuai.config_entries.options.async_init(entry.entry_id, data=None)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_TIMEOUT: 9}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == ""
    assert result["data"][CONF_TIMEOUT] == 9
