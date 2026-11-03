# Posting Profiles & Transaction Type Configuration

**Purpose:** Manage posting profiles (GL account pairs) and their mappings to transaction types for automatic double-entry accounting

---

## Overview

Posting profiles define **which GL accounts to debit and credit** when posting a transaction. Every transaction type (AR_INVOICE, AP_PAYMENT, etc.) is mapped to a posting profile so the system knows how to generate journal entries automatically.

**Relationship chain:**
```
Transaction Type (e.g., AR_INVOICE)
  → Transaction Type Posting Profile (mapping)
    → Posting Profile (e.g., "Customer Receivables")
      → Debit Account: <accounts_receivable> (illustrative — actual GL varies per org's COA)
      → Credit Account: <operating_revenue>
```

## Fail-loud rule (Batch C7, 2026-05-05)

**No hardcoded GL number fallbacks anywhere in the system.** Profile-based resolvers use the following common chain where implemented; verify the specific route before assuming every stage applies:

1. `transaction_type_posting_profiles` for the txn type → side-specific account
2. Generic `posting_profiles` row keyed by `profile_type` matching the txn (e.g., `'vendor_payment'`, `'revenue'`)
3. Canonical `account_subtype` lookup against `master_accounts` (e.g., `'accounts_payable'`, `'operating_revenue'`)
4. **`raise ValueError(...)`** with an actionable message — NO fallback to `'1000'`/`'4000'`/etc.

If a route cannot resolve its required accounts, it must refuse to post and surface the missing configuration. A missing profile alone is not an error for routes with explicit line accounts, bank mappings or category accounts. This is intentional: a half-posted journal with the wrong account is much harder to detect and reverse than a clear refusal at submit time.

CI guardrails enforce this rule at every commit:
- `mcp-server/tests/test_c5_no_coa_coupling.py` — Python (zero-tolerance)
- `admin-dashboard/__tests__/server/accounting-router.test.ts` — TypeScript (zero-tolerance)

For the canonical subtype taxonomy used in step 3 of the resolution chain, see [accounts-management.md](./accounts-management.md) — "Canonical Subtype Taxonomy" section.

**What you can do:**
- List all posting profiles and their GL account assignments
- List all transaction type → posting profile mappings
- Create, update, and delete posting profiles via workflow system
- Search profiles by type, name, or account number
- Auto-link posting profiles to transaction types on creation

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

---

## Querying Posting Profiles

### List All Posting Profiles

```javascript
query("posting_profile", filters={"legal_entity_id": 13})
```

Returns all posting profiles with resolved account numbers and names.

### Filter by Profile Type

```javascript
query("posting_profile", filters={"legal_entity_id": 13, "profile_type": "customer"})
```

### Search Posting Profiles

```javascript
query("posting_profile", query="customer")
```

Searches across: `profile_name`, `profile_type`, `debit_account_number`, `credit_account_number`

### Get Specific Posting Profile

```javascript
get_entity("posting_profile", id=123)
```

---

## Querying Transaction Type Mappings

### List All Transaction Type → Posting Profile Mappings

```javascript
query("transaction_type_posting_profile", filters={"legal_entity_id": 13})
```

Returns each transaction type with its assigned posting profile and GL accounts.

### Filter by Transaction Type

```javascript
query("transaction_type_posting_profile", filters={"legal_entity_id": 13, "transaction_type_code": "AR_INVOICE"})
```

### Search Transaction Type Mappings

```javascript
query("transaction_type_posting_profile", query="AR_INVOICE")
```

Searches across: `transaction_type_code`, `transaction_type_name`, `profile_name`

---

## Managing Posting Profiles (Create / Update / Delete)

All write operations use the workflow system via `submit()`.

### Create a Posting Profile

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="posting_profile", operation="create")

