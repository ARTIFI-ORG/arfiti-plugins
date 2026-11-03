# Billing Management Guide

Proration arithmetic (AR-417 / AR-585): daily proration retains the day
ratio until each fixed line's monetary amount is rounded. Preview sums those
rounded line amounts, matching execution's line boundary, rather than rounding
an aggregate. Full-period/none choices and capability holds are unchanged.

## Durable billing alerts (AR-473 C, local implementation under verification)

Migration 754 adds retained billing observations, capability-hold episodes and
transactional email delivery records. New billing execution requires this storage
before allocating a run. A receipt and its alert ownership commit together; a
later subject failure cannot erase earlier committed subjects. Repeated observations
of one held episode reuse its alert; generic failed receipts each retain their own
alert. Successful observations can clear only the same known service period, and
both old and corrected terms remain available. Replaying an old receipt never
reopens a cleared episode. Existing billing-run cleanup does not delete this
separate evidence history.

The supported operations are `billing_alert.update` (explicit configuration),
`billing_alert.preview` (scoped configuration, delivery states and retained receipt
pages), and `billing_alert.retry` (re-evaluate an unattempted alert or retry a known
not-sent delivery). They require explicit entity scope and installed permission-
guarded definitions: AR write for update/retry and AR read for inspection. Current
execution identity is rechecked. Configuration explicitly supplies enabled state,
event kinds (`capability_hold`, `execution_failure`), sender and recipients.
**Without an explicit configuration an alert goes to the organisation's active owners
and admins who can access the entity** (AR-274; Andrew, 31 Oct 2026), from the
organisation's default sender (its verified domain, else Arfiti Notifications), for
both event kinds. An explicit configuration replaces that default; an alert already
bound to the default then waits as `awaiting_reauthorization` until retried. Only
when no owner or admin can be reached does an alert stay `awaiting_configuration`.
After configuration changes, explicitly retry an unattempted alert to bind it.
Inspection returns separate `next_alert_id`, `next_receipt_id` and
`next_attempt_id` cursors (including late provider observations) so
individual failures remain reachable beyond the first page.

The host scheduler processes pending alerts independently of agent credits. Each
attempt freezes sender, recipients, body/text, tags and provider key and checks
current configuration and its author's authority before committing a sending
marker. Later revocation cannot unsend a message already in flight. Provider
acceptance requires a message ID and is not proof of delivery. Unknown results,
expired sending leases or lost acknowledgements are held for reconciliation;
there is no automatic resend based on an assumed provider deduplication window.
Known not-sent outcomes use bounded retry/backoff and become visibly failed when
exhausted. Retrying cannot change an attempted destination or silently create a
new provider key. Existing direct agent failure mail is suppressed only by actual
committed receipt/outbox ownership, not by a supplied flag.

**Deployment order and rollback:** install migration 754, workflow catalog and
explicit guarded definitions first; verify every tenant and template, including
new-organization cloning, before releasing receipt-writer code. Missing storage
fails billing before run allocation; never weaken that check for rolling deploys.
Drain old billing workers before enabling configured dispatch. Rollback preserves
all episode/receipt/outbox/attempt evidence. Stop the new worker and retain the
legacy-email ownership suppression compatibility fix, or prevent the old direct
failure-mail path from sending during rollback. An old binary without that guard
can duplicate an accepted or uncertain alert; it is not a safe automatic rollback.
Do not reset unknown messages, provider keys or attempted payloads to make rollback
appear successful. No deployment/rollback action is performed by this plan.

These local changes have not activated any provider, recipient configuration or
production worker. New durable alerts do not decide whether held service should
be billed, accrued or waived. Hold-decision operations and improved calendar
arithmetic remain separate unfinished work. Database failure before durable
capture can only surface as an operational/unknown outcome, not guaranteed mail.


## Billing capability checks (AR-473 S0, local, unreleased)

Shared billing execution and preview now evaluate whether existing arithmetic can
safely represent the stored terms. Weekly, biweekly, monthly, quarterly, semiannual
and annual cadences with any `billing_interval` of 1 or more are supported when the
cursor/period and receipt history agree (cadence periods below); `once`, `custom`, a
missing or non-positive interval, and a weekly or biweekly contract that also stores
a `billing_day_of_month` are held.
Unsupported cadence, a next-period gap/overlap, uncovered service before the cursor,
and contradictory receipt identity produce named capability findings. This is an
engine limitation, not a country rule or a decision that the service is free.
An exact live receipt skips only an independently resolvable supported period;
legacy monthly-shaped receipts do not certify weekly or multi-interval terms.
Final finite terms remain clipped and retain the existing nominal-end cursor rule.

### Cadence periods (AR-463)

One period is `billing_interval` units of `billing_frequency`: weekly 7 days,
biweekly 14 days, monthly 1 month, quarterly 3 months, semiannual 6 months, annually
12 months. `weekly` with `billing_interval: 2` and `biweekly` with interval 1 both bill
fourteen-day periods. Preview, execution, the next billing date, daily proration and
the period-close billing check all use this one calculation.

- **Weekly and biweekly** periods run back to back from the contract start: the first
  period starts on `start_date`, each next one the day after the previous period ends.
  A day of the month does not apply; `recurring_contract.create` refuses
  `billing_day_of_month` with these cadences, and a stored row that has one is held.
- **Month-based** periods start on the anchor day (`billing_day_of_month`, default 1),
  clamped to each month's last day (AR-1009; Andrew, 1 Nov 2026): an anchor of 31 gives
  31 Jan, 28 Feb, 31 Mar, 30 Apr. A period ends the day before the next anchor date.
- **First period:** every chain starts on `start_date`. A start off the anchor gets a
  short first period up to the day before the first anchor (start 15 Sep, anchor 1:
  15–30 Sep, then 1 Oct onwards), priced against the full period it belongs to:
  `daily_prorata` bills 16/30. **Under `full_period` (the default) a short first period
  bills the whole amount**, as that strategy always has. Only a contract's first period
  may be short: a short period after billed ones (a cursor left on the old 28th cap, a
  manual `next_billing_date` edit, a changed billing day) is held as `anchor_transition`
  for review instead of being invoiced.
- **Contract end:** the last period is clipped to `end_date`. `proration_strategy`
  decides the amount: `daily_prorata` bills the clipped days over the full period's
  days (ten days of a fourteen-day period bills 10/14), `full_period` bills the whole
  period's amount. That choice is the contract's stored term, not a product default.
  **A fixed term that starts off the anchor therefore bills one more full charge under
  `full_period`**: 15 Sep 2026 – 14 Sep 2027, anchor 1, bills 15–30 Sep, Oct–Aug and
  1–14 Sep 2027, 13 charges for 12 months. Choose `daily_prorata`, or start the term on
  the anchor day, when the term's total must equal its monthly price × months.
- **When a period is due:** in advance, once it has started; **in arrears, once the run's
  billing date reaches the period's last day**, and the invoice carries that date
  (AR-1009). A run never creates an in-arrears invoice ahead of its date.
- **Catch-up:** one run bills every due period, oldest first, up to **12 per contract**.
  Each extra period is billed in a further round, which is its own billing run, and each
  contract is billed in its own transaction. A contract stops at its first period that
  does not bill. The result lists `billing_run_ids` and `catch_up_rounds`; preview lists
  each contract's `due_periods` (amounts are for the first). A task-bound run bills the
  one period its usage proof covers.
- **Changing cadence:** `recurring_contract.update` accepts `billing_frequency`,
  `billing_interval` and `billing_day_of_month`; the change applies from the next unbilled
  period. A weekly or biweekly cadence needs `billing_day_of_month: null`. Only the
  recurring cadences are accepted (`once` and `custom` are refused). Fixed line amounts are
  charged per period and do not follow the cadence (100 a month moved to quarterly bills
  100 a quarter), so a frequency or interval change on a contract with fixed lines is
  refused until the caller restates the amounts with `contract_line.update` and resends
  with `per_period_amounts_confirmed: true`.
- **Term provenance:** `metadata.term_provenance` records each billing term as `entered`
  (supplied) or `default` (the product default applied).
- **Renewal:** a renewed contract's first period starts on its new start date.

A held subject produces a failed receipt with `terms_snapshot.capability`, without
an invoice, usage consumption or cursor advance. Other supported subjects may
commit. Preview reports the same observed facts without writing and still requires
execution rechecking. Evidence remains bounded by the existing 16 KiB snapshot
limit: excessive receipt-ID evidence fails closed rather than being truncated or
converted to a successful hold receipt. A failed evidence write is an unknown
outcome requiring inspection, not permission for a blind retry.

For authenticated billing-task callbacks, the saved command's complete subject set
and periods are checked under sorted contract locks before each usage effect and
before billing allocation. An already-billed or stale task period requires review;
it does not record usage into a different period. Earlier committed usage is not
undone or represented as having never happened. Standalone usage recording remains
available without the built-in agent. Authority/storage failures retain their
existing conservative outcomes.

Optional pipeline 1.0.2 preserves named usage failure reasons in its final result
and uses the existing source-bound delayed refusal reader. It is registered but
not activated. Retained 1.0.0 and 1.0.1 still stop unsafe effects, but can display a
generic usage failure summary; upgrade and drain verification are release gates
before claiming named-reason coverage for all agent paths. No definition is changed
by this implementation. Durable alert delivery, hold decisions, new calendar
arithmetic and editable usage-finality policy remain separate unfinished work.


