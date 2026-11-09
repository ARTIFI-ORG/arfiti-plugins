# Reconciliation evidence and recovery

Companion to [reconciliation operations](reconciliation-management.md).
Available through `get_guidance("reconciliation-evidence")`; these controls apply
to supported external callers as well as optional built-in agents.

### Residual write-off contract (bank/card processing, slice 1)

`reconciliation.write_off_item` disposes only of a current residual on an already-applied item in a completed run. `amount_paid` records total settlement, including an approved write-off: an invoice of 100 with 97 applied and 3 disposed becomes paid 100 / due 0. The payment is not applied again. A genuine zero `amount_due` stays zero even without a reconciliation stamp; only NULL uses the legacy face-amount fallback.

The executor locks the run, item and affected transaction headers and validates current remaining value before posting. It currently accepts positive AR/AP invoice residuals in one common document/functional currency. An unapplied proposal, stale balance, credit/overpayment, cross-currency difference, or existing variance/reclass journal requires review; none is silently cleared. For a forgiven receivable the journal credits AR control; for a forgiven payable it debits AP control. Configured gain/loss accounts supply the other side.

The entity's `reconciliation.write_off_limit` is mandatory; unset or exceeded means refusal. No fixed global threshold or adjusting-journal bypass applies. Missing/failed journal creation rolls back completion. Repeated/concurrent requests do not apply another disposal. For the retained legacy cohort, supported unmatch/payment-unapply and run void restore the disposed residual and original invoice application. Dated owned applications instead require explicit-date unmatch first; an owned residual additionally supplies its exact `undo_residual_journal_id` so disposal inverse, original application undo and history commit together. Run void then finalizes the inactive run without another reversal. The disposal is not additional payment cash; current period and retained-evidence date checks apply.

Residual disposal does not establish purchase identity or document adequacy. Apply the reviewed allocation and evidence-task contracts below when a bill involves several captures or purchases.

### Reviewed manual allocations (September 2026)

A bill may have several explicitly reviewed purchase links. A manual allocation
can select a linked purchase without automatic uniqueness rejecting the other
linked purchases; vendor/entity, version, source capacity and bill due checks still
apply. The agent's `bill_purchase_plans` can also apply independent purchases
without regrouping them when each has a shared typed reference or reviewed bill
link, every purchase uniquely identifies this bill, all amounts are in the bill
currency, and the complete set fits the remaining balance. The entire eligible set
is rechecked under application locks. An equal-sum combination alone remains
ambiguous. A bill whose own lines itemise several charges (one dated entry per
charge) is the separate `itemised_bill_lines` rule in the reconciliation guide. For a single-source
foreign-currency purchase, omitted source_applied_amount can be derived only from
its recorded original-currency evidence using the existing allocation service.
Never compare a EUR source amount numerically to a USD invoice amount.


### Evidence tasks for third-party settlement

Use the existing evidence agent to read the bill and the card-payment source
receipt. Equal amounts, merchant names and nearby dates are not relationship
proof. For a concrete proposed pair, submit `card_purchase.manage` with
`action: "request_settlement_review"`, `legal_entity_id`, `purchase_id`,
`expected_version`, `bill_transaction_id`, `relationship_reference`,
`attachment_ids` and `reason`. Attachments must be stored, hashed and belong to
the same entity. The resulting task snapshots both documents and the purchase.

The reconciliation owner processes the typed approve/hold/decline response.
Approval rechecks the evidence and capacity, links only that pair and posts through
the normal settlement executor. The financial effect and task outcome commit
together; repeated delivery is a no-op. Changed or missing evidence holds the task.
The vendor IDs on original documents remain intact. Direct cross-vendor linking
requires the corresponding `approval_attempt_id`; it is not a global vendor alias.

### Merchant-of-record settlement and multiple captures

The legacy prepaid-hotel agent was migrated to the native evidence-review path by
migration 608, after the supporting code shipped. It investigates document
references and creates `request_settlement_review` tasks; it does not create
synthetic clearing bills/payments or vendor aliases. Only definitions matching the
legacy algorithm were migrated; do not assume every custom agent was rewritten.