// Step 2: Submit with discovered fields
submit("posting_profile", "create", '{
    "legal_entity_id": 13,
    "profile_name": "Customer Receivables",
    "profile_type": "customer",
    "debit_account_number": "1100",
    "credit_account_number": "4000",
    "description": "AR invoices and credit memos",
    "is_default": true,
    "transaction_type_code": "AR_INVOICE"
}')
// Tip: Use validate_only=true to check payload before submitting
```

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

**Required fields:**

| Parameter | Description |
|-----------|-------------|
| `legal_entity_id` | Legal entity ID |
| `profile_name` | Display name (e.g., "Customer Receivables") |
| `profile_type` | Category string (e.g., "customer", "vendor", "bank_fee") |
| `debit_account_number` | GL account number for debit side |
| `credit_account_number` | GL account number for credit side |

**Optional fields:**

| Parameter | Description |
|-----------|-------------|
| `description` | Profile description |
| `is_default` | Default profile for this type (default: false). Setting true unsets existing default. |
| `transaction_type_code` | Transaction type code (e.g., "BANK_FEE"). If set, auto-creates linkage in `transaction_type_posting_profiles`. |

**Notes:**
- `profile_type` accepts any string — common types listed below
- Account numbers are validated against the entity's chart of accounts via `v_accounts_effective`
- If `is_default: true`, any existing default for this profile_type is unset
- **Key feature:** Including `transaction_type_code` auto-creates the transaction type linkage — no separate step needed

### Update a Posting Profile

```javascript
submit("posting_profile", "update", '{
    "posting_profile_id": 42,
    "legal_entity_id": 13,
    "debit_account_number": "6350",
    "is_default": true,
    "transaction_type_code": "BANK_FEE"
}')
```

**Required fields:** `posting_profile_id`, `legal_entity_id`

**Updatable fields:** `profile_name`, `profile_type`, `debit_account_number`, `credit_account_number`, `description`, `is_default`, `transaction_type_code`

**Notes:**
- Only provided fields are updated (dynamic SET clause)
- Account number changes are resolved via `v_accounts_effective`
- If `transaction_type_code` is provided, upserts the linkage in `transaction_type_posting_profiles`

### Delete (Deactivate) a Posting Profile

```javascript
submit("posting_profile", "delete", '{
    "posting_profile_id": 42,
    "legal_entity_id": 13
}')
```

**Behavior:** Soft delete — sets `is_active = false` on the profile AND deactivates all linked `transaction_type_posting_profiles` rows. Returns count of deactivated linkages.

---

## Profile Types Reference

Profile types are categories that group posting profiles. One profile type can serve multiple transaction types.

### Standard Profile Types (IFRS)

| Profile Type | Profile Name | Debit Account | Credit Account | Description |
|-------------|-------------|---------------|----------------|-------------|
| `customer` | Customer Receivables | 1100 (Trade Debtors) | 4000 (Revenue) | AR invoices, credit memos, debit memos |
| `vendor` | Vendor Payables | 6200 (Admin Expenses) | 2000 (Trade Creditors) | AP invoices, credit memos, debit memos |
| `customer_payment` | Customer Payment Receipt | 1000 (Cash) | 1100 (Trade Debtors) | Customer payments received |
| `vendor_payment` | Vendor Payment | 2000 (Trade Creditors) | 1000 (Cash) | Payments to vendors |
| `inventory_receipt` | Inventory Receipt | 1300 (Inventories) | 2000 (Trade Creditors) | Inventory purchases |
| `inventory_shipment` | Inventory Shipment | 5000 (Cost of Sales) | 1300 (Inventories) | COGS on sales |
| `inventory_adjustment` | Inventory Adjustment | 5300 (Stock Losses) | 1300 (Inventories) | Write-downs, shrinkage |
| `bank_deposit` | Bank Deposit | 1000 (Cash) | (varies) | Deposits to bank |
| `bank_withdrawal` | Bank Withdrawal | (varies) | 1000 (Cash) | Withdrawals from bank |
| `bank_transfer` | Bank Transfer | 1000 (Cash) | 1000 (Cash) | Inter-bank transfers |
| `expense` | Operating Expenses | 6200 (Admin Expenses) | 1000 (Cash) | General expenses, bank fees |
| `revenue` | Service Revenue | 1100 (Trade Debtors) | 4100 (Service Revenue) | Bank interest, misc revenue |
| `depreciation` | Depreciation Expense | 6400 (Depreciation) | 1620 (Accum. Depreciation) | Monthly depreciation |
| `payroll_salary` | Payroll - Salaries | 6010 (Base Salaries) | 2210 (Accrued Salaries) | Salary expense |
| `payroll_tax_employer` | Payroll - Employer Taxes | 6100 (Social Charges) | 2400 (Payroll Tax Payable) | Employer payroll taxes |
| `payroll_tax_employee` | Payroll - Employee Tax | 2210 (Accrued Salaries) | 2410 (Income Tax Withheld) | Employee withholding |
| `vat_output` | VAT Output (Sales) | 1100 (Trade Debtors) | 2300 (VAT Payable) | VAT on sales |
| `vat_input` | VAT Input (Purchases) | 2310 (VAT Receivable) | 2000 (Trade Creditors) | VAT on purchases |
| `fx_gain_loss` | FX Gain/Loss | 7200 (FX Loss) | 4800 (FX Gain) | Currency differences |
| `usage_accrual` | Usage Accrual | 1100 (Trade Debtors) | 2500 (Deferred Income) | Metered usage |
| `wallet_topup` | Prepaid Wallet Top-Up | 1000 (Cash) | 2510 (Customer Deposits) | Customer prepayments |
| `journal_entry` | Manual Journal Entry | 8000 (Suspense) | 8000 (Suspense) | Manual journals |
| `reclassification` | Reclassification Entry | 8000 (Suspense) | 8000 (Suspense) | Account reclassifications |
| `opening_balance` | Opening Balance Entry | 8000 (Suspense) | 3300 (Retained Earnings) | Opening balances |
| `closing_entry` | Period Closing Entry | 8000 (Suspense) | 3300 (Retained Earnings) | Year-end close |
| `cost_allocation` | Cost Allocation | 8000 (Suspense) | 8000 (Suspense) | Cost distribution |
| `revenue_allocation` | Revenue Allocation | 8000 (Suspense) | 8000 (Suspense) | Revenue distribution |
| `intercompany` | Intercompany Charge | 8050 (Clearing) | 8050 (Clearing) | Intercompany entries |
| `tax_payment` | Tax Payment | 2300 (VAT Payable) | 1000 (Cash) | Tax remittance |
| `tax_adjustment` | Tax Adjustment | 7300 (Tax Expense) | 2300 (VAT Payable) | Tax provisions |
| `card_expense` | Default Card Expense | 7400 (Other Expenses) | (varies — card program's `gl_clearing_account_number`, or funding bank GL for debit cards) | Default for CARD_EXPENSE; the card transaction processor overrides the debit per-MCC at posting time |

**Note:** Account numbers shown are for IFRS template. US GAAP template uses different account numbers for some profiles.

---

## Transaction Type → Posting Profile Mappings

Selected standard mapping examples follow. Actual creation depends on the deployed template and eligible account configuration:

| Transaction Type | Posting Profile Type | Description |
|-----------------|---------------------|-------------|
| `AR_INVOICE` | customer | Customer invoice |
| `AR_CREDIT_MEMO` | customer | Customer credit note |
| `AR_DEBIT_MEMO` | customer | Customer debit memo |
| `RECURRING_INVOICE` | customer | Recurring billing |
| `USAGE_ACCRUAL` | usage_accrual | Metered usage accrual |
| `WALLET_TOPUP` | wallet_topup | Customer prepayment |
| `AP_INVOICE` | vendor | Vendor bill |
| `AP_CREDIT_MEMO` | vendor | Vendor credit note |
| `AP_DEBIT_MEMO` | vendor | Vendor debit memo |
| `AR_PAYMENT` | customer_payment | Customer payment |
| `AP_PAYMENT` | vendor_payment | Vendor payment |
| `JOURNAL_ENTRY` | journal_entry | Manual journal |
| `RECLASSIFICATION` | reclassification | Reclassification |
| `OPENING_ENTRY` | opening_balance | Opening balances |
| `CLOSING_ENTRY` | closing_entry | Period close |
| `INVENTORY_RECEIPT` | inventory_receipt | Goods receipt |
| `INVENTORY_SHIPMENT` | inventory_shipment | Goods shipment |
| `INVENTORY_ADJUSTMENT` | inventory_adjustment | Inventory adjustment |
| `BANK_DEPOSIT` | bank_deposit | Bank deposit |
| `BANK_WITHDRAWAL` | bank_withdrawal | Bank withdrawal |
| `BANK_TRANSFER` | bank_transfer | Inter-bank transfer |
| `BANK_FEE` | expense | Bank charges |
| `BANK_INTEREST` | revenue | Interest earned |
| `COST_ALLOCATION` | cost_allocation | Cost distribution |
| `REVENUE_ALLOCATION` | revenue_allocation | Revenue distribution |
| `INTERCOMPANY_CHARGE` | intercompany | Intercompany entry |
| `TAX_PAYMENT` | tax_payment | Tax remittance |
| `TAX_ADJUSTMENT` | tax_adjustment | Tax adjustment |
| `DEPRECIATION` | depreciation | Depreciation |
| `FOREIGN_EXCHANGE_GAIN` | fx_gain_loss | FX gain |
| `FOREIGN_EXCHANGE_LOSS` | fx_gain_loss | FX loss |
| `CARD_EXPENSE` | card_expense | Card transaction posted by `card_transaction_processor`. The agent overrides the debit account per-MCC; the credit account is the card program's `gl_clearing_account_number` (credit-card mode) or the funding bank's GL (debit-card mode). Profile is auto-created when a card program is created — see [Corporate Cards Management](corporate-cards-management.md). |
| `AP_REFUND` | (no profile required) | Vendor cash refund auto-detected by `bank_transaction_processor` when a credit line matches a prior debit to the same vendor (same merchant + amount within ±0.5%, last 90 days). Posts `DR Bank / CR <original counterpart account>` — the agent reads the counterpart from the original GL transaction's lines, so no posting profile is needed. Vendor/party linkage inherited from the original. See [Bank Statements Management](bank-statements-management.md). |
| `AR_REFUND` | (no profile required) | Mirror of `AP_REFUND` for customer refunds we issue. Posts `DR <original counterpart> / CR Bank`. |

**Note:** Multiple transaction types can share the same posting profile type (e.g., AR_INVOICE, AR_CREDIT_MEMO, AR_DEBIT_MEMO, and RECURRING_INVOICE all use the `customer` profile).

---

## How Posting Profiles Work

### During Onboarding

When a legal entity is created, the system automatically seeds:
1. **Posting profiles** from the COA template (IFRS: 35 profiles, US GAAP: 35)
2. **Transaction type mappings** linking each transaction type to its posting profile

When a **card program** is created later (via `card_program.create`), `CardProgramService._ensure_card_expense_posting_profile` also auto-creates the `CARD_EXPENSE` posting profile if one doesn't exist for that entity. Migration `368_seed_card_expense_posting_profiles.sql` back-fills the same profile for any existing card program that pre-dates this auto-seed behavior. See [Corporate Cards Management](corporate-cards-management.md) for the debit-vs-credit posting modes.

### During Transaction Posting

When a transaction is posted (e.g., an AR invoice):
1. System looks up `transaction_type_posting_profiles` for the transaction type
2. Finds the linked `posting_profile` with `is_default = true`
3. Reads the `debit_account_id` and `credit_account_id` from the profile
4. Creates journal lines using those GL accounts

### Profile Priority

Each mapping has a `priority` field (default: 100). When multiple profiles exist for the same transaction type, the one with the lowest priority number is used first. This enables scenario-specific overrides.

---

## Common Tasks

### 1. Check if All Transaction Types Have Profiles

```javascript
// List all transaction type mappings
query("transaction_type_posting_profile", filters={"legal_entity_id": 13})
// Verify count matches expected (35 for IFRS, 35 for US GAAP)
```

### 2. Verify a Specific Posting Profile's GL Accounts

```javascript
// Search for the customer posting profile
query("posting_profile", filters={"legal_entity_id": 13, "profile_type": "customer"})
// Check debit_account_number and credit_account_number are correct
```

### 3. Create a Custom Posting Profile

```javascript
// Example: Create a new expense profile for marketing expenses with auto-linkage
submit("posting_profile", "create", '{
    "legal_entity_id": 13,
    "profile_name": "Marketing Expenses",
    "profile_type": "expense",
    "debit_account_number": "6300",
    "credit_account_number": "1000",
    "description": "Marketing and advertising expenses",
    "is_default": false,
    "transaction_type_code": "BANK_FEE"
}')
```

### 4. Audit Posting Configuration

```javascript
// List all profiles to verify debit/credit account assignments
query("posting_profile", filters={"legal_entity_id": 13})

