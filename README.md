# Firefly III voor Home Assistant

Leest **alleen** rekeningen, spaarpotjes en abonnementen uit Firefly III. Transacties/betalingen worden niet opgehaald.

## Installatie

**Handmatig**
1. Kopieer de map `custom_components/firefly3` naar `/config/custom_components/firefly3` in Home Assistant
   (bijv. via de *File editor*, *Samba* of *SSH* add-on).
2. Herstart Home Assistant.

**Via HACS (custom repository)**
1. Zet deze map in een eigen GitHub-repository.
2. HACS → ⋮ → *Custom repositories* → URL van je repo, type *Integration*.
3. Installeer en herstart Home Assistant.

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
| Soort | Sensoren |
|---|---|
| Rekening | Saldo (attributen: IBAN, rol, type, …) |
| Spaarpotje | Huidig bedrag, Doelbedrag, Nog te sparen, Voortgang (%), Streefdatum |
| Abonnement | Bedrag (gemiddelde van min/max), Volgende betaling (datum) |

Domein: `firefly3` – bewust anders dan de ingebouwde `firefly_iii`-integratie van Home Assistant, zodat ze niet botsen.