## Per-contract execution evidence (AR-473 prerequisite A, local, unreleased)

New billing execution requires migration 752 before allocating a run or invoice.
Each new `billing_run_contracts` receipt stores a versioned `terms_snapshot`;
legacy receipts retain null evidence and must be read as terms not captured.
Preview creates no receipt. Snapshot data is bounded to 16 KiB of UTF-8 JSON per
receipt, rather than accumulated into the run metadata. It records the header
terms read under the contract lock, the current period-engine revision and cursor,
resolved timing/proration/payment terms, and actual saved invoice/posting/due dates
when an invoice was created. Proposed dates and not-resolved/not-saved fields are
explicit. This does not certify that legacy period calculations implement every
stored interval or anniversary option.

A billed receipt commits with the invoice and cursor advance. Skipped outcomes
commit with their locked-term observation. A failed attempt gets a separate
receipt after rollback, retaining only privately captured attempted terms; failure
before capture records not resolved instead of rereading changed terms. A receipt
write failure propagates as an unknown outcome; the run is marked failed if that
write succeeds. Earlier subjects may already have committed, so inspect receipts
before retrying. No new no-effect proof or permission to retry blindly is added.

Evidence cannot be updated, including by cancellation. Retry writes a new receipt;
original snapshots remain unchanged. Existing explicit billing-run deletion still
removes receipts for runs eligible for deletion: this is update immutability while
the receipt is retained, not a permanent audit archive. A conflicting receipt for
the same run/contract is refused unless every saved field and snapshot agrees.
Old writers may still create null snapshots during a rolling deployment; rollout
must not claim universal capture until all billing workers use the new code.

This prerequisite does not implement unsupported-period holds, reliable alert
delivery, hold-resolution approval, or new usage-date policy. Existing legacy date
and payment-term defaults are observed, not endorsed as universal accounting rules.

## Billing input compatibility matrix (local, unreleased)

Execute and preview accept `legal_entity_id`, `legal_entity_ids`, `contract_ids`,
`customer_id`, `billing_date`, `auto_post`, `auto_post_invoices`, `dry_run` and
`notes`. Retry additionally requires `billing_run_id`; an explicit retry date
must equal its source run date. IDs are positive JSON integers, lists are
non-empty, dates are exact valid `YYYY-MM-DD`, and flags are JSON booleans.
Posting flags accept only `true`; execution `dry_run` accepts only `false`.
Use the preview operation for planning. No universal future-date prohibition
is introduced. Omitted fields differ from explicit null: null business values
are refused. Notes accept strings, including empty strings, and are persisted
in run metadata; completion merges its summary without replacing existing
metadata. Preview does not persist notes.

Unknown business fields are refused by name before allocation. Known legacy
scheduler, saga and task callback envelope fields remain inert compatibility
data; they never establish actor, organization or approval authority. Nested
job business restrictions must agree with effective submitted restrictions;
retained 1.0.0 cannot silently discard a nested contract/customer/date filter.
A nested legacy default entity must agree with the effective entity; billing
schedules refuse this per-run override before emitting events.
Server `_billing_task` binding retains its separate authority and replay checks.

Billing pipeline 1.0.3 (which carries the 1.0.1 scope handling, the 1.0.2 named usage outcomes and the 1.0.3 durable waits and authenticated attribution), the shipped default since AR-274, sends canonical business payloads and reads its
actual saved event. Recognized saved scheduler and dashboard/MCP scheduled-job
run-once envelopes normalize their absent-scope sentinels; arbitrary caller
null or empty scope is still refused. A legacy dashboard Run once event that names
the first entity and a different multi-entity list is refused. The integrated
billing Run once producer now emits one singleton-scoped event per selected
entity in a single transaction; it never reduces the requested list to the
first entity. This dispatch queues work and does not prove invoice completion. Per-run notification, assignment and
default-entity configuration overrides are explicitly unsupported by
1.0.3: edit the agent configuration instead. Existing authored configuration
remains supported. The old `emit_delivery_events` and `emit_payment_events`
booleans are inert compatibility values; they do not control invoice events.
Retained 1.0.0 blocks and global runner behavior are unchanged. In particular,
runner `state.config` merging does not make billing blocks' `context.config`
read per-run overrides. Inventory existing job payloads/custom pipelines before
rollout. A definition with an active revision keeps its pinned pipeline until the
1.0.3 release is published and activated for it; one without an active revision
reads the shipped `pipeline.yaml` and runs 1.0.3 once deployed.

### Usage record rollback evidence (local, unreleased)

`contract_usage.record` now has its own bounded rollback evidence. Only explicitly
owned usage checks after source authority validation can create it, and only after
the executor's full transaction rollback is acknowledged. The result binds the
organization, explicit entity, contract line, exact payload and any reviewed
billing-task source. It means this recording attempt made no change; previously
recorded or billed usage remains intact. Batch recording, update and delete are
not certified by this proof. Missing explicit entity, authorization/tamper failures,
storage errors, nested transactions and uncertain transaction exits remain
unproved. Keep request identity and known record IDs when reconciling uncertainty.

Delayed approval stores the proof with terminal workflow state. A response becomes
definitive only after that receipt commit is acknowledged; replay checks the
same workflow, source and payload and rejects contradictory successful evidence.
Human usage execution rechecks the submitter's current authority and the saved
workflow definition's configured permission. Existing definitions with no configured
permission do not acquire a new universal permission floor. The optional billing
1.0.1 pipeline consumes this exact usage proof separately from billing execute
preflight; a later billing refusal never erases earlier usage. Existing 1.0.0 stays
unchanged. No country/accountant policy, pipeline activation or production repair
is introduced.


Local billing 1.0.1 is an explicit opt-in candidate; retained 1.0.0 is unchanged.
Only bound execute preflight evidence can establish a no-billing-effect refusal.
Approval receipt recovery requires committed, matching evidence; missing/conflicting
receipts stay unknown. Preserve request identity after uncertainty. Usage recording has a separate bounded owned-transaction proof; retry and partial
invoices are not certified by billing execute preflight.


## Exact billing request scope and scheduled dispatch (local, unreleased)

Billing workflows re-check the current submitter authority and the referenced
definition’s configured permission when execution starts, including after approval.
Approval does not replace revoked entity access. This does not add a permission
floor to legacy definitions with no configured permission or serialize concurrent
RBAC edits through commit.

Execute and retry require one unambiguous authorized entity. Preview may cover
multiple authorized entities. Omitted filters differ from explicit empty lists:
`contract_ids: []` and `legal_entity_ids: []`, malformed IDs and contradictory
contract/customer/entity restrictions are rejected. Execute and preview apply
both contract and customer filters. Execute validates before creating a run or
allocating its number; retry retains the original run's entity and cannot widen
an empty failed-contract selection into all contracts. Requested unsupported
posting modes (`auto_post: false`, `dry_run: true`) are rejected; use preview for
planning. This does not change contract calendar or invoice-date policy.

Billing schedules re-read the current saved job, definition identity, payload and
entity scope at fire time. Missing/disabled/changed bindings emit no event; failed
reads never use stale captured arguments. Event creation and last-run marking
commit together. Only a verified stored legacy empty entity array normalizes to
unspecified scope; arbitrary request arrays do not. Other agent families and
agentless schedules keep their existing behavior. This does not cancel events
already emitted or billing already running.


This guide explains how to manage customer pricing, subscriptions, and recurring billing in the AI-Native ERP system.

---

## Overview

The billing system provides two complementary approaches for customer billing:

1. **Customer Special Pricing** - Price lookup table for negotiated discounts
2. **Recurring Contracts** - Full subscription and automated billing management

**What you can do:**
- Set up customer-specific prices and discounts
- Create subscription contracts with fixed or usage-based billing
- Run automated billing to generate invoices
- Manage prepaid wallets for customer credits
- Handle mid-term upgrades, downgrades, and amendments

---

## Choosing the Right Approach

### Decision Matrix

| Scenario | Use `customer_item_pricing` | Use `recurring_contracts` |
|----------|:---------------------------:|:-------------------------:|
| Customer gets 50% discount on orders | Yes | No |
| Negotiated price for specific item | Yes | No |
| Monthly SaaS subscription | No | Yes |
| Track API usage and bill monthly | No | Yes |
| Track seat count (users) | No | Yes |
| Prepaid credits that auto-deduct | No | Yes |
| Auto-generate invoices on schedule | No | Yes |
| Mid-period upgrades/downgrades | No | Yes |

### Key Differences

| Aspect | Customer Special Pricing | Recurring Contracts |
|--------|--------------------------|---------------------|
| **Purpose** | Price lookup table | Full subscription management |
| **Automation** | None (manual invoicing) | Auto-generates invoices |
| **Usage Tracking** | No | Yes (seats, hours, API calls) |
| **Billing Schedule** | N/A | Daily/Weekly/Monthly/Quarterly/Annual |
| **Prepaid Wallets** | No | Yes |
| **Proration** | No | Yes (mid-period changes) |

### When to Combine Both

Use BOTH when a subscription customer also has negotiated pricing:

