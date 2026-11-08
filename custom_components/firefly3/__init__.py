"""Firefly III Overzicht: rekeningen, spaarpotjes en abonnementen als sensoren."""

from __future__ import annotations

from homeassistant.const import CONF_API_TOKEN, CONF_URL, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FireflyApi
from .const import CONF_ACCOUNTS, CONF_BILLS, CONF_PIGGY_BANKS, DOMAIN, LEGACY_TOKEN_KEYS
from .coordinator import FireflyConfigEntry, FireflyCoordinator

PLATFORMS = [Platform.SENSOR]


def _remove_unselected_devices(hass: HomeAssistant, entry: FireflyConfigEntry) -> None:
    """Verwijder apparaten (en hun sensoren) die niet meer geselecteerd zijn."""
    eid = entry.entry_id
    wanted = {eid}
    for kind in (CONF_ACCOUNTS, CONF_PIGGY_BANKS, CONF_BILLS):
        wanted |= {f"{eid}_{kind}_{i}" for i in entry.options.get(kind, [])}
    dev_reg = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(dev_reg, eid):
        if not any(d == DOMAIN and i in wanted for d, i in device.identifiers):
            dev_reg.async_update_device(device.id, remove_config_entry_id=eid)


@callback
def _ensure_token(hass: HomeAssistant, entry: FireflyConfigEntry) -> str | None:
    """Geef het token; zet een token onder een andere sleutel om naar api_token."""
    if token := entry.data.get(CONF_API_TOKEN):
        return token
    for key in LEGACY_TOKEN_KEYS:
        if token := entry.data.get(key):
            data = {k: v for k, v in entry.data.items() if k not in LEGACY_TOKEN_KEYS}
            data[CONF_API_TOKEN] = token
            hass.config_entries.async_update_entry(entry, data=data)
            return token
    return None


async def async_setup_entry(hass: HomeAssistant, entry: FireflyConfigEntry) -> bool:
    if not (token := _ensure_token(hass, entry)):
        raise ConfigEntryAuthFailed("Er is geen token opgeslagen voor Firefly III")
    session = async_get_clientsession(hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, True))
    api = FireflyApi(session, entry.data[CONF_URL], token)
    coordinator = FireflyCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    _remove_unselected_devices(hass, entry)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload(hass: HomeAssistant, entry: FireflyConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: FireflyConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
