# Vendor Contracts & Prepaid Expense Amortization

AR-474 capability guard: `recurring_contract.amend` refuses
nonempty `new_lines` when `effective_date` is in the future, before writing the
amendment or lines. The current writer cannot schedule economic revisions;
previously it applied those changes immediately. Same-day execution remains the
existing path, not proof of full effective-period/history correctness. Stored line
dates and empty amendment records do not schedule pricing. Direct line updates,
Stripe writers and all-writer economic history remain separate open work.

Direct `contract_line.update` also refuses `effective_date`: it cannot schedule
price, rate or quantity changes. Combining that field with supported edits fails
without applying them, including after approval. Omit it only when requesting an
immediate supported edit; this does not provide historical pricing revisions.


Dashboard line-read scope (AR-474): contract detail and standalone line lists
bind each returned line to the stored parent's authorized entity in the same SQL
read. Supplying an allowed entity with another entity's contract ID returns no
lines. Standalone lists retain active/inactive filtering and now include the same
`effective_window` and `beyond_contract_end` evidence as detail. This is read-only
evidence, not pricing policy.

Supported-line fidelity (AR-474): creating lines inline with a contract
preserves `usage_metric`, as standalone line creation already does. An explicitly
supplied `fixed_amount: 0` remains zero even when quantity/unit price are nonzero;
it is not treated as missing or recomputed. The contract total uses that zero
fixed amount. Standalone creation also returns zero in `fixed_amount`; null
means no fixed amount (for example, a usage line). Renewal preserves these supported values. This is input fidelity,
not a rule requiring zero charges or activating effective-dated pricing.
Both creation paths preserve an explicitly supplied `unit_price: 0`. For a fixed
line without a fixed amount, an explicit unit price derives quantity × price,
including zero. This does not assign a price when the caller omits it.
Inline and standalone creation use shared line storage and the same numeric rules: omitted quantity is
one, explicit null quantity is refused, and omitted/null price remains absent.
A fixed line needs a fixed amount or unit price; a usage line needs a unit price
(which may explicitly be zero). New numeric values must be finite and nonnegative.
Updates validate only supplied numeric fields: omission keeps the old value,
zero is valid, and null/negative/nonfinite inputs refuse. Numeric clearing is not
supported. Untouched legacy numeric fields are not revalidated by unrelated edits.
Amendments now use the same validator for supplied quantity, unit price and fixed
amount before writing any amendment or line. Zero remains valid; a bad value in
any line refuses the whole batch, including when executed after approval. This
change does not implement proration, credit adjustments or price history.
Successful amendments refresh the derived contract total from active fixed amounts
in the same transaction. An explicitly supplied contract value remains unchanged,
including explicit zero; it is not replaced by the derived sum.
Amendment-added lines now use shared new-line storage: supported item/description
aliases, quantity/rate/fixed amounts, usage metric, dimensions and entity-scoped
accounts follow the same contract as ordinary creation. Their start is the
amendment date and must fit the parent term. Nested line date-window fields
are refused rather than silently ignored or treated as a scheduling mechanism.
Existing-line amendment updates now use the same supported field writer as
ordinary updates: item/description aliases, quantity, rate, fixed amount, scoped
account, usage metric and charging method. Unsupported dimensions/date-window
changes refuse; omitted fields remain unchanged. Targets must belong to the
amended contract, including no-field requests. A no-field request counts as zero
updated lines. This does not implement historical economic revisions.
Amendment `new_lines`, when supplied, must be a list of objects, each with
`_action: add` or `_action: update`. Missing or unsupported actions refuse the
entire request before writes; they are never silently skipped. Empty or omitted
lines retain the existing record-only behavior and do not schedule changes.
New amendment records store version-1 `previous_values` and `new_values` with
selected actual contract/line values, including totals, in the same transaction.
Evidence-storage failure rolls back the amendment changes. Later ordinary line
edits do not rewrite those observations. Older empty records are not backfilled.
These observations are not effective-price revisions, a complete accounting
history or a claim of database-enforced immutability; no new read API is added.
Renewal copies the existing `delivery_config` and `auto_email_invoices` values
into the new draft, preserving null versus empty configuration. This retains
configured terms; it does not activate the draft or send an invoice.
For line descriptions, `item_description` and `description` must agree when both
are supplied. Standalone creation, inline creation and update reject conflicting
values instead of silently choosing one. Matching aliases remain supported.
`item_id` is an alias for the same **master item ID** as `master_item_id`, not
an entity-item row ID. Inline creation, standalone creation and update normalize
it to `master_item_id`; supplying different values is refused. Update results
name the persisted canonical field once. This adds no item-access bypass.
Line update and delete also accept `contract_line_id` as an alias for `line_id`.
Both names must agree if supplied together, and the target must be a positive
integer. The alias does not bypass the stored parent entity authorization.
For line accounts, `account_id` is a master-account ID resolved in the contract's
entity. Inline creation, standalone creation and update require the referenced
account to be active, non-header and available there. If `gl_account_number` is
also supplied, it must name that same account. An ID-based update stores and
reports `gl_account_number`; it does not silently ignore the ID.

