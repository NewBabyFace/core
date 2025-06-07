"""Define tests for the lookin config flow."""

from __future__ import annotations

import dataclasses
from ipaddress import ip_address
from unittest.mock import patch

from aiolookin import NoUsableService

from menuai import config_entries
from menuai.components.lookin.const import DOMAIN
from menuai.const import CONF_HOST
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from . import (
    DEFAULT_ENTRY_TITLE,
    DEVICE_ID,
    IP_ADDRESS,
    MODULE,
    ZEROCONF_DATA,
    _patch_get_info,
)

from tests.common import MockConfigEntry


async def test_manual_setup(menuai: menuai) -> None:
    """Test manually setting up."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    with (
        _patch_get_info(),
        patch(f"{MODULE}.async_setup_entry", return_value=True) as mock_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: IP_ADDRESS}
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_HOST: IP_ADDRESS}
    assert result["title"] == DEFAULT_ENTRY_TITLE
    assert len(mock_setup_entry.mock_calls) == 1


async def test_manual_setup_already_exists(menuai: menuai) -> None:
    """Test manually setting up and the device already exists."""
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: IP_ADDRESS}, unique_id=DEVICE_ID
    )
    entry.add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    with _patch_get_info():
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: IP_ADDRESS}
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_manual_setup_device_offline(menuai: menuai) -> None:
    """Test manually setting up, device offline."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    with _patch_get_info(exception=NoUsableService):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: IP_ADDRESS}
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_HOST: "cannot_connect"}


async def test_manual_setup_unknown_exception(menuai: menuai) -> None:
    """Test manually setting up, unknown exception."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]

    with _patch_get_info(exception=Exception):
        result = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: IP_ADDRESS}
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_discovered_zeroconf(menuai: menuai) -> None:
    """Test we can setup when discovered from zeroconf."""

    with _patch_get_info():
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=ZEROCONF_DATA,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        _patch_get_info(),
        patch(
            f"{MODULE}.async_setup_entry", return_value=True
        ) as mock_async_setup_entry,
    ):
        result2 = await menuai.config_entries.flow.async_configure(result["flow_id"], {})
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == {CONF_HOST: IP_ADDRESS}
    assert result2["title"] == DEFAULT_ENTRY_TITLE
    assert mock_async_setup_entry.called

    entry = menuai.config_entries.async_entries(DOMAIN)[0]
    zc_data_new_ip = dataclasses.replace(ZEROCONF_DATA)
    zc_data_new_ip.ip_address = ip_address("127.0.0.2")

    with (
        _patch_get_info(),
        patch(
            f"{MODULE}.async_setup_entry", return_value=True
        ) as mock_async_setup_entry,
    ):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=zc_data_new_ip,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == "127.0.0.2"


async def test_discovered_zeroconf_cannot_connect(menuai: menuai) -> None:
    """Test we abort if we cannot connect when discovered from zeroconf."""

    with _patch_get_info(exception=NoUsableService):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=ZEROCONF_DATA,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def test_discovered_zeroconf_unknown_exception(menuai: menuai) -> None:
    """Test we abort if we get an unknown exception when discovered from zeroconf."""

    with _patch_get_info(exception=Exception):
        result = await menuai.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=ZEROCONF_DATA,
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unknown"