An approved purchase with multiple capture legs settles through the atomic bundle
executor: each leg consumes its own available amount, and all legs plus the task
outcome commit together. Hold/decline and stale evidence do not post. Several
independent purchases retain their identities and require the evidence and
uniqueness checks above; equal sums alone do not establish identity.

### Run scope and current obligations

Select a named period or explicit period bounds for a period run. The dashboard
requires an explicit period/all-open selection; legacy callers omitting scope and
period still scan all open work. Do not interpret an unscoped run as proof that a
particular month was reconciled. Period bounds apply to payment sources; older
open invoices can remain settlement targets. Dismissed items stay excluded.

Run counters describe the attempt, not the current outstanding queue. Inspect
current source/application state and separate statement coverage before close.
An unpaid invoice alone is not a blocking unmatched reconciliation item.


## Purchase evidence investigation (September 2026)

For CARD_EXPENSE-to-bill identity, compare original merchant amount/currency and
provider purchase-date evidence separately from settlement dates and fees.
Revolut uses `metadata.purchase_occurred_at`, or the retained routed
`metadata.original_source.transaction_date`. Do not substitute ingestion time,
change posted dates, or use nearest-date guessing. Same-day twins remain ambiguous.
The owner retries deterministic leftovers after applied matches remove competitors.

Purchase investigations are optional: `purchase_investigation_enabled` defaults
to false, including when omitted, and requires organization opt-in through an
agent revision. Only boolean `true` enables queueing; strings, numbers and other
values do not opt in. Disabling queueing does not cancel existing tasks or sagas. Normal
matching remains available when a bill arrives; a missing bill alone does not
require a chasing task. This setting does not add a period-close check.

Deployment does not overwrite an existing agent revision that explicitly enables
investigations. Startup sync (`AgentRegistry.seed_from_templates`) creates missing
definitions from the file default (`false`); existing versioned definitions are
retained, and legacy definitions are captured with their effective configuration.
Entity onboarding through `seed_agent_definitions` copies
`system.agent_definition_templates`, whose reconciliation config has no such key;
the omitted-means-off rule covers those organizations. A saved configuration that
omits the key was previously treated as on and is off after this release. Changing an existing organization's choice
requires the supported revision/approval process. This code change does not itself
activate a replacement template release.

When enabled, unresolved purchases with a vendor can enter a scoped reconciliation saga. It can
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

Reconciliation now uses the sole pipeline host. Original-currency matching precedes
functional-amount passes; leftover refunds are counted separately instead of becoming
unmatched payment tasks. Review responses expose typed outcomes: an evidence reply is
`waiting_dependency`, never proof of settlement. Approval rechecks the human reviewer's
current permissions, evidence and available capacity. Duplicate callback receipts replay
without another settlement. Expired investigation claims cannot dispatch more tools;
interrupted calls retain their spend reservation until an authoritative receipt exists.


### Control-account identity for reconciliation adjustments (unreleased)

A linked adjustment must find exactly one AP/AR control account in the target
invoice's original GL for the selected entity. Missing or mixed control-account
history requires review; the service does not substitute the first current account
or a newly changed posting profile. Without a linked invoice, a fallback is permitted
only when exactly one active control account exists. Multiple controls require an
explicit source invoice. The source transaction must also belong to the selected
entity, even when an operator provides a separate repair posting date.

Missing/inactive write-off accounts are refused rather than silently skipping the
journal. The shared writer validates the final account identity, activity and header
status before creating the journal. Resolve the source evidence or account mapping
and retry the supported operation; do not toggle manual-entry flags, invent an
account number or mark the residual resolved without its journal. These checks do
not activate AP/AR aging. The narrow residual write-off exception below now supplies
a database-validated permission; other controlled-adjustment permissions remain open.

### Explicit receipt/refund offset (October 2026)

Use `reconciliation.match` with `scope="ar"`, `legal_entity_id`,
`source_transaction_id` (AR_PAYMENT) and `refund_transaction_id` (AR_REFUND).
Omit `applications`, purchase fields and write-offs. This links an existing refund;
it neither sends money nor posts another journal. Both documents must be wholly
unapplied, posted and unreversed, with the same customer, entity, document and
functional currencies, equal absolute document amounts and exactly opposite
booked accounts in document, functional and reporting currencies. The refund
cannot precede the receipt. Preflight and execution check the same evidence;
execution locks both documents and rechecks consumption.

