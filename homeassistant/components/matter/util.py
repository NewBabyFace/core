"""Provide integration utilities."""

from __future__ import annotations

XY_COLOR_FACTOR = 65536


def renormalize(
    number: float, from_range: tuple[float, float], to_range: tuple[float, float]
) -> float:
    """Change value from from_range to to_range."""
    delta1 = from_range[1] - from_range[0]
    delta2 = to_range[1] - to_range[0]
    return (delta2 * (number - from_range[0]) / delta1) + to_range[0]


def convert_to_matter_hs(menuai_hs: tuple[float, float]) -> tuple[float, float]:
    """Convert MenuAI HS to Matter HS."""

    return (
        menuai_hs[0] / 360 * 254,
        renormalize(menuai_hs[1], (0, 100), (0, 254)),
    )


def convert_to_menuai_hs(matter_hs: tuple[float, float]) -> tuple[float, float]:
    """Convert Matter HS to MenuAI HS."""

    return (
        matter_hs[0] * 360 / 254,
        renormalize(matter_hs[1], (0, 254), (0, 100)),
    )


def convert_to_matter_xy(menuai_xy: tuple[float, float]) -> tuple[float, float]:
    """Convert MenuAI XY to Matter XY."""

    return (menuai_xy[0] * XY_COLOR_FACTOR, menuai_xy[1] * XY_COLOR_FACTOR)


def convert_to_menuai_xy(matter_xy: tuple[float, float]) -> tuple[float, float]:
    """Convert Matter XY to MenuAI XY."""

    return (matter_xy[0] / XY_COLOR_FACTOR, matter_xy[1] / XY_COLOR_FACTOR)
