"""Tests for the kraken sensor platform."""

from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from pykrakenapi.pykrakenapi import KrakenAPIError
import pytest

from menuai.components.kraken.const import (
    CONF_TRACKED_ASSET_PAIRS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TRACKED_ASSET_PAIR,
    DOMAIN,
)
from menuai.const import CONF_SCAN_INTERVAL, EVENT_menuai_START
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from .const import (
    MISSING_PAIR_TICKER_INFORMATION_RESPONSE,
    MISSING_PAIR_TRADEABLE_ASSET_PAIR_RESPONSE,
    TICKER_INFORMATION_RESPONSE,
    TRADEABLE_ASSET_PAIR_RESPONSE,
)

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that sensor has a value."""
    with (
        patch(
            "pykrakenapi.KrakenAPI.get_tradable_asset_pairs",
            return_value=TRADEABLE_ASSET_PAIR_RESPONSE,
        ),
        patch(
            "pykrakenapi.KrakenAPI.get_ticker_information",
            return_value=TICKER_INFORMATION_RESPONSE,
        ),
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            unique_id="0123456789",
            options={
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
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

        await menuai.config_entries.async_setup(entry.entry_id)

        await menuai.async_block_till_done()

        menuai.bus.async_fire(EVENT_menuai_START)
        await menuai.async_block_till_done()

        xbt_usd_sensor = menuai.states.get("sensor.xbt_usd_ask")
        assert xbt_usd_sensor.state == "0.0003494"
        assert xbt_usd_sensor.attributes["icon"] == "mdi:currency-usd"

        xbt_eur_sensor = menuai.states.get("sensor.xbt_eur_ask")
        assert xbt_eur_sensor.state == "0.0003494"
        assert xbt_eur_sensor.attributes["icon"] == "mdi:currency-eur"

        ada_xbt_sensor = menuai.states.get("sensor.ada_xbt_ask")
        assert ada_xbt_sensor.state == "0.0003494"
        assert ada_xbt_sensor.attributes["icon"] == "mdi:currency-btc"

        xbt_jpy_sensor = menuai.states.get("sensor.xbt_jpy_ask")
        assert xbt_jpy_sensor.state == "0.0003494"
        assert xbt_jpy_sensor.attributes["icon"] == "mdi:currency-jpy"

        xbt_gbp_sensor = menuai.states.get("sensor.xbt_gbp_ask")
        assert xbt_gbp_sensor.state == "0.0003494"
        assert xbt_gbp_sensor.attributes["icon"] == "mdi:currency-gbp"

        ada_eth_sensor = menuai.states.get("sensor.ada_eth_ask")
        assert ada_eth_sensor.state == "0.0003494"
        assert ada_eth_sensor.attributes["icon"] == "mdi:cash"

        xbt_usd_ask_volume = menuai.states.get("sensor.xbt_usd_ask_volume")
        assert xbt_usd_ask_volume.state == "15949"

        xbt_usd_last_trade_closed = menuai.states.get("sensor.xbt_usd_last_trade_closed")
        assert xbt_usd_last_trade_closed.state == "0.0003478"

        xbt_usd_bid_volume = menuai.states.get("sensor.xbt_usd_bid_volume")
        assert xbt_usd_bid_volume.state == "20792"

        xbt_usd_volume_today = menuai.states.get("sensor.xbt_usd_volume_today")
        assert xbt_usd_volume_today.state == "146300.24906838"

        xbt_usd_volume_last_24h = menuai.states.get("sensor.xbt_usd_volume_last_24h")
        assert xbt_usd_volume_last_24h.state == "253478.04715403"

        xbt_usd_volume_weighted_average_today = menuai.states.get(
            "sensor.xbt_usd_volume_weighted_average_today"
        )
        assert xbt_usd_volume_weighted_average_today.state == "0.000348573"

        xbt_usd_volume_weighted_average_last_24h = menuai.states.get(
            "sensor.xbt_usd_volume_weighted_average_last_24h"
        )
        assert xbt_usd_volume_weighted_average_last_24h.state == "0.000344881"

        xbt_usd_number_of_trades_today = menuai.states.get(
            "sensor.xbt_usd_number_of_trades_today"
        )
        assert xbt_usd_number_of_trades_today.state == "82"

        xbt_usd_number_of_trades_last_24h = menuai.states.get(
            "sensor.xbt_usd_number_of_trades_last_24h"
        )
        assert xbt_usd_number_of_trades_last_24h.state == "128"

        xbt_usd_low_last_24h = menuai.states.get("sensor.xbt_usd_low_last_24h")
        assert xbt_usd_low_last_24h.state == "0.0003446"

        xbt_usd_high_last_24h = menuai.states.get("sensor.xbt_usd_high_last_24h")
        assert xbt_usd_high_last_24h.state == "0.0003521"

        xbt_usd_opening_price_today = menuai.states.get(
            "sensor.xbt_usd_opening_price_today"
        )
        assert xbt_usd_opening_price_today.state == "0.0003513"


async def test_sensors_available_after_restart(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that all sensors are added again after a restart."""
    with (
        patch(
            "pykrakenapi.KrakenAPI.get_tradable_asset_pairs",
            return_value=TRADEABLE_ASSET_PAIR_RESPONSE,
        ),
        patch(
            "pykrakenapi.KrakenAPI.get_ticker_information",
            return_value=TICKER_INFORMATION_RESPONSE,
        ),
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            options={
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_TRACKED_ASSET_PAIRS: [DEFAULT_TRACKED_ASSET_PAIR],
            },
        )
        entry.add_to_menuai(menuai)

        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, "XBT_USD")},
            name="XBT USD",
            manufacturer="Kraken.com",
            entry_type=dr.DeviceEntryType.SERVICE,
        )

        await menuai.config_entries.async_setup(entry.entry_id)

        await menuai.async_block_till_done()

        menuai.bus.async_fire(EVENT_menuai_START)
        await menuai.async_block_till_done()

        sensor = menuai.states.get("sensor.xbt_usd_ask")
        assert sensor.state == "0.0003494"


