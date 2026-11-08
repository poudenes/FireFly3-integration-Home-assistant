# Firefly III voor Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Release](https://img.shields.io/github/v/release/poudenes/FireFly3-integration-Home-assistant)](https://github.com/poudenes/FireFly3-integration-Home-assistant/releases)
[![Validate](https://github.com/poudenes/FireFly3-integration-Home-assistant/actions/workflows/validate.yml/badge.svg)](https://github.com/poudenes/FireFly3-integration-Home-assistant/actions/workflows/validate.yml)

Leest **alleen** rekeningen, spaarpotjes en abonnementen uit Firefly III. Transacties/betalingen worden niet opgehaald.

## Installatie

**Via HACS (aanbevolen)**

[![Open je Home Assistant en voeg deze repository toe aan HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=poudenes&repository=FireFly3-integration-Home-assistant&category=integration)

1. HACS → ⋮ → *Custom repositories*.
2. Repository: `https://github.com/poudenes/FireFly3-integration-Home-assistant`, type *Integration*.
3. Zoek *Firefly III* in HACS, klik *Downloaden* en herstart Home Assistant.

Nieuwe versies verschijnen daarna vanzelf als update in HACS (en onder *Instellingen → Updates*).

**Handmatig**
1. Download `firefly3.zip` van de [laatste release](https://github.com/poudenes/FireFly3-integration-Home-assistant/releases/latest).
2. Pak uit naar `/config/custom_components/firefly3` in Home Assistant.
3. Herstart Home Assistant.

## Token maken in Firefly III
Firefly III → **Opties → Profiel → OAuth → Personal Access Tokens → Nieuw token aanmaken**.
Kopieer het token meteen; Firefly laat het maar één keer zien.

## Toevoegen
**Instellingen → Apparaten & diensten → Integratie toevoegen → "Firefly III"**
1. Vul de URL in (bijv. `http://192.168.1.10:8080`) en het token.
2. Na een geslaagde verbinding kies je welke rekeningen, spaarpotjes en abonnementen je wilt.

## Achteraf aanpassen
- **Configureren**: selectie van rekeningen / spaarpotjes / abonnementen en het update-interval.
  Niet meer geselecteerde items worden automatisch uit Home Assistant verwijderd.
- **⋮ → Opnieuw configureren**: URL, token of SSL-controle wijzigen.
- Is het token verlopen, dan vraagt Home Assistant zelf om een nieuw token.

## Sensoren
| Apparaat | Sensoren | Voorbeeld entity_id |
|---|---|---|
| Firefly III | Totaal saldo | `sensor.firefly_iii_totaal_saldo` |
| Rekening *naam* | Saldo (attributen: `iban`, `rol`, …) | `sensor.rekening_<naam>_saldo` |
| Spaarpot *naam* | Gespaard (attributen: `doel`, `voortgang`, `groep`, …), Doel, Nog te sparen, Voortgang | `sensor.spaarpot_<naam>_gespaard` |
| Abonnement *naam* | Status (`betaald`, `open`, `te_laat`, `niet_deze_maand`, `inactief`), Verwachte datum, Betaald op, Betaald bedrag, Verwacht bedrag | `sensor.abonnement_<naam>_status` |

Domein: `firefly3` – bewust anders dan de ingebouwde `firefly_iii`-integratie van Home Assistant, zodat ze niet botsen.

## Nieuwe versie uitbrengen
Versienummering volgt [SemVer](https://semver.org/lang/nl/) (`MAJOR.MINOR.PATCH`).
1. Verhoog `version` in `custom_components/firefly3/manifest.json` (bijv. `1.0.0` → `1.0.1`).
2. Vul `CHANGELOG.md` aan.
3. Commit en push naar `main`.

De *Release*-workflow maakt dan automatisch tag `v1.0.1` en een GitHub-release met `firefly3.zip`;
HACS biedt die versie vervolgens aan als update. Een versie als `1.1.0b1` wordt als pre-release gepubliceerd.

## Licentie
MIT – zie [LICENSE](LICENSE).
