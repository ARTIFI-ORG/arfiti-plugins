# Customer Contracts & Deferred Revenue Recognition

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
and contract update/activate/suspend/terminate/amend record explicit success receipts. Retrying the same request after approval
returns that saved result instead of an unknown-outcome warning. Existing saved
receipts are not rewritten; an older unknown result still requires reconciliation
under its original request identity. This does not change who may approve, the
chosen contract terms, or the total calculation.


Proration selection and renewal (AR-416 / AR-586): `proration_strategy` accepts
`full_period`, `daily_prorata` or `none` and retains that choice through approval
and draft creation. Omission retains the existing `full_period` default; explicit
null or unknown values refuse. Billing capability holds still apply. Daily proration rounds each fixed line
after applying the day ratio; preview sums those rounded amounts. Renewal retains
these terms on the new draft. A successful approved renewal records an explicit
success receipt so a retry of the same request can return the saved outcome.

## Contract term input capabilities (local, unreleased)

Header create/update refuses `billing_timezone` and `auto_post_invoices` writes:
legacy stored values do not control current billing. Header update also refuses
`billing_timing`, `proration_strategy` and `start_date`, which this update writer
does not implement. Their existing supported create values and renewal copies
remain unchanged. This is a capability limit, not an accounting rule against
changing terms; effective economic revisions remain separately designed work.

Line update refuses unsupported `effective_date`, `effective_from`, `effective_to`, `start_date`,
`end_date`, `recognition_method` and `amount` instead of silently dropping them.
Use supported `fixed_amount` for an existing immediate amount update; this does
not make that operation a scheduled amendment mechanism. If both `description`
and `item_description` are supplied they must agree and count as one update.

New inline lines persist their explicit date evidence, defaulting omitted start
to the new contract start rather than execution day. Standalone line create uses
the same alias/window resolver. Date aliases must agree; line end cannot precede
line start, and the existing no-before-contract-start check remains. New inline
and standalone lines also refuse a start or explicit end after a finite contract
end. Equality at the boundary is valid; an omitted line end stays unspecified,
and no date is silently clamped. Standalone creation reads the parent term under
the existing contract lock. This does not validate later parent-term edits or
activate effective-dated billing. Copied renewal
lines begin at the new term start, leaving original line dates intact; no old
line end is silently shifted into the new term. These stored dates do not activate
effective-dated pricing selection in billing. Supplied contract term ends cannot
precede starts on create, renew or update; a null end remains unbounded. Historical
and future terms are not prohibited by a clock rule, and evergreen does not
rewrite supplied dates. Existing renew expiry behavior remains unchanged.

Unknown unrelated input remains legacy-compatible; this is not a universal
extra-field rejection or an all-writer amendment fix. Import/connector effectivity,
active amendments, renewal lifecycle and deployed/custom definition rollout remain
open. No historical rows are backfilled and no production behavior is activated.

## Contract execution and supported update results (local, unreleased)

Contract and line writes enforce the target contract's stored entity scope.
Completion after approval re-checks the submitter's current authority and the referenced
workflow definition's configured permission at execution; the approver does not substitute
for the submitter. A legacy definition with no configured permission does not gain
a new domain-permission rule from this change. Agent-authored workflows retain
shared agent authorization. Header writes lock the contract; line writes take the
contract lock before the line lock.

Updates return an integer `fields_updated` and the persisted field names in
`updated_fields`; a no-op returns zero and an empty list. These results do not
mean every arbitrary input is supported. Discover the operation schema and read
back required values. Renewal preserves existing `billing_timing`,
`proration_strategy` and line `usage_metric`. It does not activate scheduled
amendments or change the meaning of line effective dates. Effective economic
amendments, imported billing history and definition rollout remain open in AR-474.


This guide covers the full customer revenue lifecycle: creating subscription contracts, recurring billing, deferred revenue recognition (ASC 606 / IFRS 15 compliant), recognition-policy considerations, proration, amendments, and amortization runs. All operations flow through `submit()` and produce a uniform audit trail.

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

## Overview

