## Explicit application dates (local candidate; not deployed)

The candidate manual `reconciliation.match` and `reconciliation.confirm_item`
paths require `application_effective_date` (YYYY-MM-DD) for simple AP/AR cash
payment-to-invoice applications in the entity's functional currency. Manual
`reconciliation.unmatch` requires `undo_effective_date` for that cohort. Missing
dates refuse the operation; neither document dates nor an agent's preference
silently supply an accounting decision. External callers can supply the date
through the same supported workflow APIs. No built-in saga is required.

The server checks saved history, current counters, document identity, period
locks and chronological consistency. It records an immutable event receipt and
the reporting-date resolver evidence. Undo retains the earlier application and
adds its own dated event; rematch uses a new item. Future-effective events are
not supported by this immediate-counter capability. This does not redefine the
existing native foreign-currency allocation mechanism or certify legacy
history. Native receipts retain their existing date rules; previously receipted inactive
items are not certified as reusable new proposals. Mixed native and
simple applications on one source currently require separate supported recovery.

Run void and standalone payment reversal/void refuse live dated applications;
explicit-date unmatch must finish first. Payment reversal using a caller-supplied
connection is unsupported once this schema is installed unless an audited outer
admission path is added; ordinary standalone payment reversal remains a separate
path. Invoice cancellation is not a payment application reversal. Missing or
inconsistent history refuses rather than reconstructing a balance from a header.

This local candidate requires migration 751 and coordinated caller changes.
Older callers that omit the date receive a refusal; do not retry with an invented
date, force flag or direct SQL. The public validator schema exposes the date
fields. Dashboard Confirm asks for an explicit date for eligible cash pairs;
the field starts empty. Native allocation dates remain unchanged, and supplying
the new date field to that native path is refused rather than ignored. Full aging/control
reports, all automatic writers and entity-wide containment are outside this
candidate's verified scope.

## Already-settled missing batch links (candidate operator repair)

When the invoice is already paid and its existing payment application is intact,
do not apply it again. The candidate `repair_settled_payment_links` operator service
repairs only missing batch/statement links and audit receipts, preserving balances,
applications (including legacy null source consumption), ledger entries and dates.
It is not deployed or exposed as an agent operation. Different booking dates need
exact provider/request identity and corroborating stored creation/completion dates.
Use a reviewed no-change preview and exact fingerprint with explicit scoped approval;
no normal confirmation, status-sync or ad-hoc write is a substitute. Never bypass
an adoption refusal or rewrite financial evidence to make it pass.

## Automatic proposals that require review

An explicit `manual_review` proposal is not eligible for automatic application,
even when its confidence exceeds the configured threshold. The reconciliation
services and both purchase reconsideration paths preserve that state. If one
proposal leg of the same purchase needs review, the purchase bundle remains
unapplied. Run totals count these proposals as skipped/review, not matched.
The automatic write methods also reject reviewed proposals before writing.

This guard concerns the current proposal objects. It does not introduce a
cross-run hold on every future proposal involving the same source, redesign
saved review identities, or change the supported explicit Confirm operation.
Confirm continues to check its saved item and authority separately. Historical
application dating, containment and settlement-currency corrections remain
separate work. Confidence thresholds remain editable configuration.

## Reserved invoices and existing cash payments

Reconciliation 1.1 records a reservation-blocked candidate as unapplied manual
review and continues independent safe matches. Purchase groups remain atomic.
Read blocked/review counts and the partial task outcome; execution completion
does not mean every proposed match applied. Pinned 1.0 revisions need separate
reviewed activation of 1.1; never rewrite their implementation hashes.

Provider-completed lines without posted_transaction_id still reserve capacity.
An already-posted statement cannot be repaired by confirm_line, status sync,
cancellation or another cash posting. The internal operator-only adoption service
requires exact identity, ledger evidence, a no-DML preview and explicit recovery
authorization. It is not exposed as an agent operation; do not emulate it with
ad-hoc writes. Preserve provider evidence and review each other stale line separately.

> Current bank contract: bank scope is not supported by reconciliation.*. Use bank_statement_line match/unmatch/exclude and statement coverage controls. The bank examples below are historical; do not execute them. Other scopes require an explicit scope.



## Card purchase policy

Use the backend purchase workspace and shared matching decision; do not implement a competing card matcher in conversation. Preserve provider rows and show net purchase spend. Reference conflicts and competing candidates require review. A paid/settled item can still lack documentation; attach missing source evidence to the existing bill. Evidence review, waiver and grouping use `card_purchase.manage` with current version, evidence fingerprint and reason. Never infer write-off authority from matching tolerance.

Receipt follow-up belongs to the purchase obligation, with one owner and deduplicated reminder stages. Automation and delivery are report-only until the entity rollout settings are explicitly enabled. Statement coverage and opening/movement/closing balance controls must pass independently of agent match counts. August deletion/replay requires its own reviewed manifest and explicit authorization through transaction.delete; implementation permission does not authorize it.

Legacy payment-pass descriptions below apply to non-card AP/AR behavior. Card rows use the shared purchase policy and cannot use nearest-date refund pairing, fuzzy amount identity or adjusting-journal workarounds.

# Reconciliation Management

This guide covers reconciliation in the ERP: bank statement reconciliation (matching bank lines to GL transactions) and transaction reconciliation (matching payments to invoices). Both processes ensure accounting records agree with actual bank activity and that AP/AR aging is accurate.

---

## Overview

