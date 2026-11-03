

## Agent callback and failure evidence

For Bank pipeline 1.1.0, dependency completion means a stored, currently verified
producer outcome. A completed activation or copied success flag is insufficient.
Inspect each source outcome and permission error before retrying; a rolled-back
workflow can have an attempted ID without a surviving row. Preview does not test
posting. Use normal guarded processing after authority/evidence repair, and do not
change classification to bypass a permission failure. Unlinked bills/card expenses
remain pending until normal reconciliation is run. Version 1.0.0 retained runs keep
their original consumer; verify the active revision before relying on 1.1.0 behavior.


## Card purchase policy

### Purchase read ownership

MCP `get` and `query` for `card_purchase` require AP read permission and apply
stored membership and employee ownership before returning rows, pages or totals.
Human owner, admin, accountant and viewer memberships have broad access within
entity scope. Other nonempty membership roles see only purchases linked through
entity `employees.id` to their login; mixed-owner purchases with no employee ID
are withheld. Missing membership or actor identity fails closed. Custom role
names, supplied employee IDs and wildcard operation permissions do not widen
employee ownership. Trusted agent identities retain AP/entity/task-scoped reads.
Producer-bound reconciliation execution and saga metadata also uses this current
ownership rule, including phases, linked runs and attempts. Missing actor identity
fails closed for these references; unrelated purchase_id fields are unchanged.
Purchase aggregation remains unsupported. These read checks do not authorize
purchase management or financial changes.

Use the backend purchase workspace and shared matching decision; do not implement a competing card matcher in conversation. Preserve provider rows and show net purchase spend. Reference conflicts and competing candidates require review. A paid/settled item can still lack documentation; attach missing source evidence to the existing bill. Evidence review, waiver and grouping use `card_purchase.manage` with current version, evidence fingerprint and reason. Never infer write-off authority from matching tolerance.

Receipt follow-up belongs to the purchase obligation, with one owner and deduplicated reminder stages. Automation and delivery are report-only until the entity rollout settings are explicitly enabled. Statement coverage and opening/movement/closing balance controls must pass independently of agent match counts. August deletion/replay requires its own reviewed manifest and explicit authorization through transaction.delete; implementation permission does not authorize it.

Legacy payment-pass descriptions below apply to non-card AP/AR behavior. Card rows use the shared purchase policy and cannot use nearest-date refund pairing, fuzzy amount identity or adjusting-journal workarounds.

# Corporate Cards Management

This resource covers corporate card management: card programs, issued cards, and card transactions.

---

### Reading monthly card statements

The list groups transactions by card and month. **Purchases / txns** separates
purchase groups from source movements; skipped zero-value verifications remain
in the transaction count but do not count as purchases. **Net spend** is charges
less refunds, with fees disclosed separately. Legacy unsigned charges and signed
provider amounts are normalized by transaction type. **Movement** is the signed
cash movement in that month: outflows are negative and refunds are positive.
A later refund changes the purchase's current net in its owning month but belongs
to the refund month for movement totals.

The match-rate denominator excludes entries with `posting_status='excluded'`.
Skipped entries count as resolved for the statement status. For example, 28
matched transactions and seven skipped verifications show 100% and Reconciled.
Status cells display only a badge; skipped counts and individual skipped entries
remain available in the card statement detail. Provider settlement status alone
does not prove an ERP ledger posting exists.

## Overview

Corporate cards enable employee spending with automated transaction tracking, categorization, and GL posting.

**What you can do:**
- Create and manage card programs (company-level card configurations)
- Issue cards to employees with spending limits
- View and categorize card transactions
- Submit transactions for approval and GL posting
- Reconcile card transactions

**Available Tools:**

| Tool | Purpose |
|------|---------|
| `get_entity("card_program", id=X)` | Get single card program |
| `get_entity("card", id=X)` | Get single card |
| `get_entity("card_transaction", id=X)` | Get single card transaction |
| `query("card_program", filters)` | List card programs |
| `query("card", filters)` | List cards |
| `query("card_transaction", filters)` | List card transactions |
| `query("card_program", query)` | Search card programs |
| `query("card", query)` | Search cards |
| `query("card_transaction", query)` | Search transactions by merchant |
| `submit("card_program", "create", {...})` | Create card program |
| `submit("card_program", "update", {...})` | Update card program |
| `submit("card_program", "deactivate", {...})` | Deactivate card program |
| `submit("card", "issue", {...})` | Issue card to employee |
| `submit("card", "activate", {...})` | Activate issued card |
| `submit("card", "suspend", {...})` | Suspend card |
| `submit("card", "cancel", {...})` | Cancel card |
| `submit("card_transaction", "submit", {...})` | Submit transaction for approval |
| `submit("import", "execute", {object_type: "card_transaction", ...})` | Import card transactions |
| `query("card_transaction", group_by, aggregates, filters)` | Aggregate card spend (e.g., by merchant, employee) |
| `query(entity_type, filters={...})` ×N | Fetch reference data (issue the calls in parallel) |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any operation above, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

---

## Number Series

| Series Type | Prefix | Example | Usage |
|------------|--------|---------|-------|
| `card_program` | `CP-` | `CP-0001` | Auto-generated `program_code` when not user-provided |
| `card` | `CARD-` | `CARD-000001` | Auto-generated `card_reference` on every card issuance |

---

## Card Programs

Card programs define company-level settings for a group of corporate cards.

### Creating a Card Program

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="card_program", operation="create")

