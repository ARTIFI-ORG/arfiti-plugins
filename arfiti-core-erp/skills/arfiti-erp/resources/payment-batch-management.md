# Payment Batch Management

This resource covers AP payment batch management: creating payment batches, adding payment lines, approval workflows, bank transmission, and payment confirmation from bank statements.

---

## Overview

Payment batches organize multiple vendor payments into a single transmission to the bank. The system supports ACH, wire, SEPA, and check payments with full approval controls and audit trails.

**What you can do:**
- Create payment batches for vendor payments
- Add and remove payment lines
- Submit batches for approval
- Approve or reject pending batches
- Transmit approved batches to the bank
- Cancel batches before transmission
- Confirm payments from bank statement evidence

**Available Tools:**

| Tool | Purpose |
|------|---------|
| `submit("payment_batch", "create", {...})` | Create new payment batch |
| `submit("payment_batch", "add_line", {...})` | Add payment line to draft batch |
| `submit("payment_batch", "remove_line", {...})` | Remove line from draft batch |
| `submit("payment_batch", "edit_line", {...})` | Edit payment amount on a batch line |
| `submit("payment_batch", "submit", {...})` | Submit batch for approval |
| `submit("payment_batch", "approve", {...})` | Approve pending batch — **only when no approval workflow is in flight**; normally you complete the task `submit` created (see Status Lifecycle) |
| `submit("payment_batch", "reject", {...})` | Reject pending batch — same caveat as `approve` |
| `submit("payment_batch", "transmit", {...})` | Transmit an approved batch (moves money on the connector route; runs the organisation's transmit workflow). Only when the user asks for that batch (see Bank Transmission) |
| `submit("payment_batch", "cancel", {...})` | Cancel batch |
| `submit("payment_batch", "update", {...})` | Correct `batch_date` (label only, no GL effect) |
| `submit("payment_batch", "confirm_line", {...})` | Confirm single line from bank statement |
| `submit("payment_batch", "confirm_batch", {...})` | Auto-confirm all lines from bank statement |
| `query("payment_batch", filters)` | List payment batches |
| `query("payment_batch", query)` | Search batches |
| `get_entity("payment_batch", id=X)` | Get single batch: `related.lines` = the lines that can still be paid (not `incomplete`, `excluded` or `cancelled`; their sum is `total_amount`), `related.incomplete_lines` = lines without a bank account, `related.held_lines` = held lines with `excluded_reason`, `related.cancelled_lines` = cancelled lines |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any operation above, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

---

## Payment Batch Lifecycle

```
draft → pending_approval → approved → transmitted → completed
  ↑            |                                       ↓
  |            v                              partially_completed
  +-------- rejected                                   ↓
                                                    failed

draft/pending/approved → cancelled
```

| Status | Description | Allowed Actions |
|--------|-------------|-----------------|
| `draft` | Batch created, editable | add_line, remove_line, edit_line, submit, cancel |
| `pending_approval` | Awaiting approval | approve, reject, cancel, remove_line, edit_line |
| `approved` | Ready for transmission | transmit, cancel |
| `transmitted` | Sent to bank (connector path: lines move to `processing` while the bank executes; a line the provider completed stays confirmable until its statement debit posts it) | confirm_line, confirm_batch, sync_status |
| `completed` | All payments confirmed | (final) |
| `partially_completed` | Some lines confirmed, some failed | (final) |
| `failed` | All lines failed | (final) |
| `rejected` | Returned to draft | (same as `draft`: add_line, remove_line, submit, cancel) |
| `cancelled` | Permanently terminated | (final) |

> `update` (batch_date relabel) is allowed in ANY status, including `transmitted` — the date is a label; no cash leg is posted from a batch, cash posts at reconciliation with the bank line's own date. Requires `edit_reason`; Yellow lane by default.

> **Approving is not a `submit()` call.** `payment_batch.submit` moves the batch
> to `pending_approval` **and creates the approval workflow** whose id is stamped
> on `bank_payment_batches.approval_workflow_id`. Approval happens by completing
> **that task** — via `manage_submissions(action="decide")` or the admin UI. Calling
> `submit("payment_batch", "approve", ...)` while that workflow is still in
> flight is rejected on purpose: it would spawn a second, redundant approval task
> that could only fail later. The `approve` / `reject` operations exist for
> batches with no approval workflow in flight, not as the normal path.
>
> Before a MCP decision, read `get_submissions(action="task_details", task_id=...)` and pass the returned `payload_hash` as `expected_payload_hash` to `manage_submissions(action="decide", ...)`. A stale supplied revision is refused before recording any decision. Refresh the task and review the changed payload before deciding again.
>
> After the final task decision, verify both workflow history and batch status. The final reviewer is recorded as the batch approver; execution authority remains the submitter's. Do not supply an approver ID in the payload. Self-approval is refused when another eligible reviewer exists; the sole-reviewer exception remains. Multiple steps alone do not require a different person at each step.
>
> If task approvals are recorded but execution fails, the workflow may be rejected while the batch is still pending. Use the supported rejection/recovery operation and resubmit after the cause is fixed, or cancel a disposable test batch. Never transmit based on task approvals alone.
>
> Which lane a batch gets is decided by the definition's lane rules; whether that
> lane has approval steps is your organisation's workflow configuration. The
> `status` in the result is authoritative. If a batch sits in `draft` and will not move, check that
> `payment_batch.approve` has an active workflow definition for the org before
> assuming the batch itself is broken.

---

## Creating a Payment Batch

### Step 1: Create the Batch Header

```javascript
// Discover required fields first
schema = get_submissions(action='schema', object_type="payment_batch", operation="create")

// Then submit with discovered fields
submit("payment_batch", "create", {
  legal_entity_id: 4,
  payment_method: "ach",              // ACH, WIRE, SEPA, CHECK — any spelling, stored canonical
  batch_date: "2026-02-25",           // or payment_date (alias)
  currency_code: "EUR",
  bank_account_id: 1,                 // or from_bank_account_id (alias); OPTIONAL — omit to use
                                      // the entity's is_default_payments account in this currency
  description: "February vendor payments"  // optional
})
// Tip: Use validate_only=true to check payload before submitting
// Returns: { batch_id, batch_number: "PAY-000001", status: "draft",
//            total_amount: 0, line_count: 0 }
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `legal_entity_id` | number | Legal entity ID |
| `payment_method` | string | Payment method: `ach`, `wire`, `check`, `sepa` |
| `currency_code` | string | ISO 4217 currency code (USD, EUR, etc.) |
| `bank_account_id` | number | Source company bank account ID |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `batch_date` | string | Batch date (YYYY-MM-DD), defaults to today |
| `description` | string | Batch description |
| `invoice_ids` | number[] | Auto-add lines from these AP invoice IDs |

**Notes:**
- `batch_number` is auto-generated by a database trigger (format: `PAY-000001`)
- The bank account must be active and belong to the specified legal entity
- The system accepts both `bank_account_id` and `from_bank_account_id` (alias)
- The system accepts both `batch_date` and `payment_date` (alias)

### Step 2: Add Payment Lines

```javascript
submit("payment_batch", "add_line", {
  payment_batch_id: 1,                // or batch_id (alias)
  master_vendor_id: 153,
  payment_amount: 3500.50,            // or amount (alias)
  vendor_bank_account_id: 3,          // optional: auto-selects default
  source_transaction_id: 1001,        // optional: link to AP invoice
  source_reference: "INV-2026-001"    // optional: reference text
})
// Returns: { line_id, line_number, vendor_name, payment_amount, status: "pending" }
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `payment_batch_id` | number | Batch ID (or `batch_id` alias) |
| `master_vendor_id` | number | Vendor master ID |
| `payment_amount` | number | Payment amount (or `amount` alias) |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `vendor_bank_account_id` | number | Specific vendor bank account (auto-selects if omitted) |
| `source_transaction_id` | number | AP invoice transaction ID to link payment to |
| `source_reference` | string | Invoice number or reference text |
| `payment_reference` | string | Bank-file payment reference. Defaults from the vendor's `remittance_reference` when omitted on vendor lines |
| `payment_memo` | string | Memo/narrative for bank file generation (stored in `bank_payment_batch_lines.payment_memo`) |

**Notes:**
- `line_number` is auto-assigned sequentially
- If `vendor_bank_account_id` is omitted, the system auto-selects the vendor's bank account where `is_default_payments = true` and currency matches the batch
- The batch must be in `draft` status to add lines

### Step 3: Remove a Line (if needed)

```javascript
submit("payment_batch", "remove_line", {
  payment_batch_id: 1,                // or batch_id (alias)
  line_id: 5
})
// Recalculates batch total_amount and line_count
```

The batch must be in `draft` or `pending_approval` status. Removing lines while in `pending_approval` is used by approvers to exclude specific vendors before approving. Removing the last line results in `total_amount: 0` and `line_count: 0`.

### Step 4: Edit a Line (if needed)

Any combination of amount, reference, and memo — at least one required:

```javascript
submit("payment_batch", "edit_line", {
  payment_batch_id: 1,                // or batch_id (alias)
  line_id: 5,
  payment_amount: 2800.00,            // or amount (alias) — recalculates batch total
  source_reference: "INV-2026-0193",  // correct an auto-generated reference
  payment_reference: "2200221234567", // bank-file reference (e.g. tax office ref)
  payment_memo: "July payroll taxes"  // payee-visible memo for the bank file
})
```

The batch must be in `draft` or `pending_approval` status. Editing during `pending_approval` allows approvers to adjust amounts during review. Reference/memo edits do not change batch totals.

---

## Submitting for Approval

```javascript
submit("payment_batch", "submit", {
  batch_id: 1
})
// Returns: { batch_id, status: "pending_approval", total_amount, line_count,
//            submitted_by, submitted_at }
```

**Validation:**
- Batch must have at least 1 actionable payment line (excludes `incomplete`, `excluded`, `cancelled` lines)
- Batch must be in `draft` status

---

## Approving or Rejecting

When a batch is submitted via `submit("payment_batch", "submit", {...})`, a workflow approval task is automatically created. The approver must complete the task in the admin dashboard at `/workflows/my-tasks` — not via the `approve` or `reject` tools directly.

### Workflow-based approval (standard)

After submitting, the batch enters `pending_approval` and a task appears in `/workflows/my-tasks`. The approver:
1. Opens the task in the admin dashboard
2. Reviews payment lines — can uncheck individual vendors to exclude them before approving
3. Lines with missing bank accounts are automatically disabled (status `incomplete`)
4. Clicks Approve or Reject:
   - **Approved lines** → status changes from `pending` to `approved` (ready for transmission)
   - **Unchecked lines** → status changes to `excluded` (stays in batch for audit, not transmitted)
   - **Incomplete lines** → remain `incomplete` (unchanged)
   - A bill comes back to the next proposal when its line is held (`excluded`), `cancelled` or reported failed by the provider (`failed`: rejected, declined or reverted), or when its line is `incomplete` on a finished batch (transmitted, processing, partially completed or completed). A line whose outcome is unknown (`processing`) keeps the bill, so nothing is paid twice.

In the template workflow definition, batches with `total_amount >= 50,000` (in the batch currency) are assigned the **Red lane** (high-risk); the organisation can change the threshold, and which roles must approve is its workflow configuration. Use `approval_lane` and `approval_status` for the child approval workflow. `lane` describes the outer submission workflow.

### Direct approval (legacy batches without a workflow)

For batches that predate the workflow engine (no `approval_workflow_id`), direct approval is still available:

```javascript
submit("payment_batch", "approve", {
  batch_id: 1,
  approval_note: "Reviewed — all invoices verified"  // optional
})
// Returns: { batch_id, status: "approved", approved_by, approved_at }
```

**Separation of duties:** The approver must be a **different user** than the submitter. Self-approval returns an error.

```javascript
submit("payment_batch", "reject", {
  batch_id: 1,
  rejection_reason: "Vendor 153 amount doesn't match invoice"  // required
})
// Returns: { batch_id, status: "draft", rejected_by, rejection_reason }
```

After rejection, the batch returns to `draft` status. The submitter can edit lines and resubmit.

---

## House Bank (which of OUR accounts pays a payee)

Each payee bank account can carry `preferred_source_bank_account_id`
(vendors mig 266, employees mig 532): the proposal agent pays that payee
from this account when the currency matches, else falls back to a
currency/method-matched entity account (preferring `is_default_payments`).
Set or clear it via update on the payee's bank account:

```javascript
submit("employee_bank_account", "update", {
  employee_bank_account_id: 12,
  preferred_source_bank_account_id: 7   // or null to clear
})
```

Batches group per (payment_method, currency, source bank) — one batch per
house bank per run.

## Transmitting to Bank

### Transmitting a batch

Transmission is available through the connector and in the admin dashboard
(Runs → Payment proposals → open the batch → Transmit); both go through the same
gateway and the organisation's `payment_batch.transmit` workflow, so any
approval steps it configured apply to either. Two routes exist: **bank
transmission** through the linked bank connector, which moves money, and the
**file route** (`route: "file"`), which only records that the user uploaded the
payment file to the bank by hand.

Transmit only when the user asks you to transmit that batch. First confirm its
state with `query(entity_type="payment_batch", …)` (it must be `approved`) and
tell the user what will happen: batch number, total, and whether money leaves
through a connector or the file route is recorded. Then
`submit("payment_batch", "transmit", {"batch_id": …, "connector_id": …})` for
the bank rail, or `{"batch_id": …, "route": "file"}` for the file route. If the
workflow parks it for approval, the approver decides it with
`manage_submissions(action="decide", …)` or in Tasks. Read the result:
`lines_accepted`, `lines_failed` and per-line statuses, and say plainly if any
line failed or its outcome is unknown. A `posting_unknown` answer means the
outcome needs checking: do not resubmit under a new identity.

What a transmit does (from the connector or the dashboard's Transmit button), so you can explain the outcome:

- **The rail follows the bank account.** Without a route, the batch is paid
  through the connector its source bank account is linked to. If the account
  has no payment connector, or the linked one is disabled, in another entity
  or cannot pay, transmission is **refused**; the batch is never quietly
  stamped transmitted while no money moved. The file route records that the
  payment file was uploaded to the bank by hand and contacts no provider.
- On the connector rail (payment-capable connectors, e.g. Revolut), real
  payments are sent through the provider's API, one payment per line,
  idempotent, and per-line results are persisted (provider identity/status,
  definitive failure, or an uncertain processing attempt; lines with no bank
  account on file fail locally and are never sent). A definitive rejection is
  recorded as failure with the provider's reason on the line (`failure_reason`,
  also in the transmit result's `line_results[].error`): for Revolut an HTTP
  400, 401, 403, 404 or 422 answer, e.g. "Revolut rejected the payment (HTTP
  422): Insufficient balance". Tell the user that reason; nothing was paid. A
  401/403 reason says the Revolut connector needs re-authorising. A reason
  starting "Not sent to" means the connector stopped before sending anything
  (token refused, source account not found): nothing was paid either. A
  timeout, 5xx or other answer, missing response or conflicting provider ID
  leaves the attempt `processing` with `transmission_uncertain=true`;
  `review_required` and `uncertain_line_ids` signal review, not permission to
  resend. If `sync_status` cannot establish the outcome, keep the reservation
  and investigate.

Providers settle asynchronously. Recovery and status checks stay available
through the connector:

```javascript
submit("payment_batch", "sync_status", { batch_id: 1 })
// Updates in-flight lines from the provider and rolls the batch up:
// processing → completed / partially_completed / failed
```

If `sync_status` cannot establish an uncertain line's outcome, keep the
reservation and investigate.

**Important:** No GL entries are created at transmission time. Cash GL entries are created when payments are **confirmed from bank statements**.

### Manual Transmission (No Bank Connector)

When the source bank account has no payment connector, the payment file is generated (by Claude, a payout plugin, or any other tool) and uploaded to the bank by hand:

1. **Generate payment file**: User asks Claude to generate a SEPA pain.001 XML or CSV for the batch. **The file holds only the lines whose status is `pending` or `approved`** — the lines transmit sends. Leave out `excluded` (held), `incomplete` and `cancelled` lines, and set `NbOfTxs` / `CtrlSum` (or the CSV's count and sum) from those lines. `get_entity("payment_batch", id)` already lists the other lines apart (`related.incomplete_lines`, `related.held_lines`, `related.cancelled_lines`), so `related.lines` holds exactly the lines for the file and its sum equals the header's `total_amount` / `line_count`. A held line's bill can be proposed again on a later batch, so paying it from this file pays it twice.
2. **Download and upload**: User downloads the file and uploads it to their bank portal
3. **Mark as transmitted**: After uploading the file, the transmission is recorded with the file route (`route: "file"`): the user clicks Transmit in the admin dashboard, or asks you to submit `payment_batch.transmit` with `route: "file"`. That records the transmission and never contacts a provider, even when the source account is linked to one. A plain transmit on an account with no connector is refused, not recorded.

**Important**: Generating a payment file alone does not mean it was sent. Record the batch as transmitted only after the user confirms the upload to their bank.

---

## Resending refused lines

Refused lines are never retried in their own batch. When the user has fixed the
cause (topped up the account, re-authorised the connector), create a new batch
from them and take it through submit and approval as usual:

```javascript
submit("payment_batch", "create", {
  legal_entity_id: 40,
  failed_lines_from_batch_id: 23,   // the refused batch
  payment_method: "SEPA",
  payment_date: "2026-11-03",
  currency_code: "EUR"              // the source batch's currency
})
// result.resent_line_ids = the refused lines copied into the new draft
```

Only lines refused without a provider payment are copied (payee, amount and
source are kept). Tell the user what the result reports:
- `skipped_lines`: already resent in a live batch, or the document is no longer
  payable, reserved by a proposal, in another live batch or paid since — each
  with its reason;
- `incomplete_lines`: the payee's bank account is no longer active, so the copy
  has no account; the user gives the payee a current account, removes that line
  (or cancels the batch) and resends.

A payroll batch is resent whole, including lines that were `incomplete` because
a payee had no bank account (they take the payee's current account): if some of
its lines were paid or are still in progress, a payee has no active bank account, or the payroll run was
voided or its journal reversed (it was redone), the resend is refused and
nothing is created; tell the user why and do not split it by hand.
If a copy is refused too, resend from the copy's batch. A line the status sync
failed after the provider created the payment is never copied: ask the user to
check the bank statement first. Do not resend lines whose outcome is unknown —
recover them with `sync_status`.

## Cancelling a Batch

```javascript
submit("payment_batch", "cancel", {
  batch_id: 2,
  cancellation_reason: "Payment run postponed"  // required
})
// Returns: { batch_id, status: "cancelled" }
```

Can cancel batches in `draft`, `pending_approval`, or `approved` status. Cannot cancel `transmitted` batches.

---

## Payment Confirmation

After transmission, payments are confirmed when they appear on bank statements. This is when GL entries are created.

### Confirm a Single Line

```javascript
submit("payment_batch", "confirm_line", {
  legal_entity_id: 4,
  statement_line_id: 500,             // bank statement line ID
  batch_line_id: 10,                  // payment batch line ID
  confirmed_amount: 3500.50,          // optional: override if bank amount differs
  confirmed_date: "2026-02-26"        // optional: override date
})
// Creates AP_PAYMENT GL entry, links statement line, updates batch line to "completed"
```

### Auto-Confirm Batch from Statement

```javascript
submit("payment_batch", "confirm_batch", {
  legal_entity_id: 4,
  statement_id: 50,                   // bank statement ID
  batch_id: 1                         // optional: specific batch (default: all transmitted)
})
// Returns: { matches_found, confirmed, failed, unmatched_statement_lines, unmatched_batch_lines }
```

### Automatic settlement identity

The bank processor and `confirm_batch` use the same conservative matcher. Automatic confirmation requires one unique exact payment reference, provider payment ID, or echoed `arfiti-<batch>-<line>` request ID. Substring references, amount-only matches, and name/amount tolerances never authorize cash posting. Matching amount and currency must agree; a statement dated before the batch is held for review.

Conflicting or duplicate identities and amount-only candidates need review. `confirm_batch` returns them in `review_required` without posting. The bank processor marks unclear candidates or failed confirmations `needs_review` and does not fall through to classification of a new payment. For legitimate fees, FX or reference differences, review the source evidence and use explicit `confirm_line` only when its supported settlement rules permit it.

For an incorrectly confirmed payment, use `transaction.reverse` with the original settlement transaction, entity, reversal date and reason. The reversal atomically reopens its uniquely linked completed batch line to `transmitted`, clears the statement match into `needs_review`, and reopens a sole-source canonical bank movement. Reversal history stays in metadata and the original ledger entry remains linked to its reversal. This does not resend money, cancel a provider payment or remove approval. Reconfirm only after reviewing the correct source evidence.

Recovery refuses multiple/missing statement links, incompatible batch states, active confirmation claims and canonical movements shared with other source representations; the entire reversal rolls back. Do not unmatch the statement first: recovery needs the original linkage. A statement-derived external reference is cleared when it differs from the batch's payment reference; the previous value is retained in recovery history. Generic transactions without a linked batch settlement retain ordinary reversal behavior.

### Atomic confirmation and existing-posting review (local implementation)

A new confirmation commits its cash posting, source application, batch link and
statement link in one database transaction. An error or lost connection before
commit leaves none of those new writes committed. A lost response during commit
is uncertain: re-read the recorded result rather than assuming rollback. A retry after a successful
commit sees the batch's posted transaction and cannot create another payment,
even when it names a different statement line. A retry with a uniquely verified
existing settlement link returns the known IDs with `existing_effect_state: linked`;
it does not create a new hold or claim a new posting. AP posting still uses the shared
authorization and period checks. Its agent events and outbound connector jobs
commit with the posting; queue failures use savepoints and remain best effort.

An already posted movement is different from a newly created payment. Its source
invoice or expense application is not inferred from the matching bank movement.
Confirmation returns `payment_link_lost`, `effect_outcome: existing` and the known
transaction, entity, batch, batch-line and statement IDs, with review required.
This is **not a no-effect refusal**. A durable `confirmation_existing_effect` hold
blocks subsequent confirmations of that batch line against any statement. The
batch-wide operation reports this item as requiring review, not as confirmed.
Never automatically reverse the existing journal or submit another payment.

The existing operator-only `services/posted_payment_adoption.py` helper can
preview and apply an exactly evidenced, full, previously unapplied vendor payment
in functional currency. It requires the separately approved preview fingerprint
and actor/reason. Successful adoption clears only the hold naming that same
payment, statement, invoice and batch line, and retains it in the adoption audit
receipt. It is not an agent/tool operation. Partial, FX, employee/payroll and
ambiguous legacy postings require a separately reviewed recovery; there is no
generic hold-clear operation. Do not clear claims or holds by editing metadata.
Old confirmation claims without sufficient posting evidence also remain review
work; deploying this code does not repair historical records.

For new employee reimbursements, the expense source must belong to the same
employee/entity/currency and have sufficient outstanding amount. The exact source
application receipt is saved with the cash posting and links. `transaction.reverse`
undoes that recorded application once, in the same transaction as the reversal
and settlement-link recovery. A missing or inconsistent receipt on a linked legacy
reimbursement blocks the entire reversal for reviewed recovery. Reversing an
unlinked legacy journal does not by itself clear a confirmation hold.

These changes are local and require the coordinated AR-273 existing-effect
transport integration before release. They do not send or resend money, deploy
code, approve a historical repair, or change accounting policy.

### What Confirmation Creates

For each confirmed line:
1. **AP_PAYMENT transaction** — DR Accounts Payable, CR Cash (bank GL account)
2. **Invoice linkage** — Payment applied to source AP invoice (if linked)
3. **Statement match** — Bank statement line linked to new GL transaction
4. **Batch completion check** — If all lines done, batch → `completed`

---

## Common Scenarios

### Scenario 1: Weekly AP Payment Run

```javascript
// Step 1: Find due invoices
query("transaction", filters={
    legal_entity_id: 4,
    transaction_type: "AP_INVOICE",
    status: "posted"
  },
  date_filters={
    due_date: { to: "2026-02-28" }
  })

// Step 2: Create batch
const batch = submit("payment_batch", "create", {
  legal_entity_id: 4,
  payment_method: "ach",
  batch_date: "2026-02-28",
  currency_code: "USD",
  bank_account_id: 1,
  description: "Weekly AP run - Feb 24-28"
})

// Step 3: Add lines for each vendor/invoice
submit("payment_batch", "add_line", {
  payment_batch_id: batch.batch_id,
  master_vendor_id: 100,
  payment_amount: 5000.00,
  source_transaction_id: 1001,
  source_reference: "INV-2026-045"
})

submit("payment_batch", "add_line", {
  payment_batch_id: batch.batch_id,
  master_vendor_id: 200,
  payment_amount: 12500.00,
  source_transaction_id: 1002,
  source_reference: "INV-2026-046"
})

// Step 4: Submit for approval
submit("payment_batch", "submit", { batch_id: batch.batch_id })

// Step 5: Approve (different user)
// Standard: Approver completes the workflow task at /workflows/my-tasks
// Legacy (batches without workflow): direct approval via submit
submit("payment_batch", "approve", {
  batch_id: batch.batch_id,
  approval_note: "Weekly run verified"
})

// Step 6: Transmit, when the user asks for it (or they click Transmit in the
// admin dashboard). This moves money through the linked connector.
submit("payment_batch", "transmit", {
  batch_id: batch.batch_id,
  connector_id: "<the source account's connector id>"
})
```

### Scenario 2: Batch Rejection and Correction

```javascript
// Approver rejects due to incorrect amount
submit("payment_batch", "reject", {
  batch_id: 1,
  rejection_reason: "Vendor 200 amount should be $12,750 not $12,500"
})

// Submitter fixes: remove incorrect line
submit("payment_batch", "remove_line", {
  payment_batch_id: 1,
  line_id: 5
})

// Add corrected line
submit("payment_batch", "add_line", {
  payment_batch_id: 1,
  master_vendor_id: 200,
  payment_amount: 12750.00,
  source_transaction_id: 1002,
  source_reference: "INV-2026-046"
})

// Resubmit
submit("payment_batch", "submit", { batch_id: 1 })

// Approver approves corrected version
submit("payment_batch", "approve", {
  batch_id: 1,
  approval_note: "Corrected amount verified"
})
```

### Scenario 3: International Wire Payments

```javascript
// Create EUR wire batch
const batch = submit("payment_batch", "create", {
  legal_entity_id: 4,
  payment_method: "wire",
  batch_date: "2026-02-25",
  currency_code: "EUR",
  bank_account_id: 3,              // EUR bank account
  description: "EU vendor payments - February"
})

// Add EUR vendor payment
submit("payment_batch", "add_line", {
  payment_batch_id: batch.batch_id,
  master_vendor_id: 153,
  payment_amount: 3500.50,
  vendor_bank_account_id: 3        // Vendor's EUR bank account
})
```

### Scenario 4: Confirming Payments from Bank Statement

```javascript
// After bank statement is imported/synced, confirm all transmitted payments
submit("payment_batch", "confirm_batch", {
  legal_entity_id: 4,
  statement_id: 50
})
// Auto-matches statement debit lines to transmitted batch lines
// Creates AP_PAYMENT GL entries for each match
// Updates batch to "completed" when all lines confirmed

// For unmatched lines, confirm individually
submit("payment_batch", "confirm_line", {
  legal_entity_id: 4,
  statement_line_id: 505,
  batch_line_id: 12,
  confirmed_amount: 3480.00        // Bank settled slightly different amount
})
```

### Scenario 5: Check Vendor Bank Account Before Adding Line

```javascript
// Find vendor's bank accounts
get_entity("vendor", id=153)
// Returns vendor with bank_accounts array

// Or query directly
query("vendor_bank_account", filters={
    master_vendor_id: 153,
    is_active: true,
    is_default: true
  })

// If no default bank account, create one first
submit("vendor_bank_account", "create", {
  master_vendor_id: 153,
  account_nickname: "Arvutitark EUR Account",
  bank_name: "Swedbank",
  iban: "EE382200221020145685",
  swift_code: "HABAEE2X",
  currency: "EUR",
  is_default_payments: true
})
```

---

## Key Concepts

### GL Timing: Confirmation, Not Transmission

Cash GL entries (AP_PAYMENT for vendor bills; payroll/reimbursement types for employee and direct payroll liabilities) are created when payments are **confirmed from bank statements**, not at transmission time. This ensures the GL reflects actual cash movements verified by the bank.

```
Transmission:  Batch → Bank (no GL)
Confirmation:  Bank Statement → Match → AP_PAYMENT (GL created)
                                         DR AP   CR Cash
```

### Separation of Duties

The system enforces that the user who submits a batch cannot also approve it. This is a fundamental internal control for payment processing.

### Batch Number Auto-Generation

Batch numbers are auto-generated by a PostgreSQL trigger in the format `PAY-000001`, `PAY-000002`, etc. You never need to provide a batch number when creating.

### Vendor Bank Account Auto-Selection

When adding a line without specifying `vendor_bank_account_id`, the system automatically selects the vendor's bank account where:
- `is_default_payments = true`
- `currency` matches the batch currency
- `is_active = true`

If no matching account is found, the line is added without a bank account. The `submit` operation will then block until all lines have bank accounts assigned.

### Payment Proposal Agent

The payment proposal agent (`payment_proposal` agent type) can automate batch creation by:
1. Scanning open AP invoices due within a configurable horizon
2. Grouping by `(payment_method, currency_code, source_bank_id)` — three-part key ensures vendors preferring different source banks produce separate batches
3. Creating and populating payment batches (one line per invoice)
4. Auto-submitting for approval

---

## Key Takeaways

- **Payment batches** group multiple vendor payments into a single bank transmission
- **11 workflow operations** cover the full lifecycle: create, add_line, remove_line, edit_line, submit, approve, reject, transmit, cancel, confirm_line, confirm_batch
- **Transmission moves money** — available through the connector and the dashboard, both through the organisation's transmit workflow; transmit only when the user asks for that batch
- **Separation of duties** — submitter and approver must be different users
- **GL entries created at confirmation** — when bank statement evidence confirms payment, not at transmission
- **Auto-matching** — `confirm_batch` uses 4-priority matching to link bank statement lines to batch lines
- **Field aliases** — executors accept both DB column names and workflow-definition names (e.g., `batch_id` or `payment_batch_id`)
- **Batch number auto-generated** — no need to provide `batch_number` when creating
- **Vendor bank account auto-selected** — if `vendor_bank_account_id` not specified, selects default for currency

---

*Last Updated: 2026-02-25*
*Related Resources:*
- [Bank Statements Management](bank-statements-management.md) - Statement import and reconciliation
- [Bank Accounts Management](bank-accounts-management.md) - Company and vendor bank accounts
- [Vendor Management](vendor-management.md) - Vendor master data and bank accounts
- [Transaction Processing](transaction-processing.md) - GL transactions and AP invoices


## Invoice capacity and transmission recovery

Approved, transmitted, processing, and provider-completed-but-unposted lines
reserve invoice capacity. Manual AP payments, reconciliation and batch approval
share the same locked capacity check. Confirmation consumes its own persisted
reservation internally; callers cannot bypass it with an exclusion ID or flag.
An uncertain dispatch keeps its reservation until definitive rejection or native
posting resolves it. `sync_status` can recover an attempt missing a provider ID
using the original request identity; it never sends a replacement payment.
Provider completion alone is not a posted AP payment: verify
`posted_transaction_id` after statement confirmation.


### Proposal reservations and setup replies

The Payment Proposal pipeline reserves source payables before creation approval;
do not clear `payment_proposal_pending` to bypass a pending or uncertain workflow.
`proposed` means a live batch reached its approval lifecycle, not that money moved.
Changed balances/bank details require a fresh proposal. Missing source banks stay
in a configuration task instead of an unrelated fallback batch. Use the task's
Recheck bank setup option after configuring banks; completion verifies the original
live obligations and current bank setup without creating a payment. Keep on hold
and Decline preserve an explicit outcome; free text is recorded, not executed.


### Explicit file-route boundary

`route: "file"` records the caller's confirmed manual upload and never contacts
an API provider, including when the batch already stores a connector ID. Combining
that route with an explicit `connector_id` is rejected as contradictory by both
the gateway validator and executor. Omit the connector ID when recording a manual
upload. A saved connector remains available for the default connector route.


### Payroll batch confirmation: source liabilities and dimensions

For a batch line with `source_reference: PAY-RUN-{run_id}`, confirmation resolves the **exact run** linked to that batch and entity. It requires a posted, unreversed PAYROLL accrual in the payment currency. It never selects a liability from a different employee or the latest unrelated run.

- Employee net pay posts `SALARY_PAYMENT`, debiting that employee's accrued net-pay credit account(s) and crediting the bank.
- An authority/vendor payment without a source invoice, outside `payroll.tax_bill_vendor_ids`, posts `BANK_WITHDRAWAL` against the run's original vendor-tagged payroll liability credits. Multiple tax liability accounts remain separate; this does not debit ordinary AP or create another tax expense.
- Vendors configured in `payroll.tax_bill_vendor_ids` retain the existing settlement-bill/AP_PAYMENT route and its open-bill requirements. Explicit source invoices also retain AP application behavior.
- Each liability debit and its bank credit preserve the source GL master employee/vendor IDs and recorded dimensions. Current employee defaults do not replace the accrual snapshot.

The direct-accrual path currently supports full-payee settlement in the entity's functional currency. It refuses missing/reversed source accruals, duplicate active payee lines, partial/fee-adjusted amounts, foreign-currency payroll, and dimensions that are no longer eligible under posting validation. Review these cases explicitly; do not change AP profiles, drop dimensions, or invent tax filings to force confirmation. Failed validation creates no cash posting. The normal statement anchor and batch-line claim still prevent duplicate confirmations.

No migration or automatic repair of older cash entries is included. Incorrect historical postings require reviewed reversal and reconfirmation through supported workflows. The file transmission route still records a status; cash is posted only from statement confirmation. Synthetic acknowledgements/statements are only for explicitly authorized, isolated QA scenarios and are not evidence of real bank transmission.


### Approval configuration and rejection recovery

Payment approval requires an active review step after lane skips and step conditions are evaluated. Both Approval and Edit & approve (`change_request`) are human decision steps and satisfy this requirement; notification-only steps do not. A definition with no applicable review step is refused with a configuration error. Lane labels describe risk, not reviewer count; the configured step chain determines the actual reviews. Submission returns `approval_workflow_id`, `approval_lane` and `approval_status` separately from the outer submission workflow.

For “no active review step”, inspect the effective entity definition, step types, selected lane, lane skips and matching conditions before assigning a cause. Distinguish no configured steps from configured human steps that routing skipped. `approval`, `review` and `change_request` are supported human steps. If one should remain pending, preserve the revision and routing evidence for investigation. Unreleased diagnostics distinguish an empty step chain, no recognized human step, routing that skips every human step, and a human step missing from pending state despite being required. The last case calls for defect investigation. These categories do not prove an individual velocity rule or unlinked advance caused the refusal. Do not repeatedly retry unchanged configuration, remove approval controls or suggest a manual transfer as a workaround. Have an authorized administrator correct a confirmed configuration issue through the supported editor; configuration authority does not grant payment approval or transmission authority.

Rejecting (or requesting changes on) the approval task returns the pending batch to draft in the same transaction. The old workflow and its object link retain the decision history; resubmission creates a new review workflow. For legacy batches stuck pending after an already rejected approval, `payment_batch.reject` with a reason can return the batch to draft. Recovery refuses active or approved workflows and batches with transmitted/posted lines. Do not clear workflow references directly in SQL.

Migration 650 adds one mandatory admin review step only to active, uncustomized payment approval definitions with no steps, including the shared template. Existing/custom step chains and lane rules remain unchanged. Customized definitions without an applicable review step require an administrator to correct their configuration.


### Edits and rolling-total approval rules

A pending batch edit evaluates velocity rules with the original submitter and approval definition. The edited batch amount replaces its stored workflow amount once in the rolling total. If the lane is unchanged, edits before recorded approvals may proceed; if the required lane changes, reject and resubmit. Read the updated task and review its new payload hash before deciding. Do not retry with a stale reviewed hash or bypass the lane-change refusal.


### Cancellation before transmission

Approved batches can be cancelled with a required reason through `payment_batch.cancel` or the Admin batch page. Completed approval history is retained. Cancellation locks the batch and checks its current status; connector dispatch and file transmission must claim approved status before proceeding. Once transmission has started (including processing or an uncertain provider outcome), cancellation is refused. Cancellation does not recall a bank transfer or create a GL entry. Refresh after a concurrent-state refusal.


### Conditional approval order

When approval steps use condition groups, the first matching group determines the action. Later groups cannot replace an earlier automatic rejection or inclusion decision. Within an OR group, the first matching condition supplies the action/assignee. Keep one consistent action per AND group. Multiple steps still require their configured reviews; completion of one step alone does not approve a batch with further reviews pending.


Unreleased configured rejection handling: if an approval workflow rejects immediately via an auto_reject step condition, payment_batch.submit reports success=false, approval_status=rejected and status=draft. The batch link is reconciled in the submission transaction, clearing the active approval reference/submission markers while retaining the rejected workflow and object-link history. This is a policy refusal, not an approval or payment execution. Do not automatically resubmit without correcting the payload or having an authorized administrator review the rule. Local synthetic tests verify threshold behavior and draft recovery; production rollout is pending.

Local unreleased dimension-edit guard: workflow payload corrections and payment-line payload synchronization now resolve dimension approver dependencies against both the stored and proposed payload before saving. A changed or unresolved reviewer refuses the edit; reject and resubmit to establish a new route. Included steps use the saved approver rules; conditional assignee overrides and submitter-assigned steps take precedence. Dimension fallback dependencies are checked conservatively even when another rule may currently win. This does not reassign existing tasks or record decisions, and does not certify handling of later changes to employee/dimension master data.

On the QA branch, payment-batch workflow/request reads require at least one of
`payments:read`, `ap:read`, or `accounting:read` (or matching broad authority).
Salary batches additionally require `payroll:read`; payroll, AR, audit or ordinary
master-data read alone does not grant batch access. Request source tables,
request/response object types and explicit batch-ID metadata all retain this
requirement, including thread summaries and linked notifications. Entity limits
remain independent. This matches the existing MCP batch registry and Admin
attachment policy; it does not add grants or authorize a payment. Direct Admin
payment-screen reads now enforce the same batch-domain grant in the requested
organization before accessing batch data. This covers lists, details, timelines,
approval links, payment lines, pending approvals and transaction links. These
queries also exclude stored salary batches without payroll read, before list
limits and detail follow-up reads. Salary provenance uses payroll-run links,
payment-line references/types and stored source transaction types. Isolated SQL
acceptance covers lists, pending approvals, details, timelines and transaction
links. Linked payment lines and transactions must match the batch entity.
Approval pointers and timeline workflows require same-organization definitions
and the shared workflow domain/entity policy. Hosted sessions, other provenance
formats and representative-scale performance remain open.

Payment workflow reads treat `batch_id` and `payment_batch_id` as aliases for the
same batch. Either may be supplied alone; when both are present they must identify
the same batch. Conflicting aliases withhold payload/detail and collection reads
even for payroll-authorized or wildcard readers. An allowed first reference does
not authorize a different second one. These read checks do not rewrite stored
workflow payloads or change approval/write authority.

## Unreadable recipient bank details

Connector transmission reads legacy plaintext and encrypted account/routing numbers with a payment-line and executing-user audit context. Unreadable values fail that line locally without sending it; valid lines retain existing batch behavior. Review the failure and verify details before retrying. No data conversion or automatic bank-detail repair is performed.

### Confirmation authority (local AR-273 integration)

Confirmation requires the current entity scope and the financial permission for
its stored settlement route: vendor AP uses `ap:write`, salary uses
`payroll:post`, and reimbursement or direct bank withdrawal uses
`accounting:write`. Generic workflow write permission does not replace these
permissions. The same check precedes returning held or already-linked posting
IDs. Approval execution reloads the submitter's current membership and grants;
revocation while waiting does not permit posting or creating a confirmation hold.
Batch confirmation checks all eligible candidates for the requested statement's
bank before matching or applying any line. An authorization failure stops the
operation rather than becoming a per-line failure with financial identifiers.


### Payment confirmation outcomes (AR-273, local implementation)

A bank payment submitted for workflow approval remains unresolved. The processor
records `payment_confirmation_pending` and the workflow ID in statement metadata,
counts the row as needing review rather than confirmed, and does not create a
second human question for that approval. Normal unmatched-line processing excludes
that row; the existing workflow remains authoritative. This change does not add
an approval callback or claim automatic completion after approval.

A `payment_link_lost` response is a known-existing-effect failure, never permission
to retry or reverse a payment. The processor preserves the owned transaction,
source transaction, batch, entity, actual/requested statement identifiers and
existing-effect state in `payment_confirmation_evidence` in statement metadata
and the run-local review entry. Those fields survive the 500-character prose
limit. Unknown execution remains unknown; inspect execution evidence before any
further action. These changes introduce no country or accountant policy.

The payment-review write checks the current line before changing it. If approval
settled the same batch and statement between submission and review, the live
posted payment link wins and the processor reports it as confirmed. An existing
linked payment likewise stays matched. Missing or unreadable evidence remains
unresolved; it never authorizes a second posting or downgrades a matched line.
