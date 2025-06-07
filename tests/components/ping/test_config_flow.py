"""Test the Ping (ICMP) config flow."""

from __future__ import annotations

import pytest

from menuai import config_entries
from menuai.components.ping import DOMAIN
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("192.618.178.1", "192.618.178.1"),
        (" 192.618.178.1 ", "192.618.178.1"),
        (" demo.host ", "demo.host"),
    ],
)
@pytest.mark.usefixtures("patch_setup")
async def test_form(menuai: menuai, host, expected) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "host": host,
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == expected
    assert result["data"] == {}
    assert result["options"] == {
        "count": 5,
        "host": expected,
        "consider_home": 180,
    }


@pytest.mark.parametrize(
    ("host", "expected_host"),
    [
        ("192.618.178.1", "192.618.178.1"),
        (" 192.618.178.1 ", "192.618.178.1"),
        (" demo.host ", "demo.host"),
    ],
)
@pytest.mark.usefixtures("patch_setup")
async def test_options(menuai: menuai, host: str, expected_host: str) -> None:
    """Test options flow."""

    config_entry = MockConfigEntry(
        version=1,
        source=config_entries.SOURCE_USER,
        data={},
        domain=DOMAIN,
        options={"count": 1, "host": "192.168.1.1", "consider_home": 180},
        title="192.168.1.1",
    )
    config_entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {
            "host": host,
            "count": 10,
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "count": 10,
        "host": expected_host,
        "consider_home": 180,
    }