// Step 2: Submit with discovered fields
submit("card_program", "create", {
  legal_entity_id: 9,
  program_code: "CORP-AMEX-2026",
  program_name: "Corporate American Express",
  program_type: "corporate",        // corporate, purchasing, travel, employee_benefit, petty_cash
  card_type: "virtual",             // virtual, physical, both
  connector_id: "uuid-of-connector", // Optional — omit for manual programs
  currency_code: "USD",

  // Funding (for prepaid/debit)
  funding_bank_account_id: 123,     // Optional: linked bank account
  card_bank_account_id: 456,       // Optional: credit_card account where charges appear
  // Cash account used when a card charge is linked to a journal: card_bank_account_id,
  // else funding_bank_account_id in debit-card mode (no clearing account, or a clearing
  // account equal to the funding account's GL). Once any card of the program is linked,
  // these accounts and gl_clearing_account_number can no longer be changed.
  funding_method: "prefund",        // prefund, postpay

  // Limits
  credit_limit: 100000.00,
  default_spending_limit: 5000.00,
  default_spending_period: "monthly", // daily, weekly, monthly

  // GL Accounts
  // gl_clearing_account_number controls the credit side of every CARD_EXPENSE entry:
  //   - Credit-card programs (Brex/Ramp/AmEx): set to a true clearing/payable
  //     account, e.g. "2100" or "2200". A separate monthly settlement entry
  //     (DR clearing / CR bank) clears the balance.
  //   - Debit-card programs (Wise/Mercury/Revolut): leave NULL OR set to the
  //     funding bank account's GL number. card_transaction_processor falls
  //     back to the funding bank's GL when this is NULL, so cash is credited
  //     directly at swipe time (no settlement step needed).
  gl_clearing_account_number: "2100",  // Optional — fallbacks to funding bank GL when NULL
  gl_expense_account_number: "6500",   // Reference only — the actual default expense
                                       // comes from the auto-seeded CARD_EXPENSE posting profile

  // Category controls (optional)
  allowed_mcc_codes: ["5411", "5812"], // Only groceries and restaurants
  blocked_mcc_codes: ["7995"],         // Block gambling
  allowed_countries: ["US", "CA"],
  blocked_countries: ["RU", "IR"]
})
// Tip: Use validate_only=true to check payload before submitting
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `legal_entity_id` | number | Legal entity ID |
| `program_code` | string | Unique code (e.g., "CORP-AMEX-2026") |
| `program_name` | string | Display name |
| `program_type` | string | corporate, purchasing, travel, employee_benefit, petty_cash |
| `card_type` | string | virtual, physical, both |
| `currency_code` | string | ISO currency code (e.g., "USD") |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `connector_id` | uuid | Banking connector UUID (omit for manual programs) |
| `funding_bank_account_id` | number | Bank account for funding |
| `card_bank_account_id` | number | Credit card bank account where charges appear |
| `funding_method` | string | prefund, postpay |
| `credit_limit` | number | Program credit limit |
| `default_spending_limit` | number | Default per-card limit |
| `default_spending_period` | string | daily, weekly, monthly |
| `gl_clearing_account_number` | string | Credit side of CARD_EXPENSE entries. **Credit-card mode:** liability/clearing account (e.g. `2200 Card payable`). **Debit-card mode:** leave NULL — the agent falls back to the funding bank account's GL. |
| `gl_expense_account_number` | string | Reference field for UI/reporting. The actual default debit account comes from the CARD_EXPENSE posting profile (auto-created on `card_program.create`). |
| `allowed_mcc_codes` | array | Allowed merchant category codes |
| `blocked_mcc_codes` | array | Blocked merchant category codes |
| `allowed_countries` | array | Allowed countries (ISO 2-letter) |
| `blocked_countries` | array | Blocked countries |

### Listing Card Programs

```javascript
// List all active card programs for an entity
query("card_program", filters={
    legal_entity_id: 9,
    is_active: true
  })

// List by program type
query("card_program", filters={
    legal_entity_id: 9,
    program_type: "corporate"
  })
```

### Getting a Card Program

```javascript
get_entity("card_program", id=1)
```

**Response:**
```json
{
  "id": 1,
  "legal_entity_id": 9,
  "program_code": "CORP-AMEX-2026",
  "program_name": "Corporate American Express",
  "program_type": "corporate",
  "card_type": "both",
  "currency_code": "USD",
  "credit_limit": 100000.00,
  "current_balance": 15432.50,
  "available_balance": 84567.50,
  "default_spending_limit": 5000.00,
  "is_active": true
}
```

### Updating a Card Program

```javascript
submit("card_program", "update", {
  card_program_id: 1,
  default_spending_limit: 7500.00,
  blocked_mcc_codes: ["7995", "5933"]  // Add pawn shops to blocked
})
```

### Deactivating a Card Program

```javascript
submit("card_program", "deactivate", {
  card_program_id: 1,
  reason: "Switching to new card provider"
})
```

---

## Cards

Cards are issued to employees under a card program.

### Issuing a Card

```javascript
// Option 1: Using entity-level employee_id
submit("card", "issue", {
  card_program_id: 1,
  legal_entity_id: 9,
  employee_id: 42,                    // Entity-level employee ID
  card_type: "virtual",               // virtual, physical

  // Spending limits (override program defaults)
  spending_limit: 3000.00,
  spending_period: "monthly",

  // Category restrictions (optional, override program)
  allowed_mcc_codes: ["5411", "5812"],
  blocked_merchants: ["CASINO*"],

  // For physical cards
  shipping_address: "123 Main St, New York, NY 10001"
})

// Option 2: Using master_employee_id (resolved to entity-level)
submit("card", "issue", {
  card_program_id: 1,
  legal_entity_id: 9,
  master_employee_id: 15,             // Master employee ID (will be resolved)
  card_type: "virtual"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `card_program_id` | number | Card program ID |
| `legal_entity_id` | number | Legal entity ID |
| `employee_id` OR `master_employee_id` | number | One of these is required |
| `card_type` | string | virtual, physical (default: virtual) |

> **Note:** You can provide either `employee_id` (entity-level) or `master_employee_id` (global).
> When `master_employee_id` is provided, it's automatically resolved to the entity-level employee ID.
> This is consistent with how vendors and customers work in the system.

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `spending_limit` | number | Per-card spending limit |
| `spending_period` | string | daily, weekly, monthly |
| `allowed_mcc_codes` | array | Allowed merchant categories |
| `blocked_mcc_codes` | array | Blocked merchant categories |
| `allowed_merchants` | array | Allowed merchant patterns |
| `blocked_merchants` | array | Blocked merchant patterns |
| `allowed_countries` | array | Allowed countries |
| `shipping_address` | string | For physical cards |
| `iban` | string | Per-card IBAN (for banks assigning individual IBANs to virtual cards) |
| `account_reference` | string | Alternative account reference |

### Listing Cards

```javascript
// List all cards for an employee
query("card", filters={
    legal_entity_id: 9,
    employee_id: 42
  })

// List active cards in a program
query("card", filters={
    card_program_id: 1,
    status: "active"
  })

// List suspended cards
query("card", filters={
    legal_entity_id: 9,
    status: "suspended"
  })
```

### Getting a Card

```javascript
get_entity("card", id=5)
```

**Response:**
```json
{
  "id": 5,
  "card_program_id": 1,
  "program_name": "Corporate American Express",
  "legal_entity_id": 9,
  "employee_id": 42,
  "employee_name": "John Smith",
  "card_number_last4": "4532",
  "card_type": "virtual",
  "status": "active",
  "spending_limit": 3000.00,
  "spending_period": "monthly",
  "remaining_limit": 1567.50,
  "limit_reset_at": "2026-03-01T00:00:00Z",
  "issued_at": "2026-01-15T10:00:00Z",
  "activated_at": "2026-01-15T10:05:00Z"
}
```

> **Note:** `program_name` is a virtual field resolved inline from `card_program_id`. Related transactions are included by default via `include_related=True`.

### Activating a Card

```javascript
submit("card", "activate", {
  card_id: 5
})
```

### Suspending a Card

```javascript
submit("card", "suspend", {
  card_id: 5,
  reason: "Employee on leave"
})
```

### Cancelling a Card

```javascript
submit("card", "cancel", {
  card_id: 5,
  reason: "Employee terminated"
})
```

---

## Card Transactions

Card transactions are imported from the card provider and can be submitted for approval.

### Listing Card Transactions

```javascript
// List all transactions for a card
query("card_transaction", filters={
    card_id: 5,
    legal_entity_id: 9
  },
  sort_by="transaction_date",
  sort_order="desc")

