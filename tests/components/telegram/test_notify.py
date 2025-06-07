"""The tests for the telegram.notify platform."""

from unittest.mock import patch

from menuai import config as menuai_config
from menuai.components import notify
from menuai.components.telegram import DOMAIN
from menuai.const import SERVICE_RELOAD
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import get_fixture_path


async def test_reload_notify(menuai: menuai) -> None:
    """Verify we can reload the notify service."""

    with patch("menuai.components.telegram_bot.async_setup", return_value=True):
        assert await async_setup_component(
            menuai,
            notify.DOMAIN,
            {
                notify.DOMAIN: [
                    {
                        "name": DOMAIN,
                        "platform": DOMAIN,
                        "chat_id": 1,
                    },
                ]
            },
        )
        await menuai.async_block_till_done()

    assert menuai.services.has_service(notify.DOMAIN, DOMAIN)

    yaml_path = get_fixture_path("configuration.yaml", "telegram")
    with patch.object(menuai_config, "YAML_CONFIG_FILE", yaml_path):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await menuai.async_block_till_done()

    assert not menuai.services.has_service(notify.DOMAIN, DOMAIN)
    assert menuai.services.has_service(notify.DOMAIN, "telegram_reloaded")
