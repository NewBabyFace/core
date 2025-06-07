"""Test the Reolink util functions."""

from unittest.mock import MagicMock, patch

import pytest
from reolink_aio.exceptions import (
    ApiError,
    CredentialsInvalidError,
    InvalidContentTypeError,
    InvalidParameterError,
    LoginError,
    NoDataError,
    NotSupportedError,
    ReolinkConnectionError,
    ReolinkError,
    ReolinkTimeoutError,
    SubscriptionError,
    UnexpectedDataError,
)

from menuai.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.components.reolink.const import DOMAIN
from menuai.components.reolink.util import get_device_uid_and_ch
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError, ServiceValidationError
from menuai.helpers import device_registry as dr

from .conftest import TEST_NVR_NAME, TEST_UID, TEST_UID_CAM

from tests.common import MockConfigEntry

DEV_ID_NVR = f"{TEST_UID}_{TEST_UID_CAM}"
DEV_ID_STANDALONE_CAM = f"{TEST_UID_CAM}"


@pytest.mark.parametrize(
    ("side_effect", "expected"),
    [
        (
            ApiError("Test error"),
            menuaiError(translation_key="api_error"),
        ),
        (
            ApiError("Test error", translation_key="firmware_rate_limit"),
            menuaiError(translation_key="firmware_rate_limit"),
        ),
        (
            ApiError("Test error", translation_key="not_in_strings.json"),
            menuaiError(translation_key="api_error"),
        ),
        (
            CredentialsInvalidError("Test error"),
            menuaiError(translation_key="invalid_credentials"),
        ),
        (
            InvalidContentTypeError("Test error"),
            menuaiError(translation_key="invalid_content_type"),
        ),
        (
            InvalidParameterError("Test error"),
            ServiceValidationError(translation_key="invalid_parameter"),
        ),
        (
            LoginError("Test error"),
            menuaiError(translation_key="login_error"),
        ),
        (
            NoDataError("Test error"),
            menuaiError(translation_key="no_data"),
        ),
        (
            NotSupportedError("Test error"),
            menuaiError(translation_key="not_supported"),
        ),
        (
            ReolinkConnectionError("Test error"),
            menuaiError(translation_key="connection_error"),
        ),
        (
            ReolinkError("Test error"),
            menuaiError(translation_key="unexpected"),
        ),
        (
            ReolinkTimeoutError("Test error"),
            menuaiError(translation_key="timeout"),
        ),
        (
            SubscriptionError("Test error"),
            menuaiError(translation_key="subscription_error"),
        ),
        (
            UnexpectedDataError("Test error"),
            menuaiError(translation_key="unexpected_data"),
        ),
    ],
)
async def test_try_function(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
    side_effect: ReolinkError,
    expected: menuaiError,
) -> None:
    """Test try_function error translations using number entity."""
    reolink_connect.volume.return_value = 80

    with patch("menuai.components.reolink.PLATFORMS", [Platform.NUMBER]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    entity_id = f"{Platform.NUMBER}.{TEST_NVR_NAME}_volume"

    reolink_connect.set_volume.side_effect = side_effect
    with pytest.raises(expected.__class__) as err:
        await menuai.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: 50},
            blocking=True,
        )

    assert err.value.translation_key == expected.translation_key

    reolink_connect.set_volume.reset_mock(side_effect=True)


@pytest.mark.parametrize(
    ("identifiers"),
    [
        ({(DOMAIN, DEV_ID_NVR), (DOMAIN, DEV_ID_STANDALONE_CAM)}),
        ({(DOMAIN, DEV_ID_STANDALONE_CAM), (DOMAIN, DEV_ID_NVR)}),
    ],
)
async def test_get_device_uid_and_ch(
    menuai: menuai,
    config_entry: MockConfigEntry,
    reolink_connect: MagicMock,
    device_registry: dr.DeviceRegistry,
    identifiers: set[tuple[str, str]],
) -> None:
    """Test get_device_uid_and_ch with multiple identifiers."""
    reolink_connect.channels = [0]

    dev_entry = device_registry.async_get_or_create(
        identifiers=identifiers,
        config_entry_id=config_entry.entry_id,
        disabled_by=None,
    )

    # setup CH 0 and host entities/device
    with patch("menuai.components.reolink.PLATFORMS", [Platform.SWITCH]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    result = get_device_uid_and_ch(dev_entry, config_entry.runtime_data.host)
    # always get the uid and channel form the DEV_ID_NVR since is_nvr = True
    assert result == ([TEST_UID, TEST_UID_CAM], 0, False)
