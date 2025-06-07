"""Test the Nmap Tracker config flow."""

from unittest.mock import patch

import pytest

from menuai import config_entries
from menuai.components.device_tracker import (
    CONF_CONSIDER_HOME,
    CONF_SCAN_INTERVAL,
)
from menuai.components.nmap_tracker.const import (
    CONF_HOME_INTERVAL,
    CONF_OPTIONS,
    DEFAULT_OPTIONS,
    DOMAIN,
)
from menuai.const import CONF_EXCLUDE, CONF_HOSTS
from menuai.core import CoreState, menuai
from menuai.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    "hosts", ["1.1.1.1", "192.168.1.0/24", "192.168.1.0/24,192.168.2.0/24"]
)
async def test_form(menuai: menuai, hosts: str) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    schema_defaults = result["data_schema"]({})
    assert CONF_SCAN_INTERVAL not in schema_defaults

    with patch(
        "menuai.components.nmap_tracker.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOSTS: hosts,
                CONF_HOME_INTERVAL: 3,
                CONF_OPTIONS: DEFAULT_OPTIONS,
                CONF_EXCLUDE: "4.4.4.4",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == f"Nmap Tracker {hosts}"
    assert result2["data"] == {}
    assert result2["options"] == {
        CONF_HOSTS: hosts,
        CONF_HOME_INTERVAL: 3,
        CONF_OPTIONS: DEFAULT_OPTIONS,
        CONF_EXCLUDE: "4.4.4.4",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_range(menuai: menuai) -> None:
    """Test we get the form and can take an ip range."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "menuai.components.nmap_tracker.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOSTS: "192.168.0.5-12",
                CONF_HOME_INTERVAL: 3,
                CONF_OPTIONS: DEFAULT_OPTIONS,
                CONF_EXCLUDE: "4.4.4.4",
            },
        )
        await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Nmap Tracker 192.168.0.5-12"
    assert result2["data"] == {}
    assert result2["options"] == {
        CONF_HOSTS: "192.168.0.5-12",
        CONF_HOME_INTERVAL: 3,
        CONF_OPTIONS: DEFAULT_OPTIONS,
        CONF_EXCLUDE: "4.4.4.4",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_hosts(menuai: menuai) -> None:
    """Test invalid hosts passed in."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOSTS: "not an ip block",
            CONF_HOME_INTERVAL: 3,
            CONF_OPTIONS: DEFAULT_OPTIONS,
            CONF_EXCLUDE: "",
        },
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {CONF_HOSTS: "invalid_hosts"}


async def test_form_already_configured(menuai: menuai) -> None:
    """Test duplicate host list."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            CONF_HOSTS: "192.168.0.0/20",
            CONF_HOME_INTERVAL: 3,
            CONF_OPTIONS: DEFAULT_OPTIONS,
            CONF_EXCLUDE: "4.4.4.4",
        },
    )
    config_entry.add_to_menuai(menuai)
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOSTS: "192.168.0.0/20",
            CONF_HOME_INTERVAL: 3,
            CONF_OPTIONS: DEFAULT_OPTIONS,
            CONF_EXCLUDE: "",
        },
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_form_invalid_excludes(menuai: menuai) -> None:
    """Test invalid excludes passed in."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOSTS: "3.3.3.3",
            CONF_HOME_INTERVAL: 3,
            CONF_OPTIONS: DEFAULT_OPTIONS,
            CONF_EXCLUDE: "not an exclude",
        },
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {CONF_EXCLUDE: "invalid_hosts"}


async def test_options_flow(menuai: menuai) -> None:
    """Test we can edit options."""

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            CONF_HOSTS: "192.168.1.0/24",
            CONF_HOME_INTERVAL: 3,
            CONF_OPTIONS: DEFAULT_OPTIONS,
            CONF_EXCLUDE: "4.4.4.4",
        },
    )
    config_entry.add_to_menuai(menuai)
    menuai.set_state(CoreState.stopped)

    assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    assert result["data_schema"]({}) == {
        CONF_EXCLUDE: "4.4.4.4",
        CONF_HOME_INTERVAL: 3,
        CONF_HOSTS: "192.168.1.0/24",
        CONF_CONSIDER_HOME: 180,
        CONF_SCAN_INTERVAL: 120,
        CONF_OPTIONS: "-F -T4 --min-rate 10 --host-timeout 5s",
    }

    with patch(
        "menuai.components.nmap_tracker.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOSTS: "192.168.1.0/24, 192.168.2.0/24",
                CONF_HOME_INTERVAL: 5,
                CONF_CONSIDER_HOME: 500,
                CONF_OPTIONS: "-sn",
                CONF_EXCLUDE: "4.4.4.4, 5.5.5.5",
                CONF_SCAN_INTERVAL: 10,
            },
        )
        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert config_entry.options == {
        CONF_HOSTS: "192.168.1.0/24,192.168.2.0/24",
        CONF_HOME_INTERVAL: 5,
        CONF_CONSIDER_HOME: 500,
        CONF_OPTIONS: "-sn",
        CONF_EXCLUDE: "4.4.4.4,5.5.5.5",
        CONF_SCAN_INTERVAL: 10,
    }
    assert len(mock_setup_entry.mock_calls) == 1
