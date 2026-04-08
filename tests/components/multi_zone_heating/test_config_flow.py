"""Tests for the multi_zone_heating config flow."""

from __future__ import annotations

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_NAME

from custom_components.multi_zone_heating.const import DEFAULT_TITLE, DOMAIN
from custom_components.multi_zone_heating.config_flow import (
    CONF_ACTIVE_VALUE,
    CONF_ACTUATOR_ENTITY_IDS,
    CONF_AGGREGATION_MODE,
    CONF_CLIMATE_ENTITY_IDS,
    CONF_CONTROL_TYPE,
    CONF_DEFAULT_HYSTERESIS,
    CONF_ENABLED,
    CONF_FLOW_DETECTION_THRESHOLD,
    CONF_FLOW_SENSOR_ENTITY_ID,
    CONF_FROST_PROTECTION_MIN_TEMP,
    CONF_INACTIVE_VALUE,
    CONF_LOCAL_GROUPS,
    CONF_MAIN_RELAY_ENTITY_ID,
    CONF_MIN_RELAY_OFF_TIME_SECONDS,
    CONF_MIN_RELAY_ON_TIME_SECONDS,
    CONF_NUMBER_SEMANTIC_TYPE,
    CONF_PRIMARY_SENSOR_ENTITY_ID,
    CONF_RELAY_OFF_DELAY_SECONDS,
    CONF_SENSOR_ENTITY_IDS,
    CONF_TARGET_ENTITY_ID,
    CONF_TARGET_SOURCE,
    CONF_ZONES,
)
from custom_components.multi_zone_heating.models import (
    AggregationMode,
    ControlType,
    NumberSemanticType,
    TargetSourceType,
)


async def _start_basic_flow(hass, *, name: str = DEFAULT_TITLE):
    """Start the config flow and submit the global step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    return await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: name,
            CONF_MAIN_RELAY_ENTITY_ID: "switch.boiler_relay",
            CONF_DEFAULT_HYSTERESIS: 0.3,
            CONF_MIN_RELAY_ON_TIME_SECONDS: 0,
            CONF_MIN_RELAY_OFF_TIME_SECONDS: 0,
            CONF_RELAY_OFF_DELAY_SECONDS: 0,
        },
    )


async def test_user_flow_creates_entry_for_climate_zone(hass) -> None:
    """The flow should create a full config entry for a climate zone."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "My Heating",
            CONF_MAIN_RELAY_ENTITY_ID: "switch.boiler_relay",
            CONF_FLOW_SENSOR_ENTITY_ID: "sensor.system_flow",
            CONF_FLOW_DETECTION_THRESHOLD: 1.5,
            CONF_DEFAULT_HYSTERESIS: 0.4,
            CONF_MIN_RELAY_ON_TIME_SECONDS: 60,
            CONF_MIN_RELAY_OFF_TIME_SECONDS: 45,
            CONF_RELAY_OFF_DELAY_SECONDS: 30,
            CONF_FROST_PROTECTION_MIN_TEMP: 7.0,
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "zone"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Living Room",
            CONF_ENABLED: True,
            CONF_CONTROL_TYPE: ControlType.CLIMATE,
            CONF_TARGET_SOURCE: TargetSourceType.CLIMATE,
            CONF_TARGET_ENTITY_ID: "climate.living_room_target",
            CONF_FROST_PROTECTION_MIN_TEMP: 8.0,
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "climate_zone"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SENSOR_ENTITY_IDS: ["sensor.living_room_temperature"],
            CONF_CLIMATE_ENTITY_IDS: ["climate.living_room_radiator"],
            CONF_AGGREGATION_MODE: AggregationMode.PRIMARY,
            CONF_PRIMARY_SENSOR_ENTITY_ID: "sensor.living_room_temperature",
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "zone_options"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"add_another_zone": False},
    )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "My Heating"
    assert result["data"] == {
        CONF_MAIN_RELAY_ENTITY_ID: "switch.boiler_relay",
        CONF_FLOW_SENSOR_ENTITY_ID: "sensor.system_flow",
        CONF_FLOW_DETECTION_THRESHOLD: 1.5,
        CONF_DEFAULT_HYSTERESIS: 0.4,
        CONF_MIN_RELAY_ON_TIME_SECONDS: 60,
        CONF_MIN_RELAY_OFF_TIME_SECONDS: 45,
        CONF_RELAY_OFF_DELAY_SECONDS: 30,
        CONF_FROST_PROTECTION_MIN_TEMP: 7.0,
        CONF_ZONES: [
            {
                CONF_NAME: "Living Room",
                CONF_ENABLED: True,
                CONF_CONTROL_TYPE: ControlType.CLIMATE,
                CONF_TARGET_SOURCE: TargetSourceType.CLIMATE,
                CONF_TARGET_ENTITY_ID: "climate.living_room_target",
                CONF_FROST_PROTECTION_MIN_TEMP: 8.0,
                CONF_SENSOR_ENTITY_IDS: ["sensor.living_room_temperature"],
                CONF_CLIMATE_ENTITY_IDS: ["climate.living_room_radiator"],
                CONF_LOCAL_GROUPS: [],
                CONF_AGGREGATION_MODE: AggregationMode.PRIMARY,
                CONF_PRIMARY_SENSOR_ENTITY_ID: "sensor.living_room_temperature",
            }
        ],
    }


