# Entity Management

Guide to creating, querying, and updating legal entities, including VAT registration management.

---

## Overview

A **legal entity** represents a distinct legal business unit within your organization. Each entity has its own:
- Chart of accounts
- Tax registrations
- Fiscal periods
- Transactions (filtered by `legal_entity_id` dimension column)
- Agent email addresses — 4 inboxes (`bills.*`, `invoices.*`, `payments.*`, `receipts.*`), but only `bills.*` and `receipts.*` have autonomous agents (`invoices.*`/`payments.*` are outbound/manual utility addresses)

---

## Available Tools

### Read Operations

| Tool | Purpose | Example |
|------|---------|---------|
| `query("legal_entity")` | List all entities | `query("legal_entity")` |
| `get_entity("legal_entity", id=X)` | Get entity details | `get_entity("legal_entity", id=13)` |
| `query("legal_entity", query="...")` | Search entities by name/code | `query("legal_entity", query="US")` |

### Write Operations

| Tool | Purpose |
|------|---------|
| `submit("legal_entity", "update", data)` | Update safe scalar fields on an existing entity |
| `manage_onboarding(action="start", ...)` | Create the FIRST legal entity in an organization (via onboarding wave 1) |
| `manage_onboarding(action="add_entity", ...)` | Create a 2nd+ legal entity in an already-onboarded organization |

> **NEVER call `submit("legal_entity", "create", ...)`** — that executor does not exist. Legal entities are created by the onboarding flow, not by `submit()`.

---

## Creating a Legal Entity

Admin `/entities/create` provides assistant setup instructions; its legacy direct
creation endpoint rejects writes. Creation happens via the onboarding tool, never via `submit()`. The entity is created atomically with full infrastructure (chart of accounts, fiscal periods, tax codes, payment terms, GL posting profiles, number series, agent emails, agent definitions, and optional VAT registration).

### First entity in a new organization

```
manage_onboarding(action="start",
    country_code="US",
    accounting_standard="us_gaap_standard",
    tax_jurisdiction="us_sales_tax",
    fiscal_year_start_month=1
)
# Then run waves until complete:
manage_onboarding(action="run_wave")  # repeat until progress_pct == 100
```

Wave 1's `create_legal_entity` task auto-derives the entity from the organization record:
- `entity_name` ← `organizations.name`
- `entity_code` ← `country_code` (e.g., `US`)
- `functional_currency` ← country lookup (US→USD, EE→EUR, GB→GBP, …)

See [procedures/onboarding.md](../procedures/onboarding.md) for the full procedure.

### Additional entities in an onboarded organization

```
manage_onboarding(action="add_entity",
    entity_name="Acme Corp UK",
    entity_code="ACME-UK",
    country_code="GB",
    base_currency="GBP",
    is_vat_registered=true,
    tax_id="GB123456789"
)
```

Collect ALL fields (including `is_vat_registered` + `tax_id`) BEFORE calling `add_entity`. There is no post-hoc path to flip the VAT flag through `legal_entity.update` — VAT lives in `entity_tax_registrations`.

---

## Update Legal Entity

Updates a tightly scoped set of safe fields on a legal entity. Structural fields (entity_code, currency, entity_type, accounting_standard) are intentionally not updatable.

### Parameters (passed in `data`)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entity_id` (or `legal_entity_id`) | int | Yes (or use `lookup_entity_code`) | Entity to update |
| `lookup_entity_code` | str | Alt to entity_id | Find entity by entity_code |
| `entity_name` | str | No | Display name |
| `tax_id` | str | No | VAT / tax identification number (max 50). EE: KMKR. Distinct from `register_id`. |
| `register_id` | str | No | Business/commercial registry number (max 50). EE: äriregistri kood; CZ: IČ; PL: KRS. Distinct from `tax_id` (VAT). |
| `country_code` | str | No | ISO 2-letter code |
| `address_line_1` | str | No | Registered street address (max 255). Added in mig 409. |
| `address_line_2` | str | No | Apt / suite / building (max 255, optional). |
| `city` | str | No | Registered city (max 100). |
| `state_province` | str | No | State / province / region (max 100, optional). |
| `postal_code` | str | No | Postal code / ZIP (max 50). |
| `address` | str (JSON) or object | No | **DEPRECATED** — legacy JSONB. Kept for transition; prefer the structured columns above. |
| `is_active` | bool | No | Activate/deactivate entity |
| `metadata` | object | No | Arbitrary JSONB metadata |

