"""DataUpdateCoordinator voor Firefly III."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FireflyAuthError, FireflyClient, FireflyError
from .const import (
    CONF_ACCOUNTS,
    CONF_BILLS,
    CONF_PIGGY_BANKS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    KIND_ACCOUNT,
    KIND_BILL,
    KIND_PIGGY,
)

_LOGGER = logging.getLogger(__name__)

FireflyData = dict[str, dict[str, dict[str, Any]]]


class FireflyCoordinator(DataUpdateCoordinator[FireflyData]):
    """Haalt periodiek alleen de geselecteerde soorten gegevens op."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: FireflyClient) -> None:
        minutes = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=max(1, minutes)),
        )
        self.client = client

    async def _async_update_data(self) -> FireflyData:
        opts = self.config_entry.options
        data: FireflyData = {KIND_ACCOUNT: {}, KIND_PIGGY: {}, KIND_BILL: {}}
        try:
            if opts.get(CONF_ACCOUNTS):
                data[KIND_ACCOUNT] = await self.client.accounts()
            if opts.get(CONF_PIGGY_BANKS):
                data[KIND_PIGGY] = await self.client.piggy_banks()
            if opts.get(CONF_BILLS):
                data[KIND_BILL] = await self.client.bills()
        except FireflyAuthError as err:
            raise ConfigEntryAuthFailed(f"Firefly III weigert het token: {err}") from err
        except FireflyError as err:
            raise UpdateFailed(f"Fout bij ophalen uit Firefly III: {err}") from err
        return data