```
Example: SaaS Customer with Volume Discount

1. customer_item_pricing: ACME Corp gets 20% off
   - Item "API Access" standard: $1,000/month
   - ACME special price: $800/month

2. recurring_contracts: Monthly subscription
   - References item "API Access"
   - Uses customer's special price ($800)
   - Auto-bills monthly
```

---

## Customer Special Pricing

### What is Customer Special Pricing?

The `customer_item_pricing` table stores negotiated prices and discounts. It answers: "What price does Customer X pay for Item Y?"

### Database Schema

```
customer_item_pricing (
    id                  SERIAL PRIMARY KEY,
    legal_entity_id     INTEGER NOT NULL,
    item_id             INTEGER NOT NULL,      -- Entity-level item ID
    customer_id         INTEGER NOT NULL,      -- Entity-level customer ID
    price               NUMERIC(15,2),         -- Fixed price override
    discount_percent    NUMERIC(5,2),          -- OR percentage discount
    effective_from      DATE,                  -- Start date
    effective_to        DATE,                  -- End date (NULL = no end)
    notes               TEXT,                  -- Agreement notes
    created_at, created_by, updated_at, updated_by
)
```

### Key Fields

| Field | Description | Example |
|-------|-------------|---------|
| `price` | Fixed price override | $80.00 |
| `discount_percent` | Percentage off standard | 20.00 (= 20% off) |
| `effective_from` | Start date | 2025-01-01 |
| `effective_to` | End date (NULL = permanent) | 2025-12-31 |

**Note:** Use either `price` OR `discount_percent`, not both. If both set, `price` takes precedence.

### Available Workflows

| Workflow | Purpose | When to Use |
|----------|---------|-------------|
| `customer_item_pricing.create` | Create special pricing | New negotiated price |
| `customer_item_pricing.update` | Update pricing | Change price/dates |
| `customer_item_pricing.delete` | Remove pricing | Revert to standard |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

### Workflow: customer_item_pricing.create

**Required Fields:**
- `item_id` (integer) - Entity-level item ID
- `customer_id` (integer) - Entity-level customer ID
- `legal_entity_id` (integer) - Legal entity
- `price` (decimal) - Customer-specific unit price

**Optional Fields:**
- `discount_percent` (decimal) - Discount percentage (0-100)
- `effective_from` (date) - Start date (defaults to today)
- `effective_to` (date) - End date (null = no end)
- `notes` (text) - Pricing agreement notes

**Example:**
```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="customer_item_pricing", operation="create")

// Step 2: Submit with discovered fields
submit("customer_item_pricing", "create", {
    "legal_entity_id": 13,
    "customer_id": 456,
    "item_id": 101,
    "price": 80.00,
    "effective_from": "2025-01-01",
    "effective_to": "2025-12-31",
    "notes": "Annual volume discount - 20% off"
})
// Tip: Use validate_only=true to check payload before submitting
```

### Workflow: customer_item_pricing.update

**Required Fields:**
- `id` (integer) - Pricing record ID

**Optional Fields:**
- `price` (decimal) - New price
- `discount_percent` (decimal) - New discount
- `effective_from` (date) - New start date
- `effective_to` (date) - New end date
- `notes` (text) - Updated notes

### Workflow: customer_item_pricing.delete

**Required Fields:**
- `id` (integer) - Pricing record ID to delete

**Optional Fields:**
- `deletion_reason` (text) - Reason for deletion

### Pricing Lookup Hierarchy

When invoicing, prices are looked up in this order:
1. `customer_item_pricing` (customer-specific price)
2. `item_prices` (standard item prices by date range)
3. `items.unit_price` (default item price)

---

## Recurring Contracts

### What is Recurring Billing?

Recurring billing automates subscription invoicing for customers on regular billing cycles.

### Key Concepts

| Term | Definition | Example |
|------|------------|---------|
| **Contract** | Customer subscription agreement | Annual SaaS license |
| **Billing Frequency** | How often to bill | Monthly, Quarterly, Annual |
| **Billing Run** | Batch invoice generation | Generate all monthly invoices |
| **Usage-Based** | Charge based on consumption | API calls, storage GB |
| **Prepaid Wallet** | Customer credit balance | $5,000 prepaid |
| **Proration** | Partial period billing | Mid-month upgrade |

### Contract Lifecycle

```
draft → active → (suspended) → terminated/completed/renewed
```

| Status | Description |
|--------|-------------|
| `draft` | Being configured, not yet billing |
| `active` | Currently billing |
| `suspended` | Temporarily paused |
| `terminated` | Cancelled early |
| `completed` | Ended naturally at end_date |
| `renewed` | Replaced by new contract |

### Available Workflows

**Contract Management:**

| Workflow | Purpose |
|----------|---------|
| `recurring_contract.create` | Create new subscription |
| `recurring_contract.update` | Update contract details |
| `recurring_contract.activate` | Start billing |
| `recurring_contract.suspend` | Pause billing |
| `recurring_contract.terminate` | Cancel contract |
| `recurring_contract.amend` | Mid-term upgrade/downgrade |
| `recurring_contract.renew` | Renew expiring contract |

**Contract Lines:**

| Workflow | Purpose |
|----------|---------|
| `contract_line.create` | Add line to contract |
| `contract_line.update` | Update line item |
| `contract_line.delete` | Remove line |

**Billing Runs:**

| Workflow | Purpose |
|----------|---------|
| `billing_run.execute` | Generate invoices |
| `billing_run.preview` | Preview without generating |
| `billing_run.retry` | Retry failed contracts |
| `billing_run.cancel` | Reverse a run's invoices + reset billing dates so the period can be re-billed |
| `billing_run.delete` | Purge a run record + junction rows (housekeeping; refused for runs with live invoices — reverse or cancel first) |

**Billing Run Features:**

| Feature | Description |
|---------|-------------|
| Usage-Based Billing | Includes unbilled usage from `recurring_contract_usage` for usage-type lines |
| Customer Tax Profiles | Applies tax exemptions or default tax codes from `customer_tax_profiles` |
| Customer Dimensions | Propagates customer dimensions to invoice header as defaults |
| Duplicate Billing Protection | Prevents re-billing the same contract for the same period |
| Proration Calculation | Prorates fixed amounts for partial periods (based on `proration_strategy`) |

**Prepaid Wallets:**

| Workflow | Purpose |
|----------|---------|
| `prepaid_wallet.create` | Create customer wallet |
| `prepaid_wallet.credit` | Add funds |
| `prepaid_wallet.debit` | Remove funds |
| `prepaid_wallet.close` | Close and refund |

---

## Contract Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

### recurring_contracts Table

**Required Fields:**
- `legal_entity_id` (integer) - Legal entity
- `customer_id` (integer) - Customer ID
- `contract_name` (string, max 255) - Contract name
- `start_date` (date) - Contract start
- `billing_frequency` (enum) - weekly, biweekly, monthly, quarterly, semiannual, annually (or once)
- `billing_interval` (integer, default 1) - billing_frequency units per period (weekly + 2 = every two weeks)
- `currency_code` (string, 3 chars) - Currency (USD, EUR, etc.)

**Optional Fields:**
- `end_date` (date) - Contract end (null = evergreen)
- `contract_type` (enum) - subscription, usage_based, hybrid
- `billing_timing` (enum) - `in_advance` | `in_arrears`. Controls the invoice/posting/due date relative to the service period: `in_advance` dates the invoice at **period start** (subscriptions), `in_arrears` at **period end** (usage-based). Defaults from `contract_type` (`usage_based` → `in_arrears`, else `in_advance`). The date passed to `billing_run.execute` only selects which contracts are due — it never sets the invoice date.
- `evergreen` (boolean) - Auto-continues without end
- `auto_renew` (boolean) - Auto-renew at term end
- `billing_interval` (integer) - Every N periods
- `billing_day_of_month` (integer) - Day of month to bill (1-28)
- `payment_terms_code` (string) - Payment terms (net_30, etc.)
- `notes` (text) - Contract notes

### recurring_contract_lines Table

**Required Fields:**
- `contract_id` (integer) - Parent contract
- `master_item_id` (integer) - Item being sold
- `line_type` (enum) - fixed, usage, tiered, minimum

**Optional Fields:**
- `item_description` (string) - Line description
- `quantity` (decimal) - Quantity (for fixed)
- `unit_price` (decimal) - Price per unit
- `fixed_amount` (decimal) - Flat fee per period
- `usage_metric` (string) - Metric name (api_calls, storage_gb)
- `gl_account_number` (string) - Revenue GL account
- `start_date` (date) - Line start
- `end_date` (date) - Line end
- `pricing_tiers` (jsonb) - Tiered pricing array

---

## Billing Run Details

### Duplicate Billing Protection

The billing run prevents re-billing the same contract for the same period:

```
If billing run executed again for same period:
- System checks billing_run_contracts junction for (contract, period) match
- Skips with warning "Already billed: <invoice_number>" if a 'billed' row
  with a non-reversed/non-voided transaction exists
- No duplicate invoice created
```

Reversal-and-rebill is supported: once the original transaction is reversed (status='reversed'), the duplicate check ignores it and the next billing run can re-bill the same period.

### Cancelling a Billing Run