Line create/inline/update refuse new values for `pricing_tiers`, `pricing_config`,
`unit_of_measure`, `price_currency`, `minimum_commitment_*`, `commitment_period`,
`billing_frequency_override`, `billing_interval_override`, `cost_*`, `sort_order`
and line `metadata`; these settings are not implemented by those operations.
Creation supports `is_active: true` only. Updates refuse `is_active` (use
`contract_line.delete` to deactivate) and `dimensions`. Existing legacy values
are retained on unrelated edits; this does not change account-specific policy.
Creation (inline or standalone) stores `dimensions` as an object mapping dimension
names to string value codes, or null. Renewal copies the stored dimensions,
including an empty object, without changing the original line. This is retention
of supplied data, not confirmation that those values are currently allowed:
invoice posting still applies its dimension validation. Updating line dimensions
remains unsupported in this contract.




New contract inline lines and standalone line creation reject explicit dates outside
the stored parent term, including dates after a finite contract end. Equal boundary
dates remain valid; omitted line ends are not silently filled or clamped. This
consistency check does not activate effective-dated billing or change renewal policy.


Inline usage-line retention (AR-474): `recurring_contract.create` retains each supplied
line's `usage_metric`, including through approval; renewal copies the stored metric
to the new draft. Omission remains absent. This corrects field persistence, does
not backfill existing lines and does not establish effective-dated pricing or
end-to-end metered invoice correctness.

Amendment target integrity (AR-474): an update targeting a missing line or a line
from another contract refuses and rolls back the entire amendment, including any
earlier line edits. It must not count a zero-row update as a changed line. This
does not add effective-dated pricing support.

A successful update with no fields also has a recoverable receipt, while retaining
`updated: false`, `fields_updated: 0` and `updated_fields: []`; it makes no contract
or line change. Amendment receipt recovery does not certify financial amendment
or effective-date semantics.

Approval success receipts (AR-474): successful contract-line create/update/delete
and contract update/activate/suspend/terminate/amend record explicit success receipts.
Retrying the same request after approval returns the saved outcome without
another domain write. Existing unknown receipts are not rewritten: reconcile
them under the original request identity. Approval and scope checks are unchanged.

Proration selection and renewal (AR-416 / AR-586): `proration_strategy` accepts
`full_period`, `daily_prorata` or `none` and retains that choice through approval
and draft creation. Omission retains the existing `full_period` default; explicit
null or unknown values refuse. Billing capability holds still apply. Daily proration rounds each fixed line
after applying the day ratio; preview sums those rounded amounts. Renewal retains
these terms on the new draft. A successful approved renewal records an explicit
success receipt so a retry of the same request can return the saved outcome.

This guide covers vendor contracts (prepaid expenses) and their amortization: creating vendor contracts, creating expense amortization schedules, running recognition, and viewing amortization runs. Prepaid expenses are first-class vendor contracts in this system -- same primitive as customer subscription contracts, different party.

---

## Overview

