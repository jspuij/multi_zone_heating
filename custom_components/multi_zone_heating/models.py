"""Shared models for the multi_zone_heating integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .coordinator import MultiZoneHeatingCoordinator


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


class NumberSemanticType(StrEnum):
    """Supported meanings for number-based actuators."""

    PERCENTAGE = "percentage"
    TEMPERATURE = "temperature"


@dataclass(slots=True)
class LocalControlGroup:
    """Placeholder model for a switch or number driven local spot."""

    name: str
    control_type: ControlType
    actuator_entity_ids: list[str] = field(default_factory=list)
    sensor_entity_ids: list[str] = field(default_factory=list)
    aggregation_mode: AggregationMode = AggregationMode.AVERAGE
    primary_sensor_entity_id: str | None = None
    number_semantic_type: NumberSemanticType | None = None
    active_value: float | None = None
    inactive_value: float | None = None


@dataclass(slots=True)
class ZoneConfig:
    """Placeholder zone configuration model."""

    name: str
    control_type: ControlType
    target_source: TargetSourceType
    target_entity_id: str
    sensor_entity_ids: list[str] = field(default_factory=list)
    climate_entity_ids: list[str] = field(default_factory=list)
    climate_off_fallback_temperature: float | None = None
    local_groups: list[LocalControlGroup] = field(default_factory=list)
    aggregation_mode: AggregationMode = AggregationMode.AVERAGE
    primary_sensor_entity_id: str | None = None
    enabled: bool = True
    frost_protection_min_temp: float | None = None


@dataclass(slots=True)
class IntegrationConfig:
    """Top-level integration configuration."""

    main_relay_entity_id: str | None = None
    flow_sensor_entity_id: str | None = None
    flow_detection_threshold: float | None = None
    missing_flow_timeout_seconds: int | None = None
    zones: list[ZoneConfig] = field(default_factory=list)
    default_hysteresis: float = 0.3
    min_relay_on_time_seconds: int | None = None
    min_relay_off_time_seconds: int | None = None
    relay_off_delay_seconds: int | None = None
    frost_protection_min_temp: float | None = None
    failsafe_mode: str | None = None


@dataclass(slots=True)
class RuntimeData:
    """Runtime container attached to the config entry."""

    config_entry_id: str
    config: IntegrationConfig = field(default_factory=IntegrationConfig)
    coordinator: MultiZoneHeatingCoordinator | None = None


@dataclass(slots=True)
class GlobalOverride:
    """Represents the optional system-wide target override."""

    target_temperature: float
    active: bool = True


@dataclass(slots=True)
class LocalControlGroupEvaluation:
    """Pure evaluation result for a local control group."""

    name: str
    control_type: ControlType
    current_temperature: float | None
    target_temperature: float | None
    effective_target_temperature: float | None
    demand: bool
    available_sensor_entity_ids: list[str] = field(default_factory=list)
    available_actuator_entity_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ZoneEvaluation:
    """Pure evaluation result for a zone.

    For zones composed of local control groups, `current_temperature` remains
    `None` because temperature is evaluated at the group level.
    """

    name: str
    control_type: ControlType
    current_temperature: float | None
    target_temperature: float | None
    effective_target_temperature: float | None
    demand: bool
    available_sensor_entity_ids: list[str] = field(default_factory=list)
    available_actuator_entity_ids: list[str] = field(default_factory=list)
    local_groups: list[LocalControlGroupEvaluation] = field(default_factory=list)


@dataclass(slots=True)
class RelayRuntimeState:
    """Minimal runtime state needed to make relay timing decisions."""

    is_on: bool
    last_on_at: datetime | None = None
    last_off_at: datetime | None = None
    off_requested_at: datetime | None = None


@dataclass(slots=True)
class RelayDecision:
    """Deterministic relay decision produced by the pure control logic."""

    desired_on: bool
    resulting_state: bool
    should_turn_on: bool = False
    should_turn_off: bool = False
    off_requested_at: datetime | None = None
    next_recheck_at: datetime | None = None
    hold_reason: str | None = None


@dataclass(slots=True)
class FlowWarningDecision:
    """Decision describing whether a missing-flow warning should be active."""

    warning_active: bool
    warning_since: datetime | None = None
    next_recheck_at: datetime | None = None


@dataclass(slots=True)
class RuntimeSnapshot:
    """Current runtime state assembled from Home Assistant and control logic."""

    sensor_values: dict[str, float | None] = field(default_factory=dict)
    target_temperatures: dict[str, float | None] = field(default_factory=dict)
    flow_value: float | None = None
    flow_detected: bool = False
    missing_flow_warning: bool = False
    missing_flow_warning_since: datetime | None = None
    actuator_available_entity_ids: list[str] = field(default_factory=list)
    unavailable_entity_ids: list[str] = field(default_factory=list)
    zone_evaluations: list[ZoneEvaluation] = field(default_factory=list)
    system_demand: bool = False
    relay_runtime_state: RelayRuntimeState | None = None
    relay_decision: RelayDecision | None = None