| Aspect | Detail |
|--------|--------|
| **Purpose** | Track customer commitments, bill on schedule, and recognize revenue when earned |
| **Compliance** | ASC 606 / IFRS 15 -- five-step model |
| **Party type** | `customer` -- uses `customer_id` on `recurring_contracts` |
| **Billing frequencies** | `weekly`, `biweekly`, `monthly`, `quarterly`, `semiannual`, `annually` |
| **Schedule kind** | `revenue` |
| **GL pattern (invoice)** | DR AR / CR Deferred Revenue (full amount upfront) |
| **GL pattern (recognition)** | DR Deferred Revenue (source) / CR Revenue (target) per period |
| **Schedule prefix** | `REV-YYYYMM-NNNN` |
| **Schedule calculation** | `straight_line` with daily proration; other methods are not implemented by this executor |
| **Frequencies** | `monthly`, `quarterly`, `annually` |
| **Automatic flow** | billing_run_agent generates invoices; amortization_recognizer posts recognition JEs |
| **Workflow types** | `recurring_contract` (create, activate, suspend, terminate, renew, amend), `amortization_schedule` (create, update, recognize, cancel), `billing_run` (execute, preview) |
| **Backward compat** | `revenue_schedule.*` aliases route to the same `amortization_schedule.*` executors |
| **Runs table** | `amortization_runs` -- every recognition caller gets a row |

### ASC 606 Five-Step Model

1. **Identify Contract** -- agreement with customer creating enforceable rights/obligations
2. **Identify Performance Obligations** -- distinct goods or services promised
3. **Determine Transaction Price** -- total consideration expected
4. **Allocate Price** -- to each performance obligation based on standalone selling prices
5. **Recognize Revenue** -- when (or as) each obligation is satisfied

### Deferred Revenue Flow

```
Customer signs 12-month SaaS contract (12,000 EUR)

  Invoice full year upfront:
    DR 1200 AR                  12,000
    CR 2500 Deferred Revenue    12,000
        |
        v
  Create revenue recognition schedule (kind='revenue', straight_line):
    -> Daily-prorated monthly planned lines totaling 12,000
        |
        v
  Monthly recognition (automated or manual):
    DR 2500 Deferred Revenue    <due tranche amount>
    CR 4000 Revenue             <due tranche amount>
    -> Both legs carry same financial dimensions
        |
        v
  After 12 months:
    Deferred Revenue balance -> 0
    Revenue fully recognized (12,000)
```

> **IMPORTANT -- Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete -- always check the schema first.

---

## Available Tools

| Tool | Purpose |
|------|---------|
| `submit("recurring_contract", "create", {...})` | Create a customer contract |
| `submit("recurring_contract", "activate", {...})` | Activate (start billing) |
| `submit("recurring_contract", "suspend", {...})` | Pause billing |
| `submit("recurring_contract", "terminate", {...})` | End the contract |
| `submit("recurring_contract", "renew", {...})` | Renew for a new term |
| `submit("recurring_contract", "amend", {...})` | Amend mid-term |
| `submit("recurring_contract", "update", {...})` | Update contract fields |
| `submit("contract_line", "create", {...})` | Add a line item |
| `submit("contract_line", "update", {...})` | Update a line item |
| `submit("amortization_schedule", "create", {...})` | Create a revenue recognition schedule |
| `submit("amortization_schedule", "recognize", {...})` | Run recognition (post JEs) |
| `submit("amortization_schedule", "update", {...})` | Update schedule settings |
| `submit("amortization_schedule", "cancel", {...})` | Cancel outstanding lines |
| `submit("billing_run", "execute", {...})` | Generate AR invoices |
| `submit("billing_run", "preview", {...})` | Preview what would be billed |
| `get_entity("recurring_contract", id=X)` | Get contract details |
| `query("recurring_contract", filters={"legal_entity_id": X})` | List contracts (`party_type` is not a query filter: customer and vendor contracts come back together) |
| `generate_report("amortization_schedule", {...})` | Amortization schedule report |
| `query("customer", query="Acme")` | Find a customer by name |

> **Note**: `revenue_schedule.*` workflow calls still work via backward-compat aliases. New code should use `amortization_schedule.*`.

---

## Creating a Customer Contract

**Workflow:** `recurring_contract.create`

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="recurring_contract", operation="create")

// Step 2: Find the customer
customers = query("customer", query="Acme Corp", filters={"legal_entity_id": 75})
customer_id = customers.results[0].master_customer_id

