"""Handle MySensors gateways."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable
import logging
import socket
import sys
from typing import Any

from mysensors import BaseAsyncGateway, Message, Sensor, get_const, mysensors
import voluptuous as vol

from menuai.components.mqtt import (
    DOMAIN as MQTT_DOMAIN,
    ReceiveMessage as MQTTReceiveMessage,
    async_publish,
    async_subscribe,
)
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_DEVICE, EVENT_menuai_STOP
from menuai.core import Event, menuai, callback
from menuai.helpers import config_validation as cv
from menuai.helpers.service_info.mqtt import ReceivePayloadType
from menuai.setup import SetupPhases, async_pause_setup
from menuai.util.unit_system import METRIC_SYSTEM

from .const import (
    CONF_BAUD_RATE,
    CONF_GATEWAY_TYPE,
    CONF_GATEWAY_TYPE_MQTT,
    CONF_GATEWAY_TYPE_SERIAL,
    CONF_PERSISTENCE_FILE,
    CONF_RETAIN,
    CONF_TCP_PORT,
    CONF_TOPIC_IN_PREFIX,
    CONF_TOPIC_OUT_PREFIX,
    CONF_VERSION,
    DOMAIN,
    MYSENSORS_GATEWAY_START_TASK,
    ConfGatewayType,
    GatewayId,
)
from .handler import HANDLERS
from .helpers import (
    discover_mysensors_node,
    discover_mysensors_platform,
    validate_child,
    validate_node,
)

_LOGGER = logging.getLogger(__name__)

GATEWAY_READY_TIMEOUT = 20.0
MQTT_COMPONENT = "mqtt"


def is_serial_port(value: str) -> str:
    """Validate that value is a windows serial port or a unix device."""
    if sys.platform.startswith("win"):
        ports = (f"COM{idx + 1}" for idx in range(256))
        if value in ports:
            return value
        raise vol.Invalid(f"{value} is not a serial port")
    return cv.isdevice(value)


def is_socket_address(value: str) -> str:
    """Validate that value is a valid address."""
    try:
        socket.getaddrinfo(value, None)
    except OSError as err:
        raise vol.Invalid("Device is not a valid domain name or ip address") from err
    return value


async def try_connect(
    menuai: menuai, gateway_type: ConfGatewayType, user_input: dict[str, Any]
) -> bool:
    """Try to connect to a gateway and report if it worked."""
    if gateway_type == "MQTT":
        return True  # Do not validate MQTT, as that does not use connection made.
    try:
        gateway_ready = asyncio.Event()

        def on_conn_made(_: BaseAsyncGateway) -> None:
            gateway_ready.set()

        gateway: BaseAsyncGateway | None = await _get_gateway(
            menuai,
            gateway_type,
            device=user_input[CONF_DEVICE],
            version=user_input[CONF_VERSION],
            event_callback=lambda _: None,
            persistence_file=None,
            baud_rate=user_input.get(CONF_BAUD_RATE),
            tcp_port=user_input.get(CONF_TCP_PORT),
            topic_in_prefix=None,
            topic_out_prefix=None,
            retain=False,
            persistence=False,
        )
        if gateway is None:
            return False
        gateway.on_conn_made = on_conn_made

        connect_task = None
        try:
            connect_task = asyncio.create_task(gateway.start())
            async with asyncio.timeout(GATEWAY_READY_TIMEOUT):
                await gateway_ready.wait()
                return True
        except TimeoutError:
            _LOGGER.warning("Try gateway connect failed with timeout")
            return False
        finally:
            if connect_task is not None and not connect_task.done():
                connect_task.cancel()
            await gateway.stop()
    except OSError as err:
        _LOGGER.warning("Try gateway connect failed with exception", exc_info=err)
        return False


async def setup_gateway(
    menuai: menuai, entry: ConfigEntry
) -> BaseAsyncGateway | None:
    """Set up the Gateway for the given ConfigEntry."""

    return await _get_gateway(
        menuai,
        gateway_type=entry.data[CONF_GATEWAY_TYPE],
        device=entry.data[CONF_DEVICE],
        version=entry.data[CONF_VERSION],
        event_callback=_gw_callback_factory(menuai, entry.entry_id),
        persistence_file=entry.data.get(
            CONF_PERSISTENCE_FILE, f"mysensors_{entry.entry_id}.json"
        ),
        baud_rate=entry.data.get(CONF_BAUD_RATE),
        tcp_port=entry.data.get(CONF_TCP_PORT),
        topic_in_prefix=entry.data.get(CONF_TOPIC_IN_PREFIX),
        topic_out_prefix=entry.data.get(CONF_TOPIC_OUT_PREFIX),
        retain=entry.data.get(CONF_RETAIN, False),
    )


async def _get_gateway(
    menuai: menuai,
    gateway_type: ConfGatewayType,
    device: str,
    version: str,
    event_callback: Callable[[Message], None],
    persistence_file: str | None = None,
    baud_rate: int | None = None,
    tcp_port: int | None = None,
    topic_in_prefix: str | None = None,
    topic_out_prefix: str | None = None,
    retain: bool = False,
    persistence: bool = True,
) -> BaseAsyncGateway | None:
    """Return gateway after setup of the gateway."""

    with async_pause_setup(menuai, SetupPhases.WAIT_IMPORT_PACKAGES):
        # get_const will import a const module based on the version
        # so we need to import it here to avoid it being imported
        # in the event loop
        await menuai.async_add_import_executor_job(get_const, version)

    if persistence_file is not None:
        # Interpret relative paths to be in menuai config folder.
        # Absolute paths will be left as they are.
        persistence_file = menuai.config.path(persistence_file)

    if gateway_type == CONF_GATEWAY_TYPE_MQTT:
        # Make sure the mqtt integration is set up.
        # Naive check that doesn't consider config entry state.
        if MQTT_DOMAIN not in menuai.config.components:
            return None

        def pub_callback(topic: str, payload: str, qos: int, retain: bool) -> None:
            """Call MQTT publish function."""
            menuai.async_create_task(async_publish(menuai, topic, payload, qos, retain))

        def sub_callback(
            topic: str, sub_cb: Callable[[str, ReceivePayloadType, int], None], qos: int
        ) -> None:
            """Call MQTT subscribe function."""

            @callback
            def internal_callback(msg: MQTTReceiveMessage) -> None:
                """Call callback."""
                sub_cb(msg.topic, msg.payload, msg.qos)

            menuai.async_create_task(async_subscribe(menuai, topic, internal_callback, qos))

        gateway = mysensors.AsyncMQTTGateway(
            pub_callback,
            sub_callback,
            in_prefix=topic_in_prefix,
            out_prefix=topic_out_prefix,
            retain=retain,
            event_callback=None,
            persistence=persistence,
            persistence_file=persistence_file,
            protocol_version=version,
        )
    elif gateway_type == CONF_GATEWAY_TYPE_SERIAL:
        gateway = mysensors.AsyncSerialGateway(
            device,
            baud=baud_rate,
            event_callback=None,
            persistence=persistence,
            persistence_file=persistence_file,
            protocol_version=version,
        )
    else:
        gateway = mysensors.AsyncTCPGateway(
            device,
            port=tcp_port,
            event_callback=None,
            persistence=persistence,
            persistence_file=persistence_file,
            protocol_version=version,
        )
    gateway.event_callback = event_callback
    gateway.metric = menuai.config.units is METRIC_SYSTEM

    if persistence:
        await gateway.start_persistence()

    return gateway


async def finish_setup(
    menuai: menuai, entry: ConfigEntry, gateway: BaseAsyncGateway
) -> None:
    """Load any persistent devices and platforms and start gateway."""
    await _discover_persistent_devices(menuai, entry, gateway)
    await _gw_start(menuai, entry, gateway)


async def _discover_persistent_devices(
    menuai: menuai, entry: ConfigEntry, gateway: BaseAsyncGateway
) -> None:
    """Discover platforms for devices loaded via persistence file."""
    new_devices = defaultdict(list)
    for node_id in gateway.sensors:
        if not validate_node(gateway, node_id):
            continue
        discover_mysensors_node(menuai, entry.entry_id, node_id)
        node: Sensor = gateway.sensors[node_id]
        for child in node.children.values():  # child is of type ChildSensor
            validated = validate_child(entry.entry_id, gateway, node_id, child)
            for platform, dev_ids in validated.items():
                new_devices[platform].extend(dev_ids)
    _LOGGER.debug("discovering persistent devices: %s", new_devices)
    for platform, dev_ids in new_devices.items():
        discover_mysensors_platform(menuai, entry.entry_id, platform, dev_ids)


async def gw_stop(
    menuai: menuai, entry: ConfigEntry, gateway: BaseAsyncGateway
) -> None:
    """Stop the gateway."""
    connect_task = menuai.data[DOMAIN].pop(
        MYSENSORS_GATEWAY_START_TASK.format(entry.entry_id), None
    )
    if connect_task is not None and not connect_task.done():
        connect_task.cancel()
    await gateway.stop()


async def _gw_start(
    menuai: menuai, entry: ConfigEntry, gateway: BaseAsyncGateway
) -> None:
    """Start the gateway."""
    gateway_ready = asyncio.Event()

    def gateway_connected(_: BaseAsyncGateway) -> None:
        """Handle gateway connected."""
        gateway_ready.set()

    gateway.on_conn_made = gateway_connected
    # Don't use menuai.async_create_task to avoid holding up setup indefinitely.
    menuai.data[DOMAIN][MYSENSORS_GATEWAY_START_TASK.format(entry.entry_id)] = (
        asyncio.create_task(gateway.start())
    )  # store the connect task so it can be cancelled in gw_stop

    async def stop_this_gw(_: Event) -> None:
        """Stop the gateway."""
        await gw_stop(menuai, entry, gateway)

    entry.async_on_unload(
        menuai.bus.async_listen_once(EVENT_menuai_STOP, stop_this_gw),
    )

    if entry.data[CONF_DEVICE] == MQTT_COMPONENT:
        # Gatways connected via mqtt doesn't send gateway ready message.
        return
    try:
        async with asyncio.timeout(GATEWAY_READY_TIMEOUT):
            await gateway_ready.wait()
    except TimeoutError:
        _LOGGER.warning(
            "Gateway %s not connected after %s secs so continuing with setup",
            entry.data[CONF_DEVICE],
            GATEWAY_READY_TIMEOUT,
        )


def _gw_callback_factory(
    menuai: menuai, gateway_id: GatewayId
) -> Callable[[Message], None]:
    """Return a new callback for the gateway."""

    @callback
    def mysensors_callback(msg: Message) -> None:
        """Handle messages from a MySensors gateway.

        All MySenors messages are received here.
        The messages are passed to handler functions depending on their type.
        """
        _LOGGER.debug("Node update: node %s child %s", msg.node_id, msg.child_id)

        msg_type = msg.gateway.const.MessageType(msg.type)
        msg_handler = HANDLERS.get(msg_type.name)

        if msg_handler is None:
            return

        msg_handler(menuai, gateway_id, msg)

    return mysensors_callback