| Aspect | Detail |
|--------|--------|
| **Two domains** | Bank statement reconciliation (bank lines vs GL) and transaction reconciliation (payments vs invoices) |
| **Bank recon approach** | Claude finds matches interactively, or `bank_transaction_processor` agent processes automatically |
| **Transaction recon approach** | `reconciliation_agent` runs 6-pass matching algorithm automatically |
| **Bank line statuses** | `unmatched`, `matched`, `excluded`, `reconciled` |
| **Transaction recon statuses** | `NULL` (never reconciled), `partial`, `reconciled` |
| **Key tables** | `bank_statement_lines` (bank recon), `reconciliation_runs` + `reconciliation_items` (transaction recon) |
| **Variance handling** | FX differences auto-posted as gain/loss when FX auto-posting is on (on by default, `auto_post_fx_variance`), otherwise left for review; same-currency differences require manual review |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any reconciliation operation, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

### Temporal Ordering

```
1. Invoice created (AP_INVOICE) --- bill processor or manual entry
2. Payment created (AP_PAYMENT) --- bank_transaction_processor or payment runs
3. Bank reconciliation ----------- matches bank line to GL transaction
4. Transaction reconciliation ---- matches payment to invoice, updates aging
5. Bills collection -------------- follows up on orphaned payments (no invoice)
```

---

## Bank Statement Reconciliation

Bank statement reconciliation matches individual bank statement lines to GL transactions. This verifies that every cash movement at the bank has a corresponding entry in the accounting system.

```
Bank Statement Line               GL Transaction
-----------------                  ---------------
ACH PAYMENT ACME $5,000    <->    AP Payment - Acme Corp $5,000
WIRE FEE $25               <->    Bank Fee JE $25
DEPOSIT #4567 $10,000      <->    AR Payment - Customer XYZ $10,000
```

### Key Columns on bank_statement_lines

| Column | Type | Description |
|--------|------|-------------|
| `recon_status` | `VARCHAR(20)` | `unmatched`, `matched`, `excluded`, `reconciled` |
| `gl_transaction_id` | `BIGINT` | Direct FK to `transactions.id` (the matched GL transaction) |
| `metadata` | `JSONB` | Match history, notes, provider info |

### Line Status Flow

```
unmatched --> matched --> reconciled
    |                        ^
    +-- excluded ------------+
```

### Available Tools

| Tool | Purpose |
|------|---------|
| `get_entity("bank_statement_line", id=X)` | Get a single statement line |
| `query("bank_statement_line", filters={...})` | List statement lines (filter by `recon_status`, `bank_account_id`, etc.) |
| `query("bank_statement_line", query="query text")` | Search by description or reference |
| `query("bank_statement_line", group_by, aggregates, filters)` | Aggregate lines (e.g., totals by status) |
| `submit("bank_statement_line", "match", {...})` | Match a line to a GL transaction |
| `submit("bank_statement_line", "unmatch", {...})` | Remove a match |
| `submit("bank_statement_line", "exclude", {...})` | Exclude a line (no GL posting needed) |
| `submit("reconciliation", "match", {...})` | Manually match payment to invoice(s) (AR/AP) |
| `submit("reconciliation", "unmatch", {...})` | Reverse a match (AR/AP/card — see "Reverse a Match") |
| `query("reconciliation_run", ...)` / `query("reconciliation_item", ...)` | Inspect match records: which run matched what, at what confidence |
| `submit("reconciliation", "dismiss", {...})` | Close a transaction as reconciled without match |
| `generate_report("reconciliation_status", {...})` | Reconciliation status report |

---

## Bank Reconciliation Workflows

All bank reconciliation write operations go through the workflow system via `submit()`.

### Matching a Statement Line

Match a bank statement line to a GL transaction:

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="bank_statement_line", operation="match")

// Step 2: Submit with discovered fields
// Tip: Use validate_only=true to check payload before submitting
submit("bank_statement_line", "match", {
  statement_line_id: 123,
  gl_transaction_id: 456,
  legal_entity_id: 9,
  notes: "Matched by amount and vendor name"  // optional
})
```

**Result:** Sets `recon_status = 'matched'` and `gl_transaction_id = 456` on the statement line.

**Validation:** Statement line must exist and be `unmatched`. GL transaction must exist in the same legal entity. Statement must not already be reconciled.

| Field | Required | Description |
|-------|----------|-------------|
| `statement_line_id` | Yes | Bank statement line ID |
| `gl_transaction_id` | Yes | GL transaction ID to link |
| `legal_entity_id` | Yes | Legal entity ID |
| `notes` | No | Match reason (for audit trail) |

### Unmatching a Statement Line

Remove an incorrect match:

```javascript
submit("bank_statement_line", "unmatch", {
  statement_line_id: 123,
  legal_entity_id: 9,
  reason: "Matched to wrong transaction"  // optional
})
```

**Result:** Clears `gl_transaction_id`, sets `recon_status = 'unmatched'`, creates audit log entry.

### Excluding a Statement Line

Mark a line as excluded when no GL posting is needed (duplicates, non-business items, internal transfers already handled):

```javascript
submit("bank_statement_line", "exclude", {
  statement_line_id: 123,
  legal_entity_id: 9,
  reason: "Duplicate entry"  // optional
})
```

**Result:** Sets `recon_status = 'excluded'`. Line is removed from unmatched count.

### Workflow Risk Levels

| Workflow | Risk | Reason |
|----------|------|--------|
| `bank_statement_line.match` | Low | Creates linkage, reversible |
| `bank_statement_line.unmatch` | Medium | Removes linkage, audit trail needed |
| `bank_statement_line.exclude` | Low | Marks as excluded, reversible |

---

## Interactive Bank Reconciliation (Claude-Driven)

Claude performs intelligent matching by reviewing unmatched lines and searching for corresponding GL transactions.

### Step 1: List Unmatched Lines

```javascript
query("bank_statement_line", filters={
    legal_entity_id: 9,
    bank_account_id: 1,
    recon_status: "unmatched"
  })