// Cross-reference with chart of accounts
query("account", query="", filters={"legal_entity_id": 13, "account_type": "asset"})
```

---

## Troubleshooting

### "No posting profile found for transaction type X"

The transaction type is not mapped to a posting profile. Check mappings:
```javascript
query("transaction_type_posting_profile", filters={"legal_entity_id": 13, "transaction_type_code": "AR_INVOICE"})
```

If no mapping exists, create a posting profile with `transaction_type_code` to auto-link:
```javascript
submit("posting_profile", "create", '{
    "legal_entity_id": 13,
    "profile_name": "AR Invoice Posting",
    "profile_type": "customer",
    "debit_account_number": "1100",
    "credit_account_number": "4000",
    "transaction_type_code": "AR_INVOICE",
    "is_default": true
}')
```

### "Cannot list posting profiles"

Use the entity registry tools:
```javascript
// Correct - use query
query("posting_profile", filters={"legal_entity_id": 13})

// Also correct - use search
query("posting_profile", query="customer")
```

Do NOT use deprecated tools `list_posting_profiles` or `get_posting_profile` — they are disabled.

### Posting Profile Has Wrong GL Accounts

List the profile to see current accounts:
```javascript
query("posting_profile", filters={"legal_entity_id": 13, "profile_type": "customer"})
```

**Option A — Update in place** (preferred):
```javascript
submit("posting_profile", "update", '{
    "posting_profile_id": 42,
    "legal_entity_id": 13,
    "debit_account_number": "1100",
    "credit_account_number": "4000"
}')
```

**Option B — Create new default** (old one remains but loses default):
```javascript
submit("posting_profile", "create", '{
    "legal_entity_id": 13,
    "profile_name": "Customer Receivables - Corrected",
    "profile_type": "customer",
    "debit_account_number": "1100",
    "credit_account_number": "4000",
    "is_default": true,
    "transaction_type_code": "AR_INVOICE"
}')
```

---

## Database Schema

### posting_profiles Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `legal_entity_id` | integer | Legal entity |
| `profile_type` | varchar | Category (customer, vendor, etc.) |
| `profile_name` | varchar | Display name |
| `debit_account_id` | bigint | FK to master_accounts |
| `credit_account_id` | bigint | FK to master_accounts |
| `description` | text | Profile description |
| `is_active` | boolean | Active status |
| `is_default` | boolean | Default for this type |
| `created_at` | timestamp | Creation time |
| `created_by` | integer | User who created |
| `updated_by` | integer | User who last updated |
| `updated_at` | timestamp | Last update time |

### transaction_type_posting_profiles Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `legal_entity_id` | integer | Legal entity |
| `transaction_type_code` | varchar | FK to system.transaction_types |
| `posting_profile_id` | integer | FK to posting_profiles |
| `priority` | integer | Priority (lower = higher priority) |
| `is_active` | boolean | Active status |
| `created_at` | timestamp | Creation time |

### Views (for querying)

- **`v_posting_profiles`** — Joins posting_profiles with master_accounts to show account numbers and names
- **`v_transaction_type_posting_profiles`** — Joins mappings with posting_profiles, master_accounts, and system.transaction_types

---

## Related Resources

- [Accounts Management](accounts-management.md) — Chart of accounts
- [Transaction Processing](transaction-processing.md) — How transactions use posting profiles
- [Tax Management](tax-management.md) — Tax-related posting profiles
- [Payroll Management](payroll-management.md) — Payroll posting profiles

### Header accounts (hardening branch, unreleased)

Profile create/update requires an active non-header account in the selected entity.
Do not choose a grouping/header account or infer posting permission from its name.
Template initialization skips a profile if any specified side is missing, inactive or
a header, exposing `summary.posting_profile_setup_gaps`; only deliberately empty sides
retain nullable bank-aware behavior. Resolve gaps with a reviewed eligible account,
not by toggling the header flag or guessing a child account. Existing profiles are not
silently repaired. The optional operator database guard protects both populated sides
and blocks a referenced account becoming a header, even under concurrent writes and
replication mode. AP/AR manual-entry scope activation remains separate and unfinished.

Dashboard connector setup now returns `postingProfileIssues`: connector success can
coexist with rejected profile mappings. It requires distinct active non-header
accounts in the connector entity and an active transaction type. Valid profile writes
are transactional with default replacement and type linking. Dashboard organization
copy validates populated account mappings and classification, preserves intentional
NULL sides and maps profile links by IDs. Its `entityConfigCopyIssue` is separate from
organization creation success. MCP organization copying now uses the same selection rules and exact profile-link
identity, with its own transactional Python service. Manual
permission, later account-classification changes and AP/AR scope remain separate work.


For `manage_organization(action="create_client")`, inspect `posting_profiles_copied`,
`posting_profile_copy_issue` and `t1_created`, not just `success`. A profile-copy failure
rolls back initial entity setup but does not undo the separately created organization,
schema or master configuration. Do not claim the client is ready or blindly repeat
creation using the same slug. Review the existing organization/setup state first;
automatic recovery of failed T1 setup is not implemented here. No source entity means
profiles were not copied and requires configuration; `copy_config=false` skips the step.


### Fixed-asset repair boundary

Do not infer an acquisition profile replacement from the profile name. Acquisition from
bills links already-posted source costs; capitalization uses explicit accounts; depreciation
and disposal resolve category accounts and operation-specific inputs. A seeded acquisition
mapping does not prove an executor or NULL-side fallback exists. Do not clear a header-account
profile side, choose an arbitrary leaf or change the header flag to make a guard pass.
Reviewed profile remapping remains outside the configuration-only account correction tool.


### Concurrent profile updates

The Python `posting_profile.update` executor locks the selected entity/profile row before
reading its current account pair. Pair validation, profile edits, default changes and the
optional transaction-type link write run in that transaction. An edit waiting behind another
edit rechecks the winning pair and entity scope; it cannot validate an obsolete pair and
then combine its change with a conflicting account edit. A failed link validation rolls
back the profile edit. This does not certify historical impact or authorize a source repair,
and it does not add this locking behavior to other profile writers.

### Operator replacement review

`review_posting_profile_replacement.py` is a read-only maintenance script, not an MCP apply
tool. It captures exact profile/target configuration, links and retained entity exposure;
`apply_supported` is always false and `approval` is null. Do not interpret successful capture
or empty configuration errors as approval. Explicit replacement master IDs must come from
reviewed accounting intent, not account names or a first matching leaf. Generic fallbacks,
party defaults, pending documents, historical treatment and cached consumers need review.


Standard IFRS/US GAAP onboarding excludes the generic `fixed_asset` acquisition profile and
`FIXED_ASSET_ACQUISITION` link. There is no registered transaction-post executor for that code.
Do not recreate the obsolete template entry through automatic configuration repair. Use the
supported [fixed-asset workflows](fixed-assets.md) and category account configuration.
Existing rows are preserved and require their own reviewed retirement/replacement decision.

The separate `apply_reviewed_profile_transition.py` (migration 681) supports audited
retirement of the unsupported acquisition profile or side replacement in an entity with no
retained transactions/settlements. It is privileged maintenance, not a public/MCP apply tool.
Never manufacture its exact-hash review, consumer-quiescence attestation or accounting reason.
Read-only review output alone is not an apply proposal. General historical profile replacement
and AP/AR activation remain unsupported by this procedure.

### Reviewed future-only FX profile replacement (unreleased, migration 696)

`replace_fx_future` in `apply_reviewed_profile_transition.py` supports an entity
with retained history. It changes only explicitly selected debit/credit master
account IDs on its single active default `fx_gain_loss` profile. Existing GL,
transactions and dated settlement history remain unchanged; later postings use
the reviewed mapping after cached consumers are drained or restarted.

Both resulting sides must be distinct, canonical, active, nonheader P&L accounts.
Unposted or unknown-state documents, explicit transaction-type links, other direct
profile references, competing active FX profiles and missing sides block this
procedure. FX readers use entity-effective account numbers, so reviewed number
overrides are supported. Missing, ambiguous, inactive, header or non-P&L mappings
are refused.

A real operator review must approve the exact proposal hash, confirm consumer
quiescence and specify `historical_treatment: "preserve_booked_gl"`. Apply locks
the configuration and financial sources, rechecks the complete review snapshot,
records a permanent audit, and verifies that financial history did not change.
Any mismatch rolls back the profile update and audit together. Regenerate stale
proposals; never edit a saved proposal to remove blockers. A repeated identical
apply reports the existing receipt and whether current configuration still matches.

This does not reclassify old balances or replace AP/AR control accounts. Correcting
old postings, partial settlement allocations and broader historical transitions
remain separate work. No production profile or aging membership changes merely
by installing the migration. Undo requires a new reviewed cutover; do not delete
the audit or assume restoring configuration reverses postings made since cutover.

FX profile reader alignment (unreleased): `FXPostingService` now resolves both
profile master IDs through `v_accounts_effective` for the selected entity and
requires unique effective account numbers. Multiple active default profiles or
duplicate effective identities are errors. Missing profiles still return
unconfigured; constructor fallback numbers cannot replace invalid profile sides.
A gain may credit a valid expense account. Deploy this reader together with the
updated transition service before approving cutovers that use number overrides.
This is a code change; migration 696 remains unchanged.


### Posting-profile request reference reads (QA branch, not deployed)

For installed `create_posting_profile` and `fix_posting_profile_accounts`
requests, supplied `bank_account_id` values must resolve to the request entity's
bank account. Supplied `existing_posting_profile_id` and returned
`created_entity_id` values must resolve through the existing posting-profile
read view in that entity. If the returned ID carries `entity_type`, it must be
`posting_profile`. Explicit `legal_entity_id` must agree with the request.
The response inherits the originating action for these checks.

Missing, malformed or foreign explicit references withhold Admin/MCP task rows,
counts, pages, thread siblings and supported virtual execution metadata. These
hints remain optional: Bill and FX producers legitimately omit bank accounts,
and repair requests can lack an identified profile. Inactive profiles remain
readable history. Existing account/profile read policies add no new domain grant;
a configurable transaction-type hint is not treated as a stored transaction.
Unrelated actions retain their own contracts.

Read checks do not establish profile repair completion, current active account
configuration, copied bank samples, free-text descriptions or original email
payload authority. Those producer snapshots and hosted acceptance remain open;
mutation and completion verification still apply independently.


Bill recovery task reads (QA branch, not deployed): `fix_default_expense_account`
is Bill-specific and requires AP read access. A posting-profile create task with
an original Bill payload also requires AP access; its explicit entity and known
nested references are checked through the shared task graph. Generic profile
requests without that payload retain the existing read policy. Profile repair
completion and retry authority remain separate from read access.
