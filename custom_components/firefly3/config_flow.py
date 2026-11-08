"""Config flow, opties en herconfiguratie voor Firefly III."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_URL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    FireflyAuthError,
    FireflyClient,
    FireflyConnectionError,
    normalize_url,
)
from .const import (
    CONF_ACCOUNTS,
    CONF_BILLS,
    CONF_PIGGY_BANKS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SELECTION_KEYS,
)

_LOGGER = logging.getLogger(__name__)

URL_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.URL))
TOKEN_SELECTOR = TextSelector(
    TextSelectorConfig(type=TextSelectorType.PASSWORD, multiline=False)
)

ACCOUNT_TYPE_LABEL = {
    "asset": "rekening",
    "liabilities": "schuld",
    "liability": "schuld",
}

REPEAT_LABEL = {
    "weekly": "wekelijks",
    "monthly": "maandelijks",
    "quarterly": "per kwartaal",
    "half-year": "halfjaarlijks",
    "yearly": "jaarlijks",
}


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _money(value: Any, attrs: Mapping[str, Any]) -> str:
    amount = _num(value)
    symbol = attrs.get("currency_symbol") or attrs.get("currency_code") or ""
    if amount is None:
        return "?"
    return f"{symbol} {amount:,.2f}".strip()


def _inactive(attrs: Mapping[str, Any]) -> str:
    return " – inactief" if attrs.get("active") is False else ""


def _build_choices(
    accounts: dict[str, dict], piggies: dict[str, dict], bills: dict[str, dict]
) -> dict[str, list[SelectOptionDict]]:
    """Maak lijsten met keuzes (id + leesbaar label) voor de selectievelden."""

    def sort_key(item: tuple[str, dict]) -> str:
        return str(item[1].get("name", "")).lower()

    acc_opts = [
        SelectOptionDict(
            value=item_id,
            label=(
                f"{a.get('name')} ({ACCOUNT_TYPE_LABEL.get(a.get('type', ''), a.get('type', ''))}, "
                f"{_money(a.get('current_balance'), a)}){_inactive(a)}"
            ),
        )
        for item_id, a in sorted(accounts.items(), key=sort_key)
    ]
    piggy_opts = [
        SelectOptionDict(
            value=item_id,
            label=(
                f"{p.get('name')} ({_money(p.get('current_amount'), p)}"
                f" / {_money(p.get('target_amount'), p)}){_inactive(p)}"
            ),
        )
        for item_id, p in sorted(piggies.items(), key=sort_key)
    ]
    bill_opts = [
        SelectOptionDict(
            value=item_id,
            label=(
                f"{b.get('name')} ({_money(b.get('amount_max') or b.get('amount_min'), b)}, "
                f"{REPEAT_LABEL.get(b.get('repeat_freq', ''), b.get('repeat_freq', ''))}){_inactive(b)}"
            ),
        )
        for item_id, b in sorted(bills.items(), key=sort_key)
    ]
    return {CONF_ACCOUNTS: acc_opts, CONF_PIGGY_BANKS: piggy_opts, CONF_BILLS: bill_opts}


async def _connect(
    hass: HomeAssistant, url: str, token: str, verify_ssl: bool
) -> tuple[FireflyClient, dict[str, Any]]:
    """Maak een client en controleer URL + token. Gooit Firefly*Error bij fouten."""
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    client = FireflyClient(session, url, token)
    info = await client.about()
    return client, info


async def _fetch_choices(client: FireflyClient) -> dict[str, list[SelectOptionDict]]:
    return _build_choices(
        await client.accounts(), await client.piggy_banks(), await client.bills()
    )


def _selection_schema(
    choices: dict[str, list[SelectOptionDict]],
    current: Mapping[str, Any],
    with_interval: bool,
) -> vol.Schema:
    """Schema met drie multi-select lijsten (+ optioneel het update-interval)."""
    fields: dict[Any, Any] = {}
    for key in SELECTION_KEYS:
        options = choices.get(key, [])
        if not options:
            continue  # niets om uit te kiezen, veld niet tonen
        valid = {o["value"] for o in options}
        default = [v for v in current.get(key, []) if v in valid]
        fields[vol.Optional(key, default=default)] = SelectSelector(
            SelectSelectorConfig(
                options=options, multiple=True, mode=SelectSelectorMode.LIST
            )
        )
    if with_interval:
        fields[
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=int(current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
            )
        ] = NumberSelector(
            NumberSelectorConfig(
                min=1, max=1440, step=1, mode=NumberSelectorMode.BOX,
                unit_of_measurement="min",
            )
        )
    return vol.Schema(fields)


def _counts(choices: dict[str, list[SelectOptionDict]]) -> dict[str, str]:
    return {
        "accounts": str(len(choices.get(CONF_ACCOUNTS, []))),
        "piggy_banks": str(len(choices.get(CONF_PIGGY_BANKS, []))),
        "bills": str(len(choices.get(CONF_BILLS, []))),
    }


def _selection_from_input(user_input: Mapping[str, Any]) -> dict[str, list[str]]:
    return {key: list(user_input.get(key, [])) for key in SELECTION_KEYS}


class FireflyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configuratie via de UI."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._title = "Firefly III"
        self._choices: dict[str, list[SelectOptionDict]] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return FireflyOptionsFlow()

    # ---------- Stap 1: URL + token ----------
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = normalize_url(user_input[CONF_URL])
            await self.async_set_unique_id(url)
            self._abort_if_unique_id_configured()
            try:
                client, info = await _connect(
                    self.hass, url, user_input[CONF_ACCESS_TOKEN],
                    user_input.get(CONF_VERIFY_SSL, True),
                )
                self._choices = await _fetch_choices(client)
            except FireflyAuthError:
                errors["base"] = "invalid_auth"
            except FireflyConnectionError as err:
                _LOGGER.warning("Kan Firefly III niet bereiken op %s: %s", url, err)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Onverwachte fout bij verbinden met Firefly III")
                errors["base"] = "unknown"
            else:
                self._data = {
                    CONF_URL: url,
                    CONF_ACCESS_TOKEN: user_input[CONF_ACCESS_TOKEN].strip(),
                    CONF_VERIFY_SSL: user_input.get(CONF_VERIFY_SSL, True),
                }
                if info.get("email"):
                    self._title = f"Firefly III ({info['email']})"
                return await self.async_step_select()

        schema = vol.Schema(
            {
                vol.Required(CONF_URL): URL_SELECTOR,
                vol.Required(CONF_ACCESS_TOKEN): TOKEN_SELECTOR,
                vol.Optional(CONF_VERIFY_SSL, default=True): BooleanSelector(),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
            description_placeholders={
                "example_local": "http://192.168.1.10:8080",
                "example_domain": "https://firefly.example.com",
            },
        )

    # ---------- Stap 2: kiezen wat je wilt zien ----------
    async def async_step_select(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            options: dict[str, Any] = _selection_from_input(user_input)
            options[CONF_SCAN_INTERVAL] = DEFAULT_SCAN_INTERVAL
            return self.async_create_entry(
                title=self._title, data=self._data, options=options
            )
        return self.async_show_form(
            step_id="select",
            data_schema=_selection_schema(self._choices, {}, with_interval=False),
            description_placeholders=_counts(self._choices),
        )

    # ---------- Nieuw token als het oude niet meer werkt ----------
    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            token = user_input[CONF_ACCESS_TOKEN].strip()
            try:
                await _connect(
                    self.hass, entry.data[CONF_URL], token,
                    entry.data.get(CONF_VERIFY_SSL, True),
                )
            except FireflyAuthError:
                errors["base"] = "invalid_auth"
            except FireflyConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Onverwachte fout bij reauth")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry, data={**entry.data, CONF_ACCESS_TOKEN: token}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_ACCESS_TOKEN): TOKEN_SELECTOR}),
            description_placeholders={"url": entry.data[CONF_URL]},
            errors=errors,
        )

    # ---------- URL / token achteraf wijzigen ----------
    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            url = normalize_url(user_input[CONF_URL])
            token = (user_input.get(CONF_ACCESS_TOKEN) or "").strip() or entry.data[
                CONF_ACCESS_TOKEN
            ]
            verify_ssl = user_input.get(CONF_VERIFY_SSL, True)
            try:
                await _connect(self.hass, url, token, verify_ssl)
            except FireflyAuthError:
                errors["base"] = "invalid_auth"
            except FireflyConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Onverwachte fout bij herconfigureren")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=url,
                    data={CONF_URL: url, CONF_ACCESS_TOKEN: token, CONF_VERIFY_SSL: verify_ssl},
                )
        schema = vol.Schema(
            {
                vol.Required(CONF_URL, default=entry.data[CONF_URL]): URL_SELECTOR,
                vol.Optional(CONF_ACCESS_TOKEN): TOKEN_SELECTOR,
                vol.Optional(
                    CONF_VERIFY_SSL, default=entry.data.get(CONF_VERIFY_SSL, True)
                ): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)


class FireflyOptionsFlow(OptionsFlow):
    """Selectie van rekeningen / spaarpotjes / abonnementen achteraf aanpassen."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self.config_entry
        if user_input is not None:
            options: dict[str, Any] = _selection_from_input(user_input)
            options[CONF_SCAN_INTERVAL] = int(
                user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            )
            return self.async_create_entry(data=options)

        try:
            client, _ = await _connect(
                self.hass, entry.data[CONF_URL], entry.data[CONF_ACCESS_TOKEN],
                entry.data.get(CONF_VERIFY_SSL, True),
            )
            choices = await _fetch_choices(client)
        except FireflyAuthError:
            return self.async_abort(reason="invalid_auth")
        except FireflyConnectionError:
            return self.async_abort(reason="cannot_connect")

        return self.async_show_form(
            step_id="init",
            data_schema=_selection_schema(choices, entry.options, with_interval=True),
            description_placeholders=_counts(choices),
        )
