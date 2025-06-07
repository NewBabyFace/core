"""Define tests for the QNAP QSW init."""

from unittest.mock import patch

from aioqsw.exceptions import APIError

from menuai.components.qnap_qsw.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from .util import CONFIG

from tests.common import MockConfigEntry


async def test_firmware_check_error(menuai: menuai) -> None:
    """Test firmware update check error."""

    config_entry = MockConfigEntry(
        domain=DOMAIN, unique_id="qsw_unique_id", data=CONFIG
    )
    config_entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.qnap_qsw.QnapQswApi.check_firmware",
            side_effect=APIError,
        ),
        patch(
            "menuai.components.qnap_qsw.QnapQswApi.validate",
            return_value=None,
        ),
        patch(
            "menuai.components.qnap_qsw.QnapQswApi.update",
            return_value=None,
        ),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        assert config_entry.state is ConfigEntryState.LOADED


async def test_unload_entry(menuai: menuai) -> None:
    """Test unload."""

    config_entry = MockConfigEntry(
        domain=DOMAIN, unique_id="qsw_unique_id", data=CONFIG
    )
    config_entry.add_to_menuai(menuai)

    with (
        patch(
            "menuai.components.qnap_qsw.QnapQswApi.check_firmware",
            return_value=None,
        ),
        patch(
            "menuai.components.qnap_qsw.QnapQswApi.validate",
            return_value=None,
        ),
        patch(
            "menuai.components.qnap_qsw.QnapQswApi.update",
            return_value=None,
        ),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
        assert config_entry.state is ConfigEntryState.LOADED

        await menuai.config_entries.async_unload(config_entry.entry_id)
        await menuai.async_block_till_done()
        assert config_entry.state is ConfigEntryState.NOT_LOADED
