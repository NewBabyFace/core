"""Tests for the kraken config_flow."""

from unittest.mock import patch

from menuai.components.kraken.const import CONF_TRACKED_ASSET_PAIRS, DOMAIN
from menuai.const import CONF_SCAN_INTERVAL
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .const import (
    MISSING_PAIR_TRADEABLE_ASSET_PAIR_RESPONSE,
    TICKER_INFORMATION_RESPONSE,
    TRADEABLE_ASSET_PAIR_RESPONSE,
)

from tests.common import MockConfigEntry


async def test_config_flow(menuai: menuai) -> None:
    """Test we can finish a config flow."""
    with patch(
        "menuai.components.kraken.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await menuai.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result["type"] is FlowResultType.FORM

        result = await menuai.config_entries.flow.async_configure(result["flow_id"], {})

        await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert len(mock_setup_entry.mock_calls) == 1


async def test_already_configured(menuai: menuai) -> None:
    """Test we cannot add a second config flow."""
    MockConfigEntry(domain=DOMAIN).add_to_menuai(menuai)

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options(menuai: menuai) -> None:
    """Test options for Kraken."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={
            CONF_SCAN_INTERVAL: 60,
            CONF_TRACKED_ASSET_PAIRS: [
                "ADA/XBT",
                "ADA/ETH",
                "XBT/EUR",
                "XBT/GBP",
                "XBT/USD",
                "XBT/JPY",
            ],
        },
    )
    entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.kraken.config_flow.KrakenAPI.get_tradable_asset_pairs",
            return_value=TRADEABLE_ASSET_PAIR_RESPONSE,
        ),
        patch(
            "pykrakenapi.KrakenAPI.get_tradable_asset_pairs",
            return_value=TRADEABLE_ASSET_PAIR_RESPONSE,
        ),
        patch(
            "pykrakenapi.KrakenAPI.get_ticker_information",
            return_value=TICKER_INFORMATION_RESPONSE,
        ),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        assert menuai.states.get("sensor.xbt_usd_ask")

        result = await menuai.config_entries.options.async_init(entry.entry_id)
        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_SCAN_INTERVAL: 10,
                CONF_TRACKED_ASSET_PAIRS: ["ADA/ETH"],
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await menuai.async_block_till_done()

        ada_eth_sensor = menuai.states.get("sensor.ada_eth_ask")
        assert ada_eth_sensor.state == "0.0003494"

        assert menuai.states.get("sensor.xbt_usd_ask") is None


async def test_deselect_removed_pair(menuai: menuai) -> None:
    """Test options for Kraken."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        options={
            CONF_SCAN_INTERVAL: 60,
            CONF_TRACKED_ASSET_PAIRS: [
                "XBT/USD",
            ],
        },
    )
    entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.kraken.config_flow.KrakenAPI.get_tradable_asset_pairs",
            return_value=TRADEABLE_ASSET_PAIR_RESPONSE,
        ),
        patch(
            "pykrakenapi.KrakenAPI.get_tradable_asset_pairs",
            return_value=TRADEABLE_ASSET_PAIR_RESPONSE,
        ),
        patch(
            "pykrakenapi.KrakenAPI.get_ticker_information",
            return_value=TICKER_INFORMATION_RESPONSE,
        ),
    ):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    with (
        patch(
            "menuai.components.kraken.config_flow.KrakenAPI.get_tradable_asset_pairs",
            return_value=MISSING_PAIR_TRADEABLE_ASSET_PAIR_RESPONSE,
        ),
        patch(
            "pykrakenapi.KrakenAPI.get_tradable_asset_pairs",
            return_value=MISSING_PAIR_TRADEABLE_ASSET_PAIR_RESPONSE,
        ),
        patch(
            "pykrakenapi.KrakenAPI.get_ticker_information",
            return_value=TICKER_INFORMATION_RESPONSE,
        ),
    ):
        result = await menuai.config_entries.options.async_init(entry.entry_id)
        schema = result["data_schema"].schema
        assert "XBT/USD" in schema.get(CONF_TRACKED_ASSET_PAIRS).options
        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_SCAN_INTERVAL: 10,
                CONF_TRACKED_ASSET_PAIRS: ["ADA/ETH"],
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await menuai.async_block_till_done()

        ada_eth_sensor = menuai.states.get("sensor.ada_eth_ask")
        assert ada_eth_sensor.state == "0.0003494"
