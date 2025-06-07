"""Test for DNS IP component Init."""

from __future__ import annotations

from unittest.mock import patch

from menuai.components.dnsip.const import (
    CONF_HOSTNAME,
    CONF_IPV4,
    CONF_IPV6,
    CONF_PORT_IPV6,
    CONF_RESOLVER,
    CONF_RESOLVER_IPV6,
    DEFAULT_PORT,
    DOMAIN,
)
from menuai.config_entries import SOURCE_USER, ConfigEntryState
from menuai.const import CONF_NAME, CONF_PORT
from menuai.core import menuai

from . import RetrieveDNS

from tests.common import MockConfigEntry


async def test_load_unload_entry(menuai: menuai) -> None:
    """Test load and unload an entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data={
            CONF_HOSTNAME: "home-assistant.io",
            CONF_NAME: "home-assistant.io",
            CONF_IPV4: True,
            CONF_IPV6: False,
        },
        options={
            CONF_RESOLVER: "208.67.222.222",
            CONF_RESOLVER_IPV6: "2620:119:53::53",
            CONF_PORT: 53,
            CONF_PORT_IPV6: 53,
        },
        entry_id="1",
        unique_id="home-assistant.io",
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.dnsip.config_flow.aiodns.DNSResolver",
        return_value=RetrieveDNS(),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_port_migration(
    menuai: menuai,
) -> None:
    """Test migration of the config entry from no ports to with ports."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data={
            CONF_HOSTNAME: "home-assistant.io",
            CONF_NAME: "home-assistant.io",
            CONF_IPV4: True,
            CONF_IPV6: True,
        },
        options={
            CONF_RESOLVER: "208.67.222.222",
            CONF_RESOLVER_IPV6: "2620:119:53::53",
        },
        entry_id="1",
        unique_id="home-assistant.io",
        version=1,
        minor_version=1,
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.dnsip.sensor.aiodns.DNSResolver",
        return_value=RetrieveDNS(),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert entry.version == 1
    assert entry.minor_version == 2
    assert entry.options[CONF_PORT] == DEFAULT_PORT
    assert entry.options[CONF_PORT_IPV6] == DEFAULT_PORT
    assert entry.state is ConfigEntryState.LOADED


async def test_migrate_error_from_future(menuai: menuai) -> None:
    """Test a future version isn't migrated."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data={
            CONF_HOSTNAME: "home-assistant.io",
            CONF_NAME: "home-assistant.io",
            CONF_IPV4: True,
            CONF_IPV6: True,
            "some_new_data": "new_value",
        },
        options={
            CONF_RESOLVER: "208.67.222.222",
            CONF_RESOLVER_IPV6: "2620:119:53::53",
        },
        entry_id="1",
        unique_id="home-assistant.io",
        version=2,
        minor_version=1,
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.dnsip.sensor.aiodns.DNSResolver",
        return_value=RetrieveDNS(),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    entry = menuai.config_entries.async_get_entry(entry.entry_id)
    assert entry.state is ConfigEntryState.MIGRATION_ERROR
