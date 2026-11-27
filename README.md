# Firefly III for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Release](https://img.shields.io/github/v/release/poudenes/FireFly3-integration-Home-assistant)](https://github.com/poudenes/FireFly3-integration-Home-assistant/releases)
[![Validate](https://github.com/poudenes/FireFly3-integration-Home-assistant/actions/workflows/validate.yml/badge.svg)](https://github.com/poudenes/FireFly3-integration-Home-assistant/actions/workflows/validate.yml)

A custom Home Assistant integration that brings your [Firefly III](https://www.firefly-iii.org/) **accounts**,
**piggy banks** and **subscriptions (bills)** into Home Assistant as sensors, so you can build dashboards
and automations around your personal finances.

- Read-only: the integration never changes anything in Firefly III, and it doesn't import individual transactions.
- You choose exactly which accounts, piggy banks and subscriptions become sensors.
- Subscriptions get a monthly status: paid, open, overdue or not due this month.
- Comes with ready-made dashboard cards (see [Dashboard cards](#dashboard-cards)).

> **Note:** sensor names, entity IDs, attribute names and status values are in **Dutch**
> (for example `sensor.rekening_<name>_saldo`). The setup screens are available in English and Dutch.
> See [Sensors](#sensors) for a translation of every name.

## Requirements
- Home Assistant 2024.12 or newer (the integration icon shows from 2026.3).
- A Firefly III server reachable from Home Assistant, with API access.
- A Firefly III **Personal Access Token**.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and add this repository to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=poudenes&repository=FireFly3-integration-Home-assistant&category=integration)

1. In HACS, open ⋮ → **Custom repositories**.
2. Add `https://github.com/poudenes/FireFly3-integration-Home-assistant` with type **Integration**.
3. Search for **Firefly III** in HACS, click **Download** and restart Home Assistant.

New versions then show up as updates in HACS and under **Settings → Updates**.

### Manual
1. Download `firefly3.zip` from the [latest release](https://github.com/poudenes/FireFly3-integration-Home-assistant/releases/latest).
2. Extract it to `/config/custom_components/firefly3/` in Home Assistant.
3. Restart Home Assistant.

## Configuration

### 1. Create a token in Firefly III
In Firefly III, go to **Options → Profile → OAuth → Personal Access Tokens → Create new token**.
Copy the token right away: Firefly III shows it only once.

### 2. Add the integration
Go to **Settings → Devices & services → Add integration** and search for **Firefly III**.

1. Enter the URL of your Firefly III server (for example `http://192.168.1.10:8080` or
   `https://firefly.example.com`, without `/api`) and the token.
   Turn off **Verify SSL certificate** if your server uses a self-signed certificate.
2. Tick the accounts, piggy banks and subscriptions you want in Home Assistant.

### Changing settings later
- **Configure** on the integration: change the selection and the update interval (default 15 minutes).
  Items you untick are removed from Home Assistant automatically.
- When the token expires or is revoked, Home Assistant shows a repair notification asking for a new token.
- To change the URL or the SSL setting, remove the integration and add it again.

## Sensors
Every selected item becomes a device with one or more sensors. Entity IDs follow the pattern
`sensor.<device name>_<sensor name>`, for example `sensor.rekening_checking_saldo`.

| Device | Sensor (English meaning) | Example entity ID |
|---|---|---|
| Firefly III | Totaal saldo (total balance of active accounts that count towards net worth) | `sensor.firefly_iii_totaal_saldo` |
| Rekening *name* (account) | Saldo (balance) | `sensor.rekening_<name>_saldo` |
| Spaarpot *name* (piggy bank) | Gespaard (saved), Doel (target), Nog te sparen (left to save), Voortgang (progress %) | `sensor.spaarpot_<name>_gespaard` |
| Abonnement *name* (subscription) | Status, Verwachte datum (expected date), Betaald op (paid on), Betaald bedrag (amount paid), Verwacht bedrag (expected amount) | `sensor.abonnement_<name>_status` |

### Subscription status values
| State | Meaning |
|---|---|
| `betaald` | Paid this month |
| `open` | Due later this month, not paid yet |
| `te_laat` | Expected date has passed this month, not paid yet (overdue) |
| `niet_deze_maand` | Not due this month |
| `inactief` | Subscription is inactive in Firefly III |

### Useful attributes
| Sensor | Attributes |
|---|---|
| Saldo | `iban`, `rekeningnummer` (account number), `rol` (role), `actief` (active), `telt_mee_in_vermogen` (included in net worth), `saldo_datum` (balance date) |
| Gespaard | `doel` (target), `voortgang` (progress %), `groep` (Firefly III group), `rekeningen` (linked accounts), `startdatum`, `doeldatum` (target date), `actief` |
| Status | `verwachte_datum`, `volgende_verwachte_datum` (next expected date), `betaald_op`, `betaald_bedrag`, `bedrag_min`, `bedrag_max`, `frequentie` (repeat frequency), `groep`, `aantal_betalingen_deze_maand` (payments this month) |

The domain is `firefly3`, deliberately different from Home Assistant's built-in `firefly_iii`
integration, so both can be installed side by side.

## Dashboard cards
Ready-made cards are in the [`examples/`](examples) folder. Most of them need
[button-card](https://github.com/custom-cards/button-card) (install it via HACS → **Frontend**).
The text the cards show is in Dutch and amounts are formatted as euros; both are easy to change in the card code.

The cards find sensors by their entity ID, so don't rename the sensors. Renaming the *devices* is fine:
the cards show the device name.

### 1. Accounts – [`rekeningen-card.yaml`](examples/rekeningen-card.yaml)
- **Shows:** the total balance (red when negative), then every account with its initial, name,
  the last 4 digits of the IBAN and its balance. A bar shows each account's share of the positive total.
- **Reads:** all `sensor.rekening_*_saldo` sensors of this integration and their `iban` attribute.
- **Sorting:** highest balance first. Negative balances are red and have no bar.
- **Setup:** none. New accounts appear automatically.

### 2. Piggy banks per group – [`spaarpotjes-template.yaml`](examples/spaarpotjes-template.yaml) + [`spaarpotjes-card.yaml`](examples/spaarpotjes-card.yaml)
One card you reuse for each piggy bank group in Firefly III. The code lives in a single button-card
template, and each card only sets the group.

- **Shows:** the total saved, "van €… · …%" (of target) with a progress bar towards the combined target, and per
  piggy bank the amount / target with its own bar. Bars turn green at 100%. Piggy banks without a target
  show "geen doel ingesteld" (no target set).
- **Reads:** `sensor.spaarpot_*_gespaard` and the attributes `groep`, `doel` and `voortgang`.
- **Sorting:** highest progress first; piggy banks without a target last.
- **Install:**
  1. Open your dashboard → ✏️ → ⋮ → **Raw configuration editor**.
  2. Paste the `button_card_templates:` block from `spaarpotjes-template.yaml` at the very top, at the same level as `views:`.
  3. Add one card per group, as in `spaarpotjes-card.yaml`.
- **Variables:**

  | Variable | Default | Meaning |
  |---|---|---|
  | `groep` | `Overig` | Group name exactly as in Firefly III (case-sensitive). Piggy banks without a group count as `Overig`. |
  | `toon_voortgang` | `true` | Show a progress bar per piggy bank. |
  | `toon_kop` | `false` | Show a grey line "*group* · N spaarpotjes" above the total. |
  | `niet_in_totaal` | `[]` | Piggy bank names (without the "Spaarpot " prefix) that are listed but left out of the total and target. |

- **Seeing "Geen spaarpotjes gevonden in groep …" (no piggy banks found)?** The group name doesn't match
  exactly, or those piggy banks aren't selected under **Configure**.

### 3. Monthly subscriptions – [`abonnementen-card.yaml`](examples/abonnementen-card.yaml)
- **Shows:** the amount still to pay this month, "€… betaald van €…" (paid of total) with a progress bar,
  and a red badge when something is overdue. Below that, two lists:
  - **Deze maand** (this month): subscriptions that are paid, open or overdue, with a date tile
    (payment date when paid, otherwise the expected date), name, amount and a coloured label.
  - **Later**: subscriptions not due this month (dimmed).
- **Reads:** `sensor.abonnement_*_status` and the attributes `bedrag_min`, `bedrag_max`,
  `betaald_bedrag`, `betaald_op` and `verwachte_datum`. Inactive subscriptions are skipped.
- **Amounts:** the actual amount paid when paid; otherwise the average of the minimum and maximum amount.
- **Colours:** change them in the `stat` block at the top of the code.

### 4. Accounts as a table – [`rekeningen-markdown-card.yaml`](examples/rekeningen-markdown-card.yaml)
- **Shows:** a simple *Account | Balance* table with a total row; negative balances in red.
- **Reads:** the same `sensor.rekening_*_saldo` sensors as card 1, via `integration_entities('firefly3')`.
- **Why use it:** it's a standard Markdown card, so it doesn't need button-card.

## Troubleshooting
- **Cannot connect:** check that Home Assistant can reach the URL, and turn off SSL verification for self-signed certificates.
- **Invalid token:** create a new Personal Access Token in Firefly III.
- **Debug logging:** add this to `configuration.yaml` and restart:
  ```yaml
  logger:
    logs:
      custom_components.firefly3: debug
  ```
- Found a bug? [Open an issue](https://github.com/poudenes/FireFly3-integration-Home-assistant/issues)
  and include your versions and the log lines for `firefly3`.

## Releasing (maintainers)
Versions follow [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`).
1. Bump `version` in `custom_components/firefly3/manifest.json`.
2. Add an entry to `CHANGELOG.md`.
3. Commit and push to `main`.

The **Release** workflow then creates the tag `vX.Y.Z` and a GitHub release with `firefly3.zip`,
which HACS offers as an update. Versions such as `1.2.0b1` are published as pre-releases.

## License
MIT – see [LICENSE](LICENSE).

Firefly III is a project by James Cole; this integration is not affiliated with it.