```

### Step 2: Search for Matching GL Transaction

```javascript
query("transaction", query="payment to vendor XYZ amount 5000")
```

### Step 3: Create the Match

```javascript
submit("bank_statement_line", "match", {
  statement_line_id: 123,
  gl_transaction_id: 456,
  legal_entity_id: 9,
  notes: "Exact amount and date match"
})
```

### Step 4: Verify Progress

```javascript
query("bank_statement_line", filters={
    bank_statement_id: 10,
    legal_entity_id: 9
  })
// Check how many are matched vs unmatched
```

### Claude's Matching Judgment

| Scenario | Action |
|----------|--------|
| Exact amount, same date, matching reference | Match immediately |
| Amount matches, date within 3 days | Match with note |
| Amount close (within 2%), description similar | Match with explanation |
| Multiple possible matches | Ask user which one is correct |
| No match found | Flag for investigation, post adjusting JE if needed |

---

## Automated Bank Processing (Agent-Driven)

The `bank_transaction_processor` agent processes unmatched bank statement lines automatically. It handles all bank transaction sources (Stripe, Revolut, manual CSV imports).

### Triggering the Agent

After importing bank statement lines, trigger automated processing:

```javascript
manage_connectors(action="process_bank_lines", bank_account_id=5, legal_entity_id=9)
```

### What the Agent Does

1. Reads unmatched statement lines for the bank account
2. Detects source (Stripe, bank connector, manual import)
3. For each line: identifies counterparty, posts GL entry, matches the line
4. Creates vendors for debit lines (payments, fees)
5. Creates customers for credit lines (incoming payments)
6. Sets `recon_status = 'matched'` on processed lines

### Source Detection

| Source | Detection | Processing |
|--------|-----------|------------|
| Stripe | `metadata.stripe_type` exists | Charge -> AR payment, fee -> expense, payout -> bank transfer |
| Bank (Revolut) | `metadata.provider` = revolut | Credits -> AR match, Debits -> AP match |
| Manual Import | No metadata.provider | Same as bank path with heavier description parsing |

---

## Handling Exceptions

When a bank statement line has no matching GL transaction, an adjusting journal entry must be posted first.

### Bank Fees

```javascript
// Step 1: Post adjusting JE for bank fee
submit("transaction", "post", {
  transaction_type_code: "JOURNAL_ENTRY",
  legal_entity_id: 9,
  entry_date: "2026-01-15",
  description: "Bank wire fee",
  lines: [
    { account_number: "6500", debit: 25.00 },
    { account_number: "1000", credit: 25.00 }
  ]
})

// Step 2: Match the statement line to the new JE
submit("bank_statement_line", "match", {
  statement_line_id: 789,
  gl_transaction_id: <new_je_transaction_id>,
  legal_entity_id: 9
})
```

### Interest Income

Same pattern: post adjusting JE (DR Cash / CR Interest Income), then match.

### Other Exception Types

| Exception | Action |
|-----------|--------|
| Bank fees | Post JE (DR Bank Fees / CR Cash), then match |
| Interest income | Post JE (DR Cash / CR Interest Income), then match |
| NSF returns | Reverse deposit, update AR, match |
| Outstanding checks | Document for next period (will clear later) |
| Errors | Investigate with bank or correct GL |

---

## Correcting a Match Error

```javascript
// Remove incorrect match
submit("bank_statement_line", "unmatch", {
  statement_line_id: 123,
  legal_entity_id: 9,
  reason: "Wrong vendor payment"
})

