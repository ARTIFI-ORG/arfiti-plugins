

## Card purchase policy

Use the backend purchase workspace and shared matching decision; do not implement a competing card matcher in conversation. Preserve provider rows and show net purchase spend. Reference conflicts and competing candidates require review. A paid/settled item can still lack documentation; attach missing source evidence to the existing bill. Evidence review, waiver and grouping use `card_purchase.manage` with current version, evidence fingerprint and reason. Never infer write-off authority from matching tolerance.

Receipt follow-up belongs to the purchase obligation, with one owner and deduplicated reminder stages. Automation and delivery are report-only until the entity rollout settings are explicitly enabled. Statement coverage and opening/movement/closing balance controls must pass independently of agent match counts. August deletion/replay requires its own reviewed manifest and explicit authorization through transaction.delete; implementation permission does not authorize it.

Legacy payment-pass descriptions below apply to non-card AP/AR behavior. Card rows use the shared purchase policy and cannot use nearest-date refund pairing, fuzzy amount identity or adjusting-journal workarounds.

# Transaction Processing

> **MSEO release contract:** Posting freezes resolved line dimensions before approval. Defaults cannot reclassify approved lines, and reversal copies the original assignments and provenance. New dimension writers must use the shared typed boundary. See the dimensions-management resource for assignment, approval and compatibility rules.

This resource explains how to post transactions in the AI-Native ERP system using the V5 unified ledger.

---

## Overview

The V5 Unified Ledger uses a **single universal workflow** for ALL transaction posting:

```
Post:    submit("transaction", "post", {...})    → Router → Type-Specific Executor → GL Posting → Complete
Update:  submit("transaction", "update", {...})  → TransactionUpdateExecutor → Header/Line Update → Complete
Delete:  submit("transaction", "delete", {...})  → TransactionDeleteExecutor → Snapshot + Hard DELETE → Complete
Reverse: submit("transaction", "reverse", {...}) → TransactionReverseExecutor → Reversing GL Lines → Complete
```

**Key Concepts:**
- **One workflow** (`transaction.post`) handles ALL transaction types
- **One update workflow** (`transaction.update`) edits ANY posted transaction (header fields and/or GL lines)
- **One delete workflow** (`transaction.delete`) permanently removes ANY posted transaction (with audit trail)
- **One reversal workflow** (`transaction.reverse`) reverses ANY posted transaction
- **Router pattern** automatically routes to correct executor based on `transaction_type_code`
- **No separate tables** for bills, invoices, payments - all stored in `transactions` table
- **Automatic GL posting** via executors
- **Dimension support** for reporting and routing
- **Approval lanes** (green/yellow/red) based on risk

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

---

## Payment-to-invoice linking lifecycle (READ FIRST)