At least one updatable field must be provided. If none are, the call is a no-op.

### Example

```
submit("legal_entity", "update", {
    "entity_id": 13,
    "entity_name": "Acme Corporation USA",
    "tax_id": "12-3456789"
})
```

Response:

```json
{
    "entity_id": 13,
    "entity_code": "ACME-US",
    "entity_name": "Acme Corporation USA",
    "updated_fields": ["entity_name", "tax_id"],
    "message": "Legal entity 13 updated."
}
```

### More Examples

```
# Update registered address (structured columns from mig 409 — preferred)
submit("legal_entity", "update", {
    "entity_id": 13,
    "address_line_1": "123 Main St",
    "city": "Dublin",
    "state_province": "Leinster",
    "postal_code": "D02",
    "country_code": "IE"
})

# Deactivate entity
submit("legal_entity", "update", {"entity_id": 13, "is_active": false})

# Reactivate
submit("legal_entity", "update", {"entity_id": 13, "is_active": true})
```

### NOT Updatable Fields

These fields are intentionally blocked because changing them would invalidate existing data:

| Field | Reason |
|-------|--------|
| `entity_code` | Referenced by agent emails, number series, reports |
| `functional_currency` | All transaction amounts already stored in this currency |
| `reporting_currency` | Consolidation reports depend on this |
| `entity_type` | Structural classification for reporting hierarchy |
| `accounting_standard` | Chart of accounts structure depends on this |
| `fiscal_year_start_month` | Fiscal periods already generated for the FY |
| `is_vat_registered` | Does NOT exist on `legal_entities` — VAT lives in `entity_tax_registrations` (see below) |

If any of these truly need to change, the correct move is to deactivate the entity and create a replacement via `add_entity`, not to mutate the existing record.

---

## VAT Registration

### How It Works

VAT registration is stored in `entity_tax_registrations` with `registration_type = 'vat'`. Manage it via the `tax_registration` workflows — NOT via `legal_entity.update`.

**Enable VAT (new or reactivate):**

```
submit("tax_registration", "create", {
    "legal_entity_id": 13,
    "registration_type": "vat",
    "registration_number": "EE101980223",
    "effective_from": "2026-04-01"
})
```

**Disable VAT:** update the active registration row to `is_active=false` with `effective_to=CURRENT_DATE`:

```
submit("tax_registration", "update", {
    "registration_id": <id>,
    "is_active": false,
    "effective_to": "2026-04-24"
})
```

**Create VAT at entity-creation time** (preferred — avoids a two-step flow):

```
manage_onboarding(action="add_entity",
    entity_name="Acme UK Ltd",
    entity_code="ACME-UK",
    country_code="GB",
    base_currency="GBP",
    is_vat_registered=true,
    tax_id="GB123456789"
)
```

`add_entity` inserts the `entity_tax_registrations` row automatically when `is_vat_registered=true`.

### Impact on Transactions

| Transaction Type | Non-VAT Behavior |
|-----------------|-----------------|
| AP Invoice | Tax rolled into expense GL line |
| AR Invoice | Tax posting skipped entirely |
| Journal Entry | Tax rolled into original GL line |

**Reverse charge tax codes are blocked** for non-VAT entities.

The check uses the **transaction date** -- backdated entries respect historical VAT status.

---

## Entity Properties Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

### Core Fields

| Field | Description | Updatable? | Example |
|-------|-------------|------------|---------|
| `entity_name` | Display name | Yes | "Acme Corp USA" |
| `entity_code` | Short identifier | **No** | "ACME-US" |
| `functional_currency` | Transaction currency | **No** | "USD" |
| `reporting_currency` | Reporting currency | **No** | "EUR" |
| `country_code` | ISO country | Yes | "US" |
| `tax_id` | Tax / VAT number | Yes | "12-3456789" |
| `register_id` | Business register / KMK code | Yes | "17266831" |
| `entity_type` | Type classification | **No** | "subsidiary" |
| `accounting_standard` | Accounting standard | **No** | "IFRS", "US_GAAP", "LOCAL" |
| `fiscal_year_start_month` | Month fiscal year begins (1-12) | **No** | 1 (January) |
| `address_line_1` | Registered street address (mig 409) | Yes | "Rankestraße 8" |
| `address_line_2` | Apt / suite / building (mig 409) | Yes | "Suite 200" |
| `city` | Registered city (mig 409) | Yes | "Tallinn" |
| `state_province` | State / province / region (mig 409) | Yes | "Harju" |
| `postal_code` | Postal code / ZIP (mig 409) | Yes | "10101" |
| `address` | **DEPRECATED** legacy JSONB | Yes (transition) | superseded by structured columns above |
| `is_active` | Active status | Yes | true |

