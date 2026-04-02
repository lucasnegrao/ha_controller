"""Services for Universal Remote."""

import logging
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.service import validate_service_call

_LOGGER = logging.getLogger(__name__)

DOMAIN = "universal_controller"

SERVICE_LEARN = "learn_command"
SERVICE_DELETE = "delete_command"
SERVICE_MANAGE_BUTTONS = "manage_buttons"


async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Universal Remote."""

    async def handle_learn_command(call: ServiceCall) -> None:
        """Handle learn command service call."""
        remote_entity = call.data.get("remote_entity")
        device = call.data.get("device")
        command = call.data.get("command")
        command_type = call.data.get("command_type", "ir")
        
        if remote_entity:
            await remote_entity.async_learn_command(
                command=command,
                command_type=command_type,
                device=device,
            )

    async def handle_delete_command(call: ServiceCall) -> None:
        """Handle delete command service call."""
        remote_entity = call.data.get("remote_entity")
        device = call.data.get("device")
        command = call.data.get("command")
        
        if remote_entity:
            await remote_entity.async_delete_command(
                command=command,
                device=device,
            )

    hass.services.async_register(
        DOMAIN,
        SERVICE_LEARN,
        handle_learn_command,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE,
        handle_delete_command,
    )
