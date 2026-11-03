# Expense Management

This guide covers employee expense reports: reimbursements, per-diem claims, and mileage claims. Expense reports flow through approval workflows, post to GL (DR Expense / CR Employee Payable), and get reimbursed via payment batches.

---

## Overview

| Aspect | Detail |
|--------|--------|
| **Submission channels** | Claude.ai chat, email receipts, admin dashboard |
| **Line types** | `reimbursement`, `per_diem`, `mileage` |
| **Default lane thresholds** | Report total, in the report's currency: under 500 Green, 500 to under 5,000 Yellow, 5,000 and over Red. Thresholds and each lane's approval steps are configurable per organisation; the submit() result is authoritative |
| **GL posting** | DR Expense accounts per line / CR Employee Payable (2150) |
| **Transaction type** | `EXPENSE_REPORT` in unified transactions table |
| **Payout type** | `REIMBURSEMENT_PAYOUT` -- DR Employee Payable / CR Bank (clears payable on payment) |
| **Reimbursement** | Employee's linked vendor -> AP aging -> payment proposal agent |
| **Currency** | Entity's functional currency (enforced -- no multi-currency on expenses/rates) |
| **Line requirement** | Every line MUST have either `item_id` or `account_number` (no hardcoded GL fallbacks) |

### Expense Report Lifecycle

```
Employee submits expense(s) via Claude.ai / email / admin dashboard
    |
    v
submit("expense_report", "create", {...})
    |
    v
ExpenseReportCreateExecutor -> creates expense_report + lines (status: draft)
    |
    v
submit("expense_report", "submit", {"expense_report_id": 42})
    |
    v
Workflow engine -> risk lane assessment -> approval if needed
    |
    v
On approval: ExpenseReportApproveExecutor
    -> calls ExpenseReportExecutor (transaction.post)
    -> EXPENSE_REPORT: DR Expense accounts / CR Employee Payable (2170)
    |
    v
Employee has payable balance -> payment proposal agent picks up
    |
    v
Payment batch -> bank transmits payment
    |
    v
Bank statement confirms payment -> payment_confirmation executor
    -> REIMBURSEMENT_PAYOUT: DR Employee Payable (2170) / CR Bank (1000)
    -> clears employee payable balance
```

### Three Line Types

| Line Type | Description | Key Fields |
|-----------|-------------|------------|
| `reimbursement` | Employee paid out-of-pocket, needs reimbursement | `amount`, `merchant_name`, `spend_date`, `receipt_url` |
| `per_diem` | Travel daily allowance based on configured rates | `country_code`, `city`, `per_diem_days`, `meals_included` |
| `mileage` | Distance-based reimbursement | `distance`, `distance_unit`, `vehicle_type`, `origin_location`, `destination_location` |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

> **Field Name Warning:** The workflow schema may return `expense_date` and `expense_type` as field names, but the executor requires `spend_date` and `line_type` respectively. Always use `spend_date` (not `expense_date`) for the date field on expense lines, and `line_type` (not `expense_type`) with values `reimbursement`, `per_diem`, or `mileage`.

---

## Creating Expense Reports

### Basic Reimbursement

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="expense_report", operation="create")

