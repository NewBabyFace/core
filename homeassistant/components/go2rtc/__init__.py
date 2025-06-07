"""The go2rtc component."""

import logging
import shutil

from aiohttp.client_exceptions import ClientConnectionError, ServerConnectionError
from awesomeversion import AwesomeVersion
from go2rtc_client import Go2RtcRestClient
from go2rtc_client.exceptions import Go2RtcClientError, Go2RtcVersionError
from go2rtc_client.ws import (
    Go2RtcWsClient,
    ReceiveMessages,
    WebRTCAnswer,
    WebRTCCandidate,
    WebRTCOffer,
    WsError,
)
import voluptuous as vol
from webrtc_models import RTCIceCandidateInit

from menuai.components.camera import (
    Camera,
    CameraWebRTCProvider,
    WebRTCAnswer as HAWebRTCAnswer,
    WebRTCCandidate as HAWebRTCCandidate,
    WebRTCError,
    WebRTCMessage,
    WebRTCSendMessage,
    async_register_webrtc_provider,
)
from menuai.components.default_config import DOMAIN as DEFAULT_CONFIG_DOMAIN
from menuai.config_entries import SOURCE_SYSTEM, ConfigEntry
from menuai.const import CONF_URL, EVENT_menuai_STOP
from menuai.core import Event, menuai, callback
from menuai.exceptions import ConfigEntryNotReady
from menuai.helpers import (
    config_validation as cv,
    discovery_flow,
    issue_registry as ir,
)
from menuai.helpers.aiohttp_client import async_get_clientsession
from menuai.helpers.typing import ConfigType
from menuai.util.menuai_dict import menuaiKey
from menuai.util.package import is_docker_env

from .const import (
    CONF_DEBUG_UI,
    DEBUG_UI_URL_MESSAGE,
    DOMAIN,
    HA_MANAGED_URL,
    RECOMMENDED_VERSION,
)
from .server import Server

_LOGGER = logging.getLogger(__name__)