The dated application consumes both open items from the later document date.
`reconciliation.unmatch` uses the **receipt** ID and restores both current balances;
prior reports retain the match until the undo date. Receipt reversal releases the
refund; unmatch before reversing the refund itself. Partial refunds, FX differences,
revenue refunds and unrelated payments are not accepted by this exact-offset path.
They require their appropriate accounting workflow, never guessed netting.
Invoice connectors exclude refund targets from invoice-application exports.
Migration 649 updates both operational and report AR open-item functions, including
the future-company template, before enabling this workflow. It changes no journals
or existing application rows. Save function definitions before applying; rollback
restores those definitions after unmatching any newly created offsets.

Admin only shows a reconciliation-run link when an application actually belongs
to a run. Direct receipt/application records can legitimately have no run.

### Residual write-off source authorization (unreleased)

Before posting a residual write-off, the gateway now requires both the source and
invoice to satisfy the shared posted predicate and to have no reversing transaction.
The customer (AR) or vendor (AP) must be present and identical on both documents.
A status label alone or a same-entity link is insufficient. Missing posting evidence,
reversed documents and missing/mismatched parties are refused before creating the
journal or consuming the residual. Resolve the underlying evidence through the
supported workflow; do not override the flags or manufacture a party link.

Existing limits, same-functional-currency restriction, recorded residual checks and
locks still apply. This strengthens the source authorization of `write_off_item`; it
does not grant a controlled-journal exception, change FX treatment, or activate aging.

### Dated settlement adjustments (unreleased, migration 691)

A later-dated write-off or FX journal must not change aging before its journal date.
New application-history events now take the later of the source date, invoice date
and linked variance-journal date. If an application is initially created with a
later adjustment already attached, capture records an application-only snapshot at
the document date and the adjusted snapshot at the later journal date. Attaching
an adjustment to an existing application retains its earlier application snapshot.

This changes future history capture only. Existing immutable snapshots are not
rewritten: audit earlier events and review affected historical reports before an
entity activation. This migration grants no controlled-journal exception and changes
no live aging account membership.

### Audited residual write-off permission (unreleased, migrations 692–694)

For an entity with reviewed ordinary-journal enforcement enabled,
`reconciliation.write_off_item` can now post a same-currency residual against the
invoice's booked AP/AR control account. The database validates the existing applied
settlement, completed run in the same entity/scope, posted unreversed payment and
invoice, matching party, entity currency, configured limit, remaining invoice amount
and booked control-account basis. The journal must contain the exact two residual
lines, dated no earlier than either document, with a canonical P&L counterpart.
Revenue, expense and COGS counterparts are supported with the correct debit/credit
direction; names do not determine permission. A valid configured gain can credit an
expense account. This evidenced operation also supports a non-manual P&L account.

Successful validation creates a private, immutable receipt bound to that journal
and settlement item. Commit requires the invoice to be settled and source ledgers
to match the captured evidence. Failure rolls back the journal, receipt and
settlement together. Caller metadata or direct receipt insertion cannot grant
permission. Changing a permitted journal invalidates its permission; use supported
reversal/correction workflows rather than editing the receipt.

This exception currently supports `AP_PAYMENT`/`AR_PAYMENT` against the matching
invoice type. It does not authorize FX, credit-memo/prepayment/refund/card-funded
write-offs, multi-control allocations or arbitrary control-account corrections.
Those routes require their own evidence and permission work before entity activation.
Existing journals receive no automatic receipts. Installation leaves entity policy
and live aging membership unchanged.

The shared adjustment writer dates both gateway write-offs and agent FX adjustments
at the later payment/invoice date. Explicit repair dates must also be no earlier
than either document. A missing target in the selected entity is refused. Closed
periods are still refused; there is no automatic move into an open period. The shared writer records header `functional_amount` equal to the
functional GL debit total it books; this does not introduce currency conversion.

### Booked evidence for automatic FX (unreleased)

