"""Config and options flow for the multi_zone_heating integration."""

from __future__ import annotations

from copy import deepcopy

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlowWithConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DEFAULT_TITLE, DOMAIN
from .models import AggregationMode, ControlType, NumberSemanticType, TargetSourceType

CONF_ACTION = "action"
CONF_ACTIVE_VALUE = "active_value"
CONF_ACTUATOR_ENTITY_IDS = "actuator_entity_ids"
CONF_AGGREGATION_MODE = "aggregation_mode"
CONF_CLIMATE_ENTITY_IDS = "climate_entity_ids"
CONF_CLIMATE_OFF_FALLBACK_TEMPERATURE = "climate_off_fallback_temperature"
CONF_CONTROL_TYPE = "control_type"
CONF_DEFAULT_HYSTERESIS = "default_hysteresis"
CONF_ENABLED = "enabled"
CONF_FLOW_DETECTION_THRESHOLD = "flow_detection_threshold"
CONF_FLOW_SENSOR_ENTITY_ID = "flow_sensor_entity_id"
CONF_FROST_PROTECTION_MIN_TEMP = "frost_protection_min_temp"
CONF_GROUP = "group"
CONF_INACTIVE_VALUE = "inactive_value"
CONF_LOCAL_GROUPS = "local_groups"
CONF_MAIN_RELAY_ENTITY_ID = "main_relay_entity_id"
CONF_MISSING_FLOW_TIMEOUT_SECONDS = "missing_flow_timeout_seconds"
CONF_MIN_RELAY_OFF_TIME_SECONDS = "min_relay_off_time_seconds"
CONF_MIN_RELAY_ON_TIME_SECONDS = "min_relay_on_time_seconds"
CONF_NUMBER_SEMANTIC_TYPE = "number_semantic_type"
CONF_PRIMARY_SENSOR_ENTITY_ID = "primary_sensor_entity_id"
CONF_RELAY_OFF_DELAY_SECONDS = "relay_off_delay_seconds"
CONF_SENSOR_ENTITY_IDS = "sensor_entity_ids"
CONF_TARGET_ENTITY_ID = "target_entity_id"
CONF_TARGET_SOURCE = "target_source"
CONF_ZONE = "zone"
CONF_ZONES = "zones"

ACTION_ADD_GROUP = "add_group"
ACTION_ADD_ZONE = "add_zone"
ACTION_DONE = "done"
ACTION_EDIT_GLOBALS = "edit_globals"
ACTION_EDIT_GROUP = "edit_group"
ACTION_EDIT_ZONE = "edit_zone"
ACTION_REMOVE_GROUP = "remove_group"
ACTION_REMOVE_ZONE = "remove_zone"

DEFAULT_HYSTERESIS = 0.3
DEFAULT_MISSING_FLOW_TIMEOUT_SECONDS = 60
DEFAULT_MIN_RELAY_ON_TIME_SECONDS = 0
DEFAULT_MIN_RELAY_OFF_TIME_SECONDS = 0
DEFAULT_RELAY_OFF_DELAY_SECONDS = 0