// List unreconciled transactions
query("card_transaction", filters={
    legal_entity_id: 9,
    recon_status: "pending_recon"    // or use alias: reconciliation_status
  })

// List transactions by employee
query("card_transaction", filters={
    employee_id: 42,
    legal_entity_id: 9
  })

// List transactions in a date range
query("card_transaction", filters={
    legal_entity_id: 9,
    card_program_id: 1
  },
  date_filters={
    transaction_date: {from: "2026-01-01", to: "2026-01-31"}
  })

// List pending transactions needing categorization
query("card_transaction", filters={
    legal_entity_id: 9,
    posting_status: "pending"
  })
```

**Filter Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `legal_entity_id` | number | Legal entity ID |
| `card_program_id` | number | Card program ID |
| `card_id` | number | Card ID |
| `employee_id` | number | Employee ID |
| `status` | string | pending, authorized, posted, settled, declined, reversed, disputed |
| `recon_status` | string | pending_recon, confirmed, exception, adjusted |
| `posting_status` | string | pending, submitted, approved, posted, rejected |
| `card_type` | string | physical, virtual |
| `card_brand` | string | Card brand filter |
| `shipping_status` | string | Shipping status filter |

### Getting a Card Transaction

```javascript
get_entity("card_transaction", id=123)
```

**Response:**
```json
{
  "id": 123,
  "card_id": 5,
  "card_program_id": 1,
  "legal_entity_id": 9,
  "employee_id": 42,
  "employee_name": "John Smith",
  "master_vendor_id": null,
  "vendor_name": null,
  "external_transaction_id": "TXN-2026-00123",
  "transaction_type": "purchase",
  "transaction_date": "2026-01-20T14:30:00Z",
  "posted_date": "2026-01-21",
  "merchant_name": "AMAZON.COM",
  "merchant_category_code": "5942",
  "merchant_category_description": "Book Stores",
  "merchant_city": "SEATTLE",
  "merchant_country": "US",
  "amount": 125.99,
  "currency_code": "USD",
  "status": "posted",
  "recon_status": "pending_recon"
}
```

> **Note:** `employee_name` and `vendor_name` are virtual fields resolved inline — no separate lookups needed.

### Searching Card Transactions

```javascript
// Search by merchant name
query("card_transaction", query="Amazon", filters={"legal_entity_id": 9})

// Search by description
query("card_transaction", query="office supplies", filters={"employee_id": 42})
```

### Aggregate Card Spend

Use `query` for quick card spending analytics:

**Top merchants by spend:**
```javascript
query(
  entity_type="card_transaction",
  group_by=["merchant_name"],
  aggregates={"amount": "sum", "id": "count"},
  filters={"legal_entity_id": 9},
  sort_by="sum_amount",
  limit=10
)
```

**Monthly card spend trend:**
```javascript
query(
  entity_type="card_transaction",
  group_by=[],
  aggregates={"amount": "sum", "id": "count"},
  filters={"legal_entity_id": 9},
  time_bucket={"field": "transaction_date", "interval": "month"}
)
```

### Submitting a Card Transaction for Approval

When an employee needs to categorize and submit a transaction:

```javascript
submit("card_transaction", "submit", {
  card_transaction_id: 123,
  legal_entity_id: 9,

  // Categorization
  expense_item_id: 45,              // Expense category (e.g., "Office Supplies")
  business_purpose: "Books for professional development",
  project_id: 10                    // Optional: link to project
})
```

**Receipts are not part of this payload.** A receipt is attached to the
charge separately (see [Receipts Management](receipts-management.md)) and its
state is read from `receipt_status` on the transaction. There is no
`receipt_attached` or `receipt_url` field — those never existed on this
table, and passing them does nothing.

Linked run input/output must be JSON objects or null and cannot contradict the charge or entity. Inconsistent runs are withheld while their valid queued event remains visible. Agent-type labels are read only from definitions in the same company. This is a narrow receipt-status view; it does not expose execution payloads or grant access to operational run details.

The timeline also omits conflicting links: an event payload cannot name a different entity, and a waiver cannot name another source schema or charge. Missing legacy source-schema and duplicate-ID metadata remains compatible; the stored company, entity and charge reference still determine access.

Receipt timeline events, agent runs and waiver reviews must belong to the charge’s entity as well as its company. Records with another entity or no assigned entity are omitted; an otherwise valid queued event remains visible when its linked run is withheld. The latest review is selected after this filtering.

Receipt timeline failures show fixed guidance to ask the finance team to review the charge. Raw agent error text is not returned by this endpoint; detailed diagnostic data stays in the stored run and requires the separate authorized operational reader. Successful and queued runs without an error do not display failure guidance. Do not treat the generic message as the root cause or resubmit a charge solely because it appears.

The Admin receipt timeline shows waiver explanations, decisions and notes only when the stored fields are strings. Malformed objects, arrays, numbers and booleans are omitted rather than passed to the page. Existing employee ownership and entity checks still apply. This is a display safeguard; it does not repair stored review data or change the review decision.

**Attaching is only half the job.** Since 2026-08-14 a receipt has a
lifecycle: `attach_receipt` files the document and leaves the charge at
`uploaded` — a draft — and nothing happens until someone calls
`submit_receipt`, which hands it to the bill pipeline. The charge then follows
that run (`processing` → `posted` → `reconciled`, or `in_review` / `rejected`).
If you attach and stop, the receipt sits there and no agent will ever look at
it. Full rules in [Receipts Management](receipts-management.md).

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `card_transaction_id` | number | Card transaction ID |
| `legal_entity_id` | number | Legal entity ID |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `expense_item_id` | number | Expense category ID |
| `business_purpose` | string | Business justification |
| `project_id` | number | Project to charge |

**Note:** Dimensions (department, cost center, etc.) are assigned when the transaction is posted to GL, not on the card transaction itself.

---

## Importing Card Transactions

Card transactions can be imported manually when not using a direct connector integration.
This is useful for testing, CSV imports, or migrating from other systems.

### Import via MCP Tool

Use `submit("import", "execute", {...})` with `object_type: "card_transaction"`:

```javascript
submit("import", "execute", {
  object_type: "card_transaction",
  legal_entity_id: 9,
  records: [
    {
      external_transaction_id: "TEST-TX-001",  // Required: unique ID
      card_id: 1,                               // Required: card must exist
      amount: -125.99,                          // Required: negative = expense
      transaction_date: "2026-01-15T10:30:00Z", // Required: ISO timestamp
      merchant_name: "AMAZON.COM",              // Optional
      merchant_category_code: "5942",           // Optional: MCC code
      currency_code: "USD",                     // Default: USD
      status: "posted",                         // Default: posted
      transaction_type: "purchase"              // Default: purchase
    },
    {
      external_transaction_id: "TEST-TX-002",
      card_id: 1,
      amount: -15.50,
      transaction_date: "2026-01-16T09:15:00Z",
      merchant_name: "STARBUCKS",
      merchant_category_code: "5812"
    }
  ],
  options: {
    on_duplicate: "skip"  // Skip the same provider event, card and transaction type
  }
})
```

### CSV Format for Bulk Import

```csv
external_transaction_id,card_id,transaction_date,merchant_name,merchant_category_code,amount,currency_code,status,transaction_type
TXN-001,1,2026-01-15T10:30:00Z,AMAZON.COM,5942,-125.99,USD,posted,purchase
TXN-002,1,2026-01-16T09:15:00Z,STARBUCKS,5812,-15.50,USD,posted,purchase
TXN-003,2,2026-01-17T14:00:00Z,DELTA AIR,4511,-450.00,USD,posted,purchase
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `external_transaction_id` | string | Unique ID from card provider or your system |
| `card_id` | number | Card ID (must exist in bank_cards_issued) |
| `amount` | number | Transaction amount (negative = expense) |
| `transaction_date` | datetime | ISO timestamp of transaction |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `merchant_name` | string | Merchant name |
| `merchant_category_code` | string | MCC code (e.g., "5812") |
| `merchant_category_description` | string | MCC description |
| `merchant_city` | string | Merchant city |
| `merchant_state` | string | Merchant state |
| `merchant_country` | string | Merchant country (ISO 2-letter) |
| `merchant_id` | string | Merchant identifier |
| `merchant_descriptor` | string | Merchant descriptor from card network |
| `currency_code` | string | Currency (default: "USD") |
| `billing_amount` | number | Amount in billing currency |
| `billing_currency` | string | Billing currency |
| `fx_rate` | number | Exchange rate |
| `status` | string | authorized, posted, declined, settled (default: "posted") |
| `transaction_type` | string | purchase, refund, reversal, fee (default: "purchase") |
| `authorization_code` | string | Authorization code from processor |
| `posted_date` | date | Date transaction was posted |
| `settlement_date` | date | Date transaction was settled |