| Aspect | Detail |
|--------|--------|
| **Purpose** | Track vendor prepaid expenses and amortize them over the service period (matching principle) |
| **Party type** | `vendor` -- uses `vendor_id` on `recurring_contracts` |
| **Billing frequency** | Usually `once` for prepaid bills (annual hosting, insurance, 12-month licenses) |
| **Schedule kind** | `expense` |
| **GL pattern** | Each recognition period: DR Expense (target) / CR Prepaid Asset (source) |
| **Schedule prefix** | `EXP-YYYYMM-NNNN` |
| **Automatic flow** | Bill processor detects prepaid lines -> creates vendor contract -> creates schedule |
| **Manual flow** | User creates contract + schedule via `submit()` calls below |
| **Workflow object types** | `recurring_contract` (create, update, terminate, renew), `amortization_schedule` (create, update, recognize, cancel) |
| **Runs table** | `amortization_runs` -- every recognition caller gets a row here |

### Prepaid Expense Flow

```
Vendor bill received (e.g., 12-month software license)
  Post AP Invoice:
    DR 1400 Prepayments  1200
    CR 2100 AP           1200
        |
        v
Create vendor contract (party_type='vendor', billing_frequency='once')
  -> Anchors the amortization schedule to a named entity
        |
        v
Create amortization schedule (kind='expense')
  -> Generates monthly planned lines using daily proration (total 1200)
  -> Snapshots dimensions from the source GL line
        |
        v
Monthly recognition (amortization_recognizer agent or manual):
  DR 6960 Software & Subscriptions  <due tranche amount>
  CR 1400 Prepayments               <due tranche amount>
  -> Both legs carry the same financial dimensions
        |
        v
After 12 months: schedule status = 'completed'
  Prepayments balance -> 0 (fully amortized)
```

> **IMPORTANT -- Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete -- always check the schema first.

---

## Available Tools

| Tool | Purpose |
|------|---------|
| `submit("recurring_contract", "create", {...})` | Create a vendor contract |
| `submit("recurring_contract", "update", {...})` | Update contract details |
| `submit("recurring_contract", "terminate", {...})` | Terminate a vendor contract |
| `submit("recurring_contract", "renew", {...})` | Renew an expired contract |
| `submit("amortization_schedule", "create", {...})` | Create an expense amortization schedule |
| `submit("amortization_schedule", "recognize", {...})` | Run recognition (post JEs for due periods) |
| `submit("amortization_schedule", "update", {...})` | Update schedule accounts or description |
| `submit("amortization_schedule", "cancel", {...})` | Cancel outstanding planned lines |
| `get_entity("recurring_contract", id=X)` | Get contract details |
| `query("recurring_contract", filters={"legal_entity_id": X})` | List contracts (`party_type` is not a query filter: customer and vendor contracts come back together) |
| `generate_report("amortization_schedule", {"kind": "expense", ...})` | List/summarize expense schedules |
| `query("vendor", query="Acme")` | Find a vendor by name |

---

## Creating a Vendor Contract

**Workflow:** `recurring_contract.create`

Vendor contracts represent prepaid commitments. The `billing_frequency='once'` flag means this is a one-shot prepaid bill that doesn't generate recurring invoices.

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="recurring_contract", operation="create")

// Step 2: Find the vendor
vendors = query("vendor", query="Anthropic", filters={"legal_entity_id": 75})
vendor_id = vendors.results[0].master_vendor_id

