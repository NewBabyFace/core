"""Test the flo config flow."""

from http import HTTPStatus
import json
import time
from unittest.mock import patch

import pytest

from menuai import config_entries
from menuai.components.flo.const import DOMAIN
from menuai.const import CONTENT_TYPE_JSON
from menuai.core import menuai
from menuai.data_entry_flow import FlowResultType

from .common import TEST_EMAIL_ADDRESS, TEST_PASSWORD, TEST_TOKEN, TEST_USER_ID

from tests.test_util.aiohttp import AiohttpClientMocker


@pytest.mark.usefixtures("aioclient_mock_fixture")
async def test_form(menuai: menuai) -> None:
    """Test we get the form."""

    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "menuai.components.flo.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        result2 = await menuai.config_entries.flow.async_configure(
            result["flow_id"], {"username": TEST_USER_ID, "password": TEST_PASSWORD}
        )

        assert result2["type"] is FlowResultType.CREATE_ENTRY
        assert result2["title"] == TEST_USER_ID
        assert result2["data"] == {"username": TEST_USER_ID, "password": TEST_PASSWORD}
        await menuai.async_block_till_done()
        assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test we handle cannot connect error."""
    now = round(time.time())
    # Mocks a failed login response for flo.
    aioclient_mock.post(
        "https://api.meetflo.com/api/v1/users/auth",
        json=json.dumps(
            {
                "token": TEST_TOKEN,
                "tokenPayload": {
                    "user": {"user_id": TEST_USER_ID, "email": TEST_EMAIL_ADDRESS},
                    "timestamp": now,
                },
                "tokenExpiration": 86400,
                "timeNow": now,
            }
        ),
        headers={"Content-Type": CONTENT_TYPE_JSON},
        status=HTTPStatus.BAD_REQUEST,
    )
    result = await menuai.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await menuai.config_entries.flow.async_configure(
        result["flow_id"], {"username": "test-username", "password": "test-password"}
    )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}
