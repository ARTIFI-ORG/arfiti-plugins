---
name: arfiti-reconciliation
description: Reconcile one legal entity's open payments (bank payments, card expenses, refunds) against its open bills and invoices in Arfiti through the MCP tools. Reads every document and its card purchase, uses history, dates, references and original-currency amounts as evidence, matches one-to-one, many-to-one and one-to-many, applies each match through submit with a row-level read-back, and turns every item it cannot settle into a person task. Use for every reconciliation session.
---

> **Without a roster (Cowork, Claude Code).** Where this skill hands work to the
> master-data or configuration agent, no such agent is available: follow the
> `arfiti-master-data` or `arfiti-configuration` skill in this plugin yourself, with
> the same brief, and come back here with its result block. Step 0 (confirm the
> organisation) still applies: your own sign-in decides which organisation you are in.

# Reconcile payments to invoices

Background: `get_guidance` on reconciliation ("Manual Matching a Held Card
Purchase", "Reviewed manual allocations", "Evidence tasks for third-party
settlement", "Explicit receipt/refund offset") and card management. This
skill has no fixed pass list: it gives you the evidence on each document and
asks you to decide from it.

Tools: `query`, `get_entity`, `get_guidance`, `get_organization` (read: `get_info`),
`read_attachment`, `generate_report`, `get_submissions`, `submit`.

## What you reconcile

**Vendor and customer scopes: open payments against open invoices.** A payment
is anything that settles a document: `AP_PAYMENT`, `AP_PREPAYMENT`,
`AP_REFUND`, `CARD_EXPENSE` (vendor); `AR_PAYMENT`, `AR_PREPAYMENT`,
`AR_REFUND` (customer). Invoices: `AP_INVOICE` (vendor); `AR_INVOICE`,
`AR_CREDIT_MEMO` (customer).

**Card-paid bills are part of the vendor scope.** When a card is charged, the
charge is booked straight away as a `CARD_EXPENSE` (debit expense, credit the
card account). The vendor's invoice arrives later and is posted as an
`AP_INVOICE` (debit expense, credit AP). Until the two are linked the expense
is counted twice and AP shows a debt that the card already paid. Linking them
is a normal `reconciliation.match` with the `CARD_EXPENSE` as the payment; the
gateway then posts a `CARD_EXPENSE_RECLASS` journal (debit AP, credit the
card's expense, plus any FX difference) so the expense counts once.

Every card charge belongs to a **card purchase**: the workspace that groups a
charge's legs (`purchase`, `refund`, `reversal`, `chargeback`, `fee`,
`interest`). A purchase can hold several capture legs of one buy (a hold and
its remainder, split captures). The gateway checks card-paid settlements
against the purchase, so you read the purchase too (step 3).

**Card scope is something else: feed lines against their postings.** A card
transaction from the provider feed (`card_transaction`, `recon_status =
"pending_recon"`) is tied to the `CARD_EXPENSE` transaction that booked it
(`card_statement_line.match`). That says "this ledger posting is that card
charge"; it settles no bill. A card expense can be tied to its feed line and
still be waiting for its bill, or the other way round.

Bank statement lines are not in scope (the bank agent's work).

## Rules that never bend

1. **Match when the evidence identifies one answer, and state the evidence.**
   There is no fixed list of passes and no rule that amounts must be exact.
   An answer is a set of payments and invoices with amounts. Apply it when,
   after reading everything in steps 3 and 4, it is the only answer the
   evidence supports, from both sides: no other open document fits that
   payment as well, and no other open payment fits that invoice as well.
   Write the evidence into `notes` and the report.
2. **Read all data before deciding** (step 3): the transaction, its lines,
   metadata, attachments, references, the card purchase and every leg, the
   card transaction's provider fields and receipts, original-currency
   amounts. A decision made on amount and party alone is not a decision.
3. **Dates are evidence, never the only evidence.** A charge the day after
   the bill date, or inside the invoice's service period, supports that
   bill over a charge a month later. Equal amounts plus closeness in time
   alone, with nothing else, is weak when another candidate also fits;
   combine it with the other evidence in step 4.
4. **History shows the pattern.** How this vendor's earlier bills were paid
   (one charge or a hold plus remainder, how many days after the bill,
   which card, which currency) is evidence for the next one.
5. **One stop only.** If, after all the evidence, two answers remain equally
   supported, or the gateway refuses and you cannot see why, do not choose:
   that item becomes a task for a person ("Tasks for a person"):
   `ambiguous_match` with one option per answer, or `system_refusal`. Nothing
   open is left without either a match or a task.
6. **Every write goes through `submit`, followed by a read-back** (step 8). A
   success response whose rows did not change is a failure: stop applying
   and report it.
7. **Policy is the organisation's.** Write-offs, the application date and
   any client rule come from configuration or rules (step 1). Missing policy
   is a question, not a default you invent.
8. **Never convert at a rate you chose.** Cross-currency amounts come from the
   records (step 5d). Say which record gave each amount.
9. **Scope.** One legal entity per session; every call carries its
   `legal_entity_id`. Do not use `submit("reconciliation", "auto_match", ...)`:
   it runs a server matcher, not this procedure.

## Inputs (first message)

`organization_id`, `legal_entity_id`, scopes (`vendor`, `customer`, `card`;
none given: all three), and the period (`period_start`,
`period_end`, or `all_open`). The period bounds payments only; open invoices
of any date are candidates. Optional `payment_ids` or `invoice_ids`: when
given, start from those (all open documents of the same party are still
candidates). Optional `answered_tasks: [<request ids>]`: tasks an earlier
session raised that a person has answered ("Tasks for a person").

## Step 0: confirm the organisation and legal entity (before anything else)

1. `get_organization(action="get_info")`. Its `organization_id` must equal the
   `organization_id` in the first message. The organisation comes from the MCP
   connection (`?org=` on the agent's server URL), not from anything you pass;
   the signed-in user belongs to several organisations, so this check is the
   only proof of where your writes will land.
2. `query("legal_entity", filters={"id": <legal_entity_id>})` must return
   exactly that entity, and it must be active.
3. Either check fails, or the first message names no organisation: write
   nothing, end with the result block with `status: wrong_scope` and the ids
   you saw.

## Open questions come first (after step 0)

A document a person has been asked about is theirs until they answer. Right
after step 0, before any other step raises a task or applies a match, list the
open review tasks once and reuse the list for the whole session (add each task
you raise to it):
`query("agent_request", filters={"request_type": "verification", "status": "pending"})`
and again with `"status": "in_progress"`; keep those whose
`request_data.action` is `agent_review` and whose `legal_entity_id` is this
entity. For each, note its subject (type and id) and
every document number its `title`, `question` and `details` name
(`RCV…`, `ARR…`, `INV…`, `BILL…`, `CARD…`, a transaction id). You read
the tasks your agent raised in any session and those assigned to its role; a
task you cannot read cannot stop you, so say under `gaps` that the list may be
partial when it is empty but the records hint at a person's question.

A match touches a task when any of its documents (the payment, the refund,
each invoice or bill, the card purchase) is that task's subject (same type
and id) or is named in its text. Such a match is not applied, whatever the evidence: the task asks a
person exactly this kind of decision. List it under `person_task` with the
open task's id ("waiting for <request_id>"), not as `unmatched`, and raise
nothing new for it. A session given that task in `answered_tasks` acts on the
answer instead (below).

**One case, one open task.** Before raising a task, look in the same list for
an open task on the same case: the same subject, or a subject or document
named in the other's text, or the same party and amount. If there is one, do
not raise another:

- New facts a person needs for the same decision: raise one follow-up on it,
  `"parent_request_id": "<open task id>"` in the create (three rounds at most;
  a refusal for the limit means report it, not raise a fresh task).
- Nothing new: report the item with the open task's id.

A task that would ask a different decision about the same documents waits
for the open one: say so in the report (`gaps`), not in a second task. If you
find you already acted against an open task (a match you made before reading
it), do not undo it yourself and do not raise a separate "should I undo"
task: raise one follow-up on the open task that says what you did, with the
options to keep or undo it.

## Step 1: configuration and rules

`query("agent_definition", filters={"agent_type": "reconciliation_agent"})`,
then `get_entity("agent_definition", <id>)`, for one thing only: the
free-text `managed_agent_rules` key is the client's rules. A `client_rules:`
block in the first message adds rules for this session (an operator may
supply them for a test). Rules never bypass the gateway.

Every other `config` key is a product default, the same for every organisation and chosen by no client: the tolerance keys
(`amount_tolerance_*`, `approx_tolerance_*`, `amount_group_tolerance_*`,
`date_range_days`, `group_max_days_*`), the small-charge write-off figure,
`scopes` and `max_items_per_run`. Not the client's policy; not read. A match
is decided by identity evidence (references, the party, the documents), never
by an amount or date band. How wide you search is your own working choice;
report it under `config_used` as `search window: skill's own - <what you
searched>`. An amount difference is applied only as the records and rules
allow (the write-off below); otherwise it stays open and is reported.

**Application date.** The gateway requires `application_effective_date`
(YYYY-MM-DD) for a simple cash application (an `AP_PAYMENT` or `AR_PAYMENT`
whose currency, the invoice's currency and the entity's functional currency
are all the same) and refuses a missing one. Every other pair (card expenses,
refunds, prepayments, any foreign currency) uses the native allocation path,
which refuses the field: do not send it there. Never infer the date from
document dates (`GUIDE_RECONCILIATION.md`, "Explicit application dates").
Take it from the client's rules; a rule may name a field (for example "the
payment's own date"). If no rule gives it, do not stop and do not ask in the
session: raise one `question` task for the whole session ("Tasks for a
person"), `title`: "Which date to record payments on", subject the first
such payment, and list in its details every match that waits on it (payment,
invoice, amount). Ask it for someone who is not an accountant: "When a
payment settles a bill, which date should the books show for it?", with the
choices "The day the payment was made", "The bill's date" and "The day it is
matched", and what each means for these matches in the option's note. Go on
with every match that does not need the date (cards, refunds, foreign
currency) and report the waiting ones as `person_task`, not as `unmatched`.
When the answer arrives, apply the waiting matches with it; the answer is a
standing instruction, so propose it as a rule for your agent as
`arfiti-working-with-people` describes, and it is not asked again. Never
retry a refusal with a date you chose.

**Write-off.** Read the entity's limit:
`query("config_setting", filters={"config_key": "reconciliation.write_off_limit",
"legal_entity_id": X})` (`config_value`; with no active entity row, the
organisation default with `"legal_entity_id": None`). No limit: the gateway
refuses every write-off, so none is sent. Within the limit, write off only
what a client rule allows (the rule says which residues qualify). A
write-off is part of the match call for a payment you have identified and
applied (`write_off_amount` beside the `applications`); it never stands in
for a payment that exists in the records. Otherwise a difference stays open
on the document and you say so. A card purchase application (`purchase_id`)
refuses a write-off in the same call; apply the purchase, and report the
residue.

**Card purchase settlement is the default.** Settling a bill against a card
purchase posts the reclass that moves the charge out of its provisional
account; do it whenever the evidence supports the match. Only a client rule
changes that (for example "report card matches, do not settle them"): then
report each match with its evidence and apply none.

## The client's stored rules

Read them in every session, right after the rules step above and before any
decision:

`query("agent_rules", filters={"agent_type": "reconciliation_agent", "legal_entity_id": X})`

The answer's `prompt_block` is the client's rules for this kind of work,
already wrapped in `<client_rules>`: the organisation's and the entity's, the
ones for all agents and the ones for this role. Read it as the client's
instructions on how they want the work done. On a conflict the more specific
rule set applies (entity over organisation, this role over all). Empty
`results`: the client has stored no rules. A rule set with
`status: "invalid"`: stop and raise a `system_refusal` task; do not work
without the client's rules. If the call itself is refused or unknown to the
server, say so under `gaps` and go on with the other sources.

These stored rules, a `managed_agent_rules` key in an agent definition and a
`client_rules:` block in the first message all count as client rules; where
they disagree, the stored rules apply and you report the disagreement. Client
rules guide your choices. They never override the system's controls: a write
the gateway refuses stays refused.

## Step 2: load open items

Page through every list with `limit`/`offset` until done.

- Payments: `query("transaction", filters={"legal_entity_id": X,
  "transaction_type": [<payment types of the scope>], "status": "posted",
  "recon_status": null})` and again with `"recon_status": "partial"` (a list
  filter cannot include null). Keep those dated in the period.
- Invoices: `query("transaction", filters={"legal_entity_id": X,
  "transaction_type": [<invoice types>], "status": ["posted", "partial"]})`.
  `amount_due` is not filterable: keep rows with `amount_due` null or above
  zero yourself, and drop `recon_status = "dismissed"`.
- Card purchases (vendor scope): `query("card_purchase",
  filters={"legal_entity_id": X, "settlement_state": "open"})` and again with
  `"partial"` and `"review"`.
- Group everything by party (`vendor_id` / `customer_id`). A card expense
  without a vendor whose card purchase has one belongs to that vendor: the
  gateway settles it under the purchase's vendor. Any other payment
  without a party: read it (step 3); if its documents name the party, hand it
  to the master-data agent to confirm the party; otherwise raise a `question`
  task.
- Use `amount_due` / `amount_paid` as the paid signal, never status alone.
  Skip any row with `reversed_by_id` set.

## Step 3: read every document

For each party with open items on both sides, read before you compare.

**Every transaction** (payment and invoice): `get_entity("transaction", id)`:
`transaction_date`, `due_date`, `amount`, `amount_due`, `amount_paid`,
`currency`, `reference_number`, `description`, `metadata` (external ids,
provider and connector references), `lines` (descriptions, service periods,
quantities), `gl_lines`, `reversal_of_id`.

**Invoice documents**: `query("attachment", filters={"legal_entity_id": X,
"transaction_id": <id>, "is_deleted": false})`, then
`read_attachment(storage_url, content_type)` for the invoice. Look for: the
invoice and order numbers, the service period, "paid" stamps, the payment
method and the card's last four digits, the date it was charged, amounts in
another currency, receipt numbers, and the vendor's account or customer id.
If the read is refused or fails, note it under `gaps` with the refusal and go
on with the other evidence; an unreadable document is not a reason to stop
or to ask.

**Card expenses**: find the card purchase that holds it. For the party's
purchases (`query("card_purchase", filters={"legal_entity_id": X,
"vendor_id": V})`, then `get_entity("card_purchase", id)` for each) read:
- `version` (needed to write), `identity_state`, `provider_state`,
  `posting_state`, `settlement_state`, `net_amount`, `currency_code`,
  `reference_kind`, `purchase_reference`;
- `source_legs`: each leg's `id` (the card transaction), `role`,
  `transaction_date`, `amount`, `currency`, `original_amount` and
  `original_currency` (the merchant's charge in its own currency, for
  example USD on a EUR card), `external_transaction_id`,
  `posted_transaction_id` (the `CARD_EXPENSE` id), `receipt_status`,
  `receipt_evidence`;
- `bills`: documents already linked or applied (`status = "document_link"`
  means a reviewed link exists; `is_applied`, `applied_amount`,
  `source_applied_amount`).

Then `get_entity("card_transaction", <leg id>)` for the provider's view:
`merchant_name`, `merchant_descriptor`, `merchant_id`, `authorization_code`,
`transaction_type`, `transaction_date`, `posted_date`, `settlement_date`,
`amount`/`currency_code`, `billing_amount`/`billing_currency`, `fx_rate`,
`metadata` (the provider payload), and its `receipts`.

A card expense with no purchase, or a purchase in `identity_state`
`unresolved` / `review` or `provider_state` not `booked`, cannot be settled
yet (the gateway refuses it): raise a `question` task saying what is
unresolved.

**Bank payments**: `metadata` and `description` carry the counterparty name,
IBAN and the remittance text the bank line had; read them for invoice
numbers.

## Step 4: history and evidence

**History for the party.** `query("transaction", filters={"legal_entity_id":
X, "vendor_id": V, "transaction_type": "AP_INVOICE", "status": "paid"})`
(or `customer_id` and AR types), most recent first, up to 12. For each:
`query("reconciliation_item", filters={"legal_entity_id": X,
"target_transaction_id": <bill id>, "is_applied": true})` gives which
payments settled it and with what amounts; read those payments. Note:
- how many payments settled one bill, and their shape (one charge; a fixed
  hold such as 5.00 plus a remainder; several small charges summing to the
  bill);
- the days between bill date and charge, and whether the charge came before
  or after the bill;
- the currency pair (USD bill, EUR card) and which amounts were used;
- `variance_journal_entry_id` on card items (the reclass journal).

**Evidence, strongest first.** Use all that you have.
1. A reference that both sides carry: the invoice or order number in the
   payment's text or metadata; the same provider purchase id or receipt
   number; a reviewed link already in the purchase's `bills`.
2. The invoice says how and when it was paid (card last four, charge date,
   "paid" with an amount) and one payment matches that.
3. Amounts: the payment equals the open amount; or payments sum to it; or the
   card leg's `original_amount` in the invoice currency equals it.
4. The party's pattern from history (shape, lag, card, currency).
5. Dates: the charge falls on or just after the bill date, or inside its
   service period, and the other candidate does not.

## Step 5: decide

For each party, write down the candidate answers and the evidence for each.

**a. One payment, one invoice.** Usual case. When the payment and the
invoice are for the same party, the same currency and exactly the same
amount, and each is the only open item of its kind for that party in the
scope, that is the answer: apply it. A reference that does not carry the
invoice number, a generic description, a party with no paid history or an
invoice document you could not read do not block it; name them in the result
and report the match as `judged`. A posted payment is a fact of the ledger:
whether it is "real" is not a question you ask.

**b. Several payments, one invoice.** Any number of payments (two, or
thirty) may settle one invoice: split card captures, a hold plus a remainder,
instalments. The answer is the set whose amounts add up to what is applied
(the open amount, or less if the rest stays open), and every payment in the
set must be supported by evidence, not by the sum alone. When several sets
add up to the same total (for example three identical 5.00 holds and one
invoice of 5.76), choose between them with the other evidence (same-day or
next-day pairing of a hold and its remainder, the same authorization code or
provider reference, the vendor's pattern). Still equal: an
`ambiguous_match` task. A one-cent card leg (a purchase split between two
funding sources) is a payment in the set like any other and is matched, not
written off.

**c. One payment, several invoices.** A payment may settle many invoices of
the same party (a remittance listing them, a payment equal to their sum).
Same test: the set must be the one the evidence supports.

**d. Different currencies.** The invoice is in one currency and the payment
in another (a USD bill paid by a EUR card). The gateway needs the applied
amount in the invoice's currency (`applied_amount`) and, for the payment
side, `source_applied_amount` in the payment's currency. Take them from the
records, in this order, and say which you used:
1. The card leg's `original_amount` / `original_currency`: when they equal the
   invoice's open amount and currency, the card charge paid it. For a single
   card leg you may omit `source_applied_amount`; the gateway derives it
   from the recorded original amount.
2. The whole charge pays the whole invoice: when the evidence identifies this
   charge as the payment of this invoice in full and nothing else, the
   amounts are the invoice's open amount and the charge's full amount. No
   rate is involved; the gateway posts the FX difference itself.
3. The card transaction's `billing_amount` / `billing_currency` or the
   invoice text stating the amount charged in the other currency.
4. Otherwise there is no recorded basis: a `question` task (what is missing).

**e. Partial.** A payment smaller than the open amount, clearly for that
invoice, is applied in full; the rest stays open. A payment larger than the
invoice is applied up to the open amount; the rest stays unapplied on the
payment.

**f. Refunds.** A customer refund that exactly offsets a receipt uses the
refund form in step 6. A vendor refund against a charge has no offset
operation: a `question` task.

**When nothing fits** (a payment with no open document, an invoice with no
payment): leave it open; its counterpart may not have arrived. An invoice
or bill that is not yet due and has no payment is not a question and gets
no task: nothing is wrong and a person has nothing to decide. List it under
`unmatched` with its due date. When it is
older than the party's usual lag in history, raise a `question` task saying
what is missing; otherwise report it under `unmatched` with the reason.

**Differences.** If the evidence identifies the answer but the amounts differ
by a small residue (rounding, an FX cent), apply what the records support and
leave the residue open, unless a client rule says write it off within the
limit (step 1). A residue that is itself a charge in the records (a fee
charged as its own card or bank movement) is a payment to match, not a
residue.

## Step 6: apply

`get_submissions(action="schema", object_type="reconciliation",
operation="match")` and `get_submissions(action="schema",
object_type="card_purchase", operation="manage")` once each.

**Non-card payments** (one call per payment; several invoices go in one
`applications` list):

```
submit("reconciliation", "match", {
  "legal_entity_id": X,
  "scope": "ap" | "ar",
  "source_transaction_id": <payment id>,
  "applications": [{"target_transaction_id": <invoice id>, "applied_amount": <invoice currency>,
                    "source_applied_amount": <payment currency, only when currencies differ>}],
  "application_effective_date": "YYYY-MM-DD",   // only for simple cash applications (step 1)
  "notes": "<evidence in one line>"
}, idempotency_key="recon-<legal_entity_id>-<payment id>-<invoice ids joined by _>")
```

Several payments to one invoice: one call per payment, each with its own
`applied_amount`, in any order; the invoice's `amount_due` falls with each.

**One run for the whole session.** Your matches are recorded as one
reconciliation run, shown on the runs page as agent activity and linked to
this session:

- An AR refund offset (`refund_transaction_id`) is a match of the `ar` run
  like any other: it opens it or joins it with the same fields.
- The **first** non-card payment match of the session adds
  `"open_run": true` and
  `"run_reference": {"runtime": "managed_agents", "session_id": "<managed_session_id from the kickoff>"}`.
  The response's `reconciliation_run_id` is your run; note it.
- **Every later** non-card payment match (same entity and scope) adds
  `"reconciliation_run_id": <your run>` instead. AP and AR are separate runs:
  open one per scope you match in.
- A refusal saying the run is closed or its session has ended: submit the
  same match once more with `"open_run": true` (and `run_reference`) in place
  of `reconciliation_run_id`, under the same idempotency key plus `-r`.
- After your last match in a scope, close the run:
  `submit("reconciliation", "finalize", {"legal_entity_id": X, "scope": "ap" | "ar",
  "reconciliation_run_id": <your run>})`.
- Card purchase matches (`purchase_id`) take none of these fields; they keep
  their own run.
- No `managed_session_id` in the kickoff: use `open_run` and
  `reconciliation_run_id` without `run_reference`, and say so under `gaps`.

**Card expenses** settle through the card purchase. Two steps, both through
the gateway (`GUIDE_RECONCILIATION.md`, "Manual Matching a Held Card
Purchase"):

1. **Link the bill to the purchase** (records your decision and evidence; no
   ledger write):
   ```
   submit("card_purchase", "manage", {
     "legal_entity_id": X, "purchase_id": <purchase id>, "expected_version": <version>,
     "action": "link_existing_bill", "bill_transaction_id": <bill id>,
     "reason": "<the evidence in one or two sentences>"
   }, idempotency_key="recon-<legal_entity_id>-link-<purchase id>-<bill id>")
   ```
   Do this for every purchase you apply, also when the gateway might accept
   the match without it: the link is what lets you settle when the
   gateway's own identity check finds two equal candidates (two identical
   monthly charges, several holds), and it records why. Skip it only when
   the purchase's `bills` already shows a `document_link` to that bill.
   The bill's vendor must be the purchase's vendor. When the card paid a
   bill from a different vendor (a merchant of record, a booking site), use
   `"action": "request_settlement_review"` with `relationship_reference`
   (the reference both documents carry) and `attachment_ids` (the bill's
   attachments) instead: it creates a review task for a person, and the
   approval posts the settlement. Report it as `pending_approval`.
2. **Apply**, after the link's read-back:
   - One purchase with one purchase leg, or several purchase legs of one
     purchase in the same currency (a hold and its capture), settling one
     bill:
     ```
     submit("reconciliation", "match", {
       "legal_entity_id": X, "scope": "ap",
       "source_transaction_id": <the CARD_EXPENSE id of a purchase leg>,
       "purchase_id": <purchase id>, "purchase_version": <version>,
       "applications": [{"target_transaction_id": <bill id>, "applied_amount": <bill currency>}],
       "notes": "<evidence>"
     }, idempotency_key="recon-<legal_entity_id>-purchase-<purchase id>-<bill id>")
     ```
     The gateway sizes each leg itself and applies them in one transaction.
     One bill per call; no write-off in this call. Several legs in a
     currency other than the bill's are refused here
     (`cross_currency_split_requires_review`); apply each leg instead as
     its own call without `purchase_id`, with both amounts from step 5d
     (each leg's `original_amount`). No recorded basis per leg: a
     `question` task.
   - Several separate purchases settling one bill (CityBee-style charges
     that are each their own purchase): link each purchase (step 1), then
     one call per card expense without `purchase_id`, `applied_amount` =
     that charge's amount in the bill currency (plus `source_applied_amount`
     when currencies differ, step 5d).
   - One purchase settling several bills: link each bill, then one call with
     the card expense as source and one `applications` entry per bill.
   - Cross-currency, single leg: `applied_amount` in the bill currency;
     `source_applied_amount` as step 5d says (omit it for the
     original-amount case).

**AR refund offset**: `"refund_transaction_id": <AR_REFUND id>` with no
`applications`, only when refund and receipt are the same customer, currency
and absolute amount (`GUIDE_RECONCILIATION.md`, "Explicit receipt/refund
offset").

**Card scope**: a feed line with `recon_status = "pending_recon"` whose
`CARD_EXPENSE` the evidence identifies (same card, amount, date and merchant,
or its `posted_transaction_id`):
`submit("card_statement_line", "match", {"card_transaction_id": C,
"gl_transaction_id": G, "legal_entity_id": X})`.

**Refusals and approvals** follow "Refusals and unknown outcomes". A pending
approval already sits with a person: record the workflow id and do not apply
anything that depends on it (a match after a link that waits for approval).
A stale `version` means re-read the purchase and submit once more with the
new version under the key plus `-v<version>`. A refusal naming the purchase's
identity (`competing_purchase_candidates`, `competing_bill_candidates`,
`purchase_mismatch`) after you linked the bill means the link did not land:
read the purchase's `bills` back before anything else.

## Step 7: hand off to the master-data or configuration agent

Either roster member may help; each sees none of this conversation, so the
brief carries everything: `organization_id`, `legal_entity_id`, the problem
in one sentence, the evidence (ids, the text you read, any refusal verbatim
with its workflow id), the goal, and an idempotency-key prefix
(`<your prefix>-md-` or `<your prefix>-config-`).

- **Master data** (returns `MASTER_DATA_RESULT`): a payment or bill on the
  wrong or no party, a party found twice, bank details that differ.
- **Configuration** (returns `CONFIGURATION_RESULT`): a setup gap that blocks
  a write: no posting profile, an inactive account, no fiscal period, no
  default FX profile, a control account that is not controlled.

Hand off a cause a refusal names in its `message` or `failure_reason`, or a
gap you can see in the records, or ask the configuration agent to check
named preconditions read-only and fix a definite gap. Never hand off "make
this operation pass". Continue only after the helper reports `done` (or
`found` / `created`) and its read-back shows the gap closed, then submit
again with a new key. One level only.

## Step 8: read back after every write

Before writing, note for every row involved `amount`, `amount_paid`,
`amount_due`, `recon_status`, and the purchase's `version` and `bills`.

After a link: `get_entity("card_purchase", id)`: `bills` has the bill with
`status = "document_link"`.

After a match:
1. `get_entity("transaction", <invoice id>)`: `amount_paid` rose and
   `amount_due` fell by the applied amount; `recon_status` is `reconciled` or
   `partial`.
2. `get_entity("transaction", <payment id>)` for every payment applied:
   `recon_status` is `reconciled` or `partial`.
3. `query("reconciliation_item", filters={"legal_entity_id": X,
   "source_transaction_id": <payment id>, "is_applied": true})` shows an item
   per application.
4. Card expense to bill: each item has `variance_journal_entry_id`, and
   `get_entity("transaction", <that id>)` is a posted `CARD_EXPENSE_RECLASS`.
   The gateway skips the reclass in some cases and still reports success; a
   missing reclass means the expense is still counted twice.
5. Card purchase: `get_entity("card_purchase", id)`: `settlement_state` is
   `settled` (or `partial`), `bills` shows the application.

Any expected change missing: record `SUCCESS_WITHOUT_EFFECT` with the submit
response and the rows, stop applying further matches, and report.

## Refusals and unknown outcomes

Every `submit` answer is one of five kinds. Read which before doing anything
else (`GUIDE_WORKFLOW_MANAGEMENT.md`, "Failed execution"):

- **Executed.** Read the rows back (the read-back step).
- **Pending approval** (`status: "pending"`, a `workflow_id`, no record id):
  the organisation's approval lane holds it. Record the workflow id; do
  nothing that depends on it in this session. Then say that you wait for
  it, once per workflow ("A decision comes back to this session"):
  `submit("managed_agent_run", "wait", {"session_id": "<managed_session_id>",
  "workflow_id": "<workflow_id>", "waiting_for": "<one line: what continues
  once this is decided>"})`.
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
  bank and card refusals arrive this way today. First read the affected
  rows. Changed: it took effect; carry on with the read-back. Unchanged: act
  on `failure_reason` as for a definite refusal, and only then submit again,
  with a new key. Submitting again under the same key only replays the
  unknown answer. No `failure_reason` and the rows unchanged: raise a
  `system_refusal` task with the workflow id.

A refusal for a missing permission, or because the step needs a person of a
certain level, is handed over as the work itself, never as a request for
access (`arfiti-working-with-people`, "When you are not allowed to do
something"): for a card link, "Link bill <number> to its card charge", with
the bill, the purchase and the evidence that they belong together.

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

Before raising one, check "Open questions come first (after step 0)": one case has one open
task, and a document a person was asked about is not matched past them.

Nothing uploaded or received is skipped. Every item this session does not
post or settle and that needs a person's decision (so not an invoice that is
simply not due yet) ends as a real task for a person, raised through the gateway
(`GUIDE_AGENT_REQUESTS.md`, "Review tasks any agent can raise"), or as a line
pointing at the open task that already asks it (one case, one open task). Ask in a
task, not in the session: the session ends and a later session continues
from the answer.

```
submit("agent_request", "create", {
  "request_type": "verification", "legal_entity_id": X,
  "request_data": {
    "action": "agent_review",
    "kind": "question" | "document_not_postable" | "ambiguous_match" | "system_refusal",
    "question": "<10 to 2,000 characters: the one decision needed>",      // not on system_refusal
    "title": "<what you need from the person, 3 to 80 characters, one line, e.g. Need expense account, Review bank line, Choose the matching bill>",
    "details": "<up to 4,000 characters: what you checked and what you concluded>",
    "subject": {"type": "transaction | card_purchase", "id": <id>, "label": "<number or name, up to 200 characters>"},
    "options": [{"id": "<lower_case_id>", "label": "<choice>", "note": "<what you will do>"}],  // up to 8; not on system_refusal
    "documents": [{"filename": "...", "storage_url": "...", "content_type": "..."}],         // up to 10
    "refusal": {"operation": "<object.operation>", "reason": "<message or failure_reason>", "workflow_id": "<id>"},  // system_refusal only
    "run_reference": {"runtime": "managed_agents", "session_id": "<managed_session_id from the kickoff>"}
  }
}, idempotency_key="recon-X-task-<kind>-<subject id>")
```

- `question`: a decision the records cannot settle. Give the options you see
  and what you will do with each.
- `document_not_postable`: a document that is not something this skill
  posts (a credit note, a bare receipt, an unreadable file). Needs
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
`submit("managed_agent_run", "wait", {"session_id": "<managed_session_id>",
"workflow_id": "<workflow_id>", "waiting_for": "<one line>"})`. Declare each
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

**A session given answered tasks** (`answered_tasks: [<request ids>]` in the
first message) starts with them, after step 0: `get_entity("agent_request",
<id>)`. `status` `completed`: the answer is `response_data.selected_option`
(or `resolution_id`) and `response_data.notes`. The answer is not tied to a
version of the records, so read the subject's current rows again before
acting. Act on it through the normal steps of this skill, then link the
outcome: `submit("agent_request", "update", {"request_id": <id>,
"result_type": "<record type>", "result_id": "<id>"},
idempotency_key="recon-X-task-<id>-result")`. Not completed: leave it and
report it as still waiting.

Every task is echoed in the result block as one line:
`person_task: <request_id> <kind> <subject> - <decision needed>`

## Step 9: report

Every open item you looked at ends in exactly one of: applied,
pending_approval, a task, or `unmatched` with a reason.

```
RECONCILIATION_RESULT
status: done | wrong_scope | stopped
organization_id: <id from get_organization>   legal_entity_id: <id>   scopes: <...>   period: <...>
payments_considered: <n>   invoices_considered: <n>   purchases_considered: <n>
applied: <n>
  - <payment id(s)> -> <invoice id(s)>, <amounts in each currency>, route (match | purchase | link+match),
    evidence: <one line>, reclass: <journal id or n/a>
pending_approval: <n>   (each: workflow id, what waits)
reconciliation_runs: <run id per scope, and whether you closed it>
person_task:
  - <request_id> <kind> <subject> - <the decision needed>   (one per task; not_created - <refusal>
    when the create was refused)
unmatched: <n>   (each: item, why no document or payment fits)
success_without_effect: <n> (each with submit response and rows)
questions_asked: <n> - <each in one line>
history_used: <per party: the pattern you read, in one line>
config_used: <rules and configuration values read>
gaps: <anything the MCP tools could not do that the evidence called for>
```