// Create correct match
submit("bank_statement_line", "match", {
  statement_line_id: 123,
  gl_transaction_id: 789,
  legal_entity_id: 9
})
```

---

## Reconciliation Equation

```
Bank Balance (per statement)
+ Deposits in Transit
- Outstanding Checks
+/- Bank Errors
= Book Balance (per GL)
```

---

## Transaction Reconciliation

Transaction reconciliation matches payment transactions to invoice transactions. The `bank_transaction_processor` creates AP_PAYMENT / AR_PAYMENT / CARD_EXPENSE transactions from bank/card activity, but these payments are standalone -- they have no link to invoices. Transaction reconciliation fills this gap by matching payments to invoices and updating financial records.

### Why It Matters

Without transaction reconciliation:
- AP_PAYMENT exists (paid vendor $500) but no link to AP_INVOICE ($500 bill)
- A card charge posts but has no link to the AP_INVOICE it settles
- Invoice `amount_due` and `amount_paid` fields remain stale
- AP/AR aging reports are inaccurate

### The Reconciliation Agent

The `reconciliation_agent` is an automated code agent. Card charges get ONE deterministic identity pass (`purchase_match`); everything else runs the legacy multi-pass algorithm below.

| Aspect | Detail |
|--------|--------|
| Agent type | `reconciliation_agent` |
| Execution mode | `hybrid` (Python code + inline Haiku calls) |
| Triggers | `schedule.triggered`, `manual.trigger`, `agent_request.completed.configuration` |
| Scopes | `vendor` (AP payments + CARD_EXPENSE vs AP invoices), `customer` (AR payments vs AR invoices) |
| Concurrency | 1 concurrent run |
| Timeout | 30 minutes |

### Scope Configuration

| Scope | Payment Types | Invoice Types | Party Column |
|-------|--------------|---------------|-------------|
| `vendor` | `AP_PAYMENT`, `AP_PREPAYMENT`, `AP_REFUND`, `CARD_EXPENSE`, `AP_CREDIT_MEMO` | `AP_INVOICE` | `vendor_id` |
| `customer` | `AR_PAYMENT`, `AR_PREPAYMENT`, `AR_REFUND` | `AR_INVOICE`, `AR_CREDIT_MEMO` | `customer_id` |

### Agent Execution Flow

```
1. Resolve legal entities and validate FX posting profiles
2. FOR EACH SCOPE (vendor, customer):
   a. Create reconciliation_run record (status='running'), stamped with
      period_start/period_end when the triggering event carries a close period
   b. Load unreconciled payments (recon_status IS NULL or 'partial'), bounded
      by the run's period when one is stamped -- invoices are NOT date-bounded
   c. Load open invoices (status IN 'posted', 'partial'; amount_due > 0;
      recon_status IS DISTINCT FROM 'dismissed')
   d. Group both by party_id (vendor_id or customer_id)
   e. FOR EACH PARTY with payments:
      -> Card (CARD_EXPENSE) payments first: close net-zero purchases
         (provider refund nets a purchase to zero -- verified identity via
         card_purchase_members, no amount/date tie-break), then propose
         purchase_match via bill_purchase_proposal
      -> refund/reversal/chargeback leftovers held out of every pass below
      -> remaining NON-CARD payments run the legacy multi-pass algorithm
      -> terminal small-fee pass accepts a tiny, non-supplier charge as a fee
   f. FOR EACH PARTY with invoices but NO open payments:
      -> Record as 'unmatched'
   g. Apply confirmed matches (confidence >= 0.85):
      -> Insert reconciliation_items
      -> Update invoice financials (amount_paid, amount_due, status)
      -> Handle variance (FX posting or pending_review)
      -> Update payment recon_status
   h. Record below-threshold matches as 'manual_review'
   i. Finalize run with stats
```

---

## Card Purchase Identity (`purchase_match`)

Every CARD_EXPENSE with a `vendor_id`, not a provider-marked fee, goes through `_match_card_purchases` BEFORE any legacy pass -- whatever it does not resolve is removed from the working set entirely, never falling through to the passes below. Identity comes from `bill_purchase_proposal` (`src/services/card_purchases/matching.py`): a verified reference shared between purchase and bill, or a unique exact-amount fallback within a date window -- **no tie-break by nearest date, amount similarity, or merchant name**. Among tied exact-amount candidates only, the single one dated the same calendar day as the subject is eligible (`exact_amount_same_date`, date identity for recurring same-amount vendors; two same-day candidates stay tied). The agent can apply several independent purchases when every one has a shared typed reference or reviewed bill link, each uniquely identifies this bill, and their same-currency total fits its remaining balance. Otherwise competing candidates or competing open bills remain ambiguous; equal-sum combinations alone are insufficient. One exception is evidence printed on the bill itself (`itemised_bill_lines`): when the bill's posted lines carry one dated entry per session, each entry maps to exactly one same-vendor, same-currency purchase dated that day, every purchase on a printed day maps to an entry, and charges and lines both total the bill exactly, all of those purchases settle the bill, each as its own allocation. All or nothing; any leftover or ambiguity applies nothing and the unmatched bill records the reason. Per-line vendor tax rounding counts only when the agent config `itemised_bill_rounding_units_per_taxed_line` is 1 (default 0 = exact), and the differences must equal the bill's own rounding lines exactly. A manual `reconciliation.match` with `purchase_id` accepts the same evidence under the same organisation setting, one charge per call, with no `link_existing_bill` step.

A refund/reversal/chargeback leg is held out of every payment/invoice pass (money coming back cannot pay a bill). A card purchase whose provider refund(s) net it to zero, with everything posted, closes deterministically (`refund_offset`) via `card_purchase_members` identity alone -- no invoice, no amount/date guess. A partial refund is netted by the pre-auth pass instead (`preauth_net`: charge minus refund equals the bill).

### Manual Match for a Held Purchase

```python
# 1. Link the verified bill
await submit("card_purchase", "manage", data='{"legal_entity_id": 40,
    "purchase_id": 501, "expected_version": 3, "action": "link_existing_bill",
    "bill_transaction_id": 9001, "reason": "Confirmed against vendor statement"}')

# 2. Apply the payment -- scope MUST be "ap" (bank/card are refused here)
await submit("reconciliation", "match", data='{"legal_entity_id": 40,
    "scope": "ap", "source_transaction_id": <charge id>, "purchase_id": 501,
    "purchase_version": 3, "applications": [
        {"target_transaction_id": 9001, "applied_amount": "32.40"}]}')
