---
name: arfiti-period-close
description: Run the month-end close for one legal entity and fiscal period in Arfiti through the MCP tools only - collect the evidence for each standard check, report every finding with its evidence, decide which findings block from the client's own close rules (never from this skill), fix what ordinary operations or the helpers can fix, raise plain-language tasks for the rest, and close the period through submit(object_type="fiscal_period", operation="close") when asked and nothing the client calls blocking is open. Also resolves a paused built-in close saga. Never forces, never reopens, never locks.
---

> **Without a roster (Cowork, Claude Code).** Where this skill hands work to the
> master-data or configuration agent, no such agent is available: follow the
> `arfiti-master-data` or `arfiti-configuration` skill in this plugin yourself, with
> the same brief, and come back here with its result block. Step 0 (confirm the
> organisation) still applies: your own sign-in decides which organisation you are in.

# Close one period

Uses only what the public MCP tools can do. The paused-saga procedure is the
last section here.

The close does not need the built-in month-end saga. `fiscal_period.close` is an
ordinary gateway operation: inside its own transaction it re-runs every
registered check and refuses the close when an integrity check fails, when a
check the organisation's close policy calls blocking fails, when a draft
transaction sits in the period, or when the trial balance does not tie. This
skill does the rest of a close: collect the evidence, put it in front of the
client's rules, resolve what can be resolved, and ask a person for what
cannot.

Tools: `query`, `get_entity`, `get_guidance`, `get_organization` (read:
`get_info`), `read_attachment`, `generate_report`, `get_submissions`,
`submit`. Helpers (roster): the master-data agent (parties) and the
configuration agent (setup: posting profiles, accounts, FX profiles, rates).

## What decides what

| Part | Who decides | Where it lives |
|---|---|---|
| Evidence for a check | This skill, through the tools | The records |
| Integrity: period open, trial balance ties, reversal pairs complete, AP and AR control accounts tie to their subledgers | The system; nothing lowers them | The integrity checks `fiscal_period.close` re-runs |
| Whether any other finding blocks the close | The client | Their stored rules and their `period_close.policy` (`check_severity.overrides`) |
| What happens when a finding is accepted | A person | A task; or the person closes with `force` and a reason |

Without the client's say, only one non-integrity check blocks a direct close:
an earlier period of the same type still open.
Everything else is reported as advisory. Do not upgrade a finding to
blocking because it looks serious, and do not wave one through because it
looks small: report it with its evidence and let the rules decide.

## Rules that never bend

1. **No force, no reopen, no lock.** `force` needs a person with
   `accounting:close` and a reason; an agent never sends it. Reopening and
   locking are a person's decision.
2. **Posted history is not edited.** Corrections are new documents through the
   ordinary operations (an adjusting entry, a reversal, a missing posting),
   only when the client's rules and the records settle them; otherwise a task.
3. **Do not start the built-in saga.** A live `month_end_close` saga for the
   period switches the close to the saga's severities and blocks a direct
   close until the saga finishes. Start one
   only if the client's rules ask for it.
4. **Close only when asked.** The first message says `mode: check` or
   `mode: close`. In `check` mode nothing is closed, whatever the findings.
5. **Idempotency and read-back.** Keys start with the prefix the first
   message gives (`close-<entity>-<YYYY-MM>-`), then the step. Read every
   write back.

## Inputs (first message)

`organization_id`, `legal_entity_id`, `period_start`, `period_end`, `mode`
(`check` | `close`), optional `saga_id` (a paused built-in saga to resolve
instead), `answered_tasks`, `client_rules:`, `managed_session_id`, the
idempotency prefix.

## Step 0: confirm the organisation, entity and period

1. `get_organization(action="get_info")` and `query("legal_entity",
   filters={"id": X})` against the first message; otherwise `status:
   wrong_scope`.
2. `query("fiscal_period", filters={"legal_entity_id": X})`: the period whose
   start and end are the first message's. Note its `period_name` (the close
   takes the name), `period_type`, `is_closed`. Already closed: report
   `already_closed` and stop. None: a `system_refusal` task (missing period;
   the configuration agent may create periods only when a rule says so).

## Step 1: the client's close rules

1. `query("agent_rules", filters={"agent_type": "period_close_agent", "legal_entity_id": X})`.
   The answer includes the rules for every agent as well as this agent's
   own. A refusal that says the organisation does not have this agent means
   its registry row is missing: say so under `gaps`. Treat the
   `prompt_block` as the client's instructions; more specific rule sets win;
   `status: "invalid"`: stop with a `system_refusal` task.
