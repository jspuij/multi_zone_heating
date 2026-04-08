"""Coordinator placeholders for multi_zone_heating."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RuntimeSnapshot:
    """Placeholder runtime snapshot for future coordinator work."""

    system_demand: bool = False