**Duplicate Detection:**

Duplicate identity is card + provider event ID (`metadata.provider_event_id`, falling
back to `external_transaction_id`) + transaction type. A refund reusing a charge ID
remains a separate source. Use `options: { on_duplicate: "skip" }` for an identical
replay, or `"update"` for a compatible lifecycle update. Booked amount/currency
changes are refused and require correction review. Metadata is normalized from
an object or serialized JSON before replay checks. The normalization fix deployed in PR #226; production skip/update replay and
booked-amount refusal tests passed without duplicate source/purchase rows.

---

## Auto-Routing from Bank Statements

When a bank statement is synced or imported for a bank account linked to a card program (via `card_bank_account_id`), the system automatically routes statement lines to `bank_card_transactions` instead of `bank_statement_lines`.

### How Auto-Routing Works

1. Statement is uploaded/synced for a bank account
2. System checks: does `bank_card_programs.card_bank_account_id` match this bank account?
3. If yes → lines are converted to `bank_card_transactions` with `status = 'posted'`
4. Each line is attributed to a specific card by matching the transaction's
   counterparty IBAN against `bank_cards_issued.iban` (ignoring spaces, hyphens
   and case)
5. `bank_transaction_processor` processes them in card mode (classification, GL
   posting, vendor resolution)

### When a Card Cannot Be Identified

Attribution decides whose card — and therefore which employee — a charge belongs
to, so an unresolved match is never guessed silently:

| Situation | Result |
|---|---|
| IBAN matches a card | Attributed to it, `recon_status = 'pending_recon'` |
| No match, program has **one** active card | Attributed to it (unambiguous), `recon_status = 'pending_recon'` |
| No match, program has **two or more** active cards | Recorded but flagged: `recon_status = 'exception'` plus `metadata.card_attribution` |

Flagged rows are deliberately **not** picked up for automatic GL posting — that
query only takes `pending_recon` — so a charge never posts under a guessed
employee. Ask the user whose card it is and reassign it to clear the flag.

### Card Discovery During Statement Import

When processing card statements, the agent should validate that cards and programs exist:

**Unknown card number in statement:**
> "Statement contains transactions for card ending in **4242** but no card with this number exists in program **Arfiti Corporate Card**. What should I do?"
> 1. **Issue a new card** for this number
> 2. **Map to existing card** (select from list)
> 3. **Skip these transactions**

**No card program for credit card account:**
> "Bank account **LHV Card Account EUR** is a credit_card type account but isn't linked to any card program. Should I create one?"

**Multiple card programs possible:**
> "This credit card account could belong to multiple programs. Which card program should receive these transactions?"

### Setting Up Auto-Routing

```javascript
// 1. Ensure the bank account has account_type = 'credit_card'
submit("bank_account", "update", {
  bank_account_id: 10,
  legal_entity_id: 12,
  account_type: "credit_card"
})

// 2. Link it to a card program
submit("card_program", "update", {
  card_program_id: 415,
  legal_entity_id: 12,
  card_bank_account_id: 10
})

// 3. Now any statement imported for bank_account 10
//    will automatically create card transactions
```

### Per-Card IBAN Matching

For banks that assign individual IBANs to virtual cards (e.g., LHV, Revolut), auto-routing matches a
statement line's counterparty IBAN against each card's `iban` column (`bank_cards_issued.iban`) to
link the transaction to that specific card (see step 5 above).

**Note:** there is currently no `submit()` operation that sets `iban` on an issued card — the
`card` object type only supports `issue`, `activate`, `suspend`, `reactivate`, `cancel`, and
`update_limit` (`src/services/workflow_executors/card/card.py`), and none of them accept an
`iban` field. Per-card IBAN matching therefore only engages for cards whose `iban` was populated
some other way (e.g. directly in the database). Until a write path is added, don't tell a user
this can be configured via chat.

---

## Common Scenarios

### Scenario 1: Set Up Corporate Card Program