// Step 3: Create the contract
submit("recurring_contract", "create", {
  party_type: "customer",
  customer_id: customer_id,
  legal_entity_id: 75,
  contract_name: "Acme Corp SaaS subscription 2025",
  start_date: "2025-01-01",
  end_date: "2025-12-31",
  billing_frequency: "monthly",
  billing_day_of_month: 1,
  currency_code: "EUR",
  total_contract_value: 12000.00,
  auto_renew: true,
  notes: "Pro plan, 12-month term"
})
// Returns: { recurring_contract_id: 6, contract_number: "CON-000003", party_type: "customer" }
```

A supplied `contract_number` (e.g. the customer's own reference) is honoured and must be unique on the legal entity — a duplicate is refused naming the existing contract. Omit it to get the next series number.

---

## Adding Contract Lines

Contracts support per-line pricing with fixed, usage, and tiered types:

```javascript
// Fixed-price line
submit("contract_line", "create", {
  contract_id: 6,
  line_type: "fixed",
  item_description: "Pro plan monthly subscription",
  fixed_amount: 1000.00,
  gl_account_number: "4000",   // Revenue account
  is_active: true
})

// Usage-based line (API call overage)
submit("contract_line", "create", {
  contract_id: 6,
  line_type: "usage",
  item_description: "API calls (overage beyond 10k)",
  unit_price: 0.01,
  usage_metric: "api_calls",
  gl_account_number: "4010",   // Usage revenue account
  is_active: true
})
```

---

## Activating a Contract

Contracts start in `draft`. Activate to start billing:

```javascript
submit("recurring_contract", "activate", {
  contract_id: 6,
  legal_entity_id: 75
})
// Status -> 'active', next_billing_date set based on billing_day_of_month
```

---

## Billing Runs

Active customer contracts generate AR invoices via automated billing runs:

```javascript
// Preview what would be billed
submit("billing_run", "preview", {
  legal_entity_id: 75,
  billing_date: "2025-02-01"
})

// Execute billing run
submit("billing_run", "execute", {
  legal_entity_id: 75,
  billing_date: "2025-02-01"
})
```

Billing runs only process `party_type='customer'` contracts with `billing_frequency != 'once'`.

**Price basis.** Contract prices are net unless the contract states otherwise: the
customer's tax code adds VAT on top. A contract whose prices are the end price the
customer pays sets `prices_include_tax: true` on `recurring_contract.create` or
`update` (kept on `renew`); its invoices carve VAT out of the price instead. `false`
is VAT on top. Ask the user which basis a contract uses rather than assuming one.

---

## Recognition Methods

### 1. Straight-Line Recognition

Equal amount each period. Best for:
- SaaS subscriptions, software licenses (time-based), service contracts

```javascript
schema = get_submissions(action='schema', object_type="amortization_schedule", operation="create")

submit("amortization_schedule", "create", {
  kind: "revenue",
  schedule_type: "straight_line",
  legal_entity_id: 75,
  source_transaction_id: 24001,             // the AR invoice
  related_entity_type: "recurring_contract",
  related_entity_id: 6,
  start_date: "2025-01-01",
  end_date: "2025-12-31",
  total_amount: 12000.00,
  source_account_id: 2500,                  // Deferred Revenue
  target_account_id: 4000,                  // Revenue
  currency_code: "EUR",
  frequency: "monthly",
  description: "Rev rec for Acme Corp subscription"
})
// Creates 12 lines at 1,000 each
```

### 2. Milestone-Based Recognition

Revenue recognized upon achieving milestones. Best for:
- Consulting projects, custom development, implementation services

The unified schedule executor does not implement milestone calculation. Do not
submit `schedule_type: "milestone"` or expect `as_of_date` to recognize a chosen
percentage. Collect milestone acceptance evidence and follow the configured
approval/posting workflow for the earned amount; never substitute straight-line
recognition for a different contractual policy.

### 3. Usage-Based Recognition

Revenue as usage occurs. Best for:
- API calls, compute/storage, transaction-based pricing, metered services

```
Contract: API Access (pay-per-use)
Rate: $0.10 per call, 10,000 included

Month 1: 8,000 calls -> $1,000 (minimum applies)
Month 2: 15,000 calls -> $1,000 + $500 overage = $1,500
```

Usage-based revenue is typically recognized immediately when billed (no deferred component) -- no schedule needed.

### 4. Percentage-of-Completion

Revenue based on % complete. Best for:
- Long-term projects, construction, complex implementations

```
Project: ERP Implementation ($500,000)
  Month 3: 20% complete -> recognize $100,000
  Month 6: 50% complete -> recognize $250,000
  Month 9: 75% complete -> recognize $375,000
  Month 12: 100% complete -> recognize $500,000
