"""Test Telegram broadcast."""

from menuai.core import menuai
from menuai.setup import async_setup_component


async def test_setup(menuai: menuai, mock_external_calls: None) -> None:
    """Test setting up Telegram broadcast."""
    assert await async_setup_component(
        menuai,
        "telegram_bot",
        {
            "telegram_bot": {
                "platform": "broadcast",
                "api_key": "1234567890:ABC",
                "allowed_chat_ids": [1],
            }
        },
    )
    await menuai.async_block_till_done()

    assert menuai.services.has_service("telegram_bot", "send_message") is True
