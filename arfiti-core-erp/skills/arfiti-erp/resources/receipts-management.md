

## Receipt lifecycle correction (implementation; deployment pending)

The purchase projection now distinguishes attached evidence (`draft`, Ready to submit, employee action) from `processing` (Sent for review) and `review` (Being reviewed). Migration 639 refreshes the tenant and template views without modifying receipts, provider rows, or GL. It does not repair existing posting holds.

A pending-posting Bill result is counted as held and its reason is included in the run summary. It must not be reported as No attachments processed. For agent-bound workflow completion, current run authority is reloaded through the agent authority gate; authored agents still require their creator's current membership, while human submissions retain the human membership gate.

Recovery of the QA receipt requires confirming the exact stored refusal, absence of a workflow/transaction for its immutable candidate, and no active processing before reopening that candidate for one retry. Time elapsed or a missing workflow ID alone is not proof that retrying is safe.


> **Production verification note (2026-10-06):** Provider/card-feed status `posted` does not prove GL posting. Check the linked posted transaction and posting state separately. Attaching a receipt files evidence; explicit submission starts the bill pipeline, which can produce an AP bill and settlement accounting. The historical blanket statement below that the entire receipt lifecycle never touches GL is too broad; it applies to attachment itself. Current purchase workspace: `/transactions/card-purchases`.
>
> In QA, an upload-only purchase displayed Being reviewed before submission. A later submitted receipt was held with `pending_posting=true`, no workflow ID, and an incorrect No attachments processed summary. These remain open issues. A completed agent run is not proof of posting or settlement; inspect the document outcome and linked accounting records, and do not resubmit a pending-posting document blindly.


## Card purchase policy

Use the backend purchase workspace and shared matching decision; do not implement a competing card matcher in conversation. Preserve provider rows and show net purchase spend. Reference conflicts and competing candidates require review. A paid/settled item can still lack documentation; attach missing source evidence to the existing bill. Evidence review, waiver and grouping use `card_purchase.manage` with current version, evidence fingerprint and reason. Never infer write-off authority from matching tolerance.

Receipt follow-up belongs to the purchase obligation, with one owner and deduplicated reminder stages. Automation and delivery are report-only until the entity rollout settings are explicitly enabled. Statement coverage and opening/movement/closing balance controls must pass independently of agent match counts. August deletion/replay requires its own reviewed manifest and explicit authorization through transaction.delete; implementation permission does not authorize it.

Legacy payment-pass descriptions below apply to non-card AP/AR behavior. Card rows use the shared purchase policy and cannot use nearest-date refund pairing, fuzzy amount identity or adjusting-journal workarounds.

# Receipts Management

Receipts for corporate card charges: how they arrive, how their state is
tracked, and what you can and cannot do about them.

---

## The one rule

**A receipt documents a charge that is already posted. It never creates a
transaction and never touches the GL.**

The card feed posts the expense when the charge arrives. Receipt collection
happens afterwards and never blocks or reverses accounting. So
`receipt_status` is a documentation-compliance field, not an accounting one —
never reason about whether an expense is recognised by looking at it.

---

## Attaching is not submitting

**This is the single thing to get right.** Filing a document against a charge
and handing it to the bill pipeline are two separate operations:

```
attach_receipt   → the file is held on the charge     → receipt_status = 'uploaded'
submit_receipt   → the document is handed over        → receipt_status = 'processing'
```

An attach on its own does nothing else. No extraction starts, no bill is
posted, nobody is asked anything — the charge sits at `uploaded` until
something submits it. **A receipt you attach and do not submit is not
documented, and nothing will remind anyone**: the collector only emails
charges at `pending`/`requested`, so an unsubmitted draft drops out of the
chase ladder entirely. It shows on the page's **Needs attention** list, and
nowhere else. Never leave one behind.

Two steps, not one, on purpose: a partial set of photographs is never
processed halfway. Attach every page, then submit once.

So **every attach in this document is followed by a submit**, and yours must
be too.

---

## Two ways a receipt arrives

Both are normal. The same cardholder will use both in the same month.

### Path A — filed against a specific charge, then submitted

The employee opens **Card expenses** (`/transactions/card-expenses`), finds
their charge and uploads the file, then clicks **Send for review**; or Claude
calls `attach_receipt` and then `submit_receipt`. Because the charge was
picked, there is no matching problem.