```

A purchase leg whose card expense was posted without a vendor is applied under the purchase's vendor (the one vendor its legs name); the bill must belong to that vendor and the posted card expense is not changed. With no purchase, or a purchase that names no single vendor, the match is refused (`Payment <id> has no vendor assigned`).

A one-cent leg of a split charge (61.48 + 0.01 of 61.49) is applied like any other leg and posts its own reclass; only an amount that rounds to 0.00 is refused. Do not use `reconciliation.write_off_item` for the last cent of a card-paid bill: an item that already has a reclass journal is refused there. Apply the remaining card leg instead.

---

## Legacy Multi-Pass Algorithm (non-card payments only)

Runs only over payments that are not CARD_EXPENSE. Per party; each pass operates on items remaining from the previous pass. All amount comparisons use functional currency.

### Pass 1: Exact Amount Match

| Property | Value |
|----------|-------|
| Confidence | 1.0 |
| Method | `exact_amount` |
| Matching | 1:1 |
| Strategy | Greedy -- closest date first |

Same party + exact functional amount + date within configurable range (default 90 days).

### Pass 2: Reference Number Match

| Property | Value |
|----------|-------|
| Confidence | 0.95 |
| Method | `reference_match` |
| Matching | 1:1 |

Payment's `reference_number` matches invoice's `reference_number` (case-insensitive). Amount within tolerance in the functional currency (`amount_tolerance_abs`, default 5.00, or `amount_tolerance_pct`, default 1%).

### Pass 2.5: Cross-Reference Match

| Property | Value |
|----------|-------|
| Confidence | 0.92 -- 0.95 |
| Method | `cross_reference` |
| Matching | 1:1 |

Searches for invoice reference tokens (5+ chars) inside payment descriptions, and vice versa. Example: payment description "Payment for INV-2025-0042" matches invoice reference "INV-2025-0042".

### Pass 3: Approximate Amount Match (FX Tolerance)

| Property | Value |
|----------|-------|
| Confidence | 0.85 -- 0.95 (variable by diff %) |
| Method | `approx_amount` |
| Matching | 1:1 |

Matches amounts within FX tolerance. Hard cap: never match > 5% difference.

| Difference % | Confidence |
|--------------|------------|
| < 0.5% | 0.95 |
| 0.5% -- 1.5% | 0.92 |
| 1.5% -- 3.0% | 0.88 |
| 3.0% -- 5.0% | 0.85 |
| > 5.0% | No match |

### Pass 4: Amount Grouping

| Property | Value |
|----------|-------|
| Confidence | 0.50 -- 0.95 (variable) |
| Method | `amount_group` |
| Matching | 1:1, 1:N, N:1 |

Three sub-strategies:
- **1:1** -- single payment/invoice within stricter tolerance
- **1:N** -- one payment covers multiple invoices (sum matches)
- **N:1** -- multiple payments cover one invoice

Temporal filter: invoices within 45 days before / 7 days after payment.

### Pass 5: Haiku Fuzzy Match

| Property | Value |
|----------|-------|
| Confidence | 0.70 |
| Method | `haiku_fuzzy` |
| Max items | 40 payments + 40 invoices per party |

Called only when a party has both unmatched payments AND invoices after passes 1--4. Sends data to Haiku LLM for fuzzy matching. Typically below auto-apply threshold (0.85) and recorded as `manual_review`.

### Pass 6 (Implicit)

All remaining unmatched items are recorded as `match_status = 'unmatched'`.

---

## Financial Updates on Match

When a match is confirmed (confidence >= 0.85 auto-apply threshold):

1. **Insert `reconciliation_items`** with `is_applied = true`
2. **Update invoice financials:**
   - `amount_paid` increases by applied amount
   - `amount_due` decreases by applied amount
   - `status` changes to `paid` (if fully paid) or `partial`
   - `recon_status` changes to `reconciled` or `partial`
3. **Update payment `recon_status`** to `reconciled`

Below-threshold matches (confidence < 0.85) are recorded with `is_applied = false` and appear in the admin dashboard for manual review.

---

## Variance Resolution

When a payment matches an invoice but amounts differ:

| Scenario | Action | Variance Status |
|----------|--------|-----------------|
| Multi-currency, auto-post enabled | Post FX gain/loss journal entry | `fx_posted` |
| Same-currency difference | Leave for manual UI resolution | `pending_review` |
| Difference <= 0.01 (document currency) | Ignore (rounding noise) | `none` |

**FX gain/loss auto-posting:** When source and target currencies differ, the agent posts a journal entry to FX Gain/Loss accounts (from posting profiles, fallback to accounts 8100/9100).

**Same-currency differences** always require manual review -- they usually indicate incorrect match, discount, short payment, or fee adjustment.

---

## Multi-Currency Matching

All matching passes compare transactions in functional currency (the entity's base currency), not document currency. This enables matching a EUR payment to a USD invoice when the entity's functional currency is USD.

Key transaction fields used:

| Field | Purpose |
|-------|---------|
| `functional_amount` | Amount converted to functional currency at posting time |
| `functional_currency` | Functional currency code (e.g., USD) |
| `document_to_functional_rate` | Exchange rate used at posting |
| `currency` | Document currency code (e.g., EUR) |

---

## Database Schema

### Bank Statement Tables

| Table | Purpose |
|-------|---------|
| `bank_statements` | Statement header with date range, opening/closing balances, status |
| `bank_statement_lines` | Individual lines with `recon_status` and `gl_transaction_id` |

### Transaction Reconciliation Tables

#### reconciliation_runs

One row per agent execution per scope.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `BIGSERIAL` | Primary key |
| `legal_entity_id` | `INTEGER` | Legal entity |
| `scope` | `VARCHAR(20)` | `vendor`, `customer`, `netting`, `card`. **Card-paid vendor bills live in the `vendor` scope** — a CARD_EXPENSE acting as the payment side of an AP invoice is a normal vendor payment→invoice match (unmatch with `scope="ap"`); the `card` scope only covers confirming card lines against their own posted GL transactions. **Bank-statement matching is a separate domain** — use `bank_statement_line.match` workflow against `bank_statement_lines.gl_transaction_id`, not `reconciliation_items`. Calling `reconciliation.auto_match` with `scope=bank` raises an error. |
| `status` | `VARCHAR(20)` | `running`, `completed`, `failed`, `cancelled`, `voided` |
| `period_start` / `period_end` | `DATE` | Optional date range |
| `agent_instance_id` | `UUID` | Link to agent instance |
| `total_items_scanned` | `INTEGER` | Payments processed |
| `items_matched` | `INTEGER` | Fully matched |
| `items_partially_matched` | `INTEGER` | Partially matched |
| `items_unmatched` | `INTEGER` | Unmatched |
| `items_skipped` | `INTEGER` | Below-threshold (manual review) |
| `total_amount_matched` | `NUMERIC(15,2)` | Total applied amount |
| `total_amount_unmatched` | `NUMERIC(15,2)` | Total unmatched amount |

#### reconciliation_items

Each row represents one matched pair or unmatched payment.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `BIGSERIAL` | Primary key |
| `reconciliation_run_id` | `BIGINT` | FK to reconciliation_runs |
| `source_transaction_id` | `BIGINT` | Payment transaction ID |
| `target_transaction_id` | `BIGINT` | Invoice transaction ID (NULL if unmatched) |
| `match_status` | `VARCHAR(20)` | `matched`, `partial`, `unmatched`, `credit_applied`, `manual_review`, `voided` |
| `match_method` | `VARCHAR(30)` | Algorithm pass that created the match |
| `match_confidence` | `NUMERIC(3,2)` | 0.00 -- 1.00 |
| `applied_amount` | `NUMERIC(15,2)` | How much applies to this invoice |
| `amount_difference` | `NUMERIC(15,2)` | Difference in functional currency |
| `is_applied` | `BOOLEAN` | Whether financials were updated |
| `variance_status` | `VARCHAR(20)` | `none`, `fx_posted`, `written_off`, `adjusted`, `pending_review` |

### Matching Patterns

- **1:1** -- One payment, one invoice: 1 reconciliation_items row
- **1:N** -- One payment, multiple invoices: N rows with same `source_transaction_id`, each with `applied_amount`
- **Partial** -- `applied_amount` < invoice total, `match_status = 'partial'`
- **Unmatched** -- `target_transaction_id IS NULL`

---

## Reconciliation Agent Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `scopes` | `["vendor", "customer"]` | Which scopes to process |
| `auto_apply_threshold` | `0.85` | Auto-apply matches at or above this confidence |
| `amount_tolerance_pct` | `1.0` | % tolerance for reference matching |
| `amount_tolerance_abs` | `5.00` | Absolute tolerance for reference matching, in the functional currency |
| `approx_tolerance_pct` | `5.0` | % tolerance for approximate matching |
| `date_range_days` | `90` | Date window for exact/approximate matching |
| `max_items_per_run` | `500` | Max payments per scope per run |
| `auto_post_fx_variance` | `true` | Auto-post FX gain/loss journal entries |

---

## Bills Collector Agent

After transaction reconciliation, some AP_PAYMENTs still have no matching AP_INVOICE -- the business paid but never received a bill. The `bills_collector_agent` identifies these orphaned payments and sends email reminders requesting documentation.

| Key | Default | Description |
|-----|---------|-------------|
| `min_payment_amount` | `50.00` | Skip payments below this |
| `lookback_days` | `90` | How far back to look |
| `reminder_intervals_days` | `[7, 14, 30]` | Escalation intervals |
| `max_vendors_per_run` | `100` | Max vendors per run |

---

## Reconciliation Status Report

```javascript
generate_report("reconciliation_status", {
  legal_entity_id: 9,
  bank_account_id: 123
})
```

---

## Common Scenarios

### Monthly Bank Reconciliation (Claude-Driven)

```javascript
// Step 1: Import statement
submit("bank_statement", "import", {
  legal_entity_id: 9,
  bank_account_id: 1,
  statement_date: "2026-01-31",
  opening_balance: 100000.00,
  closing_balance: 125000.00,
  lines: [...]
})

