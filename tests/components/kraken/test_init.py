"""Tests for the kraken integration."""

from unittest.mock import patch

from pykrakenapi.pykrakenapi import CallRateLimitError, KrakenAPIError
import pytest

from menuai.components.kraken.const import DOMAIN
from menuai.core import menuai

from .const import TICKER_INFORMATION_RESPONSE, TRADEABLE_ASSET_PAIR_RESPONSE

from tests.common import MockConfigEntry


async def test_unload_entry(menuai: menuai) -> None:
    """Test unload for Kraken."""
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
        entry = MockConfigEntry(domain=DOMAIN)
        entry.add_to_menuai(menuai)

        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
        assert await menuai.config_entries.async_unload(entry.entry_id)
        assert DOMAIN not in menuai.data


async def test_unknown_error(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test unload for Kraken."""
    with (
        patch(
            "pykrakenapi.KrakenAPI.get_tradable_asset_pairs",
            return_value=TRADEABLE_ASSET_PAIR_RESPONSE,
        ),
        patch(
            "pykrakenapi.KrakenAPI.get_ticker_information",
            side_effect=KrakenAPIError("EQuery: Error"),
        ),
    ):
        entry = MockConfigEntry(domain=DOMAIN)
        entry.add_to_menuai(menuai)

        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
        assert "Unable to fetch data from Kraken.com:" in caplog.text


async def test_callrate_limit(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test unload for Kraken."""
    with (
        patch(
            "pykrakenapi.KrakenAPI.get_tradable_asset_pairs",
            return_value=TRADEABLE_ASSET_PAIR_RESPONSE,
        ),
        patch(
            "pykrakenapi.KrakenAPI.get_ticker_information",
            side_effect=CallRateLimitError(),
        ),
    ):
        entry = MockConfigEntry(domain=DOMAIN)
        entry.add_to_menuai(menuai)

        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
        assert (
            "Exceeded the Kraken.com call rate limit. Increase the update interval to"
            " prevent this error" in caplog.text
        )
