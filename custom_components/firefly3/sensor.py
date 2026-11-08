"""Sensoren voor Firefly III rekeningen, spaarpotjes en abonnementen."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CONF_URL, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import FireflyConfigEntry
from .const import (
    CONF_ACCOUNTS,
    CONF_BILLS,
    CONF_PIGGY_BANKS,
    DOMAIN,
    KIND_ACCOUNT,
    KIND_BILL,
    KIND_PIGGY,
    MANUFACTURER,
    MODEL,
    WEB_PATH,
)
from .coordinator import FireflyCoordinator

Item = dict[str, Any]


# ---------- hulpfuncties ----------
def _num(value: Any) -> float | None:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None


def _currency(item: Item) -> str | None:
    return item.get("currency_code") or None


def _bill_amount(item: Item) -> float | None:
    lo, hi = _num(item.get("amount_min")), _num(item.get("amount_max"))
    if lo is None:
        return hi
    if hi is None:
        return lo
    return round((lo + hi) / 2, 2)


def _piggy_percentage(item: Item) -> float | None:
    pct = _num(item.get("percentage"))
    if pct is not None:
        return pct
    cur, target = _num(item.get("current_amount")), _num(item.get("target_amount"))
    if cur is None or not target:
        return None
    return round(cur / target * 100, 1)


def _pick(item: Item, *keys: str) -> dict[str, Any]:
    return {k: item.get(k) for k in keys if item.get(k) not in (None, "")}


def _account_attrs(item: Item) -> dict[str, Any]:
    return _pick(
        item, "type", "account_role", "iban", "account_number", "bic",
        "currency_symbol", "current_balance_date", "active", "include_net_worth",
        "credit_card_type", "liability_type", "interest", "interest_period",
    )


def _piggy_attrs(item: Item) -> dict[str, Any]:
    attrs = _pick(
        item, "target_amount", "left_to_save", "save_per_month",
        "start_date", "target_date", "active", "currency_symbol", "object_group_title",
    )
    # Firefly >= 6.2 kan meerdere gekoppelde rekeningen hebben, ouder slechts één.
    if item.get("accounts"):
        attrs["accounts"] = [
            {"id": a.get("account_id") or a.get("id"), "name": a.get("name"),
             "current_amount": a.get("current_amount")}
            for a in item["accounts"]
        ]
    elif item.get("account_name"):
        attrs["account"] = item.get("account_name")
    return attrs


def _bill_attrs(item: Item) -> dict[str, Any]:
    return _pick(
        item, "amount_min", "amount_max", "repeat_freq", "skip", "date", "end_date",
        "extension_date", "active", "currency_symbol", "next_expected_match",
        "next_expected_match_diff", "pay_dates", "paid_dates", "object_group_title",
    )


# ---------- entity descriptions ----------
@dataclass(frozen=True, kw_only=True)
class FireflySensorDescription(SensorEntityDescription):
    """Beschrijving van een Firefly-sensor."""

    value_fn: Callable[[Item], Any]
    monetary: bool = False
    attrs_fn: Callable[[Item], dict[str, Any]] | None = None


ACCOUNT_SENSORS: tuple[FireflySensorDescription, ...] = (
    FireflySensorDescription(
        key="balance",
        translation_key="balance",
        icon="mdi:bank",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        monetary=True,
        value_fn=lambda i: _num(i.get("current_balance")),
        attrs_fn=_account_attrs,
    ),
)

PIGGY_SENSORS: tuple[FireflySensorDescription, ...] = (
    FireflySensorDescription(
        key="current_amount",
        translation_key="current_amount",
        icon="mdi:piggy-bank",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        monetary=True,
        value_fn=lambda i: _num(i.get("current_amount")),
        attrs_fn=_piggy_attrs,
    ),
    FireflySensorDescription(
        key="target_amount",
        translation_key="target_amount",
        icon="mdi:target",
        device_class=SensorDeviceClass.MONETARY,
        monetary=True,
        value_fn=lambda i: _num(i.get("target_amount")),
    ),
    FireflySensorDescription(
        key="left_to_save",
        translation_key="left_to_save",
        icon="mdi:piggy-bank-outline",
        device_class=SensorDeviceClass.MONETARY,
        monetary=True,
        value_fn=lambda i: _num(i.get("left_to_save")),
    ),
    FireflySensorDescription(
        key="percentage",
        translation_key="percentage",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_piggy_percentage,
    ),
    FireflySensorDescription(
        key="target_date",
        translation_key="target_date",
        icon="mdi:calendar-flag",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda i: _date(i.get("target_date")),
    ),
)

BILL_SENSORS: tuple[FireflySensorDescription, ...] = (
    FireflySensorDescription(
        key="amount",
        translation_key="bill_amount",
        icon="mdi:cash-sync",
        device_class=SensorDeviceClass.MONETARY,
        monetary=True,
        value_fn=_bill_amount,
        attrs_fn=_bill_attrs,
    ),
    FireflySensorDescription(
        key="next_due",
        translation_key="next_due",
        icon="mdi:calendar-clock",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda i: _date(i.get("next_expected_match")),
    ),
)

SETUP: tuple[tuple[str, str, tuple[FireflySensorDescription, ...]], ...] = (
    (CONF_ACCOUNTS, KIND_ACCOUNT, ACCOUNT_SENSORS),
    (CONF_PIGGY_BANKS, KIND_PIGGY, PIGGY_SENSORS),
    (CONF_BILLS, KIND_BILL, BILL_SENSORS),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FireflyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Maak sensoren aan voor alle geselecteerde items."""
    coordinator = entry.runtime_data
    entities: list[FireflySensor] = []
    for conf_key, kind, descriptions in SETUP:
        for item_id in entry.options.get(conf_key, []):
            entities.extend(
                FireflySensor(coordinator, kind, str(item_id), desc)
                for desc in descriptions
            )
    async_add_entities(entities)


class FireflySensor(CoordinatorEntity[FireflyCoordinator], SensorEntity):
    """Eén waarde van een rekening, spaarpotje of abonnement."""

    _attr_has_entity_name = True
    entity_description: FireflySensorDescription

    def __init__(
        self,
        coordinator: FireflyCoordinator,
        kind: str,
        item_id: str,
        description: FireflySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._kind = kind
        self._item_id = item_id

        entry = coordinator.config_entry
        device_key = f"{entry.entry_id}_{kind}_{item_id}"
        self._attr_unique_id = f"{device_key}_{description.key}"

        item = self._item or {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_key)},
            name=item.get("name") or f"{MODEL[kind]} {item_id}",
            manufacturer=MANUFACTURER,
            model=MODEL[kind],
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=f"{entry.data[CONF_URL]}/{WEB_PATH[kind]}/{item_id}",
        )

    @property
    def _item(self) -> Item | None:
        data = self.coordinator.data or {}
        return data.get(self._kind, {}).get(self._item_id)

    @property
    def available(self) -> bool:
        return super().available and self._item is not None

    @property
    def native_value(self) -> Any:
        item = self._item
        return self.entity_description.value_fn(item) if item else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.entity_description.monetary:
            item = self._item
            return _currency(item) if item else None
        return self.entity_description.native_unit_of_measurement

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        item = self._item
        if not item or self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(item)