When you post or modify a payment, three different code paths can be involved.
Pick the correct one — mixing them up causes either silent data drift (paid
status doesn't update) or noisy validator errors ("Cannot delete X with
non-zero amount").

**The three flows**:

1. **Bank statement processing** — used by `bank_transaction_processor`. Each
   bank statement line becomes one transaction (`BANK_FEE`, `AP_PAYMENT`,
   `AR_PAYMENT`, etc.). Linked to the line via
   `bank_statement_lines.gl_transaction_id`. **Does NOT update any invoice's
   `amount_paid`** — payments posted this way are *standalone* until flow 3
   reconciles them.
2. **Payment proposal** — `payment_proposal_agent` builds a batch from open
   invoices. `bank_payment_batch_lines.source_transaction_id` points at the
   invoice (set at proposal time). At confirmation, the executor is called
   with `applications: [{invoice_id, amount}, …]`, which updates the
   invoice's `amount_paid` / `amount_due` / `status` directly on the
   `transactions` row, and `posted_transaction_id` is written back onto the
   batch line. **Linked end-to-end before reconciliation runs.**
3. **Reconciliation** — `reconciliation_agent` (scopes: `vendor`, `customer`,
   `card` — **NOT `bank`**) does n:n matching of standalone payments (from
   flow 1) against open invoices. Writes a `reconciliation_items` row
   (`source_transaction_id` = payment, `target_transaction_id` = invoice),
   then runs the same in-place invoice update that flow 2 does at
   confirmation time.

### `applications` payload — what it actually does

The AP/AR payment executors accept `applications: [{invoice_id, amount}, …]`.
For each entry: `invoice.amount_paid += amount`, `invoice.amount_due -= amount`,
`invoice.status = 'paid' | 'partial'`. **No separate `payment_applications`
table is written** (that table was dropped in migration 262). Use the
parameter when posting a payment that pays known invoices (flow 2). Omit it
for standalone bank-derived payments (flow 1) — reconciliation will link them
later.

### Standalone-payment teardown (the most common cleanup case)

When a `bank_transaction_processor` import goes wrong and you need to delete
the resulting `AP_PAYMENT` / `AR_PAYMENT` transactions, `transaction.delete`
will refuse by default with: *"Cannot delete X with non-zero amount …"*.
This is correct — silent loss of cash data is a footgun. Five legitimate
options:

| Operation | When | Effect |
|---|---|---|
| `submit('transaction', 'reverse', …)` | Real money moved, production data | Posts an offsetting `REV-…` entry. Original stays. |
| `submit('transaction', 'cancel', …)` | Unposted documents only | `status='void'`, audit row written. Posted documents require an explicit dated reversal. |
| `submit('transaction', 'delete', { …, force: true })` | Test / agent-cleanup data only | Hard-delete bypassing the non-zero-amount block. Audit-logged. |
| `submit('reconciliation', 'auto_match', { scope: 'vendor' \| 'customer', … })` | The payment is real and an invoice exists | Links payment to invoice via `reconciliation_items`. **No deletion.** |
| `submit('bank_statement', 'void', …)` then `submit('bank_statement', 'delete', …)` | The whole statement was a mistake | Reverses every linked GL transaction, then hard-deletes the statement (CASCADE removes lines). Clean up the resulting `REV-…` rows by deleting either half — `reversal_pair_deleted` removes both. |

**Don't**: try `transaction.delete` without `force: true` on a non-zero
payment and conclude there's a `payment_applications` table somewhere — there
isn't. The error wording was historical leftover; the real constraint is
`amount > 0`.

---

## Transaction Types

### Accounts Payable (AP)

| Type Code | Description | When to Use |
|-----------|-------------|-------------|
| `AP_INVOICE` | Vendor bill / purchase invoice | Recording bills from vendors for goods or services |
| `AP_CREDIT_MEMO` | Vendor credit note | Vendor returns, price adjustments, credits received |
| `AP_DEBIT_MEMO` | Vendor debit memo | Additional charges from vendor, purchase adjustments |
| `AP_PAYMENT` | Vendor payment | Paying vendor bills |

### Accounts Receivable (AR)

| Type Code | Description | When to Use |
|-----------|-------------|-------------|
| `AR_INVOICE` | Customer invoice | Billing customers for goods or services |
| `AR_CREDIT_MEMO` | Customer credit note | Customer refunds, return allowances |
| `AR_DEBIT_MEMO` | Customer debit memo | Additional charges to customer |
| `AR_PAYMENT` | Customer payment receipt | Recording payments received from customers |
| `RECURRING_INVOICE` | Recurring customer billing | Automated periodic customer invoicing |

### Banking

| Type Code | Description | When to Use |
|-----------|-------------|-------------|
| `BANK_DEPOSIT` | Bank deposit | Recording deposits to bank account |
| `BANK_WITHDRAWAL` | Bank withdrawal | Recording withdrawals from bank account |
| `BANK_TRANSFER` | Inter-bank transfer | Moving funds between bank accounts |
| `BANK_FEE` | Bank charges | Recording bank service fees and charges |
| `BANK_INTEREST` | Bank interest earned | Recording interest income from bank |

### Stripe Payment Processing

| Type Code | Description | When to Use |
|-----------|-------------|-------------|
| `STRIPE_CHARGE` | Stripe payment received | Customer card payment via Stripe |
| `STRIPE_REFUND` | Stripe refund issued | Refund processed through Stripe |
| `STRIPE_PAYOUT` | Stripe payout to bank | Stripe settlement to bank account |
| `STRIPE_FEE` | Stripe processing fee | Stripe transaction fees |

### Journal & General Ledger

| Type Code | Description | When to Use |
|-----------|-------------|-------------|
| `JOURNAL_ENTRY` | Manual GL entry | Adjustments, accruals, reclassifications, corrections |
| `OPENING_ENTRY` | Opening balance entry | Setting up opening balances for new periods or entities |
| `CLOSING_ENTRY` | Period closing entry | Year-end income summary close to retained earnings |

> **OPENING_ENTRY: Do NOT post via `submit("transaction", "post")`.**
> Always use `manage_imports("opening_balances", ...)` or `manage_imports("opening_balances_with_subledger", ...)` instead.
> These tools handle validation, auto-balancing, fiscal period checks, and optional subledger records (individual AR/AP items, fixed assets).
> See [Bulk Import: Opening Balance](bulk-import.md#opening-balance-import) for the complete workflow.
| `RECLASSIFICATION` | Account reclassification | Moving balances between GL accounts |

### Fixed Assets

> **Note:** Fixed asset transactions are NOT posted via `transaction.post`. They are handled by dedicated fixed asset workflows:
> - `fixed_asset.acquire_from_bill` — Link asset to a source bill/transaction
> - `fixed_asset.capitalize_expense` — Reclassify expense as asset (posts GL: DR Asset, CR Expense)
> - `fixed_asset.capitalize_cwip` — Capitalize construction-in-progress (posts GL: DR Asset, CR CWiP)
> - `fixed_asset.dispose` — Dispose of asset (posts GL: DR Cash/AccumDepr/Loss, CR Asset)
> - `fixed_asset_depreciation.schedule` + `fixed_asset_depreciation.process` — Run depreciation (posts GL: DR Depr Expense, CR Accum Depr)
>
> See the [Fixed Assets Management](fixed-assets.md) resource for details.

### Tax

| Type Code | Description | When to Use |
|-----------|-------------|-------------|
| `TAX_PAYMENT` | Tax liability remittance | Paying VAT/sales tax to tax authority |
| `TAX_ADJUSTMENT` | Tax provision adjustment | Correcting tax provisions or liabilities |

### Allocations & Intercompany

| Type Code | Description | When to Use |
|-----------|-------------|-------------|
| `COST_ALLOCATION` | Cost distribution | Allocating shared costs across departments/entities |
| `REVENUE_ALLOCATION` | Revenue distribution | Allocating shared revenue across departments/entities |
| `INTERCOMPANY_CHARGE` | Intercompany transaction | Charges between legal entities in same organization |

### Foreign Exchange

| Type Code | Description | When to Use |
|-----------|-------------|-------------|
| `FOREIGN_EXCHANGE_GAIN` | FX gain | Realized gain from currency fluctuations |
| `FOREIGN_EXCHANGE_LOSS` | FX loss | Realized loss from currency fluctuations |

### Revenue & Usage

| Type Code | Description | When to Use |
|-----------|-------------|-------------|
| `USAGE_ACCRUAL` | Metered usage accrual | Accruing revenue for metered/usage-based billing |
| `WALLET_TOPUP` | Prepaid wallet top-up | Customer prepayment to wallet/deposit |

### Loans & Equity

| Type Code | Description | When to Use |
|-----------|-------------|-------------|
| `LOAN_DISBURSEMENT` | Loan given to third party | Recording a loan disbursement to a borrower |
| `LOAN_REPAYMENT` | Loan principal received back | Recording receipt of loan repayment from borrower |
| `OWNER_DISTRIBUTION` | Profit/capital distribution to owners | Recording dividend or equity distribution to shareholders |
| `CAPITAL_CONTRIBUTION` | Capital injection from owners | Recording cash or asset contribution by shareholders |

### Payroll

| Type Code | Description | When to Use |
|-----------|-------------|-------------|
| `PAYROLL` | Payroll posting | Recording payroll transactions (salary, taxes, deductions) |

### Inventory

| Type Code | Description | When to Use |
|-----------|-------------|-------------|
| `INVENTORY_ADJUSTMENT` | Inventory adjustment | Write-downs, shrinkage, count adjustments |

### Other

| Type Code | Description | When to Use |
|-----------|-------------|-------------|
| `EXPENSE_REPORT` | Expense report | Employee expense reimbursements |
| `REIMBURSEMENT_PAYOUT` | Reimbursement payout | Bank payout for employee reimbursement |

---

## How to Post Transactions

### Basic Pattern

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="transaction", operation="post")

// Step 2: Submit with discovered fields
submit("transaction", "post", {
  "transaction_type_code": "<TYPE_CODE>",
  "legal_entity_id": <entity_id>,
  "currency_code": "<ISO_4217>",           // REQUIRED for all transaction types
  // Type-specific fields...
  "lines": [...]
})
// Tip: Use validate_only=true to check payload before submitting
```

### Per-Type Required Fields Summary

Each transaction type requires different header and line fields. The table below summarizes the key requirements. Always call `get_submissions(action='schema', object_type="transaction", operation="post")` for the authoritative list.

| Type Code | Required Header Fields | Required Line Fields |
|-----------|----------------------|---------------------|
| `AP_INVOICE` | `vendor_id`, `invoice_date`, `due_date`, `currency_code`, `description` | `account_number` or `item_id`, `quantity`, `unit_price` or `amount`, `tax_code` |
| `AR_INVOICE` | `customer_id`, `invoice_date`, `due_date`, `currency_code`, `description` | `account_number` or `item_id`, `quantity`, `unit_price` or `amount`, `tax_code` |
| `AP_CREDIT_MEMO` | `vendor_id`, `original_transaction_id`, `reference_number`, posting/document dates, original invoice currency, `description` | `account_number` or `item_id`, `quantity`, `unit_price` or `amount`, `tax_code` |
| `AR_CREDIT_MEMO` | `customer_id`, `invoice_date`, `currency_code`, `description` | `account_number` or `item_id`, `quantity`, `unit_price` or `amount`, `tax_code` |
| `AP_PAYMENT` | `vendor_id`, `currency_code` | `account_number`, `amount` |
| `AR_PAYMENT` | `customer_id`, `currency_code` | `account_number`, `amount` |
| `JOURNAL_ENTRY` | `fiscal_period_id`, `currency_code`, `description` | `account_number`, `debit`, `credit` (must balance) |
| `BANK_DEPOSIT` | `currency_code` | `account_number`, `debit`, `credit` |
| `BANK_WITHDRAWAL` | `currency_code` | `account_number`, `debit`, `credit` |
| `BANK_TRANSFER` | `currency_code` | `account_number`, `debit`, `credit` |
| `BANK_FEE` | `currency_code` | `account_number`, `debit`, `credit` |
| `TAX_PAYMENT` | `currency_code` | `account_number`, `debit`, `credit` |

**All types** also require `transaction_type_code`, `legal_entity_id`, `transaction_date`, and `currency_code` at the header level.

> **CRITICAL -- Line field differences by transaction type:**
> - **Journal Entries** (`JOURNAL_ENTRY`, `OPENING_ENTRY`, `CLOSING_ENTRY`, `RECLASSIFICATION`) and **Banking** (`BANK_DEPOSIT`, `BANK_WITHDRAWAL`, `BANK_TRANSFER`, `BANK_FEE`): Lines use `debit` and `credit` fields. Each line must have either a debit or a credit (not both, not neither). Do NOT use `amount` -- it will be rejected.
> - **AP/AR Invoices and Credit/Debit Memos** (`AP_INVOICE`, `AR_INVOICE`, etc.): Lines use `quantity` + `unit_price` or `amount`, plus `tax_code`. Do NOT use `debit`/`credit`.
> - **Payments** (`AP_PAYMENT`, `AR_PAYMENT`): Lines use `amount` and `account_number`.
>
> **Common mistake:** Using `amount` on journal entry lines. Journal entries require explicit `debit`/`credit` fields. The system will reject journal entry lines that use `amount` instead.

### AP Invoice (Vendor Bill)

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

**CRITICAL: Tax codes are REQUIRED for all AP invoices.** Every line item must include a valid `tax_code` to ensure correct VAT/tax calculation and compliance. Before posting any bill, look up the available tax codes using `query("tax_code", filters={"is_active": true})`.

**Required Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `transaction_type_code` | string | Must be `"AP_INVOICE"` |
| `legal_entity_id` | integer | Legal entity ID |
| `vendor_id` | integer | Vendor ID (lookup by name if needed) |
| `transaction_date` | string | Transaction date (YYYY-MM-DD) |
| `invoice_date` | string | Invoice date (YYYY-MM-DD) |
| `due_date` | string | Due date (YYYY-MM-DD) |
| `description` | string | Transaction description |
| `currency_code` | string | Currency code (EUR, USD, etc.) |
| `lines` | array | At least one line item |

**Optional Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `reference_number` | string | Vendor invoice number |
| `dimensions` | object | Header-level dimensions |
| `payment_term_code` | string | Payment terms code |

**Example 1: Domestic Purchase with VAT (Estonia)**
```javascript
submit("transaction", "post", {
  "transaction_type_code": "AP_INVOICE",
  "legal_entity_id": 10,
  "vendor_id": 123,
  "transaction_date": "2025-01-15",
  "invoice_date": "2025-01-15",
  "due_date": "2025-02-14",
  "reference_number": "INV-2025-001",
  "description": "Office supplies from local vendor",
  "currency_code": "EUR",
  "dimensions": {
    "cost_center": "CC-1000",
    "location": "EE"
  },
  "lines": [
    {
      "description": "Printer paper and toner",
      "quantity": 10,
      "unit_price": 25.00,
      "account_number": "6200",
      "tax_code": "EU-EE-STD",
      "dimensions": {
        "cost_center": "CC-1000",
        "location": "EE"
      }
    }
  ]
})
```

**Example 2: EU B2B Purchase (Reverse Charge)**
```javascript
submit("transaction", "post", {
  "transaction_type_code": "AP_INVOICE",
  "legal_entity_id": 10,
  "vendor_id": 456,
  "transaction_date": "2025-01-20",
  "invoice_date": "2025-01-18",
  "due_date": "2025-02-17",
  "reference_number": "DE-2025-0042",
  "description": "Software license from German vendor",
  "currency_code": "EUR",
  "lines": [
    {
      "description": "Annual software license",
      "quantity": 1,
      "unit_price": 1200.00,
      "account_number": "6200",
      "tax_code": "EU-EE-IC-ACQ",
      "dimensions": {
        "cost_center": "CC-2000",
        "location": "EE"
      }
    }
  ]
})
```

**Example 3: Non-EU Purchase (Reverse Charge)**
```javascript
submit("transaction", "post", {
  "transaction_type_code": "AP_INVOICE",
  "legal_entity_id": 10,
  "vendor_id": 789,
  "transaction_date": "2025-01-25",
  "invoice_date": "2025-01-22",
  "due_date": "2025-02-21",
  "reference_number": "US-INV-5678",
  "description": "Cloud hosting services from US provider",
  "currency_code": "EUR",
  "lines": [
    {
      "description": "Monthly cloud hosting - January",
      "quantity": 1,
      "unit_price": 500.00,
      "account_number": "6200",
      "tax_code": "EU-EE-RC-FOREIGN",
      "dimensions": {
        "cost_center": "CC-3000",
        "location": "EE"
      }
    }
  ]
})
```

### Tax Code Selection Guide

**IMPORTANT:** Always look up available tax codes before posting: `query("tax_code", filters={"is_active": true})`

The correct tax code depends on the transaction scenario:

| Scenario | Tax Code | Rate | Description |
|----------|----------|------|-------------|
| Domestic purchase (standard) | `EU-EE-STD` | 24% | Standard Estonian VAT on local purchases (from 1 July 2025) |
| Domestic purchase (accommodation) | `EU-EE-RED13` | 13% | Accommodation, with or without breakfast (from 1 January 2025) |
| Domestic purchase (reduced) | `EU-EE-RED` | 9% | Reduced rate (books, medicines, press publications) |
| Zero-rated domestic | `EU-EE-ZERO` | 0% | Zero-rated supplies |
| VAT-exempt purchase | `EU-EE-EXEMPT` | 0% | Exempt supplies (financial services, insurance) |
| EU B2B purchase (intra-community) | `EU-EE-IC-ACQ` | 24% | Intra-community acquisition — reverse charge applies |
| EU B2B sale (intra-community) | `EU-EE-IC-SUPPLY` | 0% | Intra-community supply — zero-rated |
| Non-EU services (reverse charge) | `EU-EE-RC-FOREIGN` | 24% | Services from a non-EU supplier — buyer self-assesses VAT |
| Import VAT paid at customs | `EU-EE-IMPORT` | 24% | Import VAT on the customs decision for goods from outside the EU; deducted, not a reverse charge |
| Export outside EU | `EU-EE-ZERO` | 0% | Export of goods/services outside EU |
| Historical rate (Jan 2024 – Jun 2025) | `EU-EE-STD-22` | 22% | Old standard rate; only for transactions and credit invoices dated in that window |
| Historical rate (until Dec 2023) | `EU-EE-OLD-20` | 20% | Old standard rate; only for transactions and credit invoices dated in that window |
| Transitional press rate | `EU-EE-RED5-PRESS` | 5% | Sales only: press publications under the cash-accounting transition (VAT Act § 46(27)); otherwise press is 9% |

These are the codes onboarding creates for an Estonian entity. Organisations onboarded
earlier may lack `EU-EE-RED13` or `EU-EE-RC-FOREIGN`, or hold an `EU-EE-RC` code whose
meaning varies by organisation — check the entity's codes before posting. Domestic reverse
charge under VAT Act § 41¹ (immovables, scrap metal, precious metal) is not seeded yet; an
organisation that needs it adds the code itself with `tax_scope: "domestic"`, once the bill
agent's reverse-charge code selection respects scope.

**Rules of thumb:**
- **Local Estonian vendor** → Use `EU-EE-STD` (24%) for most purchases
- **EU vendor (B2B with VAT number)** → Use `EU-EE-IC-ACQ` (reverse charge)
- **Non-EU vendor (services)** → Use `EU-EE-RC-FOREIGN` (reverse charge)
- **Non-EU vendor (goods import)** → The supplier's invoice carries no Estonian VAT; the import VAT on the customs decision uses `EU-EE-IMPORT` (24% goods; ask for goods at another rate)
- **When unsure** → Look up tax codes first: `query("tax_code", filters={"is_active": true})`

### AR Invoice (Customer Invoice)

**Required Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `transaction_type_code` | string | Must be `"AR_INVOICE"` |
| `legal_entity_id` | integer | Legal entity ID |
| `customer_id` | integer | Customer ID |
| `transaction_date` | string | Transaction date (YYYY-MM-DD) |
| `invoice_date` | string | Invoice date (YYYY-MM-DD) |
| `due_date` | string | Due date (YYYY-MM-DD) |
| `description` | string | Transaction description |
| `currency_code` | string | Currency code |
| `lines` | array | At least one line item |

**Example:**
```javascript
submit("transaction", "post", {
  "transaction_type_code": "AR_INVOICE",
  "legal_entity_id": 10,
  "customer_id": 456,
  "transaction_date": "2025-01-15",
  "invoice_date": "2025-01-15",
  "due_date": "2025-02-14",
  "description": "Consulting services - January",
  "currency_code": "EUR",
  "reference_number": "INV-2025-0123",
  "lines": [
    {
      "description": "Consulting services - January",
      "quantity": 40,
      "unit_price": 150.00,
      "account_number": "4100",
      "tax_code": "EU-EE-STD",
      "dimensions": {
        "cost_center": "CC-1000",
        "location": "EE"
      }
    }
  ]
})
```

### Journal Entry

**Journal-entry tax routing:** automatic tax on `expense` and `cogs` lines uses
`purchase_account_number`; `revenue` lines use `sales_account_number`. Each falls
back only to the effective `default_tax_account_number`, never to the opposite
side. The account type determines the side even for a reversing line: a credit
to an expense reverses input VAT. Entity tax-code overrides apply. Other account
types retain the configured default; balance-sheet classification alone does
not identify a purchase or sale. For those adjustments, select a tax code with
the intended default or enter the reviewed tax lines explicitly. Missing or
inactive effective codes and missing, inactive or header tax accounts refuse
the journal atomically. This changes new postings only; it does not reclassify
historical journals or add reverse-charge/non-recoverable-tax support.


**Required Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `transaction_type_code` | string | Must be `"JOURNAL_ENTRY"` |
| `legal_entity_id` | integer | Legal entity ID |
| `transaction_date` | string | Entry date (YYYY-MM-DD) |
| `fiscal_period_id` | integer | Fiscal period ID (required, no auto-lookup) |
| `description` | string | Transaction description |
| `currency_code` | string | Currency code |
| `lines` | array | At least 2 lines (debits = credits) |

**Optional Party Fields (header — single party):**
| Field | Type | Description |
|-------|------|-------------|
| `vendor_id` | integer | Link JE to a vendor (for vendor-related adjustments) |
| `customer_id` | integer | Link JE to a customer (for customer-related adjustments) |
| `party_type` | string | Party type: `"vendor"`, `"customer"`, `"employee"`, etc. |
| `party_id` | integer | Generic party ID (when using party_type) |

**Optional Party Fields (per line — multi-party):**
For transactions touching multiple vendors/customers/employees (payroll, AR offsets, multi-party JEs), include partner refs on individual lines:

| Per-line field | Type | Use when |
|----------------|------|----------|
| `vendor_id` | integer | This specific line is a payable to / expense for a vendor |
| `customer_id` | integer | This specific line is a receivable from / credit to a customer |
| `employee_id` | integer | This specific line is salary/expense/payable for a specific employee |
| `project_id` | integer | This specific line belongs to a project |

Header-level fields cover the simple "one transaction, one party" case. Line-level fields enable AP-aging-by-vendor / AR-aging-by-customer reports to roll up payroll-derived liabilities, multi-vendor JEs, etc. correctly. When both are populated, line-level wins for reporting.

> **Note:** Header-level party fields are also supported on all banking transaction types (BANK_FEE, BANK_DEPOSIT, BANK_WITHDRAWAL, LOAN_DISBURSEMENT, LOAN_REPAYMENT, OWNER_DISTRIBUTION, CAPITAL_CONTRIBUTION, etc.).

**Example:**
```javascript
submit("transaction", "post", {
  "transaction_type_code": "JOURNAL_ENTRY",
  "legal_entity_id": 10,
  "transaction_date": "2025-01-31",
  "fiscal_period_id": 45,
  "description": "January accrued expenses",
  "currency_code": "EUR",
  "reference_number": "JE-2025-0015",
  "lines": [
    {
      "account_number": "6500",
      "debit": 5000.00,
      "credit": 0,
      "description": "Accrued utilities"
    },
    {
      "account_number": "2100",
      "debit": 0,
      "credit": 5000.00,
      "description": "Accrued utilities payable"
    }
  ]
})
```

**Example with line-level partner refs (multi-vendor JE):**
```javascript
submit("transaction", "post", {
  "transaction_type_code": "JOURNAL_ENTRY",
  "legal_entity_id": 10,
  "transaction_date": "2025-01-31",
  "fiscal_period_id": 45,
  "description": "Reclassify January accruals across vendors",
  "currency_code": "EUR",
  "lines": [
    {"account_number": "2100", "debit": 1200, "credit": 0,
     "description": "Reverse accrual — Vendor A", "vendor_id": 101},
    {"account_number": "2100", "debit": 800, "credit": 0,
     "description": "Reverse accrual — Vendor B", "vendor_id": 102},
    {"account_number": "6500", "debit": 0, "credit": 2000,
     "description": "Net adjustment"}
  ]
})
```

---

## How to Reverse Transactions

To reverse any posted transaction, use `transaction.reverse`:

```javascript
submit("transaction", "reverse", {
  "transaction_id": 71,
  "legal_entity_id": 4,
  "reversal_date": "2024-12-31",
  "reversal_reason": "Replacing with corrected opening balances"
})
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `transaction_id` | integer | ID of the posted transaction to reverse |
| `legal_entity_id` | integer | Legal entity the transaction belongs to |
| `reversal_date` | string | Date for the reversal (YYYY-MM-DD) |
| `reversal_reason` | string | Why the transaction is being reversed |

### What Happens

1. Original transaction status changes to `reversed`
2. A new reversing transaction is created with swapped DR/CR GL lines — document AND functional/reporting amounts, so every report nets the pair (reversals written before 2026-09-08 carried document amounts only and were invisible to reports; repaired 2026-10-01)
3. Dimensions are copied from the original to the reversing transaction
4. Both transactions are linked via `reversed_by_id` / `reversal_of_id`
5. A reversed transaction can no longer be voided; a reversal is read under the permission of the transaction it reverses (a payroll reversal needs `payroll:read`)

### Success Response

```json
{
  "success": true,
  "reversing_transaction_id": 85,
  "reversing_transaction_number": "REV-000012",
  "original_transaction_id": 71,
  "original_transaction_number": "JE000001",
  "gl_lines_created": 4,
  "dimensions_copied": 2
}
```

### Validation Errors

```json
{
  "success": false,
  "errors": [
    "Transaction 999 not found"
  ]
}
```

Other possible validation errors:
- Transaction already reversed
- Transaction has no GL lines to reverse
- Invalid reversal_date format
- Invoice or memo has live payment applications (named with amounts) — unapply them with `reconciliation.unmatch` or reverse the payment first; reversing a payment unapplies its own applications

---

## How to Update Posted Transactions

To edit a posted transaction's header fields and/or replace its GL lines, use `transaction.update`:

### Header-Only Update (no GL impact)

```javascript
submit("transaction", "update", {
  "transaction_id": 123,
  "legal_entity_id": 10,
  "description": "Corrected description",
  "reference_number": "INV-2025-0042",
  "edit_reason": "Typo in original description"
})
```

### Custom Fields (any period)

Organisations define their own document fields (`query("custom_field")`,
`applies_to` contains `transaction`; `transaction_types` narrows a field to
named types, otherwise it applies to AR/AP invoices and credit notes and
journal entries). Set them at posting with `"custom_fields": {"key": value}`
on `transaction.post`. To correct one afterwards, send only the fields:

```javascript
submit("transaction", "update", {
  "transaction_id": 123,
  "legal_entity_id": 10,
  "custom_fields": {"po_reference": "PO-4471"},
  "custom_fields_clear": ["approved_by"]
})
```

A custom-fields-only update (optionally with `edit_reason`) is allowed in an
open, closed or VAT-locked period and changes nothing else; the ledger
activity records the old and new values. A journal held by a bank or card
match is refused: set its custom fields when posting.
Combined with other fields it follows the normal update restrictions below.
Reversals copy the values. Never put these facts in `description` or
`metadata`. Filter with `query("transaction", filters={"custom_fields.<key>": value})`.
All rules (register, types, required fields, transactions, filters, import, merge): the custom-fields resource; full contract `docs/GUIDES/GUIDE_CUSTOM_FIELDS.md`.

### Full Line Replacement (GL lines rewritten)

```javascript
submit("transaction", "update", {
  "transaction_id": 123,
  "legal_entity_id": 10,
  "lines": [
    {"account_number": "6100", "debit": 800, "credit": 0, "description": "Office supplies"},
    {"account_number": "2000", "debit": 0, "credit": 800, "description": "AP - vendor"}
  ],
  "edit_reason": "Wrong amount on original posting"
})
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `transaction_id` | integer | ID of the posted transaction to edit |
| `legal_entity_id` | integer | Legal entity the transaction belongs to |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | New transaction description |
| `reference_number` | string | New reference number |
| `transaction_date` | string | New transaction date (YYYY-MM-DD) — fiscal period auto-updated |
| `due_date` | string | New due date (YYYY-MM-DD) |
| `dimensions` | object | New header-level dimensions |
| `lines` | array | Full replacement of GL lines (min 2, debits must equal credits) |
| `custom_fields` | object | Custom field values to set (patch; keys left out are unchanged) |
| `custom_fields_clear` | array | Custom field keys to empty |
| `edit_reason` | string | Reason for the edit (recommended for audit trail) |

### What Happens

1. **Header-only update**: Only the provided header fields are changed; GL lines remain untouched
2. **Line replacement**: If `lines` is provided, ALL existing GL lines are deleted and replaced with the new lines
3. **Fiscal period auto-update**: If `transaction_date` changes, the fiscal period is automatically re-resolved
4. **Bank auto-unmatch**: If the transaction amount changes and the transaction was matched to a bank statement line, the match is automatically removed
5. **AP/AR amount_due recalculation**: If an invoice's amount changes, `amount_due` is recalculated based on `amount_paid`

### Restrictions

- Transaction must be in `posted` status (not reversed, cancelled, or draft)
- Transaction must not have been reversed (`reversed_by_id` must be NULL)
- The fiscal period for the transaction date must be open (not closed) — except an update of custom fields only
- If changing `transaction_date`, the new period must also be open
- **AP/AR invoices with payments**: Line edits are blocked if the invoice has partial/full payments applied — only header fields can be updated
- **AP/AR payments**: Line/amount edits are blocked if the payment has been applied to invoices

### Success Response

```json
{
  "success": true,
  "transaction_id": 123,
  "transaction_number": "JE000001",
  "fields_updated": ["description", "reference_number"],
  "lines_replaced": true,
  "bank_statements_unmatched": 0,
  "amount": 800.00
}
```

---

## How to Delete Transactions

To permanently remove a posted transaction, use `transaction.delete`. The full transaction data is preserved in the workflow audit trail.

```javascript
submit("transaction", "delete", {
  "transaction_id": 123,
  "legal_entity_id": 10,
  "deletion_reason": "Duplicate entry created by mistake"
})
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `transaction_id` | integer | ID of the posted transaction to delete |
| `legal_entity_id` | integer | Legal entity the transaction belongs to |
| `deletion_reason` | string | Why the transaction is being deleted (required for audit trail) |

### What Happens

1. A full snapshot of the transaction (header, lines, GL, dimensions) is captured for the audit trail
2. Bank statement lines matched to this transaction are automatically unmatched
3. Bank card transactions matched to this transaction are automatically unmatched
4. If the transaction is part of a reversal pair (original + reversing), **both are deleted together**
5. The transaction and all child records are permanently removed (CASCADE delete)

### Restrictions

- The fiscal period for the transaction must be open (not closed)
- **AP/AR invoices with payments**: Cannot delete if `amount_paid > 0` — delete/reverse the payments first
- **AP/AR payments**: Cannot delete if the payment has been applied to invoices
- **Reversal pairs**: If deleting a reversed transaction, both the original and its reversal are deleted together. Both fiscal periods must be open.

### Success Response

```json
{
  "success": true,
  "deleted_transaction_ids": [123],
  "deleted_transaction_numbers": ["JE000001"],
  "deletion_reason": "Duplicate entry created by mistake",
  "bank_statements_unmatched": 0,
  "bank_cards_unmatched": 0,
  "reversal_pair_deleted": false
}
```

---

## Line Item Fields

### For AP/AR Invoices

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string | Yes | Line description |
| `quantity` | number | Yes | Quantity (must be > 0) |
| `unit_price` | number | Yes* | Unit price per item |
| `amount` | number | Yes* | Total line amount (alternative to unit_price) |
| `account_number` | string | Yes** | GL account number |
| `item_id` | integer | Yes** | Item ID (alternative to account_number) |
| `tax_code` | string | Yes | Tax code string (e.g., "EU-EE-STD"). Also accepts `tax_code_id` (integer). |
| `is_tax_inclusive` | boolean | No | True if the amount includes tax. Omitted on an AR line: the tax code's own `is_tax_inclusive` decides, net when the code has none (B2B prices are net; a gross-priced code says so on the code). An explicit line value wins. |
| `dimensions` | object | Yes | Line-level dimensions (cost_center, location, etc.) |

*Either `unit_price` OR `amount` is required. If only `amount` is provided, `unit_price` is auto-derived as `amount / quantity`. If both are provided, `unit_price` takes precedence.

**Either `account_number` OR `item_id` is required, not both.

### For Journal Entries

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `account_number` | string | Yes | GL account number |
| `debit` | number | Yes | Debit amount (0 if credit) |
| `credit` | number | Yes | Credit amount (0 if debit) |
| `description` | string | No | Line description |
| `dimensions` | object | No | Line-level dimensions |

**Note:** Journal entries must balance (total debits = total credits).

---

## Auto-Calculated Fields

The system automatically derives certain fields to simplify transaction posting. You can omit these fields and let the system calculate them.

### Line Amount and Unit Price

For AP/AR invoices, `amount` and `unit_price` are interchangeable:

**If you provide `unit_price`:**
```
amount = quantity x unit_price
```

**If you provide `amount` but not `unit_price`:**
```
unit_price = amount / quantity
```

**Example — providing unit_price (recommended):**
```javascript
{
  "quantity": 10,
  "unit_price": 25.00
  // amount auto-calculated: 10 x 25.00 = 250.00
}
```

**Example — providing amount instead:**
```javascript
{
  "quantity": 10,
  "amount": 250.00
  // unit_price auto-derived: 250.00 / 10 = 25.00
}
```

**Rounding:** Amounts are rounded to 2 decimal places using banker's rounding.

**Validation:** A line amount of exactly zero is rejected. **Negative line amounts are allowed** on invoice-shaped transactions (post AND update): a discount, credit, rebate, or "included usage" line keeps the sign the document prints and posts on the opposite GL side. The DOCUMENT total must stay positive — negative adjustment lines cannot exceed the positive lines. Never drop a credit line or flip its sign to satisfy validation: that overstates the bill by twice the credit.

### Fiscal Period ID

For **AP/AR invoices and payments**, `fiscal_period_id` is **auto-looked up** from `transaction_date`:

```javascript
// You provide:
{
  "transaction_date": "2025-01-15",
  "legal_entity_id": 10
  // fiscal_period_id not provided
}

// System looks up:
// Finds fiscal period containing 2025-01-15 for entity 10
// Sets fiscal_period_id automatically
```

**Exception:** `JOURNAL_ENTRY` transactions require explicit `fiscal_period_id` (no auto-lookup). This is intentional since journal entries often need to post to specific periods.

**Locked after posting:** Once a transaction is posted, `fiscal_period_id` is locked and cannot be changed directly. If you update `transaction_date` via `transaction.update`, the fiscal period is automatically re-resolved to match the new date. You cannot manually override `fiscal_period_id` on a posted transaction.

**Error hints:** If fiscal_period_id validation fails, the error message includes current and previous open periods:
```
fiscal_period_id is required | Current period: ID 45 (2025-01, 2025-01-01 to 2025-01-31) | Previous period: ID 44 (2024-12, 2024-12-01 to 2024-12-31)
```

### AR invoice due dates

**Local AR-187 persistence correction (unreleased):** new customer invoice
postings save the already-resolved `invoice_date` separately from accounting
`transaction_date` and `due_date`. If one of invoice/accounting dates is omitted,
the existing resolver mirrors the supplied date; payment-term precedence below
is unchanged. Linked customer credit memos reuse this header writer and preserve
their own resolved document date too. No existing document dates are backfilled;
recovering missing historical dates requires independently verified evidence.

For `transaction.post` with `AR_INVOICE`, a supplied `due_date` wins. Otherwise
choose `payment_term_code` from the payload, then the customer's effective
`payment_terms_code` for the target entity, then
`transaction_type_settings.default_payment_terms_code`. Add the effective term's
`days_until_due` to `invoice_date` (which defaults to `transaction_date`). With no
term at any level, the invoice is due on its invoice date.

Customer and payment-term entity overrides are honored. Missing, inactive or
invalid selected terms fail validation and posting; zero days means immediate.
An explicit term is validated even when an explicit due date wins; inherited
terms are not consulted when that date is supplied. Term codes are identifiers:
the resolver uses stored calendar days, not code parsing or end-of-month rules.
Validation and execution use the same resolver; execution rechecks current terms.
This affects new AR postings only, not existing invoice dates or ledger amounts.
AP bill posting and reviewed bill-candidate semantics are unchanged by this fix;
provide an explicit AP due date rather than relying on this AR fallback.

### Tax Code Resolution

For line items, you can provide either:
- `tax_code`: String code like `"EU-EE-STD"` (recommended, easier to read)
- `tax_code_id`: Integer ID like `176` (internal database ID)

The system **auto-resolves** `tax_code` string to `tax_code_id`:

```javascript
// You provide (recommended):
{
  "tax_code": "EU-EE-STD"
}

// System resolves to:
// tax_code_id = 176 (looked up from master_tax_codes)
```

**Error handling:** If `tax_code` is invalid, validation returns an error with guidance:
```
Line 1: tax_code 'INVALID_CODE' not found. Query available codes with: query('tax_code', filters={"is_active": true})
```

---

## Dimensions

### Dimension Format

The preferred format is an **object/dict**:

```javascript
// RECOMMENDED - object format
"dimensions": {
  "cost_center": "CC-1000",
  "location": "EE",
  "department": "SALES"
}
```

The system also accepts array format (auto-converted internally):

```javascript
// ALSO VALID - array format (converted to object)
"transaction_dimensions": [
  {"dimension_type": "cost_center", "dimension_value": "CC-1000"},
  {"dimension_type": "location", "dimension_value": "EE"}
]
```

**Recommendation:** Use the object format (`dimensions`) for simplicity and readability.

### Header-Level Dimensions

Apply to all lines (unless overridden):

```javascript
{
  "dimensions": {
    "cost_center": "CC-1000",
    "department": "SALES",
    "location": "EE"
  },
  "lines": [...]
}
```

### Line-Level Dimensions

Override header for specific lines:

```javascript
{
  "dimensions": {
    "department": "SALES"
  },
  "lines": [
    {
      "description": "Item 1",
      // Inherits: department=SALES
    },
    {
      "description": "Item 2",
      "dimensions": {
        "department": "MARKETING"  // Overrides header
      }
    }
  ]
}
```

### Required Dimensions

Dimension requirements are configured per transaction type in the workflow definition. For example, AP_INVOICE may require `cost_center` and `location`, while JOURNAL_ENTRY may have no required dimensions.

**Validation behavior:**
- If required dimensions are missing, submission returns validation errors
- Dimensions can be provided at header level (inherited by all lines) or line level (overrides header)
- If a dimension is required at both header and line level, providing it at the header satisfies both

**Example error when dimensions are missing:**
```json
{
  "success": false,
  "errors": [
    "Required dimension 'cost_center' is missing. Add to header: \"dimensions\": {\"cost_center\": \"<value>\"} OR provide on all lines.",
    "Required dimension 'location' is missing. Add to header: \"dimensions\": {\"location\": \"<value>\"} OR provide on all lines."
  ]
}
```

---

## Tax Handling

### CRITICAL: Always Include Tax Codes on Bills

**Every AP invoice line MUST include a `tax_code`.** This ensures:
- Correct VAT/tax calculation on the bill
- Proper tax reporting (VAT returns, tax filings)
- Input VAT is correctly recorded for deduction
- Compliance with local tax regulations

**Before posting any bill, always:**
1. Look up available tax codes: `query("tax_code", filters={"is_active": true})`
2. Determine the correct tax code based on vendor location and transaction type (see Tax Code Selection Guide above)
3. Include `tax_code` on every line item

### Line-Level Tax

Add `tax_code` (string) or `tax_code_id` (integer) to individual lines:

```javascript
{
  "lines": [
    {
      "description": "Office supplies",
      "quantity": 1,
      "unit_price": 100.00,
      "account_number": "6200",
      "tax_code": "EU-EE-STD"  // 24% Estonian VAT
    }
  ]
}
```

### Tax Inclusive Pricing

If the price includes tax:

```javascript
{
  "lines": [
    {
      "description": "Item with VAT included",
      "quantity": 1,
      "unit_price": 124.00,  // Includes 24% VAT
      "account_number": "6200",
      "tax_code": "EU-EE-STD",
      "is_tax_inclusive": true  // Tax extracted from price
    }
  ]
}
```

### VAT Registration & Tax Posting Behavior

Tax posting adapts automatically based on whether the entity is VAT-registered. VAT status is derived from `entity_tax_registrations` (registration_type = 'vat', active, date in range).

**VAT-registered entity** (standard behavior):
- AP Invoice: Separate DR Input VAT GL line (tax receivable), AP liability = net + tax
- AR Invoice: Separate CR Tax Payable GL line, AR debit = net + tax
- Journal Entry: Separate tax GL line mirroring original line direction

**Non-VAT-registered entity** (auto-adjusted):
- AP Invoice: Tax rolled into expense line (no separate Input VAT GL line). Full gross amount goes to expense. AP liability = net + tax
- AR Invoice: Tax skipped entirely — non-VAT seller cannot charge VAT. AR debit = net only
- Journal Entry: Tax rolled into original GL line (no separate tax GL line)

**Reverse charge tax codes**: Blocked entirely for non-VAT entities (validation error). Reverse charge is a VAT mechanism that requires VAT registration.

**Same tax codes work for both** — the system auto-adjusts posting behavior. No need for separate "non-VAT" tax codes.

---

## Response Handling

Whether a posting completes at once or waits for approval depends on the organisation's workflow configuration; branch on `status` and `lane` in the result.

### Success (completed without an approval step)

```json
{
  "success": true,
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "lane": "green",
  "transaction_id": 123,
  "transaction_number": "AP-0045",
  "message": "Transaction posted successfully"
}
```

### Pending Approval

```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "lane": "yellow",
  "message": "Transaction post submitted for approval in yellow lane",
  "next_step": "Use get_submissions(action='my_tasks') to view pending approvals or get_submissions(action='history') to see status"
}
```

### Validation Error

```json
{
  "success": false,
  "error": "Validation Failed",
  "errors": [
    "vendor_id: Vendor 999 not found",
    "lines[0].account_number: Account 9999 does not exist",
    "Missing required dimension 'cost_center'"
  ]
}
```

---

## Query Transactions

**Available Query Tools:**

| Tool | Purpose |
|------|---------|
| `query("transaction", query, filters)` | Free-text search transactions |
| `query("bill", query, filters)` | Search bills only (AP invoices) |
| `query("transaction", filters, date_filters)` | List/filter transactions with pagination |
| `query("bill", filters, date_filters)` | List/filter bills with pagination |
| `get_entity("transaction", id=X)` | Get single transaction with all details |
| `get_entity("bill", id=X)` | Get single bill with all details |
| `query("transaction", filters, date_filters, limit=1)` | Count matching transactions (use `total_count` from response) |
| `query("transaction", group_by, aggregates, filters)` | Ad-hoc GROUP BY / SUM / COUNT analytics |
| `query("bill", group_by, aggregates, filters)` | Aggregate bills (e.g., spend by vendor) |
| `query(entity_type, filters={...})` ×N | Fetch reference data (issue the calls in parallel) (tax codes, payment terms, etc.) |
| `generate_report(report_type, params)` | Formal financial statements (trial balance, P&L, aging reports, etc.) |
| `generate_report("list", {"category": ...})` | Discover available reports and their required parameters |

**Key features:**
- **`party_name` virtual field**: Transaction results automatically include `party_name` (vendor/customer name resolved inline) — no separate lookup needed
- **`include_lines=True`**: Pass as a **top-level parameter** (NOT inside filters) to batch-fetch all transaction lines in a single query. Capped at 500 lines total across all matched records (on both `query` and `query`) — a `lines_truncated` warning in the response means narrow the query rather than trust it as complete
- **`include_related=True`**: Default for `get_entity` — automatically includes GL lines, dimensions, attachments
- **`date_filters`**: Use for date-based filtering (NOT text search)

### List Transactions with Lines

```javascript
query("transaction",
  filters={"legal_entity_id": 10, "transaction_type": "AP_INVOICE", "status": "posted"},
  date_filters={"transaction_date": {"from": "2025-01-01", "to": "2025-01-31"}},
  include_lines=true,   // TOP-LEVEL parameter, NOT inside filters
  limit=50,
  sort_by="transaction_date",
  sort_order="asc"
)
```

### Get Single Transaction

```javascript
get_entity("transaction", id=123)
// include_related defaults to true — returns GL lines, dimensions, attachments
```

### Search Transactions by Text

```javascript
query("transaction", query="Acme",
  filters={"legal_entity_id": 10, "transaction_type": "AP_INVOICE"},
  include_lines=true  // TOP-LEVEL parameter
)
```

> **Important:** `query()` does text matching only. For date-based queries, always use `query()` with `date_filters`. The tool will warn you if your search query looks like a date.

### Aggregate Transactions (Ad-hoc Analytics)

Use `query` for GROUP BY / SUM / COUNT queries without pre-built reports.

**Total spend by vendor (AP invoices):**
```javascript
query(
  entity_type="bill",
  group_by=["vendor_name"],
  aggregates={"amount": "sum", "id": "count"},
  filters={"legal_entity_id": 10},
  sort_by="sum_amount",
  limit=10
)
```

**Monthly revenue trend:**
```javascript
query(
  entity_type="transaction",
  group_by=["party_name"],
  aggregates={"amount": "sum"},
  filters={"legal_entity_id": 10, "transaction_type": "AR_INVOICE"},
  date_filters={"transaction_date": {"from": "2025-01-01", "to": "2025-12-31"}},
  time_bucket={"field": "transaction_date", "interval": "month"},
  sort_by="period"
)
```

**Bills by status:**
```javascript
query(
  entity_type="bill",
  group_by=["status"],
  aggregates={"id": "count", "amount": "sum"},
  filters={"legal_entity_id": 10}
)
```

> **Supported entities for aggregation:** `transaction`, `bill`, `bank_statement_line`, `card_transaction`, `fixed_asset`, `recurring_contract`, `budget_line`

> **Reading the `totals` row:** an `avg` aggregate in `totals` is weighted by a paired `count` aggregate when one is present in the same call, otherwise it's omitted (with an `avg_total_omitted` note) rather than showing a misleading unweighted average. If the group count hits `limit`, the response also sets `totals_truncated: true` — the totals only cover the returned groups, so raise `limit` (max 500) or narrow filters before trusting `totals` as a grand total.

### Batch Reference Data Lookup

Issue the reference-data `query()` calls in parallel rather than sequentially.

**Before posting a transaction:**
```javascript
query("account", filters={"legal_entity_id": 10, "is_active": true}, limit=100)
query("vendor", filters={"legal_entity_id": 10, "is_active": true}, limit=50)
query("tax_code", filters={"legal_entity_id": 10})
query("payment_term")
query("dimension_type", filters={"is_required": true})
```

Each sub-query runs independently — one failure doesn't block others. Results are keyed by entity_type.

### Financial Reports

Use `generate_report` for formal financial statements and `generate_report("list")` to discover what's available.

**Discover available reports:**
```javascript
generate_report("list", {"category": "financial"})
```

**Transaction-related reports:**

| Report Type | Description | Required Params |
|-------------|-------------|-----------------|
| `trial_balance` | All accounts with debit/credit balances | `legal_entity_id`, `as_of_date` |
| `income_statement` | Profit & Loss statement | `legal_entity_id`, `start_date`, `end_date` |
| `balance_sheet` | Balance sheet | `legal_entity_id`, `as_of_date` |
| `general_ledger_detail` | Detailed GL transactions | `legal_entity_id`, `start_date`, `end_date` |
| `account_activity` | Activity for a specific account | `legal_entity_id`, `account_number`, `start_date`, `end_date` |
| `ap_aging` | Accounts payable aging | `legal_entity_id`, `as_of_date` |
| `ar_aging` | Accounts receivable aging | `legal_entity_id`, `as_of_date` |
| `vendor_aging_detail` | Aging for a specific vendor | `legal_entity_id`, `vendor_id`, `as_of_date` |
| `cash_position` | Current cash balances | `legal_entity_id` |

**Examples:**
```javascript
// Trial Balance
generate_report("trial_balance", {
  "legal_entity_id": 10,
  "as_of_date": "2025-12-31"
})

// Income Statement
generate_report("income_statement", {
  "legal_entity_id": 10,
  "start_date": "2025-01-01",
  "end_date": "2025-12-31"
})

// AP Aging
generate_report("ap_aging", {
  "legal_entity_id": 10,
  "as_of_date": "2025-01-31"
})
```

> **Rule of thumb:** Use `query()` for quick ad-hoc questions (e.g., "total spend by vendor"). Use `generate_report()` for formal financial statements with standard accounting formatting (e.g., "give me a trial balance").

### Common Workflow Patterns

**Pattern 1: Preflight Data → Post Transaction**
```
1. parallel query() calls → get accounts, vendors, tax codes, payment terms concurrently
2. submit("transaction", "post", {...}) → post the transaction with valid reference IDs
```

**Pattern 2: Analytics → Drill Down → Details**
```
1. query("bill", group_by=["vendor_name"], aggregates={"amount": "sum"}) → summary
2. query("bill", filters={"vendor_id": 123}, include_lines=true) → vendor's bills
3. get_entity("bill", id=456) → single bill with GL lines and dimensions
```

**Pattern 3: Count → Decide → List**
```
1. query("transaction", filters={"status": "posted"}, limit=1) → check total_count
2. query("transaction", ...) → only if count is manageable
```

**Pattern 4: Search → Inspect → Update/Delete**
```
1. query("transaction", query="Acme") → find by text
2. get_entity("transaction", id=123) → full details with related data
3. submit("transaction", "update", {...}) → edit the transaction
```

**Pattern 5: Report Discovery → Generate**
```
1. generate_report("list", {"category": "financial"}) → discover available reports
2. generate_report("trial_balance", {...}) → generate with required params
```

---

## Common Errors

### "transaction_date is required"

**Fix:** Always include `transaction_date` in YYYY-MM-DD format.

### "vendor_id: Vendor X not found"

**Fix:** Lookup vendor first: `query("vendor", query="Acme")`

### "Missing required dimension 'cost_center'"

**Fix:** Include required dimensions in the `dimensions` object:
```javascript
"dimensions": { "cost_center": "CC-1000" }
```

### "Journal entry does not balance"

**Fix:** Ensure total debits equal total credits across all lines.

### "Line X: Either item_id or account_number is required"

**Fix:** Provide either `account_number` OR `item_id` for each line (not both, not neither).

### "Line X: line amount must be positive"

**Fix:** Ensure each line has `unit_price` or `amount` greater than zero. The system calculates `line_amount = quantity x unit_price`. If you provide `amount` instead of `unit_price`, the system derives `unit_price = amount / quantity`.

### "Transaction total must be positive"

**Fix:** The sum of all line amounts must be greater than zero. Check that `unit_price` or `amount` is provided on every line.

### "Line X: tax_code 'XXX' not found"

**Fix:** Look up valid tax codes first: `query("tax_code", filters={"is_active": true})`. Use the correct tax code string from the results.

### "Line X: tax code 'XXX' is not an active tax code of legal entity N"

An AR invoice line names a code the invoice's entity cannot use: unknown to that entity,
or deactivated for it. Nothing was posted. **Fix:** use a code active for that entity
(`query("tax_code", filters={"legal_entity_id": N, "is_active": true})`), or activate the
code for the entity. To credit an invoice issued at a retired (deactivated) rate, post an
AR credit memo: it accepts the deactivated code.

### "Line X: tax_code_id N is 'A', not 'B'; send one or make them agree"

The line sent both `tax_code_id` and `tax_code` and they name different codes. Send only
one of them, or correct the one that is wrong.

---

## Best Practices

1. **Always look up tax codes before posting bills** — Use `query("tax_code", filters={"is_active": true})` to get available codes and select the correct one based on vendor location and transaction type
2. **Always lookup IDs first** — Use search tools to find vendor_id, customer_id, account_number before posting
3. **Include tax_code on every line** — Required for correct VAT/tax handling and compliance
4. **Check required dimensions** — Query `query("dimension_type", filters={"is_required": true})` before posting
5. **Use reference_number** — Store external invoice/reference numbers for reconciliation
6. **Provide descriptions** — Helps with audit trail and reporting
7. **Verify accounts exist** — Use `query("account")` to confirm account numbers
8. **Use `unit_price` for clarity** — While `amount` also works, `unit_price` is the preferred field
9. **Check vendor exists before posting AP** — If vendor doesn't exist, create it first using `vendor.create` workflow
10. **Use parallel `query()` calls for reference data** — Gather tax codes, payment terms, accounts, and vendors concurrently before posting
11. **Use `query` for analytics** — Get totals by vendor, monthly trends, or status breakdowns without writing multiple queries

---

## Transaction Number Series

Transaction numbers are **auto-generated** by the system based on `transaction_type_settings`, not the general `number_series` table. Each transaction type has its own prefix. To change a type's prefix or enable/disable it for an entity, use `submit(object_type="transaction_type_setting", operation="update", ...)` (the counter itself is not editable).

| Transaction Type | Prefix | Example |
|-----------------|--------|---------|
| `AP_INVOICE` | `AP-` | `AP-000045` |
| `AR_INVOICE` | `AR-` | `AR-000123` |
| `JOURNAL_ENTRY` | `JE` | `JE000015` |
| `AP_PAYMENT` | `APAY-` | `APAY-000001` |
| `AR_PAYMENT` | `ARPAY-` | `ARPAY-000001` |
| `BANK_DEPOSIT` | `BDEP-` | `BDEP-000001` |
| `BANK_WITHDRAWAL` | `BWTH-` | `BWTH-000001` |
| `BANK_TRANSFER` | `BXFR-` | `BXFR-000001` |
| `BANK_FEE` | `BFEE-` | `BFEE-000001` |
| `EXPENSE_REPORT` | `EXPR-` | `EXPR-000042` |
| `REIMBURSEMENT_PAYOUT` | `RPAY-` | `RPAY-000001` |
| `TAX_PAYMENT` | `TXPAY-` | `TXPAY-000001` |
| Reversals | `REV-` | `REV-000012` |

**Important:** `submit(object_type="number_series", operation="allocate", data={...})` (replaces `get_next_number()`, MCP registration removed) uses the separate `number_series` table, which covers master data types only (vendor, customer, employee, expense_report, fixed_asset, item, etc.). Transaction numbers are generated automatically during posting and do not use this allocation call.

---

## Related Resources

- **[Document Attachments](document-attachments.md)** - Attaching invoices/bills to transactions
- **[Tax Management](tax-management.md)** - Tax codes, rates, exemptions
- **[Accounts Management](accounts-management.md)** - Chart of accounts
- **[Dimensions Management](dimensions-management.md)** - Cost centers, departments, projects
- **[Posting Profiles](posting-profiles-management.md)** - GL account pairs for automatic posting
- **[Vendor Management](vendor-management.md)** - Creating and managing vendors

### Linked vendor credit documents

Post `transaction.post` with `transaction_type_code: "AP_CREDIT_MEMO"`,
`original_transaction_id`, the original vendor/entity/document currency, the
supplier credit `reference_number`, `invoice_date`, `transaction_date`, and
positive net lines. Use the original accounts and tax codes. A credit is not a
negative invoice or a journal substitute. The executor locks the original,
limits cumulative live credits to its face amount, uses its recorded currency
basis, and posts opposite expense/tax/AP entries atomically. Missing original
currency evidence requires review.

Apply the credit as the source of `reconciliation.match`, with the original
invoice as its target. Partial application and unapplication preserve both open
balances. Ordinary payment matching does not treat vendor credits as invoices.
Reverse linked credits before reversing or financially replacing their source;
financial credit edits require reverse-and-replace. Supplier refunds need their
own evidenced cash lifecycle and must not be inferred as invoice payments.


### Effective schema and reversal dates

Schema discovery combines validator field types with organization-required header fields. Inspect workflow_requirements for conditional transaction-type, line and identifier rules. A generic optional field can be mandatory under the company's workflow policy. Payment reversal application history uses the GL reversal date after migration 624; historical records captured before that fix require audited recovery.


### Existing transaction authorization (2026-09-30)

Update, reverse, cancel and delete require write authority for the document's
stored domain: AP/expense → `ap:write`, AR → `ar:write`, payroll → `payroll:post`,
other ledger types → `accounting:write`. The authenticated company and stored
entity/type determine access; a submitted type hint cannot override it. Entity
access, workflow approval and period/payment-state rules remain additional checks.
Dry runs and cached submissions are also checked. A hard-deleted document cannot
be authorized for replay; inspect its workflow/audit record rather than repeatedly
submitting the deletion. These rules also apply at executor dispatch using the
effective task actor, and the `transaction.create` posting alias is gated.


Reversal reads retain `transaction_type=REVERSAL` but inherit the original
transaction's domain permission, including payroll sensitivity. This applies to
MCP lists/details/GL/aggregates and Admin transaction reads. Source traversal stays
within the company and entity and fails closed for broken or cyclic links.

### Posted cancellation protection

`transaction.cancel` refuses posted, paid, partially paid, reconciled and already
reversed/voided records. It rechecks posting evidence under a row lock at execution;
approval of an earlier draft does not authorise cancelling it after posting.
Use `transaction.reverse` with the chosen `reversal_date` and reason for posted
corrections. The cancellation tool does not choose a date or auto-convert the
request. Ordinary cancellation has no sanctioned escape through closed-period
DB guards. Historical posted voids require separate reviewed repair evidence.


### Customer credit and invoice references (PR #224, October 2026)

`transaction.post` supports `AR_CREDIT_MEMO` with a required `original_transaction_id`,
customer credit `reference_number`, the original customer/entity/currency, dates,
and positive invoice-style lines. Credits debit revenue/tax and credit the original
receivable control account. Cumulative live credits cannot exceed the original
invoice face amount. Apply through `reconciliation.match` to the linked original;
unapply restores both open balances. Reverse live credits before reversing or
financially replacing the original invoice. Financial credit edits require reversal
and replacement. A credit is not a cash refund.

Currency conversion uses the original recorded functional and reporting amounts.
New AR invoices persist reporting amounts from the posted receivable GL. For older invoices with missing reporting headers, preflight and posting can
recover the basis only when the entity reporting currency equals the original
functional currency, every booked GL line proves reporting/functional parity,
and the booked AR control equals the original functional amount. This uses booked
evidence without changing the original invoice. Inconsistent or foreign reporting
basis remains refused and requires audited review; never substitute current rates. Migration 637 adds customer reference uniqueness and extends the
linked-credit history guard to AR invoices; apply before enabling the executor.

AR invoices preserve `project_id` on the header, business lines and GL. A line's
project overrides the header; the referenced project must be assigned to the same
entity and effective on the invoice date. Project revenue allocation remains a
separate business operation; a project reference alone does not mark time billed.

Connector export keeps customer/vendor credits as credit documents. Application capability does not make them cash payments; Odoo linked-document reconciliation remains their application path.

Customer-credit preflight must resolve the original invoice before validating its
AR control account and historical tax registration. Validation uses that original
only for the current request and performs no posting. A follow-up to PR #224 fixes
the live gateway failure found during QA; deployment and live credit retest remain
tracked in PLAN_USER_WORKFLOWS_AND_PERMISSIONS.

### Receipt project attribution

An explicit `project_id` on `AR_PAYMENT` is preserved on the receipt header,
its business line and both GL lines. The project must be assigned to the receipt's
legal entity and effective on the payment date; validation and posting both refuse
unavailable projects. Omit the field for receipts spanning multiple projects.
A custom project dimension is independent of this record link; neither is inferred
from the other. Existing posted receipts are not retagged by the fix. Correct them
only through the supported reversal and replacement workflow after reviewing their
applications.

### Explicit AP/AR partial carrying-value allocation (unreleased hardening)

Partial AP payments and AR receipts release booked functional and reporting carrying amounts
using the evidenced remaining balance and each currency's configured precision. The last
payment releases the remaining booked balance; no new FX rate is guessed for
that release. Incomplete/non-finite GL components, currency disagreement and
amounts incompatible with the currency precision are refused for review.

The allocator also checks actual GL storage scales. Current two-decimal columns
cannot preserve a three-decimal currency, so that case is refused until a
storage/writer migration is completed. This is not a claim of three-decimal
posting support. Outstanding revaluations and historical foreign applications
without supported carrying evidence still require their existing review paths.
This does not extend agent FX permissions to partial applications or activate aging.

### Historical invoice settlement routing (unreleased hardening)

Native AP payments and AR receipts with explicit invoice applications resolve the
control from the original invoices' booked GL, rather than the current posting
profile. A later profile choice cannot redirect settlement of an older invoice.
The original control must remain active, uniquely resolvable and a posting account.
Invoices on different controls produce separate GL lines in the same payment;
each releases its own booked carrying amount. The single AP business line has no
single-account attribution when several controls are used; its amount is still the
payment total. AR retains its bank business line. Inactive controls require a
reviewed transition; the writer
does not reactivate them or rewrite old GL. Payments without applications use
the current configured profile through the entity-effective account view.

Source invoices are rechecked and locked in stable order before posting: entity,
party, currency, posting/reversal state, date and remaining capacity must agree.
Incomplete, ambiguous or unbalanced booked control evidence is refused. Concurrent
receipts cannot consume the same remaining invoice balance twice.

Both native AP and AR applications persist explicit source document consumption and
the allocated target functional amount. AR foreign receipts now use the shared
remaining carrying-value calculation, with gain/loss lines for the difference
between bank and invoice carrying amounts. FX lines preserve party, project and
dimensions and require one unambiguous profile with active P&L counterparts. Missing
configuration rolls back the entire payment and its applications. Reversals use
the existing supported workflow. This does not repair old application evidence,
extend agent partial-FX permissions, support active revaluation allocation, permit
multiple controls within one source invoice, or change live AP/AR aging membership.

New native AP/AR invoices and unapplied payments now share control-profile resolution.
An explicit transaction-type link uses its transaction direction (AP invoice credit,
AP payment debit, AR invoice debit, AR payment credit). A generic vendor profile uses
its payable credit side; a generic customer profile uses its receivable debit side,
including payment fallbacks. An explicit vendor-payment profile uses its debit side.
Entity account-number overrides are honored. Tied priorities, ambiguous defaults,
wrong entity/subtype, inactive/header targets, missing selected sides and duplicate
effective account numbers are refused; a malformed selected profile does not silently
fall through. Existing manual-entry flags and aging membership are unchanged.

Invoice line corrections preserve the original booked AP/AR control, even when the
current posting profile selects a different account. Both full replacements and
patch-by-id edits capture the control from the existing ledger before deleting any
lines. Stored business-line contra rows are removed from the patch base using that
booked control, preventing double counting after a profile change. The existing
ledger must balance, agree with the document amount and memo direction, and identify
one active, non-header control in the correct entity. Missing, ambiguous, inactive
or inconsistent evidence requires review; the edit does not substitute today's
profile. This does not enable historical profile cutovers or change aging membership.

When unmatching AP/AR payment applications for one reconciliation run, other runs'
applications remain consumed and the payment keeps its remaining reconciliation
status. Undo uses each recorded `source_applied_amount` in payment currency, not the
invoice or functional amount. For legacy rows, invoice amounts are usable only
when both document currencies are known and equal. Missing cross-currency source
amounts, currency contradictions, invalid amounts or over-consumed payment history
stop the undo before invoice balances or application rows change. Existing live
applications are counted even when an older writer omitted the payment's
`amount_paid`; any larger stored consumption is retained conservatively. A replay
of an already-undone run does not free the same amount again. These rules do not
enable partial FX adjustment permissions or change aging membership.

Agent payment-to-invoice capacity checks use the same exact historical source
consumption rules as unmatch. Retained cross-currency applications without a
recorded source amount, orphan targets, contradictory currencies and invalid
amounts stop a new application; the check never reconstructs historical payment
consumption from the target functional amount. Legacy same-currency history is
supported when both document currencies agree. New partial cross-currency proposals
must provide `source_applied_amount`; the old functional-ratio calculation rounded
to two decimals has been removed. A proposal consuming the full recorded payment
functional amount may use the full document amount, subject to current capacity.
The check requires a caller transaction, posted dates, document currencies and a
finite nonnegative invoice balance. This validates capacity only: explicit source
amounts do not grant partial FX journal permission or prove source/target functional
carrying allocations. Those permissions and their audited legacy repair remain open.

Before native foreign-currency carrying release or agent FX settlement, relevant
posted currency revaluations must be cleared as of the settlement date. A linked
reversal counts only if it belongs to the same entity, points back to that
revaluation, is posted, and is dated on or before settlement. A future-dated,
unrelated or unposted reversal does not clear the exposure. Reversal entries are
not treated as fresh revaluations. Missing/blank revaluation currency evidence is
held conservatively; another identified currency, another entity, a draft, or a
future revaluation does not block this dated check. The agent's database permission
independently checks the same evidence. This refuses unsupported carrying-value
cases; it does not calculate revalued partial allocations or authorize a repair.

Supported revaluation and settlement writers now coordinate per tenant and legal
entity. Native AP/AR payment posting, agent invoice application, manual invoice
matching and shared unapply take a shared transaction lock; the native revaluation
writer takes the exclusive counterpart before reading open items. Concurrent
settlements remain possible under their existing source/invoice capacity locks,
and a different entity or tenant is independent. After a wait, balance reads use
the newly committed state. These paths require a read-committed transaction;
repeatable-read and serializable callers must retry the whole operation in a fresh
supported transaction. The lock lasts through the caller transaction's commit or
rollback. This coordinates the named application routes; it is not a database-wide
guard against direct SQL, connector/import writers or every historical mutation.

The same revaluation boundary now covers native AP/AR invoices and their credit-memo
subclasses, historical invoice updates, shared transaction reversal, importer direct
posting and importer GL backfill. Reversal of a revaluation takes the exclusive
side; ordinary reversals share the settlement side. Backfill rechecks entity/type
and existing GL under the original-document lock, and its own transaction/savepoint
rolls back partial inserts before an import error handler can continue. A competing
backfill sees the first committed result and does not append duplicate lines.
Linked connector backfill errors propagate to the import's row-error result, including
when duplicate mode is skip. Unbalanced supplied GL rolls back the attempt; retry the
same external identity after correcting the source. An existing booked GL is not
replaced by re-import. A skipped duplicate alone is not evidence of source completeness.
Connector application replay delegates to the coordinated manual match/unmatch
workflows. These locks do not certify every arbitrary SQL or operator repair path.

### Native partial-payment reversals and carrying receipts (unreleased)

An earlier instalment may be reversed while later instalments remain. Subsequent
native AP/AR payments use the surviving applications' actual carrying releases,
not a reconstructed original proportion. The final payment releases the exact
remaining functional and reporting amounts. Intermediate payments divide that
remaining carrying balance over the remaining document amount at currency precision.

Native control GL lines retain `carrying_allocations_v1`: invoice transaction
ID, document/functional/reporting amounts as decimal strings, and their currencies.
Before a later foreign payment, the reader reconciles these totals to the booked
control line and the selected invoice's live application amounts. Distinct reporting
currency amounts are retained independently. Contradictions are refused. For older
native payments without a receipt, a single-invoice allocation may be recovered
from the actual control GL; ambiguous multi-invoice foreign allocations require
review. Same-currency historical amounts retain their exact one-to-one basis.

This receipt is native settlement evidence, not an agent controlled-adjustment
permission or a repair of historical application records. Partial agent FX, reviewed
legacy repair and coordinated aging activation remain separate unfinished work.

### Typed parties on manual journal lines

`transaction.post` with `transaction_type_code: "JOURNAL_ENTRY"` accepts optional
`lines[].employee_id`, `vendor_id`, and `customer_id` as positive **master IDs**.
Each supplied ID must belong to the posting entity; employee employment must cover
the posting date. The GL base line and its generated tax lines retain these IDs.
Missing IDs remain NULL; header party and current employee dimensions are not
implicitly substituted. Historical inactive parties can be used for corrections
when entity/date membership is valid. Validation-only and execution both check IDs.

For a historical dimension correction, preserve the original posting and provide
explicit original/replacement dimensions and typed parties on the correcting
journal. This change does not rewrite previous journals or settlements, and a
later dimension journal does not change payroll's stored source snapshot.
Review account/party/dimension nets before considering historical repair complete.


### US GAAP posting defaults (unreleased ledger-integrity branch)

New US GAAP charts include active posting accounts 6990 General Operating Expenses
and 6590 General Depreciation Expense. Vendor, operating expense, purchase sales-tax
and expense-report defaults use 6990; the depreciation default uses 6590. Header
accounts 6000 and 6500 remain grouping accounts. These numbers are template mappings,
not runtime classification rules. Document lines and asset-category configuration
still select their specific accounts where configured.

This template change does not alter existing organisations or repair skipped or
historical posting profiles. Review those profiles against each entity's actual
active, non-header accounts before updating them through the audited configuration
route. Onboarding continues to report a setup gap for invalid account references.


AP/AR invoice account checks (unreleased): preflight checks explicit line accounts
and item-derived expense/revenue accounts against the entity's active, non-header
accounts. Execution independently checks the resolved line and AP/AR control accounts.
A grouping header cannot receive an invoice posting. Correct the line, item default
or posting profile to an appropriate posting account; do not change a header into
a posting account to bypass the error. `allow_manual_entries=false` does not bar
native invoice control posting, and this change does not activate aging membership.


### Agent application currency precision (unreleased ledger hardening)

Before applying an AP/AR invoice match, the agent checks invoice-currency applied
amounts, payment-currency consumption and any matched functional amount against the
configured currency units and the actual destination column scales. It does not
round the proposal to fit storage. Missing precision, fractional yen, excess euro
fractions and currencies whose precision exceeds application/header storage are
refused before application writes. A NULL transaction functional-currency header
uses the entity currency; an explicit mismatch requires review.

Correct the proposed amounts or missing currency configuration from source evidence.
Do not reduce a currency's configured precision to bypass a storage refusal.
Three-decimal support requires a coordinated monetary-storage and writer migration;
widening one column is not release approval. These checks establish representability; foreign applications also require booked
carrying evidence. Live aging membership is unchanged.

### Foreign partial allocations (unreleased)

Standard AP/AR payment-to-invoice applications through agent matching, manual matching
and reviewed-proposal confirmation use SQL-verified independent source and target
functional allocations. Supply explicit source and target document amounts for differing
currencies. Same foreign-currency applications use the same evidence path. Subsequent
applications use surviving receipts with cumulative rounding and exact final remainders.
Do not supply receipt JSON, actor fields or the internal capture flag from agent input.

A nonzero difference needs configured FX accounts and an exact journal against the
original booked control. If posting or evidence attachment fails, the application stays
pending FX review and reporting withholds uncertain carrying amounts. Do not describe a
pending application as fully resolved. No fallback account or current-rate estimate is
permitted. Unsupported legacy consumption, native mixed-control carrying receipts or
outstanding revaluation require operator review.

Undo retains dated evidence and restores capacity; it cannot backdate restored capacity
before the application. A new application gets a new receipt. Neither this mechanism nor
FX evidence capture activates ordinary-journal policy or changes live aging membership.
The operator-only preview and migration 701 proposal records remain read-only evidence
from the agent's perspective; `apply_authorized=false` is not posting permission.


### Reviewed invoice-default changes (unreleased)

An operator may approve an exact AP/AR invoice-default cutover through the audited
transition procedure. This is not an agent permission to edit used account settings or
posting profiles. Subsequent invoice creation uses the approved default; existing invoices
retain their booked controls, and applied payments must resolve those original controls.
Do not redirect settlement to today's default or claim historical balances moved.
The operator completes deferred database checks before certifying final profile/link
state and preserved financial history. A failed apply rolls back its change and receipt;
do not report a cutover as completed from a proposal or intermediate state.
The same retained-history check applies to retirement and unused replacement. Busy
writers refuse apply without changes; retry only after they finish, and obtain a new
review if evidence changed. Do not bypass locks or delete history to make a retry pass.
The operation neither retires old accounts nor activates a new aging membership policy.
Linked/party-specific defaults and date-versioned classification remain outside this
narrow procedure. A backdated new invoice still uses the current creation-time default.


Migration 710 adds a separate operator-reviewed linked-invoice cutover. A unique
invoice link may select a replacement control while a separate fallback default stays
unchanged. This does not authorize an agent to edit profiles or links. Shared payment
profiles, competing invoice links and party-specific references remain unsupported.
Apply the original-booked-control rule to payments after either kind of cutover.
Native AP/AR credit memos also keep their source invoice's booked control and currency
basis, even after the invoice profile changes. Do not use today's default or rate to
redirect a credit. Migration 711 adds a separate operator-reviewed operation for profiles
shared only by the matching invoice and credit-memo types. This grants no agent permission
to edit profiles or remove links. Debit-memo, recurring, payment and party-specific links
remain outside that operation; connector mapping certification is separate work.
Migration 712 adds a separate operator-only transition retaining matching dormant
debit-memo links and customer RECURRING_INVOICE links. It refuses retained transactions
of those codes or a newly registered executor. Ordinary recurring billing posts AR_INVOICE.
Do not delete links to satisfy a proposal, reroute old balances, or treat this as permission
to post new debit memos. Party/payment references and connector mappings remain separate.

### Ordinary-journal activation evidence freshness (unreleased)

Operator activation proposals bind settlement items/runs, controlled permission receipts
and applicable configuration rows as well as ledger/account evidence. A changed write-off
limit or settlement requires a fresh proposal and review, including shared tenant defaults.
Agents must not reuse stale activation approvals or change account flags to bypass a refusal.
This operator evidence check does not activate AP/AR aging or approve legacy allocations.

Activation evidence also binds the underlying account-role, policy-enabled, posted-status
and installed receipt FX/booked-snapshot helpers. Helper/security changes require a fresh
operator proposal even when current balances are unchanged. A missing required receipt
helper blocks readiness. Operator DDL and consumers must be quiesced during apply; agents
cannot treat table locks as protection against concurrent owner-level function changes.


### Reviewed entity control setup before first financial use (unreleased)

Migration 713 provides an operator-only reviewed path to set an existing entity AP/AR
account's manual-entry override to false before retained financial activity. It preserves
the shared master account and other entity settings and does not activate journal policy
or change live aging membership. An agent cannot approve/apply this configuration change,
create private permits, delete evidence to pass checks, or infer that historical balances
may be excluded. Historical entities still need their own reviewed transition. Ordinary
posted documents and original booked-control settlement rules remain unchanged.


### Retired-account history review (unreleased)

Activation preparation includes `evidence.historical_review`: candidate/blocked
counts and per-journal fingerprints, retired account IDs and reasons. A candidate
is only structurally suitable for exact historical review, not a posting permission
or evidence of original authorization. All existing activation blockers remain.
Do not reactivate old accounts, change manual-entry flags, copy a candidate fingerprint
into transaction metadata, or infer that historical permission or aging activation
was granted. A narrow operator-only retired-journal permission path is described below; broader historical transitions remain unfinished.


### Reviewed retired-journal receipts (unreleased)

Migrations 716–720 add private immutable historical journal receipts. Operators use
`review_historical_journals.py` with explicit journal IDs, an exact proposal hash,
a review reference/reason, `preserve_exact_retired_journals` treatment and confirmed
consumer quiescence. The tool does not activate journal policy or AP/AR aging.
Receipt apply and separate journal activation refuse busy writers immediately and
check reviewed evidence after deferred constraints, before commit. Do not bypass a
lock refusal or reuse a stale review after source changes; quiesce writers and
prepare a fresh review when evidence has changed.
An activation proposal must be freshly prepared after receipt apply. Never infer
review approval from candidate status, fabricate a receipt or copy its fingerprint
into transaction metadata. Accounts and booked GL remain unchanged. Existing exact
reciprocal reversals are allowed; new entries, changed historical accounting and
broken reversal pairs are not authorized by a receipt.


Historical AP/AR control review: `preview_account_scope_transition.py --account
MASTER_ID` (repeatable) adds an explicit-account historical packet. It requires one
read-only repeatable snapshot, includes all dates/statuses and fingerprints current
entity financial/configuration sources. Its journal/reversal/opening review notes
are requirements for a future transition, not posting permissions or proof of an
invalid entry. Never infer approval to flip `allow_manual_entries`, create an
override or activate aging from the packet. `apply_supported` and `activation_ready`
remain false. Live aging continues to use its existing membership.


An operator-only `review_historical_account_policy.py` path now supports a narrow
used-control restriction with treatment
`preserve_native_subledger_history_and_live_aging`. It changes one existing entity
manual-entry override only after exact review and a locked evidence recheck. Posted
AP/AR invoice/payment/credit-memo types may qualify; selected journals, openings,
unresolved reversals, unposted or later-dated entries require another transition.
Exact dated native reversal pairs may qualify only with reciprocal posted headers,
matching scope/currencies/parties, opposite stored ledger lines and preserved line
and header dimensions, with every assignment scoped to the selected entity.
Matching cross-entity dimensions do not qualify. This does not authorize a reversal of an otherwise unsupported
journal, restore a void, or infer missing evidence from descriptions. Both live
aging reports must be complete/certified at the explicit review date and unchanged
after apply. Ordinary-journal policy remains dormant; aging membership is unchanged.
Do not use a read-only history packet as this operation's approval, invoke it from
an application role, or interpret the flag update as coordinated activation.

Private `reversal_diagnostics` bind source evidence and describe missing/conflicting
metadata and exact swapped line/dimension comparisons.
`header_dimension_scope_matches` and `line_dimension_scope_matches` independently
report whether all assignments belong to the selected entity. Empty sets pass
this scope check only; matching dimensions do not imply valid scope or complete
evidence. These are observations,
not repair instructions or additional eligibility. Never fill missing parties from
the other header merely because amounts match. Reprepare older review packets.

Historical restriction proposals expose each aging report's quality status,
certification and evidence-gap codes. Complete reports with disclosures remain
blocked separately from incomplete reports. Do not describe a disclosure-only
blocker as incomplete amounts or waive it; reprepare and review after resolution.

The historical restriction can recognize a narrow full functional-currency
card settlement via `verified_full_card_settlements` proposal evidence. It requires
an existing applied reconciliation linking the same vendor's card, bill and
CARD_EXPENSE_RECLASS, equal full amounts, no competing active allocation, and
balanced stored GL preserving the AP and expense line classifications/dimensions.
All three documents must also have identical stored header-dimension multisets
within the selected entity. Missing/different headers remain blocked; matching
line dimensions are insufficient. Every line assignment on the card, bill and
journal must also belong to the selected entity, even if both clearing sides
carry identical assignments. Reprepare proposals after this proof update.
This does not post another clearing entry, reconstruct a missing link, create an
allocation receipt, change P&L or activate aging. Partial/foreign/reversed card
settlements and incomplete evidence still require a separate review.

`verified_full_fx_settlements` records existing full payment/invoice FX evidence
for historical account review: same entity/party/control, explicit currency and
full-amount linkage, balanced source GL and an exact signed two-line FX journal.
The first case excludes partial allocations, allocation receipts, header/control/
adjustment-journal dimensions, reversals and outstanding revaluations. Dimensions
on untouched non-control payment/invoice lines may remain, but every assignment
must belong to the selected entity. It does not clear or temporarily remove
`variance_journal_entry_id`, call the prospective validator as if the journal were
unposted, create controlled FX permissions, or waive report-completeness blockers.
Recognition is not activation and changes no P&L amounts. Residual write-off
recognition has a separate evidence field and does not authorize historical entries.

For historical FX recognition, a missing journal `functional_amount` header is
accepted only when the explicit functional GL lines prove the exact amount and
journal currency is the entity functional currency. An explicitly conflicting
header amount is refused. This reads stored ledger evidence; it does not fill or
rewrite the missing header.

`verified_full_writeoffs` recognizes only a same-functional-currency, single-payment
invoice residual cleared by an existing exact two-line journal: AP debit/revenue
credit or AR credit/expense debit. Partially consumed payments, multiple-payment
history, receipts, header/control/adjustment-journal dimensions and reversed or
foreign documents require separate review. Source-line dimension scope is checked
by the same proof as FX. An otherwise
valid FX-classified counterpart is recognized with its stored subtype and
`classification_review_required=true`; never silently reclassify it.
`historical_authorization_verified=false` is explicit: never
convert this recognition into a controlled-writeoff permission, assume a historical
limit from today's configuration, or bypass an aging gap. The operation changes no
posted amount or P&L; it does not activate posting or aging policy.


Historical FX/write-off review packets: the operator-only workflow in
`review_historical_settlements.py prepare/validate` is read-only and has no apply.
It displays exact booked profit impact and requires one explicit authorization and
classification decision per journal. Do not invent reviewer identity, original
approval evidence or retrospective approval; do not infer these from current
limits. A successful validation is an evidence match, not a permission receipt:
`permission_granted=false`, `apply_supported=false`, and independent historical
authorization verification remains false. Policy/aging activation and accounting
corrections stay separate. A stale packet needs fresh preparation and review.


Exact historical settlement receipts (721, unreleased): a distinct operator CLI
`review_historical_settlement_permissions.py prepare/apply` accepts fresh permission
proposals and explicit per-journal retention/authorization/classification decisions.
The read-only review packet cannot be passed as an apply proposal. Apply also needs
a direct owner connection, confirmed quiescence, current locked evidence and private
immutable guards; it grants no prospective write-off/FX permission and enables no
policy or aging scope. Never fabricate the human decisions or infer them from current
limits. Successful apply pins original accounting immediately. With migration 722,
native unmatch or payment reversal can undo the whole settlement and reverse its
adjustment together. The database requires exact opposite GL, preserved dimensions,
restored balances and matching dated application history. Manual undo uses entity
business date; payment reversal and adjustment undo share the selected reversal date.
Closed periods refuse, and reversing the adjustment alone is not sufficient. Keep
the immutable original receipt: a later match needs its own evidence and adjustment
authorization. Broader correction/supersession remains unfinished. Do not disable
guards, delete a receipt or toggle the old application back to applied. Use identical
retries only after inspecting an uncertain result. Ordinary-journal activation and
coordinated AP/AR activation remain separate reviews.


Historical account-transition reviews may recognize the retained original and exact
reversal of an already reviewed full FX/write-off settlement after native undo.
This requires intact private receipt/guards and dated undo history, not merely zero
net GL. Both aging reports still need complete certified evidence. Agents must not
create substitute receipts, waive report gaps or treat recognition as activation;
a fresh reviewed operator proposal is required for any account-setting transition.


## Historical transition development notes — superseded rollout status

The following dated development notes preserve proof semantics and earlier review
boundaries. Their “local”, “not deployed”, “policies disabled” and September-hold
statements describe the earlier checkpoint, not current production status. PR361
and PR370 delivered these supported paths. PR370's current verified status is in
“Reviewed canceled and corrected journals” below. Do not replay the earlier steps.

Existing-control review refinement (local, not deployed): keep advisory warnings in
`review_historical_account_policy.py` evidence. Only the explicit known warning codes
listed in platform operations are advisory; incomplete/uncertified aging, blocking
or unknown disclosures still refuse. If `evidence.retained_party_evidence_pairs` is
nonempty, an operator must review the linked original/reversal identities and supply
that exact list as `retained_party_evidence_pairs` in the review. Do not invent the
acknowledgment, fill historical party fields, infer payment links from descriptions,
or change paid amounts to make readiness pass. Source hashes and all financial/tax/
dimension checks remain binding. This is not a general historical-data repair route.


Existing retired-journal permissions may be composed into a prospective account
restriction only while their accounting snapshots and required database guards
remain valid. This does not create a permission from age, rewrite the historical
entry, or activate the company policy. The local transition refinement remains
undeployed pending review and production approval.


Additional local transition proofs (not deployed) recognize exact reciprocal
canceled journal/card adjustments only when no active allocation remains; existing
latest report exclusions only while header/ledger fingerprints and immutable guards
remain valid; and full foreign-currency bills settled by functional-currency cards
only with exact document/source units, carrying values and supported FX legs.
These are read-only evidence checks, not permission to edit history or renew a
report decision. Partial/composite settlements, conflicting tax metadata, invalid
chronology and incomplete aging remain blocked. Disposable-copy payment/header
repairs and append-only current-date history corrections are separate proposals;
they are not an automatic production repair capability.


Local repair planning also distinguishes omitted reversal metadata from conflicting
values. Unique source-line correspondence and unchanged booked amounts are required;
nonzero-line currency gaps need a separate review. The planner does not write data.
The disposable apply rehearsal uses existing mutation guards and audit context, and
is not production authorization. Restoring historical tax metadata requires separate
tax-impact review before any production application. A stored FX-card difference is
accepted only if zero/unpopulated or exactly the independently proved functional
cash/carrying variance; the booked FX leg must still match. Unresolved dated source
conflicts and deferred-period corrections remain activation blockers.


Local settlement proof refinement (2026-10-15; not deployed): a fully paid
same-currency invoice may be settled by multiple fully consumed cards only when
**every active leg** independently proves its journal, source amounts, account and
dimension classification, and chronology. All legs must sum exactly to the bill;
one missing, conflicting or unverified leg rejects the whole family. This does not
approve an arbitrary partially paid bill, mixed-currency family, refund or composite
correction. Full foreign-card proofs keep document units separate from functional
carrying amounts and require exact existing FX legs.

Private copied-data date/link proposals remain separate from these read-only proofs.
Moving a clearing or reversal accounting date can change interim-period reports even
when full-month P&L is unchanged. Actual creation/posting timestamps are retained.
Normalizing a negative credit into an equal positive debit preserves signed balances
but changes gross debit/credit presentation; verification must not claim all trial
balance totals or GL columns are unchanged. Source-document conflicts and missing
refund/deposit evidence stay blocked rather than being cleared by date inference.

A separate partial-source proof recognizes one fully paid same-currency bill cleared
from a larger card expense. It requires exact bill/AP/journal amounts, sufficient
source amount, matching source classifications and no competing active allocation.
The evidence explicitly reports the unallocated source amount. It neither proves a
refund nor removes the residual expense, and it does not certify the whole card
charge as settled. This recognition changes no booked amounts or P&L.


### Retained historical dates — revised review boundary, 2026-10-15

The current proposal keeps existing accounts and journal dates. Earlier private
experiments moving consolidated clearing/reversal dates or normalizing a signed
credit solely to satisfy a checker are **withdrawn as production proposals**.
Historical presence on a control account does not by itself establish an error.

A fully proved, fully paid same-currency split-card family may contain clearing
entries preceding the final consolidated invoice. The platform retains and discloses
the exact source, clearing and invoice dates. Before any account restriction is
applied, the reviewer must acknowledge the exact `retained_settlement_timing` list
and supply `settlement_timing_source_reference`. The reference is retained in the
immutable audit reason. This is source-reviewed recognition of a retained chain,
not certification of every historical interim report. It changes no dates or report
calculations. Clearing before its card source, a future invoice beyond the review
date, incomplete/mixed allocations, changed evidence and missing source review still
refuse. A single cross-month payment match is not automatically treated as a deposit.

A fresh disposable copy excluding the earlier date-shift experiments recognizes the
source-supported consolidated families while preserving all compared source rows and
report totals. Remaining evidence/report blockers stay open and both company policies
remain disabled. Genuine proposed errors are listed separately in the private review
packet: proven missing links, crossed monthly matches and denomination/variance data
mismatches. Missing sources and chronology alone are not labeled accounting errors.
No production application, push or deployment is authorized by this rehearsal.
September and dependent corrections remain deferred.


Further local evidence refinement (2026-10-15, not deployed): the card-settlement
writer stores source currency in `reconciliation_items.currency`; the FX historical
proof accepts that label or the older functional-currency label only while explicit
source/target currencies and booked units independently match. A populated functional
matched amount must match the independently established source or target carrying
amount; a document-unit value is not accepted merely because the labels look valid.

An applied `dismissed` review marker does not compete with a real allocation only
when its target id/type and variance journal are absent, variance status is `none`,
and applied/source-applied/functional-matched/difference amounts are null or zero.
Any financial content keeps it a competing row. No marker is deleted or rewritten.
Tests cover each financial field independently, wrong currencies and wrong units.

Two copied document-unit/functional-unit metadata mismatches and their linked run
summaries were corrected in a guarded private rehearsal. Journal headers, dates,
ledger rows, accounts and periods were unchanged. Existing corrective journals must
be included before suggesting any additional accounting correction; a residual in
an isolated leg is not proof that the complete chain is wrong. Other classification
and chronology differences remain investigation items, not presumed accounting errors.


### Retained FX and signed-tax evidence — local verification, 15 October 2026

Historical FX proof accepts an existing `adjusted` variance label only with the
same exact booked source, target, amount, currency and journal proof required for
`fx_posted`. The label alone is insufficient. A signed negative invoice-tax leg
is recognized read-only only for a tax-coded VAT payable/receivable line with
one-sided, matching document/functional signs. Other negative or multi-sided
components remain refused; balancing and exact settlement checks still apply.
No stored line is normalized, and prospective posting validations are unchanged.

The affected regression suite passed 178 tests, including missing tax codes,
wrong account classes, inconsistent functional signs and incorrect adjusted
variance amounts. Fresh disposable preparation recognizes two additional valid
historical FX chains. Compared journal headers/dates, GL and period fingerprints,
P&L, balance-sheet and trial-balance totals remain unchanged. Both company
activations still fail closed on remaining evidence/report prerequisites. This is
local verification only, not a completed transition or production approval.
September and dependent corrections remain deferred.


### Existing same-currency settlement variances — local only

Read-only transition proof now covers an already-booked full same-currency card
settlement with a separate variance leg. Document and functional amounts must agree
for both source and invoice; the recorded difference must equal their exact
carrying difference. AP relief, the full source-expense reversal, the signed
variance leg, party/dimension identity, dates, full invoice settlement and absence
of competing allocations must all pass. No tolerance threshold or new write-off
permission is introduced. The existing variance classification is preserved, not
reclassified or recommended for new postings.

Evidence is exposed separately as
`verified_full_same_currency_variance_settlements`. Independent report certification
still gates the transition even when this evidence passes. The fresh private
rehearsal recognized eight additional chains without changing any stored journal,
date, ledger line or report total. Both company activations remain blocked by
other evidence/report prerequisites. This is not deployed; production and September
remain untouched. Earlier-dated cancellations use the separate retained-history
proof described below; replacement invoices alone do not authorize accepting them.


### Refunded card sources — local proof, not deployed

`verified_refunded_card_settlements` proves one complete same-currency chain:
posted charge, posted refund linked to that charge, fully settled AP invoice, and
its existing clearing journal. The refund must reverse the exact bank and expense
classifications/dimensions; the net charge must match the cleared expense plus the
separately booked signed variance. Explicit reconciliation units, vendor/entity,
amounts, dates and both financial links must agree. Reversed/void documents,
competing applied allocations, unknown units and unbalanced or missing legs refuse.
No refunds, journals, dates, classifications or historical permissions are created
by this proof. No small-difference tolerance or new posting permission is added.

The new evidence is included in transition preparation and its source fingerprints;
report certification remains an independent blocker. Six additional complete chains
were proved on the private disposable copy with no accounting changes or P&L impact.
Both existing-company activations remain blocked on other history/report evidence.
No production action is approved by these results; September remains deferred.


### Retained cancellation before a future invoice date — local proof, not deployed

Historical account-transition preparation can separately prove an already-posted
invoice cancellation whose accounting date precedes the invoice date. Both dates
must be within the reviewed cutoff. Reciprocal links, exact swapped ledger lines,
entity/currency/party/dimensions, and balanced finite functional amounts must agree.
The cancellation must have been posted after the original was posted and no later
than its own accounting date (conservative UTC cutoff). Active applied settlement
links touching either document refuse this route. Unknown or conflicting evidence
remains blocked.

This is `verified_retained_advance_cancellations`, not a valid prospective reversal.
The database reversal guard is unchanged. Preparation discloses both accounting
dates and posting timestamps in `retained_reversal_timing`, with the source hash.
Apply requires acknowledgment of that exact list and a nonblank
`reversal_timing_source_reference`; source changes invalidate the review. The source
reference is retained in the audited reason. This does not certify the interim
period's presentation or waive any independent report-certification blocker.
No journals, dates, amounts, reporting decisions or settlement links are changed.

The private rehearsal recognizes the retained cancellation pair without redating it.
AR control history now has no unsupported lines, but AP report evidence still blocks
its transition. Other settlement history remains unresolved in both companies;
neither company policy has been activated. September remains deferred.


### Single full advance clearing and AP diagnostics — local only

`verified_single_advance_card_settlements` uses the exact settlement-family proof
for a single fully applied, same-currency card charge whose clearing precedes its
invoice. The clearing cannot precede the card charge; all three dates must fall
within the reviewed cutoff. Full invoice settlement, exact applied and functional
units, balanced ledger legs, matching AP/source-expense classifications and dimensions,
and absence of competing applications are required. The dates remain unchanged and
are exposed in `retained_settlement_timing`; apply requires the exact acknowledgment
and a source reference. This is not authorization to post a new early clearing or
an assertion that interim expense presentation was correct. Unproven/mixed-source
families remain blocked.

Private historical transition proposals now retain the report's `control_tie_out`,
application-history exception count/details and history cutoff under each report's
`reconciliation` field. Missing evidence stays null, not zero. The complete report
hash and existing certification checks remain binding; diagnostics cannot override
an incomplete report. Keep company-specific proposal values outside Git.

The refreshed disposable-copy rehearsal proves one additional advance clearing
without changing journal dates or financial records. The outstanding AP tie-out is
fully attributable to deferred September movements; no exclusion, offset or date
change is proposed to clear it. Other historical settlement chains still require
proof. Existing-company activation remains blocked and production is unchanged.


### Existing card correction review — local review aid, not deployed

`historical_card_correction_review.inspect` accepts an explicitly selected settlement
and existing correction journal. It reads a repeatable, read-only snapshot and checks
four distinct documents: card, invoice, original clearing and correction. It proves
full document-currency settlement, functional carrying amounts, exact combined AP
relief/source-expense reversal/FX, matching classifications and dimensions, posted
lifecycle, chronology and no competing financial applications. Empty dismissed
markers are nonfinancial only when every application/variance field is absent or
zero. Missing or conflicting evidence refuses review; there is no cents tolerance.

The returned source hash binds the selected records. `requires_reviewed_link=true`
and `authorizes_transition=false` are intentional: matching amounts and narrative
references do not establish an audited relationship. This helper creates no link,
permission, journal or reporting disposition, and is not an apply endpoint. A future
approved relationship must recheck source evidence. Existing correction journals
must not be posted again merely because a transition cannot yet follow their chain.
Report certification remains independent.

A separately cloned rehearsal now includes the previously source-proven crossed
invoice-application repair. Only the two application targets and associated cent
amounts changed; all journal dates and protected configuration stayed unchanged.
Existing application history was preserved, with automatic effective-date events
and explicit review-date snapshots appended. Exact company/document values and
monthly P&L effects remain in the private proposal, outside Git. No production
change is authorized by this rehearsal. The full transition remains blocked on
other settlement proofs and the deferred September AP difference.


### Explicit correction links in historical transition proposals — local only

`review_historical_account_policy.py prepare --correction-links <private.json>`
accepts an explicit array of `{reconciliation_item_id, correction_id}` selections.
Selections must use unique positive integer IDs; duplicate or overlapping chains
refuse. No candidates are selected from descriptions, amounts or vendor names.
Preparation runs the complete read-only financial proof for each selected chain.
Its original clearing and existing correction can then satisfy historical control
coverage, while every report-certification and other source guard remains binding.

The proposal records `requested_correction_links` and `verified_correction_chains`.
Apply requires acknowledgment of the exact verified chains plus a nonblank
`correction_source_reference`, in addition to the existing whole-proposal approval.
It locks/revalidates all source evidence and retains the reviewed relationship in
the existing private transition audit. It changes only the approved account override;
it never reposts the correction, rewrites a source journal or creates a reporting
exclusion. Standalone inspection still grants no permission. Stale source evidence
refuses and a repeated identical application uses the existing audit receipt.

When an invoice's stored functional header differs from its balanced booked AP
line, the full corrected chain must reconcile exactly to the booked AP amount.
`retained_header_carrying` discloses the header, booked amount and difference for
explicit review; neither value is silently substituted in stored records. Original
and correcting FX legs may use their respective canonical loss/gain accounts, but
all non-account dimensions and the exact combined variance must agree. There is
no rounding tolerance: an uncorrected cent still refuses. This proof does not
certify every historical invoice-header use or remove independent report gaps.

Three explicitly selected copied correction chains now pass without further data
changes. The full preparation still stops at remaining settlement history and the
deferred September AP difference. Both company policies remain disabled; no
production approval, accounting mutation or deployment is implied.


### Retained FX timing and expense classification — local review only

Historical full FX and residual-adjustment proofs retain a journal dated on or
later than its payment but before its invoice when all source documents exist by
the review cutoff and the complete booked chain passes the existing exact tests.
Revaluation evidence is checked at both the journal and later invoice dates.
`retained_settlement_timing` exposes the original dates; apply still requires the
exact list and `settlement_timing_source_reference`. Recognition neither validates
interim accounting presentation nor permits a new early-dated posting.

Same-currency full card clearings may have canceled the invoice expense rather
than the original card expense. Recognition requires the clearing to cancel the
exact invoice expense classification and amount; any other invoice lines must be
neutral VAT, with the original balanced card expense retained. Arbitrary expense
offsets remain rejected. `retained_expense_classifications` identifies both account
IDs and the retained amount. Apply requires that exact list plus
`expense_classification_source_reference`, which is retained in the audit reason.
This proves the stored classification, not that it was the preferred classification.
No journal, date, tax, account flag, aging membership or report gate is changed.

An inactive/header historical control remains unavailable for ordinary new journals.
Do not reactivate it, substitute a new account, or infer invoice amounts simply to
clear a transition blocker. Separate source and correction review remains required.

### Explicit complete settlement-family review — local, not deployed

`review_historical_account_policy.py prepare --settlement-families <private.json>`
accepts an array of explicit `{ "bill_id": ..., "correction_id": ... }` selections.
It reads every applied member of that invoice family; no correction is inferred
from matching cents or descriptions. It requires distinct posted documents, exact
entity/vendor/currency scope, complete invoice-unit settlement, individually
balanced card/clearing ledgers, exact expense cancellation and booked FX, and an
existing correction that makes aggregate AP relief equal the invoice control.
Competing financial applications, reversals, lost dimensions, future documents,
and unexplained offsets fail closed. Inert dismissed markers qualify only with
no target, journal or financial amounts. Overlapping selected chains are refused.

The evidence preserves actual dates and discloses recorded source/target units,
missing source-applied amounts, recorded functional matches and booked relief.
It does not repair those records, infer an exchange rate, approve the economic
correctness of prior FX, or create a new payment allocation. Apply requires the
exact `verified_settlement_families` plus a nonempty
`settlement_family_source_reference`; that reference is saved in the audit reason.
The entire family is read and compared again under the transition locks. Existing
report completeness/certification gates remain mandatory. A family proof is not
company activation or authorization to change old journals.

The retained-invoice-expense proof also covers foreign invoices when booked
functional card and invoice amounts are exactly equal. It preserves the original
card classification and requires the same explicit classification review as the
same-currency path. A nonzero variance cannot use this alternate classification
path. Neither change affects P&L or journal dates.


A retained settlement undo with a historical settlement receipt must pass its
dedicated receipt and application-history guards. Generic canceled-adjustment
recognition cannot substitute for a missing or disabled reviewed-undo guard.


### Retained-history production status — 16 October 2026

PR361's retained-history proof and guard fixes are deployed and verified. Earlier
dated copy-only notes describe the rehearsal stage, not the current release status.
The expressly reviewed non-September metadata repairs and exact historical permissions
have been applied; Hala's 1100/1200 entity restrictions are recorded. These receipts
preserve exact source evidence and do not authorize arbitrary new journals or
renew themselves after source drift. Both company-wide policies remain disabled.
September-dependent AP transitions, independent report gaps and activation approval
remain unresolved; do not infer full readiness from this completed prerequisite work.
Original journal dates and signed financial amounts remain unchanged. Pending
supplier attachments remain pending and are not replaced by review assertions.


### Reviewed canceled and corrected journals — production verified, 16 October 2026

Migration `740_reviewed_historical_control_permissions.sql` and
`historical_control_permissions` add an operator-only exact historical permission
path. Migration 740 and the matching application are deployed and verified. The
separately approved two-company transition is complete: exact permissions and
account restrictions are recorded and both policies are enabled. Migration alone
creates empty private receipt tables and guards; it does not enable policies,
create receipts or edit company accounting.

Supported selections are `canceled_journal` (an original JOURNAL_ENTRY with its
complete reciprocal native reversal), `card_correction` (an explicitly selected
reconciliation item and existing correction), and `card_family` (an explicitly
selected invoice and existing correction covering every settlement leg). The
service reuses the strict native cancellation/card proof used by account transition.
It does not match by memo, amount alone, company identity or a caller's system flag.
Existing reviewed-settlement undo cannot use the generic canceled-journal path.

Use `scripts/review_historical_control_permissions.py prepare --org <organization>
--entity <entity> --selections <private.json> --as-of <date> --output <private.json>`.
Each selection contains `journal_id`, `control_account_id`, and `kind`;
`card_correction` additionally requires `reconciliation_item_id`, and `card_family`
requires `bill_id`. Preparation is read-only and saves a new mode-0600 packet.
Apply requires the exact proposal hash, one explicit authorization/classification
decision per journal, the exact `retained_proofs` array and confirmed consumer/DDL
quiescence. Use the same command's `apply --org ... --entity ... --proposal ...
--review ...` only for a separately approved target. An identical retry returns
its existing receipt; it does not insert a second permission.

Native evidence is rechecked under locks. The receipt freezes its exact document
headers, ledger rows, dimensions, linked reconciliation/application history and
account classification. This intentionally also prevents edits to included header
fields; later source corrections need a separate reviewed procedure, not receipt
rewriting. Unrelated new journals do not invalidate the receipt. ALWAYS triggers
protect the sources even under replica mode; application callers cannot write the
private receipt table. Both activation and runtime posting use the same validity
predicate, and missing/disabled guards block activation. No permission is granted
to an unreviewed new control-account journal.

Historical full-FX settlement receipts also accept the retained `adjusted` status
already recognized by the native full-settlement proof, alongside `fx_posted`.
The status is not rewritten. A label alone is insufficient: exact full payment,
party, currency, journal, dimensions and competing-link checks still must pass.
There is no new FX or write-off posting route.

The full private two-company rehearsal and approved production transition passed
with these receipts, reviewed genuine accounting corrections, remaining account
restrictions and native policy activation. Both AP/AR reports are complete, certified and tied. The platform
permissions/restrictions/activation change neither P&L nor cash, and original journal
dates remain unchanged. Applied financial corrections and their exact verified impacts are
kept in the private review packet. Both policies are enabled. Pending original
supplier documents remain pending. September-dependent transition evidence is
resolved without changing original journal dates. Future company changes still
require their own current evidence and authorization; these receipts grant no
permission to new ordinary control-account journals.

### Bill case receipt conflicts

AP posting records the reviewed bill case result in the same transaction as its
ledger entries. If that case receipt cannot be recorded, posting raises a failure
and rolls back; it is not a definitive typed refusal. Do not retry solely from
the error text: inspect the durable case and transaction outcome. A posted case
stays protected even with a missing invoice link; a linked case cannot be moved
back into review by a late refusal. The local reviewed-AP approval path records
`refused: true` and `reason_code` only with exact persisted no-effect evidence.
Pending replay can return that receipt; the bill returns for clarification with
its saved reason and can accept a new reviewed revision. Unknown execution
failures remain unknown. Immediate execution, other durable families and older
callers retain their prior contracts and may display stale responses. Not deployed.


An owned `payment_link_lost` result with `effect_outcome=existing` and
`review_required=true` preserves the existing transaction and payment/statement
identities. Never interpret it as `refused=true`, a safe retry, or an instruction
to reverse. If `receipt_status=unavailable`, workflow receipt storage failed but
the known financial effect remains. Inspect the committed confirmation hold and
use reviewed recovery. Replaying the same intent preserves its historical result;
a new reviewed intent requires a new explicit key and current validation. This
transport is local and requires the payment producer package before release.

For `payment_batch.confirm_line`, a repeated request requires current access to
both the workflow and the saved line's settlement domain. A failed result-cache
write can be recovered from an exact committed hold or unique posted link without
reposting. An in-progress request with no positive evidence remains unknown and
requires reconciliation; do not change keys merely to bypass it.

Reviewed AP submissions through either the agent gateway or MCP preserve saved
refusal and posting receipts. A postcommit callback error must not be interpreted
as rejection: read the returned transaction receipt. A proven validation refusal
returns the candidate to review. For `posting_unknown`, reconcile the current
case before retrying; do not bypass its durable request identity.