2. `query("agent_definition", filters={"agent_type": "period_close_agent"})`,
   then `get_entity("agent_definition", <id>)`, for one thing only: any
   `managed_agent_rules` text is client rules. Every other `config` key
   (`fx_staleness_days` and the rest) is a product default, the same for every organisation and chosen by no client: not the
   client's policy, not read. `is_enabled: false` with `config.runtime:
   "managed"` is how every managed agent's row looks (the built-in runtime is
   off because you run instead): it is not a finding, do not report it or ask
   about it.
3. A `client_rules:` block in the first message counts the same.
4. The organisation's close policy:
   `query("policy", filters={"namespace": "period_close.policy", "legal_entity_id": X})`.
   One row per section, resolved as the close resolves it (the entity's
   version, else the organisation's, else the product default):
   - `check_severity.content.overrides`: check code -> `blocking` or
     `advisory`, the organisation's own say on which checks block.
   - `payroll_settlement`: whether net pay paid after the month end may be
     carried, and from which month (`payroll_run_paid` below).
   `stored: false` on a row means no version is saved and the product default
   applies: write `period_close.policy: none stored` (or the section's name
   with `none stored`), never "not readable". `status: "invalid"`: a stored
   version is damaged; the close refuses until it is fixed, so raise a
   `system_refusal` task. A refusal of the read itself (permission, scope)
   goes under `gaps` with its message.

Write the rules down as a list before the checks: for each check the rules
or the policy mention, `blocking` or `advisory` and the rule's words (or the
policy's version id).

## Step 2: collect the evidence

Run each check through the calls below for the entity and the period. Record
for each: `pass`, `fail` (with the items: ids, numbers, amounts) or
`not_checked` (with why). `REACHABLE` checks you run in full; `PARTIAL` ones as
far as the tools go, saying what you could not see; `SAGA-ONLY` ones you list
as not checked.

**Configuration and environment**
- `period_open` (integrity) and `earlier_periods_closed`: the fiscal periods
  above; every earlier period of the same type closed. REACHABLE.
- `entity_config`: `get_entity("legal_entity", X)` has functional currency
  and country; `query("tax_registration", filters={"legal_entity_id": X})`
  (a missing registration is a warning). REACHABLE.
- `fx_rates_fresh`: `query("exchange_rate", filters={"from_currency": "<the entity's functional currency, from entity_config>"},
  sort by effective_date desc, limit=1)`. How old a rate may be is the
  client's policy: there is no organisation or entity setting for it in the
  public tools. A client rule that states the age decides `pass` / `fail`.
  No rule: record the newest rate's date and its age in days at period end
  as `evidence_only - no company rule on rate age`, neither pass nor fail.
  REACHABLE.

**Bank**
- `lines_confirmed`: every in-period line of every active bank account is
  matched, reconciled, confirmed or adjusted:
  `query("bank_statement_line", filters={"legal_entity_id": X,
  "recon_status": "unreconciled"}, date_filters={"transaction_date":
  {"from": <period start>, "to": <period end>}})`. REACHABLE.
- `lines_posted`: every confirmed line in the period is linked to its
  posting (`gl_transaction_id`) or to the payment-batch line that settled it
  (`payment_batch_line_id`): the same query with
  `filters={"legal_entity_id": X, "recon_status": "confirmed", "gl_transaction_id": None, "payment_batch_line_id": None}`
  lists the ones that are not (leave out lines of a voided statement).
  REACHABLE.
- `statements_cover_period` and `bank_gl_to_provider_balance`:
  `query("bank_statement", filters={"legal_entity_id": X})` (dates, opening
  and closing balances, `metadata.controls`), and the bank account's GL
  balance from `generate_report("trial_balance", as_of_date=<period end>)`.
  The statement's `metadata.controls` is the result of the balance tie and
  coverage controls the import ran (what they check is product mechanics,
  `GUIDE_BANKING_OPERATIONS.md`); report its outcome. REACHABLE.

**Cards**
- `card_lines_confirmed`: `generate_report("card_reconciliation_status",
  {"legal_entity_id": X, "period_start": "<YYYY-MM-DD>", "period_end": "<YYYY-MM-DD>"})`
  (these two names, not `start_date` / `end_date`) and
  `query("card_transaction", filters={"legal_entity_id": X})`. PARTIAL (the
  entity time-zone rule for dates is not reproduced).
- `clearing_account_nets_zero`: each card programme's clearing account
  (`query("card_program", ...)`) at zero in the trial balance. PARTIAL.

**Expense reports**
- `reports_settled`: `query("expense_report", filters={"legal_entity_id": X})`
  with `report_date` in the period: every one posted, paid, cancelled or
  rejected. REACHABLE.

**Subledgers**
- `depreciation_run`: `query("depreciation_run", ...)` covering the period and
  `generate_report("unposted_depreciation", fiscal_period_id=...)` empty.
  REACHABLE.
- `amortization_run`: `generate_report("amortization_schedule", ...)`: no
  due tranche unposted. PARTIAL.
- `billing_run` and `unbilled_contracts`: `query("billing_run", ...)`,
  `generate_report("billing_hold_list")`, `query("recurring_contract", ...)`
  against `query("transaction", filters={"transaction_type": "AR_INVOICE"})`
  in the period. PARTIAL.

**Payroll**
- `payroll_run_paid`: `query("payroll_run", ...)` for the period, and its net
  pay settled. A run whose net pay is paid after the month end passes as
  carried only when the policy's `payroll_settlement` section (step 1) allows
  it from that month. REACHABLE.

**Payments**
- `approved_untransmitted`, `failed_payment_lines`:
  `query("payment_batch", filters={"legal_entity_id": X})`, `get_entity` for
  the lines. REACHABLE.

**Reconciliation**
- `unmatched_items`: `query("reconciliation_run", ...)` covering the period,
  and no posted `CARD_EXPENSE`, `AP_PAYMENT` or `AR_PAYMENT` in the period
  with `recon_status` unreconciled
  (`query("transaction", filters={..., "transaction_type": ..., "status": "posted"})`).
  REACHABLE.

**General ledger**
- `trial_balance_ties` (integrity): `generate_report("trial_balance",
  as_of_date=<period end>)` balances in document and functional columns.
  PARTIAL (the report is cumulative to a date, not the period alone; the
  close re-checks the period itself).
- `reversal_pairs` (integrity): `query("transaction", filters={"legal_entity_id":
  X, "reversal_of_id": {"gt": 0}}, date_filters={"transaction_date": {...the
  period}})` lists the period's reversals; each names the original in
  `reversal_of_id`, and the original names it back in `reversed_by_id`
  (`get_entity("transaction", <id>, include_related=true)` for the lines when
  the amounts must be compared). A pair is complete when both are posted and
  their GL lines are opposite. REACHABLE.
- `ap_control_ties`, `ar_control_ties` (integrity):
  `generate_report("ap_aging" | "ar_aging", as_of_date=<period end>)` comes
  back certified (the same aging the close uses). REACHABLE.
- `no_draft_transactions`: `query("transaction", filters={"legal_entity_id":
  X, "status": "draft"})` dated in the period; also `pending`. REACHABLE. The
  close refuses on any.
- `control_account_signs`, `reporting_source_evidence`: control accounts by
  `account_subtype` and their sign in the trial balance; the trial balance's
  evidence gaps. PARTIAL.
- `generate_report("gl_integrity", {"legal_entity_id": X})`: unbalanced or line-less postings,
  orphan lines, dates outside a period, stale drafts. Not a close check, but
  any finding in the period is reported.
- Manual journal review: read the period's manual journal entries
  (`query("transaction", filters={"transaction_type": "JOURNAL_ENTRY", ...})`)
  and report any that look unusual (round amounts to unusual accounts,
  postings on the last day reversing on the first, a description that does
  not explain the entry). Advisory; your reading, labelled as such.

**Documents**
- `duplicate_bills`: AP invoices in the period with the same vendor,
  reference and amount. REACHABLE.
- `new_counterparty_tax_codes`, `master_vendor_tax_codes_effective`: vendors
  first used in the period and their tax codes (`query("vendor", ...)`,
  `query("tax_code", ...)`). REACHABLE.
- `ar_invoices_delivered`: SAGA-ONLY (the delivery log has no query entity).

**Tax**
- `filings_recorded`: `query("tax_return", ...)` for the period's forms.
  REACHABLE.
- `vat_authority_balance`: the period's movement on the tax accounts against
  the VAT report. The trial balance is cumulative; the period's movement on
  one account is `generate_report("account_activity", {"legal_entity_id": X,
  "account_number": "<n>", "start_date": <period start>, "end_date": <period end>})`
  (`opening_balance`, the period's lines, `closing_balance`). Run it for each
  tax account (`query("account", filters={"account_subtype": ...})` for the
  entity's input and output tax accounts) and compare with
  `generate_report("vat_report", {"legal_entity_id": X, "start_date": ...,
  "end_date": ...})`. PARTIAL (which accounts carry the authority balance is
  the entity's set-up; say which you used).
- The line tax checks (`line_tax_codes_valid`, `line_vat_math`,
  `entity_vat_registration_dated`): the lines of the period's transactions.
  PARTIAL. What a tax code should be is country policy: report differences,
  never decide them.

Do not read every transaction's lines for the PARTIAL tax checks; sample the
period's largest documents and say you sampled.

## Step 3: weigh the findings

For each failed check, its weight in this order:
1. Integrity check: `blocking`.
2. The client's rules name it: as the rule says.
3. `earlier_periods_closed`: `blocking`.
4. The organisation's `check_severity` overrides (step 1) name it: as the
   override says.
5. Otherwise: `advisory` (no rule and no override; the product default on a
   direct close).

## Step 4: resolve what you can

- A fix an ordinary operation makes from the records at hand, that the
  client's rules allow you to make (for example a missing depreciation run
  when a rule says to post it): validate, submit, read back.
- A party gap: the master-data agent. A setup gap (missing FX profile,
  posting profile, exchange rate source, missing fiscal period, an entity
  setting such as the reporting time zone): the configuration agent. Both
  are your helpers in this session ("Handing off to a helper" below); a
  person's answer that settles a setup value is handed to the configuration
  agent the same way, never raised as a refusal.
- Work that belongs to another agent (unreconciled bank lines, unmatched
  payments, unposted bills, a correction to a posted bill, draft expense
  reports): not yours, and not something to submit yourself (your user reads
  AP, AR and payroll but does not write them, so the gateway refuses it).
  Hand it to that agent ("Handing work to another agent" below) when it is
  a concrete piece of work with its evidence: a person decided a posted bill
  needs correcting, a bank or card line in the period is unmatched, a
  submitted expense claim waits. List it under `for_other_agents` as well,
  with the hand-off id. Do not raise a `system_refusal` task for it.
- Everything else: a task (below), written for the person who runs the
  business, not an accountant. "Seven bank payments from October have not
  been matched to an invoice yet. Should October be closed anyway?" with the
  options "Wait until they are matched" / "Close October and match them
  later"; the check code and the items go in `details`.

## Handing work to another agent

The bill, bank, reconciliation and expense agents are not helpers in your
session; their work is handed to them, and each runs it in its own session
under its own user, permissions and the organisation's approval steps:

```
submit(object_type="managed_agent_run", operation="handoff", data=JSON.stringify({
  "agent_type": "bill_processor" | "bank_transaction_processor" | "reconciliation_agent" | "expense_processor",
  "legal_entity_id": X,
  "brief": "<20 to 4,000 characters: what to do and the evidence>",
  "subject": {"type": "transaction | bank_statement_line | expense_report", "id": <id>, "label": "<number>"},
  "session_id": "<managed_session_id from your first message>"
}), idempotency_key="<prefix>handoff-<agent>-<subject id>")
```

Which agent: a bill (create, correct, its VAT or accounts) to `bill_processor`;
bank or card statement lines and card charges to `bank_transaction_processor`;
payments not yet applied to invoices to `reconciliation_agent`; expense claims
and receipts to `expense_processor`. The brief is all it knows: the document
and its ids, what is wrong, and a person's decision verbatim with its task id
and the chosen option. One hand-off per document; an open hand-off for the
same document comes back as `already_open` with its id.

The answer gives a `handoff_id`. Do not wait for it in this session and do
not poll: when that agent's session ends, its result block arrives here (or a
fresh session of yours starts with it), "Work you handed to another agent has
come back.", with its outcome and report as data. Read the records it names,
then carry on; what it could not do goes in your result or a task. A session
that a hand-off started cannot hand on, and you never hand work to another
period close.

## Handing off to a helper

Your helpers are the master-data agent and the configuration agent; call
them from this session (the other agents are not helpers: their work is
handed over as above). Each sees none of this conversation, so the brief
carries everything: `organization_id`, `legal_entity_id`, the problem in one
sentence, the evidence (ids, the text you read, any refusal verbatim with its
workflow id, a person's answer with its task id and the option chosen), the
goal, and an idempotency-key prefix (`<your prefix>md-` or
`<your prefix>config-`).

- **Master data** (returns `MASTER_DATA_RESULT`): a vendor or customer
  missing, found twice, or with details that differ from the documents.
- **Configuration** (returns `CONFIGURATION_RESULT`): a posting profile,
  account, fiscal period, FX profile or rate source the close needs; an
  entity setting a person has confirmed (for example "the company's time zone
  is Europe/Tallinn": the brief names the zone and the answered task).

Continue only after the helper reports `done` (or `found` / `created`) and
its read-back shows the gap closed; a helper's `pending_approval` is declared
with `managed_agent_run.wait` like your own. A helper that refuses or cannot
reach the cause: report it under `handed_off` with its result, and raise a
`system_refusal` task only for a refusal no helper can remove. One level
only: the helpers cannot delegate further.

## Step 5: close (mode `close` only)

Close when no finding weighed `blocking` is open and no task you raised in
this session asks whether to close:

```
submit(object_type="fiscal_period", operation="close",
  data=JSON.stringify({"legal_entity_id": X, "period_name": "<period_name>"}),
  idempotency_key="<prefix>close")