`billing_run.cancel` automates reverse-and-rebill. For the given run it reverses every posted invoice, rolls each affected contract's `next_billing_date` back to that run's `period_start` (and clears `last_billed_date`), and marks the run cancelled. A later `billing_run.execute` then re-bills the same period with convention-correct dates (see `billing_timing`).

```python
submit("billing_run", "cancel", {
    "billing_run_id": 123,
    "cancel_reason": "Wrong invoice date — re-billing"  # optional
})
```

- **Atomic:** the reversals run inside the cancel's transaction — if any step fails, the whole cancel rolls back (no partial state).
- **Approval:** routed through the workflow engine — yellow lane, single admin approval by default (configurable per org).
- **Refuses paid invoices:** if any billed invoice is `paid`/`partially_paid`, cancel aborts with no changes and lists the blockers. Reverse the payment manually first, then cancel.
- **Refuses runs with nothing to cancel:** a run that produced no billed invoices (a `partial`/skipped run, or one whose invoices are already reversed/cancelled) is rejected with a clear message instead of a no-op status flip.
- Typical flow: **cancel → approve → re-run billing.** A "Cancel run" button is also available on the billing-run detail page in the admin dashboard.

> Reversing a billing-run invoice — via cancel **or** a standalone `transaction.reverse` — automatically releases the period's usage back to `recorded`, rolls the contract's `next_billing_date` back, and marks the invoice's `billing_run_contracts` row `cancelled`, so billing history stays consistent.

- **Phantom 'billed' rows** (junction row `billed` but `transaction_id IS NULL`, from pre-fix runs that "billed" a usage contract with no usage): there is no invoice to reverse, so cancel reopens the consumed period directly — `next_billing_date` rolls back to the row's `period_start` and the row is marked `cancelled`. Such contracts appear in `contracts_reset` with `"phantom": true`.

### Deleting a Billing Run

`billing_run.delete` is the housekeeping counterpart to cancel: where cancel keeps the run as history, delete removes the run record and its `billing_run_contracts` junction rows entirely — for purging cancelled/failed/phantom runs that clutter the billing-runs list.

```python
submit("billing_run", "delete", {
    "billing_run_id": 11,
    "delete_reason": "Phantom €0 run — clutter"  # optional
})
# Returns: { "success": true, "deleted": true, "run_number": "BR-000010", ... }
```

- **Refuses runs with live invoices** (any junction transaction not reversed/voided/cancelled) — deleting them would orphan the invoice's billing history and break the reverse cascade. Reverse the invoice (or cancel the run) first, then delete.
- **Refuses runs still `running`.**
- **GL is never touched** — invoices, reversals, and postings stay in `transactions`; only the run's operational record is removed.
- **Approval:** yellow lane, single admin approval by default (configurable per org).

### Period Stamping on Invoice Lines

Recurring-invoice lines automatically include the service period in the description:

```
Contract line item_description: "Consulting Services"
Invoice line description:        "Consulting Services (2026-05-01 to 2026-05-31)"
```

Applies to both `usage` and `fixed` line types. Tier name (when present) appears after the period:

```
"Consulting Services (2026-05-01 to 2026-05-31) [Tier 2]"
```

No template syntax to learn — the engine unconditionally appends `(period_start to period_end)` after whatever's in `recurring_contract_lines.item_description`. Matches the convention used by NetSuite, Xero, and QuickBooks for subscription/recurring lines.

To rewrite the line description on an already-issued invoice (e.g. bare lines from before this change), use `submit("transaction", "update", {...})`.

### Customer Data Propagation

**Customer Tax Profiles:**
- Looks up `customer_tax_profiles` for customer + entity
- `tax_exempt = true` → Lines marked as tax exempt
- `default_tax_code_id` → Applied to lines without explicit tax
- Contract prices are NET unless the contract says otherwise: the run sets the tax code, and VAT goes on top (72 × €7 under a 24% code = €504.00 + €120.96 VAT). A contract with the term `prices_include_tax: true` (set on `recurring_contract.create` / `update`, kept on `renew`) bills its prices as the end price with VAT carved out (€504.00 = €406.45 + €97.55); `false` or unset keeps VAT on top, unless the tax code itself is marked `is_tax_inclusive`.

**Customer Dimensions:**
- Queries `customer_dimensions` for customer + entity
- Adds as header-level dimensions on invoice
- Lines inherit dimensions for GL posting

### Proration Strategies

| Strategy | Behavior |
|----------|----------|
| `full_period` | Bill full amount regardless of start date (default) |
| `daily_prorata` | Prorate based on active days / total days |
| `none` | Same as full_period |

Example: Contract starts Jan 15, billing period Jan 1-31
- Active days: 17, Total days: 31
- Proration factor: 17/31 = 0.548
- $1,000 monthly → $548.39 prorated

---

## Usage-Based Billing

### Recording Usage Data

**Workflows:**

| Workflow | Required Fields | Description |
|----------|-----------------|-------------|
| `contract_usage.record` | `contract_line_id`, `usage_date`, `quantity` | Record single usage data point |
| `contract_usage.batch_record` | `legal_entity_id`, `usage_records` | Batch import multiple usage records |
| `contract_usage.update` | `usage_id` | Update unbilled usage record |
| `contract_usage.delete` | `usage_id` | Delete unbilled usage record |

**Database Columns:**
| Payload Field | Database Column | Description |
|---------------|-----------------|-------------|
| `usage_date` | `usage_period_start` | Start date of usage period |
| `usage_period_end` | `usage_period_end` | End date (optional, defaults to usage_date) |
| `external_reference_id` | `source_reference` | Deduplication key |
| `unit_of_measure` | `unit_of_measure` | Metric name (entities, storage_gb, api_calls) |

**Auto-Population of unit_of_measure:**
If `unit_of_measure` is not provided in the payload, it auto-populates from the contract line's `usage_metric` field. This ensures tier matching works correctly without requiring the metric name in every usage record.

**Example: Single Usage Record**
```javascript
submit("contract_usage", "record", {
    "contract_line_id": 456,
    "usage_date": "2025-01-15",           // Maps to usage_period_start
    "quantity": 4,
    "unit_of_measure": "entities",         // Optional if line has usage_metric set
    "external_reference_id": "usage-2025-01-15-entities",  // Deduplication
    "source": "api"                        // Optional: workflow, api, import
})
```

**Example: Batch Import (1000+ records)**
```javascript
submit("contract_usage", "batch_record", {
    "legal_entity_id": 13,
    "source_system": "metrics_api",        // Identifies the source
    "batch_description": "January API usage import",
    "fail_on_error": false,                // Continue on individual failures
    "usage_records": [
        {
            "contract_line_id": 456,
            "usage_date": "2025-01-15",
            "quantity": 1250,
            "unit_of_measure": "api_calls"
        },
        {
            "contract_line_id": 456,
            "usage_date": "2025-01-16",
            "quantity": 980,
            "unit_of_measure": "api_calls"
        }
    ]
})

// Response:
{
    "success": true,
    "batch_id": 123,
    "records_submitted": 2,
    "records_inserted": 2,
    "records_updated": 0,
    "records_failed": 0
}
```

**Batch Features:**
- **Tracking:** Creates `recurring_usage_batches` record for audit trail
- **Deduplication:** If `external_reference_id` matches existing record, updates instead of duplicating
- **Partial Success:** With `fail_on_error: false`, continues processing even if some records fail
- **Error Reporting:** Returns list of failed records with error details

**Note:** Only unbilled usage (`status = 'recorded'`) can be updated/deleted.

**Update field mapping:** there is no `usage_date` column — the table stores `usage_period_start`/`usage_period_end`. Passing `usage_date` to `contract_usage.update` sets both period columns (single-day period, same as record); explicit period fields win. There is no `description` column — use `metadata` for notes. `billing_period_date` is system-managed (stamped at billing, cleared on reversal) and cannot be set via the workflow.

### Usage in Billing Runs

For lines with `line_type = 'usage'`:
1. Queries `recurring_contract_usage` for unbilled records (`status = 'recorded'`) whose `usage_period_start` falls inside the billing period (the window starts at the contract's `next_billing_date`). Matching is NOT by `billing_period_date` — that column is system-stamped only when the record gets billed, and is always NULL on unbilled records.
2. Calculates: `SUM(quantity) * unit_price`
3. Marks usage records as `status = 'billed'` after invoice creation
4. Preview shows amounts separately; execute marks as billed

**No usage recorded → contract SKIPPED, period stays open.** If a usage-only contract has no unbilled usage in the period, the run creates NO invoice (never a €0 one), records the contract as `skipped`, and does NOT advance `next_billing_date` — the period stays open and is billed automatically by a later run once usage is recorded. Skipped contracts are listed in the result's `contracts_skipped_no_usage`, and the scheduled billing agent creates ONE **"provide usage data" verification task in My Tasks** (assigned to the org owner/admin, with a notification email; dedup-checked so daily re-runs don't stack tasks) listing each contract and its open period — completing it means recording the usage and re-running billing. If a preview shows €0 for a usage contract, check the per-contract `warning` — it names the period window that was checked; record usage for that window first, then run billing.

### Pricing Models

**1. Per-Unit Pricing:**
```
Rate: $0.10 per API call
Usage: 10,000 calls
Charge: $1,000
```

