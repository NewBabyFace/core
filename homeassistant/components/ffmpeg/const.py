"""Support for FFmpeg."""

from menuai.util.signal_type import SignalType

DOMAIN = "ffmpeg"

SIGNAL_FFMPEG_START = SignalType[list[str] | None]("ffmpeg.start")
SIGNAL_FFMPEG_STOP = SignalType[list[str] | None]("ffmpeg.stop")
SIGNAL_FFMPEG_RESTART = SignalType[list[str] | None]("ffmpeg.restart")
