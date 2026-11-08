"""Config flow voor Firefly III Overzicht."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_API_TOKEN, CONF_URL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
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

from .api import FireflyApi, FireflyAuthError, FireflyConnectionError
from .const import (
    CONF_ACCOUNTS,
    CONF_BILLS,
    CONF_PIGGY_BANKS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_URL,
    DOMAIN,
)
from .coordinator import current_period

_LOGGER = logging.getLogger(__name__)

KINDS = (CONF_ACCOUNTS, CONF_PIGGY_BANKS, CONF_BILLS)
TOKEN_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, default=DEFAULT_URL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.URL)
        ),
        vol.Required(CONF_API_TOKEN): TOKEN_SELECTOR,
        vol.Optional(CONF_VERIFY_SSL, default=True): bool,
    }
)


def _make_api(hass: HomeAssistant, url: str, token: str, verify_ssl: bool) -> FireflyApi:
    return FireflyApi(async_get_clientsession(hass, verify_ssl=verify_ssl), url, token)


def _error_for(err: Exception) -> str:
    if isinstance(err, FireflyAuthError):
        return "invalid_auth"
    if isinstance(err, FireflyConnectionError):
        return "cannot_connect"
    _LOGGER.exception("Onverwachte fout bij verbinden met Firefly III")
    return "unknown"


async def _fetch_choices(api: FireflyApi) -> dict[str, list[dict]]:
    """Alle rekeningen, spaarpotjes en abonnementen om uit te kiezen."""
    start, end = current_period()
    return {
        CONF_ACCOUNTS: await api.asset_accounts(),
        CONF_PIGGY_BANKS: await api.piggy_banks(),
        CONF_BILLS: await api.bills(start, end),
    }


def _options(items: list[dict]) -> list[SelectOptionDict]:
    def label(i: dict) -> str:
        a = i.get("attributes", {})
        name = a.get("name") or str(i["id"])
        return name if a.get("active", True) else f"{name} (inactief)"

    return [
        SelectOptionDict(value=str(i["id"]), label=label(i))
        for i in sorted(items, key=lambda i: (i.get("attributes", {}).get("name") or "").lower())
    ]


def _selection_schema(
    choices: dict[str, list[dict]], selected: dict[str, list[str]] | None
) -> dict:
    """Schema-velden voor de drie keuzelijsten.

    Zonder eerdere keuze staat niets aangevinkt, zodat je bewust kiest.
    """
    fields: dict = {}
    for kind in KINDS:
        valid = {str(i["id"]) for i in choices[kind]}
        default = [x for x in (selected or {}).get(kind, []) if x in valid]
        fields[vol.Optional(kind, default=default)] = SelectSelector(
            SelectSelectorConfig(
                options=_options(choices[kind]),
                multiple=True,
                mode=SelectSelectorMode.DROPDOWN,
            )
        )
    return fields


class FireflyConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._choices: dict[str, list[dict]] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].strip().rstrip("/")
            await self.async_set_unique_id(url.lower())
            self._abort_if_unique_id_configured()
            api = _make_api(
                self.hass, url, user_input[CONF_API_TOKEN], user_input[CONF_VERIFY_SSL]
            )
            try:
                await api.about()
                self._choices = await _fetch_choices(api)
            except Exception as err:  # noqa: BLE001
                errors["base"] = _error_for(err)
            else:
                self._data = {**user_input, CONF_URL: url}
                return await self.async_step_select()
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_select(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title=f"Firefly III ({self._data[CONF_URL].split('://')[-1]})",
                data=self._data,
                options={
                    **{k: user_input.get(k, []) for k in KINDS},
                    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                },
            )
        return self.async_show_form(
            step_id="select",
            data_schema=vol.Schema(_selection_schema(self._choices, None)),
            description_placeholders={
                "accounts": str(len(self._choices[CONF_ACCOUNTS])),
                "piggy_banks": str(len(self._choices[CONF_PIGGY_BANKS])),
                "bills": str(len(self._choices[CONF_BILLS])),
            },
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            api = _make_api(
                self.hass, entry.data[CONF_URL], user_input[CONF_API_TOKEN],
                entry.data.get(CONF_VERIFY_SSL, True),
            )
            try:
                await api.about()
            except Exception as err:  # noqa: BLE001
                errors["base"] = _error_for(err)
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_API_TOKEN: user_input[CONF_API_TOKEN]}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_TOKEN): TOKEN_SELECTOR}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return FireflyOptionsFlow()


class FireflyOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={
                    **{k: user_input.get(k, []) for k in KINDS},
                    CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                }
            )
        entry = self.config_entry
        if not entry.data.get(CONF_API_TOKEN):
            return self.async_abort(reason="missing_token")
        api = _make_api(
            self.hass, entry.data[CONF_URL], entry.data[CONF_API_TOKEN],
            entry.data.get(CONF_VERIFY_SSL, True),
        )
        try:
            choices = await _fetch_choices(api)
        except (FireflyAuthError, FireflyConnectionError):
            return self.async_abort(reason="cannot_connect")

        fields = _selection_schema(choices, dict(entry.options))
        fields[
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            )
        ] = NumberSelector(
            NumberSelectorConfig(
                min=1, max=1440, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement="min"
            )
        )
        return self.async_show_form(step_id="init", data_schema=vol.Schema(fields))