// Step 2: Submit with discovered fields
// Tip: Use validate_only=true to check payload before submitting
```
```
submit("expense_report", "create", {
    "legal_entity_id": 9,
    "employee_id": 5,
    "title": "Business Lunch - March 2026",
    "lines": [
      {
        "line_type": "reimbursement",
        "spend_date": "2026-03-01",
        "amount": 45.50,
        "merchant_name": "Restaurant Name",
        "description": "Client lunch meeting",
        "item_id": <EXP-MEALS item ID>,
        "receipt_url": "https://..."
      }
    ]
})
```

### Per-Diem Claim

Per-diem amounts are automatically calculated from configured rates.

```
submit("expense_report", "create", {
    "legal_entity_id": 9,
    "employee_id": 5,
    "title": "NYC Business Trip Per-Diem",
    "lines": [
      {
        "line_type": "per_diem",
        "spend_date": "2026-03-01",
        "country_code": "US",
        "city": "New York",
        "per_diem_days": 3,
        "meals_included": {"breakfast": true, "lunch": false, "dinner": false},
        "description": "NYC client visit Mar 1-3"
      }
    ]
})
```

The system will:
1. Look up the per-diem rate for US / New York
2. Apply meal deductions for included meals (breakfast provided by hotel)
3. Calculate: `days * daily_rate - meal_deductions`
4. Store the calculated amount and rate snapshot on the line

### Mileage Claim

Mileage amounts are automatically calculated from configured rates.

```
submit("expense_report", "create", {
    "legal_entity_id": 9,
    "employee_id": 5,
    "title": "Client Visit Mileage",
    "lines": [
      {
        "line_type": "mileage",
        "spend_date": "2026-03-01",
        "distance": 150.5,
        "distance_unit": "mi",
        "vehicle_type": "personal_car",
        "origin_location": "Office - 123 Main St",
        "destination_location": "Client HQ - 456 Oak Ave",
        "description": "Round trip to client office"
      }
    ]
})
```

The system will:
1. Look up the mileage rate for `personal_car` in miles
2. Apply tiered rates if distance exceeds threshold
3. Calculate: `distance * rate_per_unit` (or tiered calculation)
4. Store the calculated amount and rate snapshot on the line

### Mixed Report (Multiple Line Types)

```
submit("expense_report", "create", {
    "legal_entity_id": 9,
    "employee_id": 5,
    "title": "Chicago Trip - March 2026",
    "lines": [
      {
        "line_type": "mileage",
        "spend_date": "2026-03-01",
        "distance": 280,
        "distance_unit": "mi",
        "vehicle_type": "personal_car",
        "origin_location": "Office",
        "destination_location": "Chicago",
        "description": "Drive to Chicago"
      },
      {
        "line_type": "per_diem",
        "spend_date": "2026-03-01",
        "country_code": "US",
        "city": "Chicago",
        "per_diem_days": 2,
        "description": "Chicago per-diem Mar 1-2"
      },
      {
        "line_type": "reimbursement",
        "spend_date": "2026-03-01",
        "amount": 25.00,
        "merchant_name": "O Hare Parking",
        "description": "Airport parking",
        "item_id": <EXP-TRANSPORT item ID>
      }
    ]
})
```

---

## Managing Expense Reports

### Adding Lines to Existing Report

```
submit("expense_report", "update", {
    "expense_report_id": 42,
    "action": "add_line",
    "line": {
      "line_type": "reimbursement",
      "spend_date": "2026-03-02",
      "amount": 35.00,
      "merchant_name": "Taxi",
      "description": "Airport transfer"
    }
})
```

### Attaching a Receipt

```
submit("expense_report", "update", {
    "expense_report_id": 42,
    "action": "attach_receipt",
    "line_number": 1,
    "receipt_url": "https://files.example.com/receipts/abc123.pdf"
})
```

### Removing a Line

```
submit("expense_report", "update", {
    "expense_report_id": 42,
    "action": "remove_line",
    "line_number": 3
})
```

---

## Submitting for Approval

```
submit("expense_report", "submit", {"expense_report_id": 42})
```

### What Happens on Submit

1. **Validation**: All reimbursement lines checked for receipts (if policy requires). Every line must have `item_id` or `account_number`.
2. **Workflow routing**: Amount-based risk lane assignment (default thresholds on the report total; the organisation can change them and configures the approval steps each lane runs)
   - Green lane by default: under 500 (no approval step unless the organisation has configured one)
   - Yellow lane by default: 500 to under 5,000 (manager approval, where configured)
   - Red lane by default: 5,000 and over (multi-level approval, where configured)
3. **On approval**:
   - Each line's GL account is resolved via 3-tier logic (no hardcoded fallbacks):
     1. Direct `account_number` on the line
     2. `item_id` -> `v_items_effective.default_expense_account`
     3. Posting profile for `EXPENSE_REPORT` -> `debit_account_id`
     4. If none resolve -> `ValueError` (line rejected)
   - Posts via `ExpenseReportExecutor` (transaction type: `EXPENSE_REPORT`)
   - DR Expense accounts per line / CR Employee Payable (2170)
   - Updates status to `posted`
4. **Reimbursement**: Employee has payable balance -> payment proposal agent picks up -> payment batch -> bank payment
5. **Payout confirmation**: When bank statement confirms the payment, a `REIMBURSEMENT_PAYOUT` transaction is posted (DR Employee Payable 2170 / CR Bank 1000) to clear the payable balance

### Rejection

```
submit("expense_report", "reject", {"expense_report_id": 42, "reason": "Missing receipt for line 2"})
```

After rejection, the employee can update the report and resubmit.

### Cancellation

```
submit("expense_report", "cancel", {"expense_report_id": 42})
```

Cancellation only moves `draft`/`submitted`/`rejected` reports to `cancelled` (no
delete, keeps the row). To actually remove a report, use delete (below).

### Deletion

Permanently removes a report — and its GL document — for any state **up to posted**:

```
submit("expense_report", "delete", {"expense_report_id": 42, "reason": "duplicate"})
```

Behavior:
- `draft` / `submitted` / `rejected` / `cancelled`: deletes the report + lines.
- `approved` / `posted`: also hard-deletes the linked `EXPENSE_REPORT` transaction
  (full GL-line CASCADE, via `transaction.delete`). An already-removed transaction
  (orphaned posted report) is tolerated — the header is still cleaned up.
- reimbursed (any settlement on the linked transaction — `amount_paid > 0`, full
  or partial): **blocked** with an error. The cash already left the bank and is
  reconciled; deleting would orphan the payment application and reversing would
  falsely imply the cash returned. Unwind the payment deliberately (unmatch the
  reconciliation or reverse the payout) first. The check reads the transaction's
  settlement amounts, not the report's stored status — the row never advances
  past `posted`.

Direct + audit-logged (no approval workflow). Returns `{deleted, transaction_deleted,
was_orphan}`. Use for cleaning up erroneous or duplicate postings; for a *reimbursed*
report you must handle the payment unwind separately.

---

## Querying Expense Reports

### Search

```
query("expense_report", query="EXPR-000042")
query("expense_report", query="John Smith")
```

### List with Filters

```
query("expense_report", filters={
  "legal_entity_id": 9,
  "status": "submitted"
})
```

### Get Details

```
get_entity("expense_report", id=42)
```

Returns report header, all lines (with calculated amounts), and GL journal lines if posted.

### Aggregation

```
query(
  "expense_report", group_by=["status"],
  aggregates={"total_amount": "sum", "id": "count"},
  filters={"legal_entity_id": 9}
)
```

---

## Rate Configuration

### Per-Diem Rates

Per-diem rates are configured per legal entity, by country/region/city with effective dates. Currency is enforced to match the entity's functional currency.

**Key fields:**
- `country_code` (required): ISO 2-letter country code
- `region` (optional): State/province for more specific rates
- `city` (optional): City for most specific rates
- `daily_rate`: Full-day per-diem amount
- `first_last_day_rate`: Reduced rate for travel days (defaults to 75% of daily_rate)
- `breakfast_deduction`, `lunch_deduction`, `dinner_deduction`: Amounts deducted when meals are provided
- `tier_threshold_days` (optional): Day threshold for reduced rate (e.g., 20 days)
- `tier_daily_rate` (optional): Reduced daily rate after threshold (both must be set together)
- `effective_from` / `effective_to`: Date range for the rate

**Rate lookup priority** (per_destination): City-specific > Region-specific > Country-level.

Per-diem is calculated by a **date-aware engine** (`src/services/expenses/per_diem/`)
from the trip's dated segments and the entity's **per-diem policy** (the rule shape).
The policy's `reset_period` is what makes calendar rules expressible:

- `none` — flat / single rate, no day-count tier.
- `trip` — the tier day-counter runs across the whole trip.
- `calendar_month` — the tier day-counter **resets each calendar month** (e.g. Estonia:
  €75/day for the first 15 days of foreign travel per month, then €40).

Tier **amounts** live on the rate (`daily_rate`, `tier_threshold_days`,
`tier_daily_rate`); the policy carries the **shape** (`rate_basis`, `reset_period`,
`first_last_day_pct`, `deduction_basis`). Set tier amounts via `submit`:

```
submit("per_diem_rate", "create", {
    "legal_entity_id": 9,
    "country_code": "EE",
    "daily_rate": 75.00,
    "tier_threshold_days": 15,
    "tier_daily_rate": 40.00,
    "effective_from": "2026-01-01"
})
```

> **Now settable:** the tier fields (`tier_threshold_days` / `tier_daily_rate`) are
> accepted by `submit` — they were previously stripped by validation. `reset_period`
> and policy configuration (`per_diem_policies`) are rolling out; until an entity has a
> non-default policy, per-diem uses `reset_period='none'`.

**Worked example — Estonia, 27 Jun – 4 Aug** (policy `flat_foreign` + `calendar_month`,
€75 first 15 days/month then €40): June €300 + July €1,765 + Aug €300 = **€2,365** over
39 days — the €75 tier resets at each month boundary.

### Mileage Rates

Mileage rates are configured per legal entity, by vehicle type.

**Key fields:**
- `vehicle_type`: `personal_car`, `motorcycle`, `bicycle`, `electric_car`
- `rate_per_unit`: Rate per mile/km
- `distance_unit`: `mi` (miles) or `km` (kilometers)
- `tier_threshold` / `tier_rate`: Optional single-breakpoint tiered pricing (lower rate above threshold). A `tier_rate` of **`0`** is valid and means "stop compensating above the threshold" — it is not read as "no tier".
- `tiers`: Optional **multi-band** tiers `[{"threshold": 5000, "rate": 0.25}, {"threshold": 10000, "rate": 0.20}]` — base rate below the first threshold, then banded above each breakpoint (overrides `tier_threshold`/`tier_rate`)
- `max_amount_per_month`: Optional **amount ceiling per employee per calendar month** (see below)
- `effective_from` / `effective_to`: Date range

**Example**: IRS 2026 rate = $0.67/mile. Above 5,000 miles/year, reduced to $0.21/mile.
Multi-band example: €0.30/km, then €0.25 above 5,000 km, then €0.20 above 10,000 km.

#### Monthly cap vs distance tier — pick the right one

They are not interchangeable, and this is the most common mistake:

| | Applies to | Resets |
|---|---|---|
| `tier_threshold` | distance | **per line** |
| `max_amount_per_month` | amount | per employee per **calendar month** |

A tier cannot implement a monthly ceiling. Split a month into two lines, or two
reports, and each gets a fresh allowance. Any policy phrased as "at most X per
month" needs `max_amount_per_month`.

When the ceiling binds, the claim is **not rejected**. It is compensated down to
the employee's remaining headroom for that month, and the full original claim is
preserved in the line's `metadata.mileage_cap` (`claimed_amount`,
`compensated_amount`, `excess_amount`, `already_claimed_this_month`) so the
unreimbursed excess stays visible for any fringe-benefit assessment.

Headroom counts the employee's mileage lines across **all** their reports for
that month. Drafts hold their allowance; only `rejected` and `cancelled` release it.

The rate and the monthly ceiling are the entity's policy, usually following its country's
tax-free limits (e.g. Estonia; the country payroll role lists them). Set `rate_per_unit` and
`max_amount_per_month` from that policy, and ask the user when none is recorded.

### Calculation

**Neither per-diem nor mileage has a standalone calculation tool.** Both are computed
by the create executor when the line is created — one calculation path, so a preview
can never drift from the posting:

- **Per-diem**: from the trip's dated segments + the entity's per-diem policy
  (date-aware engine, including calendar-month resets).
- **Mileage**: from `distance` + `vehicle_type` against the configured mileage rate,
  including **distance tiers** (banded — the base rate up to the threshold, the
  reduced rate above; multiple bands supported) and then the **monthly amount cap**
  (`max_amount_per_month`) against what the employee has already claimed that
  calendar month.

To preview without committing, create a **draft** report and read the computed line —
a draft has no GL impact and can be cancelled.

---

## Expense Category Mapping

18 seeded expense items map to GL accounts via `default_expense_account` on `master_items`:

| Item Code | Category | Default GL Account |
|-----------|----------|-------------------|
| `EXP-MEALS-001` | Meals & Entertainment | 6100 |
| `EXP-MEALS-002` | Team Meals | 6100 |
| `EXP-TRAVEL-001` | Travel - Airfare | 6200 |
| `EXP-TRAVEL-002` | Travel - Lodging | 6200 |
| `EXP-TRAVEL-003` | Travel - Ground Transport | 6200 |
| `EXP-OFFICE-001` | Office Supplies | 6300 |
| `EXP-OFFICE-002` | Office Equipment | 6300 |
| `EXP-SOFTWARE-001` | Software Licenses | 6400 |
| `EXP-SOFTWARE-002` | Cloud Services | 6400 |
| `EXP-SOFTWARE-003` | SaaS Subscriptions | 6400 |
| `EXP-PROF-001` | Consulting Services | 6500 |
| `EXP-PROF-002` | Legal Fees | 6500 |
| `EXP-PROF-003` | Accounting & Audit | 6500 |
| `EXP-MKTG-001` | Advertising | 6600 |
| `EXP-MKTG-002` | Marketing Materials | 6600 |
| `EXP-UTIL-001` | Internet & Phone | 6700 |
| `EXP-UTIL-002` | Utilities | 6700 |
| `EXP-OTHER-001` | Miscellaneous Expenses | 6900 |

Every expense line requires either `item_id` (resolved to the item's `default_expense_account`) or an explicit `account_number`. There are no hardcoded GL account fallbacks -- if neither is provided, the system rejects the line with a clear error.

### MCC Code Mappings

Merchant Category Codes (from card transactions) are automatically mapped to expense items for categorization by the expense processor agent. For example, MCC `5812` (restaurants) maps to `EXP-MEALS-001`.

---

## GL Posting

### EXPENSE_REPORT Transaction

When an expense report is approved, the system creates a journal entry:

```
DR  6100 Meals & Entertainment     45.50  (line 1 - reimbursement)
DR  6200 Travel                   237.00  (line 2 - per diem)
DR  6200 Transportation           100.84  (line 3 - mileage)
    CR  2170 Employee Expense Payable    383.34  (total reimbursable)