```
attach  (page upload, or card_transaction.attach_receipt)
  → row in card_transaction_receipts, file in R2
  → receipt_status = 'uploaded'          ← a draft; nothing else happens

submit  ("Send for review", or card_transaction.submit_receipt)
  → receipt_status = 'processing'
  → ONE bill.upload event, carrying ONE document → bill_processor
  → the bill pipeline extracts, resolves the vendor (inherited from the
    charge if it already posted — see below) and VAT, posts an AP invoice
  → the settle tail applies that bill to this charge and posts CARD_EXPENSE_RECLASS
  → receipt_status = 'posted'      (a bill exists)
  → receipt_status = 'reconciled'  (that bill settled the charge in full)
```

**Don't resolve the vendor yourself when the charge already posted.** If the
charge this receipt names has already posted, the bill inherits ITS vendor
directly — the pipeline never runs its own vendor resolution or creates a
new vendor for this document. This matters because a receipt's own text can
name the charge's legal operator rather than its brand (e.g. card charge
"Esso", receipt text "Wonnegau Ost / M.Weber GmbH & Co KG") — trusting the
posted charge's vendor is what stops a duplicate vendor being created for
spend that already has one. A duplicate here would make settlement fail and
double-count the expense.

The run can end other ways, and the charge follows it:

| The run | The charge becomes |
|---|---|
| posted a bill | `posted` |
| …and that bill fully settled the charge | `reconciled` |
| needs a person (low confidence, or an approval step) | `in_review` |
| was declined by a person | `rejected` |
| was skipped, or errored | `rejected` |
| was a duplicate **and knows which bill already covers the charge** | `posted` |
| was a duplicate that knows no bill, or is waiting on another agent | unchanged |

There is **no separate verification step and no match grading.** The bill
pipeline's own extraction and confidence gate make the judgment. Nothing
computes "does this receipt match this charge" any more.

### Path B — emailed in

The employee forwards the receipt to the entity's `bills@` or `receipts@`
address — either works, because routing happens by what the document *is*,
not which mailbox it landed in. A merchant document (a real invoice, or a
till slip) always ends up as a bill; only an out-of-pocket employee
reimbursement (no merchant document, or per-diem/mileage) becomes an
expense report instead.

Once it is a document, `bill_processor` posts it as an AP invoice. What
happens to the matching card charge depends on whether this document
arrived carrying a link to one:

- **Linked** (Path A above fed the document in) — the bill settles that
  charge **immediately, at posting time**, through `reconciliation.match`
  (`scope='ap'`). This is always two postings: the application, plus a
  `CARD_EXPENSE_RECLASS` journal that reclasses the card's own expense line
  against the AP control the bill credited, dated on the later of the card and
  bill dates (a card paid before its invoice settles when the bill exists).
  Skip the reclass and the expense
  is counted twice and AP is never relieved — never write a settlement that
  applies a `CARD_EXPENSE` to a bill without it.
- **Unlinked** (the ordinary case — most `bills@` mail) — the bill posts,
  then the email-lane matcher (`bill_match_card_charge`) looks for the charge
  it covers: same entity and vendor, a posted unreconciled `CARD_EXPENSE`,
  functional amount within the org's `reconciliation.write_off_limit` (unset
  = exact amount only), charge date within `card_match_window_days` of the
  bill date. Exactly **one** candidate → the bill settles it immediately
  through the same settle tail as the linked case (which can still decline).
  **Two or more** → vendor + amount is a guess, and two similar dinners at
  the same restaurant must never auto-pair — the bill stays posted and
  **open**, the candidates are logged as a progress step, and NO human
  review is raised (2026-09-03 ruling, both lanes: the email-lane shell and
  its pipeline-stage twin). Settlement ambiguity is the reconciliation
  agent's job, not the bill processor's — its pre-authorisation netting
  pass resolves exactly this shape (a hold plus a later partial credit look
  like "two charges" until netted). **Zero** → the bill waits and the
  reconciliation agent applies the matching charge on its own schedule.

