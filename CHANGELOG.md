# Changelog

All notable changes to this project are documented here.
Versions follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

## [1.1.0] - 2026-11-08
### Changed
- Restored the integration code that was in use before the HACS releases (0.2.2, "Firefly III Overzicht").
  Versions 1.0.0 to 1.0.3 accidentally shipped a different implementation with other sensor names,
  which broke existing dashboards. Sensors are again named `sensor.rekening_<name>_saldo`,
  `sensor.spaarpot_<name>_gespaard`, `sensor.abonnement_<name>_status` and so on.
- A token stored as `access_token` by 1.0.x is migrated automatically; if no token is stored,
  Home Assistant asks for a new one.
- Restored the original icon.

## [1.0.3] - 2026-11-08
### Added
- Integration icon in `custom_components/firefly3/brand/` (Firefly III logo), shown from Home Assistant 2026.3.

## [1.0.2] - 2026-11-08
### Fixed
- `KeyError: 'access_token'` on startup for existing installations without a token, or with the token stored under another key.
  A token under an old key is migrated automatically; if it is missing, Home Assistant asks for a new token.
- **Configure** and **Reconfigure** returned a 500 error when no token was stored.

## [1.0.1] - 2026-11-08
### Changed
- Example URLs in the setup screen now use description placeholders (required by hassfest).

## [1.0.0] - 2026-11-08
### Added
- First release: Firefly III accounts, piggy banks and subscriptions as sensors.
- Installation and updates via HACS.
