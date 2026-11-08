# Changelog

Alle noemenswaardige wijzigingen worden hier bijgehouden.
Versienummering volgt [Semantic Versioning](https://semver.org/lang/nl/): `MAJOR.MINOR.PATCH`.

## [1.1.0] - 2026-11-08
### Gewijzigd
- De integratiecode is teruggezet naar de versie die eerder in gebruik was (0.2.2, "Firefly III Overzicht").
  Versies 1.0.0 t/m 1.0.3 bevatten per ongeluk een andere opzet met andere sensoren, waardoor dashboards niet meer klopten.
  De sensoren heten weer o.a. `sensor.rekening_<naam>_saldo`, `sensor.spaarpot_<naam>_gespaard` en `sensor.abonnement_<naam>_status`.
- Token dat door 1.0.x als `access_token` is opgeslagen wordt automatisch omgezet; ontbreekt het, dan vraagt Home Assistant om een nieuw token.
- Origineel icoon terug.

## [1.0.3] - 2026-11-08
### Toegevoegd
- Eigen icoon in `custom_components/firefly3/brand/` (Firefly III-logo); zichtbaar vanaf Home Assistant 2026.3.

## [1.0.2] - 2026-11-08
### Opgelost
- `KeyError: 'access_token'` bij het opstarten van een bestaande installatie zonder (of met een anders genoemd) token.
  Een token onder een oude sleutel wordt automatisch overgezet; ontbreekt het, dan vraagt Home Assistant om een nieuw token.
- *Configureren* en *Opnieuw configureren* gaven een 500-fout als er geen token was opgeslagen.

## [1.0.1] - 2026-11-08
### Gewijzigd
- Voorbeeld-URL's in het configuratiescherm via placeholders (voldoet aan hassfest).

## [1.0.0] - 2026-11-08
### Toegevoegd
- Eerste release: rekeningen, spaarpotjes en abonnementen uit Firefly III als sensoren.
- Installatie en updates via HACS.