async def test_user_flow_creates_entry_for_switch_zone_with_local_group(hass) -> None:
    """The flow should create switch zones with at least one local group."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Switch System",
            CONF_MAIN_RELAY_ENTITY_ID: "switch.boiler_relay",
            CONF_DEFAULT_HYSTERESIS: 0.3,
            CONF_MIN_RELAY_ON_TIME_SECONDS: 0,
            CONF_MIN_RELAY_OFF_TIME_SECONDS: 0,
            CONF_RELAY_OFF_DELAY_SECONDS: 0,
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Bedroom",
            CONF_ENABLED: True,
            CONF_CONTROL_TYPE: ControlType.SWITCH,
            CONF_TARGET_SOURCE: TargetSourceType.INPUT_NUMBER,
            CONF_TARGET_ENTITY_ID: "input_number.bedroom_target",
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "local_group"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Radiator",
            CONF_SENSOR_ENTITY_IDS: ["sensor.bedroom_temperature"],
            CONF_ACTUATOR_ENTITY_IDS: ["switch.bedroom_valve"],
            CONF_AGGREGATION_MODE: AggregationMode.AVERAGE,
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "local_group_options"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"add_another_group": False},
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "zone_options"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"add_another_zone": False},
    )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Switch System"
    assert result["data"][CONF_ZONES] == [
        {
            CONF_NAME: "Bedroom",
            CONF_ENABLED: True,
            CONF_CONTROL_TYPE: ControlType.SWITCH,
            CONF_TARGET_SOURCE: TargetSourceType.INPUT_NUMBER,
            CONF_TARGET_ENTITY_ID: "input_number.bedroom_target",
            CONF_FROST_PROTECTION_MIN_TEMP: None,
            CONF_SENSOR_ENTITY_IDS: [],
            CONF_CLIMATE_ENTITY_IDS: [],
            CONF_LOCAL_GROUPS: [
                {
                    CONF_NAME: "Radiator",
                    CONF_CONTROL_TYPE: ControlType.SWITCH,
                    CONF_SENSOR_ENTITY_IDS: ["sensor.bedroom_temperature"],
                    CONF_ACTUATOR_ENTITY_IDS: ["switch.bedroom_valve"],
                    CONF_AGGREGATION_MODE: AggregationMode.AVERAGE,
                    CONF_PRIMARY_SENSOR_ENTITY_ID: None,
                    CONF_NUMBER_SEMANTIC_TYPE: None,
                    CONF_ACTIVE_VALUE: None,
                    CONF_INACTIVE_VALUE: None,
                }
            ],
            CONF_AGGREGATION_MODE: AggregationMode.AVERAGE,
            CONF_PRIMARY_SENSOR_ENTITY_ID: None,
        }
    ]


async def test_user_flow_supports_multiple_zones_and_multiple_local_groups(hass) -> None:
    """The add-another loops should allow multiple groups and multiple zones."""
    result = await _start_basic_flow(hass, name="Whole Home")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Upstairs",
            CONF_ENABLED: True,
            CONF_CONTROL_TYPE: ControlType.SWITCH,
            CONF_TARGET_SOURCE: TargetSourceType.INPUT_NUMBER,
            CONF_TARGET_ENTITY_ID: "input_number.upstairs_target",
        },
    )

    assert result["step_id"] == "local_group"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Bedroom Valve",
            CONF_SENSOR_ENTITY_IDS: ["sensor.bedroom_temperature"],
            CONF_ACTUATOR_ENTITY_IDS: ["switch.bedroom_valve"],
            CONF_AGGREGATION_MODE: AggregationMode.AVERAGE,
        },
    )

    assert result["step_id"] == "local_group_options"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"add_another_group": True},
    )

    assert result["step_id"] == "local_group"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Office Valve",
            CONF_SENSOR_ENTITY_IDS: ["sensor.office_temperature"],
            CONF_ACTUATOR_ENTITY_IDS: ["switch.office_valve"],
            CONF_AGGREGATION_MODE: AggregationMode.MINIMUM,
        },
    )

    assert result["step_id"] == "local_group_options"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"add_another_group": False},
    )

    assert result["step_id"] == "zone_options"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"add_another_zone": True},
    )

    assert result["step_id"] == "zone"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Living Room",
            CONF_ENABLED: True,
            CONF_CONTROL_TYPE: ControlType.CLIMATE,
            CONF_TARGET_SOURCE: TargetSourceType.CLIMATE,
            CONF_TARGET_ENTITY_ID: "climate.living_room_target",
        },
    )

    assert result["step_id"] == "climate_zone"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SENSOR_ENTITY_IDS: ["sensor.living_room_temperature"],
            CONF_CLIMATE_ENTITY_IDS: ["climate.living_room_radiator"],
            CONF_AGGREGATION_MODE: AggregationMode.AVERAGE,
        },
    )

    assert result["step_id"] == "zone_options"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"add_another_zone": False},
    )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert len(result["data"][CONF_ZONES]) == 2
    assert len(result["data"][CONF_ZONES][0][CONF_LOCAL_GROUPS]) == 2
    assert result["data"][CONF_ZONES][1][CONF_NAME] == "Living Room"


async def test_number_group_requires_number_values(hass) -> None:
    """Number-based groups should reject missing active or inactive values."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: DEFAULT_TITLE,
            CONF_MAIN_RELAY_ENTITY_ID: "switch.boiler_relay",
            CONF_DEFAULT_HYSTERESIS: 0.3,
            CONF_MIN_RELAY_ON_TIME_SECONDS: 0,
            CONF_MIN_RELAY_OFF_TIME_SECONDS: 0,
            CONF_RELAY_OFF_DELAY_SECONDS: 0,
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Office",
            CONF_ENABLED: True,
            CONF_CONTROL_TYPE: ControlType.NUMBER,
            CONF_TARGET_SOURCE: TargetSourceType.INPUT_NUMBER,
            CONF_TARGET_ENTITY_ID: "number.office_target",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Desk Radiator",
            CONF_SENSOR_ENTITY_IDS: ["sensor.office_temperature"],
            CONF_ACTUATOR_ENTITY_IDS: ["number.office_valve"],
            CONF_AGGREGATION_MODE: AggregationMode.AVERAGE,
            CONF_NUMBER_SEMANTIC_TYPE: NumberSemanticType.PERCENTAGE,
            CONF_ACTIVE_VALUE: 80,
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "local_group"
    assert result["errors"] == {"base": "number_values_required"}