VAT registration is not a column on `legal_entities` — it lives in `entity_tax_registrations`. See the VAT Registration section above.

Fields marked **No** are structural -- changing them would invalidate existing transaction data, account structures, or reporting.

### Entity Types

| Type | Description |
|------|-------------|
| `subsidiary` | Separate legal entity owned by parent |
| `division` | Operational unit within entity |
| `branch` | Geographic location of entity |
| `consolidation` | Reporting-only entity for consolidation |

### Accounting Standards

| Standard | Description |
|----------|-------------|
| `GAAP` | US Generally Accepted Accounting Principles |
| `IFRS` | International Financial Reporting Standards |
| `LOCAL` | Local accounting standard (country-specific) |
| `CUSTOM` | Custom chart of accounts (user-imported) |

### Agent Email Addresses

Each entity gets 4 dedicated email addresses. Only two have autonomous agents behind them:

| Email | Agent | Purpose |
|-------|-------|---------|
| `bills.{entity}.{org-slug}@mail.arfiti.com` | `bill_processor` | Inbound vendor bills → AP invoices |
| `receipts.{entity}.{org-slug}@mail.arfiti.com` | `expense_processor` | Inbound expense receipts |
| `invoices.{entity}.{org-slug}@mail.arfiti.com` | *(none — manual)* | Outbound AR invoice sending / manual inbox |
| `payments.{entity}.{org-slug}@mail.arfiti.com` | *(none — manual)* | Manual inbox for remittance advices |

When presenting emails to the user after onboarding, list ONLY `bills.*` and `receipts.*` — the other two are utility addresses without autonomous processing and confuse users when framed as "agent emails."

Use `query("entity_email", filters={"legal_entity_id": X, "default_agent_type": "bills"})` to get the actual email address for a specific entity.

---

## Entity Lifecycle

```
Created (via dashboard/MCP/onboarding)
    |
Active (is_active=true)
    | Toggle VAT if needed
    | Update name/address/tax_id
    |
Inactive (is_active=false, via submit("legal_entity", "update", {"entity_id": X, "is_active": false}))
    | Can be reactivated
    |
Active (reactivated)
```

Entities are never hard-deleted -- they are deactivated. Inactive entities:
- Are hidden from entity list by default (unless "Show inactive" is toggled)
- Cannot have new transactions posted
- Remain visible in historical reports

---

## Common Workflows

### Rename an Entity

```
submit("legal_entity", "update", {
    "entity_id": 13,
    "entity_name": "New Company Name LLC"
})
```

### Register for VAT

Use `tax_registration.create` — NOT `legal_entity.update`. Set the legal entity's `tax_id` first (if it isn't already), then create the VAT registration:

```
# 1. Set tax_id on the entity
submit("legal_entity", "update", {
    "entity_id": 13,
    "tax_id": "IE1234567T"
})

# 2. Create the VAT registration
submit("tax_registration", "create", {
    "legal_entity_id": 13,
    "registration_type": "vat",
    "registration_number": "IE1234567T",
    "effective_from": "2026-04-01"
})
```

### Update Business Address

Use the structured columns from migration 409 — the legacy `address` JSONB is deprecated for new writes:

```
submit("legal_entity", "update", {
    "entity_id": 13,
    "address_line_1": "456 Business Ave",
    "city": "San Francisco",
    "state_province": "CA",
    "postal_code": "94102",
    "country_code": "US"
})
```

### Set Non-Calendar Fiscal Year

`fiscal_year_start_month` cannot be changed on an existing entity — fiscal periods are already generated. If it's genuinely wrong (e.g., set during onboarding with the wrong value), the fix is to deactivate the entity and create a new one with `add_entity` + `fiscal_year_start_month=X`.

### Deactivate and Reactivate

```
# Deactivate
submit("legal_entity", "update", {"entity_id": 13, "is_active": false})

# Reactivate later
submit("legal_entity", "update", {"entity_id": 13, "is_active": true})
```

