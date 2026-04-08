"""Tests for the multi_zone_heating config flow."""

from __future__ import annotations

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_NAME

from custom_components.multi_zone_heating.const import DEFAULT_TITLE, DOMAIN


async def test_user_flow_creates_entry(hass) -> None:
    """The user flow should create a config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: DEFAULT_TITLE},
    )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_TITLE
    assert result["data"] == {}


async def test_user_flow_uses_custom_name(hass) -> None:
    """The user flow should persist a provided title."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: "My Heating"},
    )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "My Heating"


async def test_single_instance_flow_aborts_when_entry_exists(hass, config_entry) -> None:
    """Only one config entry should be allowed."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
