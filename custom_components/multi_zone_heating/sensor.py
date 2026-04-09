"""Sensor platform for multi_zone_heating."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import MultiZoneHeatingConfigEntry
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MultiZoneHeatingConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for a config entry."""
    if entry.runtime_data.coordinator is None:
        return
    async_add_entities([MultiZoneHeatingRelayStateSensor(entry)])


class MultiZoneHeatingRelayStateSensor(CoordinatorEntity, SensorEntity):
    """Diagnostic sensor describing relay control state."""

    _attr_has_entity_name = True

    def __init__(self, entry: MultiZoneHeatingConfigEntry) -> None:
        """Initialize the entity."""
        super().__init__(entry.runtime_data.coordinator)
        self._entry = entry
        self._attr_name = "Relay State"
        self._attr_unique_id = f"{entry.entry_id}_relay_state"
        self._attr_icon = "mdi:valve"

    @property
    def available(self) -> bool:
        """Return whether coordinator data is available."""
        return self.coordinator.data is not None

    @property
    def device_info(self) -> dict[str, object]:
        """Describe the integration device that owns these entities."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
        }

    @property
    def native_value(self) -> str | None:
        """Return the relay diagnostic state."""
        data = self.coordinator.data
        if data is None or data.relay_runtime_state is None:
            return None

        if data.global_force_off:
            return "forced_off"

        if data.relay_decision is not None and data.relay_decision.hold_reason == "off_delay":
            return "pending_off"

        return "on" if data.relay_runtime_state.is_on else "off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return relay diagnostics."""
        data = self.coordinator.data
        if data is None:
            return {}

        zones_calling_for_heat = [
            evaluation.name for evaluation in data.zone_evaluations if evaluation.demand
        ]
        return {
            "desired_on": data.relay_decision.desired_on if data.relay_decision else None,
            "hold_reason": data.relay_decision.hold_reason if data.relay_decision else None,
            "missing_flow_warning": data.missing_flow_warning,
            "missing_flow_warning_since": data.missing_flow_warning_since.isoformat()
            if data.missing_flow_warning_since is not None
            else None,
            "flow_detected": data.flow_detected,
            "flow_value": data.flow_value,
            "zones_calling_for_heat": zones_calling_for_heat,
        }
