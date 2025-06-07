"""The dhcp integration."""

from __future__ import annotations

from collections.abc import Callable
import dataclasses
from dataclasses import dataclass
from typing import TypedDict

from menuai.loader import DHCPMatcher
from menuai.util.menuai_dict import menuaiKey

from .const import DOMAIN


@dataclass(slots=True)
class DhcpMatchers:
    """Prepared info from dhcp entries."""

    registered_devices_domains: set[str]
    no_oui_matchers: dict[str, list[DHCPMatcher]]
    oui_matchers: dict[str, list[DHCPMatcher]]


class DHCPAddressData(TypedDict):
    """Typed dict for DHCP address data."""

    hostname: str
    ip: str


@dataclasses.dataclass(slots=True)
class DHCPData:
    """Data for the dhcp component."""

    integration_matchers: DhcpMatchers
    callbacks: set[Callable[[dict[str, DHCPAddressData]], None]] = dataclasses.field(
        default_factory=set
    )
    address_data: dict[str, DHCPAddressData] = dataclasses.field(default_factory=dict)


DATA_DHCP: menuaiKey[DHCPData] = menuaiKey(DOMAIN)
