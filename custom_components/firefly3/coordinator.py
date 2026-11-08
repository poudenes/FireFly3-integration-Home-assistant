"""Data-coördinator voor Firefly III Overzicht."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import FireflyApi, FireflyAuthError, FireflyConnectionError
from .const import (
    CONF_ACCOUNTS,
    CONF_BILLS,
    CONF_PIGGY_BANKS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

type FireflyConfigEntry = ConfigEntry[FireflyCoordinator]


def current_period() -> tuple[date, date]:
    today = dt_util.now().date()
    return today.replace(day=1), today.replace(
        day=calendar.monthrange(today.year, today.month)[1]
    )


@dataclass
class FireflyData:
    accounts: dict[str, dict]
    piggy_banks: dict[str, dict]
    bills: dict[str, dict]
    period_start: date
    period_end: date


class FireflyCoordinator(DataUpdateCoordinator[FireflyData]):
    """Haalt periodiek de gekozen rekeningen, spaarpotjes en abonnementen op."""

    config_entry: FireflyConfigEntry

    def __init__(self, hass: HomeAssistant, entry: FireflyConfigEntry, api: FireflyApi) -> None:
        minutes = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=minutes),
        )
        self.api = api
        self.version: str | None = None
        self._amount_cache: dict[str, float] = {}

    def _selected(self, key: str) -> set[str]:
        return {str(x) for x in self.config_entry.options.get(key, [])}

    async def _async_setup(self) -> None:
        try:
            self.version = (await self.api.about()).get("version")
        except FireflyAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except FireflyConnectionError as err:
            raise UpdateFailed(str(err)) from err

    async def _paid_amount(self, paid: dict) -> float | None:
        journal_id = str(paid.get("transaction_journal_id"))
        if journal_id in self._amount_cache:
            return self._amount_cache[journal_id]
        group_id = paid.get("transaction_group_id")
        if not group_id:
            return None
        try:
            group = await self.api.transaction_group(str(group_id))
        except FireflyConnectionError as err:
            _LOGGER.debug("Bedrag van transactie %s niet op te halen: %s", group_id, err)
            return None
        splits = group.get("attributes", {}).get("transactions", [])
        match = next(
            (s for s in splits if str(s.get("transaction_journal_id")) == journal_id),
            splits[0] if splits else None,
        )
        if not match:
            return None
        try:
            amount = round(abs(float(match["amount"])), 2)
        except (KeyError, TypeError, ValueError):
            return None
        self._amount_cache[journal_id] = amount
        return amount

    async def _async_update_data(self) -> FireflyData:
        start, end = current_period()
        want_acc = self._selected(CONF_ACCOUNTS)
        want_pig = self._selected(CONF_PIGGY_BANKS)
        want_bill = self._selected(CONF_BILLS)
        try:
            accounts = await self.api.asset_accounts() if want_acc else []
            piggies = await self.api.piggy_banks() if want_pig else []
            bills = await self.api.bills(start, end) if want_bill else []
            accounts = [a for a in accounts if str(a["id"]) in want_acc]
            piggies = [p for p in piggies if str(p["id"]) in want_pig]
            bills = [b for b in bills if str(b["id"]) in want_bill]
            for bill in bills:
                paid = []
                for p in bill.get("attributes", {}).get("paid_dates") or []:
                    paid.append(
                        {
                            "date": p.get("date"),
                            "amount": await self._paid_amount(p),
                            "transaction_group_id": p.get("transaction_group_id"),
                        }
                    )
                bill["paid"] = paid
        except FireflyAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except FireflyConnectionError as err:
            raise UpdateFailed(f"Firefly III niet bereikbaar: {err}") from err

        _LOGGER.debug(
            "Firefly: %s rekeningen, %s spaarpotjes, %s abonnementen",
            len(accounts), len(piggies), len(bills),
        )
        return FireflyData(
            accounts={str(a["id"]): a for a in accounts},
            piggy_banks={str(p["id"]): p for p in piggies},
            bills={str(b["id"]): b for b in bills},
            period_start=start,
            period_end=end,
        )
