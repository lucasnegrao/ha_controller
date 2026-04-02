import asyncio
import random

from homeassistant.core import HomeAssistant


class Hub:

    manufacturer = "Universal Controller"

    def __init__(self, hass: HomeAssistant, name: str) -> None:
        self._hass = hass
        self._name = name
        self._id = name.lower()
        self.buttons = []
        self.remotes = []
        self.online = True

    @property
    def hub_id(self) -> str:
        return self._id

    async def test_connection(self) -> bool:
        await asyncio.sleep(1)
        return True