// Step 3: Create the contract
submit("recurring_contract", "create", {
  party_type: "vendor",
  vendor_id: vendor_id,
  legal_entity_id: 75,
  contract_name: "Annual Claude API subscription 2025",
  start_date: "2025-01-01",
  end_date: "2025-12-31",
  billing_frequency: "once",         // one-shot, not recurring
  total_contract_value: 12000.00,
  currency_code: "EUR",
  notes: "Prepaid annual API credits"
})
// Returns: { recurring_contract_id: 5, contract_number: "CON-000002", party_type: "vendor" }
```

A supplied `contract_number` (e.g. the vendor's own reference) is honoured and must be unique on the legal entity — a duplicate is refused naming the existing contract. Omit it to get the next series number.

**Key fields:**
- `party_type` must be `"vendor"` (enforced by XOR constraint)
- `vendor_id` is required (not customer_id)
- `billing_frequency: "once"` is the standard for prepaid bills
- `end_date` is required when `billing_frequency='once'`

---

## Creating an Expense Amortization Schedule

**Workflow:** `amortization_schedule.create`

After the vendor contract exists and the AP invoice is posted, create the schedule:

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="amortization_schedule", operation="create")

// Step 2: Find the prepaid and expense accounts
accounts = query("account", query="prepaid", filters={"legal_entity_id": 75})
prepaid_account_id = accounts.results[0].master_account_id  // 1400 Prepayments

accounts = query("account", query="software", filters={"legal_entity_id": 75})
expense_account_id = accounts.results[0].master_account_id  // 6960 Software & Subscriptions

// Step 3: Create the schedule
submit("amortization_schedule", "create", {
  kind: "expense",                          // revenue or expense
  schedule_type: "straight_line",
  legal_entity_id: 75,
  source_transaction_id: 23235,             // the AP invoice ID
  related_entity_type: "recurring_contract",
  related_entity_id: 5,                     // the vendor contract ID
  start_date: "2025-01-01",
  end_date: "2025-12-31",
  total_amount: 12000.00,
  source_account_id: prepaid_account_id,    // DR side at bill time (1400)
  target_account_id: expense_account_id,    // DR side at recognition time (6960)
  currency_code: "EUR",
  description: "Amortize annual Claude API subscription",
  // Optional: dimensions snapshot (auto-resolved from source line if omitted)
  dimensions: { "department": "ENG", "project": "INFRA" }
})
// Returns schedule_id, schedule_code, periods, total_amount, first_period_amount,
// period_amounts: [{period_start, period_end, amount}, ...], status.
// amount_per_period is null when period amounts differ (daily proration/stubs).
```

**Important:** If you omit `dimensions`, the executor automatically resolves them from the source transaction GL line. You only need to pass them explicitly when the source line has no dimensions or you want to override.

---

### Source identity, splits and recognition dates

Read the posted source transaction and its GL before creating a schedule. Provide
`source_transaction_id` and, when needed, `source_gl_line_id` to identify exactly
one line in the entity/source account. `source_transaction_line_id` denotes the
source document line, not a GL ID. Ambiguous source lines are refused. The schedule
currency must match the source GL document currency. A source-less schedule cannot
provide this source-capacity protection; do not omit a known source to bypass it.

A second allocation requires `allow_source_split: true` and must fit remaining
source capacity. Changing the destination account does not create new capacity.
Paused commitments and posted portions of cancelled schedules still count.
Cancellation voids unposted lines; it does not undo recognition journals. Inspect
posted lines before replacing a cancelled schedule.

Use `schedule_type: "straight_line"`; unsupported calculation methods are refused.
Monthly amounts use daily proration and may vary. Creation returns `total_amount`,
`first_period_amount` and `period_amounts`; `amount_per_period` is populated only
when all periods are equal. Do not multiply the first stub by the period count.

Recognition keeps service dates and posts on the earliest open, unlocked date on
or after service-period end, no later than `as_of_date` or today. If none exists,
the line requires remediation/review. Journal posting and line consumption commit
atomically, including concurrent recognizers. A no-work scan is not a failure.


## Running Recognition

**Workflow:** `amortization_schedule.recognize`

Recognition posts journal entries for all schedule lines with `period_end <= as_of_date`. Every executed recognition attempt creates a row in `amortization_runs`; an idempotent replay returns the existing result.

```javascript
// Recognize due expense lines for entity 75 through February
submit("amortization_schedule", "recognize", {
  legal_entity_id: 75,
  as_of_date: "2025-02-28",
  kind_filter: "expense"
})
// Returns: { run_id, run_number, status, recognized_count, total_amount,
//            posted_transactions, errors, ... }
// Amounts follow the actual daily-prorated schedule lines.
```

**Targeted recognition** (for retries or specific schedules):
```javascript
submit("amortization_schedule", "recognize", {
  legal_entity_id: 75,
  as_of_date: "2025-06-30",
  schedule_ids: [3],                // only this schedule
  kind_filter: "expense"            // only expense schedules
})
```

**Dry run** (preview without posting):
```javascript
submit("amortization_schedule", "recognize", {
  legal_entity_id: 75,
  as_of_date: "2025-12-31",
  dry_run: true
})
// Returns lines_to_process count + preview, no JEs posted, still creates a runs row
```

---

## Querying Vendor Contracts

