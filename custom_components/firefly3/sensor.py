"""Sensoren voor Firefly III Overzicht."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import CONF_URL, PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MANUFACTURER, SUBSCRIPTION_STATES
from .coordinator import FireflyConfigEntry, FireflyCoordinator


# ---------- hulpfuncties ----------

def _num(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _date(value: Any) -> date | None:
    if not value:
        return None
    return dt_util.parse_date(str(value)[:10])


def _bill_info(bill: dict) -> dict[str, Any]:
    """Bepaal status, verwachte datum en betaling binnen de huidige maand."""
    a = bill.get("attributes", {})
    today = dt_util.now().date()
    pay_dates = sorted(d for d in (_date(x) for x in a.get("pay_dates") or []) if d)
    paid = sorted(bill.get("paid", []), key=lambda p: p.get("date") or "")
    last = paid[-1] if paid else None

    if not a.get("active", True):
        status = "inactief"
    elif last:
        status = "betaald"
    elif pay_dates:
        status = "te_laat" if pay_dates[0] < today else "open"
    else:
        status = "niet_deze_maand"

    return {
        "status": status,
        "expected": pay_dates[0] if pay_dates else _date(a.get("next_expected_match")),
        "next_expected": _date(a.get("next_expected_match")),
        "paid_date": _date(last["date"]) if last else None,
        "paid_amount": last["amount"] if last else None,
        "paid_count": len(paid),
    }


# ---------- setup ----------

async def async_setup_entry(
    hass: HomeAssistant, entry: FireflyConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    known: set[str] = set()

    async_add_entities([TotalBalanceSensor(coordinator)])

    @callback
    def _add_new() -> None:
        """Voeg sensoren toe voor nieuwe rekeningen/spaarpotjes/abonnementen."""
        data = coordinator.data
        if data is None:
            return
        new: list[SensorEntity] = []
        for acc_id in data.accounts:
            if (key := f"a{acc_id}") not in known:
                known.add(key)
                new.append(AccountBalanceSensor(coordinator, acc_id))
        for pig_id in data.piggy_banks:
            if (key := f"p{pig_id}") not in known:
                known.add(key)
                new.extend(PiggySensor(coordinator, pig_id, *d) for d in PIGGY_SENSORS)
        for bill_id in data.bills:
            if (key := f"b{bill_id}") not in known:
                known.add(key)
                new.extend(
                    [
                        SubscriptionStatusSensor(coordinator, bill_id),
                        SubscriptionDateSensor(coordinator, bill_id, "expected", "Verwachte datum", "mdi:calendar-clock"),
                        SubscriptionPaidTextSensor(coordinator, bill_id, "paid_date", "Betaald op", "mdi:calendar-check"),
                        SubscriptionPaidTextSensor(coordinator, bill_id, "paid_amount", "Betaald bedrag", "mdi:cash-check"),
                        SubscriptionAmountSensor(coordinator, bill_id, "expected_amount", "Verwacht bedrag"),
                    ]
                )
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


# ---------- basisklassen ----------

class FireflyItemSensor(CoordinatorEntity[FireflyCoordinator], SensorEntity):
    """Sensor die hoort bij één rekening, spaarpot of abonnement."""

    _attr_has_entity_name = True
    _kind = ""          # attribuutnaam in FireflyData
    _model = ""         # ook prefix voor de apparaatnaam
    _url_path: str | None = None

    def __init__(self, coordinator: FireflyCoordinator, item_id: str, key: str, name: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._item_id = item_id
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{self._kind}_{item_id}_{key}"
        item_name = self._attrs.get("name", item_id)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{self._kind}_{item_id}")},
            name=f"{self._model} {item_name}",
            manufacturer=MANUFACTURER,
            model=self._model,
            sw_version=coordinator.version,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=(
                f"{entry.data[CONF_URL]}/{self._url_path}/{item_id}" if self._url_path else None
            ),
        )

    @property
    def _item(self) -> dict | None:
        return getattr(self.coordinator.data, self._kind).get(self._item_id)

    @property
    def _attrs(self) -> dict:
        item = self._item
        return item.get("attributes", {}) if item else {}

    @property
    def available(self) -> bool:
        return super().available and self._item is not None


# ---------- rekeningen ----------

class AccountBalanceSensor(FireflyItemSensor):
    _kind = "accounts"
    _model = "Rekening"
    _url_path = "accounts/show"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:bank"

    def __init__(self, coordinator: FireflyCoordinator, item_id: str) -> None:
        super().__init__(coordinator, item_id, "balance", "Saldo")

    @property
    def native_value(self) -> float | None:
        return _num(self._attrs.get("current_balance"))

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self._attrs.get("currency_code")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        a = self._attrs
        return {
            "iban": a.get("iban"),
            "rekeningnummer": a.get("account_number"),
            "rol": a.get("account_role"),
            "actief": a.get("active"),
            "telt_mee_in_vermogen": a.get("include_net_worth"),
            "saldo_datum": a.get("current_balance_date"),
        }


class TotalBalanceSensor(CoordinatorEntity[FireflyCoordinator], SensorEntity):
    """Totaal van alle actieve rekeningen die meetellen in je vermogen."""

    _attr_has_entity_name = True
    _attr_name = "Totaal saldo"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:scale-balance"

    def __init__(self, coordinator: FireflyCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_total_balance"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Firefly III",
            manufacturer=MANUFACTURER,
            sw_version=coordinator.version,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=entry.data[CONF_URL],
        )

    def _totals(self) -> tuple[dict[str, float], str | None]:
        totals: dict[str, float] = defaultdict(float)
        counts: Counter[str] = Counter()
        for acc in self.coordinator.data.accounts.values():
            a = acc.get("attributes", {})
            if not a.get("active", True) or not a.get("include_net_worth", True):
                continue
            if (value := _num(a.get("current_balance"))) is None:
                continue
            cur = a.get("currency_code") or "EUR"
            totals[cur] += value
            counts[cur] += 1
        main = counts.most_common(1)[0][0] if counts else None
        return totals, main

    @property
    def native_value(self) -> float | None:
        totals, main = self._totals()
        return round(totals[main], 2) if main else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self._totals()[1]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        totals, _ = self._totals()
        data = self.coordinator.data
        return {
            "per_valuta": {k: round(v, 2) for k, v in totals.items()},
            "aantal_rekeningen": len(data.accounts),
            "periode_start": data.period_start.isoformat(),
            "periode_eind": data.period_end.isoformat(),
        }


# ---------- spaarpotjes ----------

# (veld in API, naam, monetair?, icoon)
PIGGY_SENSORS = [
    ("current_amount", "Gespaard", True, "mdi:piggy-bank"),
    ("target_amount", "Doel", True, "mdi:flag-checkered"),
    ("left_to_save", "Nog te sparen", True, "mdi:cash-clock"),
    ("percentage", "Voortgang", False, "mdi:percent-circle"),
]


class PiggySensor(FireflyItemSensor):
    _kind = "piggy_banks"
    _model = "Spaarpot"
    _url_path = "piggy-banks/show"
    _attr_suggested_display_precision = 2

    def __init__(
        self, coordinator: FireflyCoordinator, item_id: str,
        field: str, name: str, monetary: bool, icon: str,
    ) -> None:
        super().__init__(coordinator, item_id, field, name)
        self._field = field
        self._monetary = monetary
        self._attr_icon = icon
        if monetary:
            self._attr_device_class = SensorDeviceClass.MONETARY
            self._attr_state_class = SensorStateClass.TOTAL
        else:
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_suggested_display_precision = 0

    @property
    def native_value(self) -> float | None:
        return _num(self._attrs.get(self._field))

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self._monetary:
            return self._attrs.get("currency_code")
        return PERCENTAGE

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self._field != "current_amount":
            return None
        a = self._attrs
        # Firefly 6.2+: meerdere rekeningen per spaarpot; ouder: account_name
        accounts = [x.get("name") for x in a.get("accounts") or [] if x.get("name")]
        if not accounts and a.get("account_name"):
            accounts = [a["account_name"]]
        return {
            "doel": _num(a.get("target_amount")),
            "voortgang": _num(a.get("percentage")),
            "startdatum": a.get("start_date"),
            "doeldatum": a.get("target_date"),
            "rekeningen": accounts,
            "groep": a.get("object_group_title"),
            "actief": a.get("active"),
        }


# ---------- abonnementen ----------

class SubscriptionBase(FireflyItemSensor):
    _kind = "bills"
    _model = "Abonnement"

    @property
    def _info(self) -> dict[str, Any]:
        item = self._item
        return _bill_info(item) if item else {}


class SubscriptionStatusSensor(SubscriptionBase):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = SUBSCRIPTION_STATES
    _attr_translation_key = "subscription_status"
    _attr_icon = "mdi:calendar-sync"

    def __init__(self, coordinator: FireflyCoordinator, item_id: str) -> None:
        super().__init__(coordinator, item_id, "status", "Status")

    @property
    def native_value(self) -> str | None:
        return self._info.get("status")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        a, info = self._attrs, self._info
        data = self.coordinator.data

        def iso(d: date | None) -> str | None:
            return d.isoformat() if d else None

        return {
            "verwachte_datum": iso(info.get("expected")),
            "volgende_verwachte_datum": iso(info.get("next_expected")),
            "betaald_op": iso(info.get("paid_date")),
            "betaald_bedrag": info.get("paid_amount"),
            "aantal_betalingen_deze_maand": info.get("paid_count"),
            "bedrag_min": _num(a.get("amount_min")),
            "bedrag_max": _num(a.get("amount_max")),
            "valuta": a.get("currency_code"),
            "frequentie": a.get("repeat_freq"),
            "groep": a.get("object_group_title"),
            "periode_start": data.period_start.isoformat(),
            "periode_eind": data.period_end.isoformat(),
        }


class SubscriptionDateSensor(SubscriptionBase):
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator, item_id, field: str, name: str, icon: str) -> None:
        super().__init__(coordinator, item_id, field, name)
        self._field = field
        self._attr_icon = icon

    @property
    def native_value(self) -> date | None:
        return self._info.get(self._field)


class SubscriptionAmountSensor(SubscriptionBase):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:cash"

    def __init__(self, coordinator, item_id, field: str, name: str) -> None:
        super().__init__(coordinator, item_id, field, name)
        self._field = field

    @property
    def native_value(self) -> float | None:
        if self._field == "paid_amount":
            return self._info.get("paid_amount")
        lo, hi = _num(self._attrs.get("amount_min")), _num(self._attrs.get("amount_max"))
        if lo is None or hi is None:
            return lo if hi is None else hi
        return round((lo + hi) / 2, 2)

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self._attrs.get("currency_code")


MAANDEN = [
    "januari", "februari", "maart", "april", "mei", "juni", "juli",
    "augustus", "september", "oktober", "november", "december",
]


def _eur(value: float) -> str:
    return "€ " + f"{value:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")


class SubscriptionPaidTextSensor(SubscriptionBase):
    """Betaaldatum of -bedrag als leesbare tekst, met een tekst als er nog niets betaald is.

    De ruwe waarden (ISO-datum en getal) staan als attributen op de Status-sensor.
    """

    def __init__(self, coordinator, item_id, field: str, name: str, icon: str) -> None:
        super().__init__(coordinator, item_id, field, name)
        self._field = field
        self._attr_icon = icon

    @property
    def native_value(self) -> str | None:
        if self._item is None:
            return None
        value = self._info.get(self._field)
        if self._field == "paid_date":
            if value is None:
                return "Datum onbekend"
            return f"{value.day} {MAANDEN[value.month - 1]} {value.year}"
        if value is None:
            return "Nog niet betaald"
        return _eur(value)
