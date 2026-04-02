"""Config flow for Universal Remote integration."""

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .remote import DOMAIN, CONF_DEVICE

_LOGGER = logging.getLogger(__name__)



class UniversalRemoteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Universal Remote."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
             await self.async_set_unique_id(user_input[CONF_NAME])
              self._abort_if_unique_id_configured()
              return self.async_create_entry(
                  title=user_input[CONF_NAME], data=user_input
              )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): cv.string,
                vol.Required(CONF_DEVICE): cv.string,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors, last_step=True
        )

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this config entry."""
        return UniversalRemoteOptionsFlow(config_entry)


class UniversalRemoteOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Universal Remote."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options or {}
        schema = vol.Schema(
            {
                vol.Optional(
                    "auto_delete_buttons",
                    default=options.get("auto_delete_buttons", True)
                ): cv.boolean,
                vol.Optional(
                    "show_notifications",
                    default=options.get("show_notifications", True)
                ): cv.boolean,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