```javascript
// Step 1: Create card program
submit("card_program", "create", {
  legal_entity_id: 9,
  program_code: "CORP-VISA-2026",
  program_name: "Corporate Visa Cards",
  program_type: "corporate",
  card_type: "both",
  connector_id: "connector-uuid",  // optional — omit for programs fed by CSV import
  currency_code: "USD",
  credit_limit: 50000.00,
  default_spending_limit: 2500.00,
  default_spending_period: "monthly",
  gl_clearing_account_number: "2100",
  gl_expense_account_number: "6500"
})

// Step 2: Issue cards to employees
submit("card", "issue", {
  card_program_id: 1,
  legal_entity_id: 9,
  employee_id: 42,
  card_type: "virtual",
  spending_limit: 5000.00
})
```

### Scenario 2: Employee Submits Expense

```javascript
// Step 1: View unsubmitted transactions
query("card_transaction", filters={
    employee_id: 42,
    legal_entity_id: 9,
    posting_status: "pending"
  })

// Step 2: Submit with categorization
submit("card_transaction", "submit", {
  card_transaction_id: 123,
  legal_entity_id: 9,
  expense_item_id: 45,
  business_purpose: "Client lunch meeting"
})
// The receipt is handled separately. receipt_status tells you where it is:
// pending/requested/overdue = none yet; uploaded = a file is attached but
// NOT submitted (call submit_receipt); processing/in_review = in flight;
// posted/reconciled/waived/not_required = done; rejected = declined, the
// employee must replace it.
```

### Scenario 3: Finance Reviews Card Transactions

```javascript
// View all unreconciled transactions
query("card_transaction", filters={
    legal_entity_id: 9,
    recon_status: "pending_recon"
  },
  sort_by="transaction_date",
  sort_order="desc")

// Spend by merchant (merchant category is not a query filter)
query("card_transaction", filters={
    legal_entity_id: 9
  },
  group_by=["merchant_name"],
  aggregates={amount: "sum"})
```

### Scenario 4: Import Card Transactions for Testing

```javascript
// Import test transactions (no connector needed)
submit("import", "execute", {
  object_type: "card_transaction",
  legal_entity_id: 9,
  records: [
    {
      external_transaction_id: "TEST-001",
      card_id: 1,  // Must be an existing card
      amount: -89.99,
      transaction_date: "2026-01-20T14:30:00Z",
      merchant_name: "Office Depot",
      merchant_category_code: "5943",
      status: "posted"
    },
    {
      external_transaction_id: "TEST-002",
      card_id: 1,
      amount: -42.50,
      transaction_date: "2026-01-21T10:15:00Z",
      merchant_name: "Uber Eats",
      merchant_category_code: "5812"
    }
  ],
  options: {
    on_duplicate: "skip"
  }
})
```

---

## Workflow Lane Rules (Card Transaction Submission)

An organisation can route card transaction submissions by amount, for example:

| Lane | Condition (example) | Flow |
|------|-----------|------|
| **Green** | e.g. Amount < $25 | No approval step unless the organisation has configured one |
| **Yellow** | e.g. $25 <= Amount < $250 | Manager review, where configured |
| **Red** (dual control) | e.g. Amount >= $250 | Manager approval + Accountant review, where configured |

Lanes are assigned by your organisation's workflow rules; the submit() result is authoritative.

---

## Reconciliation Status Values

| Status | Description |
|--------|-------------|
| `pending_recon` | Transaction not yet reconciled |
| `confirmed` | POSTED to GL and confirmed — `posted_transaction_id` links the card line to its CARD_EXPENSE transaction. This is a posting-lifecycle state, NOT a payment↔invoice match. If the posted CARD_EXPENSE also settles a vendor bill, that settlement is a separate ap-scope `reconciliation_item`. |
| `exception` | Requires manual review |
| `adjusted` | Reconciled with adjustment |

### Reversing card reconciliation

Two different links can exist for a card transaction — undo the right one:

| What you want to undo | Operation |
|-----------------------|-----------|
| The card line's GL confirmation (`confirmed` → `pending_recon`) | `submit("reconciliation", "unmatch", { scope: "card", legal_entity_id, card_transaction_id })` — voids the card-scope reconciliation items; the posted GL transaction is NOT touched |
| A settlement of the card's posted CARD_EXPENSE against a vendor bill | `submit("reconciliation", "unmatch", { scope: "ap", legal_entity_id, source_transaction_id: <posted_transaction_id> })` — restores the bill's amount_due/status and reverses the CARD_EXPENSE_RECLASS settlement journal |

To find the posted GL transaction: `get_entity("card_transaction", id)` → `posted_transaction_id`. To see whether (and to what) that transaction is matched: `query("reconciliation_item", filters={ legal_entity_id, source_transaction_id: <posted_transaction_id> })`.

---

## Transaction Status Values

| Status | Description |
|--------|-------------|
| `pending` | Pending processing |
| `authorized` | Authorization received, not yet posted |
| `posted` | Transaction posted by card provider |
| `settled` | Transaction settled by provider |
| `declined` | Transaction declined |
| `reversed` | Transaction reversed/refunded |
| `disputed` | Transaction under dispute |

---

## Posting Status Values

| Status | Description |
|--------|-------------|
| `pending` | Awaiting employee categorization |
| `submitted` | Submitted for approval |
| `approved` | Approved, ready for GL posting |
| `posted` | Posted to GL |
| `rejected` | Rejected by approver |

---

## Hybrid Architecture

Card programs use a **hybrid architecture** where card statements are unified with bank statement processing via the `card_bank_account_id` field. When a card program has a `card_bank_account_id` configured, card transactions flow through the same bank statement reconciliation pipeline as regular bank transactions. This enables:

- Unified reconciliation workflow across bank accounts and credit cards
- Card transactions appearing as bank statement lines for matching
- Consistent GL posting through the bank statement processing agents

Set `card_bank_account_id` when creating or updating a card program to link it to a credit card bank account (account type `credit_card`).

### Card Program Bank Account Links

Each card program has **two** bank account references plus a GL clearing account:

| Field | Purpose | Account Type |
|-------|---------|-------------|
| `funding_bank_account_id` | Bank account that funds the card. **Debit cards:** account that gets debited at swipe. **Credit cards:** account that pays the monthly bill. | `checking` (most common) |
| `card_bank_account_id` | Credit card-typed bank account where charges accumulate as a liability. Triggers auto-routing of statement lines into `bank_card_transactions`. | `credit_card` |
| `gl_clearing_account_number` | The GL number that the credit side of every CARD_EXPENSE entry posts to. | (account number, not FK) |

**Debit-card vs credit-card posting modes**