async def test_global_config_requires_flow_threshold_when_flow_sensor_is_set(hass) -> None:
    """A configured flow sensor should require a matching threshold."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: DEFAULT_TITLE,
            CONF_MAIN_RELAY_ENTITY_ID: "switch.boiler_relay",
            CONF_FLOW_SENSOR_ENTITY_ID: "sensor.system_flow",
            CONF_DEFAULT_HYSTERESIS: 0.3,
            CONF_MIN_RELAY_ON_TIME_SECONDS: 0,
            CONF_MIN_RELAY_OFF_TIME_SECONDS: 0,
            CONF_RELAY_OFF_DELAY_SECONDS: 0,
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "flow_threshold_required"}


async def test_zone_rejects_target_entity_domain_mismatch(hass) -> None:
    """Zone target entity IDs should match the selected target source type."""
    result = await _start_basic_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Living Room",
            CONF_ENABLED: True,
            CONF_CONTROL_TYPE: ControlType.CLIMATE,
            CONF_TARGET_SOURCE: TargetSourceType.CLIMATE,
            CONF_TARGET_ENTITY_ID: "input_number.living_room_target",
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "zone"
    assert result["errors"] == {"base": "target_entity_domain_mismatch"}


async def test_zone_requires_non_empty_name(hass) -> None:
    """Zone names should reject blank input."""
    result = await _start_basic_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "   ",
            CONF_ENABLED: True,
            CONF_CONTROL_TYPE: ControlType.CLIMATE,
            CONF_TARGET_SOURCE: TargetSourceType.CLIMATE,
            CONF_TARGET_ENTITY_ID: "climate.living_room_target",
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "zone"
    assert result["errors"] == {"base": "zone_name_required"}


async def test_local_group_requires_non_empty_name(hass) -> None:
    """Local groups should reject blank input."""
    result = await _start_basic_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Bedroom",
            CONF_ENABLED: True,
            CONF_CONTROL_TYPE: ControlType.SWITCH,
            CONF_TARGET_SOURCE: TargetSourceType.INPUT_NUMBER,
            CONF_TARGET_ENTITY_ID: "input_number.bedroom_target",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "   ",
            CONF_SENSOR_ENTITY_IDS: ["sensor.bedroom_temperature"],
            CONF_ACTUATOR_ENTITY_IDS: ["switch.bedroom_valve"],
            CONF_AGGREGATION_MODE: AggregationMode.AVERAGE,
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "local_group"
    assert result["errors"] == {"base": "group_name_required"}


async def test_climate_zone_requires_primary_sensor_when_primary_mode_selected(hass) -> None:
    """Primary aggregation should require a primary sensor selection."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: DEFAULT_TITLE,
            CONF_MAIN_RELAY_ENTITY_ID: "switch.boiler_relay",
            CONF_DEFAULT_HYSTERESIS: 0.3,
            CONF_MIN_RELAY_ON_TIME_SECONDS: 0,
            CONF_MIN_RELAY_OFF_TIME_SECONDS: 0,
            CONF_RELAY_OFF_DELAY_SECONDS: 0,
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Living Room",
            CONF_ENABLED: True,
            CONF_CONTROL_TYPE: ControlType.CLIMATE,
            CONF_TARGET_SOURCE: TargetSourceType.CLIMATE,
            CONF_TARGET_ENTITY_ID: "climate.living_room_target",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SENSOR_ENTITY_IDS: ["sensor.living_room_temperature"],
            CONF_CLIMATE_ENTITY_IDS: ["climate.living_room_radiator"],
            CONF_AGGREGATION_MODE: AggregationMode.PRIMARY,
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "climate_zone"
    assert result["errors"] == {"base": "primary_sensor_required"}


async def test_single_instance_flow_aborts_when_entry_exists(hass, config_entry) -> None:
    """Only one config entry should be allowed."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
