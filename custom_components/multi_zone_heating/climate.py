"""Climate platform for multi_zone_heating."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
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
    """Set up climate entities for a config entry."""
    if entry.runtime_data.coordinator is None:
        return
    async_add_entities([MultiZoneHeatingSystemClimate(entry)])


class MultiZoneHeatingSystemClimate(CoordinatorEntity, ClimateEntity):
    """Top-level climate entity for system-wide override control."""

    _attr_has_entity_name = True
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_target_temperature_step = 0.5
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, entry: MultiZoneHeatingConfigEntry) -> None:
        """Initialize the climate entity."""
        super().__init__(entry.runtime_data.coordinator)
        self._entry = entry
        self._attr_name = "System"
        self._attr_unique_id = f"{entry.entry_id}_system_climate"

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
    def hvac_mode(self) -> HVACMode | None:
        """Return the effective HVAC mode."""
        if self.coordinator.data is None:
            return None
        return HVACMode.OFF if self.coordinator.data.global_force_off else HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return whether the system is heating right now."""
        data = self.coordinator.data
        if data is None:
            return None
        if data.global_force_off:
            return HVACAction.OFF
        return HVACAction.HEATING if data.system_demand else HVACAction.IDLE

    @property
    def target_temperature(self) -> float | None:
        """Return the displayed target temperature."""
        data = self.coordinator.data
        if data is None:
            return None
        if data.global_override is not None and data.global_override.active:
            return data.global_override.target_temperature
        for target_temperature in data.target_temperatures.values():
            if target_temperature is not None:
                return target_temperature
        return None

    @property
    def current_temperature(self) -> float | None:
        """Return the mean visible zone temperature when available."""
        data = self.coordinator.data
        if data is None:
            return None

        temperatures: list[float] = []
        for evaluation in data.zone_evaluations:
            if evaluation.current_temperature is not None:
                temperatures.append(evaluation.current_temperature)
            for group in evaluation.local_groups:
                if group.current_temperature is not None:
                    temperatures.append(group.current_temperature)

        if not temperatures:
            return None
        return sum(temperatures) / len(temperatures)

    @property
    def min_temp(self) -> float:
        """Return the minimum target temperature the entity should expose."""
        config_minimums = []
        if self.coordinator.config.frost_protection_min_temp is not None:
            config_minimums.append(self.coordinator.config.frost_protection_min_temp)
        config_minimums.extend(
            zone.frost_protection_min_temp
            for zone in self.coordinator.config.zones
            if zone.frost_protection_min_temp is not None
        )
        return min(config_minimums, default=5.0)

    @property
    def max_temp(self) -> float:
        """Return the maximum supported target temperature."""
        return 35.0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return system override and demand attributes."""
        data = self.coordinator.data
        if data is None:
            return {}

        override_target_temperature = None
        override_active = False
        if data.global_override is not None:
            override_active = data.global_override.active
            override_target_temperature = data.global_override.target_temperature

        return {
            "override_active": override_active,
            "override_target_temperature": override_target_temperature,
            "zones_calling_for_heat": [
                evaluation.name for evaluation in data.zone_evaluations if evaluation.demand
            ],
            "global_force_off": data.global_force_off,
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set system HVAC mode."""
        await self.coordinator.async_set_global_force_off(hvac_mode == HVACMode.OFF)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the global override target temperature."""
        target_temperature = kwargs.get("temperature")
        if target_temperature is None:
            return

        await self.coordinator.async_set_global_override(float(target_temperature))