An unlinked document **never writes `receipt_status`** — the card row still
reads `pending` or `requested`. The charge is nonetheless fully documented,
and both the dashboard and the chase agent know it (see
[Derived statuses](#derived-values--read-time-only-never-written)).

**A till slip forwarded to the bill pipeline does not auto-post as a rule.**
It is correctly recognised as a bill, but its extraction confidence
(~0.55 — no invoice number, no date, no line items) usually sits below the
default 0.85 confidence threshold, so it lands in human review like any
other low-confidence document. Do not tell a user slips post automatically.

**The same purchase can arrive by two doors** — the receipt emailed in
*and* photographed and uploaded on the card-expenses page. Before posting,
the pipeline checks whether the document's linked card charge is already
reconciled; if so it does not post a second bill — the document is settled
as a duplicate, with the reason naming the charge it duplicates.

---

## What you can do

| Goal | How |
|------|-----|
| See a charge's receipt state | `get_entity("card_transaction", id=X)` → `receipt_status` |
| See **which** receipts are attached | `get_entity("card_transaction", id=X, include_related=true)` → `receipts` (file name, type, size, upload source) |
| List charges missing receipts | `query("card_transaction", filters={legal_entity_id: 9, receipt_status: "pending"})` |
| List charges holding an unsubmitted draft | `query("card_transaction", filters={legal_entity_id: 9, receipt_status: "uploaded"})` |
| See the chase requests | `query("agent_request", filters={request_type: "receipt", status: "pending"})` |
| See open no-receipt explanations | `query("agent_request", filters={request_type: "receipt_waiver", status: "pending"})` |
| Read one chase request | `get_entity("agent_request", id=X)` |

> **Schema discovery first.** Before any `submit()`, call
> `get_submissions(action='schema', object_type, operation)`. Field requirements are
> per-organization; never assume the fields shown in examples are complete.

### Filing a receipt yourself — both steps

When you hold the bytes (a file in your working directory, or one you pulled
from a shared drive), file it against the charge and then submit it:

```javascript
// 1. Get the bytes into R2 first. Route on WHO HOLDS THEM (never on size):
//      - already in the org's Drive folder → read_attachment(
//        storage_url="connector://<connector_id>/<file_id>",
//        content_type=<MIME type>) returns stored_url.
//        PULL ONLY — you cannot put a file into Drive to transfer it.
//      - on your disk AND you have egress (Claude Code) → curl to the
//        tokenized upload endpoint.
//      - anything else, and always in Cowork (egress is blocked) → generate
//        an upload link and hand it to the USER.
//    See document-attachments.md for the full table.
//
//    NOTE: an upload link generated with entity_type "CARD_TRANSACTION" files
//    the card receipt by itself — steps 1 and 2 collapse into one, and you
//    resume at step 3. Use this shape when the user is doing the uploading.

// 2. File it against the charge. The charge is now 'uploaded' — a draft.
submit("card_transaction", "attach_receipt", {
  card_transaction_id: 123,
  legal_entity_id: 9,
  file_name: "bolt-receipt.pdf",
  content_type: "application/pdf",
  source_url: "<the R2 reference from step 1>",
  business_purpose: "Client meeting travel"   // optional
})

// 3. SUBMIT IT. Without this the charge stays a draft and stays chased.
//    A submission hands over ONE document. Omit receipt_ids only when the
//    charge has exactly one receipt; with several, name the one that IS the
//    receipt for this charge.
submit("card_transaction", "submit_receipt", {
  card_transaction_id: 123,
  legal_entity_id: 9
  // receipt_ids: [456]   // required once the charge has more than one receipt
})
// → { receipt_status: "processing", agent_event_ids: [...] }
```

**Constraints, and why:**

- **`source_url`, never inline file data.** A receipt scan through a tool
  argument is a large lossy round trip; the upload endpoint already exists and
  stores to R2.
- **`connector://` is rejected here** — call `read_attachment` on it first
  (that stores the bytes and hands back `stored_url`), then pass that.
  Resolving connector refs in two places would duplicate the fetch and its
  permission checks.
- **Re-sending identical bytes is a no-op**, answered with the receipt that
  already holds them. Safe to retry.
- **A charge already settled through a bill is skipped**, with the reason
  said out loud — it needs no second document.
- **One submission, one document, at most one bill.** A card charge is one
  expense. Submitting used to emit a `bill.upload` per receipt, which made two
  photographs of one till slip into two independent bill runs and **two AP
  invoices for one charge**. Now a charge with several receipts and no
  `receipt_ids` is refused, with the ids listed so you can pick; naming two is
  an error. The receipts you do not send stay attached to the charge as
  evidence — nothing is lost by choosing one.

Uploading a generic *attachment* against `bank_card_transactions` still does
nothing: no agent listens for it. Use the operations above.

### When there is no receipt at all

The slip was lost, or the merchant issued none. Submit an **explanation
instead of a document** — same operation, different field:

```javascript
submit("card_transaction", "submit_receipt", {
  card_transaction_id: 123,
  legal_entity_id: 9,
  no_receipt_reason: "Parking meter issued no receipt."
})
// → { receipt_status: "in_review", agent_request_id: "..." }
```

This never becomes a bill — there is nothing to extract and no VAT to
reclaim. It opens a `receipt_waiver` request assigned to a human (the org
owner, or an admin), and the charge waits at `in_review` until they decide.

**A receipt and an explanation are mutually exclusive.** Sending both is
refused: a charge with a document attached needs no excuse.

### Deciding a no-receipt explanation (privileged roles only)

```javascript
submit("card_transaction", "review_receipt", {
  card_transaction_id: 123,
  legal_entity_id: 9,
  decision: "accept"            // or "reject"
  // note: "..."                // REQUIRED when decision is "reject"
})
```

- **accept** → `waived`, unless a bill is genuinely applied against this
  charge, in which case `posted`. It is `waived` in almost every real case.
- **reject** → `rejected`, and the note is what the employee has to act on,
  so it is mandatory.
- Only meaningful while the charge is at `in_review`; anything else is
  refused with the actual status named.

**Two different things put a charge at `in_review`, and they answer
differently.** A no-receipt explanation opens a review request, and both
decisions above apply to it. A *bill run* that routes the document to a person
— low confidence, an entity mismatch — writes the same status and opens no
request, because the bill's own review task is what a human answers there. On
that second kind:

- **reject** works, and is the way out: the charge returns to `rejected` so
  the employee can replace the document and submit again.
- **accept** is refused, with the reason said out loud. The pipeline bounced
  that document and recorded why; accepting here would leave the charge
  claiming documentation no bill supports. Resolve the bill's review task
  instead — it posts the document and reports back.

Before 2026-08-14 the second kind could not be answered at all and the charge
deadlocked: submit, attach, delete and review all refused it.

### Removing one you filed by mistake

```javascript
submit("card_transaction", "delete_receipt", {
  card_transaction_id: 123,
  receipt_id: 456,
  legal_entity_id: 9
})
```

All three ids must agree — a receipt is only removable through the charge it
documents. Three things to expect:

- **Delete is refused once anyone has acted on the submission.** It is
  allowed only while the charge is `uploaded`, `received`, `rejected`,
  `pending`, `requested` or `overdue`. On `processing`, `in_review`,
  `posted`, `reconciled`, `verified`, `waived` or `not_required` the answer
  is a refusal with the reason. **Evidence is immutable once someone has
  acted on it** — you may always add another document, never remove the one
  that was approved.
- **The status goes back to needing a receipt** — `requested` if a chase
  request is still open, otherwise `pending`.
- **The stored file is retained.** Only the link to the charge goes. An
  orphaned file is cheaper than deleting the only copy of something.

---

## Receipt status

### Stored values

These are the thirteen values the `receipt_status` column can hold. The last
two are legacy and no new charge will enter them.

| Status | Means | Delete? | Attach another? |
|--------|-------|---------|-----------------|
| `pending` | No receipt, nobody has asked | yes | yes |
| `requested` | The collector has emailed the cardholder once | yes | yes |
| `overdue` | Past the overdue threshold; final notice sent | yes | yes |
| `uploaded` | File(s) held, **not submitted** — a draft | **yes** | yes |
| `processing` | Submitted; the bill pipeline is working on it | no | no |
| `in_review` | A person must decide — unclear extraction, an approval step, or a no-receipt explanation | no | no |
| `posted` | A bill was posted from it | no | **yes** |
| `reconciled` | That bill settled the charge in full | no | **yes** |
| `rejected` | A person declined it — editable again so it can be replaced | **yes** | yes |
| `waived` | An explanation was submitted instead of a document, and accepted | no | yes |
| `not_required` | Documentation-free by rule (refund, fee, interest) | no | no |
| `received` | Legacy spelling of `uploaded`; nothing writes it any more | **yes** | yes |
| `verified` | Legacy terminal from the retired verify step; a receipt is attached and the org's workflow accepted it. No bill is implied | no | yes |

```
pending/requested/overdue ──attach──► uploaded ──submit──► processing
        ▲                                ▲                    │
        │                           delete│                    ├──► posted ──settle──► reconciled
        └────────────delete───────────────┘                    │
                                     rejected ◄───decline──────┤
                                          ▲                    └──► in_review ──approve──► posted
                                          └───────decline─────────────┘
                                                               └──► waived
                                                    (no receipt + accepted explanation)
```

**`posted` is terminal, not a spinner.** It means a bill exists but did not
fully settle this charge — a partial application, a cross-currency
difference, an approval-gated match. Do not describe it as "still working".

**`processing` can outlive its run.** If the run ended as a duplicate that
could not name a bill, or handed off to another agent that never came back,
the charge stays at `processing` with nothing running. Check whether the
posted transaction is reconciled before telling anyone the work is in
flight.

### Derived values — read time only, never written

A charge still stored as `pending`/`requested`/`overdue`/`uploaded`/
`received`/`processing` whose posted transaction is **fully reconciled** is
*displayed* as one of these. They are computed at read time and never
written to the column:

| Shown as | Meaning |
|----------|---------|
| `billed` | Applied against a vendor bill — the receipt lives on the bill |
| `refunded` | Netted against its own refund or reversal |
| `written_off` | Applied with no counterpart (fee or manual write-off) |
| `settled` | Reconciled, with no single classifying item |

`in_review` and `rejected` are deliberately **not** rescued this way: a
person owes a decision, or made one, and painting the row "Receipt posted"
would erase it from the only place it shows.

**Why it matters to you:** a charge reading `requested` or `processing` in
the database may already be fully documented. Do not tell a user they owe a
receipt based on the stored value alone — check whether the posted
transaction is reconciled.

**Mind the two id spaces.** `bank_card_transactions.id` is the charge;
`posted_transaction_id` is its GL entry in `transactions`. They are different
sequences and never interchangeable. In particular,
`posted_transaction_id IS NOT NULL` means "this charge is posted to the GL",
**not** "a bill exists" — every posted card charge has one.

---

## How chasing works

The Receipts Collector pipeline uses shared card purchase obligations. It selects
missing documentation owned by the employee; reminder/overdue stage claims prevent
duplicate sends. Targeted requests bypass age but not current evidence checks or
stage deduplication. Empty target lists are no-ops. Delivery requires the database
`card_purchases.delivery_enabled` and `delivery_start_date` settings.

Provider uncertainty retains the claim and blocks later escalation. Do not clear
or resend it through a task; an operator must verify provider evidence using the
receipt-reminder recovery procedure. Confirmed mail completes only the reminder,
not the underlying receipt requirement. Expense-report reminders are separately
scoped to entity/employee and retain per-report cooldown and age-based tone.

---

## Common scenarios

### "Do I owe a receipt for X?"

Read the charge.

- `posted`, `reconciled`, `waived`, `verified`, `not_required` → no.
- `processing`, `in_review` → not from you right now; something or someone
  else holds it. Say which.
- `uploaded`/`received` → **yes, and this is the trap**: the file is there
  but was never submitted. Submit it.
- `rejected` → yes, and the decline note says why.
- `pending`/`requested`/`overdue` → check whether the posted transaction is
  reconciled first. If it is, the receipt is already on a bill and nothing is
  owed.

### "Who is behind on receipts?"

```javascript
query("card_transaction", filters={
  legal_entity_id: 9,
  receipt_status: "overdue"
})
```

Then group by `employee_id`. Remember to exclude reconciled charges before
telling anyone they are behind — and to include `uploaded` charges, which
look filed but are not.

### "Chase these specific charges now"

Ask the accountant to select them on the Card expenses page and click
**Request receipt**. That queues an immediate targeted run, bypassing the age
thresholds.

### "I sent it — why does it still say I owe one?"

Almost always an attach with no submit. Check for `uploaded`, and submit:

```javascript
submit("card_transaction", "submit_receipt", {
  card_transaction_id: 123, legal_entity_id: 9
})
```

### "The receipt does not match the charge"

Nothing is graded here any more. The bill pipeline extracts the document and
its own confidence gate decides; a document it cannot read confidently goes
to `in_review` and a person looks at it. If a charge was already declined it
reads `rejected`, and the decline note is the thing to act on.

---

## Other receipt types

**Petty cash and travel receipts** attach to expense reports, not card
charges — a different flow with its own reimbursement path. See
[Expense Management](expense-management.md).

**Prepaid expenses** (annual subscriptions amortised over a period) are an AP
invoice concern, not a receipt one. See
[Transaction Processing](transaction-processing.md).

---

## Key takeaways

- A receipt **documents** an already-posted charge; it never posts anything.
- **Attaching is not submitting.** `attach_receipt` leaves the charge at
  `uploaded` and starts nothing. `submit_receipt` is what hands it over. A
  receipt that is attached and not submitted is not documented and is still
  chased.
- **No receipt at all is a first-class answer**: `submit_receipt` with a
  `no_receipt_reason` opens a human review, and acceptance gives `waived`.
- Two intake paths: filed against a charge and submitted, or emailed in
  (`bills@` or `receipts@` — both reach the bill pipeline for a merchant
  document) and posted as a bill. Both are normal.
- **A bill that arrives carrying a card link settles that charge
  immediately** — as two postings, the application and a
  `CARD_EXPENSE_RECLASS` journal. An unlinked bill still waits for the
  reconciliation agent's next sweep.
- **A till slip forwarded into the bill pipeline is not a guaranteed
  auto-post** — its extraction confidence is usually below the default
  review threshold, so it commonly lands with a human.
- `receipt_status` has thirteen stored values (two of them legacy), and a
  charge documented via an unlinked bill still reads `pending`/`requested`.
  Check reconciliation before claiming a receipt is owed.
- **Evidence is immutable once someone has acted on it.** Delete is refused
  from `processing` onward; attaching another document is almost always
  allowed.
- Chasing is a two-step ladder (default 3 then 7 days), max two emails, with
  no expiry.
- **There is no match grading.** No amount/date/merchant flags are computed
  any more — the bill pipeline's extraction and confidence gate are the only
  judgment.

---

*Last verified against code: 2026-08-14*

*Related Resources:*
- [Corporate Cards Management](corporate-cards-management.md) — card programs and transactions
- [Transaction Processing](transaction-processing.md) — GL posting
- [Expense Management](expense-management.md) — employee expense reports and reimbursements
- [Reconciliation Management](reconciliation-management.md) — how a charge is matched to a bill


### Follow-up block retention (2026-10-06; deployment pending)

The original Bill follow-up module is retained byte-for-byte as bill_followups_v1.py for pinned v1.0.0 stages. Current follow-up stages register v1.0.1; new prepared releases select it. Existing revisions remain unchanged until a reviewed compatible release is activated. The retained summary may still omit an old pending-posting result; inspect its structured outcome. Version retention never removes current authorization checks.


## Card receipt posting and dimension recovery (2026-10-06)

Documentation acceptance, source GL posting and AP settlement are independent. If a receipt has already produced a bill but the card charge is unposted, process the existing source through the Bank agent in card mode, scoped by `legal_entity_id` and `card_transaction_ids`. Verify `posted_transaction_id`; then link the existing bill through `card_purchase.manage` and settle through `reconciliation.match` with scope `ap` and the current purchase version. Do not create another bill or manually adjust expense accounts to bypass this sequence. QA verified source1 -> CARD000001/49 -> Bill48 -> reclassification50.

The dimension-context change is implemented but awaits deployment verification. Cardholder defaults are used only when the transaction workflow enables `employee` as a dimension default source. A receipt uses its exact stored attachment-to-card link within the same entity; the cardholder is resolved for the posting date. Ambiguous links/history refuse processing. Explicit dimension values take precedence; reviewed Bill dimensions remain frozen. Business-purpose text is not a structured dimension assignment, and an employee's defaults do not automatically supply a project or override a product. Configure required dimensions and review missing values instead of assuming successful posting proves complete classification.

### Domain migration retention (2026-10-28)

The v1.0.1 follow-up module is also pinned by saved revisions and must remain byte-for-byte stable, including presentation text. Configure `DASHBOARD_URL=https://app.arfiti.com` for the new dashboard links; shared sender mapping supplies migrated platform addresses. Historical follow-up email footers may retain the previous brand wording. Changing that footer requires a separately versioned implementation and reviewed activation, never rewriting stored hashes or bypassing deployment preflight.