**2. Tiered Pricing:**
```
Tiers:
- 0-5,000: $0.10 each
- 5,001-10,000: $0.08 each
- 10,001+: $0.06 each

Usage: 12,000 calls
Charge: $500 + $400 + $120 = $1,020
```

**3. Block Pricing:**
```
Blocks:
- 0-10,000: $500 flat
- 10,001-25,000: $1,000 flat

Usage: 22,000 calls
Charge: $1,000 (block rate)
```

**4. Volume Pricing:**
```
Volume discounts (all units):
- 0-10,000: $0.10 each
- 10,001+: $0.08 each (all units)

Usage: 15,000 calls
Charge: 15,000 x $0.08 = $1,200
```

### Tiered Pricing Configuration

```javascript
"pricing_tiers": [
    {"min_quantity": 0, "max_quantity": 5000, "price": 0.10},
    {"min_quantity": 5001, "max_quantity": 10000, "price": 0.08},
    {"min_quantity": 10001, "max_quantity": null, "price": 0.06}
]
```

### Multi-Dimensional Tier Pricing

For complex SaaS products, tiers can be triggered by multiple metrics using the `item_pricing_tiers` table with `tier_conditions` JSONB.

**Use Case:** A SaaS product where pricing depends on:
- Number of entities (1-2, 3-5, 6-10, 11+)
- Storage used (0-1GB, 1-5GB, 5-10GB, 10GB+)
- API calls per month

**tier_conditions Structure:**
```json
{
    "match_mode": "any",
    "charging_method": "flat",
    "conditions": [
        {"metric": "entities", "min": 1, "max": 2},
        {"metric": "storage_gb", "min": 0, "max": 1}
    ]
}
```

**Boundary Convention (EXCLUSIVE UPPER BOUNDS):**

Tier ranges use **inclusive min, EXCLUSIVE max**: `[min, max)`

| Condition | Range Notation | Matches |
|-----------|----------------|---------|
| `{"min": 0, "max": 1}` | [0, 1) | 0, 0.5, 0.99 |
| `{"min": 1, "max": 5}` | [1, 5) | 1.0, 2.0, 4.99 |
| `{"min": 5, "max": null}` | [5, ∞) | 5.0, 10.0, 100.0 |

**Why Exclusive Upper Bounds?**
- Industry standard for pricing tiers
- No ambiguity at boundaries: 1.0 GB → Growth tier, not Starter
- Each value maps to exactly one tier

**Example with Storage Tiers:**
```
Starter: min=0, max=1  → matches 0.00 to 0.99 GB
Growth:  min=1, max=5  → matches 1.00 to 4.99 GB
Scale:   min=5, max=25 → matches 5.00 to 24.99 GB
Enterprise: min=25, max=null → matches 25.00+ GB
```

**Match Modes:**
| Mode | Behavior |
|------|----------|
| `any` | Tier applies if customer matches ANY condition (OR logic) |
| `all` | Tier applies if customer matches ALL conditions (AND logic) |

**Charging Methods:**
| Method | Behavior | Example |
|--------|----------|---------|
| `flat` (default) | Tier price IS the total amount | $99/mo for 1-2 entities |
| `per_unit` | Tier price × quantity | $0.10 × 10,000 API calls = $1,000 |

**Note:** When `charging_method` is not specified:
- JSONB tiers (with `tier_conditions`): Default to `"flat"`
- Legacy tiers (only `min_quantity`/`max_quantity`): Default to `"per_unit"`

**Example: SaaS Pricing Tiers (Flat Pricing)**
```
Tier: Starter ($99/month flat)
- tier_conditions: {"match_mode": "any", "charging_method": "flat", "conditions": [
    {"metric": "entities", "min": 1, "max": 2}
  ]}

Tier: Growth ($499/month flat)
- tier_conditions: {"match_mode": "any", "charging_method": "flat", "conditions": [
    {"metric": "entities", "min": 3, "max": 5}
  ]}

Tier: Enterprise ($999/month flat)
- tier_conditions: {"match_mode": "any", "charging_method": "flat", "conditions": [
    {"metric": "entities", "min": 6, "max": null}
  ]}
```

**Example: API Usage Pricing (Per-Unit)**
```
Tier: Standard ($0.10 per API call)
- tier_conditions: {"match_mode": "any", "charging_method": "per_unit", "conditions": [
    {"metric": "api_calls", "min": 0, "max": null}
  ]}
```

**Tier Selection Logic:**
1. Get all active tiers for the item ordered by price (highest first)
2. For each tier, evaluate `tier_conditions` against customer's usage metrics
3. First tier that matches is selected (highest-price tier wins when multiple match)

**Recording Usage for Tier Matching:**
```javascript
// Record entity count
submit("contract_usage", "record", {
        "contract_line_id": 456,
        "usage_date": "2025-01-15",
        "quantity": 4,                          // Customer has 4 entities
        "unit_of_measure": "entities"           // Metric name matches tier condition
    })
)

// Record storage usage
submit("contract_usage", "record", {
        "contract_line_id": 456,
        "usage_date": "2025-01-15",
        "quantity": 2.5,
        "unit_of_measure": "storage_gb"
    })
)
```

**Billing Run Behavior:**
- For usage-based lines, the billing run:
  1. Aggregates usage by `unit_of_measure` for the billing period
  2. Calls `TierMatchingService.find_matching_tier()` with usage metrics
  3. Applies pricing based on `charging_method`:
     - `"flat"`: Uses tier price as total (e.g., $99 regardless of quantity)
     - `"per_unit"`: Multiplies tier price by quantity (e.g., $0.10 × 10,000)
  4. Falls back to contract line's `unit_price × quantity` if no tier matches
  5. Updates contract's `current_tier_id`, `current_tier_name`, `current_tier_price` after billing
  6. Records tier changes in `recurring_contract_tier_history` for audit trail

**Contract Tier Tracking:**
After each billing run, the contract stores the current tier information:
- `current_tier_id` - ID of the matched pricing tier
- `current_tier_name` - Display name (e.g., "Growth - Scaling Companies")
- `current_tier_price` - The tier price applied (e.g., $499)
- `tier_updated_at` - When the tier was last updated

This enables accurate MRR/ARR reporting based on actual billed amounts rather than base contract values.

**Flat Tier Deduplication:**
For contracts with multiple usage lines (e.g., `storage_gb` + `entities`), flat tier pricing is applied only ONCE per contract. The billing run tracks whether a flat tier has already been billed and skips subsequent usage lines for the same tier, while still marking their usage as billed.

---

## Prepaid Wallets

### What are Prepaid Wallets?

Customer credit balances that auto-deduct from invoices.

### Wallet Fields

**Required:**
- `customer_id` (integer) - Customer
- `legal_entity_id` (integer) - Entity
- `currency_code` (string) - Currency

**Optional:**
- `contract_id` (integer) - Link to specific contract
- `initial_balance` (decimal) - Starting balance
- `auto_reload` (boolean) - Auto-reload when low
- `reload_threshold` (decimal) - Balance to trigger reload
- `reload_amount` (decimal) - Amount to reload

### Wallet Deduction Flow

```
Invoice: $1,000 monthly subscription
Wallet Balance: $5,000

1. System deducts $1,000 from wallet
2. New wallet balance: $4,000
3. Invoice shows:
   - Amount: $1,000
   - Wallet Applied: -$1,000
   - Balance Due: $0
```

---

## Contract Amendments

### Amendment Types

**What `recurring_contract.amend` does today.** An amendment takes effect on the
day it is approved. A past `effective_date` is refused, and a future one with line
changes is refused, because no schedule defers them. The changed lines apply to the
next billed period. No proration or upgrade charge is calculated, and nothing is
refunded or credited for the current period.

A price or quantity change never reprices days already in force at the old price
(AR-1015): it takes effect from today, or from the next unbilled period if that is
later, and the line in force is versioned (see "Dated price changes" below).

Planned for platform plan changes (AR-1012, not built): an upgrade or downgrade
takes effect immediately and is prorated, with the unused part of the old plan
credited and the rest of the period charged at the new plan on one AR invoice.

### Dated price changes (AR-1015)

`contract_line.update` with a new `quantity`, `unit_price` or `fixed_amount` on an active
contract versions the line instead of overwriting it:

- `price_effective_from` (YYYY-MM-DD) says when the new price starts. Omitted, it is
  today, or the contract's next unbilled period if that is later.
- The line in force is ended the day before; a new line (next line number, metadata
  `replaces_line_id`) carries the new price from that date. Non-price fields given in the
  same request apply to both.
- Billing charges each version for its days of the period only. A period the change falls
  inside is split by days on one invoice (Andrew, 31 Oct 2026): €100 → €120 from 15 Sep
  bills "1–14 Sep" at 100 × 14/30 = 46.67 and "15–30 Sep" at 120 × 16/30 = 64.00. Preview
  shows the same amounts.
- A date before the next unbilled period is refused: those days were billed or are due at
  the price in force then. Correct a billed period with a credit memo or an additional
  invoice. (A correction path with its own approval is not built yet.)
- On a draft contract, and for a change dated on or before the line's first day, the edit
  applies in place: nothing was billed at the old price.
- A dated change on a usage line is refused; end the line and add a new one.
- Derived contract totals and renewals count only the version in force.

### Amendment Workflow