```

### When No Schedule Is Needed

Monthly billing with monthly delivery -- revenue recognized immediately:
```
Jan 1: Invoice for January service
  DR 1200 AR       $100
  CR 4000 Revenue   $100
  -- Obligation satisfied same period, no deferral
```

No schedule needed when billing and delivery occur in the same period.

---

## Running Recognition

The unified engine handles both revenue and expense. Every executed recognition attempt creates a row in `amortization_runs`; an idempotent replay returns the existing result.

```javascript
// Recognize all due revenue lines through March
submit("amortization_schedule", "recognize", {
  legal_entity_id: 75,
  as_of_date: "2025-03-31"
})
// Returns: { run_id, run_number, recognized_count, total_amount, posted_transactions }

// Revenue-only recognition
submit("amortization_schedule", "recognize", {
  legal_entity_id: 75,
  as_of_date: "2025-03-31",
  kind_filter: "revenue"
})

// Dry run (preview, no JEs posted)
submit("amortization_schedule", "recognize", {
  legal_entity_id: 75,
  as_of_date: "2025-12-31",
  dry_run: true
})
```

### Journal Entry Per Recognition Line

```
DR 2500 Deferred Revenue     <due tranche amount>
CR 4000 Revenue              <due tranche amount>
  -> Both legs carry the same financial dimensions (project, department, etc.)
  -> metadata: {source, schedule_id, schedule_code, kind, related_entity_id, amortization_run_id}
```

---

## Schedule Line States

| Status | Description | Action |
|--------|-------------|--------|
| `planned` | Future recognition period | Recognized on next run when `period_end <= as_of_date` |
| `posted` | Recognition JE recorded | Verify the journal is still live and unreversed |
| `skipped` | Intentionally skipped | Manual review needed |
| Recognition error | Recorded on run; unposted line remains `planned` | Confirm remediation or resolve the review task |

---

## Proration and Amendments

### Mid-Period Upgrade

When a customer upgrades mid-contract:

```
Original: Standard ($1,000/month), Jan-Dec
Recognized through April: $4,000

Upgrade May 15 to Premium ($1,500/month):
  May 1-14: 14 days at Standard = $467
  May 15-31: 17 days at Premium = $823
  June-Dec: 7 months x $1,500 = $10,500

Create amended schedule for remaining term at new rate.
```

### Contract Amendment

```javascript
submit("recurring_contract", "amend", {
  contract_id: 6,
  legal_entity_id: 75
  // Amendment details per get_submissions(action='schema', ...)
})
```

---

## Bundled Products (Multiple Performance Obligations)

Per ASC 606, allocate the transaction price to each obligation and create separate schedules:

```javascript
// 1. Software license: straight-line over 12 months
submit("amortization_schedule", "create", {
  kind: "revenue",
  schedule_type: "straight_line",
  legal_entity_id: 75,
  related_entity_type: "recurring_contract",
  related_entity_id: 6,
  total_amount: 10000.00,
  source_account_id: 2500,
  target_account_id: 4000,
  start_date: "2025-01-01",
  end_date: "2025-12-31",
  frequency: "monthly",
  description: "Software license - 12 month term"
})

// Implementation services requiring milestone recognition are handled separately
// with acceptance evidence and the configured approval/posting workflow.
// Do not submit an unsupported milestone amortization schedule.
```

---

## Querying

```javascript
// List active contracts (party_type is not a query filter; filter by
// customer with master_customer_id when you know the customer)
query("recurring_contract", filters={
  "status": "active",
  "legal_entity_id": 75
})

// Get contract with related entities
get_entity("recurring_contract", id=6)

// List revenue schedules for a contract (report returns full schedule rows,
// each carrying contract_id -- filter client-side for a single contract)
generate_report("amortization_schedule", {
  legal_entity_id: 75,
  kind: "revenue"
})

// Deferred revenue report
generate_report("amortization_schedule", {
  legal_entity_id: 75,
  kind: "revenue",
  status: "active"
})
// summary.total_remaining = your total deferred revenue liability
```

---

## Common Scenarios

### Scenario 1: New SaaS customer onboarding

1. Create customer: `submit("customer", "create", {...})`
2. Create contract: `submit("recurring_contract", "create", {party_type: "customer", ...})`
3. Add line items: `submit("contract_line", "create", {...})`
4. Activate: `submit("recurring_contract", "activate", {...})`
5. Billing runs automatically on billing_day_of_month
6. Create revenue schedule after first invoice posts
7. Recognition runs automatically on the 1st of each month

### Scenario 2: Annual subscription paid upfront

```javascript
// 1. Invoice the full year
// (billing_run generates: DR AR 12,000 / CR Deferred Revenue 12,000)

