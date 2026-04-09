"""Switch platform for multi_zone_heating."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
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
    """Set up switches for a config entry."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    if coordinator is None:
        return

    entities: list[SwitchEntity] = [
        MultiZoneHeatingGlobalForceOffSwitch(entry),
        *[
            MultiZoneHeatingZoneEnabledSwitch(entry, zone.name)
            for zone in runtime_data.config.zones
        ],
    ]
    async_add_entities(entities)


class MultiZoneHeatingSwitchBase(CoordinatorEntity, SwitchEntity):
    """Base switch entity backed by the runtime coordinator."""

    _attr_has_entity_name = True

    def __init__(self, entry: MultiZoneHeatingConfigEntry) -> None:
        """Initialize the entity."""
        super().__init__(entry.runtime_data.coordinator)
        self._entry = entry

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


class MultiZoneHeatingGlobalForceOffSwitch(MultiZoneHeatingSwitchBase):
    """Switch controlling the global force-off mode."""

    def __init__(self, entry: MultiZoneHeatingConfigEntry) -> None:
        """Initialize the entity."""
        super().__init__(entry)
        self._attr_name = "Global Force Off"
        self._attr_unique_id = f"{entry.entry_id}_global_force_off"
        self._attr_icon = "mdi:power"

    @property
    def is_on(self) -> bool | None:
        """Return whether global force-off is active."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.global_force_off

    async def async_turn_on(self, **kwargs) -> None:
        """Enable global force-off."""
        await self.coordinator.async_set_global_force_off(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable global force-off."""
        await self.coordinator.async_set_global_force_off(False)


class MultiZoneHeatingZoneEnabledSwitch(MultiZoneHeatingSwitchBase):
    """Switch controlling whether one zone may call for heat."""

    def __init__(self, entry: MultiZoneHeatingConfigEntry, zone_name: str) -> None:
        """Initialize the entity."""
        super().__init__(entry)
        self._zone_name = zone_name
        self._attr_name = f"{zone_name} Enabled"
        self._attr_unique_id = f"{entry.entry_id}_{zone_name}_enabled"

    @property
    def is_on(self) -> bool | None:
        """Return whether the configured zone is enabled."""
        zone = self.coordinator.get_zone_config(self._zone_name)
        if zone is None:
            return None
        return zone.enabled

    async def async_turn_on(self, **kwargs) -> None:
        """Enable the zone."""
        await self.coordinator.async_set_zone_enabled(self._zone_name, True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable the zone."""
        await self.coordinator.async_set_zone_enabled(self._zone_name, False)
