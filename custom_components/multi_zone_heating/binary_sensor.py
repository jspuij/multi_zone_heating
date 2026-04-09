"""Binary sensor platform for multi_zone_heating."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    """Set up binary sensors for a config entry."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    if coordinator is None:
        return

    entities: list[BinarySensorEntity] = [
        MultiZoneHeatingSystemDemandBinarySensor(entry),
        *[
            MultiZoneHeatingZoneDemandBinarySensor(entry, zone.name)
            for zone in runtime_data.config.zones
        ],
    ]
    async_add_entities(entities)


class MultiZoneHeatingBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base binary sensor for coordinator-backed integration entities."""

    _attr_has_entity_name = True

    def __init__(self, entry: MultiZoneHeatingConfigEntry) -> None:
        """Initialize the entity."""
        super().__init__(entry.runtime_data.coordinator)
        self._entry = entry
        self._attr_unique_id = None

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


class MultiZoneHeatingSystemDemandBinarySensor(MultiZoneHeatingBinarySensorBase):
    """Binary sensor exposing aggregate demand."""

    def __init__(self, entry: MultiZoneHeatingConfigEntry) -> None:
        """Initialize the entity."""
        super().__init__(entry)
        self._attr_name = "System Demand"
        self._attr_unique_id = f"{entry.entry_id}_system_demand"

    @property
    def is_on(self) -> bool | None:
        """Return whether any zone currently demands heat."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.system_demand


class MultiZoneHeatingZoneDemandBinarySensor(MultiZoneHeatingBinarySensorBase):
    """Binary sensor exposing demand for one configured zone."""

    def __init__(self, entry: MultiZoneHeatingConfigEntry, zone_name: str) -> None:
        """Initialize the entity."""
        super().__init__(entry)
        self._zone_name = zone_name
        self._attr_name = f"{zone_name} Demand"
        self._attr_unique_id = f"{entry.entry_id}_{zone_name}_demand"

    @property
    def is_on(self) -> bool | None:
        """Return whether the zone currently demands heat."""
        if self.coordinator.data is None:
            return None

        for evaluation in self.coordinator.data.zone_evaluations:
            if evaluation.name == self._zone_name:
                return evaluation.demand
        return None
