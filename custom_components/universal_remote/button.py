
"""Support for ZHA button."""

from __future__ import annotations

import functools
import logging

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

# from .entity import ZHAEntity
# from .helpers import (
#     SIGNAL_ADD_ENTITIES,
#     EntityData,
#     async_add_entities as zha_async_add_entities,
#     convert_zha_error_to_ha_error,
#     get_zha_data,
# )

_LOGGER = logging.getLogger(__name__)

class controllerButton(code, action):

    def __init__(self, entity_data: EntityData) -> None:
        """Initialize the ZHA binary sensor."""
        super().__init__(entity_data)
        if self.entity_data.entity.info_object.device_class is not None:
            self._attr_device_class = ButtonDeviceClass(
                self.entity_data.entity.info_object.device_class
            )

    async def async_press(self) -> None:
        """Send out a update command."""
        await self.entity_data.entity.async_press()
