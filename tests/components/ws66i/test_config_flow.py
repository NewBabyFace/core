"""Test the WS66i 6-Zone Amplifier config flow."""

from unittest.mock import patch

from menuai import config_entries
from menuai.components.ws66i.const import (
    CONF_SOURCE_1,
    CONF_SOURCE_2,
    CONF_SOURCE_3,
    CONF_SOURCE_4,
    CONF_SOURCE_5,
    CONF_SOURCE_6,
    CONF_SOURCES,
    DOMAIN,
    INIT_OPTIONS_DEFAULT,
)
from menuai.const import CONF_IP_ADDRESS
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .test_media_player import AttrDict

from tests.common import MockConfigEntry

CONFIG = {CONF_IP_ADDRESS: "1.1.1.1"}


async def test_form(menuai: menuai) -> None:
    """Test we get the form."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "menuai.components.ws66i.config_flow.get_ws66i",
        ) as mock_ws66i,
        patch(
            "menuai.components.ws66i.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        ws66i_instance = mock_ws66i.return_value

        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], CONFIG
        )
        await menuai.async_block_till_done()

        ws66i_instance.open.assert_called_once()
        ws66i_instance.close.assert_called_once()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "WS66i Amp"
    assert result2["data"] == {CONF_IP_ADDRESS: CONFIG[CONF_IP_ADDRESS]}

    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(menuai: menuai) -> None:
    """Test cannot connect error."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("menuai.components.ws66i.config_flow.get_ws66i") as mock_ws66i:
        ws66i_instance = mock_ws66i.return_value
        ws66i_instance.open.side_effect = ConnectionError
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], CONFIG
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_wrong_ip(menuai: menuai) -> None:
    """Test cannot connect error with bad IP."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("menuai.components.ws66i.config_flow.get_ws66i") as mock_ws66i:
        ws66i_instance = mock_ws66i.return_value
        ws66i_instance.zone_status.return_value = None
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], CONFIG
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_generic_exception(menuai: menuai) -> None:
    """Test generic exception."""
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("menuai.components.ws66i.config_flow.get_ws66i") as mock_ws66i:
        ws66i_instance = mock_ws66i.return_value
        ws66i_instance.open.side_effect = Exception
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], CONFIG
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}


async def test_options_flow(menuai: menuai) -> None:
    """Test config flow options."""
    conf = {CONF_IP_ADDRESS: "1.1.1.1", CONF_SOURCES: INIT_OPTIONS_DEFAULT}

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=conf,
        options={CONF_SOURCES: INIT_OPTIONS_DEFAULT},
    )
    config_entry.add_to_menuai(menuai)

    with patch("menuai.components.ws66i.get_ws66i") as mock_ws66i:
        ws66i_instance = mock_ws66i.return_value
        ws66i_instance.zone_status.return_value = AttrDict(
            power=True, volume=0, mute=True, source=1, treble=0, bass=0, balance=10
        )
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

        result = await menuai.config_entries.options.async_init(config_entry.entry_id)

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

        result = await menuai.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_SOURCE_1: "one",
                CONF_SOURCE_2: "too",
                CONF_SOURCE_3: "tree",
                CONF_SOURCE_4: "for",
                CONF_SOURCE_5: "feeve",
                CONF_SOURCE_6: "roku",
            },
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert config_entry.options[CONF_SOURCES] == {
            "1": "one",
            "2": "too",
            "3": "tree",
            "4": "for",
            "5": "feeve",
            "6": "roku",
        }
