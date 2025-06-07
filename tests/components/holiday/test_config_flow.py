"""Test the Holiday config flow."""

from datetime import datetime
from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
from holidays import UNOFFICIAL
import pytest

from menuai import config_entries
from menuai.components.holiday.const import (
    CONF_CATEGORIES,
    CONF_PROVINCE,
    DOMAIN,
)
from menuai.const import CONF_COUNTRY, STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType
from menuai.util import dt as dt_util

from tests.common import MockConfigEntry


async def test_form(menuai: menuai, mock_setup_entry: AsyncMock) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_COUNTRY: "DE",
        },
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.FORM

    result3 = await menuai.config_entries.flow.async_configure(
        result2["flow_id"],
        {
            CONF_PROVINCE: "BW",
        },
    )
    await menuai.async_block_till_done()

    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == "Germany, BW"
    assert result3["data"] == {
        "country": "DE",
        "province": "BW",
    }
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.usefixtures("mock_setup_entry")
async def test_form_no_subdivision(menuai: menuai) -> None:
    """Test we get the forms correctly without subdivision."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_COUNTRY: "SE",
        },
    )
    await menuai.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Sweden"
    assert result2["data"] == {
        "country": "SE",
    }


@pytest.mark.usefixtures("mock_setup_entry")
async def test_form_translated_title(menuai: menuai) -> None:
    """Test the title gets translated."""
    menuai.config.language = "de"

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_COUNTRY: "SE",
        },
    )
    await menuai.async_block_till_done()

    assert result2["title"] == "Schweden"


@pytest.mark.usefixtures("mock_setup_entry")
async def test_single_combination_country_province(menuai: menuai) -> None:
    """Test that configuring more than one instance is rejected."""
    data_de = {
        CONF_COUNTRY: "DE",
        CONF_PROVINCE: "BW",
    }
    data_se = {
        CONF_COUNTRY: "SE",
    }
    MockConfigEntry(domain=DOMAIN, data=data_de).add_to_menuai(menuai)
    MockConfigEntry(domain=DOMAIN, data=data_se).add_to_menuai(menuai)

    # Test for country without subdivisions
    result_se = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=data_se,
    )
    assert result_se["type"] is FlowResultType.ABORT
    assert result_se["reason"] == "already_configured"

    # Test for country with subdivisions
    result_de_step1 = await menuai.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=data_de,
    )
    assert result_de_step1["type"] is FlowResultType.FORM

    result_de_step2 = await menuai.config_entries.flow.async_configure(
        result_de_step1["flow_id"],
        {
            CONF_PROVINCE: data_de[CONF_PROVINCE],
        },
    )
    assert result_de_step2["type"] is FlowResultType.ABORT
    assert result_de_step2["reason"] == "already_configured"


@pytest.mark.usefixtures("mock_setup_entry")
async def test_form_babel_unresolved_language(menuai: menuai) -> None:
    """Test the config flow if using not babel supported language."""
    menuai.config.language = "en-XX"

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_COUNTRY: "SE",
        },
    )
    await menuai.async_block_till_done()

    assert result["title"] == "Sweden"

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_COUNTRY: "DE",
        },
    )
    await menuai.async_block_till_done()

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PROVINCE: "BW",
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Germany, BW"
    assert result["data"] == {
        "country": "DE",
        "province": "BW",
    }


@pytest.mark.usefixtures("mock_setup_entry")
async def test_form_babel_replace_dash_with_underscore(menuai: menuai) -> None:
    """Test the config flow if using language with dash."""
    menuai.config.language = "en-GB"

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_COUNTRY: "SE",
        },
    )
    await menuai.async_block_till_done()

    assert result["title"] == "Sweden"

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_COUNTRY: "DE",
        },
    )
    await menuai.async_block_till_done()

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PROVINCE: "BW",
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Germany, BW"
    assert result["data"] == {
        "country": "DE",
        "province": "BW",
    }


@pytest.mark.usefixtures("mock_setup_entry")
async def test_reconfigure(menuai: menuai) -> None:
    """Test reconfigure flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Germany, BW",
        data={"country": "DE", "province": "BW"},
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PROVINCE: "NW",
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    entry = menuai.config_entries.async_get_entry(entry.entry_id)
    assert entry.title == "Germany, NW"
    assert entry.data == {"country": "DE", "province": "NW"}