The reconciliation agent now checks the stored settlement and both documents'
actual GL before creating a full-settlement FX journal. It requires a first,
full AP/AR payment-to-invoice application, matching party/entity/currencies,
posted unreversed documents, balanced complete ledger amounts and the same
active control account on both documents. The account role follows subtype and
manual-entry policy; account names and `is_reconcilable` do not determine it.

The proposed signed FX amount must exactly equal the combined functional
control-account balance. A differing matcher amount cannot override that evidence.
Partial applications, previously consumed payments, other applied settlements,
multiple/different controls and incomplete evidence do not receive an automatic
FX journal. The match retains `pending_review`; its application is not silently
undone by an FX refusal. Review the outstanding variance before considering the
settlement complete; do not toggle account flags to force a journal.

The application-side check is paired with the database permission in migration
695 for the supported first full settlement described below. Other FX routes
remain unsupported under controlled-journal enforcement. No entity policy or
live aging membership is changed.

### Audited full-settlement FX permission (unreleased, migration 695)

With reviewed ordinary-journal enforcement enabled, the database permits the
first full AP/AR payment-to-invoice FX adjustment when the journal exactly clears
the combined functional control balance. The payment and invoice must share one
active control account and party, have complete balanced GL, and use the entity's
functional currency. Different document currencies are supported; NULL legacy
header functional currency inherits the entity currency. Explicit disagreement
is refused. Both source and target application amounts must be evidenced.

The reconciliation run must belong to the same entity and AP/AR scope and be
running or completed. A grouped run stamped with a different entity does not
qualify: use an entity-specific run before activating this route. The counterpart
must be a canonical active nonheader P&L account. A configured expense credit
for a gain is permitted; neither account names nor caller metadata grant access.

The database creates an immutable private `controlled_fx_permissions` receipt
bound to the journal, settlement item and booked document evidence. At commit it
rechecks the evidence and requires full source consumption and invoice settlement.
Failure rolls back the journal, receipt and settlement together. A competing
attempt cannot attach a second journal. A running run is allowed because the
agent finalizes runs after individual settlement transactions commit.

Partial allocations, previously applied documents, different/multiple controls,
card-funded settlements, prepayments, credit memos and historical receipt backfills
are outside this permission. Verify required routes before entity activation.
Existing journals are not silently grandfathered. Installation activates neither
entity enforcement nor AP/AR aging membership.


### Investigation request saga authority (QA branch; not deployed)

A stored `reconciliation_agent` request with action `investigate_purchase` must
reference a saga in the same organization and entity, with type
`reconciliation_evidence_v1` and the same checkpoint purchase ID. Current AP and
purchase-owner read rules still apply. Missing, malformed, foreign or differently
bound saga references withhold the request/thread before rows, totals and pages.

The shared graph checks supported saga checkpoints, phase metadata, linked
instances and retained references. A readable request cannot make a forbidden
descendant readable. Readable completed history and self/mutual/mixed cycles
remain supported; the active-status check used when retrying an investigation
is not a condition for reading its history. Settlement-review requests retain
their separate producer contract and do not acquire a required saga ID.

These checks neither resume a saga nor approve settlement. Do not change stored
references to bypass a read refusal. Additional unmapped metadata, arbitrary
narratives, representative performance and hosted identity acceptance remain
open. Isolated SQL validation covers this implementation; merge and deployment remain pending.


## Close evidence update (b1, awaiting deployment)

A close memo now names subledger exceptions, control differences and currencies; a balanced trial balance cannot certify an uncertified AP/AR aging report. Reversal evidence retains source document identities. This change does not repair historical payment applications or implement the reconciliation containment redesign.

## Coverage evidence storage (local prerequisite, not activated)

Migration 753 and a private repository retain immutable, unattested coverage
snapshots, invalidations and history. This does not accept new coverage declarations,
change statement statuses, alter GL, switch current readers or make period close
pass. Existing coverage behavior remains in place. Country/accountant/business
requirements remain editable policy work in AR-477; full writer adoption remains
AR-478 work. Do not treat `legacy_migration` provenance as an attestation or proof
that workers were drained. Final backfill needs a separately reviewed deployment
controller and verified worker-output manifest; no production adapter exists yet.


