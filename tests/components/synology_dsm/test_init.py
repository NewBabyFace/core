"""Tests for the Synology DSM component."""

from unittest.mock import MagicMock, patch

from synology_dsm.exceptions import SynologyDSMLoginInvalidException

from menuai.components.synology_dsm.const import (
    CONF_BACKUP_PATH,
    CONF_BACKUP_SHARE,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    SERVICES,
)
from menuai.const import (
    CONF_HOST,
    CONF_MAC,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .consts import HOST, MACS, PASSWORD, PORT, USE_SSL, USERNAME

from tests.common import MockConfigEntry


async def test_services_registered(menuai: menuai, mock_dsm: MagicMock) -> None:
    """Test if all services are registered."""
    with (
        patch(
            "menuai.components.synology_dsm.common.SynologyDSM",
            return_value=mock_dsm,
        ),
        patch("menuai.components.synology_dsm.PLATFORMS", return_value=[]),
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: HOST,
                CONF_PORT: PORT,
                CONF_SSL: USE_SSL,
                CONF_USERNAME: USERNAME,
                CONF_PASSWORD: PASSWORD,
                CONF_MAC: MACS[0],
            },
        )
        entry.add_to_menuai(menuai)
        assert await menuai.config_entries.async_setup(entry.entry_id)
        for service in SERVICES:
            assert menuai.services.has_service(DOMAIN, service)


async def test_reauth_triggered(menuai: menuai) -> None:
    """Test if reauthentication flow is triggered."""
    with (
        patch(
            "menuai.components.synology_dsm.SynoApi.async_setup",
            side_effect=SynologyDSMLoginInvalidException(USERNAME),
        ),
        patch(
            "menuai.components.synology_dsm.config_flow.SynologyDSMFlowHandler.async_step_reauth",
            return_value={
                "type": FlowResultType.FORM,
                "flow_id": "mock_flow",
                "step_id": "reauth_confirm",
            },
        ) as mock_async_step_reauth,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: HOST,
                CONF_PORT: PORT,
                CONF_SSL: USE_SSL,
                CONF_USERNAME: USERNAME,
                CONF_PASSWORD: PASSWORD,
                CONF_MAC: MACS[0],
            },
        )
        entry.add_to_menuai(menuai)
        assert not await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()
        mock_async_step_reauth.assert_called_once()


async def test_config_entry_migrations(
    menuai: menuai, mock_dsm: MagicMock
) -> None:
    """Test if reauthentication flow is triggered."""
    with (
        patch(
            "menuai.components.synology_dsm.common.SynologyDSM",
            return_value=mock_dsm,
        ),
        patch("menuai.components.synology_dsm.PLATFORMS", return_value=[]),
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_HOST: HOST,
                CONF_PORT: PORT,
                CONF_SSL: USE_SSL,
                CONF_USERNAME: USERNAME,
                CONF_PASSWORD: PASSWORD,
                CONF_MAC: MACS[0],
            },
            options={CONF_SCAN_INTERVAL: 30},
        )
        entry.add_to_menuai(menuai)

        assert CONF_VERIFY_SSL not in entry.data
        assert CONF_BACKUP_SHARE not in entry.options
        assert CONF_BACKUP_PATH not in entry.options

        assert await menuai.config_entries.async_setup(entry.entry_id)

        assert entry.data[CONF_VERIFY_SSL] == DEFAULT_VERIFY_SSL
        assert CONF_SCAN_INTERVAL not in entry.options
        assert entry.options[CONF_BACKUP_SHARE] is None
        assert entry.options[CONF_BACKUP_PATH] is None
