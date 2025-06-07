"""Coordinator entity for Snapcast server."""

from __future__ import annotations

from menuai.helpers.update_coordinator import CoordinatorEntity

from .coordinator import SnapcastUpdateCoordinator


class SnapcastCoordinatorEntity(CoordinatorEntity[SnapcastUpdateCoordinator]):
    """Coordinator entity for Snapcast."""
