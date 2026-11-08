"""Constants for the Firefly III (selectie) integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "firefly3"
MANUFACTURER: Final = "Firefly III"

CONF_ACCOUNTS: Final = "accounts"
CONF_PIGGY_BANKS: Final = "piggy_banks"
CONF_BILLS: Final = "bills"
CONF_SCAN_INTERVAL: Final = "scan_interval"

SELECTION_KEYS: Final = (CONF_ACCOUNTS, CONF_PIGGY_BANKS, CONF_BILLS)

DEFAULT_SCAN_INTERVAL: Final = 15  # minuten

# Sleutels waaronder oudere installaties het token mogelijk hebben opgeslagen.
LEGACY_TOKEN_KEYS: Final = ("api_token", "token", "api_key", "personal_access_token")

# Interne "soorten" items; worden gebruikt in unique_id's en device identifiers.
KIND_ACCOUNT: Final = "account"
KIND_PIGGY: Final = "piggy"
KIND_BILL: Final = "bill"

KIND_BY_CONF: Final = {
    CONF_ACCOUNTS: KIND_ACCOUNT,
    CONF_PIGGY_BANKS: KIND_PIGGY,
    CONF_BILLS: KIND_BILL,
}

# Pad in de Firefly III web-UI om een item te openen (configuration_url).
WEB_PATH: Final = {
    KIND_ACCOUNT: "accounts/show",
    KIND_PIGGY: "piggy-banks/show",
    KIND_BILL: "bills/show",
}

MODEL: Final = {
    KIND_ACCOUNT: "Rekening",
    KIND_PIGGY: "Spaarpotje",
    KIND_BILL: "Abonnement",
}