_SUPPORTED_STREAMS = frozenset(
    (
        "bubble",
        "dvrip",
        "expr",
        "ffmpeg",
        "gopro",
        "homekit",
        "http",
        "https",
        "httpx",
        "isapi",
        "ivideon",
        "kasa",
        "nest",
        "onvif",
        "roborock",
        "rtmp",
        "rtmps",
        "rtmpx",
        "rtsp",
        "rtsps",
        "rtspx",
        "tapo",
        "tcp",
        "webrtc",
        "webtorrent",
    )
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Exclusive(CONF_URL, DOMAIN, DEBUG_UI_URL_MESSAGE): cv.url,
                vol.Exclusive(CONF_DEBUG_UI, DOMAIN, DEBUG_UI_URL_MESSAGE): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

_DATA_GO2RTC: menuaiKey[str] = menuaiKey(DOMAIN)
_RETRYABLE_ERRORS = (ClientConnectionError, ServerConnectionError)


async def async_setup(menuai: menuai, config: ConfigType) -> bool:
    """Set up WebRTC."""
    url: str | None = None
    if DOMAIN not in config and DEFAULT_CONFIG_DOMAIN not in config:
        await _remove_go2rtc_entries(menuai)
        return True

    if not (configured_by_user := DOMAIN in config) or not (
        url := config[DOMAIN].get(CONF_URL)
    ):
        if not is_docker_env():
            if not configured_by_user:
                # Remove config entry if it exists
                await _remove_go2rtc_entries(menuai)
                return True
            _LOGGER.warning("Go2rtc URL required in non-docker installs")
            return False
        if not (binary := await _get_binary(menuai)):
            _LOGGER.error("Could not find go2rtc docker binary")
            return False

        # HA will manage the binary
        server = Server(
            menuai, binary, enable_ui=config.get(DOMAIN, {}).get(CONF_DEBUG_UI, False)
        )
        try:
            await server.start()
        except Exception:  # noqa: BLE001
            _LOGGER.warning("Could not start go2rtc server", exc_info=True)
            return False

        async def on_stop(event: Event) -> None:
            await server.stop()

        menuai.bus.async_listen(EVENT_menuai_STOP, on_stop)

        url = HA_MANAGED_URL

    menuai.data[_DATA_GO2RTC] = url
    discovery_flow.async_create_flow(
        menuai, DOMAIN, context={"source": SOURCE_SYSTEM}, data={}
    )
    return True


async def _remove_go2rtc_entries(menuai: menuai) -> None:
    """Remove go2rtc config entries, if any."""
    for entry in menuai.config_entries.async_entries(DOMAIN):
        await menuai.config_entries.async_remove(entry.entry_id)


async def async_setup_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Set up go2rtc from a config entry."""
    url = menuai.data[_DATA_GO2RTC]

    # Validate the server URL
    try:
        client = Go2RtcRestClient(async_get_clientsession(menuai), url)
        version = await client.validate_server_version()
        if version < AwesomeVersion(RECOMMENDED_VERSION):
            ir.async_create_issue(
                menuai,
                DOMAIN,
                "recommended_version",
                is_fixable=False,
                is_persistent=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="recommended_version",
                translation_placeholders={
                    "recommended_version": RECOMMENDED_VERSION,
                    "current_version": str(version),
                },
            )
    except Go2RtcClientError as err:
        if isinstance(err.__cause__, _RETRYABLE_ERRORS):
            raise ConfigEntryNotReady(
                f"Could not connect to go2rtc instance on {url}"
            ) from err
        _LOGGER.warning("Could not connect to go2rtc instance on %s (%s)", url, err)
        return False
    except Go2RtcVersionError as err:
        raise ConfigEntryNotReady(
            f"The go2rtc server version is not supported, {err}"
        ) from err
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Could not connect to go2rtc instance on %s (%s)", url, err)
        return False

    provider = WebRTCProvider(menuai, url)
    async_register_webrtc_provider(menuai, provider)
    return True


async def async_unload_entry(menuai: menuai, entry: ConfigEntry) -> bool:
    """Unload a go2rtc config entry."""
    return True


async def _get_binary(menuai: menuai) -> str | None:
    """Return the binary path if found."""
    return await menuai.async_add_executor_job(shutil.which, "go2rtc")


class WebRTCProvider(CameraWebRTCProvider):
    """WebRTC provider."""

    def __init__(self, menuai: menuai, url: str) -> None:
        """Initialize the WebRTC provider."""
        self._menuai = menuai
        self._url = url
        self._session = async_get_clientsession(menuai)
        self._rest_client = Go2RtcRestClient(self._session, url)
        self._sessions: dict[str, Go2RtcWsClient] = {}

    @property
    def domain(self) -> str:
        """Return the integration domain of the provider."""
        return DOMAIN

    @callback
    def async_is_supported(self, stream_source: str) -> bool:
        """Return if this provider is supports the Camera as source."""
        return stream_source.partition(":")[0] in _SUPPORTED_STREAMS

    async def async_handle_async_webrtc_offer(
        self,
        camera: Camera,
        offer_sdp: str,
        session_id: str,
        send_message: WebRTCSendMessage,
    ) -> None:
        """Handle the WebRTC offer and return the answer via the provided callback."""
        self._sessions[session_id] = ws_client = Go2RtcWsClient(
            self._session, self._url, source=camera.entity_id
        )

        if not (stream_source := await camera.stream_source()):
            send_message(
                WebRTCError("go2rtc_webrtc_offer_failed", "Camera has no stream source")
            )
            return

        streams = await self._rest_client.streams.list()

        if (stream := streams.get(camera.entity_id)) is None or not any(
            stream_source == producer.url for producer in stream.producers
        ):
            await self._rest_client.streams.add(
                camera.entity_id,
                [
                    stream_source,
                    # We are setting any ffmpeg rtsp related logs to debug
                    # Connection problems to the camera will be logged by the first stream
                    # Therefore setting it to debug will not hide any important logs
                    f"ffmpeg:{camera.entity_id}#audio=opus#query=log_level=debug",
                ],
            )

        @callback
        def on_messages(message: ReceiveMessages) -> None:
            """Handle messages."""
            value: WebRTCMessage
            match message:
                case WebRTCCandidate():
                    value = HAWebRTCCandidate(RTCIceCandidateInit(message.candidate))
                case WebRTCAnswer():
                    value = HAWebRTCAnswer(message.sdp)
                case WsError():
                    value = WebRTCError("go2rtc_webrtc_offer_failed", message.error)

            send_message(value)

        ws_client.subscribe(on_messages)
        config = camera.async_get_webrtc_client_configuration()
        await ws_client.send(WebRTCOffer(offer_sdp, config.configuration.ice_servers))

    async def async_on_webrtc_candidate(
        self, session_id: str, candidate: RTCIceCandidateInit
    ) -> None:
        """Handle the WebRTC candidate."""

        if ws_client := self._sessions.get(session_id):
            await ws_client.send(WebRTCCandidate(candidate.candidate))
        else:
            _LOGGER.debug("Unknown session %s. Ignoring candidate", session_id)

    @callback
    def async_close_session(self, session_id: str) -> None:
        """Close the session."""
        ws_client = self._sessions.pop(session_id)
        self._menuai.async_create_task(ws_client.close())