class _MultiZoneHeatingFlowBase:
    """Shared helpers for config and options flows."""

    def __init__(self) -> None:
        """Initialize shared flow state."""
        self._config: dict[str, object] = {}
        self._title = DEFAULT_TITLE
        self._pending_zone: dict[str, object] | None = None
        self._pending_local_groups: list[dict[str, object]] = []
        self._editing_zone_index: int | None = None
        self._editing_local_group_index: int | None = None

    def _global_schema(
        self, user_input: dict[str, object] | None = None
    ) -> vol.Schema:
        """Build the global configuration form schema."""
        schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_TITLE): str,
                vol.Required(CONF_MAIN_RELAY_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["switch", "input_boolean"])
                ),
                vol.Optional(CONF_FLOW_SENSOR_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor", "number", "input_number"])
                ),
                vol.Optional(CONF_FLOW_DETECTION_THRESHOLD): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, step="any", mode="box")
                ),
                vol.Required(
                    CONF_MISSING_FLOW_TIMEOUT_SECONDS,
                    default=DEFAULT_MISSING_FLOW_TIMEOUT_SECONDS,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, step=1, mode="box")
                ),
                vol.Required(
                    CONF_DEFAULT_HYSTERESIS, default=DEFAULT_HYSTERESIS
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, step=0.05, mode="box")
                ),
                vol.Required(
                    CONF_MIN_RELAY_ON_TIME_SECONDS,
                    default=DEFAULT_MIN_RELAY_ON_TIME_SECONDS,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, step=1, mode="box")
                ),
                vol.Required(
                    CONF_MIN_RELAY_OFF_TIME_SECONDS,
                    default=DEFAULT_MIN_RELAY_OFF_TIME_SECONDS,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, step=1, mode="box")
                ),
                vol.Required(
                    CONF_RELAY_OFF_DELAY_SECONDS,
                    default=DEFAULT_RELAY_OFF_DELAY_SECONDS,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, step=1, mode="box")
                ),
                vol.Optional(CONF_FROST_PROTECTION_MIN_TEMP): selector.NumberSelector(
                    selector.NumberSelectorConfig(step=0.5, mode="box")
                ),
            }
        )
        if user_input is None:
            return schema
        return self.add_suggested_values_to_schema(schema, user_input)

    def _zone_basics_schema(
        self, user_input: dict[str, object] | None = None
    ) -> vol.Schema:
        """Build the base zone configuration form schema."""
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_ENABLED, default=True): selector.BooleanSelector(),
                vol.Required(CONF_CONTROL_TYPE, default=ControlType.CLIMATE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": item.value, "label": item.value.title()}
                            for item in ControlType
                        ],
                        mode="dropdown",
                    )
                ),
                vol.Required(
                    CONF_TARGET_SOURCE, default=TargetSourceType.CLIMATE
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": item.value, "label": item.value.replace("_", " ").title()}
                            for item in TargetSourceType
                        ],
                        mode="dropdown",
                    )
                ),
                vol.Required(CONF_TARGET_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["climate", "input_number", "number"]
                    )
                ),
                vol.Optional(CONF_FROST_PROTECTION_MIN_TEMP): selector.NumberSelector(
                    selector.NumberSelectorConfig(step=0.5, mode="box")
                ),
            }
        )
        if user_input is None:
            return schema
        return self.add_suggested_values_to_schema(schema, user_input)

    def _climate_zone_schema(
        self, user_input: dict[str, object] | None = None
    ) -> vol.Schema:
        """Build the climate-zone detail schema."""
        schema = vol.Schema(
            {
                vol.Required(CONF_SENSOR_ENTITY_IDS): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"], multiple=True)
                ),
                vol.Required(CONF_CLIMATE_ENTITY_IDS): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["climate"], multiple=True)
                ),
                vol.Optional(CONF_CLIMATE_OFF_FALLBACK_TEMPERATURE): selector.NumberSelector(
                    selector.NumberSelectorConfig(step=0.5, mode="box")
                ),
                vol.Required(
                    CONF_AGGREGATION_MODE, default=AggregationMode.AVERAGE
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": item.value, "label": item.value.title()}
                            for item in AggregationMode
                        ],
                        mode="dropdown",
                    )
                ),
                vol.Optional(CONF_PRIMARY_SENSOR_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
            }
        )
        if user_input is None:
            return schema
        return self.add_suggested_values_to_schema(schema, user_input)

    def _local_group_schema(
        self,
        zone_control_type: ControlType,
        user_input: dict[str, object] | None = None,
    ) -> vol.Schema:
        """Build the local-group schema for switch or number zones."""
        actuator_domains = ["switch"]
        if zone_control_type == ControlType.NUMBER:
            actuator_domains = ["number", "input_number"]

        schema_fields: dict[vol.Marker, object] = {
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_SENSOR_ENTITY_IDS): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor"], multiple=True)
            ),
            vol.Required(CONF_ACTUATOR_ENTITY_IDS): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=actuator_domains, multiple=True)
            ),
            vol.Required(
                CONF_AGGREGATION_MODE, default=AggregationMode.AVERAGE
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": item.value, "label": item.value.title()}
                        for item in AggregationMode
                    ],
                    mode="dropdown",
                )
            ),
            vol.Optional(CONF_PRIMARY_SENSOR_ENTITY_ID): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor"])
            ),
        }

        if zone_control_type == ControlType.NUMBER:
            schema_fields[vol.Required(CONF_NUMBER_SEMANTIC_TYPE)] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": item.value, "label": item.value.title()}
                        for item in NumberSemanticType
                    ],
                    mode="dropdown",
                )
            )
            schema_fields[vol.Optional(CONF_ACTIVE_VALUE)] = selector.NumberSelector(
                selector.NumberSelectorConfig(step="any", mode="box")
            )
            schema_fields[vol.Optional(CONF_INACTIVE_VALUE)] = selector.NumberSelector(
                selector.NumberSelectorConfig(step="any", mode="box")
            )

        schema = vol.Schema(schema_fields)
        if user_input is None:
            return schema
        return self.add_suggested_values_to_schema(schema, user_input)

    def _local_group_options_schema(self) -> vol.Schema:
        """Build the follow-up schema for local groups."""
        return vol.Schema(
            {
                vol.Required("add_another_group", default=False): selector.BooleanSelector(),
            }
        )

    def _zone_options_schema(self) -> vol.Schema:
        """Build the follow-up schema for zones."""
        return vol.Schema(
            {
                vol.Required("add_another_zone", default=False): selector.BooleanSelector(),
            }
        )

    def _action_schema(self, options: list[dict[str, str]]) -> vol.Schema:
        """Build a select-based action schema."""
        return vol.Schema(
            {
                vol.Required(CONF_ACTION): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options, mode="dropdown")
                )
            }
        )

    def _zone_select_schema(self, zones: list[dict[str, object]]) -> vol.Schema:
        """Build a zone-selection schema."""
        return vol.Schema(
            {
                vol.Required(CONF_ZONE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {
                                "value": str(index),
                                "label": self._zone_label(zone),
                            }
                            for index, zone in enumerate(zones)
                        ],
                        mode="dropdown",
                    )
                )
            }
        )

    def _group_select_schema(self, groups: list[dict[str, object]]) -> vol.Schema:
        """Build a local-group selection schema."""
        return vol.Schema(
            {
                vol.Required(CONF_GROUP): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {
                                "value": str(index),
                                "label": self._group_label(group),
                            }
                            for index, group in enumerate(groups)
                        ],
                        mode="dropdown",
                    )
                )
            }
        )

    def _validate_global_config(self, user_input: dict[str, object]) -> dict[str, str]:
        """Validate global configuration values."""
        if (
            user_input.get(CONF_FLOW_SENSOR_ENTITY_ID)
            and user_input.get(CONF_FLOW_DETECTION_THRESHOLD) is None
        ):
            return {"base": "flow_threshold_required"}
        return {}

    def _validate_zone_basics(self, user_input: dict[str, object]) -> dict[str, str]:
        """Validate shared zone configuration."""
        name = str(user_input[CONF_NAME]).strip()
        if not name:
            return {"base": "zone_name_required"}

        target_source = user_input[CONF_TARGET_SOURCE]
        target_entity_id = str(user_input[CONF_TARGET_ENTITY_ID])

        if target_source == TargetSourceType.CLIMATE and not target_entity_id.startswith(
            "climate."
        ):
            return {"base": "target_entity_domain_mismatch"}

        if target_source == TargetSourceType.INPUT_NUMBER and not (
            target_entity_id.startswith("input_number.")
            or target_entity_id.startswith("number.")
        ):
            return {"base": "target_entity_domain_mismatch"}

        return {}

    def _validate_climate_zone_details(
        self, user_input: dict[str, object]
    ) -> dict[str, str]:
        """Validate climate-zone-specific values."""
        sensor_entity_ids = user_input[CONF_SENSOR_ENTITY_IDS]
        climate_entity_ids = user_input[CONF_CLIMATE_ENTITY_IDS]

        if not sensor_entity_ids:
            return {"base": "zone_requires_sensors"}
        if not climate_entity_ids:
            return {"base": "zone_requires_climate_entities"}
        if user_input[CONF_AGGREGATION_MODE] == AggregationMode.PRIMARY:
            primary_sensor = user_input.get(CONF_PRIMARY_SENSOR_ENTITY_ID)
            if not primary_sensor:
                return {"base": "primary_sensor_required"}
            if primary_sensor not in sensor_entity_ids:
                return {"base": "primary_sensor_not_in_sensors"}
        return {}

    def _validate_local_group(
        self,
        user_input: dict[str, object],
        zone_control_type: ControlType,
    ) -> dict[str, str]:
        """Validate local-group-specific values."""
        if not str(user_input[CONF_NAME]).strip():
            return {"base": "group_name_required"}
        if not user_input[CONF_SENSOR_ENTITY_IDS]:
            return {"base": "group_requires_sensors"}
        if not user_input[CONF_ACTUATOR_ENTITY_IDS]:
            return {"base": "group_requires_actuators"}
        if user_input[CONF_AGGREGATION_MODE] == AggregationMode.PRIMARY:
            primary_sensor = user_input.get(CONF_PRIMARY_SENSOR_ENTITY_ID)
            if not primary_sensor:
                return {"base": "primary_sensor_required"}
            if primary_sensor not in user_input[CONF_SENSOR_ENTITY_IDS]:
                return {"base": "primary_sensor_not_in_sensors"}
        if zone_control_type == ControlType.NUMBER and (
            user_input.get(CONF_ACTIVE_VALUE) is None
            or user_input.get(CONF_INACTIVE_VALUE) is None
        ):
            return {"base": "number_values_required"}
        return {}

    def _save_global_config(self, user_input: dict[str, object]) -> None:
        """Store global configuration values in the working config."""
        self._title = str(user_input.get(CONF_NAME, DEFAULT_TITLE)).strip() or DEFAULT_TITLE
        zones = list(self._config.get(CONF_ZONES, []))
        self._config = {
            CONF_MAIN_RELAY_ENTITY_ID: user_input[CONF_MAIN_RELAY_ENTITY_ID],
            CONF_FLOW_SENSOR_ENTITY_ID: user_input.get(CONF_FLOW_SENSOR_ENTITY_ID),
            CONF_FLOW_DETECTION_THRESHOLD: user_input.get(CONF_FLOW_DETECTION_THRESHOLD),
            CONF_MISSING_FLOW_TIMEOUT_SECONDS: int(
                user_input[CONF_MISSING_FLOW_TIMEOUT_SECONDS]
            ),
            CONF_DEFAULT_HYSTERESIS: user_input[CONF_DEFAULT_HYSTERESIS],
            CONF_MIN_RELAY_ON_TIME_SECONDS: int(user_input[CONF_MIN_RELAY_ON_TIME_SECONDS]),
            CONF_MIN_RELAY_OFF_TIME_SECONDS: int(user_input[CONF_MIN_RELAY_OFF_TIME_SECONDS]),
            CONF_RELAY_OFF_DELAY_SECONDS: int(user_input[CONF_RELAY_OFF_DELAY_SECONDS]),
            CONF_FROST_PROTECTION_MIN_TEMP: user_input.get(CONF_FROST_PROTECTION_MIN_TEMP),
            CONF_ZONES: zones,
        }

    def _pending_zone_control_type(self) -> ControlType | None:
        """Return the control type for the pending zone."""
        if self._pending_zone is None:
            return None
        return ControlType(self._pending_zone[CONF_CONTROL_TYPE])

    def _build_pending_zone(self, user_input: dict[str, object]) -> None:
        """Store the shared zone fields that apply to all control types."""
        self._pending_zone = {
            CONF_NAME: str(user_input[CONF_NAME]).strip(),
            CONF_ENABLED: user_input[CONF_ENABLED],
            CONF_CONTROL_TYPE: user_input[CONF_CONTROL_TYPE],
            CONF_TARGET_SOURCE: user_input[CONF_TARGET_SOURCE],
            CONF_TARGET_ENTITY_ID: user_input[CONF_TARGET_ENTITY_ID],
            CONF_FROST_PROTECTION_MIN_TEMP: user_input.get(
                CONF_FROST_PROTECTION_MIN_TEMP
            ),
        }

    def _build_climate_zone(self, user_input: dict[str, object]) -> dict[str, object]:
        """Build a complete climate-zone config from pending and detail input."""
        assert self._pending_zone is not None
        return {
            **self._pending_zone,
            CONF_SENSOR_ENTITY_IDS: user_input[CONF_SENSOR_ENTITY_IDS],
            CONF_CLIMATE_ENTITY_IDS: user_input[CONF_CLIMATE_ENTITY_IDS],
            CONF_CLIMATE_OFF_FALLBACK_TEMPERATURE: user_input.get(
                CONF_CLIMATE_OFF_FALLBACK_TEMPERATURE
            ),
            CONF_LOCAL_GROUPS: [],
            CONF_AGGREGATION_MODE: user_input[CONF_AGGREGATION_MODE],
            CONF_PRIMARY_SENSOR_ENTITY_ID: user_input.get(CONF_PRIMARY_SENSOR_ENTITY_ID),
        }

    def _build_local_group(self, user_input: dict[str, object]) -> dict[str, object]:
        """Build a local-group config from the current step input."""
        zone_control_type = self._pending_zone_control_type()
        assert zone_control_type is not None
        return {
            CONF_NAME: str(user_input[CONF_NAME]).strip(),
            CONF_CONTROL_TYPE: zone_control_type,
            CONF_SENSOR_ENTITY_IDS: user_input[CONF_SENSOR_ENTITY_IDS],
            CONF_ACTUATOR_ENTITY_IDS: user_input[CONF_ACTUATOR_ENTITY_IDS],
            CONF_AGGREGATION_MODE: user_input[CONF_AGGREGATION_MODE],
            CONF_PRIMARY_SENSOR_ENTITY_ID: user_input.get(CONF_PRIMARY_SENSOR_ENTITY_ID),
            CONF_NUMBER_SEMANTIC_TYPE: user_input.get(CONF_NUMBER_SEMANTIC_TYPE),
            CONF_ACTIVE_VALUE: user_input.get(CONF_ACTIVE_VALUE),
            CONF_INACTIVE_VALUE: user_input.get(CONF_INACTIVE_VALUE),
        }

    def _build_non_climate_zone(self) -> dict[str, object]:
        """Build a complete switch or number zone from pending state."""
        assert self._pending_zone is not None
        return {
            **self._pending_zone,
            CONF_SENSOR_ENTITY_IDS: [],
            CONF_CLIMATE_ENTITY_IDS: [],
            CONF_LOCAL_GROUPS: deepcopy(self._pending_local_groups),
            CONF_AGGREGATION_MODE: AggregationMode.AVERAGE,
            CONF_PRIMARY_SENSOR_ENTITY_ID: None,
        }

    def _add_zone(self, zone: dict[str, object]) -> None:
        """Append a completed zone to the working config."""
        zone[CONF_NAME] = str(zone[CONF_NAME]).strip()
        zones = self._config.setdefault(CONF_ZONES, [])
        assert isinstance(zones, list)
        zones.append(zone)

    def _upsert_zone(self, zone: dict[str, object]) -> None:
        """Insert or replace a zone in the working config."""
        zones = self._zones()
        if self._editing_zone_index is None:
            zones.append(zone)
        else:
            zones[self._editing_zone_index] = zone
        self._config[CONF_ZONES] = zones

    def _clear_pending_zone(self) -> None:
        """Reset any in-progress zone editing state."""
        self._pending_zone = None
        self._pending_local_groups = []
        self._editing_zone_index = None
        self._editing_local_group_index = None

    def _zones(self) -> list[dict[str, object]]:
        """Return a mutable copy of the configured zones."""
        return deepcopy(list(self._config.get(CONF_ZONES, [])))

    def _zone_label(self, zone: dict[str, object]) -> str:
        """Return a human-readable label for a zone."""
        return f"{zone[CONF_NAME]} ({zone[CONF_CONTROL_TYPE]})"

    def _group_label(self, group: dict[str, object]) -> str:
        """Return a human-readable label for a local group."""
        return str(group[CONF_NAME])

    def _global_defaults(self) -> dict[str, object]:
        """Build suggested values for the global form."""
        return {
            CONF_NAME: self._title,
            CONF_MAIN_RELAY_ENTITY_ID: self._config.get(CONF_MAIN_RELAY_ENTITY_ID),
            CONF_FLOW_SENSOR_ENTITY_ID: self._config.get(CONF_FLOW_SENSOR_ENTITY_ID),
            CONF_FLOW_DETECTION_THRESHOLD: self._config.get(CONF_FLOW_DETECTION_THRESHOLD),
            CONF_MISSING_FLOW_TIMEOUT_SECONDS: self._config.get(
                CONF_MISSING_FLOW_TIMEOUT_SECONDS,
                DEFAULT_MISSING_FLOW_TIMEOUT_SECONDS,
            ),
            CONF_DEFAULT_HYSTERESIS: self._config.get(
                CONF_DEFAULT_HYSTERESIS, DEFAULT_HYSTERESIS
            ),
            CONF_MIN_RELAY_ON_TIME_SECONDS: self._config.get(
                CONF_MIN_RELAY_ON_TIME_SECONDS,
                DEFAULT_MIN_RELAY_ON_TIME_SECONDS,
            ),
            CONF_MIN_RELAY_OFF_TIME_SECONDS: self._config.get(
                CONF_MIN_RELAY_OFF_TIME_SECONDS,
                DEFAULT_MIN_RELAY_OFF_TIME_SECONDS,
            ),
            CONF_RELAY_OFF_DELAY_SECONDS: self._config.get(
                CONF_RELAY_OFF_DELAY_SECONDS,
                DEFAULT_RELAY_OFF_DELAY_SECONDS,
            ),
            CONF_FROST_PROTECTION_MIN_TEMP: self._config.get(
                CONF_FROST_PROTECTION_MIN_TEMP
            ),
        }

    def _zone_defaults(self) -> dict[str, object] | None:
        """Build suggested values for the zone basics form."""
        if self._editing_zone_index is None:
            return None
        zone = self._zones()[self._editing_zone_index]
        return {
            CONF_NAME: zone[CONF_NAME],
            CONF_ENABLED: zone.get(CONF_ENABLED, True),
            CONF_CONTROL_TYPE: zone[CONF_CONTROL_TYPE],
            CONF_TARGET_SOURCE: zone[CONF_TARGET_SOURCE],
            CONF_TARGET_ENTITY_ID: zone[CONF_TARGET_ENTITY_ID],
            CONF_FROST_PROTECTION_MIN_TEMP: zone.get(CONF_FROST_PROTECTION_MIN_TEMP),
        }

    def _climate_zone_defaults(self) -> dict[str, object] | None:
        """Build suggested values for the climate-zone detail form."""
        if self._editing_zone_index is None:
            return None
        zone = self._zones()[self._editing_zone_index]
        if zone[CONF_CONTROL_TYPE] != ControlType.CLIMATE:
            return None
        return {
            CONF_SENSOR_ENTITY_IDS: zone.get(CONF_SENSOR_ENTITY_IDS, []),
            CONF_CLIMATE_ENTITY_IDS: zone.get(CONF_CLIMATE_ENTITY_IDS, []),
            CONF_CLIMATE_OFF_FALLBACK_TEMPERATURE: zone.get(
                CONF_CLIMATE_OFF_FALLBACK_TEMPERATURE
            ),
            CONF_AGGREGATION_MODE: zone.get(CONF_AGGREGATION_MODE, AggregationMode.AVERAGE),
            CONF_PRIMARY_SENSOR_ENTITY_ID: zone.get(CONF_PRIMARY_SENSOR_ENTITY_ID),
        }

    def _local_group_defaults(self) -> dict[str, object] | None:
        """Build suggested values for the local-group detail form."""
        if self._editing_local_group_index is None:
            return None
        group = self._pending_local_groups[self._editing_local_group_index]
        return {
            CONF_NAME: group[CONF_NAME],
            CONF_SENSOR_ENTITY_IDS: group.get(CONF_SENSOR_ENTITY_IDS, []),
            CONF_ACTUATOR_ENTITY_IDS: group.get(CONF_ACTUATOR_ENTITY_IDS, []),
            CONF_AGGREGATION_MODE: group.get(CONF_AGGREGATION_MODE, AggregationMode.AVERAGE),
            CONF_PRIMARY_SENSOR_ENTITY_ID: group.get(CONF_PRIMARY_SENSOR_ENTITY_ID),
            CONF_NUMBER_SEMANTIC_TYPE: group.get(CONF_NUMBER_SEMANTIC_TYPE),
            CONF_ACTIVE_VALUE: group.get(CONF_ACTIVE_VALUE),
            CONF_INACTIVE_VALUE: group.get(CONF_INACTIVE_VALUE),
        }


