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
**Instellingen → Apparaten & diensten → Integratie toevoegen → "Firefly III Overzicht"**
1. Vul de URL in (bijv. `http://192.168.1.10:8080`) en het token.
2. Na een geslaagde verbinding kies je welke rekeningen, spaarpotjes en abonnementen je wilt.

## Achteraf aanpassen
- **Configureren**: selectie van rekeningen / spaarpotjes / abonnementen en het update-interval.
  Niet meer geselecteerde items worden automatisch uit Home Assistant verwijderd.
- URL of SSL-controle wijzigen: verwijder de integratie en voeg hem opnieuw toe.
- Is het token verlopen, dan vraagt Home Assistant zelf om een nieuw token.

## Sensoren
| Apparaat | Sensoren | Voorbeeld entity_id |
|---|---|---|
| Firefly III | Totaal saldo | `sensor.firefly_iii_totaal_saldo` |
| Rekening *naam* | Saldo (attributen: `iban`, `rol`, …) | `sensor.rekening_<naam>_saldo` |
| Spaarpot *naam* | Gespaard (attributen: `doel`, `voortgang`, `groep`, …), Doel, Nog te sparen, Voortgang | `sensor.spaarpot_<naam>_gespaard` |
| Abonnement *naam* | Status (`betaald`, `open`, `te_laat`, `niet_deze_maand`, `inactief`), Verwachte datum, Betaald op, Betaald bedrag, Verwacht bedrag | `sensor.abonnement_<naam>_status` |

Domein: `firefly3` – bewust anders dan de ingebouwde `firefly_iii`-integratie van Home Assistant, zodat ze niet botsen.

## Dashboard-cards
Kant-en-klare cards staan in de map [`examples/`](examples). De meeste gebruiken
[custom:button-card](https://github.com/custom-cards/button-card) (installeren via HACS → *Frontend*).
De cards zoeken de sensoren op basis van hun `entity_id`. Hernoem je een sensor, dan houdt de card er dus mee op;
hernoemen van het *apparaat* mag wel (die naam wordt getoond).

### 1. Rekeningen – [`rekeningen-card.yaml`](examples/rekeningen-card.yaml)
- **Toont:** het totaalsaldo bovenaan (rood als het negatief is), daaronder elke rekening met een
  rondje met de beginletter, de naam, de laatste 4 cijfers van de IBAN en het saldo.
  Een balkje laat zien welk deel van het (positieve) totaal op die rekening staat.
- **Leest:** alle `sensor.rekening_*_saldo` van deze integratie, plus het attribuut `iban`.
- **Sortering:** hoogste saldo bovenaan. Negatieve saldi zijn rood en hebben geen balkje.
- **Instellen:** niets; nieuwe rekeningen verschijnen vanzelf.

### 2. Spaarpotjes per groep – [`spaarpotjes-template.yaml`](examples/spaarpotjes-template.yaml) + [`spaarpotjes-card.yaml`](examples/spaarpotjes-card.yaml)
Eén card die je per Firefly III-groep hergebruikt (bijv. *Vaste lasten*, *Jaarlijkse kosten 2026*, *Sparen inboedel*).
Omdat alleen de groep verschilt, staat de code één keer in een sjabloon.

- **Toont:** het totaal gespaard, "van €… · …%" met een voortgangsbalk naar het totale doel, en per spaarpotje
  het bedrag / doel met een eigen balk. Op of boven 100% wordt de balk groen; zonder doel staat er
  "geen doel ingesteld".
- **Leest:** `sensor.spaarpot_*_gespaard` met de attributen `groep`, `doel` en `voortgang`.
- **Sortering:** hoogste voortgang bovenaan; spaarpotjes zonder doel onderaan.
- **Installeren:**
  1. Open het dashboard → ✏️ → ⋮ → *Ruwe configuratie-editor*.
  2. Plak het blok `button_card_templates:` uit `spaarpotjes-template.yaml` helemaal bovenaan, op hetzelfde niveau als `views:`.
  3. Voeg per groep een card toe zoals in `spaarpotjes-card.yaml`.
- **Variabelen:**

  | Variabele | Standaard | Betekenis |
  |---|---|---|
  | `groep` | `Overig` | Groepsnaam precies zoals in Firefly III (hoofdlettergevoelig). Spaarpotjes zonder groep vallen onder `Overig`. |
  | `toon_voortgang` | `true` | Voortgangsbalk per spaarpotje tonen. |
  | `toon_kop` | `false` | Grijze regel "*groep* · N spaarpotjes" boven het totaal. |
  | `niet_in_totaal` | `[]` | Spaarpotjes (naam zonder "Spaarpot ") die wel getoond worden maar niet meetellen in totaal en doel, bijv. `Boodschappen`. |

- **Zie je "Geen spaarpotjes gevonden in groep …"?** Dan klopt de groepsnaam niet precies, of die spaarpotjes
  zijn niet aangevinkt bij *Configureren* van de integratie.

### 3. Maandelijkse uitgaven – [`abonnementen-card.yaml`](examples/abonnementen-card.yaml)
- **Toont:** bovenaan het bedrag dat deze maand nog betaald moet worden, "€… betaald van €…" met een groene balk,
  en een rode badge als er iets te laat is. Daaronder twee lijsten:
  - **Deze maand:** abonnementen met status *Betaald*, *Open* of *Te laat*, met een datumblokje
    (betaaldatum als het betaald is, anders de verwachte datum), naam, bedrag en een gekleurd label.
  - **Later:** abonnementen die deze maand niet aan de beurt zijn (gedimd).
- **Leest:** `sensor.abonnement_*_status` (`betaald`, `open`, `te_laat`, `niet_deze_maand`) en de attributen
  `bedrag_min`, `bedrag_max`, `betaald_bedrag`, `betaald_op` en `verwachte_datum`.
  Inactieve abonnementen worden overgeslagen.
- **Bedragen:** bij *Betaald* het echt betaalde bedrag; anders het gemiddelde van min en max.
- **Kleuren aanpassen:** in het blok `stat` bovenin de code (nu: betaald groen, open rood, te laat blauw).

### 4. Rekeningen als tabel – [`rekeningen-markdown-card.yaml`](examples/rekeningen-markdown-card.yaml)
- **Toont:** een eenvoudige tabel *Rekening | Saldo* met een totaalregel; negatieve saldi in rood.
- **Leest:** dezelfde `sensor.rekening_*_saldo` als card 1, via `integration_entities('firefly3')`.
- **Verschil met card 1:** standaard Markdown-card, dus geen button-card nodig. Handig voor een paneelweergave of
  als button-card (nog) niet geïnstalleerd is.


## Nieuwe versie uitbrengen
Versienummering volgt [SemVer](https://semver.org/lang/nl/) (`MAJOR.MINOR.PATCH`).
1. Verhoog `version` in `custom_components/firefly3/manifest.json` (bijv. `1.0.0` → `1.0.1`).
2. Vul `CHANGELOG.md` aan.
3. Commit en push naar `main`.

De *Release*-workflow maakt dan automatisch tag `v1.0.1` en een GitHub-release met `firefly3.zip`;
HACS biedt die versie vervolgens aan als update. Een versie als `1.1.0b1` wordt als pre-release gepubliceerd.

## Licentie
MIT – zie [LICENSE](LICENSE).