```javascript
// List the entity's contracts (party_type is not a query filter, so
// customer and vendor contracts come back together)
query("recurring_contract", filters={
  "legal_entity_id": 75
})

// Get a specific contract with related entities
get_entity("recurring_contract", id=5)

// List expense schedules for a contract (report returns full schedule rows,
// each carrying contract_id -- filter client-side for a single contract)
generate_report("amortization_schedule", {
  legal_entity_id: 75,
  kind: "expense"
})
```

---

## Amortization Runs

Use `query("amortization_run", filters={"legal_entity_id": 75})` for live run
status and `get_entity("amortization_run", id=run_id)` for details. Read schedules
with `query("amortization_schedule", ...)` / `get_entity("amortization_schedule", id=3)`
and lines with `query("amortization_schedule_line", filters={"schedule_id": 3})`.

`status` is the current projection; `execution_status` and execution counters
preserve the historical attempt. Later posting/cancellation can resolve an older
blocked run. An unresolved line with no live remediation becomes `needs_review`,
not a permanent wait. A posted line requires a live, unreversed recognition journal.

---

## Amortization Report

```javascript
generate_report("amortization_schedule", {
  legal_entity_id: 75,
  kind: "expense",               // filter to expense only
  status: "active"               // only active schedules
})
// Returns: {
//   summary: { total_scheduled: 12000, total_recognized: 2000, total_remaining: 10000, schedule_count: 1 },
//   schedules: [{ schedule_code, kind, total_amount, recognized_amount, remaining_amount, ... }]
// }
```

---

## Common Scenarios

### Scenario 1: Forward an annual software invoice

A vendor sends a 12-month software license invoice. The bill processor handles this automatically:

1. Bill arrives via email -> bill_processor classifies the line as `prepaid` (>= 90 days, >= 500 EUR)
2. bill_processor posts the AP invoice: DR 1400 Prepayments / CR AP
3. bill_processor delegates to master_data_agent to create a vendor contract
4. On callback, bill_processor creates the amortization schedule
5. The monthly recognizer agent posts JEs automatically

**You don't need to do anything manually.** The entire flow is automated.

### Scenario 2: Create a manual prepaid schedule

For a prepaid expense that wasn't auto-detected (e.g., paid via bank transfer, not a vendor bill):

1. Create the vendor contract: `submit("recurring_contract", "create", {...})`
2. Create the schedule: `submit("amortization_schedule", "create", {...})`
3. Recognition runs automatically on the 1st of each month

### Scenario 3: Check amortization status

```javascript
// How much prepaid expense is left to amortize?
generate_report("amortization_schedule", {
  legal_entity_id: 75,
  kind: "expense"
})
// -> summary.total_remaining tells you the unamortized balance
```

### Scenario 4: Cancel a schedule mid-term

The vendor contract was terminated early. Cancel the remaining planned lines:

```javascript
submit("amortization_schedule", "cancel", {
  schedule_id: 3,
  cancellation_reason: "Vendor contract terminated early",
  void_pending_lines: true
})
```

### Scenario 5: Recognition fails due to missing fiscal period

If the recognizer hits a missing fiscal period, it automatically:
1. Records the error with category `missing_fiscal_period`
2. Delegates to configuration_agent to create the period
3. Reloads the durable response and retries only an explicit fix with eligible lines remaining
4. Declined/no-change responses create or reuse a review task; they do not trigger a blind retry
5. Closed periods roll forward to the earliest eligible open date within the cutoff; they are not automatically reopened

---

## Financial Dimensions

Amortization schedules inherit dimensions from the source transaction line:

```javascript
// Create a schedule with explicit dimensions
submit("amortization_schedule", "create", {
  kind: "expense",
  dimensions: { "department": "ENG", "project": "ALPHA" },
  // ... other fields
})
```

Both the debit (expense) and credit (prepaid) legs of every recognition JE carry the same dimensions. This ensures:
- Project P&L correctly reflects the monthly expense
- Balance sheet (prepaid account) nets to zero per dimension when fully amortized

If `dimensions` is omitted, the executor resolves them from the source GL line automatically.

---

## Key Takeaways