async def test_sensors_added_after_config_update(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test that sensors are added when another tracked asset pair is added."""
    with (
        patch(
            "pykrakenapi.KrakenAPI.get_tradable_asset_pairs",
            return_value=TRADEABLE_ASSET_PAIR_RESPONSE,
        ),
        patch(
            "pykrakenapi.KrakenAPI.get_ticker_information",
            return_value=TICKER_INFORMATION_RESPONSE,
        ),
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            options={
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_TRACKED_ASSET_PAIRS: [DEFAULT_TRACKED_ASSET_PAIR],
            },
        )

        entry.add_to_menuai(menuai)

        await menuai.config_entries.async_setup(entry.entry_id)

        await menuai.async_block_till_done()

        menuai.bus.async_fire(EVENT_menuai_START)
        await menuai.async_block_till_done()

        assert menuai.states.get("sensor.xbt_usd_ask")
        assert not menuai.states.get("sensor.ada_xbt_ask")

        menuai.config_entries.async_update_entry(
            entry,
            options={
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_TRACKED_ASSET_PAIRS: [DEFAULT_TRACKED_ASSET_PAIR, "ADA/XBT"],
            },
        )
        freezer.tick(timedelta(seconds=DEFAULT_SCAN_INTERVAL * 2))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

        assert menuai.states.get("sensor.ada_xbt_ask")


async def test_missing_pair_marks_sensor_unavailable(
    menuai: menuai, freezer: FrozenDateTimeFactory
) -> None:
    """Test that a missing tradable asset pair marks the sensor unavailable."""
    with (
        patch(
            "pykrakenapi.KrakenAPI.get_tradable_asset_pairs",
            return_value=TRADEABLE_ASSET_PAIR_RESPONSE,
        ) as tradeable_asset_pairs_mock,
        patch(
            "pykrakenapi.KrakenAPI.get_ticker_information",
            return_value=TICKER_INFORMATION_RESPONSE,
        ) as ticket_information_mock,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            options={
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_TRACKED_ASSET_PAIRS: [DEFAULT_TRACKED_ASSET_PAIR],
            },
        )
        entry.add_to_menuai(menuai)

        await menuai.config_entries.async_setup(entry.entry_id)

        await menuai.async_block_till_done()

        menuai.bus.async_fire(EVENT_menuai_START)
        await menuai.async_block_till_done()

        sensor = menuai.states.get("sensor.xbt_usd_ask")
        assert sensor.state == "0.0003494"

        tradeable_asset_pairs_mock.return_value = (
            MISSING_PAIR_TRADEABLE_ASSET_PAIR_RESPONSE
        )
        ticket_information_mock.side_effect = KrakenAPIError(
            "EQuery:Unknown asset pair"
        )
        freezer.tick(timedelta(seconds=DEFAULT_SCAN_INTERVAL * 2))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

        ticket_information_mock.side_effect = None
        ticket_information_mock.return_value = MISSING_PAIR_TICKER_INFORMATION_RESPONSE
        freezer.tick(timedelta(seconds=DEFAULT_SCAN_INTERVAL * 2))
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

        sensor = menuai.states.get("sensor.xbt_usd_ask")
        assert sensor.state == "unavailable"