```

**Debit account resolution** (3-tier, per line, no hardcoded fallbacks):
1. Direct `account_number` on the line -> use it
2. `item_id` -> query `v_items_effective.default_expense_account`
3. Posting profile for `EXPENSE_REPORT` -> `debit_account_id`
4. None found -> `ValueError` (rejected)

**Credit account**: Employee Expense Payable, resolved from posting profile or account 2170.

### REIMBURSEMENT_PAYOUT Transaction

When the bank statement confirms the reimbursement payment:

```
DR  2170 Employee Expense Payable   383.34  (clears payable from EXPENSE_REPORT)
CR  1000 Bank / Checking            383.34  (cash goes out)
```

- Debit account: same as EXPENSE_REPORT credit account (from posting profile)
- Credit account: resolved at runtime from `bank_accounts.gl_account_number`
- Transaction type code: `REIMBURSEMENT_PAYOUT` (category: payroll, direction: outflow, prefix: RPAY)
- Fires automatically when bank transaction processor matches statement line to payment batch

---

## Email-Based Submission

Employees can email receipts to the entity's receipts inbox (created at entity setup; find it with `query("entity_email")`):

```
receipts.<entity>.<org-slug>@mail.arfiti.com
```

The `expense_processor` agent:
1. Reads the attachment (PDF/image) via `read_attachment`
2. Classifies the document (receipt vs invoice)
3. Matches sender email to employee record
4. Creates an expense report with appropriate line items
5. Auto-submits if below the configured threshold

### Receipt vs Invoice

The agent differentiates receipts from invoices:
- **Receipts**: Small amounts, POS format, merchant name, no payment terms
- **Invoices**: Vendor details, invoice numbers, payment terms, due dates

Invoices are skipped by the expense processor (they belong to the `bill_processor` agent).

---

## Admin Dashboard

### Expense Reports Page

Navigate to **Transactions > Expense Reports** in the admin dashboard to:
- Browse all expense reports with status filters
- View report details, lines, and GL postings
- See summary statistics (total reports, submitted, approved, pending reimbursement)

### Expense Rates Page

Navigate to **Settings > Expense Rates** to view configured per-diem and mileage rates.

---

## Status Reference

| Status | Description |
|--------|-------------|
| `draft` | Created but not yet submitted |
| `submitted` | Submitted for approval |
| `approved` | Approved by manager (pre-posting) |
| `rejected` | Rejected, can be updated and resubmitted |
| `posted` | GL transaction posted (last stored status — the DB row never advances past it) |
| `paid` | Derived at read: the linked transaction is fully settled (`amount_due <= 0.01`) by a payment batch or reconciliation match. Reads report it; the stored row still says `posted` |
| `partially_paid` | Derived at read: part of the linked transaction is settled (`amount_paid > 0`, `amount_due > 0.01`) |
| `cancelled` | Cancelled, no further action |

---

*Last Updated: 2026-06-23 — per-diem pluggable calculator (date-aware engine + policies + calendar-month reset); tier rate fields now settable via submit.*
*Related Resources:*
- [Transaction Processing](transaction-processing.md) - GL posting and EXPENSE_REPORT transaction type
- [Employee Management](employee-management.md) - Employee records and vendor mappings
- [Receipts Management](receipts-management.md) - Receipt upload and validation
- [Payment Batch Management](payment-batch-management.md) - Reimbursement payment processing

### Reimbursement evidence access

Transaction and attachment reads for `REIMBURSEMENT_PAYOUT` require
`payroll:read`. AP-only access does not grant access to employee payout evidence.
The close check can assess exact payout references across periods without treating
unrelated employee details as matching evidence.

## Automated expense processing

The Expense Processor pipeline owns employee reimbursement and configured
per-diem/mileage claims; Bank processes feed transactions and Bill processes
company-paid card evidence. File content identifies a durable source, so repeated
uploads do not create another reimbursement. A draft or accepted workflow is not
proof of posting. Read the report and linked ledger result.

Approval waits resume from the original source. Unknown effects and stale report
versions require review; do not clear their receipt or invent a new source key.
Targeted receipt OCR failure can retain the file as uploaded, not verified.
Multiple matching lines require the intended report/line. Submission retains
current employee authority, receipt/rate/policy checks and configured approval.


### Owner delegation

Global wildcard/owner callers may submit reports for another employee. Restricted users retain employee ownership checks and explicit delegated roles; report policy and approval checks still apply.


### Submission result (PR #224, October 2026)

For inline approval and posting, `expense_report.submit` returns the completed
executor's `transaction_id` and `status: posted`. It does not replace that result
with the earlier submission receipt. Pending approval remains `submitted`, with
separate `workflow_status` and `lane`. Executor failures remain failures and must
not be reported as successful submissions. This change does not bypass expense
validation, spending limits, approvals or period controls.


### Fiscal-period protection when deleting a posted expense

The canonical transaction deletion executor rechecks the fiscal period inside
its database transaction, including calls made internally by expense_report.delete.
Closed or locked periods refuse deletion before report links or GL rows are
removed, even when an internal caller vouches for force. Affected period rows
remain locked against concurrent closing until deletion commits. Both documents
of a reversal pair are checked. Partial and full reimbursements remain separate
reasons to refuse expense deletion. These protections do not authorize deleting
posted documents or unwinding payments.


### Expense submission recovery (local AR-273 update; not deployed)

Expense submission keeps its request identity across uncertain outcomes, including
ordinary dashboard or external-tool submissions without a Saga. If replay
protection is unavailable, submission stops before the gate runs.

A validation refusal is definitive only when the gate's own transaction confirms
rollback. Its original reason is saved and replayed. Correct the report and make
a deliberate new submission: the dashboard already supplies a new attempt ID;
MCP callers may supply a new explicit idempotency key after a confirmed refusal.
A transport retry must keep the original identity. The Base agent's ordinary
same-payload API has no new-intent argument; deliberate fresh ordinary attempts
can use the supported MCP path. Bound agent task identities remain unchanged.

An undo restores the previous report status only when the server's exact attempt
fingerprint still matches, the report has no posting link, and no live submission
workflow owns it. A later edit/attempt, missing evidence, zero affected rows or
lost acknowledgement remains unresolved. Even `compensation_status: restored`
proves only the gate status restoration, not absence of a financial effect.

`posting_unknown` means reconcile the saved claim, report and workflow receipts.
Do not clear the claim, invent a new identity, reverse a posting or re-submit
based on elapsed time. Known transaction/workflow IDs remain evidence for review.
Lost gate acknowledgements without a saved fingerprint still require operator
reconciliation; there is no automatic historical repair or claim-reset operation.
A saved pending or unknown receipt with a trusted workflow ID may recover the
actual saved execution result without dispatch. Missing terminal results remain
unknown, with known report, transaction and workflow IDs preserved for review.
Strict receipt storage must update the exact current claim once; an unconfirmed
write remains unknown and never overwrites an earlier completed receipt.

These are integrity and recovery rules. Expense policy, rates, approval choices
and country/accountant preferences stay in their existing editable configuration.
