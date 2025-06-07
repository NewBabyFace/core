"""Tests for the Start.ca sensor platform."""

from http import HTTPStatus

from menuai.components.startca.sensor import StartcaData
from menuai.const import ATTR_UNIT_OF_MEASUREMENT, PERCENTAGE, UnitOfInformation
from menuai.core import menuai
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.setup import async_setup_component

from tests.test_util.aiohttp import AiohttpClientMocker


async def test_capped_setup(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the default setup."""
    config = {
        "platform": "startca",
        "api_key": "NOTAKEY",
        "total_bandwidth": 400,
        "monitored_variables": [
            "usage",
            "usage_gb",
            "limit",
            "used_download",
            "used_upload",
            "used_total",
            "grace_download",
            "grace_upload",
            "grace_total",
            "total_download",
            "total_upload",
            "used_remaining",
        ],
    }

    result = (
        '<?xml version="1.0" encoding="ISO-8859-15"?>'
        "<usage>"
        "<version>1.1</version>"
        "<total> <!-- total actual usage -->"
        "<download>304946829777</download>"
        "<upload>6480700153</upload>"
        "</total>"
        "<used> <!-- part of usage that counts against quota -->"
        "<download>304946829777</download>"
        "<upload>6480700153</upload>"
        "</used>"
        "<grace> <!-- part of usage that is free -->"
        "<download>304946829777</download>"
        "<upload>6480700153</upload>"
        "</grace>"
        "</usage>"
    )
    aioclient_mock.get(
        "https://www.start.ca/support/usage/api?key=NOTAKEY", text=result
    )

    await async_setup_component(menuai, "sensor", {"sensor": config})
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.start_ca_usage_ratio")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == PERCENTAGE
    assert state.state == "76.24"

    state = menuai.states.get("sensor.start_ca_usage")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "304.95"

    state = menuai.states.get("sensor.start_ca_data_limit")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "400"

    state = menuai.states.get("sensor.start_ca_used_download")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "304.95"

    state = menuai.states.get("sensor.start_ca_used_upload")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "6.48"

    state = menuai.states.get("sensor.start_ca_used_total")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "311.43"

    state = menuai.states.get("sensor.start_ca_grace_download")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "304.95"

    state = menuai.states.get("sensor.start_ca_grace_upload")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "6.48"

    state = menuai.states.get("sensor.start_ca_grace_total")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "311.43"

    state = menuai.states.get("sensor.start_ca_total_download")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "304.95"

    state = menuai.states.get("sensor.start_ca_total_upload")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "6.48"

    state = menuai.states.get("sensor.start_ca_remaining")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "95.05"


async def test_unlimited_setup(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test the default setup."""
    config = {
        "platform": "startca",
        "api_key": "NOTAKEY",
        "total_bandwidth": 0,
        "monitored_variables": [
            "usage",
            "usage_gb",
            "limit",
            "used_download",
            "used_upload",
            "used_total",
            "grace_download",
            "grace_upload",
            "grace_total",
            "total_download",
            "total_upload",
            "used_remaining",
        ],
    }

    result = (
        '<?xml version="1.0" encoding="ISO-8859-15"?>'
        "<usage>"
        "<version>1.1</version>"
        "<total> <!-- total actual usage -->"
        "<download>304946829777</download>"
        "<upload>6480700153</upload>"
        "</total>"
        "<used> <!-- part of usage that counts against quota -->"
        "<download>0</download>"
        "<upload>0</upload>"
        "</used>"
        "<grace> <!-- part of usage that is free -->"
        "<download>304946829777</download>"
        "<upload>6480700153</upload>"
        "</grace>"
        "</usage>"
    )
    aioclient_mock.get(
        "https://www.start.ca/support/usage/api?key=NOTAKEY", text=result
    )

    await async_setup_component(menuai, "sensor", {"sensor": config})
    await menuai.async_block_till_done()

    # These sensors should not be created for unlimited setups
    assert menuai.states.get("sensor.start_ca_usage_ratio") is None
    assert menuai.states.get("sensor.start_ca_data_limit") is None
    assert menuai.states.get("sensor.start_ca_remaining") is None

    state = menuai.states.get("sensor.start_ca_usage")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "0.0"

    state = menuai.states.get("sensor.start_ca_used_download")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "0.0"

    state = menuai.states.get("sensor.start_ca_used_upload")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "0.0"

    state = menuai.states.get("sensor.start_ca_used_total")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "0.0"

    state = menuai.states.get("sensor.start_ca_grace_download")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "304.95"

    state = menuai.states.get("sensor.start_ca_grace_upload")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "6.48"

    state = menuai.states.get("sensor.start_ca_grace_total")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "311.43"

    state = menuai.states.get("sensor.start_ca_total_download")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "304.95"

    state = menuai.states.get("sensor.start_ca_total_upload")
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfInformation.GIGABYTES
    assert state.state == "6.48"


async def test_bad_return_code(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test handling a return code that isn't HTTP OK."""
    aioclient_mock.get(
        "https://www.start.ca/support/usage/api?key=NOTAKEY",
        status=HTTPStatus.NOT_FOUND,
    )

    scd = StartcaData(menuai.loop, async_get_clientsession(menuai), "NOTAKEY", 400)

    result = await scd.async_update()
    assert result is False


async def test_bad_json_decode(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test decoding invalid json result."""
    aioclient_mock.get(
        "https://www.start.ca/support/usage/api?key=NOTAKEY", text="this is not xml"
    )

    scd = StartcaData(menuai.loop, async_get_clientsession(menuai), "NOTAKEY", 400)

    result = await scd.async_update()
    assert result is False
