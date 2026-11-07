

## Card purchase policy

Use the backend purchase workspace and shared matching decision; do not implement a competing card matcher in conversation. Preserve provider rows and show net purchase spend. Reference conflicts and competing candidates require review. A paid/settled item can still lack documentation; attach missing source evidence to the existing bill. Evidence review, waiver and grouping use `card_purchase.manage` with current version, evidence fingerprint and reason. Never infer write-off authority from matching tolerance.

Receipt follow-up belongs to the purchase obligation, with one owner and deduplicated reminder stages. Automation and delivery are report-only until the entity rollout settings are explicitly enabled. Statement coverage and opening/movement/closing balance controls must pass independently of agent match counts. August deletion/replay requires its own reviewed manifest and explicit authorization through transaction.delete; implementation permission does not authorize it.

Legacy payment-pass descriptions below apply to non-card AP/AR behavior. Card rows use the shared purchase policy and cannot use nearest-date refund pairing, fuzzy amount identity or adjusting-journal workarounds.

# Bulk Import (Master Data & Admin Panel)

This resource covers the universal bulk import system for **master data** (customers, vendors, employees, accounts, items, dimensions, fixed assets) via Claude chat or the admin panel CSV wizard.

> **For bulk transaction import** (AP invoices, AR invoices, journal entries, payments), see [Bulk Transaction Processing](bulk-transaction-processing.md).

---

## Overview

The import system provides a single entry point for all object types:

```
submit("<type>", "import", {
    legal_entity_id: <id>,
    records: [...],
    options: { on_duplicate: "skip", batch_size: 50 }
})
```