| Card style | What `gl_clearing_account_number` should point at | Why |
|---|---|---|
| **Credit card** (Brex, Ramp, AmEx, corporate Visa) | A true clearing/payable account, e.g. `2200 Card payable` | Cash hasn't moved at swipe time; the liability accrues until monthly settlement (`DR 2200 / CR Bank`). |
| **Debit card** (Wise, Mercury, Revolut, N26) | NULL — `bank_transaction_processor` (card mode) falls back to the funding bank account's GL automatically. (Setting it explicitly to the funding bank's GL number also works.) | Cash moves at swipe time. Crediting the bank account directly is the correct one-entry posting; no settlement step needed. |

The CARD_EXPENSE posting profile (which provides the debit/expense side) is auto-created when a card program is created (via `CardProgramService._ensure_card_expense_posting_profile`) and back-filled for existing programs by migration `368_seed_card_expense_posting_profiles.sql`. Default debit account: `7400 Other Expenses`, fallback `6900`. The agent overrides this per-MCC via `posting_profile_rules`.

**When the classifier cannot stand behind an account (AR-479).** A card charge
is never posted silently to the CARD_EXPENSE default. Each line a person must
look at carries `metadata.review_reason`, `review_details` and `review_source`:

| `review_reason` | Meaning |
|---|---|
| `looks_already_booked` | An unclaimed posted journal already moves this card's account by the same amount on the charge's date (the AR-477 same-day rule). Match the card line to it; do not post a second expense. |
| `classifier_uncertain` | It is an expense but the classifier could not tell which account fits (it answered UNSURE, picked an account outside the chart, failed, or the entity has no expense accounts). Choose the account. |
| `non_expense_payment` | The classifier, or a government/tax-authority vendor, says this is not an expense (a tax, fine or loan payment). Allocate it. |
| `always_review_merchant` | An earlier review answered "always review" for this merchant. |

Such lines stay unposted with `recon_status='exception'` and go to the card
review task. The CARD_EXPENSE posting profile still provides the credit side and
is used when a person posts the line.

**Policy — provider FX/conversion fees inherit their parent charge
(decided 2026-08-18).** A Wise-style conversion emits a separate
`transaction_type: 'fee'` card row (~0.4% of the leg) carrying the
MERCHANT's name. By design it waits for its parent charge to post, then
inherits the parent's expense account and vendor — a conversion fee on a
hotel stay IS part of the cost of that stay, and severing it onto a
generic bank-charges account would lose that attribution. No invoice will
ever match a fee line, so the reconciliation agent's terminal small-fee
pass (`_pass_small_fee_accept`) is what clears it. The gate is two
conditions, not one: the functional amount must be at/under
`small_charge_writeoff_threshold` (a ceiling, never a reason on its own)
**AND** the charge must be fee-like per `is_fee_like` (added 2026-09-03,
extended 2026-09-04) — which is true when EITHER the connector itself
flagged the row as a fee (`bank_card_transactions.transaction_type='fee'`,
read straight off the linked card row — the same flag this section
describes above) **OR** the inherited vendor has no `AP_INVOICE` anywhere
in the entity and the description carries a fee descriptor (or no vendor
at all). In practice a provider-flagged fee line almost always inherits a
real, AP-invoiced vendor (that IS the point of fee inheritance), so it is
the connector-flag branch that clears it — and it clears cleanly, even
though the same vendor has open bills. A charge that carries no provider
fee flag and inherits a real AP-invoiced supplier's vendor (and no fee
descriptor) stays unmatched like any other charge against that supplier,
until the agent's other passes (or manual review) settle it — see
GUIDE_AGENT_RECONCILIATION.md, "Terminal Pass: Small-Fee Acceptance".
Known cosmetic consequence, accepted: vendor spend totals include the
merchant's fee legs (~0.4% of foreign spend). Do NOT re-route fees to a
bank-charges account — that reverses the 2026-08-11 fee-inheritance
design (tri-state parent lookup, hardened after a prod incident where a
fee classified before its parent stuck in review forever).

**Policy — direct-to-expense is the intended behavior (decided 2026-08-18).**
The agent classifying most card charges straight to a final expense account
(travel, software, …) is not a bypass of the profile: it is the design, and
`7400` is only the fallback for charges the agent genuinely cannot classify.
Do NOT read the 7400 balance as "card spend awaiting its invoice" — most
such spend never passes through it, and it was never a reliable queue. The
real awaiting-invoice signal is `receipt_status` on the card charge (the
Card Expenses page, chased by the receipts collector, with a review task
raised when a posted bill fails to settle). The books are identical either
way: the settlement reclass credits whichever account the charge actually
debited, so expense is recognized once and nothing misstates.

### Importing Card Transactions from CSV

Since card statements flow through the unified bank statement pipeline, importing card transactions from a CSV uses the standard bank statement import. The bank account must have `account_type = 'credit_card'` and be linked to a card program via `card_bank_account_id`.

```javascript
submit("bank_statement", "import", {
  legal_entity_id: 9,
  bank_account_id: 5,          // Must be a credit_card account
  statement_date: "2026-02-28",
  source: "csv_upload",
  lines: [
    {
      transaction_date: "2026-02-10",
      description: "UBER EATS - TALLINN EST",
      debit_credit: "debit",
      amount: 18.50,
      currency: "EUR",
      metadata: {
        merchant: "UBER EATS",
        card_last4: "4242"
      }
    }
  ]
})
```

The `bank_transaction_processor` agent will detect the credit card account type and resolve the card program, card, and employee context automatically. See [Bank Statements Management](bank-statements-management.md) for full CSV import format details and metadata field mappings.

