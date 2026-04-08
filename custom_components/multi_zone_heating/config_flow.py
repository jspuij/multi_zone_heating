"""Config flow for the multi_zone_heating integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_NAME

from .const import DEFAULT_TITLE, DOMAIN


class MultiZoneHeatingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Minimal config flow for bootstrap setup."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, str] | None = None,
    ):
        """Handle the initial setup step."""
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            # Issue 001 only creates the entry shell; actual configuration fields
            # like the main relay entity will be collected in later milestones.
            title = user_input.get(CONF_NAME, DEFAULT_TITLE).strip() or DEFAULT_TITLE
            return self.async_create_entry(title=title, data={})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_NAME, default=DEFAULT_TITLE): str,
                }
            ),
        )