```

Never `force`, never `create_closing_entries` (refused: closing entries are
journals, not part of a close).

- **Pending** (the close lane is yellow by default): a person approves. Record
  the workflow id; status `close_pending_approval`.
- **Executed**: read back `query("fiscal_period", filters={"legal_entity_id":
  X})`: the period `is_closed`. Status `closed`.
- **Refused**: the message names the checks the close found failing (its own
  run, with the organisation's policy applied). Those are blocking by the
  client's policy: add them to the findings as `blocking (policy)`, resolve
  what you can, raise one `question` task for the rest ("October cannot be
  closed yet because ..."), status `blocked`. A refusal naming
  `close_saga.not_finished`: a built-in saga for the month is still active,
  paused or failed; resolve it (last section) or ask whether to cancel it;
  you do not cancel it.

`validate_only` does not run the close's checks (they run in the executor),
so there is no dry run of the close itself; the evidence from step 2 is the
dry run (gap).

## Refusals and unknown outcomes

Every `submit` answer is one of five kinds. Read which before doing anything
else (`GUIDE_WORKFLOW_MANAGEMENT.md`, "Failed execution"):

- **Executed.** Read the rows back (the read-back step).
- **Pending approval** (`status: "pending"`, a `workflow_id`, no record id):
  the organisation's approval lane holds it. Record the workflow id; do
  nothing that depends on it in this session. Then say that you wait for
  it, once per workflow ("A decision comes back to this session"):
  `submit(object_type="managed_agent_run", operation="wait", data=JSON.stringify({"session_id": "<managed_session_id>",
  "workflow_id": "<workflow_id>", "waiting_for": "<one line: what continues
  once this is decided>"}))`.
- **Replay** (`idempotent_replay: true`): the first answer to this key again;
  nothing new was written. Treat it as that first answer.
- **Definite refusal** (`refused: true`, `status: "refused"`,
  `effect_outcome: "no_effect"`, with `reason_code`, `message`,
  `workflow_id`): the server proved nothing was saved. Read `message`. When
  it names a cause you can remove from the records (a field the documents
  state, a stale version, a setup gap a helper can close and you can see),
  remove it and submit again with a **new** idempotency key (the old key plus
  `-r2`, then `-r3`). When the cause is a decision only a person can make, or
  the same refusal returns after one fix, raise a task (kind `question`
  for a missing decision, `system_refusal` when the gateway or the setup is
  in the way). A refusal with a reason is never a dead end and never a
  silent "not done".
- **Unknown** (`status: "posting_unknown"`, `error:
  "workflow_result_unavailable"`, `effect_outcome: "unknown"`, often with
  `failure_code`, `failure_reason` and `next_step`): the reason says why the
  operation failed; it does not prove that nothing was saved. Reconciliation,
  bank and card refusals (including `card_transaction.attach_receipt`) arrive
  this way today. First read the affected
  rows. Changed: it took effect; carry on with the read-back. Unchanged: act
  on `failure_reason` as for a definite refusal, and only then submit again,
  with a new key. Submitting again under the same key only replays the
  unknown answer. No `failure_reason` and the rows unchanged: raise a
  `system_refusal` task with the workflow id.

Never retry with a changed date, a force flag, or an amount or value you
made up. `get_submissions(action="history", workflow_id=<id>)` returns the
saved outcome of your own earlier submission (a workflow that was rolled back
answers `recorded: false` with the saved `outcome`); use it when a session
continues work an earlier session left pending.

**Configuration values are read, not asked.**
`query("config_setting", filters={"config_key": "<key>", "legal_entity_id": X})`
returns the entity's row (`config_value`, `is_active`); with no active entity
row, `filters={"config_key": "<key>", "legal_entity_id": None}` returns the
organisation default. Ask only when neither exists.

## Tasks for a person

Read the `arfiti-working-with-people` skill in this plugin before raising a
task and whenever one is answered: an answer is a decision you act on, and a
standing instruction in it is stored so it is not asked again.

Nothing uploaded or received is skipped. Every item this session does not
post or settle ends as a real task for a person, raised through the gateway
(`GUIDE_AGENT_REQUESTS.md`, "Review tasks any agent can raise"). Ask in a
task, not in the session: the session ends and a later session continues
from the answer.

```
submit(object_type="agent_request", operation="create", data=JSON.stringify({
  "request_type": "verification", "legal_entity_id": X,
  "request_data": {
    "action": "agent_review",
    "kind": "question" | "document_not_postable" | "ambiguous_match" | "system_refusal",
    "question": "<10 to 2,000 characters: the one decision needed>",      // not on system_refusal
    "title": "<what you need from the person, 3 to 80 characters, one line, e.g. Close October anyway, Missing bank statement, Approve the close>",
    "details": "<up to 4,000 characters: what you checked and what you concluded>",
    "subject": {"type": "fiscal_period | transaction | bank_statement | saga", "id": <id>, "label": "<number or name, up to 200 characters>"},
    "options": [{"id": "<lower_case_id>", "label": "<choice>", "note": "<what you will do>"}],  // up to 8; not on system_refusal
    "documents": [{"filename": "...", "storage_url": "...", "content_type": "..."}],         // up to 10
    "refusal": {"operation": "<object.operation>", "reason": "<message or failure_reason>", "workflow_id": "<id>"},  // system_refusal only
    "run_reference": {"runtime": "managed_agents", "session_id": "<managed_session_id from the kickoff>"}
  }
}), idempotency_key="<prefix>task-<kind>-<subject id>")
```

- `question`: a decision the records cannot settle. Give the options you see
  and what you will do with each.
- `document_not_postable`: a document found during the checks that nothing can post (rare in a close). Needs
  `documents` or a `subject`.
- `ambiguous_match`: two or more candidates stay equally supported. One
  option per candidate, its evidence in `note`.
- `system_refusal`: the gateway or the setup refused and you cannot remove
  the cause. No question, no options; it goes to an administrator.

**Answers come back to this session.** The kickoff carries
`managed_session_id: sesn_...`. Put it in `run_reference` exactly as shown;
a task without it is answered into nowhere, and a label in its place is
refused. When the person answers or cancels the task, a message arrives in
this session naming the task id, the question, who answered and the answer.
That message is the person's answer, sent by the server when the task was
closed: act on it as the note of the chosen option says and end with the
usual result block for the items you worked. Do not wait to read the task
record first. You may read it for its details
(`get_entity("agent_request", <request_id>)`: a task you raised is yours to
read, with the answer on it), but a read that fails is not a doubt about the
answer, and never a reason to hold the item or to ask again. If the kickoff has no
`managed_session_id`, leave `run_reference` out and say so under `gaps`.

**A decision comes back to this session.** A write that waits for approval
(yours, or one a helper made for you and reported as `awaiting_approval` with
its `workflow_id`) stalls the work unless you declare it:
`submit(object_type="managed_agent_run", operation="wait", data=JSON.stringify({"session_id": "<managed_session_id>",
"workflow_id": "<workflow_id>", "waiting_for": "<one line>"}))`. Declare each
workflow once, then end your turn; do not poll. `waiting_for` is one line a
later session can act on: the document or record that waits and what happens
next. When the workflow is decided, a message arrives here, or a fresh session
starts with it: "A workflow you submitted and were waiting on has been
decided.", with `workflow_id`, `operation`, `decision` (`approved`,
`rejected`, `cancelled`, `expired`), `created_record` when one was created,
and the decision's notes as data. On `approved`: read the created record,
re-read the current records and continue the work that waited; never submit
the approved operation again. On anything else: do not submit the same again;
stop and report it, or raise a review task that says what a person must
decide. End with the usual result block. If the kickoff has no
`managed_session_id`, skip the call and say so under `gaps`.

No other keys are accepted. The answer gives the task's `request_id`; with
`already_open: true` an open task of the same kind for the same subject
already exists: use its id and do not raise another. Read it back with
`get_entity("agent_request", <request_id>)` (status `pending`). Never answer
your own task. If the create is refused, report the item with
`person_task: not_created` and the refusal: the report is then its only
record.

**A person's decision recorded on another document.** A bill or other
document states the person's answer in its description or notes: who
answered, when, the choice and their words. Read it there; the task behind it
was raised by another agent and is not yours to read. An older document may
quote only a short task id (`64e2dd33`): that is not a task id and cannot be
read. Either way the decision is already applied to the document: judge it as
it stands (posted, its accounts and amounts), do not try to read the task,
and do not list it under `gaps`.

**A session given answered tasks** (`answered_tasks: [<request ids>]` in the
first message) starts with them, after step 0: `get_entity("agent_request",
<id>)`. `status` `completed`: the answer is `response_data.selected_option`
(or `resolution_id`) and `response_data.notes`. The answer is not tied to a
version of the records, so read the subject's current rows again before
acting. Act on it through the normal steps of this skill, then link the
outcome: `submit(object_type="agent_request", operation="update", data=JSON.stringify({"request_id": <id>,
"result_type": "<record type>", "result_id": "<id>"}),
idempotency_key="<prefix>task-<id>-result")`. Not completed: leave it and
report it as still waiting.

Every task is echoed in the result block as one line:
`person_task: <request_id> <kind> <document or transaction> - <what the person decides>`

**Write every task for someone who is not an accountant** (the
`arfiti-account-choice` skill, "When there is no answer"): say what happened
and what you need decided in everyday words, offer plain choices, and put
check codes, account numbers and what you will do with each choice in
`details` and the options' `note` for the accountant who reads it later.

## A paused built-in close saga (`saga_id` in the first message)

While the built-in saga still runs for some organisations, a session may be
asked to clear what pauses it.

1. `get_entity("saga", <saga_id>, include_related=true)`: `checkpoint_data`
   (period, `pause_reasons`, `failed_phase_numbers`, retry log) and its
   `phases`. Confirm it is this entity's `month_end_close`.
2. From the failed phase's output and the pause reason, name the blocking
   finding and confirm it with the step 2 calls for that check. The check
   rows themselves (`period_close_checks`) are not readable (gap); if the
   phase output does not name the check, report that and stop.
3. Resolve it as step 4 says.
4. Retry: `submit(object_type="saga", operation="retry_phase", data=JSON.stringify({"saga_id": "<uuid>",
   "phase_number": N}), validate_only=true)`, then for real with the key
   `<prefix>retry-<N>`. Read back the saga: the phase is running or complete.
   The same finding again: report it; do not loop.
5. Never cancel the saga, edit its state or close the period around it.

## Result

```
PERIOD_CLOSE_RESULT
status: closed | close_pending_approval | ready_to_close | blocked | checked | asked | already_closed | retried | wrong_scope
organization_id: <id>   legal_entity_id: <id>   period: <period_name> <start>..<end>   mode: <check|close>
rules: <each rule used: check -> blocking|advisory, the rule's words>
check: <group.code> <pass|fail|not_checked> <blocking|advisory> | <evidence: ids, counts, amounts> | <REACHABLE|PARTIAL|SAGA-ONLY>
fixed: <operation, ids, workflow id>
handed_off: <helper, brief, result>
for_other_agents: <agent: items, handoff_id when handed over>
person_task: <request_id> <kind> <subject> - <what the person decides>
close: <workflow id, lane, outcome, or "not attempted: why">
gaps: <what the tools could not show or do>
```

`ready_to_close` is `mode: check` with nothing blocking open; `checked` is
`mode: check` with blocking findings.