Local AR464 candidate only: `reconciliation.match` may carry a server-prepared
`owned_bundle` reference with the exact immutable proposal. It still uses current
entity/permission and configured workflow approval controls; the reference is not
approval. Do not invent bundle IDs, bypass a pending approval, or resubmit an
unknown attempt with a fresh financial identity. The local strict
`owned_bundle_proposal` input accepts a run, ordered exact match proposals and
configuration; preparation checks current configured authority before retaining
an attempt and then uses the existing workflow approval path. Validation-only
never prepares. Retry the original raw request/key to recover its exact saved
attempt. If workflow creation failed, a current-authorized
`bundle_recovery_payload` can be explicitly submitted through normal approval;
this references the same attempt and does not allocate a replacement. Follow a
verified `bundle_workflow_id` instead when present. Recovery does not execute
finance or prove no effect. New orchestration adoption and deployment remain
open. A receipt is historical committed evidence, not proof that a later undo
has not occurred.


Candidate native blocks1.2 retain the original worklist before submitting owned
bundles and distinguish approval waiting, unknown recovery, partial and complete
outcomes. They are not current/activated. Never treat a waiting agent's cached
summary as final application evidence, or reset a dispatching continuation to
force another attempt. Current authority is checked on continuation; no completed
agent bypass is provided. The periodic host resumes waiting stages and finalizes
existing optional saga origins through exact stored identity/generation checks.
A completion storage failure retries without another financial application.
There is no new reconciliation request type or mandatory saga. For explicit
abandoned-owner recovery, get the exact scoped `reconciliation_run` and submit its
`native_continuation.recovery_payload` through `reconciliation.match`. Never invent
or reset its owner/generation. This uses configured approval and rechecks the
original caller key/entity scope plus target native authority. Busy means a live
dispatch owns the fence; pending/approved-unresolved workflows retain their
original approval. Fenced no-effect attempts require review and cannot reuse old
approval. A committed receipt is reconciled without reposting. No elapsed-time
inference or completed-agent authority bypass is available. Release/activation
remain open in the canonical AR464 plan.

For candidate 1.2 partial runs, read `summary.owned_bundle_outcome_v1`: completed
run status does not mean every proposal applied. Confirmed refused/rolled-back
bundles retain unapplied review members and precise attempt reasons; unknown or
pending bundles do not. Use `applied_count`, `items_review`, `items_blocked` and
`bundles_blocked` according to their distinct member/bundle units. Replay does not
duplicate review rows. Changed/missing review evidence requires recovery. Never
write off an unapplied review item or use undated run void for dated applications.
The explicitly approved date is retained in shared application receipts/history;
no date or accounting policy is inferred. Candidate activation remains absent.

Draft762 clone/transaction-rollback readiness has disposable test evidence only.
It does not authorize deployment, evidence deletion, or activation of1.2. Current
pipeline pins remain1.1. Follow the canonical plan's remaining mixed-worker drain
and compatibility requirements before a release; preserve committed receipts.


### Mixed retained/candidate admission (local, not activated)

With draft762 installed, the current shared application-capacity helper checks
active owned-bundle source claims under the existing source admission lock.
Only the actual executing attempt in the same database transaction is exempt;
a matching payload token grants nothing. Conflicting admission refuses without
waiting on the reverse lock order. Installed storage requires read committed
isolation; without762 the retained helper behavior is unchanged.

The current call-site census covers reconciliation single-match and batch writers
(shared by retained1.0/1.1 and candidate1.2), and posted-payment adoption. It does
not cover arbitrary SQL, every application producer, or old deployed binaries
without this helper. Such workers require explicit operational drain before
candidate work is admitted. Do not disable current authorization needed to finish
pending approvals as a substitute for stopping new dispatch.

Code rollback must retain owned intents, claims, workflows, continuations and
committed receipts, and leave a compatible path to settle existing work. Inventory
must classify unresolved prepared/executing/unknown attempts, pending approvals,
active claims and unsettled continuations separately from retained committed
receipts. Empty observed work is not proof that external workers have stopped.
No committed-data uninstall or production drain has been performed.


### Owned application undo and current summaries

Candidate1.2 retains the original committed bundle receipt after a supported
explicitly dated unmatch. That receipt proves historical execution; it is not
permission to reapply the original attempt. Re-invocation holds for review of
current application/authorized undo evidence and emits no new completion event.
A legitimate undo does not itself require another financial rollback.

