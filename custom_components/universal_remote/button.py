"""Support for Universal Remote buttons."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonDeviceClass
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class RemoteCommandButton(ButtonEntity):
    """A button entity that triggers a remote command."""

    def __init__(self,
        hass: HomeAssistant,
        remote_entity: Any,
        device_name: str,
        command_name: str,
    ) -> None:
        """Initialize the remote command button.
        
        Args:
            hass: Home Assistant instance
            remote_entity: The UniversalRemote entity
            device_name: Name of the device (e.g., 'TV')
            command_name: Name of the command (e.g., 'power', 'volume_up')
        """
        self.hass = hass
        self._remote_entity = remote_entity
        self._device_name = device_name
        self._command_name = command_name
        
        # Generate unique entity ID
        self._attr_unique_id = (
            f"{remote_entity.unique_id}_cmd_{device_name}_{command_name}"
            .replace(" ", "_").lower()
        )
        
        # Set friendly name
        self._attr_name = f"{device_name} {command_name}".title()
        

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {("universal_controller", self._device_name)},
            "name": self._device_name,
            "manufacturer": "Universal Controller",
            "model": "Learned Command",
        }

    async def async_press(self) -> None:
        """Send the remote command when button is pressed."""
        try:
            _LOGGER.debug(
                "Button pressed: sending command '%s' to device '%s'",
                self._command_name,
                self._device_name,
            )
            await self._remote_entity.async_send_command(
                command=self._command_name,
                device=self._device_name,
            )
        except Exception as err:
            _LOGGER.error(
                "Error sending command '%s' to device '%s': %s",
                self._command_name,
                self._device_name,
                err,
            )
            raise

    @property
    def available(self) -> bool:
        """Return if button is available."""
        return self._remote_entity.available