```javascript
submit("recurring_contract", "amend", {
    "contract_id": 789,
    "amendment_type": "upgrade",
    "effective_date": "2025-01-15",
    "updated_lines": [
        {"line_id": 457, "unit_price": 1500.00}
    ],
    "prorate": true,
    "amendment_reason": "Customer upgraded to Premium"
})
```

---

## Common Use Cases

### Use Case 1: Customer Discount (Special Pricing)

```javascript
// Give ACME Corp 20% off Widget Pro
submit("customer_item_pricing", "create", {
    "legal_entity_id": 13,
    "customer_id": 456,
    "item_id": 101,
    "discount_percent": 20.00,
    "effective_from": "2025-01-01",
    "notes": "Key account discount"
})
```

### Use Case 2: Monthly SaaS Subscription

```javascript
// 1. Create contract
submit("recurring_contract", "create", {
    "legal_entity_id": 13,
    "customer_id": 456,
    "contract_name": "Standard SaaS Plan",
    "start_date": "2025-01-01",
    "billing_frequency": "monthly",
    "currency_code": "USD",
    "auto_renew": true
})

// 2. Add subscription line
submit("contract_line", "create", {
    "contract_id": 789,
    "master_item_id": 101,
    "line_type": "fixed",
    "item_description": "Standard Plan",
    "unit_price": 100.00,
    "gl_account_number": "4000"
})

// 3. Activate contract
submit("recurring_contract", "activate", {
    "contract_id": 789
})
```

### Use Case 3: API Platform with Usage

```javascript
// Add usage-based line with overage pricing
submit("contract_line", "create", {
    "contract_id": 789,
    "master_item_id": 102,
    "line_type": "tiered",
    "item_description": "API Calls",
    "usage_metric": "api_calls",
    "pricing_tiers": [
        {"min_quantity": 0, "max_quantity": 10000, "price": 0.00},
        {"min_quantity": 10001, "max_quantity": null, "price": 0.10}
    ]
})

// Result:
// - 8,000 calls = $0 (included)
// - 15,000 calls = 5,000 overage x $0.10 = $500

// Record usage data daily
submit("contract_usage", "record", {
    "contract_line_id": line_id,
    "usage_date": "2025-01-15",
    "quantity": 1250,
    "external_reference_id": "api-2025-01-15"
})
```

### Use Case 4: Prepaid Wallet

```javascript
// Create wallet with $5,000 and auto-reload
submit("prepaid_wallet", "create", {
    "customer_id": 456,
    "legal_entity_id": 13,
    "currency_code": "USD",
    "initial_balance": 5000.00,
    "auto_reload": true,
    "reload_threshold": 1000.00,
    "reload_amount": 5000.00
})
```

### Use Case 5: Run Monthly Billing

```javascript
// Generate all monthly invoices for a legal entity
submit("billing_run", "execute", {
    "legal_entity_id": 1,
    "billing_date": "2025-01-01",
    "auto_post_invoices": true,
    "notes": "January monthly billing run"
})
```

---

## Quick Reference - Required Fields

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

### Customer Item Pricing

| Workflow | Required Fields |
|----------|-----------------|
| `customer_item_pricing.create` | `item_id`, `customer_id`, `legal_entity_id`, `price` |
| `customer_item_pricing.update` | `id` |
| `customer_item_pricing.delete` | `id` |

### Recurring Contracts

| Workflow | Required Fields |
|----------|-----------------|
| `recurring_contract.create` | `legal_entity_id`, `customer_id`, `contract_name`, `start_date`, `billing_frequency`, `currency_code` |
| `recurring_contract.update` | `contract_id` |
| `recurring_contract.activate` | `contract_id` |
| `recurring_contract.suspend` | `contract_id`, `suspension_reason` |
| `recurring_contract.terminate` | `contract_id`, `termination_date` |
| `recurring_contract.amend` | `contract_id`, `amendment_type`, `effective_date` |
| `recurring_contract.renew` | `contract_id` |

### Contract Lines

| Workflow | Required Fields |
|----------|-----------------|
| `contract_line.create` | `contract_id`, `master_item_id`, `line_type` |
| `contract_line.update` | `line_id` |
| `contract_line.delete` | `line_id` |

### Contract Usage

| Workflow | Required Fields |
|----------|-----------------|
| `contract_usage.record` | `contract_line_id`, `usage_date`, `quantity` |
| `contract_usage.batch_record` | `legal_entity_id`, `usage_records` |
| `contract_usage.update` | `usage_id` |
| `contract_usage.delete` | `usage_id` |

### Billing Runs

| Workflow | Required Fields |
|----------|-----------------|
| `billing_run.execute` | `legal_entity_id`, `billing_date` |
| `billing_run.preview` | `legal_entity_id`, `billing_date` |
| `billing_run.retry` | `billing_run_id` |
| `billing_run.cancel` | `billing_run_id` (optional `cancel_reason`) |
| `billing_run.delete` | `billing_run_id` (optional `delete_reason`) |

### Prepaid Wallets

| Workflow | Required Fields |
|----------|-----------------|
| `prepaid_wallet.create` | `customer_id`, `legal_entity_id`, `currency_code` |
| `prepaid_wallet.credit` | `wallet_id`, `amount` |
| `prepaid_wallet.debit` | `wallet_id`, `amount` |
| `prepaid_wallet.close` | `wallet_id` |

---

## Summary: When to Use What

| I want to... | Use |
|--------------|-----|
| Give a customer a discount | `customer_item_pricing` |
| Set up a monthly subscription | `recurring_contracts` |
| Track monthly seat usage | `recurring_contracts` + `contract_usage` workflows |
| Bill for API calls | `recurring_contracts` + `contract_usage` workflows |
| Record usage data | `contract_usage.record` or `contract_usage.batch_record` |
| Give a key account better rates | `customer_item_pricing` |
| Auto-generate invoices | `recurring_contracts` + billing runs |
| Handle prepaid credits | `recurring_contracts` + prepaid wallets |
| Prorate mid-month upgrades | `recurring_contracts` + amendments |

**Remember:**
- `customer_item_pricing` = "what price does this customer pay?" (simple lookup)
- `recurring_contracts` = "how do we bill this customer automatically?" (full automation)

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `customer_item_pricing` | Customer-specific prices/discounts |
| `recurring_contracts` | Contract headers |
| `recurring_contract_lines` | Line items (fixed, usage) |
| `recurring_contract_line_tiers` | Pricing tiers for usage |
| `recurring_contract_usage` | Usage tracking data |
| `recurring_usage_batches` | Batch import tracking for usage data |
| `recurring_contract_invoices` | Generated invoices |
| `recurring_contract_amendments` | Contract change history |
| `recurring_billing_runs` | Billing run headers |
| `recurring_prepaid_wallets` | Customer credit balances |
| `recurring_prepaid_wallet_entries` | Wallet transactions |
| `recurring_contract_tier_history` | Tier change history for contracts |
| `customer_tax_profiles` | Customer tax exemptions and default tax codes |
| `customer_dimensions` | Customer dimension assignments |
| `item_pricing_tiers` | Multi-dimensional tier pricing for items |

---

## Multi-Dimensional Tier Pricing

For SaaS products where pricing tiers depend on **multiple independent metrics** (e.g., entities, storage, API calls), use `tier_conditions` JSONB on `item_pricing_tiers`.

### tier_conditions Structure

```json
{
    "match_mode": "any",
    "charging_method": "flat",
    "conditions": [
        {"metric": "entities", "min": 1, "max": 2},
        {"metric": "storage_gb", "min": 0, "max": 1}
    ]
}
```

### Match Modes

| Mode | Logic | Use Case |
|------|-------|----------|
| `any` | OR -- tier applies if ANY condition matches | "Upgrade when you hit 3 entities OR 5GB storage" |
| `all` | AND -- tier applies if ALL conditions match | "Enterprise requires 10+ entities AND 50+ GB" |

### Boundary Convention

Tier ranges use **inclusive min, EXCLUSIVE max**: `[min, max)`

| Condition | Matches |
|-----------|---------|
| `{"min": 0, "max": 1}` | 0, 0.5, 0.99 |
| `{"min": 1, "max": 5}` | 1.0, 2.0, 4.99 |
| `{"min": 5, "max": null}` | 5.0, 10.0, 100.0+ |

### Charging Methods

| Method | Behavior | Example |
|--------|----------|---------|
| `flat` (default for JSONB tiers) | Tier price IS the total amount | $99/mo for 1-2 entities |
| `per_unit` (default for legacy tiers) | Tier price x quantity | $0.10 x 10,000 API calls = $1,000 |

### Example: SaaS Subscription Tiers

```
Starter ($99/mo flat): 1-2 entities OR 0-1GB storage
Growth ($499/mo flat): 3-5 entities OR 1-5GB storage
Scale ($999/mo flat): 6-15 entities OR 5-25GB storage
Enterprise ($2,499/mo flat): 16+ entities OR 25+GB storage
```

### Tier Selection During Billing

1. Aggregates usage by `unit_of_measure` for the billing period
2. Evaluates each tier's `tier_conditions` (highest price first)
3. First matching tier is selected
4. Applies pricing based on `charging_method` (`flat` or `per_unit`)
5. Updates contract's `current_tier_id`, `current_tier_name`, `current_tier_price`
6. Records tier changes in `recurring_contract_tier_history`