1. **Vendor contracts are first-class** -- same `recurring_contracts` table as customer contracts, filtered by `party_type='vendor'`
2. **`billing_frequency='once'`** -- prepaid bills don't recur; they anchor a single amortization schedule
3. **Dimensions flow through** -- from source bill line to every recognition JE, both legs
4. **Runs are action-level, not agent-level** -- every executed recognition attempt creates a run row, regardless of who calls it; idempotent replays reuse the result
5. **Recovery is conditional** -- confirmed fixes may retry; unresolved or declined remediation requires a task response
6. **Bill processor automates everything** -- for invoices received via email, the full contract + schedule creation is handled automatically
7. **Always check schema first** -- call `get_submissions(action='schema', ...)` before `submit()` to discover required fields

---

End of Vendor Contracts & Prepaid Expense Amortization Guide

**Last Updated:** April 2026

**Related Resources:**
- [Customer Contracts & Revenue Recognition](customer-contracts-management.md) -- the revenue (AR) side of the same engine
- [Revenue Recognition Management](revenue-recognition-management.md) -- legacy guide for ASC 606 patterns
- [Cost Accruals Management](cost-accruals-management.md) -- COGS, expense accruals, general prepaid handling
- [Billing Management](billing-management.md) -- recurring billing runs for customer contracts

### Retrying recognition after a reviewed fix

A new worker execution or approved task response carries a new
`recognition_attempt_id`; redelivery of the same attempt retains that identity.
This allows a same-day retry after remediation without replaying the earlier blocked
result. Never rotate the identity merely to bypass a pending approval. Atomic
schedule-line consumption remains the duplicate-posting guard.

Configuration remediation must persist `response_data.status: "fixed"` on the
completed request. The recognizer reads that stored response and checks eligible
lines again. Declined, held or no-change outcomes require the review-task path;
the request being completed does not by itself authorize posting.

The 2026-09-23 platform release runs recognition through prepare/recognize/remediate/
finalize pipeline stages. Reviewed retries use the stored schedules and actor;
permissions and response version are checked again at journal posting. An approval
workflow can remain pending: that is a waiting outcome, not completed recognition.
The same durable task attempt resumes it without rotating the posting identity.
An agent preview performs no financial or task writes. Production deployment was
verified in PR #134; evidence is retained in the completed platform migration record.


### Contract workflow provenance (QA branch)

Contract detail's workflow summaries are limited to the current organization,
and each workflow definition must belong to that same organization. All matching
branches (contract ID, recurring-contract ID, and discovered-agent source) apply
the shared operational/domain/entity workflow read policy. A contract ID or linked
agent reference does not itself grant workflow access. Unreadable summaries are
omitted while the authorized contract remains available. Hosted and full-route acceptance remain separate from the isolated checks.


Contract provenance also filters its source schedule and transaction to the
contract's entity, applying stored transaction/reversal read authority before
returning bill facts. Source and downstream agents require the current company,
entity and execution read policy; delegated requests additionally use the shared
thread read policy. Trigger-event summaries require the same company and structured
payload authority. Malformed agent UUID references are ignored without hiding an
otherwise readable source bill. Authorized AP and payroll paths remain supported;
these read checks neither repair historical links nor grant write authority.


### Prepaid contract request reads (QA branch, not deployed)

For `create_vendor_contract` request and response metadata, an explicit source
bill must resolve to a same-entity AP invoice readable under the existing
transaction policy. Supplied vendor IDs use the master-vendor namespace and
must match the stored bill. Returned `contract_id`, `recurring_contract_id`,
`entity_id` and `result_id` aliases must agree and resolve to a vendor contract
in the same organization/entity; supplied vendor hints and any source bill
must match its master vendor (with the existing legacy vendor-ID fallback).
Explicit legal-entity hints must agree with the request.

These checks apply before Admin/MCP task rows, totals, pages, thread siblings
and supported virtual execution metadata. Missing, malformed or forbidden
explicit references withhold the task. Expired contracts remain readable
history. A generic contract request without a source bill retains its existing
read policy; the action alone does not add an AP grant requirement. Unrelated
actions do not acquire these field meanings. Read access does not certify
schedule completion, accounting effects or arbitrary copied narrative.


### Contract-detail line date evidence