---

## Database Schema

### legal_entities

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `organization_id` | integer | FK to system.organizations |
| `entity_name` | varchar(255) | Display name |
| `entity_code` | varchar(20) | Short identifier |
| `functional_currency` | varchar(3) | ISO currency code |
| `reporting_currency` | varchar(3) | Reporting currency |
| `country_code` | varchar(2) | ISO country code |
| `state_code` | varchar(50) | State/region code (subnational) |
| `tax_id` | varchar(50) | Tax / VAT identification number |
| `register_id` | varchar(50) | Business register / KMK code (mig 324) |
| `entity_type` | varchar(50) | subsidiary/division/branch/consolidation |
| `accounting_standard` | varchar(20) | GAAP/IFRS/LOCAL/CUSTOM |
| `fiscal_year_start_month` | integer | Month fiscal year begins (1-12) |
| `address_line_1` | varchar(255) | Registered street address (mig 409) |
| `address_line_2` | varchar(255) | Apt / suite / building (mig 409) |
| `city` | varchar(100) | Registered city (mig 409) |
| `state_province` | varchar(100) | State / province / region (mig 409) |
| `postal_code` | varchar(50) | Postal code / ZIP (mig 409) |
| `address` | jsonb | **DEPRECATED** legacy JSONB blob, superseded by the structured columns above. Readers fall back to it only when structured columns are NULL. |
| `is_active` | boolean | Active status |
| `created_at` | timestamp | Creation time |
| `updated_at` | timestamp | Last update time |

### entity_tax_registrations (VAT records)

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `legal_entity_id` | integer | FK to legal_entities |
| `tax_authority_id` | integer | FK to master_tax_authorities |
| `registration_number` | varchar(100) | Tax registration number (NOT NULL) |
| `registration_type` | varchar(50) | 'vat', 'sales_tax', etc. |
| `effective_from` | date | Registration start date |
| `effective_to` | date | Registration end date (NULL = active) |
| `is_active` | boolean | Active status |

**UNIQUE constraint:** `(legal_entity_id, tax_authority_id, registration_number)`

---

**Version**: 2.2
**Last Updated**: 2026-05-15
**Related Resources**: [Tax Management](tax-management.md), [Accounts](accounts-management.md), [Onboarding Procedure](../procedures/onboarding.md)

**Changelog**
- v2.2 — Added structured address columns (`address_line_1/2`, `city`, `state_province`, `postal_code`) from migration 409. Legacy `address` JSONB column deprecated; readers fall back to it only when structured columns are NULL.

## Reporting business date

`submit("legal_entity", "update", data={"legal_entity_id": ENTITY_ID, "reporting_timezone": "Europe/Tallinn"})`
confirms an IANA reporting timezone through the normal workflow. Onboarding and
cloning receive a DB default from a valid organisation timezone or country, falling
back to UTC where no country mapping exists. Country defaults are provisional,
especially where more than one timezone is used. Existing missing
settings are backfilled and marked for review. Reports disclose a default/fallback
as a warning and return the business date used. Confirm the correct entity timezone
before relying on date-sensitive cutoffs; a country default is not confirmation.


### Standard manual-journal policy

Migration 738 and matching PR328 application setup are deployed and verified.
Company/legal-entity creation can resume. Newly created entities initialize
restrictions automatically. The
creation transaction records an immutable `new_entity_default_v1` receipt;
there is no per-customer activation task or caller opt-out for new entities.
Standard IFRS/US GAAP chart creation disables manual entries on AP/AR control
accounts and headers, while keeping eligible ordinary leaf accounts available.
Invoices, payments and supported adjustments use their typed workflows.

Existing entities and shared account settings are preserved. A new entity in
an existing organization inherits its effective account configuration; this
does not silently repair that organization's existing chart. Custom charts
need explicit control-account flags and posting-profile setup before use.
Missing or invalid manual-account setup blocks posting instead of bypassing
the policy. Existing clients use a separately reviewed transition. This
changes permissions, not balances, report decisions or aging membership.


## Close evidence update (b1, awaiting deployment)

Close filing candidates come from an entity’s country or a registration linked to the form’s authority whose dates overlap the period. A current inactive flag with a recorded end date is evaluated historically; inactive without an end date is uncertain. Missing country/registration or missing applicability configuration is “not determined”, never proof that no return is required.