> **One card-data table, whatever the source:** every card movement lands in
> `bank_card_transactions` — a real-time card API (Stripe Issuing, Payhawk), a
> connector sync, and a manual/CSV/statement import all write there. The
> `object_type: "card_transaction"` in `submit("import", "execute", …)` names the
> *importer*, not a second table. (This note used to describe a separate
> `card_transactions` table for manual imports; no such table exists in any
> schema.)
>
> **Carry the purchase id, not just the movement id.** Set
> `metadata.provider_purchase_id` on each imported row to the provider's id for
> the *purchase* — shared by its charge, refund and fee legs — while
> `external_transaction_id` stays unique per leg. Without it every leg becomes
> its own singleton purchase and refunds land in review with no netting, silently.
> See [Bank Statements Management](bank-statements-management.md), "Two ids per
> card row".
>
> **Statement-based card processing flow depends on the bank account type:**
> - **`account_type = 'credit_card'`** with a card program's `card_bank_account_id` pointing at it → `submit("bank_statement", "import", …)` and the import auto-routes the lines into `bank_card_transactions`.
> - **`account_type = 'checking'` or `'savings'` with debit cards on the same account** (typical for Wise, Revolut, N26, Mercury) → import in **two passes**: non-card lines go to `bank_statement_lines` via `submit("bank_statement", "import", …)`; card lines go to `bank_card_transactions` via `submit("import", "execute", { object_type: "card_transaction", … })`. Card lines are excluded from the bank statement payload to avoid double-counting.
>
> **Worked example — Wise EUR checking account, 2 debit cards, 20 statement lines:**
> 1. From the CSV, filter the lines into two buckets using the heuristic in [bank-statements-management.md](bank-statements-management.md): `transaction_details_type == "CARD"`, matching `FEE-CARD-*` fee lines, presence of `merchant` / `card_last4` / MCC, or known card-merchant name patterns. Suppose 13 lines are non-card and 7 are card.
> 2. Import the 13 non-card lines:
>    ```javascript
>    submit("bank_statement", "import", {
>      legal_entity_id: 12,
>      bank_account_id: 5,           // Wise EUR checking, account_type='checking'
>      statement_date: "2026-02-28",
>      source: "csv_upload",
>      lines: [ /* the 13 non-card lines */ ]
>    })
>    ```
> 3. Import the 7 card lines, tagging each with the matching `card_id` (look it up via `query("card", card_last4)` per legal entity):
>    ```javascript
>    submit("import", "execute", {
>      import_type: "card_transaction",
>      legal_entity_id: 12,
>      lines: [
>        {
>          card_id: 383,
>          transaction_date: "2026-02-10",
>          merchant: "UBER EATS",
>          amount: 18.50,
>          currency: "EUR",
>          metadata: { card_last4: "9123", merchant_category_code: "5812" }
>        },
>        // …6 more
>      ]
>    })
>    ```
> 4. The bank account's running balance still reconciles: each card transaction settles to cash via the card-clearing → cash entry generated by the card pipeline, no separate bank statement line needed.
>
> If you can't confidently match a card line to an existing card (no `card_last4` in the CSV and no merchant lookup), post the bank-statement side and **leave the card-transaction import for the user to confirm** rather than guessing.

> **Note:** `card.reactivate` and `card.update_limit` workflows are not currently implemented. To reactivate a suspended card, use `card`, "activate". To change spending limits, update the card program defaults via `submit("card_program", "update", {...})`.

---

## Key Takeaways

- **Card Programs** define company-level settings (limits, GL accounts, controls)
- **Cards** are issued to employees with individual limits (use `employee_id` or `master_employee_id`)
- **Card Transactions** are imported from providers or manually via `submit("import", "execute", {...})`
- **Use `query`** with filters to query cards and transactions
- **Use `submit("card_transaction", "submit", {...})`** to categorize and submit expenses
- **Dimensions** (department, cost center) are assigned when posting to GL, not on the card transaction
- **Manual Import** available via `submit("import", "execute", {object_type: "card_transaction", ...})` for testing or migration
- **Hybrid Architecture** — link card programs to bank accounts via `card_bank_account_id` for unified reconciliation

---

*Last Updated: 2026-03-14*
*Related Resources:*
- [Bank Statements Management](bank-statements-management.md) - Bank account and statement management
- [Bulk Import](bulk-import.md) - Universal import system
- [Transaction Processing](transaction-processing.md) - GL posting


## Provider-backed cards (Revolut programs)

On a card program linked to the Revolut connector, the card workflows act at
Revolut first: `card.issue` creates a **virtual** card for the employee
(matched to a Revolut team member by work email — the employee record needs
the same email) and records it active; `card.suspend` freezes, `card.reactivate`
unfreezes, `card.cancel` terminates (final). `card.issue` accepts
`employee_id` or `master_employee_id`. Physical cards are ordered in the
Revolut app and appear here on the next card sync. If the provider refuses
(e.g. the card is admin-locked in the app), the message says so — relay it,
do not retry.


## Purchase evidence investigation (September 2026)

For CARD_EXPENSE-to-bill identity, compare original merchant amount/currency and
provider purchase-date evidence separately from settlement dates and fees.
Revolut uses `metadata.purchase_occurred_at`, or the retained routed
`metadata.original_source.transaction_date`. Do not substitute ingestion time,
change posted dates, or use nearest-date guessing. Same-day twins remain ambiguous.
The owner retries deterministic leftovers after applied matches remove competitors.

Only when the organization has opted in (`purchase_investigation_enabled: true`;
off by default), unresolved purchases with a vendor can enter a scoped reconciliation saga. It can
page open bills and read raw metadata and persisted bill attachments. It prepares
`review_purchase_settlement` tasks or requests missing evidence through
`investigate_purchase`. A reply to an investigation task only resumes investigation;
it does not authorize posting or settle a bill. Same-vendor settlement reviews may
cite a fingerprinted connector source plus a stored, hashed bill attachment.
Cross-vendor reviews still require both sides' documents and explicit approval.

Never treat model confidence, merchant-name similarity or free-text source
instructions as verified identity. Use the existing settlement workflow after
an approved review; it rechecks source versions/fingerprint, bill identity,
attachments and available capacity. Historical run notes retain rejection reasons
and the investigation saga ID; read current purchase and task state to determine
what remains open. Preserve the single-badge list status layout.


### Manual program setup (PR #224, October 2026)

A manual `card_program.create` may omit `connector_id` and `program_code`; the
existing number series allocates the program code. No bank connection or physical
card issuance is implied. Provider operations still require their connector.
Migration 638 moves the old default connector requirement to optional only on
uncustomized workflow definitions. Deliberately customized requirements remain.
The spending account gate is unchanged: use a `credit_card` account, or an eligible
connector-linked checking account; an ordinary unconnected checking account is
not a card spending account. The generated code is retained in the audit entry.


## Card receipt posting and dimension recovery (2026-10-06)

Documentation acceptance, source GL posting and AP settlement are independent. If a receipt has already produced a bill but the card charge is unposted, process the existing source through the Bank agent in card mode, scoped by `legal_entity_id` and `card_transaction_ids`. Verify `posted_transaction_id`; then link the existing bill through `card_purchase.manage` and settle through `reconciliation.match` with scope `ap` and the current purchase version. Do not create another bill or manually adjust expense accounts to bypass this sequence. QA verified source1 -> CARD000001/49 -> Bill48 -> reclassification50.

Production QA verified cardholder defaults on a fresh card posting and its linked receipt bill after explicit workflow configuration. Cardholder defaults are used only when the transaction workflow enables `employee` as a dimension default source. A receipt uses its exact stored attachment-to-card link within the same entity; the cardholder is resolved for the posting date. Ambiguous links/history refuse processing. Explicit dimension values take precedence; reviewed Bill dimensions remain frozen. Business-purpose text is not a structured dimension assignment, and an employee's defaults do not automatically supply a project or override a product. Configure required dimensions and review missing values instead of assuming successful posting proves complete classification.

