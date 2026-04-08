"""Shared models for the multi_zone_heating integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class AggregationMode(StrEnum):
    """Supported temperature aggregation modes."""

    AVERAGE = "average"
    MINIMUM = "minimum"
    PRIMARY = "primary"


class ControlType(StrEnum):
    """Supported zone control types."""

    CLIMATE = "climate"
    NUMBER = "number"
    SWITCH = "switch"


class TargetSourceType(StrEnum):
    """Supported target temperature source types."""

    CLIMATE = "climate"
    INPUT_NUMBER = "input_number"


@dataclass(slots=True)
class LocalControlGroup:
    """Placeholder model for a switch or number driven local spot."""

    name: str
    control_type: ControlType
    actuator_entity_ids: list[str] = field(default_factory=list)
    sensor_entity_ids: list[str] = field(default_factory=list)
    aggregation_mode: AggregationMode = AggregationMode.AVERAGE
    primary_sensor_entity_id: str | None = None


@dataclass(slots=True)
class ZoneConfig:
    """Placeholder zone configuration model."""

    name: str
    control_type: ControlType
    target_source: TargetSourceType
    target_entity_id: str
    sensor_entity_ids: list[str] = field(default_factory=list)
    climate_entity_ids: list[str] = field(default_factory=list)
    local_groups: list[LocalControlGroup] = field(default_factory=list)
    aggregation_mode: AggregationMode = AggregationMode.AVERAGE
    primary_sensor_entity_id: str | None = None
    enabled: bool = True
    frost_protection_min_temp: float | None = None


@dataclass(slots=True)
class IntegrationConfig:
    """Placeholder top-level integration configuration model."""

    main_relay_entity_id: str | None = None
    flow_sensor_entity_id: str | None = None
    zones: list[ZoneConfig] = field(default_factory=list)
    default_hysteresis: float = 0.0


@dataclass(slots=True)
class RuntimeData:
    """Runtime container attached to the config entry."""

    config_entry_id: str
    config: IntegrationConfig = field(default_factory=IntegrationConfig)