**Key features:**
- Single API for all object types
- Automatic sync (≤50 records) / async (>50 records) routing
- Pre-cached reference data for O(1) lookups
- Flexible entity resolution (by name, ID, tax_id, global_id, or external_id)
- Duplicate detection per object type
- Per-record error isolation (one failure doesn't block others)
- External ID support for data migration from QuickBooks, Xero, etc.
- Validate-only mode (dry run)
- Real-time progress tracking via `get_imports(action="status", import_id=...)` (replaces `get_import_status()`, MCP registration removed)
- Entity scope enforced before the import runs — a caller cannot import into a `legal_entity_id` outside their scope

> **Two equivalent entry points:** `submit(object_type, "import", ...)` and `manage_imports(action, ...)` (see [manage_imports() in Tools Reference](tools-reference.md)) both route through the same import executor. Whichever you use, the same rules apply: any org-configured `import_batch.review` approval workflow can put a batch into `pending_approval` before it runs, and a zero-error run — including an idempotent re-run where every record is a duplicate skip — always reports `success: true`.

---

## Supported Object Types

| Object Type | Required Fields | Duplicate Key | Notes |
|-------------|----------------|---------------|-------|
| `customer` | customer_name, email | tax_id, then customer_name | Supports billing/shipping addresses |
| `vendor` | vendor_name, email, payment_terms_code | tax_id, then vendor_name | Supports billing/remit-to addresses |
| `employee` | first_name, last_name, work_email, hire_date | work_email | Auto-generates global_employee_id |
| `account` | account_number, account_name, account_type, normal_balance | account_number | Supports parent_account_number hierarchy |
| `item` | item_number, item_name | item_number | Revenue/expense/asset/COGS account linking |
| `dimension_type` | name, display_name, applies_to | name | Hierarchy support |
| `dimension_value` | dimension_type_name, code, name | dimension_type_id + code | Parent code for hierarchies |
| `fixed_asset` | asset_number, name, legal_entity_id, original_cost, useful_life_months, in_service_date | asset_number + legal_entity_id | Category code resolution, depreciation config |

### Banking Data Importers

| Object Type | Required Fields | Duplicate Key | Notes |
|-------------|----------------|---------------|-------|
| `card_transaction` | external_transaction_id, card_id, amount, transaction_date | external_transaction_id + card_id + transaction_type | From connector or CSV. Writes to `bank_card_transactions`. **Also set `metadata.provider_purchase_id`** — the provider's id for the *purchase*, shared by every leg (charge, refund, fee) — or each leg becomes its own singleton and refunds land in review with no netting. See bank-statements-management.md, "Two ids per card row". |
| `opening_balance` | legal_entity_id, as_of_date, lines[] | — | Posts opening balance journal entry |
| `opening_balances_with_subledger` | legal_entity_id, balances[], fiscal_period_name | — | Opening balances with individual AR/AP items and fixed assets (uses clearing account 0000) |

### Transaction Importer (Generic)

| Object Type | Required Fields | Duplicate Key | Notes |
|-------------|----------------|---------------|-------|
| `transaction` | transaction_type_code, legal_entity_id, lines[] | type + reference_number + party | Handles all 30+ transaction types via executor registry |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

---

## Preflight Check (Discover Required Fields)

Before importing transactions, run a preflight check to discover the required fields for a specific transaction type. Required fields are configured per company in the workflow definition, so they vary between organizations.

```javascript
submit("transaction", "import", {
    "_operation": "preflight",
    "transaction_type_code": "AP_INVOICE",
    "legal_entity_id": 12
})
// Returns:
// {
//   "preflight": true,
//   "transaction_type_code": "AP_INVOICE",
//   "required_header_fields": [
//     {"field": "transaction_type_code", "type": "string"},
//     {"field": "legal_entity_id", "type": "number"},
//     {"field": "vendor_id", "type": "number"},
//     {"field": "payment_method", "type": "string"}
//   ],
//   "required_line_fields": [...],
//   "optional_header_fields": [...],
//   "optional_line_fields": [...]
// }
```

Optionally include a sample record in `records` to validate it against the full pipeline before submitting the batch.

---

## Performance Expectations

| Volume | Mode | Expected Time | Notes |
|--------|------|---------------|-------|
| 10 records | Sync | ~5 seconds | |
| 50 records | Sync | ~25 seconds | Dimension caching active |
| 200 records | Async | ~90 seconds | Dimension caching reduces ~30% of queries |
| 500 records | Async | ~4 minutes | |
| 5,000 records | Async | ~50 minutes | Multiple batches |
| 20,000 records | Async | ~2 hours | With dimension caching |

---

## Import via Claude Chat

### Step 1: User Provides Data

User may provide data as:
- CSV file upload
- Pasted table or list
- Verbal description ("Add these 5 vendors...")

### Step 2: Build Records Array

Map the data to the import format:

```javascript
// Step 1: Discover required fields for import
schema = get_submissions(action='schema', object_type="vendor", operation="import")

// Step 2: Submit with discovered fields
submit("vendor", "import", {
    legal_entity_id: 12,
    records: [
      {
        vendor_name: "Acme Corp",
        email: "ap@acme.com",
        payment_terms_code: "NET_30",
        tax_id: "12-3456789"
      },
      {
        vendor_name: "Office Plus",
        email: "billing@officeplus.com",
        payment_terms_code: "NET_45"
      }
    ],
    options: {
      on_duplicate: "skip"
    }
})
// Tip: Use options: { validate_only: true } to validate an import without persisting it.
```

### Step 3: Preview Before Submitting

**Always show a summary before importing:**

```
I've prepared 15 vendor records for import:
- Entity: Arfiti Technologies OÜ (ID: 12)
- Payment terms: NET_30 (10), NET_45 (3), DUE_ON_RECEIPT (2)
- Duplicate handling: skip existing

Shall I proceed?
```

### Step 4: Report Results

```
Import complete:
- 13 of 15 vendors created
- 2 skipped (duplicates: Acme Corp, Tech Solutions — already exist)
- 0 errors
```

---

## Sync vs Async Routing

| Records | Mode | Behavior |
|---------|------|----------|
| 1-50 | **Synchronous** | Full result returned immediately |
| 51+ | **Asynchronous** | Returns `import_id`, processes in background |

### Async Flow

```javascript
// Step 1: Submit large import
const result = submit("customer", "import", {
    legal_entity_id: 12,
    records: largeArray,  // 200+ records
    options: { on_duplicate: "skip" }
})
// Returns: { import_id: "uuid", async: true, status: "importing" }

// Step 2: Poll for progress
get_imports(action="status", import_id="uuid")
// Returns: { status: "importing", progress_pct: 60, processed_records: 120, ... }

// Step 3: Final result
get_imports(action="status", import_id="uuid")
// Returns: { status: "completed", imported_count: 190, skipped_count: 5, error_count: 5, ... }
```

**Concurrent limit:** Only one background import per organization at a time, including CSV and approved background imports, across server processes. Small record-array imports (≤50 rows) are unaffected. If refused, check import history and retry when the running import finishes; the refusal may include its import ID when that job is on the same server process. A refused new submission creates no import record; an approved batch keeps its existing record.

**Approval gate:** If the org has an `import_batch.review` workflow configured, the import (sync or async) can land in `pending_approval` instead of running immediately — check `status` in the response rather than assuming it always executes right away. A reviewer rejection or request for changes marks that import `rejected`; no business rows are imported. Use `get_imports(action="status", import_id=...)` to read its final status.

---

## Import Options

| Option | Default | Description |
|--------|---------|-------------|
| `on_duplicate` | `"skip"` | `"skip"` = ignore, `"update"` = overwrite, `"error"` = fail |
| `batch_size` | `100` | Records per database transaction |
| `stop_on_error` | `false` | Stop entire import on first error |
| `validate_only` | `false` | Dry run — no business writes. Record-array previews persist no import tracking; CSV checks retain a check record, file hash and row results |
| `defaults` | `{}` | Default values merged into every record |

---

## Validate-Only Mode (Dry Run)

Run validation without persisting any records:

```javascript
submit("vendor", "import", {
    legal_entity_id: 12,
    records: [...],
    options: { validate_only: true }
})
```

Returns validation results: which records would succeed, which would fail, and why.

---

## External ID Support (Data Migration)

For migrating from external systems (QuickBooks, Xero, etc.):

### Step 1: Import Master Data with External IDs

```javascript
submit("vendor", "import", {
    records: [{
      vendor_name: "Acme Corp",
      email: "ap@acme.com",
      payment_terms_code: "NET_30",
      metadata: { external_id: "QB-VEND-1234" }
    }]
})
```

The `external_id` is stored in the `metadata` JSONB column. Later, transaction imports can reference entities by their external IDs (`external_vendor_id: "QB-VEND-1234"`).

### Supported External ID Fields

| Entity | Store As | Reference As (in transactions) |
|--------|----------|-------------------------------|
| Vendors | `metadata.external_id` | `external_vendor_id` |
| Customers | `metadata.external_id` | `external_customer_id` |
| Employees | `metadata.external_id` | `external_employee_id` |
| Accounts | `metadata.external_id` | `external_account_id` (line-level) |
| Items | `metadata.external_id` | `external_item_id` (line-level) |
| Tax Codes | `metadata.external_id` | `external_tax_code_id` (line-level) |

### Migration Order

1. Import accounts (chart of accounts)
2. Import vendors, customers, employees — all with `metadata.external_id`
3. Import items
4. **Import opening balances** (see below)
5. Import transactions referencing entities by external IDs
6. Import fixed assets

---

## Opening Balance Import

**CRITICAL:** Always use `manage_imports("opening_balances", ...)` for opening balances. **Never** use `submit("transaction", "post")` — it will fail with validation errors and miss auto-balancing, fiscal period checks, and subledger support.

### When to Use

- Migrating from a prior accounting system (Merit, QuickBooks, Xero, etc.)
- Setting up opening balances for a new entity starting on Arfiti
- User provides a balance sheet from the prior year

### Step 1: Ensure Fiscal Periods Exist

Opening balances from a 31.12.2024 balance sheet should be posted to fiscal period **2025-01** (January of the new fiscal year). Check if the period exists:

```javascript
query("fiscal_period", filters={"legal_entity_id": 12}, limit=50)
```

If periods for the target year don't exist, **create them first**:

```javascript
// Create the needed fiscal period
submit("fiscal_period", "create", {
    "legal_entity_id": 12,
    "period_name": "2025-01",
    "period_type": "month",
    "start_date": "2025-01-01",
    "end_date": "2025-01-31",
    "fiscal_year": 2025
})
```

**Do NOT just post to the earliest existing period** — opening balances MUST be in the correct fiscal year.

### Step 2: Map the Balance Sheet

Read the user's balance sheet and map each line to a chart of accounts entry. Only include **balance sheet accounts** (assets, liabilities, equity) — NOT revenue or expense accounts (those reset to zero each year).

**Debit/credit rules:**
- Assets with positive balances → **debit**
- Liabilities with positive balances → **credit**
- Equity with positive balances → **credit**
- Accumulated depreciation (contra-asset) → **credit**

### Step 3: Detect Subledger Accounts (ALWAYS DO THIS)

Before uploading, check if the balance sheet includes these accounts:

| Account Type | Detection | Ask For |
|---|---|---|
| **Accounts Receivable** | `account_subtype: accounts_receivable`; names with "receivable", "trade debtor" | List of unpaid customer invoices (customer, invoice #, amount, date, due date) |
| **Accounts Payable** | `account_subtype: accounts_payable`; names with "payable", "trade creditor" | List of unpaid vendor bills (vendor, bill #, amount, date, due date) |
| **Fixed Assets** | `account_subtype: fixed_asset_cost` (cost) + `accumulated_depreciation` | List of assets (name, acquisition date, cost, accum depreciation, useful life) |

**ALWAYS ask the user for these details.** Explain the tradeoff:
- **With details**: aging reports work, depreciation runs automatically, payment scheduling has individual items
- **Without details**: GL balance is correct but subledger features don't work (one lump sum in aging)

### Step 4: Upload

**Basic (no subledger details):**

```javascript
manage_imports("opening_balances", {
    legal_entity_id: 12,
    balances: [
        {"account_number": "1000", "debit": 50000, "credit": 0},
        {"account_number": "1200", "debit": 25000, "credit": 0},
        {"account_number": "2000", "debit": 0, "credit": 30000},
        {"account_number": "3000", "debit": 0, "credit": 45000}
    ],
    fiscal_period_name: "2025-01",
    balancing_account_number: "3300"
})
```

**With subledger details (preferred):**

```javascript
manage_imports("opening_balances_with_subledger", {
    legal_entity_id: 12,
    balances: [
        {"account_number": "1000", "debit": 50000, "credit": 0},
        {"account_number": "1200", "debit": 25000, "credit": 0},
        {"account_number": "2000", "debit": 0, "credit": 30000},
        {"account_number": "1500", "debit": 40000, "credit": 0},
        {"account_number": "1600", "debit": 0, "credit": 15000},
        {"account_number": "3000", "debit": 0, "credit": 70000}
    ],
    fiscal_period_name: "2025-01",
    balancing_account_number: "3300",
    open_ar_items: [
        {"customer_name": "Acme Corp", "reference_number": "INV-001", "amount": 15000,
         "invoice_date": "2024-10-15", "due_date": "2024-11-15"},
        {"customer_name": "Widget Inc", "reference_number": "INV-002", "amount": 10000,
         "invoice_date": "2024-11-20", "due_date": "2024-12-20"}
    ],
    open_ap_items: [
        {"vendor_name": "Supplier Co", "reference_number": "BILL-042", "amount": 20000,
         "invoice_date": "2024-12-01", "due_date": "2025-01-15"},
        {"vendor_name": "Office Depot", "reference_number": "BILL-043", "amount": 10000,
         "invoice_date": "2024-12-10", "due_date": "2025-01-10"}
    ],
    fixed_assets_detail: [
        {"name": "Server Equipment", "acquisition_date": "2023-06-15",
         "original_cost": 25000, "accumulated_depreciation": 10000, "useful_life_months": 60},
        {"name": "Office Furniture", "acquisition_date": "2022-01-01",
         "original_cost": 15000, "accumulated_depreciation": 5000, "useful_life_months": 84}
    ]
})
```

**How the subledger version works:** The system uses a clearing account (0000) to keep the GL balanced. Each open AR/AP item becomes its own posted transaction. The OPENING_ENTRY posts the clearing account instead of the AR/AP control accounts. The clearing account nets to zero. Result: same GL balances, but individual items in aging reports.

### Step 5: Verify

```javascript
generate_report("trial_balance", {"legal_entity_id": 12, "as_of_date": "2025-01-01"})
```

Check: total debits = total credits, each line matches the user's balance sheet.

### The Balancing Account

The `balancing_account_number` (an equity account of the entity, e.g. its `retained_earnings` account; ask the user which one) absorbs any small rounding difference. If the balancing amount is more than rounding, something is wrong — review the data.

### Common Pitfalls

1. **Forgetting accumulated depreciation**: Fixed assets at cost (a debit to the `fixed_asset_cost` account, e.g. 1500), accumulated depreciation as a separate credit (the `accumulated_depreciation` account, e.g. 1600)
2. **Double-counting net income**: If the balance sheet already includes net income in retained earnings, don't add it again
3. **Missing fiscal periods**: Always create periods before posting — don't post to wrong year
4. **Using submit() instead of manage_imports()**: submit() doesn't handle auto-balancing or subledger detection

---

## Address Support

Three importers support address fields via flat CSV columns:

**Customer:** `billing_*` and `shipping_*` prefixes
```
billing_address_line_1, billing_city, billing_state, billing_postal_code, billing_country
shipping_address_line_1, shipping_city, shipping_state, shipping_postal_code, shipping_country
```

**Vendor:** `billing_*` (primary) and `shipping_*` (remit-to) prefixes

**Employee:** `home_*` and `mailing_*` prefixes

Addresses require `legal_entity_id` to be set.

---

## Admin Panel: CSV Import Wizard

The admin dashboard provides a 5-step wizard for CSV file imports at **Administration > Bulk Import**.

### Step 1: Select Type
- Choose object type (customer, vendor, employee, account, item, etc.)
- Select target legal entity

### Step 2: Upload CSV
- Drag-and-drop or browse file upload
- Instant preview of first 50 rows
- Shows total row count and column headers

### Step 3: Field Mapping
- **Auto-mapping**: CSV headers automatically matched to target fields (lowercased, normalized)
- **Required fields** highlighted — must be mapped or given a default value
- **Default values**: Set fallback values for unmapped required fields
- **Metadata catch-all**: Toggle to store all unmapped CSV columns as JSONB metadata (preserves legacy data)
- **Mapping templates**: Save/load reusable mapping configurations per object type

### Step 4: Review
- Summary of settings, field mapping, and options
- Duplicate handling mode selection

### Step 5: Progress
- Real-time progress bar with percentage
- Live counters: imported, updated, skipped, errors
- Error list with row numbers and record identifiers
- Duration on completion

### Import History

View past imports at **Administration > Bulk Import > History**:
- Status, counts, and duration for each import
- Filter by object type
- Color-coded status badges

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Required field missing: email` | CSV row missing required field | Map the column or set a default value |
| `Duplicate: Acme Corp` | Record already exists | Use `on_duplicate: "update"` or `"skip"` |
| `Payment term NET99 not found` | Invalid foreign key reference | Check available payment terms. Use underscore format: `NET_30`, `NET_60`, `DUE_ON_RECEIPT` |
| `Account 9999 not found` | Invalid account number | Verify account exists for this entity |

### Recovery from Partial Failures

1. Check `errors_detail` in the response
2. Fix problematic records in CSV
3. Re-submit with `on_duplicate: "skip"` to skip already-imported records
4. Successfully imported records are NOT rolled back

> A clean re-run of a batch that's already fully imported reports `success: true` with `imported: 0` and every record counted as a duplicate skip — that's the expected idempotent result, not a failure. Look at `error_count`, not `imported_count`, to tell whether the re-run actually found new problems.

---

**Version**: 1.0
**Last Updated**: February 2026
**Related Resources**:
- [Bulk Transaction Processing](bulk-transaction-processing.md) - Transaction-specific bulk import
- [Vendor Management](vendor-management.md) - Vendor master data
- [Customer Management](customer-management.md) - Customer master data
- [Employee Management](employee-management.md) - Employee records
- [Data Migration Specialist](../roles/data-migration-specialist.md) - Full system migration workflow

### Import scope and dry runs

For a records-array `import.execute`, place `validate_only` inside `options`; a top-level flag is rejected. A stored-CSV request instead supplies a company-scoped `r2_storage_key` and non-empty `field_mapping` without `records`; its legacy top-level check flag remains accepted. `get_submissions(action="schema", object_type="customer", operation="import")` describes both alternatives. Public `submit(..., validate_only=True)` checks the envelope but does not read the file or validate its rows; `options.validate_only` starts an actual CSV row check. The outer `submit` object type supplies the payload type when omitted. Supported built-in import types are `account`, `card_transaction`, `customer`, `dimension_type`, `dimension_value`, `employee`, `fixed_asset`, `item`, `opening_balance`, `transaction`, and `vendor`. A top-level `legal_entity_id` is copied into each record for synchronous, asynchronous and approval paths. A conflicting record entity is rejected. Use separate imports for different entities. Dimension codes identify classification; they never compute or allocate monetary amounts.

## Validation, partial results and transaction boundaries

For a submitted **records array**, `options.validate_only` (or `manage_imports(action=<import type>, validate_only=true)`) validates without import tracking, approval requests or business writes. The response sets `validation_only=true`; `validated_records` counts valid records and `imported` is zero.

Each independent imported record commits with its GL, workflow audit and external-link rows on one connection. A failed record rolls back its counts and IDs, and processing continues unless `stop_on_error=true`. Existing grouped imports retain group transactions. The synchronous record-array response reports `status="partial"` if some records succeeded, otherwise `status="failed"`; compatibility `success=true` may still represent partial success. A CSV job can report `completed` with rejected rows; inspect its `error_count` and row records. Inspect errors before retrying and use duplicate handling to avoid replaying committed records.

For a rejected Merit group, every rolled-back row counts as processed and as an error. The group has one summary cause and one error row outcome per record; `total_records - processed_records` still means rows not attempted.

Transaction imports refuse missing/inactive tenant `transaction.post` definitions when the template defines that operation, including validation and connector imports. This check supplements the existing `import_batch.review` approval path; it does not remove it. `get_submissions(action="schema", object_type="customer", operation="import")` and other supported import aliases expose the shared two-form import envelope; public preview success is not proof of row or file validity.


### Employee numbering across imports and creation (E2E-041)

Employee creation and imports without a supplied `global_employee_id` use the
same tenant `master_employee_seq` through the shared employee allocator. IDs
are organization-wide, formatted `EMP-` plus at least six digits; separate legal
entities do not restart this master ID sequence. Allocation skips IDs already
occupied by earlier or explicit imports, without resetting the counter or
renumbering existing records. Concurrent generated allocations use PostgreSQL
`nextval`; rolled-back or failed operations may leave normal gaps.

Explicit IDs in imports are preserved and still subject to duplicate detection
and database uniqueness checks. They do not change the configured sequence.
Do not manually reset the counter to recover a collision; retry the failed
creation after deploying the shared allocator. Custom source IDs need not have
a numeric EMP suffix. Numbers beyond six digits are preserved, not truncated.


For an R2 CSV payload (`r2_storage_key`), `options.validate_only` is the
implemented **Check rows first** path. It streams the file and persists an
import check record, `check_sha256` and per-row validation/error results; it
does not write business records or consume the approval or re-import gates.
On that check record, `imported_count` counts rows that passed validation,
not newly imported business records. Inspect `options.validate_only` and the
later Execute run separately.
A later Execute uses only the rows that passed that completed check, after
verifying the file bytes and the checked target/mapping still match.

### Interrupted import recovery

The server probes import lifetime session locks at startup and every five minutes
until shutdown. The interval schedules probes; it is not an import-age threshold.
New jobs claim
that lock before publishing `importing`, including preprocessing and nontransaction
imports, and release it after processing/finalization. Another worker's held lock
prevents recovery. An unlocked marked record becomes `failed`, retaining its
counts and existing errors and appending a restart explanation. No age threshold
is used. The message says rows **recorded** as written. CSV jobs with row
records (every importer except opening balances) commit each row or Merit
group with its row outcome and the run's counts in the same transaction. A failed outcome write
rolls back that business row, which is then recorded as an error ("CSV row
outcomes could not be persisted"); a row the ledger refuses at COMMIT is
recorded the same way. A worker loss after commit preserves its outcome. A rolled-back row's error outcome is written right after
the rollback; if that write fails, the run stops and its row records are marked
`partial`. The difference between total and processed rows is not an error
count: it is the rows not reached when the job stopped. Large record-array
imports and CSV jobs from before November 2026 can still have lagging progress,
so inspect the ledger before resubmitting a partial or historical file.

For a failed run with known or uncertain written rows, the public import-status
message and Dashboard run detail repeat that review-before-retry instruction.
They do not describe a no-write refusal as having written rows.

A CSV opening-balance import binds its posted
`OPENING_ENTRY` to the import ID and stores its processed/imported counts in the
journal metadata. If the worker stops just after posting, recovery restores
counts only from that exact journal; an unbound same-period entry is never
credited to the import. When binding cannot be verified, review the period
before retrying. A second opening entry for the same entity and period is
refused. Opening-balance CSV does not use generic per-row receipts. The CSV job reads
an opening-balance file as one batch, whatever its size, so a trial balance of more
than 100 accounts posts as one journal.
Its imported count excludes a generated balancing-account line.

Rolling-upgrade limitation: unmarked legacy `importing` records are counted in
startup logs as `legacy_needing_review` and left unchanged. Their liveness cannot
be proved with the transaction-only file lock, especially during preprocessing.
Review them after all old workers stop; do not infer failure from age or reset
counts. Pending jobs that died before starting are also outside this sweep.
The file fingerprint lock prevents a simultaneous duplicate transaction-file import. For new imports, a marker committed with the first written row also prevents a same-file retry if the worker dies before its progress count is saved. Recovery reports only durably stored outcomes; it does not guess what an in-flight row would have done. Older fingerprinted imports made before this marker or the row-outcome change require manual review when their counts may have lagged.

### Mandatory account subtype

Supply a canonical `account_subtype` for every account creation/full import, including
headers, inactive accounts and duplicate updates. Use the stored account type on updates.
Missing, null and blank subtype are errors. A partial `account.update` may omit subtype
only to retain an existing classification; explicit clearing is refused. A legacy account
with no subtype needs reviewed classification before update. Unmapped connector accounts
cannot be promoted; do not guess from names or default them to an arbitrary subtype.
Migration 664 installs the database presence constraint; legacy gaps are preserved and
require operator review/validation. This does not activate the new AP/AR membership policy.

Account updates after migrations 665–668 must preserve protected settings once the account
has a GL/document-line/profile reference. Duplicate imports with changed classification or
policy flags fail that row; unchanged settings and presentation edits remain permitted.
Zero balance is not permission to reclassify. Refer the change for a reviewed transition;
do not clear usage state or delete references. Historical transition apply remains unavailable. The migration-669 operator correction
procedure is separate, requires no retained financial evidence and cannot be invoked merely
because an import was approved.


### Transaction import event references — historical policy, superseded by PR403

Generic MCP reads of retained `import.completed.transaction` and
`import.completed.opening_balance` events from `import_executor` validate every
ID in `created_ids` and `updated_ids` against stored transaction type and the
event entity. Opening-balance import IDs refer to `OPENING_ENTRY` transactions.
The event type must agree with its payload object type; both arrays must be
present and contain positive integer IDs. Malformed, missing, foreign-entity or
unauthorized references hide the event on all generic read surfaces.

This changes event reads only. Transaction update-on-duplicate remains unsupported
and skipped by the importer; validating hostile updated arrays does not add update
support. Binding the event to its retained import record remains open coverage. Import execution and recovery permissions are unchanged.


### Master-data and card import event references — historical policy, superseded by PR403

Import completion events for customers, vendors, employees, accounts, items,
dimension types/values, fixed assets and card transactions validate both ID
arrays using the installed registry's read permissions and record keys. Effective
views use master IDs, not entity-assignment IDs. Entity records must match the
event entity; dimension types belong to the caller's organization. Every supplied
ID must resolve, even for wildcard callers.

Card IDs additionally use stored employee ownership: ordinary members can read
their own employee's records, while the existing broad membership roles retain
their wider access. Caller-supplied role labels do not grant that access. The
existing event payload domain, organization, entity, task and mailbox checks also
apply. Unknown importer types, mismatched event types and malformed arrays fail
closed. This checks referenced record access; it does not yet prove the event's
binding to a retained import run or certify arbitrary copied narrative.


### PR396 disposition — superseded by PR403 (2026-10-20)

PR396 was closed unmerged after comparing its head
`5a032a152181097285889c823e594d28df3ba475` with main
`0fe26ae70eb6c5030483d07d0ec2c1f8eb6088b0`. Its only production-code
change added retained-import envelope checks to `import_event_read_sql`. That
helper has no production callers after PR403; its remaining caller is the
explicitly historical `tests/legacy_event_read_fixtures.py`.

Current Dashboard and MCP agent-event reads use the shared agent-artifact grant
and certified entity-scope policy. Import source/payload traversal is not part of
that read decision. PR396 did not change import producers or execution validation,
so it would not fix current production behavior. The old tests and benchmarks
remain historical evidence, not acceptance requirements for the replacement
policy. Import execution/recovery and underlying business-record permissions remain
unchanged. PR396 was never merged or deployed; no replacement CI run is needed
for this documentation-only disposition.