// 2. Create recognition schedule
submit("amortization_schedule", "create", {
  kind: "revenue",
  schedule_type: "straight_line",
  frequency: "monthly",
  total_amount: 12000.00,
  start_date: "2025-01-01",
  end_date: "2025-12-31",
  source_account_id: 2500,
  target_account_id: 4000,
  // ...
})
// 12 daily-prorated monthly lines; read period_amounts rather than assuming equal months
```

### Scenario 3: Consulting project with milestones

Read the accepted milestones and contract allocation. The straight-line executor
cannot derive milestone or percentage-of-completion amounts. Use the configured
recognition approval process with that evidence; see the limitation above.

### Scenario 4: Customer churns mid-term

```javascript
// Terminate the contract
submit("recurring_contract", "terminate", {
  contract_id: 6,
  legal_entity_id: 75,
  reason: "Customer cancelled"
})

// Cancel remaining revenue schedule lines
submit("amortization_schedule", "cancel", {
  schedule_id: 4,
  cancellation_reason: "Customer contract terminated",
  void_pending_lines: true
})
// Voided amount returned; already-recognized stays posted
```

### Scenario 5: Check total deferred revenue

```javascript
generate_report("amortization_schedule", {
  legal_entity_id: 75,
  kind: "revenue"
})
// summary.total_remaining = deferred revenue liability balance
```

### Scenario 6: Multi-year contract

Create a separate schedule per billing year:

```javascript
// Year 1
submit("amortization_schedule", "create", {
  kind: "revenue",
  total_amount: 10000.00,
  start_date: "2025-01-01",
  end_date: "2025-12-31",
  // ...
})
// Repeat for Year 2 and 3 when those invoices are posted
```

### Scenario 7: Contract renewal

```javascript
submit("recurring_contract", "renew", {
  contract_id: 6,
  legal_entity_id: 75,
  new_start_date: "2026-01-01",
  new_end_date: "2026-12-31"
})
// Creates a new contract linked to the original, copies party_type + customer_id
```

---

## Workflow Quick Reference

| Workflow | Required | Notes |
|----------|----------|-------|
| `amortization_schedule.create` | `kind`, `legal_entity_id`, `start_date`, `end_date`, `total_amount`, `source_account_id`, `target_account_id` | Use `kind: "revenue"` |
| `amortization_schedule.recognize` | `legal_entity_id` | Optional: `as_of_date`, `schedule_ids`, `kind_filter`, `dry_run` |
| `amortization_schedule.update` | `schedule_id` | Only provided fields updated |
| `amortization_schedule.cancel` | `schedule_id` | Optional: `cancellation_reason`, `void_pending_lines` |
| `recurring_contract.create` | `party_type`, `customer_id`, `legal_entity_id`, `contract_name`, `start_date` | `billing_frequency` defaults to monthly; `billing_interval` (default 1) multiplies it; `billing_day_of_month` is refused for weekly/biweekly |
| `billing_run.execute` | `legal_entity_id`, `billing_date` | Only customer contracts with frequency != 'once' |
| `contract_line.update` (price) | `line_id` + new `quantity`/`unit_price`/`fixed_amount` | Optional `price_effective_from`; versions the line; before the next unbilled period only with `price_correction: true` + `correction_reason` (owner/admin decides; posts a difference document per billed period) |

---

## Key Takeaways

1. **ASC 606 compliance** -- recognize revenue when performance obligations are satisfied, not when invoiced
2. **Straight-line schedules only** -- milestone, usage and percentage-of-completion policies need their own supported approval/posting process
3. **Customer contracts drive both billing AND recognition** -- billing_run generates invoices, amortization_schedule tracks when revenue is earned
4. **`kind: "revenue"`** -- recognition JEs are DR Deferred Revenue / CR Revenue (opposite direction of expense schedules)
5. **One unified engine** -- customer and vendor schedules recognized in the same run, same `amortization_runs` table, same `submit()` API
6. **No schedule needed** for monthly-billed, monthly-delivered services (no deferral)
7. **Bundled products** -- create separate schedules per performance obligation per ASC 606 Step 4
8. **Dimensions pass through** -- from invoice line to every recognition JE, both legs
9. **Error recovery is automatic** -- missing fiscal periods / accounts delegated to remediation agents
10. **Always check schema first** -- call `get_submissions(action='schema', ...)` before `submit()`

---

End of Customer Contracts & Deferred Revenue Recognition Guide

**Last Updated:** April 2026

**Related Resources:**
- [Vendor Contracts & Prepaid Expenses](vendor-contracts-management.md) -- the expense (AP) side of the same engine
- [Billing Management](billing-management.md) -- recurring billing cycles, AR invoice generation
- [Cost Accruals Management](cost-accruals-management.md) -- COGS, expense accruals

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


### Billing usage task execution (2026-09-23 release)

Submit usage answers through the owning task response. Structured quantities need
no model call; prose is interpreted against the requested contract periods and
validated before any write. Recording usage may wait for workflow approval. The
task stays open until its owner verifies invoices for those periods. Superseded
responses and revoked human authority cannot authorize new effects. Preview makes
no business writes. Concurrent billing locks each contract and commits the invoice,
usage consumption, period advance and billing receipt together. Invoice-created
events address Invoice Delivery only; billing does not automatically charge a card.
Migration 611 enables usage-recording workflow definitions, preserving existing
organization definitions and approval settings. Deployment remains separate.

## Resume and recognition authority

Resume a suspended contract using `recurring_contract.activate` with `contract_id`.
This preserves the next-billing cursor and prior billed periods; normal date/line
validation still applies. It does not skip suspension periods or create invoices
itself. Preview billing before executing catch-up billing. Terminated contracts
cannot be activated. Activation/resumption records the acting user in metadata.
Amortization execution reloads the submitter's current permissions. Recognition
requires accounting posting authority; approval does not grant missing authority.
After permission repair, retry failed unposted schedule lines; do not create a
second schedule or bypass the permission check.

Recognition submitted by a human uses their current membership. Scheduled agent
recognition retains the persisted run authority and capability checks; it does
not require a human membership for the system service identity.


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

## Scoped billing hold decisions and evidence report (local, not activated)

`recurring_contract.record_hold_decision` records an explicit decision for one
contract/entity and inclusive `start_date`/`end_date`. Supply `decision_text`,
`reason`, `evidence_references` (receipt, episode, decision or external citation),
and `client_idempotency_key`; classification and same-scope `supersedes_id` are
optional. Treatment is free text scoped to the client. This does not post an
accrual/invoice, clear a hold, change terms/cursors or authorize period close.

Migration 756 installed the operation inactive; migration 866 turns the untouched
installation on in every organisation and in the template, so new organisations get
it active, with no approval step (Andrew, 31 Oct 2026). A review step can be added per
organisation through workflow administration; an organisation's own activation or
replacement is kept. Current `ar:write`, configured permission and actual stored entity
are checked for human and authenticated-agent callers, including delayed execution.
Exact replay returns the same record; changed input under the same key refuses.
Decision records and resolved evidence are immutable and retained after source
cleanup. Supersession preserves old decisions; concurrent branches are visible.
Evidence is limited to 65536 canonical UTF-8 bytes without truncation. External
citations are labelled caller-supplied, never certified documents.

`generate_report("billing_hold_list", {legal_entity_id, start_date, end_date,
section, limit, cursor})` requires current `ar:read` and entity scope. Sections are
`contracts`, `usage`, `tasks`, `decisions`; retrieve every section and follow its
`next_cursor` until `truncated=false`. Page counts are not full-selection totals.
Current S0 capability is distinct from historical receipt evidence; unsupported
service has no invented engine amount. Failure count greater than one is a factual
repeat label, not a policy threshold. Suspended/stub contracts, unbilled usage,
open tasks and retained decisions remain visible. Usage with no resolvable stored
contract has unknown entity ownership and is not disclosed by this entity report;
a separately authorized organization inventory is required. Missing or foreign
task subjects are not disclosed as IDs. Tasks with subjects outside the requested
period identify that count separately from unresolved periods.

Decision detail compares captured contract/line/reference evidence with live data,
labels changed/missing/unverified evidence, and exposes all superseding branches.
A recorded decision never implies the treatment was executed. Alerts' queued,
accepted or unknown delivery states remain separate. No global accountant policy
or human-only close requirement is installed. Schema/catalog/guarded definition
setup precedes code rollout; verify default new-organization cloning and preserve
custom approval settings. Production installation and activation are not performed
by this local change.

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
