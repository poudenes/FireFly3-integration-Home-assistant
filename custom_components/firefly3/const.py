"""Constanten voor Firefly III Overzicht."""

DOMAIN = "firefly3"

CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 15  # minuten
DEFAULT_URL = "https://ff.hassio.nl"

MANUFACTURER = "Firefly III"

SUBSCRIPTION_STATES = ["betaald", "open", "te_laat", "niet_deze_maand", "inactief"]

CONF_ACCOUNTS = "accounts"
CONF_PIGGY_BANKS = "piggy_banks"
CONF_BILLS = "bills"

# Andere sleutels waaronder het token kan staan (o.a. door versie 1.0.x).
LEGACY_TOKEN_KEYS = ("access_token", "token", "api_key", "personal_access_token")
