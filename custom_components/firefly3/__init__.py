"""Firefly III integratie: rekeningen, spaarpotjes en abonnementen."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_URL, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FireflyClient
from .const import DOMAIN, KIND_BY_CONF, LEGACY_TOKEN_KEYS, SELECTION_KEYS
from .coordinator import FireflyCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type FireflyConfigEntry = ConfigEntry[FireflyCoordinator]


def selected_device_keys(entry: ConfigEntry) -> set[str]:
    """Device-sleutels van alle items die de gebruiker heeft aangevinkt."""
    return {
        f"{entry.entry_id}_{KIND_BY_CONF[conf]}_{item_id}"
        for conf in SELECTION_KEYS
        for item_id in entry.options.get(conf, [])
    }


async def async_setup_entry(hass: HomeAssistant, entry: FireflyConfigEntry) -> bool:
    """Zet de integratie op vanuit een config entry."""
    token = _async_ensure_token(hass, entry)
    if not token:
        # Geen token opgeslagen: laat Home Assistant om een (nieuw) token vragen.
        raise ConfigEntryAuthFailed("Er is geen token opgeslagen voor Firefly III")

    session = async_get_clientsession(hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, True))
    client = FireflyClient(session, entry.data[CONF_URL], token)
    coordinator = FireflyCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    _async_remove_deselected(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FireflyConfigEntry) -> bool:
    """Ontlaad de integratie."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: FireflyConfigEntry) -> None:
    """Herlaad na het wijzigen van de opties (selectie / interval)."""
    await hass.config_entries.async_reload(entry.entry_id)


@callback
def _async_ensure_token(hass: HomeAssistant, entry: ConfigEntry) -> str | None:
    """Geef het token terug; zet een token onder een oude sleutel om naar access_token."""
    if token := entry.data.get(CONF_ACCESS_TOKEN):
        return token
    for key in LEGACY_TOKEN_KEYS:
        if token := entry.data.get(key):
            data = {k: v for k, v in entry.data.items() if k not in LEGACY_TOKEN_KEYS}
            data[CONF_ACCESS_TOKEN] = token
            hass.config_entries.async_update_entry(entry, data=data)
            return token
    return None


@callback
def _async_remove_deselected(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Verwijder entiteiten en apparaten van items die niet meer geselecteerd zijn."""
    keep = selected_device_keys(entry)

    ent_reg = er.async_get(hass)
    for ent in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if not any(ent.unique_id.startswith(f"{key}_") for key in keep):
            ent_reg.async_remove(ent.entity_id)

    dev_reg = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        idents = {ident for domain, ident in device.identifiers if domain == DOMAIN}
        if not idents & keep:
            dev_reg.async_update_device(device.id, remove_config_entry_id=entry.entry_id)