Completion rereads application state rather than presenting saved committed
counts as currently active. A complete read with every original member inactive
proves zero current applications. If changed bundle evidence includes active or
missing members, current count/amount totals are unavailable, not zero:
`applied_count_available=false`, `applied_amount_available=false`, nullable totals,
and an explicit review message. The run's scalar accounting counters retain their
last projection in that unavailable case; consumers must use the availability
flags in `summary.owned_bundle_outcome_v1` for current interpretation. Historical
committed member count and immutable receipts remain separate. No retained
pipeline version or current registration was changed.

Dashboard run totals represent the latest recorded run observation, not a live
recalculation after every later accounting action. Reconciliation/card run lists
and details, the reconciliation timeline, and card aggregate statistics now honor
owned summary availability and observed values before scalar columns. Available
owned zero overrides an older scalar amount; unavailable totals display
“Unavailable” without a zero or match percentage. Ordinary rows without an owned
summary retain recorded values; missing or blank amount evidence is unavailable,
while an explicitly recorded zero remains zero. Independent undo does not automatically
refresh a saved run observation; a fresh completion readback can return newer
observations without rewriting past completion events.


### Owned card purchase undo (2026-10-23)

With reviewed migration 767 installed, the supported `reconciliation.unmatch`
workflow accepts `undo_bundle_receipt_id`, `source_transaction_id`,
`reconciliation_run_id`, `legal_entity_id`, an explicit `undo_effective_date`, and
`reason`. Obtain the original receipt from scoped `get(reconciliation_run)`:
`owned_bundle_receipts[].receipt_id`. Preparation is not financial approval;
current configured workflow permission, original API key/entity scope and approval
remain required at execution. No built-in saga is required.

The initial capability covers an unchanged owned card purchase revision, exact
original receipt/run members, one recorded source/target currency, and their
CARD_EXPENSE_RECLASS journals. Selecting one leg selects the entire original
bundle. Other runs' allocations and consumption remain intact. Arbitrary historical
card applications, changed membership, mixed currencies and ambiguous existing
reversals are outside this capability and refuse without partial effects.

The caller chooses the date; it cannot precede affected original/history evidence,
be future-dated or fall in a closed/locked period. Exact inverse journals, inactive
history on that date, source/invoice capacity and an immutable undo receipt commit
atomically in the approved workflow transaction. A later-leg failure rolls back
all undo work even when an outer caller catches it. Original bundle evidence is
retained. Identical receipt/date/reason/actor replay returns the saved result;
changed input conflicts and never sweeps later applications into an old undo.

Missing or altered storage guards refuse. Concurrent effective-policy editing may
cause a nonwaiting refusal; retry after that edit settles, with current authority
rechecked. This protocol does not widen simple-cash/native allocation receipts or
invent an accounting date policy. It is locally verified, not deployed; retained
pipeline versions and current activation pins are unchanged.


### Owned residual writeoff and dated undo

The locally verified owned residual protocol covers same-currency, dated cash
applications to AP/AR invoices with retained original application evidence. It
requires migration768's complete storage manifest, the existing controlled693
writeoff policy and the current configured workflow permission/approval controls.
No built-in agent or saga is required. Missing or altered storage refuses before
financial effects; installing a table alone is insufficient.

Submit `reconciliation.write_off_item` with an explicit
`write_off_effective_date` and the existing item/reason inputs. The date must
satisfy retained application/history and current period checks; the service does
not choose it. Current configured account/limit policy remains authoritative.
Pending approval creates no disposal. Execution rechecks the original submitter's
current key, entity scope and permissions, including after delayed approval.

The original application receipt and cash consumption remain unchanged. The
existing693 receipt records the disposal journal and its dated approved input;
target settlement increases only by that retained disposal. Use the returned
`write_off_journal_entry_id` as `undo_residual_journal_id` in the existing
`reconciliation.unmatch` operation, with exact source/run/entity, AP/AR scope,
reason and explicit `undo_effective_date`. Combined undo reverses that journal
once, releases the original cash application, restores invoice capacity and writes
dated inactive history atomically. A late failure rolls back the entire undo.
Original application, bundle and disposal evidence remains retained.

