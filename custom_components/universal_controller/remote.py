"""Platform for Universal controller integration."""
import logging
import voluptuous as vol
import asyncio
import json

from homeassistant.components.remote import (
    ATTR_ALTERNATIVE,
    ATTR_COMMAND_TYPE,
    ATTR_DELAY_SECS,
    ATTR_remote,
    ATTR_NUM_REPEATS,
    ATTR_TIMEOUT,
    DEFAULT_DELAY_SECS,
    SERVICE_DELETE_COMMAND,
    SERVICE_LEARN_COMMAND,
    SERVICE_SEND_COMMAND,
    RemoteEntity,
    RemoteEntityFeature,
    PLATFORM_SCHEMA,
    LEARN_COMMAND
)

from homeassistant.const import CONF_NAME, ATTR_COMMAND, STATE_OFF, Platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.storage import Store
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util
from homeassistant.core import callback
from homeassistant.components import persistent_notification
from datetime import timedelta

from . import HubConfigEntry
from .const import DOMAIN
from .button import async_add_button, remove_persisted_button

_LOGGER = logging.getLogger(__name__)

CONF_REMOTE = "remote"

SUPPORT_UNIVERSAL_REMOTE = LEARN_COMMAND

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_REMOTE): cv.entity_id,
    }
)

LEARNING_TIMEOUT = timedelta(seconds=60)

COMMAND_TYPE_IR = "ir"
COMMAND_TYPE_RF = "rf"

COMMAND_TYPES = [COMMAND_TYPE_IR] # we only support ir now

COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_COMMAND): vol.All(
            cv.ensure_list, [vol.All(cv.string, vol.Length(min=1))], vol.Length(min=1)
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

SERVICE_SEND_SCHEMA = COMMAND_SCHEMA.extend(
    {
        vol.Optional(ATTR_DELAY_SECS, default=DEFAULT_DELAY_SECS): vol.Coerce(float),
    }
)

SERVICE_LEARN_SCHEMA = COMMAND_SCHEMA.extend(
    {
        vol.Required(ATTR_remote): vol.All(cv.string, vol.Length(min=1)),
        vol.Optional(ATTR_ALTERNATIVE, default=False): cv.boolean,
        vol.Optional(ATTR_TIMEOUT, default=LEARNING_TIMEOUT): cv.positive_int,
    }
)

SERVICE_DELETE_SCHEMA = COMMAND_SCHEMA.extend(
    {vol.Required(ATTR_remote): vol.All(cv.string, vol.Length(min=1))}
)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HubConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    
    hub = config_entry.runtime_data
    new_devices = []
    new_devices += [UniversalControllerRemoteEntity(remote, hub) for remote in hub.remotes]
    async_add_entities(new_devices)
    hub.remotes += new_devices

class UniversalControllerRemoteEntity(RemoteEntity):
    """Universal Controller Remote entity."""

    def __init__(self, remote, hub):
        self._config_entry = hub.config_entry
        self._remote = remote
        self._attr_is_on = True
        self._attr_supported_features = (
            RemoteEntityFeature.LEARN_COMMAND
        )
        self._attr_unique_id = f"{self._controller.controller_id}_remote"
        store_filename = f"universalcontroller_remote_codes_{remote}.json"
        self._store = Store(hub.hass, 1, store_filename)
    
    
    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self._remote.register_callback(self.async_write_ha_state)

    @property
    def device_info(self):
        """Information about this entity/device."""
        return {
            "identifiers": {(DOMAIN, self._remote.remote_id)},
            # If desired, the name for the device could be different to the entity
            "name": self._config_entry.name,
            "sw_version": self._remote.firmware_version,
            "model": self._remote.model,
            "manufacturer": self._remote.hub.manufacturer,
        }

    @property
    def available(self):
        return True


    async def async_send_command(self, command, device=None, **kwargs):
        """Send a command by name or raw code."""
        if not device:
            _LOGGER.error("No device name provided for sending.")
            return
        if not isinstance(command, list):
            command = [command]
        
        # Load the stored commands from the JSON file
        codes = await self._store.async_load() or {}
        device_codes = codes.get(device, {})
        commands_to_send = []

        for cmd in command:
            # If the command is a known name, use the stored raw code
            if cmd in device_codes:
                commands_to_send.append(device_codes[cmd])
            else:
                commands_to_send.append(cmd)  # Assume it's already a raw code

        if 0 == 0:
            num_repeats = kwargs.get("num_repeats", 1)
            delay_secs = kwargs.get("delay_secs", 0)
            hold_secs = kwargs.get("hold_secs", 0)

            for cmd in commands_to_send:
                # Ensure the command is a list of integers
                if isinstance(cmd, str):
                    try:
                        cmd = [int(x) for x in cmd.split(",")]
                    except ValueError:
                        _LOGGER.error("Invalid command format for ESPHome: %s", cmd)
                        continue
                elif not isinstance(cmd, list):
                    _LOGGER.error("Invalid command format for ESPHome: %s", cmd)
                    continue

                for i in range(num_repeats):
                    # Call the ESPHome service with the list of integers
                    await self.hass.services.async_call(
                        "esphome",
                        f"{self._remote}_send",
                        {"command": cmd},
                        blocking=True,
                    )
                    _LOGGER.debug("Sent raw command '%s' to ESPHome device %s", cmd, self._remote)
                    # Hold the button if requested (simulate long press)
                    if hold_secs and hold_secs > 0:
                        await asyncio.sleep(hold_secs)

                    # Delay between repeats, except after the last one
                    if i < num_repeats - 1 and delay_secs:
                        await asyncio.sleep(delay_secs)
    
    async def async_learn_command(self, **kwargs):
        command = kwargs.get(ATTR_COMMAND)
        device = kwargs.get(ATTR_remote)
        command_type = kwargs.get(ATTR_COMMAND_TYPE)
        timeout = kwargs.get(ATTR_TIMEOUT)
        
        """Learn one or more commands and save them under the specified device."""
        if not device:
            _LOGGER.error("No device name provided for learning.")
            return
        if not command:
            _LOGGER.error("No command name(s) provided for learning.")
            return

        # Support both single string and list of commands
        if isinstance(command, str):
            command_names = [command]
        else:
            command_names = list(command)

        # Use custom timeout if provided
        learning_timeout = timedelta(seconds=timeout) if timeout else LEARNING_TIMEOUT

        # Load or create the storage file for this controller
        codes = await self._store.async_load() or {}
        device_codes = codes.get(device, {})

        for cmd_name in command_names:
            notification_id = f"learn_command_{device}_{cmd_name}".replace(" ", "_").lower()
            persistent_notification.async_create(
                self.hass,
                f"Press the '{cmd_name}' button on your '{device}' remote now.",
                title="Learn command",
                notification_id=notification_id,
            )

            learned_code = None

            if 0 == 0:
                # Prepare to catch the next IR event
                event_type = f"esphome.{self._remote}_ir_received"
                event_future = asyncio.get_running_loop().create_future()  # Ensure event_future is created properly

                @callback
                def event_listener(event):
                    code = event.data.get("code")
                    if code and not event_future.done():
                        event_future.set_result(code)

                remove_listener = None
                try:
                    # Register the listener
                    remove_listener = self.hass.bus.async_listen_once(event_type, event_listener)

                    # Signal ESPHome that learning has started
                    await self.hass.services.async_call(
                        "esphome", f"{self._remote}_learning_started", {}, blocking=True
                    )
                    await self.hass.services.async_call(
                        "esphome", f"{self._remote}_learn", {"command_type": command_type}, blocking=True
                    )

                    # Wait for the event to be set
                    learned_code = await asyncio.wait_for(event_future, timeout=learning_timeout.total_seconds())
                    _LOGGER.debug("Learned code from ESPHome: %s", learned_code)

                except asyncio.TimeoutError:
                    _LOGGER.error("Timeout waiting for ESPHome learned code event.")
                    persistent_notification.async_create(
                        self.hass,
                        f"Timeout: No code received for '{cmd_name}' on '{device}'.",
                        title="Learn command",
                        notification_id=notification_id,
                    )
                    continue

                finally:
                    # Ensure the listener is removed only if it was registered
                    if remove_listener:
                        remove_listener()
                    await self.hass.services.async_call(
                        "esphome",
                        f"{self._remote}_learning_ended",
                        {},
                        blocking=True,
                    ),
                    persistent_notification.async_dismiss(self.hass, notification_id)
            if learned_code:
                device_codes[cmd_name] = learned_code
                _LOGGER.info("Saved learned code for %s:%s", device, cmd_name)

        # Save all learned codes for this device
        codes[device] = device_codes
        await self._store.async_save(codes)
        
        # Add button entities for newly learned commands
        for cmd_name in command_names:
            await async_add_button(self, device, cmd_name, True)

    async def async_turn_on(self, **kwargs):
        self._attr_is_on = True

    async def async_turn_off(self, **kwargs):
        self._attr_is_on = False

    async def async_update(self):
        # Optionally implement: update state from device
        pass
    

    async def async_delete_command(self, command=None, device=None, **kwargs):
        """Delete one or more commands from the storage."""
        if not device:
            _LOGGER.error("No device name provided for deleting commands.")
            return
        if not command:
            _LOGGER.error("No command name(s) provided for deletion.")
            return

        # Support both single string and list of commands
        if isinstance(command, str):
            command_names = [command]
        else:
            command_names = list(command)

        # Load the storage file
        codes = await self._store.async_load() or {}
        device_codes = codes.get(device, {})

        # Delete the specified commands
        for cmd_name in command_names:
            if cmd_name in device_codes:
                del device_codes[cmd_name]
                _LOGGER.info("Deleted command '%s' for device '%s'", cmd_name, device)
                
                # Also delete the button entity and persist the change
                button_id = f"{device}_{cmd_name}".replace(" ", "_").lower()
                if button_id in self._button_entities:
                    del self._button_entities[button_id]
                
                # Remove from persisted buttons
                await remove_persisted_button(hass, self, device, cmd_name)
            else:
                _LOGGER.warning("Command '%s' not found for device '%s'", cmd_name, device)

        # Save the updated codes back to storage
        codes[device] = device_codes
        await self._store.async_save(codes)
