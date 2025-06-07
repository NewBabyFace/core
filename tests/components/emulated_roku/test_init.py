"""Test emulated_roku component setup process."""

from unittest.mock import AsyncMock, Mock, patch

from menuai.components import emulated_roku
from menuai.core import menuai
from menuai.setup import async_setup_component


async def test_config_required_fields(menuai: menuai) -> None:
    """Test that configuration is successful with required fields."""
    with (
        patch.object(emulated_roku, "configured_servers", return_value=[]),
        patch(
            "menuai.components.emulated_roku.binding.EmulatedRokuServer",
            return_value=Mock(start=AsyncMock(), close=AsyncMock()),
        ),
    ):
        assert (
            await async_setup_component(
                menuai,
                emulated_roku.DOMAIN,
                {
                    emulated_roku.DOMAIN: {
                        emulated_roku.CONF_SERVERS: [
                            {
                                emulated_roku.CONF_NAME: "Emulated Roku Test",
                                emulated_roku.CONF_LISTEN_PORT: 8060,
                            }
                        ]
                    }
                },
            )
            is True
        )


async def test_config_already_registered_not_configured(menuai: menuai) -> None:
    """Test that an already registered name causes the entry to be ignored."""
    with (
        patch(
            "menuai.components.emulated_roku.binding.EmulatedRokuServer",
            return_value=Mock(start=AsyncMock(), close=AsyncMock()),
        ) as instantiate,
        patch.object(
            emulated_roku, "configured_servers", return_value=["Emulated Roku Test"]
        ),
    ):
        assert (
            await async_setup_component(
                menuai,
                emulated_roku.DOMAIN,
                {
                    emulated_roku.DOMAIN: {
                        emulated_roku.CONF_SERVERS: [
                            {
                                emulated_roku.CONF_NAME: "Emulated Roku Test",
                                emulated_roku.CONF_LISTEN_PORT: 8060,
                            }
                        ]
                    }
                },
            )
            is True
        )

    assert len(instantiate.mock_calls) == 0


async def test_setup_entry_successful(menuai: menuai) -> None:
    """Test setup entry is successful."""
    entry = Mock()
    entry.data = {
        emulated_roku.CONF_NAME: "Emulated Roku Test",
        emulated_roku.CONF_LISTEN_PORT: 8060,
        emulated_roku.CONF_HOST_IP: "1.2.3.5",
        emulated_roku.CONF_ADVERTISE_IP: "1.2.3.4",
        emulated_roku.CONF_ADVERTISE_PORT: 8071,
        emulated_roku.CONF_UPNP_BIND_MULTICAST: False,
    }

    with patch(
        "menuai.components.emulated_roku.binding.EmulatedRokuServer",
        return_value=Mock(start=AsyncMock(), close=AsyncMock()),
    ) as instantiate:
        assert await emulated_roku.async_setup_entry(menuai, entry) is True

    assert len(instantiate.mock_calls) == 1


async def test_unload_entry(menuai: menuai) -> None:
    """Test being able to unload an entry."""
    entry = Mock()
    entry.data = {
        "name": "Emulated Roku Test",
        "listen_port": 8060,
        emulated_roku.CONF_HOST_IP: "1.2.3.5",
    }

    with patch(
        "menuai.components.emulated_roku.binding.EmulatedRokuServer",
        return_value=Mock(start=AsyncMock(), close=AsyncMock()),
    ):
        assert await emulated_roku.async_setup_entry(menuai, entry) is True

    await menuai.async_block_till_done()

    assert await emulated_roku.async_unload_entry(menuai, entry)