Exact retries return the recorded operation result without another journal or
inverse. A historical receipt does not assert that an application remains active
after a legitimate undo. Run totals represent the latest recorded run observation;
independent writeoff/undo does not promise automatic refresh of saved run totals.
Do not retry an unavailable owned operation through an undated legacy call.

This capability does not extend to FX residuals, arbitrary historical applications
or the separately scoped card-purchase undo protocol. Legacy cohorts retain their
existing contracts. The existing `void_run` finalizes only after active dated applications have
been undone explicitly; see the cancellation/finalization contract below. This is local implementation verification, not
production deployment, policy approval or pipeline activation.


### Cancelling a partial run and finalizing void

`agent_instance.cancel` stops cancellable orchestration; it does not reverse
committed accounting. Independent committed bundles remain readable and retain
their receipts. A cancelled native instance cannot dispatch new owned financial
work; delayed financial approval must still pass current native authority and
cannot revive it. Unresolved attempts/claims remain visible until supported
recovery proves their outcome. Cancellation is never a no-effect certificate.

For a completed partial reconciliation run, `reconciliation.void_run` refuses
while dated applications remain active. First use the supported explicitly dated
`reconciliation.unmatch` for each intended application: plain cash, exact card
bundle receipt, or residual journal identity as appropriate. Each operation uses
its own configured approval, current authority and retained date/evidence checks.
Void does not infer an undo date or perform a new bulk financial protocol.

After supported undo, the existing void operation can finalize the run. It checks
the run's current entity access even with zero active items and refuses unresolved
owned attempts or source claims. On installed762, public void retains the exact
original key/entity scope and approved payload in immutable submission evidence;
it rechecks current authority in the same approved transaction, including after
an approval wait. Broadening the key later does not broaden the original scope.
Malformed retained authority refuses rather than becoming unrestricted. Tenants
without762 retain the existing legacy contract; this is not a blanket legacy-key
retention certification. It preserves failed/manual-review members and all
original receipts/history; it does not dismiss those records. Public same-key
replay returns the prior result without another financial effect.

Current shared retained1.0/1.1 and candidate1.2 writers fence terminal voided runs:
financial applications, review/card records and summary writes cannot reopen the
run. Contention refuses without waiting on an inverted run lock; retry after the
other owner finishes, using current evidence. Completed nonvoided runs retain
supported reconsideration behavior. This shared-import compatibility correction
does not change retained block registrations or pipeline pins. Old binaries that
do not load these helpers still require operational drain; arbitrary SQL and
production worker shutdown are not certified by the local tests.


### Dashboard void submission result

The bank and card run pages distinguish a submitted or pending void workflow from confirmed finalization. They show “Run voided” only when the gateway returns successful executor evidence for the requested run and an explicit item count. Approval alone, unknown recovery status, or missing completion evidence stays unconfirmed; no absent count becomes zero. The workflow reference and status remain in the router response. This changes notification wording, not approval policy or financial undo: dated owned applications still require their explicit authorized undo before run finalization.


### Owned match approval retains original authority

Owned `reconciliation.match` submissions retain the authenticated originating key, entity scope and exact saved approval payload in private immutable submission evidence. Delayed approval rechecks that original key's current validity and scope, current caller permissions and configured entity policy before effects. A configuration writer conflicting with the permission fence causes refusal, not execution under a stale policy. Legacy match requests without `owned_bundle` retain their existing route.

Owned matching requires reviewed 762 storage, including the private immutable submission guard. Missing or altered guards/ACLs refuse before execution. Previously pending owned workflows without retained submitter evidence remain unexecuted and require explicit review/recovery of their existing attempt. Do not infer authority from the approver or create a fresh financial attempt to bypass this hold; inspect existing receipt/attempt evidence first. No deployment, worker drain or repair of historical pending submissions is performed by this implementation.

The same exact native submission identity/retention prerequisite applies when installed762 void or native recovery reads that shared evidence. A missing primary key, conditional or disabled retention trigger, altered retention function, or nonprivate grants makes that capability unavailable; it does not widen authority. Tenants without762 retain the existing nonowned legacy void route.
