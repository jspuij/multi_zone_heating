"""Config flow for the multi_zone_heating integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import DEFAULT_TITLE, DOMAIN
from .models import AggregationMode, ControlType, NumberSemanticType, TargetSourceType

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
CONF_ZONES = "zones"

DEFAULT_HYSTERESIS = 0.3
DEFAULT_MISSING_FLOW_TIMEOUT_SECONDS = 0
DEFAULT_MIN_RELAY_ON_TIME_SECONDS = 0
DEFAULT_MIN_RELAY_OFF_TIME_SECONDS = 0
DEFAULT_RELAY_OFF_DELAY_SECONDS = 0


class MultiZoneHeatingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for setting up a multi-zone heating system."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._config: dict[str, object] = {}
        self._title = DEFAULT_TITLE
        self._pending_zone: dict[str, object] | None = None
        self._pending_local_groups: list[dict[str, object]] = []

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

                self._title = str(user_input.get(CONF_NAME, DEFAULT_TITLE)).strip() or DEFAULT_TITLE
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
                    CONF_ZONES: [],
                }
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
                self._pending_zone = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_ENABLED: user_input[CONF_ENABLED],
                    CONF_CONTROL_TYPE: user_input[CONF_CONTROL_TYPE],
                    CONF_TARGET_SOURCE: user_input[CONF_TARGET_SOURCE],
                    CONF_TARGET_ENTITY_ID: user_input[CONF_TARGET_ENTITY_ID],
                    CONF_FROST_PROTECTION_MIN_TEMP: user_input.get(
                        CONF_FROST_PROTECTION_MIN_TEMP
                    ),
                }
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
                zone = {
                    **self._pending_zone,
                    CONF_SENSOR_ENTITY_IDS: user_input[CONF_SENSOR_ENTITY_IDS],
                    CONF_CLIMATE_ENTITY_IDS: user_input[CONF_CLIMATE_ENTITY_IDS],
                    CONF_CLIMATE_OFF_FALLBACK_TEMPERATURE: user_input.get(
                        CONF_CLIMATE_OFF_FALLBACK_TEMPERATURE
                    ),
                    CONF_LOCAL_GROUPS: [],
                    CONF_AGGREGATION_MODE: user_input[CONF_AGGREGATION_MODE],
                    CONF_PRIMARY_SENSOR_ENTITY_ID: user_input.get(
                        CONF_PRIMARY_SENSOR_ENTITY_ID
                    ),
                }
                self._add_zone(zone)
                self._pending_zone = None
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
                group = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_CONTROL_TYPE: zone_control_type,
                    CONF_SENSOR_ENTITY_IDS: user_input[CONF_SENSOR_ENTITY_IDS],
                    CONF_ACTUATOR_ENTITY_IDS: user_input[CONF_ACTUATOR_ENTITY_IDS],
                    CONF_AGGREGATION_MODE: user_input[CONF_AGGREGATION_MODE],
                    CONF_PRIMARY_SENSOR_ENTITY_ID: user_input.get(
                        CONF_PRIMARY_SENSOR_ENTITY_ID
                    ),
                    CONF_NUMBER_SEMANTIC_TYPE: user_input.get(CONF_NUMBER_SEMANTIC_TYPE),
                    CONF_ACTIVE_VALUE: user_input.get(CONF_ACTIVE_VALUE),
                    CONF_INACTIVE_VALUE: user_input.get(CONF_INACTIVE_VALUE),
                }
                self._pending_local_groups.append(group)
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

            zone = {
                **self._pending_zone,
                CONF_SENSOR_ENTITY_IDS: [],
                CONF_CLIMATE_ENTITY_IDS: [],
                CONF_LOCAL_GROUPS: self._pending_local_groups,
                CONF_AGGREGATION_MODE: AggregationMode.AVERAGE,
                CONF_PRIMARY_SENSOR_ENTITY_ID: None,
            }
            self._add_zone(zone)
            self._pending_zone = None
            self._pending_local_groups = []
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

    def _global_schema(
        self, user_input: dict[str, object] | None = None
    ) -> vol.Schema:
        """Build the global configuration form schema."""
        schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_TITLE): str,
                vol.Required(CONF_MAIN_RELAY_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["switch"])
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
        # Number-based groups always require both configured values in v1 so the
        # later runtime logic can deterministically drive the actuator when heat
        # starts and when it stops, regardless of semantic type.
        if zone_control_type == ControlType.NUMBER and (
            user_input.get(CONF_ACTIVE_VALUE) is None
            or user_input.get(CONF_INACTIVE_VALUE) is None
        ):
            return {"base": "number_values_required"}
        return {}

    def _pending_zone_control_type(self) -> ControlType | None:
        """Return the control type for the pending zone."""
        if self._pending_zone is None:
            return None
        return ControlType(self._pending_zone[CONF_CONTROL_TYPE])

    def _add_zone(self, zone: dict[str, object]) -> None:
        """Append a completed zone to the working config."""
        zone[CONF_NAME] = str(zone[CONF_NAME]).strip()
        zones = self._config.setdefault(CONF_ZONES, [])
        assert isinstance(zones, list)
        zones.append(zone)
