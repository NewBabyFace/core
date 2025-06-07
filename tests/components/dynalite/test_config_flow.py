"""Test Dynalite config flow."""

from unittest.mock import AsyncMock, patch

import pytest

from menuai import config_entries
from menuai.components import dynalite
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_HOST, CONF_PORT
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("first_con", "second_con", "exp_type", "exp_result", "exp_reason"),
    [
        (True, True, "create_entry", ConfigEntryState.LOADED, ""),
        (False, False, "abort", None, "cannot_connect"),
        (True, False, "create_entry", ConfigEntryState.SETUP_RETRY, ""),
    ],
)
async def test_flow(
    menuai: menuai,
    first_con,
    second_con,
    exp_type,
    exp_result,
    exp_reason,
) -> None:
    """Run a flow with or without errors and return result."""
    host = "1.2.3.4"
    with patch(
        "menuai.components.dynalite.bridge.DynaliteDevices.async_setup",
        side_effect=[first_con, second_con],
    ):
        result = await menuai.config_entries.flow.async_init(
            dynalite.DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_HOST: host},
        )
        await menuai.async_block_till_done()
    assert result["type"] == exp_type
    if exp_result:
        assert result["result"].state == exp_result
    if exp_reason:
        assert result["reason"] == exp_reason


async def test_existing(menuai: menuai) -> None:
    """Test when the entry exists with the same config."""
    host = "1.2.3.4"
    MockConfigEntry(domain=dynalite.DOMAIN, data={CONF_HOST: host}).add_to_menuai(menuai)
    with patch(
        "menuai.components.dynalite.bridge.DynaliteDevices.async_setup",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_init(
            dynalite.DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_HOST: host},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_existing_abort_update(menuai: menuai) -> None:
    """Test when the entry exists with a different config."""
    host = "1.2.3.4"
    port1 = 7777
    port2 = 8888
    entry = MockConfigEntry(
        domain=dynalite.DOMAIN,
        data={CONF_HOST: host, CONF_PORT: port1},
    )
    entry.add_to_menuai(menuai)
    with patch(
        "menuai.components.dynalite.bridge.DynaliteDevices"
    ) as mock_dyn_dev:
        mock_dyn_dev().async_setup = AsyncMock(return_value=True)
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
        mock_dyn_dev().configure.assert_called_once()
        assert mock_dyn_dev().configure.mock_calls[0][1][0]["port"] == port1
        result = await menuai.config_entries.flow.async_init(
            dynalite.DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_HOST: host, CONF_PORT: port2},
        )
        await menuai.async_block_till_done()
        assert mock_dyn_dev().configure.call_count == 1
        assert mock_dyn_dev().configure.mock_calls[0][1][0]["port"] == port1
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_two_entries(menuai: menuai) -> None:
    """Test when two different entries exist with different hosts."""
    host1 = "1.2.3.4"
    host2 = "5.6.7.8"
    MockConfigEntry(domain=dynalite.DOMAIN, data={CONF_HOST: host1}).add_to_menuai(menuai)
    with patch(
        "menuai.components.dynalite.bridge.DynaliteDevices.async_setup",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_init(
            dynalite.DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={CONF_HOST: host2},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].state is ConfigEntryState.LOADED


async def test_setup_user(menuai: menuai) -> None:
    """Test configuration via the user flow."""
    host = "3.4.5.6"
    port = 1234
    result = await menuai.config_entries.flow.async_init(
        dynalite.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] is None

    with patch(
        "menuai.components.dynalite.bridge.DynaliteDevices.async_setup",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": host, "port": port},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].state is ConfigEntryState.LOADED
    assert result["title"] == host
    assert result["data"] == {
        "host": host,
        "port": port,
    }


async def test_setup_user_existing_host(menuai: menuai) -> None:
    """Test that when we setup a host that is defined, we get an error."""
    host = "3.4.5.6"
    MockConfigEntry(domain=dynalite.DOMAIN, data={CONF_HOST: host}).add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        dynalite.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "menuai.components.dynalite.bridge.DynaliteDevices.async_setup",
        return_value=True,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": host, "port": 1234},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
