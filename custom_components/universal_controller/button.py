"""Support for Universal Remote buttons."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

from . import HubConfigEntry
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HubConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    hub = config_entry.runtime_data

    new_devices = []
    for remote in hub.remote:
        buttons_filename = f"universal_controller_BUTTONS_{remote}.json"
        store = Store(hass, 1, buttons_filename)
        
        new_devices = async_load_persisted_buttons(store, remote)
        
        if new_devices:
            async_add_entities(new_devices)
            hub.buttons[remote] += new_devices

async def async_load_persisted_buttons(store, remote) -> None:
        """Load persisted buttons from storage and recreate them."""
        new_buttons = []
      
        try:
            persisted = await store.async_load() or {}
            
            for device, command in persisted.items():
                new_buttons += await async_add_button(remote, device, command.key(), False, store)
            
            if new_buttons:
              return new_buttons
        except Exception as err:
            _LOGGER.error("Error loading persisted buttons: %s", err)

async def async_add_button(
         remote: str, device: str, command: str, persist: bool = False, store=None, 
    ) -> ButtonEntity:
        
        if not store:
            buttons_filename = f"universal_controller_BUTTONS_{remote}.json"
            store = Store(remote._hass, 1, buttons_filename)
        
        button = ControllerCommandButton(
            remote,
            device,
            command,
        )
        
        _LOGGER.info("Created button for %s:%s", device, command)
        
        if button:
            try:
                if persist:
                    await async_persist_button(store, remote, device, command)
                return button
            except Exception as err:
                _LOGGER.error("Error adding button entity: %s", err)

async def async_persist_button(store, device: str, command: str, code: str) -> None:
        """Save button information for persistence across restarts."""
        try:
            persisted = await store.async_load() or {}
            if device not in persisted:
                persisted[device] = {}
            
            persisted[device][command] = code
            
            await store.async_save(persisted)
            _LOGGER.debug("Persisted button for %s", device)
        except Exception as err:
            _LOGGER.error("Error persisting button: %s", err)

async def remove_persisted_button(hass, remote: str, device: str, command: str) -> None:
    """Remove a button from persistent storage."""
    try:
        
        buttons_filename = f"universal_controller_BUTTONS_{remote}.json"
        store = Store(hass, 1, buttons_filename)
        
        persisted = await store.async_load() or {}
        if device in persisted and command in persisted[device]:
            del persisted[device][command]
            if not persisted[device]:
                del persisted[device]
            await store.async_save(persisted)
            _LOGGER.debug("Removed persisted button for %s:%s", device, command)
    except Exception as err:
        _LOGGER.error("Error removing persisted button: %s", err)


class ControllerCommandButton(ButtonEntity):
    """A button entity that triggers a remote command."""

    def __init__(self, remote, device, command
    ) -> None:
        """Initialize the remote command button."""
        super().__init__(remote)

        self._remote = remote
        self._command = command
        # Generate unique entity ID
        self._attr_unique_id = (
            f"{remote.unique_id}_cmd_{device}_{command}"
            .replace(" ", "_").lower()
        )
        
        # Set friendly name
        self._attr_name = f"{device} {command}".title()

    @property
    def available(self) -> bool:
        """Return True if roller and hub is available."""
        return self._remote.online and self._remote.hub.online

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        self._remote.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        self._remote.remove_callback(self.async_write_ha_state)


    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._remote.remote_id)},
         }

    async def async_press(self) -> None:
        """Send the controller command when button is pressed."""
        try:
            _LOGGER.debug(
                "Button pressed: sending command '%s' to device '%s'",
                self._command,
                self._device,
            )
            await self._remote.async_send_command(
                command=self._command,
                device=self._device,
            )
        except Exception as err:
            _LOGGER.error(
                "Error sending command '%s' to device '%s': %s",
                self._command,
                self._device,
                err,
            )
            raise