`get_entity("recurring_contract", id=..., include_related=True)` returns retained
line dates plus `effective_window` (`start_date`, `end_date`, `is_empty`) and
`beyond_contract_end` on each included line. The window intersects the line's
stored dates with the current parent term; a null end is unbounded. When the
intersection is empty, `is_empty` is true and its crossed endpoints remain visible.
This is read-only evidence, not an instruction to invoice, prorate or amend.
A later parent-end shrink does not rewrite old lines. Explicit dates after that
end are flagged. The related list retains its existing truncation limit.
Direct `contract_line` single/batch reads and list/search queries expose the same
window fields. They inherit the stored parent contract entity restriction before
rows, counts and pagination are computed, including any narrower task scope.
The dashboard contract-detail response exposes the same `effective_window` and
`beyond_contract_end` evidence, computed from parent and line dates in one query.
Raw dates remain intact. This response addition does not add a dedicated UI
indicator or make the dates control invoice calculations.
A missing parent, missing parent entity or inaccessible parent does not expose
the line. No caller-supplied contract filter widens the entity boundary.

A new-line date outside a finite parent term raises the executor reason
`line_window_outside_term`, naming `end_date` and suggesting extending the parent
term or correcting the line dates. The reason alone is not a rollback certificate.
For initial contract/line creation, an acknowledged owned transaction rollback
can produce a definite `refused` / `no_effect` receipt bound to the exact request.
The internal gateway and MCP submit path persist and replay that receipt without
another workflow. Contradictory workflow/status/posted-record evidence prevents
a stored receipt from being treated as definite no-effect.
If receipt storage fails, the first response stays `posting_unknown`; the retained
in-progress claim blocks an immediate repeat (409), rather than executing again.
Preserve the original request identity and reconcile it; do not submit a new request
merely because a validation reason was logged. Delayed approval can recover the same refusal only from a committed failed-workflow
action whose proof matches the organization, workflow, the same operation and saved
execution payload. Missing, malformed or conflicting proof remains uncertain.
This does not turn an ordinary reviewer rejection into a rollback certificate.
MCP verification uses the real submit function with a bound synthetic identity,
not an external authentication provider.

Other contract-term refusals use the same definite receipt: `line_amount_required`
(a fixed line with neither `fixed_amount` nor `unit_price`, or a usage line without
`unit_price`), `line_account_unavailable` (the account is not active and available in
the contract's entity), `amendment_scheduled_line_changes` (an amendment dated after
today that carries `new_lines`) and `amendment_line_not_owned` (an amendment update
for a missing line or a line of another contract; the whole amendment rolls back, including its other
line edits). They apply to `contract_line.create` / `update` and
`recurring_contract.create` / `amend`, through both gateways and after a delayed
approval, and replay with the same reason under the original request identity.
`recurring_contract.renew` requires `new_start_date` (YYYY-MM-DD) at validation;
`new_end_date` is optional and cannot precede it. Other execution failures (not
found, wrong status, entity access, a renewed or expired contract) stay uncertain
outcomes until reconciled.

## Contract-line approval context (AR-614)

Dashboard review tasks for `contract_line.update` show a supplemental **Contract
line change** table: contract number/name, customer or vendor, line number and
existing description, with Current and Proposed values for supported submitted
fields. Amounts use the contract currency. Current values are read when context
is requested, not a frozen submission-time snapshot or a guarantee against later
changes. The existing Proposed update card remains available.

The read keeps existing task-access checks and restricts the source line through
its parent contract to the reader's allowed entities. A missing or inaccessible
line shows **Current contract line unavailable**, without exposing its identity
or fabricating an amount. Confirm the target and existing values before deciding.
This supplemental display does not grant authority, decide policy, or change
approval/execution controls. External workflows do not depend on this display.
When both description aliases are submitted, the supplemental table shows only
`item_description`, matching executor precedence over `description`.
A supplied `account_id` resolves to the proposed GL number only for an active,
non-header account in the stored parent entity. An unavailable account or a
conflicting supplied GL number shows a warning, not a verified account change.

Renewal applies `price_adjustment_percent` using decimal arithmetic to the copied
unit prices and fixed amounts. Existing database column precision still applies;
original line prices are unchanged. This does not choose an adjustment policy or
activate the renewed draft.


Renewal also preserves each copied line's stored `unit_of_measure`, including an
unspecified value, without changing the original line. This is retention of existing
terms, not support for new unit edits or automatic unit conversion. Renewal remains
a draft; other stored pricing/cadence fields require their own capability review.
Release status and verification evidence are tracked in the billing implementation plan and linked Linear tickets.
