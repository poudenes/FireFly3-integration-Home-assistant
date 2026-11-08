# Changelog

Alle noemenswaardige wijzigingen worden hier bijgehouden.
Versienummering volgt [Semantic Versioning](https://semver.org/lang/nl/): `MAJOR.MINOR.PATCH`.

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