For full details including volume vs graduated tier modes, see GUIDE_BILLING_MANAGEMENT.md.

---

## Viewing in Admin Dashboard

**Customer Special Pricing:**
1. Go to **Customers** → Select customer
2. Click **Special Pricing** tab
3. View items with negotiated prices

**Recurring Contracts:**
1. Go to **Contracts** or **Recurring Contracts**
2. View contract list with MRR/ARR metrics
3. Click contract to see lines and details

**Billing Runs:**
- Executed via workflow system
- Results show contracts billed, amounts, failures


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


### Invoice Delivery pipeline and uncertain sends (2026-09-23)

Invoice Delivery has one mandatory prepare/deliver/finalize pipeline, including
stored code definitions. Automatic delivery remains opt-in; a manual resend is
a new persisted event, while replaying that event does not send again. Invoice
claims and durable provider receipts prevent concurrent or uncertain sends from
being repeated. A provider message ID is required for completion; delivery log,
sent event and receipt completion commit together. Unknown dispatches await
operator provider verification using `scripts/invoice_delivery_recovery.py`;
never clear a claim to force a retry. Preview performs no rendering or writes.
The agent sends invoices and does not collect payment.


### Collection outcome and recovery

Invoice creation delivers an invoice; it does not automatically charge a card.
Payment Collection runs on explicit manual/dunning events and persisted receipt
continuations. `waiting_provider` and `waiting_workflow` are not payment completion.
`waiting_recovery` means an uncertain charge or settlement requires investigation;
do not rerun a fresh charge or clear invoice `collection_pending` metadata.
Only `collected` confirms committed AR payment/application. Confirmed declines
may schedule dunning; unknown provider outcomes stay reserved. Recovery belongs
to the operator receipt procedure, never a generic task response or model decision.


### Recurring contract field semantics

- `total_contract_value`, when supplied at creation (including zero), is the explicit
  contract-term value. It is independent of a line's per-billing-period charge. A
  two-month contract with a $300 monthly line can carry an explicit $600 total.
  The header records `metadata.contract_value_source="explicit"`; subsequent
  contract-line create/update/delete operations preserve that value. Without an
  explicit total, the legacy sum-of-line-charges calculation remains; it does not
  infer a full-term value from dates or usage forecasts.
- Inline create lines accept `account_id` as a **master account ID**, or
  `gl_account_number`. An explicitly supplied account must be active, non-header,
  and available in the contract's legal entity. If both references are supplied,
  they must agree. The resolved number is persisted in `gl_account_number`;
  invalid references abort the entire create. Omitting both retains existing
  item/default-account resolution behavior; activation/preview alone does not
  prove invoice posting is ready.
- `recurring_contract.suspend` uses `suspension_reason`; legacy `suspend_reason`
  and `reason` aliases normalize to it. Conflicting non-empty values are rejected.
  The saved metadata and response retain the existing `suspend_reason` key.
  Organization-required-field policy still applies.

These fixes do not retroactively infer discarded values for existing contracts.
Review the original workflow payload before repairing a historical record; do not
resume a test contract merely to overwrite its audit reason. No database migration
is required. End-date/evergreen behavior and invoice-delivery dispatch are unchanged.


### Contract end dates and final billing periods

Billing preview and execution select only active customer contracts whose next
service-period start is on or before the inclusive `end_date` (or whose end date
is unset). Execution rechecks current status, entity, cursor and end date while
holding the contract row lock. Explicit contract IDs and retries do not bypass
these checks. Suspended/draft contracts cannot post.

The final service period is capped at `end_date`; usage lookup and invoice period
labels use that capped window. For fixed charges, `daily_prorata` uses active days
within the original full billing period. `full_period` and `none` retain the full
period charge. The cursor advances from the original period boundary, preventing
a partial final month from looping back to its beginning. A later run may still
bill an earlier unbilled period that falls within the term; the run date alone does
not make that period invalid.

Setting auto-renew/evergreen does not implicitly extend an explicit end date;
renewal must update the stored term through the existing renewal workflow. Billing
does not automatically change contract status to completed. No data migration is
required. Existing erroneous invoices require audited reversal, not deletion.

### Cancellation posting date

Billing-run cancellation reverses each invoice on the later of the cancellation date and that invoice's transaction date. Cancelling a future-dated invoice therefore does not introduce a reversal into an earlier accounting period. Normal period validation still applies; a blocked reversal rolls back the cancellation.


### Bill and billing-usage request reads (QA branch, not deployed)

Admin and MCP request readers require `ap:read` for the installed `review_bill`
action and `ar:read` for `provide_usage_data`. These requirements apply even to
legacy rows without owner, object-type or source-table hints, and also to known
actions in response metadata. They add to existing domain/entity checks. Every
member of a thread must be readable before rows, counts and pages are returned;
a thread containing both actions requires both domains. Wildcard grants retain
both domains. Other actions are not classified by this change. Read access does
not authorize approval, posting, changing a draft or supplying usage. Broader
structured-reference and hosted-role acceptance remains open.


### Stored review and usage references (QA branch, not deployed)

For `review_bill`, a supplied draft ID and revision must resolve together to a
stored revision of a draft in the request entity. A linked transaction must be
a same-entity AP invoice. Missing/foreign drafts, absent revisions, malformed
IDs and wrong bill bindings hide the request and its thread. Legacy reviews
without either draft field remain readable under the existing AP/entity policy.
Historical revisions may remain readable; this does not approve a stale draft.

For `provide_usage_data`, a supplied billing run must match the organization and
entity, and each supplied `contracts[].contract_id` must resolve in that entity.
Malformed contract collections and missing/foreign contract IDs deny the thread.
The producer allows an absent billing-run ID; it remains supported. Checks apply
to request and response metadata before rows, counts and pagination. Responses
inherit the originating request action even when they omit their own action. Approval,
posting and usage submission still perform their existing live validations.
Bill-review draft active requests now use the same cycle-safe request/thread
authority, including response metadata. Missing, foreign or forbidden links deny
the review; absent optional links and readable cycles remain supported. The bounded draft workflow graph is described below. Source attachments and
arbitrary embedded metadata remain outstanding read-authority coverage.


### Bill draft workflow authority (QA branch, not deployed)

Bill-review request reads follow a stored draft's optional `workflow_id`. The
workflow and its definition must belong to the request organization, and its
resolved entity must match the request. Existing workflow domain, payroll and
stored-transaction checks apply; a payload hint cannot replace the stored
transaction's authority. Missing, foreign, malformed or forbidden workflows
withhold the review and its reachable thread before totals or pagination.

The shared graph also checks workflow payload request references and stored
object-link metadata. Transaction links must resolve in the same entity under
the reader's existing transaction permissions; payment-batch links retain the
existing batch policy. A producer `metadata.bill_candidate` stamp follows its
`draft_id` and `revision` through the same draft checks. Readable self/mutual
request/draft/workflow cycles terminate without being denied merely for cycling.
Response review metadata and virtual execution metadata use the same rules.

These are historical read-authority checks, not approval, current-revision or
posting authorization. They neither change stored pointers nor repair workflows.
Other object-link families retain their existing domain checks; this does not
certify every nested reference, source attachment or free-text narrative. Hosted
identity and representative performance acceptance remain open.


### Customer tax-profile task reads (QA branch, not deployed)

Tasks with `set_customer_tax_profile` require `ar:read` or `master_data:read`,
matching customer read permissions, even when owner/source hints are absent.
The same rule applies to response metadata. In this producer contract, both
`customer_id` and `master_customer_id` name **master_customers.id**, not the
entity-link row `customers.id`. At least one ID must be present on an action
payload; supplied IDs must resolve to the same customer linked to the request
entity. A supplied `legal_entity_id` must also match that entity. Missing,
malformed, conflicting or foreign references withhold the task and its thread,
including from wildcard readers. Empty responses remain valid; supplied response
IDs/entity inherit the originating action's checks. Valid single-ID legacy
payloads remain supported.

These checks apply before list counts/pages and to virtual execution metadata.
They do not grant tax-profile editing or change the delegation/retry workflow.
Do not substitute entity-link IDs or alter stored tasks to bypass a refusal.
Arbitrary context text, other master-data actions and hosted identity acceptance
remain outside this bounded verification.


## Close evidence update (b1, awaiting deployment)

The close check reports each contract’s recorded attempts separately from service-period coverage. A completed run header alone no longer proves coverage. Recorded billed intervals and eligible same-entity invoices dated by period end establish coverage; the current engine schedule classifies gaps. A future billing pointer, no-usage skip, or manual invoice description never proves coverage. A convention invoice date falling after period end is labelled “accrual not tested”. No new billing policy block is introduced: incomplete coverage retains the old no-completed-run failure or reports a warning when that old check passed.

### Complete billing failure evidence (local implementation)

Billing execution retains every collected per-contract error in the returned
`errors` list and saved run summary. The built-in failure email and textual run
summary also list every available error. Legacy workers that supply fewer errors
than their failure count still disclose the missing count; missing details are
not invented. Usage-request email display limits are unchanged.

This does not add period containment, guarantee email delivery/retry, or repair
historical truncated summaries. Existing failure classifications and per-contract
transaction behavior are unchanged.

### Payment racing billing cancellation (AR-350, local implementation)