class MultiZoneHeatingConfigFlow(_MultiZoneHeatingFlowBase, ConfigFlow, domain=DOMAIN):
    """Config flow for setting up a multi-zone heating system."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> MultiZoneHeatingOptionsFlow:
        """Create the options flow."""
        return MultiZoneHeatingOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, object] | None = None,
    ):
        """Handle the initial global system setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = self._validate_global_config(user_input)
            if not errors:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                self._save_global_config(user_input)
                return await self.async_step_zone()

        data_schema = self._global_schema(user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_zone(
        self,
        user_input: dict[str, object] | None = None,
    ):
        """Collect the shared configuration for a zone."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = self._validate_zone_basics(user_input)
            if not errors:
                self._build_pending_zone(user_input)
                self._pending_local_groups = []

                if user_input[CONF_CONTROL_TYPE] == ControlType.CLIMATE:
                    return await self.async_step_climate_zone()

                return await self.async_step_local_group()

        return self.async_show_form(
            step_id="zone",
            data_schema=self._zone_basics_schema(user_input),
            errors=errors,
        )

    async def async_step_climate_zone(
        self,
        user_input: dict[str, object] | None = None,
    ):
        """Collect climate-zone-specific settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = self._validate_climate_zone_details(user_input)
            if not errors and self._pending_zone is not None:
                self._add_zone(self._build_climate_zone(user_input))
                self._clear_pending_zone()
                return await self.async_step_zone_options()

        return self.async_show_form(
            step_id="climate_zone",
            data_schema=self._climate_zone_schema(user_input),
            errors=errors,
        )

    async def async_step_local_group(
        self,
        user_input: dict[str, object] | None = None,
    ):
        """Collect one local control group for a switch or number zone."""
        errors: dict[str, str] = {}
        zone_control_type = self._pending_zone_control_type()

        if zone_control_type is None:
            return await self.async_step_zone()

        if user_input is not None:
            errors = self._validate_local_group(user_input, zone_control_type)
            if not errors:
                self._pending_local_groups.append(self._build_local_group(user_input))
                return await self.async_step_local_group_options()

        return self.async_show_form(
            step_id="local_group",
            data_schema=self._local_group_schema(zone_control_type, user_input),
            errors=errors,
        )

    async def async_step_local_group_options(
        self,
        user_input: dict[str, object] | None = None,
    ):
        """Decide whether to add more local control groups."""
        if self._pending_zone is None:
            return await self.async_step_zone()

        if user_input is not None:
            if user_input["add_another_group"]:
                return await self.async_step_local_group()

            self._add_zone(self._build_non_climate_zone())
            self._clear_pending_zone()
            return await self.async_step_zone_options()

        return self.async_show_form(
            step_id="local_group_options",
            data_schema=self._local_group_options_schema(),
        )

    async def async_step_zone_options(
        self,
        user_input: dict[str, object] | None = None,
    ):
        """Decide whether to add another zone or finish setup."""
        if user_input is not None:
            if user_input["add_another_zone"]:
                return await self.async_step_zone()

            return self.async_create_entry(title=self._title, data=self._config)

        return self.async_show_form(
            step_id="zone_options",
            data_schema=self._zone_options_schema(),
        )


class MultiZoneHeatingOptionsFlow(
    _MultiZoneHeatingFlowBase, OptionsFlowWithConfigEntry
):
    """Options flow for editing an existing multi-zone heating setup."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow."""
        OptionsFlowWithConfigEntry.__init__(self, config_entry)
        _MultiZoneHeatingFlowBase.__init__(self)
        self._title = config_entry.title
        self._config = deepcopy(dict(config_entry.data))
        self._config.update(deepcopy(dict(config_entry.options)))

    async def async_step_init(
        self,
        user_input: dict[str, object] | None = None,
    ):
        """Choose what part of the configuration to edit."""
        if user_input is not None:
            action = user_input[CONF_ACTION]
            if action == ACTION_EDIT_GLOBALS:
                return await self.async_step_edit_globals()
            if action == ACTION_ADD_ZONE:
                self._clear_pending_zone()
                return await self.async_step_zone()
            if action == ACTION_EDIT_ZONE:
                return await self.async_step_select_zone_to_edit()
            if action == ACTION_REMOVE_ZONE:
                return await self.async_step_select_zone_to_remove()
            return self.async_create_entry(title=self._title, data=self._config)

        actions = [
            {"value": ACTION_EDIT_GLOBALS, "label": "Edit global settings"},
            {"value": ACTION_ADD_ZONE, "label": "Add zone"},
        ]
        if self._config.get(CONF_ZONES):
            actions.extend(
                [
                    {"value": ACTION_EDIT_ZONE, "label": "Edit zone"},
                    {"value": ACTION_REMOVE_ZONE, "label": "Remove zone"},
                ]
            )
        actions.append({"value": ACTION_DONE, "label": "Save changes"})

        return self.async_show_form(
            step_id="init",
            data_schema=self._action_schema(actions),
        )

    async def async_step_edit_globals(
        self,
        user_input: dict[str, object] | None = None,
    ):
        """Edit global integration settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = self._validate_global_config(user_input)
            if not errors:
                self._save_global_config(user_input)
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    title=self._title,
                )
                return await self.async_step_init()

        defaults = user_input or self._global_defaults()
        return self.async_show_form(
            step_id="edit_globals",
            data_schema=self._global_schema(defaults),
            errors=errors,
        )

    async def async_step_select_zone_to_edit(
        self,
        user_input: dict[str, object] | None = None,
    ):
        """Choose an existing zone to edit."""
        zones = self._zones()

        if user_input is not None:
            self._editing_zone_index = int(user_input[CONF_ZONE])
            self._editing_local_group_index = None
            return await self.async_step_zone()

        return self.async_show_form(
            step_id="select_zone_to_edit",
            data_schema=self._zone_select_schema(zones),
        )

    async def async_step_select_zone_to_remove(
        self,
        user_input: dict[str, object] | None = None,
    ):
        """Choose an existing zone to remove."""
        zones = self._zones()

        if user_input is not None:
            zone_index = int(user_input[CONF_ZONE])
            zones.pop(zone_index)
            self._config[CONF_ZONES] = zones
            return await self.async_step_init()

        return self.async_show_form(
            step_id="select_zone_to_remove",
            data_schema=self._zone_select_schema(zones),
        )

    async def async_step_zone(
        self,
        user_input: dict[str, object] | None = None,
    ):
        """Add or edit the shared configuration for a zone."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = self._validate_zone_basics(user_input)
            if not errors:
                self._build_pending_zone(user_input)
                selected_zone = None
                if self._editing_zone_index is not None:
                    selected_zone = self._zones()[self._editing_zone_index]

                if user_input[CONF_CONTROL_TYPE] == ControlType.CLIMATE:
                    self._pending_local_groups = []
                    return await self.async_step_climate_zone()

                if (
                    selected_zone is not None
                    and selected_zone[CONF_CONTROL_TYPE] == user_input[CONF_CONTROL_TYPE]
                ):
                    self._pending_local_groups = deepcopy(
                        list(selected_zone.get(CONF_LOCAL_GROUPS, []))
                    )
                else:
                    self._pending_local_groups = []

                if self._pending_local_groups:
                    return await self.async_step_manage_local_groups()

                self._editing_local_group_index = None
                return await self.async_step_local_group()

        defaults = user_input or self._zone_defaults()
        return self.async_show_form(
            step_id="zone",
            data_schema=self._zone_basics_schema(defaults),
            errors=errors,
        )

    async def async_step_climate_zone(
        self,
        user_input: dict[str, object] | None = None,
    ):
        """Add or edit climate-zone-specific settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = self._validate_climate_zone_details(user_input)
            if not errors:
                self._upsert_zone(self._build_climate_zone(user_input))
                self._clear_pending_zone()
                return await self.async_step_init()

        defaults = user_input or self._climate_zone_defaults()
        return self.async_show_form(
            step_id="climate_zone",
            data_schema=self._climate_zone_schema(defaults),
            errors=errors,
        )

    async def async_step_manage_local_groups(
        self,
        user_input: dict[str, object] | None = None,
    ):
        """Manage the local groups for the pending non-climate zone."""
        errors: dict[str, str] = {}

        if self._pending_zone is None:
            return await self.async_step_init()

        if user_input is not None:
            action = user_input[CONF_ACTION]
            if action == ACTION_ADD_GROUP:
                self._editing_local_group_index = None
                return await self.async_step_local_group()
            if action == ACTION_EDIT_GROUP:
                return await self.async_step_select_group_to_edit()
            if action == ACTION_REMOVE_GROUP:
                return await self.async_step_select_group_to_remove()
            if not self._pending_local_groups:
                errors = {"base": "zone_requires_local_groups"}
            else:
                self._upsert_zone(self._build_non_climate_zone())
                self._clear_pending_zone()
                return await self.async_step_init()

        actions = [
            {"value": ACTION_ADD_GROUP, "label": "Add local group"},
            {"value": ACTION_DONE, "label": "Done with zone"},
        ]
        if self._pending_local_groups:
            actions.extend(
                [
                    {"value": ACTION_EDIT_GROUP, "label": "Edit local group"},
                    {"value": ACTION_REMOVE_GROUP, "label": "Remove local group"},
                ]
            )

        return self.async_show_form(
            step_id="manage_local_groups",
            data_schema=self._action_schema(actions),
            errors=errors,
        )

    async def async_step_select_group_to_edit(
        self,
        user_input: dict[str, object] | None = None,
    ):
        """Choose a local group to edit."""
        if user_input is not None:
            self._editing_local_group_index = int(user_input[CONF_GROUP])
            return await self.async_step_local_group()

        return self.async_show_form(
            step_id="select_group_to_edit",
            data_schema=self._group_select_schema(self._pending_local_groups),
        )

    async def async_step_select_group_to_remove(
        self,
        user_input: dict[str, object] | None = None,
    ):
        """Choose a local group to remove."""
        if user_input is not None:
            group_index = int(user_input[CONF_GROUP])
            self._pending_local_groups.pop(group_index)
            return await self.async_step_manage_local_groups()

        return self.async_show_form(
            step_id="select_group_to_remove",
            data_schema=self._group_select_schema(self._pending_local_groups),
        )

    async def async_step_local_group(
        self,
        user_input: dict[str, object] | None = None,
    ):
        """Add or edit one local control group for a switch or number zone."""
        errors: dict[str, str] = {}
        zone_control_type = self._pending_zone_control_type()

        if zone_control_type is None:
            return await self.async_step_init()

        if user_input is not None:
            errors = self._validate_local_group(user_input, zone_control_type)
            if not errors:
                group = self._build_local_group(user_input)
                if self._editing_local_group_index is None:
                    self._pending_local_groups.append(group)
                else:
                    self._pending_local_groups[self._editing_local_group_index] = group
                self._editing_local_group_index = None
                return await self.async_step_manage_local_groups()

        defaults = user_input or self._local_group_defaults()
        return self.async_show_form(
            step_id="local_group",
            data_schema=self._local_group_schema(zone_control_type, defaults),
            errors=errors,
        )