// Step 2: List unmatched lines
query("bank_statement_line", filters={ legal_entity_id: 9, bank_account_id: 1, recon_status: "unmatched" })

// Step 3: For each line, search for matching GL transaction
query("transaction", query="ACME SUPPLIES 1500")

// Step 4: Create match
submit("bank_statement_line", "match", {
  statement_line_id: 124,
  gl_transaction_id: 789,
  legal_entity_id: 9,
  notes: "Exact amount and date match"
})

// Step 5: Handle exceptions (bank fees, interest) with adjusting JEs
// Step 6: Verify completion
generate_report("reconciliation_status", {
  legal_entity_id: 9,
  bank_account_id: 1
})
```

### Automated Bank Processing (Agent-Driven)

```javascript
// After importing bank statement lines:
manage_connectors(action="process_bank_lines", bank_account_id=5, legal_entity_id=9)
// Agent processes all unmatched lines automatically
```

### Scheduled Transaction Reconciliation

The `reconciliation_agent` runs on schedule or manual trigger, matching all unreconciled payments to invoices across all entities. No manual intervention needed for high-confidence matches.

### Reviewing Manual Review Items

Low-confidence matches (below 0.85) appear in the admin dashboard at `/runs/bank-reconciliation/[id]`. Actions available:
- **Confirm** -- approve the match, apply financials
- **Write Off** -- dispose of a validated residual on an already-applied item, subject to the entity configuration
- **Reject** -- reject the match, reset payment recon_status

---

## Manual Transaction Reconciliation

Apply payments to invoices directly via Claude, without running the full reconciliation agent. Supports 1:1, 1:N (split), and partial matching.

### Apply Payment to Invoice(s)

```javascript
// 1:1 match
submit("reconciliation", "match", {
  scope: "ar",                          // or "ap" for vendor bills
  legal_entity_id: 9,
  source_transaction_id: 456,           // AR_PAYMENT transaction ID
  applications: [
    { target_transaction_id: 789, applied_amount: 1500.00 }
  ],
  notes: "Matched by amount and date"
})

