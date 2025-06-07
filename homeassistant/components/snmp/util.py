"""Support for displaying collected data over SNMP."""

from __future__ import annotations

import logging

from pysnmp.hlapi.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    Udp6TransportTarget,
    UdpTransportTarget,
    UsmUserData,
)
from pysnmp.hlapi.asyncio.cmdgen import lcd, vbProcessor
from pysnmp.smi.builder import MibBuilder

from menuai.const import EVENT_menuai_STOP
from menuai.core import Event, menuai, callback
from menuai.helpers.singleton import singleton

DATA_SNMP_ENGINE = "snmp_engine"

_LOGGER = logging.getLogger(__name__)

type CommandArgsType = tuple[
    SnmpEngine,
    UsmUserData | CommunityData,
    UdpTransportTarget | Udp6TransportTarget,
    ContextData,
]


type RequestArgsType = tuple[
    SnmpEngine,
    UsmUserData | CommunityData,
    UdpTransportTarget | Udp6TransportTarget,
    ContextData,
    ObjectType,
]


async def async_create_command_cmd_args(
    menuai: menuai,
    auth_data: UsmUserData | CommunityData,
    target: UdpTransportTarget | Udp6TransportTarget,
) -> CommandArgsType:
    """Create command arguments.

    The ObjectType needs to be created dynamically by the caller.
    """
    engine = await async_get_snmp_engine(menuai)
    return (engine, auth_data, target, ContextData())


async def async_create_request_cmd_args(
    menuai: menuai,
    auth_data: UsmUserData | CommunityData,
    target: UdpTransportTarget | Udp6TransportTarget,
    object_id: str,
) -> RequestArgsType:
    """Create request arguments.

    The same ObjectType is used for all requests.
    """
    engine, auth_data, target, context_data = await async_create_command_cmd_args(
        menuai, auth_data, target
    )
    object_type = ObjectType(ObjectIdentity(object_id))
    return (engine, auth_data, target, context_data, object_type)


@singleton(DATA_SNMP_ENGINE)
async def async_get_snmp_engine(menuai: menuai) -> SnmpEngine:
    """Get the SNMP engine."""
    engine = await menuai.async_add_executor_job(_get_snmp_engine)

    @callback
    def _async_shutdown_listener(ev: Event) -> None:
        _LOGGER.debug("Unconfiguring SNMP engine")
        lcd.unconfigure(engine, None)

    menuai.bus.async_listen_once(EVENT_menuai_STOP, _async_shutdown_listener)
    return engine


def _get_snmp_engine() -> SnmpEngine:
    """Return a cached instance of SnmpEngine."""
    engine = SnmpEngine()
    mib_controller = vbProcessor.getMibViewController(engine)
    # Actually load the MIBs from disk so we do
    # not do it in the event loop
    builder: MibBuilder = mib_controller.mibBuilder
    if "PYSNMP-MIB" not in builder.mibSymbols:
        builder.loadModules()
    return engine