Cancellation now acquires the existing shared revaluation boundary before locking
its billed invoices in ID order. The paid/partially-paid check reads those locked
rows, so a payment committed while cancellation waits prevents reversal. The
operator must unwind the payment through its supported flow before cancelling.
No accounting date policy or payment reversal is performed automatically.

This fixes the payment-before-invoice-lock race only. It does not freeze a run's
receipt set against concurrent billing, or certify every cancellation/contract
writer lock ordering. Historical records are not repaired.

Cancellation rechecks run status after waiting for invoice locks. A request
that loses to another completed cancellation returns an already-cancelled
refusal. This does not change legacy recovery for billed receipts without an
invoice, and does not establish complete concurrent run/receipt-set protection.

## Scoped billing hold decisions and evidence report (on by default)

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


### Opt-in billing pipeline 1.0.3: durable waiting outcomes

Pipeline block version 1.0.3 is available as an explicit opt-in candidate; it is
not the default and does not upgrade saved organization definitions. Retained
1.0.0, 1.0.1 and 1.0.2 implementations are unchanged.

A saved pending workflow produces a `waiting_workflow` outcome while allowing
the orchestration host to finish its current step. This is a durable wait, not
confirmation that usage or invoicing completed. The existing configured approval
and current authority checks still apply when that workflow executes. Unknown
posting state and failures take precedence over a pending workflow. Missing
workflow identity cannot be reported as a recoverable approval wait; it is
reported for attention/recovery instead. Receipt-backed resumption still decides
whether the original task completed.

Before rollout, inventory customized definitions, explicitly select the reviewed
block version and drain older workers. Merely registering this code activates no
policy, sends no notification and changes no production definition.

Billing execute/retry identity comes from the authenticated agent runtime.
Conflicting supplied identity fields are rejected; they are not accepted as
business inputs. Generated invoices retain their recurring-billing system source,
while activity records retain the initiating agent and workflow for audit.


### Billing Run once scope and transaction

The dashboard's billing Run once action reloads and locks the saved job and
current enabled billing definition, then checks the user's current membership
and entity access against the entire requested scope. Invalid or inaccessible
scope refuses before any event is written. A deliberately disabled schedule can
still be run manually; a disabled agent definition cannot.

Each selected entity gets one singleton-scoped event, compatible with retained
1.0.0 and opt-in 1.0.3 consumers. All events and job tracking commit together; a
failure writing any event rolls back the whole dispatch. This action queues
billing work; it does not report that invoices were created. Reconciliation-only
period overrides are refused on billing jobs. No saved definition is upgraded.

### Hold evidence in close checks

The close check and hold report use the same entity-scoped counts of recorded
hold decisions overlapping the requested period, with a separate exact-period
count. Close details identify current capability-held contracts with no recorded
decision. This is current evidence, not a historical policy verdict: recording a
decision does not change the check status, clear a hold or authorize closure.
Missing decision storage is reported explicitly.

New decision evidence also records the authenticated execution mechanism (auth
type and whether a key, agent instance or workflow is present). It exposes no
credential identifier and does not identify a particular client or prove a human
approved the decision. Existing immutable records are unchanged.

### Audit of next billing date changes

A supported `recurring_contract.update` change to `next_billing_date` records the
old/new date and authenticated actor in the same transaction as the contract
update. Workflow/agent attribution comes from explicit server activity context.
`metadata.last_billing_cursor_change` exposes the latest audit ID and timestamp;
prior changes remain in separate audit rows. Existing notes and other metadata
are preserved, and generated audit metadata is not counted as a caller-updated
field. Replaying the same request does not add another audit entry.

If audit storage fails, the tested update path rolls back the contract, notes and
audit together. The public response still reports `posting_unknown`: reconcile
the same request/workflow identity instead of automatically retrying with a new
key. This audit changes no billing-date eligibility or accounting policy.
### Contract-line account validation — AR123 current integration

Standalone contract-line create/update validates an explicitly supplied
`gl_account_number` against active, non-header accounts in the stored contract's
entity. Invalid, inactive, header and other-entity numbers refuse without changing
the line or contract total. Current stored-target authorization and contract-first
locking remain in force. Omitted/null numbers retain existing default behavior;
this is not proof of posting readiness or a new account-ID alias.
The account fix is published for review in PR430 and integrated with PR425.
It has not yet been merged or deployed.


### Invoice-delivery event SQL failure and billing recovery

In the current atomic billing implementation, a database error inserting
`ar_invoice.created` rolls back that subject's invoice, billed receipt, usage
changes and billing cursor. The run records a failed attempt; it must not report
a rolled-back invoice as billed. Already committed subjects remain discoverable.
After correcting the fault, retry the failed billing run. A successful retry
records its own receipt and delivery event; the original failed receipt is kept.
A repeated execution observes the committed period rather than billing it twice.
This differs from the older, unmerged PR410 proposal to preserve invoices with a
best-effort event savepoint. It does not prove actual email delivery or authorize
a historical data repair. Runtime is merged; this verification did not deploy it.


### Subscription contract transaction (AR-474)

The Stripe checkout contract stage now uses one database transaction for its
existing-contract read, new header and all selected item lines. Deliveries for the
same subscribing organization serialize on that organization row. A failure in this
stage rolls back new contract writes and returns HTTP 503 so delivery can retry.
This transaction does not include earlier customer, subscription-payment or credit
grant stages, or subsequent ledger posting. Existing partial contracts are not
reconstructed by this change; their recovery remains open (checkout-to-contract
binding for new contracts is described below). Do not treat a pre-existing header or a successful webhook response as proof
that historical contract lines are complete. No production repair is included.


### Checkout-bound subscription contract reuse (AR-474)

New checkout-created contracts retain the checkout/session reference, payment
reference, subscribing organization, billed customer/entity, plan, interval and
amount as creation evidence. Redelivery reuses exactly one active contract only
when that evidence and its stored customer/entity agree. Invoice posting receives
the exact contract ID returned by that transaction, not a later unscoped first match.
A legacy unbound/partial contract, ambiguous active matches, changed checkout terms
or a terminated matching contract returns HTTP503 with
`stripe_contract_review_required` before first-invoice submission. The handler does
not invent missing lines or change those existing contracts. This is an explicit
hold, not a completed legacy recovery workflow; operator repair/binding requires a
separate reviewed procedure. Credit/activation and payment-method setup are separate from the contract transaction. No production repair is authorized by this guide.

### One subscription checkout per organisation (AR-474)

A subscription checkout starts a new subscription; it is not a plan change.
`billing.createSubscribeSession` refuses with `CONFLICT`, before any payment
provider is called, when the organisation's billing status is `active` or
`past_due`, or the billing books already hold an active subscription contract
for it. Before opening a new session it also expires the organisation's other
open subscription checkout sessions, so two open sessions (another tab, an
abandoned one) cannot both be paid. Either path would otherwise collect a second
payment, hold the contract stage for review and never post its first invoice.
A payment completing at the same instant a new session is opened can still reach
that hold; it stays a visible 503, not a silent success.

Cancelling a subscription sets the organisation to `cancelled` but leaves its
contract active, so a cancelled organisation can subscribe again only after that
contract is terminated. The rule lives in
`admin-dashboard/server/lib/subscription-checkout.ts` so any checkout provider
(Stripe today, Revolut or Adyen later) applies the same check and closes its own
earlier open sessions. Plan changes need a contract amendment flow with its own
charge or credit policy; none exists yet.


### Subscription credit receipt transaction (AR-474)

For new subscription deliveries, the payment receipt, monthly credit balance update
and credit-ledger entry now commit together. Missing plan/balance or a transaction
failure returns HTTP503 and rolls this stage back. Contract creation and invoice
posting remain separate stages. Existing payment receipts created before this change
cannot prove historical credit completion; do not regrant credits solely because a
contract is incomplete. For new grants, credit-exhaustion alert clearing and resumption of the agents
recorded as paused now use the same transaction. A failure rolls the grant and
recovery back together. Standalone alert-helper callers retain their own transaction. This change does not repair historical records.


### Subscription credit replay evidence (AR-474)

New receipts record the checkout and a versioned completion reference to the exact
credit-ledger entry, its granted amount, plan and billing interval. This evidence
commits with the grant and alert recovery. A repeated payment reference must match
the stored organization, checkout, amount, currency, payment status/type and linked
ledger entry. Missing or conflicting evidence returns HTTP503 with
`stripe_credit_review_required` before contract/invoice processing; it never
automatically grants credits again. Historical receipts without this completion
evidence require a separately reviewed resolution. Current balance and current plan
allowance are not replay evidence: credits may have been spent and plans edited.
Organization activation now commits with the first grant only. Failed grants leave
the earlier subscription state unchanged, and receipt replays do not reactivate a
cancelled subscription or reset its start date. Payment-method setup runs after
receipt validation; a failure returns HTTP503 `stripe_subscription_setup_failed`
so redelivery can retry without a second grant. This external step is not part of
the SQL transaction. Ordering against a later payment-method change, historical
repair and the complete checkout remain separate unfinished recovery work.


Renewal also preserves each copied line's stored `unit_of_measure`, including an
unspecified value, without changing the original line. This is retention of existing
terms, not support for new unit edits or automatic unit conversion. Renewal remains
a draft; other stored pricing/cadence fields require their own capability review.
