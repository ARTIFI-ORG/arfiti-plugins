# Fixed Assets Management Guide

Expense capitalization validates reporting-currency balance before committing.
If independently rounded source lines do not equal the converted total, the
operation refuses with a rounding-allocation explanation and rolls back all
capitalization writes. It does not silently distribute the difference or choose
an accountant's rounding policy. A reporting-currency rounding allocation is not
implemented by this correction.

AR-548 correction (merged in PR #467, 28 October 2026): acquire-from-bill records initial cost,
zero accumulated depreciation and equal net book value for its new book.
Lifecycle posting can insert a missing legacy value row using the stored book's
asset/entity identity. This retains disposal-before-depreciation history; it does
not bulk-repair previously disposed assets. Historical repairs remain separate.


## Dimension selection (branch implementation)

The branch implementation (migration 642; not deployed) selects assets by their
current recorded dimension assignments as of the entity business date. This is
explicitly disclosed even when the valuation date is historical; it does not
reconstruct past departmental ownership. Existing book, currency and historical
valuation limitations remain. Invalid assignment identity is an evidence gap, not
an untagged asset. Totals cover the full selected register, including paging.

## Custom Fields

Organisations define their own fixed asset fields. Before putting a business fact
into `metadata`, check `get_submissions(action="schema", object_type="fixed_asset", operation="create")`
→ `custom_fields` (key, type, limits, options, required). Set values with
`"custom_fields": {"key": value}`; on update keys you leave out are unchanged
and `"custom_fields_clear": ["key"]` empties one; never send `null`. Decimals
as numeric strings, dates `YYYY-MM-DD`, choice = one option `value`. Filter
with `query("fixed_asset", filters={"custom_fields.<key>": value}). An update names the asset's `legal_entity_id`.
All rules (register, types, required fields, transactions, filters, import, merge): the custom-fields resource; full contract `docs/GUIDES/GUIDE_CUSTOM_FIELDS.md`.

## Report correctness contract (migration 630)

The shared asset register (migration 630) returns server totals and paged rows from a retained snapshot. Held, draft, disposed and unknown assets are counted separately. Historical valuation without reconstructable book history is null; do not substitute current values. Book/currency mismatches and conflicting disposal history are explicit gaps. Combined depreciation/impairment does not support a separate impairment figure or certified GL tie-out.

Requires the matching migration/server release; code availability is not deployment evidence.

This guide explains how to manage fixed assets in the AI-Native ERP system.

---

## Overview

Fixed assets are long-term tangible assets used in business operations (equipment, vehicles, buildings). The workflow system ensures proper authorization, audit trails, and GL posting for all asset operations.

**What you can do:**
- Create asset categories with depreciation defaults
- Create and update asset records and their depreciation books
- Acquire assets from bills, journal entries, or any transaction type
- Capitalize expenses and construction-in-progress (CWiP)
- Transfer assets between departments/locations
- Record impairment and dispose of assets
- Run monthly depreciation with GL posting

**Available Workflows:**

| Category | Workflows | Purpose |
|----------|-----------|---------|
| Category Management | `fixed_asset_category.create` (fields: `get_submissions(action="schema", object_type, operation)`), `fixed_asset_category.update` (fields: `get_submissions(action="schema", object_type, operation)`) | Set up asset types with defaults |
| Asset Lifecycle | `fixed_asset.create` (fields: `get_submissions(action="schema", object_type, operation)`), `fixed_asset.update` (fields: `get_submissions(action="schema", object_type, operation)`), `fixed_asset.attach` (fields: `get_submissions(action="schema", object_type, operation)`) | Create and maintain asset records |
| Acquisition | `fixed_asset.acquire_from_bill` (fields: `get_submissions(action="schema", object_type, operation)`), `fixed_asset.capitalize_expense` (fields: `get_submissions(action="schema", object_type, operation)`), `fixed_asset.capitalize_cwip` (fields: `get_submissions(action="schema", object_type, operation)`) | Link assets to source transactions |
| Operations | `fixed_asset.transfer` (fields: `get_submissions(action="schema", object_type, operation)`), `fixed_asset.impair` (fields: `get_submissions(action="schema", object_type, operation)`), `fixed_asset.dispose` (fields: `get_submissions(action="schema", object_type, operation)`) | Transfer, impair, or dispose assets |
| Depreciation | `fixed_asset_depreciation.schedule` (fields: `get_submissions(action="schema", object_type, operation)`), `fixed_asset_depreciation.process` (fields: `get_submissions(action="schema", object_type, operation)`) | Run monthly depreciation |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow above, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

---

## Available Query Tools

| Tool | Purpose |
|------|---------|
| `get_entity("fixed_asset", id=X)` | Get single asset (includes dimensions, book values, events, attachments) |
| `query("fixed_asset", filters)` | List assets with filters and pagination |
| `query("fixed_asset", query, filters)` | Search assets by name, number, serial number |
| `query("fixed_asset", filters, limit=1)` | Count matching assets (use `total_count` from response) |
| `get_entity("fixed_asset_category", id=X)` | Get single category |
| `query("fixed_asset_category", filters)` | List categories |
| `query("fixed_asset_category", query)` | Search categories |
| `query("fixed_asset", group_by, aggregates, filters)` | Aggregate assets (e.g., total cost by category, status) |
| `query(entity_type, filters={...})` ×N | Fetch reference data (issue the calls in parallel) (categories, accounts, etc.) |
| `query("asset_acquisition_line", filters={"legal_entity_id": X})` | List bills with asset-account lines available for asset acquisition (requires fixed-asset categories with `gl_cost_account` configured — see below) — replaces `list_available_bills_for_asset_acquisition` (MCP registration removed); for a minimum-amount filter, use a range operator: `filters={"legal_entity_id": X, "available_amount": {"gte": 500}}` |
| `generate_report("fa_gl_reconciliation", {"legal_entity_id": X})` | Reconcile fixed asset register totals to GL account balances (current balances only — no `as_of_date` param) — replaces `reconcile_fixed_assets_to_gl` (MCP registration removed) |
| `generate_report("unposted_depreciation", {"fiscal_period_id": X, "legal_entity_id": X})` | Preview what a depreciation run would produce for a fiscal period without executing — replaces `preview_depreciation_run` (MCP registration removed). Without `book_code` it previews the ledger-posting book; `period_info.book_code` says which |

**Virtual fields (resolved inline — no extra lookups needed):**
- `category_name` — category name resolved from `category_master_id`

**Key notes:**
- `get_entity` defaults to `include_related=True` — returns dimensions, book values, events, and attachments automatically. Pass `include_related=False` to skip if you only need the asset record.
- Search/list results include: `id`, `asset_number`, `name`, `status`, `category_master_id`, `category_name`, `original_cost`, `depreciation_method`, `acquisition_date`, `location`

### Reconciliation & Analysis Tools

**List bills available for asset acquisition:**
```javascript
query("asset_acquisition_line", filters={"legal_entity_id": 13})
```
Returns bills with transaction lines posted to asset GL accounts that have not yet been linked to a fixed asset record. Use this before running `fixed_asset.acquire_from_bill` to find eligible source transactions.

> **Requires fixed-asset categories configured with `gl_cost_account`.** Asset-cost lines are classified by matching the transaction line's GL account against `master_fixed_asset_categories.gl_cost_account` — there is no hardcoded account-number range. If an org hasn't created any fixed-asset categories yet (or a category is missing `gl_cost_account`), this returns zero rows even if asset-looking bills exist — that's correct behavior, not a bug: nothing is acquirable until a category maps to that account. Run `fixed_asset_category.create` (or set `override_gl_cost_account` per entity) first.

**Reconcile fixed assets to GL:**
```javascript
generate_report("fa_gl_reconciliation", {"legal_entity_id": 13})
```
Compares the fixed asset register (original cost, accumulated depreciation) against GL account balances for asset and accumulated depreciation accounts. Reports any discrepancies between the subledger and general ledger.

> **Always reflects current balances — there is no `as_of_date` parameter.** The underlying reconciliation view has no date dimension, so a historical "as of" reconciliation isn't possible; passing `as_of_date` errors. The response includes `balances_as_of: "current"`. For period-specific investigation, drill into the flagged accounts with `query("transaction", filters={...})` filtered by `date_filters` instead.

**Preview depreciation run:**
```javascript
generate_report("unposted_depreciation", {"fiscal_period_id": 211, "legal_entity_id": 13, "book_code": "GAAP"})
```
Calculates what a depreciation run would produce for all active assets in the given fiscal period without actually executing or posting any entries. Returns per-asset depreciation amounts, accounts, and totals (including catch-up detection for assets with multiple unposted periods). Use this to review before running `fixed_asset_depreciation.schedule` and `fixed_asset_depreciation.process`.

---

## Creating Asset Categories

Use the `fixed_asset_category.create` workflow to set up asset types.

**See:** fixed_asset_category.create definition (fields: `get_submissions(action="schema", object_type, operation)`) for complete field details

### Basic Category

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="fixed_asset_category", operation="create")

// Step 2: Submit with discovered fields
submit("fixed_asset_category", "create", {
  "category_code": "COMPUTER",
  "name": "Computer Equipment",
  "description": "Desktop computers, laptops, tablets",
  "default_depreciation_method": "straight_line",
  "default_useful_life_months": 36,
  "default_salvage_value_pct": 0,
  "default_gl_cost_account": "1500",
  "default_gl_accum_depr_account": "1510",
  "default_gl_expense_account": "6400"
})
// Tip: Use validate_only=true to check payload before submitting
```

**Reference Lists:**
- Chart of Accounts (look up with `query(entity_type="account")`) - Valid GL account numbers
- Depreciation Methods (look up with `get_submissions(action="schema", object_type="fixed_asset_category", operation="create")`) - Available methods

### Entity-Specific Override

Override category settings for a specific legal entity:

```json
{
  "category_code": "VEHICLE",
  "legal_entity_id": 13,
  "override_useful_life_months": 60,
  "override_depreciation_method": "declining_balance_double",
  "override_gl_cost_account": "1520"
}
```

---

## Creating Assets

Use the `fixed_asset.create` workflow to add new asset records.

**See:** fixed_asset.create definition (fields: `get_submissions(action="schema", object_type, operation)`) for complete field details

### Basic Asset

```json
{
  "legal_entity_id": 13,
  "category_code": "COMPUTER",
  "asset_name": "Dell Latitude 5420 Laptop",
  "acquisition_date": "2025-01-15",
  "in_service_date": "2025-01-15",
  "original_cost": 1500.00,
  "depreciation_method": "straight_line",
  "useful_life_months": 36,
  "salvage_value": 0
}
```

### Depreciation books

The create, acquire, capitalize and import workflows create one primary book per asset;
a `books` array in the payload is not read, and no supported workflow adds a second
book yet. Every schedule line belongs to one book, and each book keeps its own
depreciation and book value (AR-370).


### Asset with Dimensions and Assignment

Tag assets with department/location and assign to employee:

```json
{
  "legal_entity_id": 13,
  "category_code": "COMPUTER",
  "asset_name": "Dell Latitude 5420 Laptop",
  "acquisition_date": "2025-01-15",
  "in_service_date": "2025-01-15",
  "original_cost": 1500.00,
  "employee_id": 42,
  "assigned_date": "2025-01-15",
  "dimensions": {
    "department": "SALES",
    "location": "NYC"
  }
}
```

The `dimensions` map is persisted with the asset (one command per type; `{ "type_code": ..., "value_code": ... }` and explicit `master_dimension_*_id` are accepted too). Only types whose `applies_to` includes `fixed_asset` can be assigned — `validate_only` refuses the others before anything is written.

**Reference Lists:**
- Dimensions (look up with `query(entity_type="dimension_type")` and `query(entity_type="dimension_value")`) - Available dimension types and values
- Legal Entities (look up with `query(entity_type="legal_entity")`) - Valid `legal_entity_id` values

---

## Acquiring Assets from Transactions

Use `fixed_asset.acquire_from_bill` to create new assets from source transactions.
Use `fixed_asset.link_source_transaction` when the asset already exists.

**See:** fixed_asset.acquire_from_bill definition (fields: `get_submissions(action="schema", object_type, operation)`) for complete field details

### Create New Asset from Transaction

When the transaction is already posted to an asset account:

```json
{
  "transaction_id": 123,
  "transaction_line_id": 456,
  "quantity": 1,
  "category_code": "COMPUTER",
  "legal_entity_id": 13,
  "asset_name_template": "Dell Laptop"
}
```

**GL Impact:** None (transaction already posted DR Asset, CR AP)

### Link Existing Asset to Transaction

For an existing asset, submit **`fixed_asset.link_source_transaction`**:

```json
{
  "legal_entity_id": 13,
  "fixed_asset_id": 45,
  "transaction_id": 43,
  "transaction_line_id": 34,
  "link_type": "acquisition"
}
```

`acquire_from_bill` creates new assets and requires `category_code`; it does not
support an `existing_asset_id` linking mode. Provide `book_id` for acquisition or
improvement links when the asset has multiple books. Submit one link per source
line. These link types can affect depreciation schedules, so select the intended
semantics rather than treating a link as documentation-only.

- `amount` is functional currency in whole cents. For `acquisition`/`improvement`
  it defaults to the line's posted asset cost not yet allocated to other assets.
- All acquisition and improvement links on one line together never exceed the
  line's posted asset cost; an over-allocation is refused with the available
  amount. Re-linking the same asset and line replaces its own amount.
- An `improvement` raises the asset cost and the book's acquisition cost and NBV,
  and re-spreads the scheduled lines from the improvement's source date over the
  same remaining periods of the selected book, net of its recognised depreciation
  and impairments (posted depreciation untouched). Re-linking applies only
  the difference. If no monthly fiscal period can hold the new lines, the link is
  refused: create the periods and link again.
- When the asset has no depreciation month left on or after the improvement's
  date (for example fully depreciated), the link needs `additional_life_months`:
  the months to depreciate the improvement over, chosen by you or the accountant
  (the platform has no default). It is refused without it, and refused when
  months remain. The asset's and book's recorded life grow by that number, and a
  `fully_depreciated` asset becomes `active` again.

### Multiple Assets from One Transaction (qty > 1)

Create 5 laptops from one bill line:

```json
{
  "transaction_id": 123,
  "transaction_line_id": 456,
  "quantity": 5,
  "category_code": "COMPUTER",
  "legal_entity_id": 13,
  "asset_name_template": "Dell Laptop #{n}",
  "depreciation_method": "straight_line",
  "useful_life_months": 36
}
```

### One Asset from Multiple Transactions

Combine multiple bills into one asset:

```json
{
  "category_code": "BUILDING",
  "legal_entity_id": 13,
  "asset_name": "Office Renovation - Phase 1",
  "source_transactions": [
    {
      "transaction_id": 101,
      "transaction_line_id": 201,
      "amount": 50000.00,
      "link_type": "acquisition"
    },
    {
      "transaction_id": 102,
      "transaction_line_id": 202,
      "amount": 30000.00,
      "link_type": "acquisition"
    }
  ],
  "depreciation_method": "straight_line",
  "useful_life_months": 180
}
```

---

## Capitalizing Expenses

Use the `fixed_asset.capitalize_expense` workflow when an expense should be reclassified as an asset.

**See:** fixed_asset.capitalize_expense definition (fields: `get_submissions(action="schema", object_type, operation)`) for complete field details

### Create New Asset from Expense

```json
{
  "transaction_id": 125,
  "transaction_line_id": 458,
  "legal_entity_id": 13,
  "fiscal_period_id": 50,
  "capitalize_amount": 8000.00,
  "asset_account_number": "1500",
  "category_code": "VEHICLE",
  "asset_name": "Engine Replacement",
  "justification": "Complete engine overhaul extending useful life by 5 years"
}
```

**GL Impact:** Yes - DR Asset, CR Expense

### Add Improvement to Existing Asset

```json
{
  "transaction_id": 126,
  "transaction_line_id": 459,
  "legal_entity_id": 13,
  "fiscal_period_id": 50,
  "capitalize_amount": 12000.00,
  "asset_account_number": "1520",
  "existing_asset_id": 42,
  "justification": "HVAC system upgrade"
}
```

Capitalizing into an existing asset moves its cost, book value and schedule
together, exactly like an `improvement` link, dated by the capitalization
journal. Add `book_id` when the asset has several books, and
`additional_life_months` when it has no depreciation months left.

---

## Capitalizing Construction-in-Progress

Use the `fixed_asset.capitalize_cwip` workflow when construction is complete.

**See:** fixed_asset.capitalize_cwip definition (fields: `get_submissions(action="schema", object_type, operation)`) for complete field details

```json
{
  "legal_entity_id": 13,
  "fiscal_period_id": 50,
  "cwip_account_number": "1600",
  "asset_account_number": "1520",
  "total_amount": 45500.00,
  "category_code": "BUILDING_IMPROVEMENT",
  "asset_name": "Office Renovation - 2nd Floor",
  "depreciation_method": "straight_line",
  "useful_life_months": 180,
  "in_service_date": "2025-02-01",
  "bill_ids": [101, 102, 103, 104, 105]
}
```

**GL Impact:** Yes - DR Asset, CR CWiP

---

## Transferring Assets

Use the `fixed_asset.transfer` workflow to move assets between dimensions.

**See:** fixed_asset.transfer definition (fields: `get_submissions(action="schema", object_type, operation)`) for complete field details

```json
{
  "asset_id": 42,
  "legal_entity_id": 13,
  "dimensions": {
    "department": "ENGINEERING",
    "location": "SF",
    "cost_center": "ENG-R&D"
  },
  "notes": "Transferred to Engineering for product development"
}
```

**GL Impact:** None (dimension change only)

---

## Recording Impairment

Use the `fixed_asset.impair` workflow when asset value permanently decreases.

**See:** fixed_asset.impair definition (fields: `get_submissions(action="schema", object_type, operation)`) for complete field details

```json
{
  "asset_id": 42,
  "legal_entity_id": 13,
  "fiscal_period_id": 50,
  "impairment_date": "2025-01-15",
  "impairment_amount": 5000.00,
  "impairment_account_number": "6450",
  "book_code": "GAAP",
  "notes": "Obsolescence due to new technology release"
}
```

**GL Impact:** Yes - DR Impairment Loss, CR Accumulated Depreciation

The journal is dated at the end of `fiscal_period_id`. The amount cannot exceed the
carrying amount at that date (cost less posted depreciation, earlier impairments and
depreciation still scheduled up to that period). Periods after it are re-based on the
new carrying amount over the asset's remaining useful life, and book values, disposal and
the GL reconciliation all include the impairment.

An impairment recorded before the 7 November 2026 release (PR #590, live 19:55 UTC) did
not re-base the schedule. Go by when it was recorded, not its `impairment_date`, which
can be backdated: the event's `created_at` is the recording time. The decisive check is
the schedule itself: if the book's scheduled depreciation after the impairment's period
totals more than its carrying amount less salvage, the later periods still use the old,
higher amounts and the book value will end below salvage (or below zero). That is the
known gap AR-1129, not a calculation error to work around; report it to the user rather
than posting a correcting journal.

---

## Disposing Assets

Use the `fixed_asset.dispose` workflow to sell, scrap, or retire assets.

**See:** fixed_asset.dispose definition (fields: `get_submissions(action="schema", object_type, operation)`) for complete field details

### Asset Sale (with proceeds)

```json
{
  "asset_id": 42,
  "legal_entity_id": 13,
  "fiscal_period_id": 50,
  "disposal_date": "2025-01-31",
  "proceeds_amount": 500.00,
  "proceeds_account_number": "1000",
  "notes": "Sold to employee at book value"
}
```

### Asset Scrapped (no proceeds)

```json
{
  "asset_id": 43,
  "legal_entity_id": 13,
  "fiscal_period_id": 50,
  "disposal_date": "2025-01-31",
  "proceeds_amount": 0,
  "notes": "Equipment beyond repair - scrapped"
}
```

**GL Impact:** Yes - DR Cash/Accum Depr/Loss, CR Asset

Disposal retires the whole asset in every book; there is no book-only disposal. The
journal comes from the entity's ledger-posting book and every other book keeps its own
closing value. `book_code` is optional: if you pass it, it must be the ledger-posting
book or the request is refused. A second disposal of the same asset, even sent at the
same moment, is refused with "Asset already disposed".

---

## Running Depreciation

### Schedule Depreciation Run

Use the `fixed_asset_depreciation.schedule` workflow:

```json
{
  "legal_entity_id": 13,
  "fiscal_period_id": 50,
  "book_code": "GAAP"
}
```

### Process Depreciation

Use the `fixed_asset_depreciation.process` workflow:

```json
{
  "run_id": 123,
  "legal_entity_id": 13,
  "auto_post": true
}
```

**GL Impact:** Yes - DR Depreciation Expense, CR Accumulated Depreciation

**Depreciation Methods:**
- `straight_line` - Equal amounts each period
- `declining_balance_double` - 200% declining balance
- `declining_balance_150` - 150% declining balance

### Sync a Migrated Asset's Subledger

Use the `fixed_asset.sync_subledger` workflow when a **migrated/imported** asset's GL is **already correct** (cost + accumulated depreciation posted via import and manual catch-up journal entries) but its FA register is stale — wrong book values, "no depreciation schedule." Do **not** run `fixed_asset_depreciation.process` for this: it would post *new* GL and double-count.

First categorize the asset if it has no category (the engine needs one):

```json
{
  "legal_entity_id": 41,
  "asset_id": 63,
  "category_code": "COMPUTER"
}
```

Then sync the subledger to the GL-tied figures:

```json
{
  "legal_entity_id": 41,
  "asset_id": 63,
  "accumulated_depreciation": "976.30",
  "last_depreciation_date": "2026-05-31",
  "book_code": "GAAP"
}
```

- `accumulated_depreciation` — the GL-tied accumulated depreciation **as of** `last_depreciation_date`.
- `last_depreciation_date` — the cut point: depreciation through here is already posted; the engine resumes **after** it (no double-counting).
- Optional `je_line_map` (`{ "period_end": transaction_line_gl_id }`) drill-down-links posted schedule rows to the catch-up JE's GL lines.
- Optional `force: true` overrides a material GL-variance rejection (logged).

**GL Impact:** None — subledger-only. It writes book values + rebuilds the schedule (posted through the cut date, scheduled after it), trues the posted rows up to `accumulated_depreciation`, then a **GL-tie guardrail** rolls the whole thing back if the subledger doesn't reconcile to GL within 1.00 in the functional currency (unless `force`).

---

## Common Scenarios

### Purchase New Equipment

1. Post bill to asset account (DR Equipment, CR AP)
2. Run `fixed_asset.acquire_from_bill` to create asset record
3. Asset linked to source transaction with depreciation schedule generated

### Capitalize Major Repair

1. Bill was posted to expense (DR Repairs, CR AP)
2. Run `fixed_asset.capitalize_expense` to reclassify
3. Creates GL entry: DR Asset, CR Repairs

### Complete Construction Project

1. Multiple bills posted to CWiP over time
2. Run `fixed_asset.capitalize_cwip` when complete
3. CWiP cleared, new asset in service

### Monthly Depreciation

1. Run `fixed_asset_depreciation.schedule` to create run
2. Run `fixed_asset_depreciation.process` to calculate and post
3. All active assets depreciated with GL posting

### Dispose Obsolete Equipment

1. Run `fixed_asset.dispose` with proceeds (if any)
2. System calculates gain/loss
3. GL entry removes asset, records gain/loss

### Transfer Asset to New Department

1. Run `fixed_asset.transfer` with new dimensions
2. Dimension assignments updated
3. Future depreciation posted to new department

### Fix a Migrated Asset Whose GL Is Already Correct

1. GL already holds the right cost + accumulated depreciation (import + catch-up JEs)
2. Run `fixed_asset.update` with `category_code` to categorize the asset (if needed)
3. Run `fixed_asset.sync_subledger` with the GL-tied `accumulated_depreciation` and `last_depreciation_date`
4. Subledger book values + schedule are rebuilt and tied to GL — **no new GL posted**; the engine resumes after the cut date

---

## Reference Data

Before constructing payloads, check these reference lists:

| Data Type | Reference List | Example Values |
|-----------|---------------|----------------|
| Depreciation methods | Depreciation Methods (look up with `get_submissions(action="schema", object_type="fixed_asset_category", operation="create")`) | `straight_line`, `declining_balance_double` |
| GL accounts | Chart of Accounts (look up with `query(entity_type="account")`) | Asset, expense, and accum depreciation accounts |
| Dimensions | Dimensions (look up with `query(entity_type="dimension_type")` and `query(entity_type="dimension_value")`) | Departments, Locations, Cost Centers |
| Legal entities | Legal Entities (look up with `query(entity_type="legal_entity")`) | Entity IDs for asset ownership |

---

## Workflow Details

For complete field specifications, validation rules, and constraints:

**Category Management:**
- fixed_asset_category.create (fields: `get_submissions(action="schema", object_type, operation)`)
- fixed_asset_category.update (fields: `get_submissions(action="schema", object_type, operation)`)

**Asset Lifecycle:**
- fixed_asset.create (fields: `get_submissions(action="schema", object_type, operation)`)
- fixed_asset.update (fields: `get_submissions(action="schema", object_type, operation)`)
- fixed_asset.attach (fields: `get_submissions(action="schema", object_type, operation)`)

**Acquisition:**
- fixed_asset.acquire_from_bill (fields: `get_submissions(action="schema", object_type, operation)`)
- fixed_asset.capitalize_expense (fields: `get_submissions(action="schema", object_type, operation)`)
- fixed_asset.capitalize_cwip (fields: `get_submissions(action="schema", object_type, operation)`)
- fixed_asset.link_source_transaction (fields: `get_submissions(action="schema", object_type, operation)`)

**Operations:**
- fixed_asset.transfer (fields: `get_submissions(action="schema", object_type, operation)`)
- fixed_asset.impair (fields: `get_submissions(action="schema", object_type, operation)`)
- fixed_asset.dispose (fields: `get_submissions(action="schema", object_type, operation)`)

**Depreciation & Subledger:**
- fixed_asset_depreciation.schedule (fields: `get_submissions(action="schema", object_type, operation)`)
- fixed_asset_depreciation.process (fields: `get_submissions(action="schema", object_type, operation)`)
- fixed_asset.sync_subledger (fields: `get_submissions(action="schema", object_type, operation)`) — subledger-only; align a migrated asset's book values + schedule to an already-correct GL

> `fixed_asset.update` also accepts `category_code` to (re)categorize a migrated/category-less asset (blocked if engine depreciation lines already exist, unless `force`).

---

## Key Concepts

### GL Impact Principle

**Transactions create GL entries when posted. Workflows create asset records and link them to transactions.**

This ensures:
- No duplicate GL postings
- Proper transaction tracking
- Complete audit trail

### Books and the ledger-posting book

- Each depreciation line belongs to one book; runs, previews and book values are per book.
- One book writes the ledger, set by governed policy `fixed_assets.policy` →
  `ledger_posting_book` (`{"book_code": "<code>"}`; default: each asset's primary book,
  a deliberate default, not a missing setting).
  Change it with `submit("policy", "save", ...)`; never assume a book code means anything.
- Other books are calculation-only: their run ends `calculated`, their lines are
  `calculated`, and no journal is written.
- A run takes each scheduled line once, even when runs for overlapping periods or a
  disposal happen at the same time.
- Disposal and impairment journal from the posting book; impairing a calculation-only
  book is refused. Omit `book_code` on a depreciation schedule to run the posting book.
- If an asset's ledger history came from a different book (the posting book was changed
  mid-life), runs skip it and disposal/impairment refuse it. Ask the user how to handle
  the transition; do not work around it.

### MSEO Pattern

Categories use the Master + Entity Override pattern:
- Master category provides organization-wide defaults
- Entity-specific overrides for different settings
- Query resolves effective values automatically

### Automatic Dimension Propagation

- Dimensions flow from source transactions to assets during acquisition
- Dimensions flow from assets to GL transactions during disposal/impairment/depreciation
- Enables dimensional reporting (depreciation by department, book value by location)

### Depreciation Schedule Generation

When assets are acquired with an `in_service_date`:
- Full depreciation schedule is generated automatically
- Schedule shows projected depreciation by period
- Catch-up depreciation calculated for backdated acquisitions

### Subledger Sync (Migrated Assets)

The FA **subledger** (book values + schedule) and the **GL** can be written independently. For a migrated asset whose GL is already correct but whose register is stale, `fixed_asset.sync_subledger` writes the subledger to match the GL **without posting any GL** — the missing subledger write path, decoupled from depreciation posting.

- It writes `fixed_asset_book_values`, rebuilds `fixed_asset_depreciation_lines` (posted through the cut date, scheduled after), and trues posted rows up to the GL-tied accumulated total.
- A **GL-tie guardrail** (`v_fixed_asset_gl_reconciliation`) rolls the whole transaction back if the result doesn't reconcile to GL within tolerance — so the subledger can never silently drift from the GL.
- Going forward the depreciation engine runs normally for the asset, resuming after `last_depreciation_date`.

### Transaction Linking

Assets can be linked to any transaction type:
- Bills (AP invoices)
- Journal entries
- Credit card transactions
- Bank transactions

Link types: `acquisition`, `improvement`, `repair`, `maintenance`, `capitalized_expense`


### Asset journal currency and period controls

Depreciation, impairment, and disposal journals carry the entity's functional currency on the header and populate document, functional, and reporting amounts on every GL detail. Reporting conversion reuses the transaction executor's rate lookup and rounding. Parent lines, project/employee attribution, and asset dimension copying remain intact. Closed or locked periods and entity/date mismatches are rejected. Disposal posts on `disposal_date` within the supplied `fiscal_period_id`; impairment and depreciation post at period end.

This change affects newly posted journals. Do not rerun a posted depreciation run to repair missing functional/reporting amounts: that risks duplicate expense and subledger movement. Historical recovery must identify affected journals, retain audit evidence, and reconcile both trial balance and asset register after an explicitly scoped correction. A zero variance in the existing FA reconciliation report alone is insufficient: its view compares document amounts, so also inspect the functional-currency trial balance.


### Disposal history and explicit recovery

For a disposed asset, stored book values retain actual accumulated depreciation and the net book value **at disposal**, used to explain the gain/loss. They are not a remaining recognized asset balance. Admin labels these values “NBV at disposal” and “Depr. at disposal”; the per-book table uses the same historical NBV label. `status=disposed` controls lifecycle eligibility; `is_active` is record availability, not proof that an asset is still in service. The asset record and posted schedule history remain available, and future scheduled depreciation is cancelled.

A full-disposal event records negative original cost and **negative actual accumulated depreciation cleared**. It does not add the full cost to accumulated depreciation. Historical events created by the older implementation may need the targeted recovery below.

Operations can preview one known defect with `mcp-server/scripts/repair_asset_posting.py` using `DATABASE_URL` from the explicitly selected environment. Required arguments: `--organization-id`, `--entity-id`, `--user-id`, `--record-id`, `--kind`, `--reason`, `--expected-host`, and `--expected-organization-name`. Omit `--apply` to preview; inspect the before/after evidence, then repeat with `--apply` only within the authorized environment and scope.

Supported kinds:
- `depreciation`: only posted, unreversed depreciation journals whose document GL balances tie to the header, currency fields have the exact legacy empty/zero signature, and document/functional/reporting currencies are identical. Closed/locked periods and partial or ambiguous values are refused. Repairs currency fields in place without creating GL or touching the depreciation schedule/register.
- `disposal_event`: only the old positive-full-cost delta signature, tied to exactly one posted, unreversed disposal GL clearing line. Corrects the event delta; preserves the journal and disposal book values.
- `depreciation_account`: only an explicitly selected master account matching a shipped US/IFRS depreciation definition by number, name, description, and normal balance, with the known wrong asset classification. Changes type/subtype to expense/depreciation_expense; custom matches are refused. Master classification affects all entities using that account.

Currency recovery uses the existing `sanction_gl_mutation` helper with the explicit `fixed_asset.currency_recovery` reason only after all eligibility checks. The database records the sanctioned mutation in transaction activity; the prior transaction-local setting is restored. No trigger is disabled and closed-period recovery remains refused. Each applied repair and its before/after evidence commit together to `system.audit_logs` with action `asset_recovery`; audit insertion failure rolls the repair back. Repeating a completed repair reports `already_correct`. Do not bulk rerun depreciation or rewrite unrelated historical journals. Verify the trial balance, income statement, asset register, and audit rows after recovery. Report-view currency limitations described above still apply.


Standard IFRS/US GAAP onboarding no longer seeds the unsupported generic acquisition profile
and `FIXED_ASSET_ACQUISITION` mapping. Use the fixed-asset workflows above; do not recreate
that mapping or change a header account into a leaf as an automatic setup repair. Existing
profile rows require separate review and are not removed by template initialization.


### AR-951 extraction candidate — not released

`capitalize_expense` treats each `capitalize_amount` as entity functional carrying
value. The extracted posting helper writes functional/reporting GL amounts and
matching transaction-line links, retaining the selected conversion evidence.
Required rates must be observed positive rates; missing-rate fallback is refused
for capitalization. Country/company capitalization policy remains outside this
integrity calculation.

Sources must be distinct current posted lines in the same entity, with identified
positive functional GL and sufficient unallocated capacity. Source writers lock
headers in a stable order; an existing target asset must belong to that entity.
The stored acquisition/improvement event maps the journal and individual source
allocations. Existing unique source-link limitations still apply.

Workflow-managed capitalization uses the workflow's own transaction, including
asset, journal, links and result recording. Standalone calls own their transaction.
After an uncertain response, inspect the original workflow; do not submit a new
operation just because a response was lost. Retrying the same gateway submission
returns the original completed result, including after a lost receipt, only when
the bound workflow matches the original actor, operation and payload. Missing
execution evidence or a pending workflow stays unresolved and cannot authorize
another posting.

Native asset requests use `manage_submissions(action="prepare_asset_actions", payload=...)`
with an object containing only `actions`, each with `operation="capitalize_expense"`
and its exact proposed `payload`. Preparation returns stable action IDs; it does
not approve, reserve source capacity or post. Submit the saved payload with its ID
in `_asset_action_id`. A new transport key cannot replace that action identity.
Changed plans require reconciliation. External callers do not need a native task.

Preparation requires installed immutable-plan retention guards (candidate migration
808; fresh local replay passed, final release numbering remains open). Completion uses
verified source coverage and current posted accounting evidence, not an agent's
claimed asset IDs. Missing coverage remains waiting for recovery. These native
hooks are extracted, but broader native lifecycle and release verification remain
open; retained action guards must not be removed to bypass that work.
This branch is not ready to release and makes no historical repair.


For native request recovery, inspect current source coverage and the request's
server-written closure fields. Never supply `closed_reason` or
`closed_transition_id` in `agent_request.update`; those inputs are refused.
Reopened work cannot reuse earlier closure evidence. Pre-tool lock contention uses a server-proven, policy-limited admission retry;
model output cannot manufacture this proof. After binding, recover existing
effects rather than assuming a retry is safe. The extraction is not released.
### Depreciation dimension allocation (unreleased AR-383 work)

Depreciation groups only assets sharing account, project, employee and all stored
dimension identities. Different departments receive separate debit and credit
allocations; identical classifications may aggregate. Posting retains the exact
classification snapshot used for grouping, including recorded inactive history.
This does not reconstruct historical effective-date assignments or repair old GL.
