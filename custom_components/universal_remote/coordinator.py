class MyCoordinator(DataUpdateCoordinator[dict[str, MyDevice]]):
    """Class to manage fetching data."""

    def __init__(self, hass: HomeAssistant, client: MyClient) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, MyDevice]:
        try:
            return await self.client.get_data()
        except MyException as ex:
            raise UpdateFailed(f"The service is unavailable: {ex}")
