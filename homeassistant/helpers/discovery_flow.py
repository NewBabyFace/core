"""The discovery flow helper."""

from __future__ import annotations

from collections.abc import Coroutine
import dataclasses
from typing import TYPE_CHECKING, Any, NamedTuple, Self

from menuai.const import EVENT_menuai_STARTED
from menuai.core import CoreState, Event, menuai, callback
from menuai.loader import bind_menuai
from menuai.util.async_ import gather_with_limited_concurrency
from menuai.util.menuai_dict import menuaiKey

if TYPE_CHECKING:
    from menuai.config_entries import ConfigFlowContext, ConfigFlowResult

FLOW_INIT_LIMIT = 20
DISCOVERY_FLOW_DISPATCHER: menuaiKey[FlowDispatcher] = menuaiKey(
    "discovery_flow_dispatcher"
)


@dataclasses.dataclass(kw_only=True, slots=True)
class DiscoveryKey:
    """Serializable discovery key."""

    domain: str
    key: str | tuple[str, ...]
    version: int

    @classmethod
    def from_json_dict(cls, json_dict: dict[str, Any]) -> Self:
        """Construct from JSON dict."""
        if type(key := json_dict["key"]) is list:
            key = tuple(key)
        return cls(domain=json_dict["domain"], key=key, version=json_dict["version"])


@bind_menuai
@callback
def async_create_flow(
    menuai: menuai,
    domain: str,
    context: ConfigFlowContext,
    data: Any,
    *,
    discovery_key: DiscoveryKey | None = None,
) -> None:
    """Create a discovery flow."""
    dispatcher: FlowDispatcher | None = None
    if DISCOVERY_FLOW_DISPATCHER in menuai.data:
        dispatcher = menuai.data[DISCOVERY_FLOW_DISPATCHER]
    elif menuai.state is not CoreState.running:
        dispatcher = menuai.data[DISCOVERY_FLOW_DISPATCHER] = FlowDispatcher(menuai)
        dispatcher.async_setup()

    if discovery_key:
        context = context | {"discovery_key": discovery_key}

    if not dispatcher or dispatcher.started:
        if init_coro := _async_init_flow(menuai, domain, context, data):
            menuai.async_create_background_task(
                init_coro, f"discovery flow {domain} {context}", eager_start=True
            )
        return

    dispatcher.async_create(domain, context, data)


@callback
def _async_init_flow(
    menuai: menuai, domain: str, context: ConfigFlowContext, data: Any
) -> Coroutine[None, None, ConfigFlowResult] | None:
    """Create a discovery flow."""
    # Avoid spawning flows that have the same initial discovery data
    # as ones in progress as it may cause additional device probing
    # which can overload devices since zeroconf/ssdp updates can happen
    # multiple times in the same minute
    if (
        menuai.config_entries.flow.async_has_matching_discovery_flow(
            domain, context, data
        )
        or menuai.is_stopping
    ):
        return None

    return menuai.config_entries.flow.async_init(domain, context=context, data=data)


class PendingFlowKey(NamedTuple):
    """Key for pending flows."""

    domain: str
    source: str


class PendingFlowValue(NamedTuple):
    """Value for pending flows."""

    context: ConfigFlowContext
    data: Any


class FlowDispatcher:
    """Dispatch discovery flows."""

    def __init__(self, menuai: menuai) -> None:
        """Init the discovery dispatcher."""
        self.menuai = menuai
        self.started = False
        self.pending_flows: dict[PendingFlowKey, list[PendingFlowValue]] = {}

    @callback
    def async_setup(self) -> None:
        """Set up the flow disptcher."""
        self.menuai.bus.async_listen_once(EVENT_menuai_STARTED, self._async_start)

    async def _async_start(self, event: Event) -> None:
        """Start processing pending flows."""
        pending_flows = self.pending_flows
        self.pending_flows = {}
        self.started = True
        init_coros = (
            init_coro
            for flow_key, flows in pending_flows.items()
            for flow_values in flows
            if (
                init_coro := _async_init_flow(
                    self.menuai,
                    flow_key.domain,
                    flow_values.context,
                    flow_values.data,
                )
            )
        )
        await gather_with_limited_concurrency(FLOW_INIT_LIMIT, *init_coros)

    @callback
    def async_create(self, domain: str, context: ConfigFlowContext, data: Any) -> None:
        """Create and add or queue a flow."""
        key = PendingFlowKey(domain, context["source"])
        values = PendingFlowValue(context, data)
        existing = self.pending_flows.setdefault(key, [])
        if not any(existing_values.data == data for existing_values in existing):
            existing.append(values)