// 1:N split -- one payment across multiple invoices
submit("reconciliation", "match", {
  scope: "ar",
  legal_entity_id: 9,
  source_transaction_id: 457,
  applications: [
    { target_transaction_id: 789, applied_amount: 1652.84 },
    { target_transaction_id: 790, applied_amount: 114.16 }
  ],
  write_off_amount: 0.01,
  notes: "Split payment with rounding write-off"
})

// Partial match -- payment $50 against invoice $100
submit("reconciliation", "match", {
  scope: "ap",
  legal_entity_id: 9,
  source_transaction_id: 100,           // AP_PAYMENT for 50
  applications: [
    { target_transaction_id: 200, applied_amount: 50.00 }
  ]
})
// Invoice 200: amount_due=50, status='partial', recon_status='partial'
// Remaining 50 will be matched by future payment
```

### Reverse a Match (Unmatch)

**Inspect before unmatching.** A status label on a document (`paid`,
`reconciled`, `confirmed`) tells you a match exists — not what it is. The
match record itself is a `reconciliation_item`; read it first:

```javascript
// What is this payment/expense matched against?
query("reconciliation_item", filters={ legal_entity_id: 9, source_transaction_id: 456, is_applied: true })
// What did this bill get settled by?
query("reconciliation_item", filters={ legal_entity_id: 9, target_transaction_id: 200, is_applied: true })
```

Then unmatch by the item's SOURCE transaction:

```javascript
submit("reconciliation", "unmatch", {
  scope: "ar",                          // "ap" for vendor-side matches
  legal_entity_id: 9,
  source_transaction_id: 456,
  reconciliation_run_id: 913,           // optional: only this run's matches
  reason: "Incorrect match"
})
// Reverses all applied matches, restores invoice financials
```

**Card-paid vendor bills (CARD_EXPENSE settlements).** When a corporate-card
charge pays a vendor bill, vendor reconciliation matches the card's posted
**CARD_EXPENSE GL transaction** (the card line's `posted_transaction_id`)
against the AP invoice — a normal payment→invoice match. Reverse it with
scope `"ap"` and the CARD_EXPENSE transaction as the source; this also
reverses the CARD_EXPENSE_RECLASS settlement journal:

```javascript
// Card charge CARD000352 → get_entity("card_transaction", 201).posted_transaction_id = 12705
submit("reconciliation", "unmatch", {
  scope: "ap",
  legal_entity_id: 40,
  source_transaction_id: 12705,         // the posted CARD_EXPENSE, NOT the card_transaction_id
  reason: "Matched against the wrong day's bill"
})
```

Do NOT confuse this with the card line's own `recon_status: "confirmed"` —
that only means "posted to GL". `scope: "card"` unmatch reverts that
confirmation (back to `pending_recon`) without touching GL or any bill
settlement.

### Dismiss (Close Without Match)

Mark a transaction as reconciled when no matching counterpart exists:

```javascript
submit("reconciliation", "dismiss", {
  scope: "ap",
  legal_entity_id: 9,
  transaction_id: 612,
  reason: "Invoice was in prior year (2024), AP closed at zero balance",
  category: "prior_period"
})
// Sets recon_status='dismissed', creates audit trail
```

**Use cases:**
- Payment for invoice from a prior closed period
- Small balance write-offs
- Duplicate transactions
- Manually settled outside the system

**Categories:** `prior_period`, `write_off`, `duplicate`, `other`

Dismiss is recorded as a workflow instance. The default definition has no
approval steps, no required permission, and runs in the green lane, so it
executes at once for anyone who can reach the entity. An organisation can set a
required permission or add an approval step in its own definition. A dismissed item
leaves every later reconciliation run, so give a reason a reviewer can check.

### Validation Rules

- **Match:** Source must be a payment type (AR_PAYMENT/AP_PAYMENT/etc.) and not fully reconciled; targets must be invoices with amount_due > 0; source and targets must belong to the same customer/vendor; total applied + write-off cannot exceed available payment amount; write-off subject to the configured entity limit
- **Dismiss:** Transaction must exist and not already be reconciled/dismissed; scope must be ap, ar, or card; reason is required (min 5 chars)

### Partial Matching Behavior

| Scenario | Invoice Status | Payment Status |
|----------|---------------|----------------|
| Payment = Invoice | `paid`, `reconciled` | `reconciled` |
| Payment < Invoice | `partial`, `partial` | `reconciled` |
| Payment across N invoices | Each fully/partially paid | `reconciled` |

---

## Variance Categories

### Timing Differences

- **Outstanding checks:** Issued in GL but not yet cleared at bank. Will appear next period.
- **Deposits in transit:** Recorded in GL but not yet credited by bank.

### Amount Differences

- **FX variances:** Exchange rate difference between invoice and payment date. Auto-posted by the reconciliation agent when `auto_post_fx_variance` is enabled; otherwise left for review.
- **Same-currency differences:** Discount, short payment, or fee adjustment. Requires manual review.
- **Rounding:** Differences <= 0.01 in the document currency are ignored.

### Errors and Omissions

- **Bank errors:** Duplicate charges, wrong amounts -- contact bank.
- **Book errors:** Duplicate entries, wrong GL amounts -- reverse and correct.
- **Bank fees / interest:** Items in bank not yet in GL -- post adjusting JE, then match.

---

## Bank Statement Line Status Values

| Status | Description |
|--------|-------------|
| `unmatched` | Imported, not yet matched to GL |
| `matched` | Linked to GL transaction via `gl_transaction_id` |
| `excluded` | Intentionally excluded (no GL posting needed) |
| `reconciled` | Statement finalized and locked |

## Transaction Recon Status Values

| Status | Description |
|--------|-------------|
| `NULL` | Never reconciled |
| `partial` | Partially matched (balance remains) |
| `reconciled` | Fully matched to corresponding invoice/payment |

---

## Best Practices

**Timing:**
- Reconcile bank statements weekly, not just monthly
- Complete month-end reconciliation within 5 business days
- Run transaction reconciliation agent after bank processing completes

**Documentation:**
- Save bank statements (PDF) for audit
- Document all matches with notes
- Record reasons for adjustments and exclusions

**Investigation:**
- Investigate variances above the organisation's investigation threshold (ask when none is set)
- Review all `manual_review` items in admin dashboard promptly
- Escalate unresolved items older than 30 days

---

*Last Updated: 2026-03-06*
*Related Resources:*
- [Bank Statements Management](bank-statements-management.md) - Importing and managing bank statements
- [Bank Accounts Management](bank-accounts-management.md) - Bank account setup
- [Transaction Processing](transaction-processing.md) - GL transactions
- [Payment Batch Management](payment-batch-management.md) - Payment runs

## Detailed evidence and recovery

For retained application receipts, configured write-off permissions, dated undo,
owned runs and cancellation, call `get_guidance("reconciliation-evidence")`.
The detailed [evidence and recovery reference](reconciliation-evidence.md) retains
these contracts and their local/deployment qualifications.


### Manual bank statement finalization — evidence gate (AR-476)

For `reconciliation.finalize` with `scope=bank`, manual finalization evaluates
exactly the balance, source coverage, posting bridge, exclusion evidence and
resolved-line controls used by automatic statement recomputation. A refusal
names the failed controls; repair the underlying evidence before retrying.
`force=true` retains its existing tentative exclusion of unmatched lines, but
cannot bypass those controls. If evidence fails, the transaction rolls back both
the exclusions and finalization. Successful finalization stores the evaluated
controls in statement metadata. This does not create ledger entries or alter
period-close policy. No built-in agent or saga is required.

This gate does not establish completion of AR-476's separate pending-review,
legacy-writer and deployment-readiness acceptance work. Statement finalization
is not a period lock or permission to bypass review and approval controls.

A manual finalizer rechecks statement status under its lock. If another writer
already finalized it, the later attempt refuses and preserves the committed
finalization record. This increment does not change automatic recomputation.

## Reverse-charge sign repair preview

`generate_report("reverse_charge_sign_repair_preview", params)` reads one scoped,
unsettled posted bill and projects a specific historical negative-credit VAT
sign correction. Required parameters are `legal_entity_id`, `transaction_id`,
`target_gl_line_id` and a nonblank `reason`; optional `dimension_filters` uses the
ordinary report filter syntax (maximum 20 selections). It requires `ap:write`
and the caller's entity access. The actor is taken from authentication.

The result contains `before`, `after`, the exact `expected_fingerprint`, and the
validated `request`. Monetary values are decimal strings. The fingerprint binds
server-read evidence and the actor/reason; it is not approval. Raw workflow
payloads and definitions are not returned. No financial data is written. Locks
are released before returning; busy or changed evidence requires a fresh preview.
The read has a 30-second operational limit and bounded lock waits. Preview does
not fence the shared workflow catalog; execution recomputes the fingerprint under
the admission fence before writing, and refuses newly changed evidence.

Pending payment-batch creation naming the invoice, or a pending add-line request
naming it as the source, blocks this repair even before batch lines exist.

The preview itself writes nothing. `repair_submission_available=true` means the
operation exists; `workflow_configuration_required=true` means the organization
must separately configure `transaction.repair_reverse_charge_sign` with a review
step. No workflow or approval policy is automatically activated.

Submit the returned `request` plus `expected_fingerprint` through
`submit("transaction", "repair_reverse_charge_sign", payload, idempotency_key=...)`.
Use the same key and unchanged payload for retries. Approval rechecks live access,
original request scope, and the complete booked evidence. Changed evidence refuses
the repair. After a failed approval, a fresh preview is allowed only when the
engine recorded rollback of that exact request and no committed repair activity
exists. Obtain a new preview and review, using a new key for the new request.
The original failed key stays held and never redispatches. A completed retry
returns the saved repair/audit receipt without another write. Pending requests,
older failures without rollback proof, and cancellations without proof remain
held; never bypass uncertain outcomes using a new key. Missing workflow or completed review evidence
refuses execution. Do not use ordinary transaction update, direct SQL or re-posting
as a substitute. Deployment of this capability must be verified before use. A preview does not establish that a
production repair has been approved or performed.