@pytest.mark.usefixtures("mock_setup_entry")
async def test_reconfigure_with_categories(menuai: menuai) -> None:
    """Test reconfigure flow with categories."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Unites States, TX",
        data={"country": "US", "province": "TX"},
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PROVINCE: "AL",
            CONF_CATEGORIES: [UNOFFICIAL],
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    entry = menuai.config_entries.async_get_entry(entry.entry_id)
    assert entry.title == "United States, AL"
    assert entry.data == {CONF_COUNTRY: "US", CONF_PROVINCE: "AL"}
    assert entry.options == {CONF_CATEGORIES: ["unofficial"]}


@pytest.mark.usefixtures("mock_setup_entry")
async def test_reconfigure_incorrect_language(menuai: menuai) -> None:
    """Test reconfigure flow default to English."""
    menuai.config.language = "en-XX"

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Germany, BW",
        data={"country": "DE", "province": "BW"},
    )
    entry.add_to_menuai(menuai)

    result = await entry.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PROVINCE: "NW",
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    entry = menuai.config_entries.async_get_entry(entry.entry_id)
    assert entry.title == "Germany, NW"
    assert entry.data == {"country": "DE", "province": "NW"}


@pytest.mark.usefixtures("mock_setup_entry")
async def test_reconfigure_entry_exists(menuai: menuai) -> None:
    """Test reconfigure flow stops if other entry already exist."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Germany, BW",
        data={"country": "DE", "province": "BW"},
    )
    entry.add_to_menuai(menuai)
    entry2 = MockConfigEntry(
        domain=DOMAIN,
        title="Germany, NW",
        data={"country": "DE", "province": "NW"},
    )
    entry2.add_to_menuai(menuai)

    result = await entry.start_reconfigure_flow(menuai)
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PROVINCE: "NW",
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    entry = menuai.config_entries.async_get_entry(entry.entry_id)
    assert entry.title == "Germany, BW"
    assert entry.data == {"country": "DE", "province": "BW"}


async def test_form_with_options(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the flow with configuring options."""
    await menuai.config.async_set_time_zone("America/Chicago")
    zone = await dt_util.async_get_time_zone("America/Chicago")
    # Oct 31st is a Friday. Unofficial holiday as Halloween
    freezer.move_to(datetime(2024, 10, 31, 12, 0, 0, tzinfo=zone))

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_COUNTRY: "US",
        },
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.FORM

    result = await menuai.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_PROVINCE: "TX",
            CONF_CATEGORIES: [UNOFFICIAL],
        },
    )
    await menuai.async_block_till_done(wait_background_tasks=True)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "United States, TX"
    assert result["data"] == {
        CONF_COUNTRY: "US",
        CONF_PROVINCE: "TX",
    }
    assert result["options"] == {
        CONF_CATEGORIES: ["unofficial"],
    }

    state = menuai.states.get("calendar.united_states_tx")
    assert state
    assert state.state == STATE_ON

    entries = menuai.config_entries.async_entries(DOMAIN)
    entry = entries[0]
    result = await menuai.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await menuai.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_CATEGORIES: []},
    )
    await menuai.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_CATEGORIES: [],
    }

    state = menuai.states.get("calendar.united_states_tx")
    assert state
    assert state.state == STATE_OFF


@pytest.mark.usefixtures("mock_setup_entry")
async def test_options_abort_no_categories(menuai: menuai) -> None:
    """Test the options flow abort if no categories to select."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_COUNTRY: "SE"},
        title="Sweden",
    )
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    result = await menuai.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_categories"