### Settlement journal dimension preservation

The settlement correction copies stored dimension identities, inheritance flags and provenance from the original bill AP-control line to the relief debit, and from the original card expense line to the expense-clearing credit. Partial applications retain the same classifications while scaling monetary amounts. Empty source classifications remain empty; current employee/vendor defaults are not reapplied. Existing account selection, FX handling and amount calculations are unchanged. The FX remainder line remains unclassified because it has no single source-line classification.

The fix requires no migration. It changes newly created settlement journals only. An already posted journal must not be edited with SQL; use the supported reconciliation unmatch/reversal and re-match lifecycle after deployment and verify dimension balances. PR232 is deployed in production. QA journal54 was reversed through journal55 and rematched through journal56 using normal reconciliation workflows. Production verification confirms the three source expense dimensions and provenance were preserved, and Admin/MCP both show the purchase settled. This verifies manual settlement; automatic settlement remains subject to the tenant rollout policy.


### Historical investigation evidence visibility (QA branch, deployment pending)

An execution's saved investigation bill/attachment evidence is withheld if the
bill is no longer readable in the entity, the attachment is deleted or outside
that bill's owner space, or a saved reference is malformed. AP read permission is
required for saved investigation metadata, including narrative without invoice IDs. A readable historical trace does not prove
settlement or authorize retrying it. Purchase employee-scope verification remains
open; this change does not expand card-workspace access.


### Reconciliation request evidence reads (QA branch, not deployed)

Stored `reconciliation_agent` requests with action `investigate_purchase` or
`review_purchase_settlement` require AP read permission and current purchase
ownership in the request entity. Ordinary/unknown human roles need their entity
employee link; broad stored finance/viewer roles retain entity-scoped reads.
Missing actors, memberships, purchases and malformed IDs fail closed. Trusted MCP
agent reads retain their existing domain/entity/task boundaries. Every member of
a request thread must pass before rows, counts or pagination are returned.

Settlement-review requests additionally resolve the saved AP bill, attachment
IDs and attachment owner snapshots, and saved card sources/journals against
current read authority. Deleted, missing, foreign-entity or unreadable evidence
hides the request. Attachment ownership uses its canonical owner type; card
sources use master employee IDs, while purchases use entity employee IDs.
Legacy requests without `source_evidence` remain supported. Readability does not
approve settlement, refresh a historical snapshot, or bypass version/effect
checks. General request-to-saga graph traversal, arbitrary metadata/free text
and hosted acceptance remain open.


### Generic card transaction read ownership

MCP `get` and `query` for `card_transaction` apply the same stored organization
membership, employee ownership and entity/task scope as purchase reads. These
checks run before rows, search, pagination, totals and aggregates. Broad stored
roles (owner/admin/accountant/viewer) retain entity-scoped reads; other nonempty
memberships see only transactions linked through entity employees to their login.
Missing actor or membership fails closed. Caller role labels, wildcard operation
permissions and supplied employee IDs cannot widen ownership. Trusted system
callers retain entity/task scope. Card transactions retain their existing tool
permission contract; the purchase-specific AP read gate is unchanged. This does
not change Bank review worklist authority or authorize writes.


### Copied card-receipt source binding

Known Bill recovery originals marked `source=card_receipt_submission` require a
readable card transaction and a nonempty attachment array. Each attachment's
supplied key or URL must match both a current receipt row for that card/entity
and a retained `card_submit_receipt` / `bill.upload` event in the same organization
and entity, with the matching payload source and card ID. The receipt key must
belong to that card's organization/entity storage namespace, without dot traversal.

The stored R2 reference may retain its historical bucket; current configuration
does not invalidate a proven historical event. Explicit key/URL disagreement,
missing records, substituted files and wrong event bindings fail closed. The
checks apply through nested Bill vendor originals and response copies. They do
not require an active processing status or authorize submission, settlement or
retry. Other payload sources retain their own contracts; provider-email binding
and copied narrative remain separate open work.


## Close evidence update (b1, awaiting deployment)

Zero-value card verifications are separated from financial movements only when amount is zero, posting_status is excluded, metadata.non_financial_reason is card_verification, and both GL links are absent. The close check additionally requires recon_status excluded. A marker alone is insufficient. Real exceptions remain outstanding. This does not authorize excluding a financial movement.


### Same-day refusal on card exclusion (AR-477)

`card_statement_line.exclude` is refused with `same_day_journal_exists` when an
unclaimed posted journal already moves the card's cash account by the same
signed amount on one of the charge's dates: the entity's business date of
`transaction_date` (its reporting timezone), the UTC date, or `posted_date`.
The money was most likely booked by hand: match the card transaction to the
journal named in `detail.journal_ids` instead of excluding it. A journal another
source already owns, a reversed journal or a reversal entry, or a different amount or date does not
refuse. Built in, not a setting.

### Card-line rollback receipts (AR-273, local; not deployed)

`card_statement_line.match`, `unmatch` and `exclude` can return a confirmed refusal
only after the operation's owned database transaction has acknowledged rollback.
The proof binds organization, entity, card source, operation and validated payload,
and includes attempted routed-parent statement updates. Earlier postings and
pre-existing links remain outside that proof; it is not permission to reverse them.

Direct/immediate submissions retain the original request identity and refusal.
Final approvals store the verified receipt with their failure outcome; same-intent
retries recover it without executing again. Missing or contradictory evidence,
failed commit/rollback acknowledgements, nested transaction uncertainty and
unconfirmed receipt storage remain unknown. Keep the original identity and known
source IDs for reconciliation. Bank-line and card-line proof cannot substitute
for each other. An arbitrary error or `refused` flag is not proof.

This covers link/match/unmatch/exclude operations, not card expense posting or
`post_as_bill`. It changes no matching, exclusion, close or accountant policy,
and requires no built-in Saga.


### Unavailable card-to-bill operation

`card_transaction.post_as_bill` is unavailable. Its retained executor refuses
with `operation_unavailable` before opening a database connection or attempting
a bill, journal, numbering or card-status write. Existing discovery and saved
workflow identities remain readable; they do not make this capability available.
This restriction does not change supported card matching, classification or
ordinary bill operations.

Direct/internal/agent submission returns the definite reason only after the
exact request's refusal receipt is saved. A delayed approval records the same
scoped refusal on its failed workflow. If receipt storage or acknowledgement is
uncertain, the result stays `posting_unknown`; retain the original request
identity and recover its saved result. Do not submit a new identity to retry the
unavailable operation. This proves no posting by this attempted capability, not
that the card has no previous posting or that another operation is safe.
