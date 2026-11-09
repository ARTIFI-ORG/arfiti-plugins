## Stale review transitions (local, unreleased)

An ordinary bank-agent review update cannot overwrite a concurrent exclusion or
completed journal link. Only an unlinked `unmatched`/`needs_review` row in the
current entity can be updated. If the source changed, the attempt reports a
source-state diagnostic through `error_validation_failed` and creates no follow-up
question for that failed update. Re-read the source; do not treat this outcome as
posting success, an exclusion revocation, or permission to retry a posting.
Statement void/revocation and cross-source identity remain separate controls.


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



## Agent callback and failure evidence

For Bank pipeline 1.1.0, dependency completion means a stored, currently verified
producer outcome. A completed activation or copied success flag is insufficient.
Inspect each source outcome and permission error before retrying; a rolled-back
workflow can have an attempted ID without a surviving row. Preview does not test
posting. Use normal guarded processing after authority/evidence repair, and do not
change classification to bypass a permission failure. Unlinked bills/card expenses
remain pending until normal reconciliation is run. Version 1.0.0 retained runs keep
their original consumer; verify the active revision before relying on 1.1.0 behavior.


## Card purchase policy

Use the backend purchase workspace and shared matching decision; do not implement a competing card matcher in conversation. Preserve provider rows and show net purchase spend. Reference conflicts and competing candidates require review. A paid/settled item can still lack documentation; attach missing source evidence to the existing bill. Evidence review, waiver and grouping use `card_purchase.manage` with current version, evidence fingerprint and reason. Never infer write-off authority from matching tolerance.

Receipt follow-up belongs to the purchase obligation, with one owner and deduplicated reminder stages. Automation and delivery are report-only until the entity rollout settings are explicitly enabled. Statement coverage and opening/movement/closing balance controls must pass independently of agent match counts. August deletion/replay requires its own reviewed manifest and explicit authorization through transaction.delete; implementation permission does not authorize it.

Legacy payment-pass descriptions below apply to non-card AP/AR behavior. Card rows use the shared purchase policy and cannot use nearest-date refund pairing, fuzzy amount identity or adjusting-journal workarounds.

# Bank Statements Management

## Plaid bank connection (local, not deployed)

The legacy Plaid preview adapter is not registered for
`manage_connectors` ingestion. Preview does not create bank lines, acknowledge a
durable cursor or prove reconciliation. Keep pending, modified and removed rows
distinct. Never invent balances to force a preview through statement import.
Platform credentials belong in server configuration, never chat. The
dedicated dashboard uses Link and stores the Item token encrypted. See the
provider guide.

The local branch also has a shared `bank_statement.sync` operation for complete
transaction-feed deltas. It goes through `submit` and always requires an active
organization workflow definition; none are activated for customers by this
change. All changed accounts need explicit mappings. Pending evidence stays out
of reconciliation; posted lines have no fabricated balances. Updates and removals
preserve source history; protected, classified, linked or closed-period evidence
refuses the complete batch. Pending-only records may advance in a closed period
only when they create or change no bank line. The cursor advances only with all
account writes. Deltas support up to 500,000 total records; larger batches fail
without acknowledging a partial cursor. This bound is not a scale guarantee.
Incoming posted date ranges overlapping non-voided manual/other non-feed
statements are refused regardless of provider IDs. Choose the start date after
existing statement history before the first sync.
Plaid's optional **Start importing from** setting filters previously unseen
transactions by an inclusive date. Choose and save it before first sync; afterward
it is fixed. Unset includes all available history. Skipped rows do not stall the
cursor, and known imported rows still receive protected corrections/removals.
Browser Link/renewal, actual signed Sandbox webhook delivery and imports into a
disposable database were tested. The local sandbox dashboard and daily/weekly
scheduler now use this gateway. Outstanding approval workflows block new
proposals, and revoked schedule-owner access stops imports. Signed public callbacks
now trigger the same consumer for connections with automatic sync enabled, with
durable retry recovery every 60 seconds. Manual mode prevents callback imports.
Real-bank connections use separate production configuration and bank OAuth; provider approval, deployment and real-bank verification remain pending. The user chooses test or real banks at creation; an existing connection cannot change environment. This is not production enablement. Renewal preserves the Item/cursor; reconnect
after removal creates a new connector and preserves history. Importing a new feed
into an account with another feed's history is refused pending explicit cutover.

## Existing postings and unclassified movements

Before automatic bank classification, same-day GL cash movements are checked within the organization, legal entity, bank GL account and document currency, using the signed amount. Reversed originals and reversal entries are both candidates. A candidate produces `possible_existing_gl` review, not an automatic match: amount and date do not establish identity. Review the source and match the existing transaction, or explicitly classify a genuinely separate movement.

`OTHER_BANK_TRANSACTION` remains in review (`uncertain_gl_account`), including when selected in a review response. A model-selected or remembered counterpart account is not sufficient evidence to post. Resolve to a supported classification, match an existing posting, or submit an evidenced journal through the normal approval workflow and then match it. Known classifications keep their existing handlers. The candidate check is limited to the same accounting date; it is not a complete cross-date duplicate detector.

For already-posted erroneous agent journals, preserve their audit history: review the statement links, reverse only the erroneous journals through the normal workflow, then match the correct original transactions and rerun statement controls and GL reports. A balanced trial balance or statement alone does not certify classification correctness.

### Advisory journal candidates (`bank_journal_candidates`)

`generate_report("bank_journal_candidates", {"legal_entity_id", "source_kind",
"source_id", "limit"?, "before_id"?})` lists posted journals that might already
book one bank statement line (`source_kind: "bank"`) or card transaction
(`"card"`). It needs accounting read access plus visibility of that source row
(the same ownership rules as `query`); a hidden source returns
`source_not_found_in_scope` without loading it.

The scan covers ledger postings only (`posted_at` set and status not `draft`,
`void`, `voided` or `cancelled`; such headers can keep GL lines but book nothing)
with a GL line on the source's own bank GL account
(a card uses its card program's card account, never the funding account), in the
account currency and with the same signed account amount, newest first, `limit`
1-100 (default 25), paged with `before_id`/`next_before_id`. Journals already
linked to the source are returned separately as `observed_anchor_ids`; journals
whose account amount cannot be determined go to `unresolved_journals`. Reversal
and payroll visibility follow the reader's transaction permissions.

Every row is labelled `business date not checked`, with `advisory_only: true`
and `ownership_verified: false`. A candidate is not identity proof, a match, a
claim or permission to post or link; no date window or tolerance is applied, and
`absence_proves_unbooked` is always false. Missing account mapping, a currency
mismatch or an unknown direction returns `determination: "unresolved"` with a
reason instead of an empty list. The report runs in a read-only repeatable-read
transaction and writes nothing. The same-day `possible_existing_gl` check above
is unchanged and does not use this report.

This resource covers bank statement management: importing statements, viewing statement lines, and reconciliation.

---

## Overview

Bank statements track cash movements in company bank accounts. Statement lines can be matched to GL transactions for reconciliation.

**What you can do:**
- Create and manage company bank accounts
- Import bank statements (CSV, OFX, connector sync)
- View and filter statement lines
- Match statement lines to GL transactions
- Track reconciliation status

**Available Tools:**

| Tool | Purpose |
|------|---------|
| `get_entity("bank_account", id=X)` | Get single bank account |
| `get_entity("bank_statement", id=X)` | Get single statement |
| `get_entity("bank_statement_line", id=X)` | Get single statement line |
| `query("bank_account", filters)` | List bank accounts |
| `query("bank_statement", filters)` | List statements |
| `query("bank_statement_line", filters)` | List statement lines |
| `query("bank_account", query)` | Search bank accounts |
| `query("bank_statement_line", query)` | Search by description/reference |
| `submit("bank_account", "create", {...})` | Create bank account |
| `submit("bank_account", "update", {...})` | Update bank account |
| `submit("bank_statement", "import", {...})` | Import bank statement |
| `submit("bank_statement_line", "match", {...})` | Match line to GL transaction |
| `submit("bank_statement_line", "unmatch", {...})` | Unmatch a line |
| `submit("bank_statement_line", "exclude", {...})` | Exclude a line (no GL needed) |
| `submit("bank_statement", "void", {...})` | Void a statement (reverses all GL) |
| `query("bank_statement_line", group_by, aggregates, filters)` | Aggregate statement lines (e.g., totals by status) |
| `query(entity_type, filters={...})` ×N | Fetch reference data (issue the calls in parallel) |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any operation above, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

---

## Choosing the import path for a statement that includes card activity

Read this **before** importing a statement that mixes regular transfers with card charges. Picking the wrong path produces silent double-counting or orphaned card data.

| You have… | The bank account `account_type` is… | Import path | Where the card lines land |
|---|---|---|---|
| A dedicated **corporate-card statement** (one bill per month) | `credit_card`, with a card program whose `card_bank_account_id` points at this account | `submit("bank_statement", "import", …)` once. Lines auto-route. | `bank_card_transactions` (handled by `bank_transaction_processor` (card mode)) |
| A **checking account with debit cards on it** (Wise, Revolut, N26, Mercury) | `checking` (or `savings`) | **Two imports**: (1) `submit("bank_statement", "import", …)` with the **non-card** lines; (2) `submit("import", "execute", { object_type: "card_transaction", … })` with the card lines. | Card lines go to `bank_card_transactions`, **not** to `bank_statement_lines` |
| Statement-only **card transactions** with no bank statement context | n/a | `submit("import", "execute", { object_type: "card_transaction", … })` directly. | `bank_card_transactions` |

**Why the split for the checking-with-debit-cards case:** the auto-routing rule (`card_bank_account_id`) is gated on `account_type='credit_card'`, so it never fires for a checking account. If you put all 20 lines on the bank statement, the 7 card lines are recorded twice (once as bank_statement_lines, once if/when the card-transaction posting later settles to cash) **or** the card-transaction lifecycle (employee submission, MCC categorisation, approval lanes, receipt attach) is skipped entirely.

**Heuristic to detect card lines in a mixed CSV:**
- `transaction_details_type` (Wise) or `Type` (Revolut) `== "CARD"`, and any matching `FEE-CARD-*` lines
- A `card_last4` / `card_id` / `merchant_category_code` populated in the row metadata
- A merchant-name pattern (UBER, AMAZON, GITHUB, hotel/airline names, etc.)

Filter card-shaped lines **out** of the bank-statement payload, then import them via the `card_transaction` path. The bank account's running balance still ties out: card-transaction postings settle to cash via the card-clearing → cash entry generated by the card pipeline.

### Two ids per card row: the event and the purchase

A provider issues **one id per movement** and, separately, identifies **which
purchase that movement belongs to**. A Bolt ride charged €5.00 and refunded
€1.46 is two movements but *one* €3.54 purchase. Carry both or the second fact
is lost:

| field | what it identifies | must be |
|---|---|---|
| `external_transaction_id` | this single movement (the leg) | unique per `(external_transaction_id, card_id, transaction_type)` — that is the importer's duplicate key |
| `metadata.provider_purchase_id` | the purchase all its legs belong to | **shared** by every leg of the same purchase |

**Why it matters.** `provider_purchase_id` is what
`card_purchases/identity.py::resolve_purchase_identity` reads to group legs into
one purchase. Supply it and the purchase resolves `identified`: the workspace
shows the **net** merchant amount, the refund attaches to *its own* charge, fees
are disclosed separately without polluting the net, a full reversal nets to zero
and raises no receipt demand, and the purchase carries **one** documentation
obligation instead of one per leg.

Omit it and nothing errors — which is the trap. Every leg silently becomes its
own singleton purchase, and every refund lands in `unresolved` for human review,
because the resolver will not guess that two rows are the same purchase from
amount, date or merchant. A statement imported without it looks fine and has
quietly lost all netting.

**Reading it off a statement.** It is usually already in the export:

- **Wise** — the `TransferWise ID` column. Both legs of a ride carry the same
  value; the fee row prefixes `FEE-`. So
  `provider_purchase_id` = that id with a leading `FEE-` stripped and any suffix
  you added to keep the leg's own id unique (`-REFUND`, `-2`) removed.
- **Revolut** — the card payment's transaction id, shared by its refund.
- Anything else — whatever field the provider repeats across the legs of one
  purchase.

**When NOT to set it.** Only when the provider itself says two movements are the
same purchase. Never synthesise one from merchant + date + amount: that is
guessing, and this design deliberately refuses amount/date similarity as
identity — three €50 fills at one petrol station are three purchases, not one.
If the provider gives you nothing, leave it out and let the rows resolve as
singletons; finance can group them explicitly through
`card_purchase.manage`, which records who decided and why.

### The provider's own stated total, when there is one — OPTIONAL

Some exports tell you what the whole purchase came to, independently of how it
was split into movements. Wise writes it into every leg's description, **signed
as cost**:

```
-5.00    "Card transaction of 6.18 EUR issued by Bolt.eu/r/2608260657 Tallinn"
-1.18    "Card transaction of 6.18 EUR issued by Bolt.eu/r/2608260657 Tallinn"
+200.07  "Card transaction of -200.07 EUR issued by Hotel At Booking.com Dublin"
```

The first two rows are one purchase: the hold was €5.00, the fare came to
€6.18, so the remainder was taken separately. The third is a refund, and Wise
states it negative. Pass the figure **exactly as the provider states it, sign
included** — never flip it, never take its absolute value:

| field | meaning |
|---|---|
| `metadata.provider_stated_amount` | the purchase total as the provider states it, signed as the provider signs it |
| `metadata.provider_stated_currency` | the currency THAT figure is in |

**Why it is worth passing.** It is the one number the grouping can be checked
against without a human. If a purchase's legs sum PAST what the provider says
it cost, or to the opposite sign, two unrelated movements were grouped or a
sign was read wrong — and neither is visible by looking at the rows. That
purchase is held for review, and released again the moment its legs tie.

Legs that fall SHORT of the stated total are not held: movements resolve one
at a time, so the first leg of a split purchase is always alone against the
full figure. A leg that truly never arrives shows up where it should — as a
gap in the statement's balance tie.

**The currency matters and is not optional.** The stated figure is in the
MERCHANT's currency, not the account's: a $20.00 subscription settles as
€17.27, and comparing those two numbers manufactures a discrepancy that is only
an exchange rate. Pass both, or pass neither.

**Fees.** Import a bank's card fee as its own row with `transaction_type: "fee"`
and the charge's `provider_purchase_id`; it then rides on the purchase as a fee
leg and is excluded from the stated-total check. A fee that ends up alone —
no charge carries its id — needs no receipt (documentation `not_required`) and
is settled when its ledger row is reconciled; it never asks finance for anything.

**Most banks do not provide this.** It is genuinely optional — leave both
fields out and nothing is lost; the purchase simply has no independent figure
to be checked against. Never compute one yourself by adding up the legs: that
checks the grouping against itself and will agree with any mistake.

> **One table, whatever the source:** every card movement lands in `bank_card_transactions` — connector sync, Stripe Issuing webhook, and manual/CSV/statement import alike. The `object_type: "card_transaction"` in the import payload is the *importer's* name, not a second table. (This note previously described a separate `card_transactions` table for manual imports; no such table exists in any schema, and `CardTransactionImporter.TABLE_NAME` is `bank_card_transactions`.)

---

## Statement Intake & Account Discovery

When a user uploads a bank statement (PDF, CSV, or via Claude), the system must validate that the account exists and is properly classified before processing. This is an **intelligent discovery flow** — the system learns about new accounts as they appear naturally.

### Step 1: Extract Account Identifier

From the uploaded statement, extract the IBAN, account number, or other identifier. For PDF statements (camt.053, MT940), the IBAN is in the header. For CSV imports, the user provides the bank_account_id or IBAN.

### Step 2: Match to Existing Bank Account

```javascript
// Search by IBAN
query("bank_account", query="EE637700771002623947", { legal_entity_id: 12 })

// Or search by account number
query("bank_account", query="771002623947", { legal_entity_id: 12 })
```

### Step 3: Route Based on Match Result

**Case A: Account found, linked to card program → Auto-route to card processing**

The system checks if this bank account is a card program's `card_bank_account_id`. If yes, statement lines are automatically converted to `bank_card_transactions` and processed by the `bank_transaction_processor` (card mode) agent.

No user action needed — this is fully automatic.

**Case B: Account found, regular bank account → Process as bank statement**

Standard bank statement processing. Lines go to `bank_statement_lines` and are processed by the `bank_transaction_processor` agent.

No user action needed.

**Case C: Account NOT found → Ask user to identify the account**

This is the critical discovery moment. The agent MUST ask the user before proceeding:

> "I found a statement for IBAN **EE637700771002699XXX** but this account doesn't exist in the system yet. What type of account is this?"
>
> 1. **Operating/checking account** — Regular bank account for business operations
> 2. **Credit card account** — Corporate card where employee charges appear
> 3. **Savings account** — Interest-bearing account
> 4. **Skip** — Don't process this statement right now

Based on the user's answer:

**If checking/savings account:**
```javascript
// Create the bank account
submit("bank_account", "create", {
  legal_entity_id: 12,
  bank_account_code: "LHV-EUR-NEW",
  account_name: "LHV New Account EUR",
  iban: "EE637700771002699XXX",
  bank_name: "LHV Pank",
  currency: "EUR",
  account_type: "checking",       // or "savings"
  gl_account_number: "1000"       // Ask user which GL account
})
// Then import the statement
```

**If credit card account:**
```javascript
// 1. Create the bank account with credit_card type
submit("bank_account", "create", {
  legal_entity_id: 12,
  bank_account_code: "LHV-CC-EUR",
  account_name: "LHV Corporate Card EUR",
  iban: "EE637700771002699XXX",
  bank_name: "LHV Pank",
  currency: "EUR",
  account_type: "credit_card",
  gl_account_number: "2100"       // Credit card payable
})

// 2. Ask: "Which card program does this belong to?"
query("card_program", filters={ legal_entity_id: 12, is_active: true })

// If existing program → link it:
// UPDATE bank_card_programs SET card_bank_account_id = <new_account_id> WHERE id = <program_id>
// Refused (bank_claim_program_retained) once any card of the program is linked to a journal.

// If new program needed → create it:
submit("card_program", "create", {
  legal_entity_id: 12,
  program_name: "LHV Corporate Card",
  program_type: "corporate",
  card_type: "virtual",
  currency_code: "EUR",
  card_bank_account_id: <new_account_id>,
  gl_clearing_account_number: "2100"   // Liability/clearing account for credit-card mode.
                                       // For debit cards (Wise/Mercury), omit this — the
                                       // card processor falls back to the funding bank's GL.
                                       // See corporate-cards-management.md → "Debit-card vs
                                       // credit-card posting modes".
})

// 3. Then import the statement (auto-routes to card processing)
```

**Case D: Account found but account_type unclear → Ask user to confirm**

If the bank account exists but has `account_type = 'checking'` and the statement contains card-like transactions (merchant names, MCC codes), ask:

> "This statement is for **LHV Card Account EUR** which is set up as a checking account, but the transactions look like card charges (merchants: UBER, GITHUB, AMAZON). Should I reclassify this as a credit card account and link it to a card program?"

### Step 4: Per-Card IBAN Matching (for card accounts)

When processing card statements, individual transactions may reference sub-account IBANs for specific cards. The system checks `bank_cards_issued.iban` to match:

```javascript
// If a transaction references IBAN EE637700771002699123
// and card #383 has iban = "EE637700771002699123"
// → Transaction is assigned to card #383 (Marika Kask)
// Matching ignores spaces, hyphens and case.

// If no card IBAN matches:
//   • program has exactly ONE active card → assigned to it (unambiguous)
//   • program has TWO OR MORE active cards → recorded but flagged
//     recon_status = 'exception' + metadata.card_attribution, and NOT
//     auto-posted (the posting query takes only 'pending_recon'), so a
//     charge never posts under a guessed employee
```

When a transaction comes back flagged, ask: "Which employee's card is this
transaction for?" Reassigning it clears the flag and returns it to the normal
posting flow.

### Step 5: Missing Card Discovery

If a card statement references a card number or IBAN that doesn't match any issued card:

> "I found transactions for card ending in **9123** but no card with this number exists in program **Arfiti Corporate Card**. Should I create a new card?"
>
> 1. **Yes, issue a new card** — Specify employee
> 2. **It belongs to an existing card** — Select from list
> 3. **Skip these transactions**

### Summary: Statement Intake Decision Tree

```
Upload statement
    ↓
Extract IBAN / account number
    ↓
Search bank_accounts
    ↓
├─ FOUND
│   ├─ Has card_program link (card_bank_account_id)
│   │   └─ ✅ Auto-route to card processing
│   ├─ account_type = 'credit_card' but no card program
│   │   └─ Ask: "Link to existing program or create new?"
│   └─ Regular account (checking/savings)
│       └─ ✅ Process as bank statement
│
└─ NOT FOUND
    └─ Ask: "What type of account is this?"
        ├─ Checking/savings → Create bank account → process
        └─ Credit card → Create bank account → link/create program → process
```

> **Key principle:** Never silently fail or skip. If something is missing or ambiguous, ask the user. Every statement upload is an opportunity to build out the account structure.

---

## Bank Accounts

Company bank accounts represent actual bank accounts used for operations.

### Creating a Bank Account

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="bank_account", operation="create")

// Step 2: Submit with discovered fields
submit("bank_account", "create", {
  legal_entity_id: 9,
  bank_account_code: "CASH-USD-MAIN",
  account_name: "Main Operating Account - Chase",
  gl_account_number: "1010",          // GL cash account

  // Bank details
  bank_name: "JP Morgan Chase",
  bank_country: "US",
  account_holder_name: "Arfiti Technologies Inc",

  // Account numbers (encrypted)
  account_number: "123456789",
  routing_number: "021000021",

  // Classification
  currency: "USD",
  account_type: "checking",           // checking, savings, credit_card
  usage_type: "operating",            // operating, payroll, tax, savings

  // Default flags
  is_operating: true,
  is_default_payments: true,
  is_default_receipts: false,

  // Limits (optional)
  daily_limit: 100000.00,
  monthly_limit: 2000000.00,

  // Import format (for CSV)
  statement_import_format: "CSV"      // CSV, OFX, QBO, MT940
})
// Tip: Use validate_only=true to check payload before submitting
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `legal_entity_id` | number | Legal entity ID |
| `bank_account_code` | string | Unique code (e.g., "CASH-USD-MAIN") |
| `account_name` | string | Display name |
| `gl_account_number` | string | GL cash account number |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `bank_name` | string | Bank name |
| `bank_country` | string | ISO 2-letter country code |
| `account_holder_name` | string | Name on account |
| `account_number` | string | Account number (encrypted) |
| `routing_number` | string | ACH routing number (encrypted) |
| `iban` | string | IBAN (encrypted) |
| `swift_code` | string | SWIFT/BIC code |
| `currency` | string | ISO currency code (default: "USD") |
| `account_type` | string | checking, savings, credit_card, line_of_credit |
| `usage_type` | string | operating, payroll, tax, savings |
| `is_operating` | boolean | Primary operating account |
| `is_default_payments` | boolean | Default for outgoing payments |
| `is_default_receipts` | boolean | Default for incoming receipts |
| `daily_limit` | number | Daily transaction limit |
| `monthly_limit` | number | Monthly transaction limit |
| `statement_import_format` | string | CSV, OFX, QBO, MT940 |

### Listing Bank Accounts

```javascript
// List all active bank accounts
query("bank_account", filters={
    legal_entity_id: 9,
    is_active: true
  })

// List by usage type
query("bank_account", filters={
    legal_entity_id: 9,
    usage_type: "operating"
  })

// List by currency
query("bank_account", filters={
    legal_entity_id: 9,
    currency: "EUR"
  })
```

### Getting a Bank Account

```javascript
get_entity("bank_account", id=1)
```

**Response:**
```json
{
  "id": 1,
  "legal_entity_id": 9,
  "bank_account_code": "CASH-USD-MAIN",
  "account_name": "Main Operating Account - Chase",
  "bank_name": "JP Morgan Chase",
  "currency": "USD",
  "account_type": "checking",
  "usage_type": "operating",
  "gl_account_number": "1010",
  "account_number_masked": "****6789",
  "routing_number_masked": "****0021",
  "is_operating": true,
  "is_default_payments": true,
  "verification_status": "verified",
  "is_active": true
}
```

---

## Bank Statements

Bank statements contain a header with period information and lines for individual transactions.

### Importing a Bank Statement

#### From CSV

```javascript
submit("bank_statement", "import", {
  legal_entity_id: 9,
  bank_account_id: 1,
  statement_date: "2026-01-31",
  statement_number: "2026-01-CHASE",
  source: "csv_upload",

  // Optional balances
  opening_balance: 50000.00,
  closing_balance: 67500.00,

  // Statement lines
  lines: [
    {
      line_number: 1,
      transaction_date: "2026-01-05",
      description: "ACH CREDIT CUSTOMER PAYMENT - INV-001",
      reference_number: "ACH123456",
      debit_credit: "credit",
      amount: 5000.00,
      balance_after: 55000.00
    },
    {
      line_number: 2,
      transaction_date: "2026-01-10",
      description: "CHECK 1001 - ACME SUPPLIES",
      reference_number: "CHK1001",
      debit_credit: "debit",
      amount: 1500.00,
      balance_after: 53500.00
    },
    // ... more lines
  ]
})
```

#### From CSV File

When user provides a CSV file, parse and submit:

```javascript
// CSV Format expected:
// transaction_date,description,reference_number,debit_credit,amount,balance_after
// 2026-01-05,ACH CREDIT CUSTOMER PAYMENT,ACH123456,credit,5000.00,55000.00
// 2026-01-10,CHECK 1001 - ACME SUPPLIES,CHK1001,debit,1500.00,53500.00

submit("bank_statement", "import", {
  legal_entity_id: 9,
  bank_account_id: 1,
  statement_date: "2026-01-31",
  lines: parsedCsvLines,  // Array of line objects
  options: {
    on_duplicate: "skip"  // Skip if reference_number exists
  }
})
```

**Required Statement Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `legal_entity_id` | number | Legal entity ID |
| `bank_account_id` | number | Bank account ID |
| `statement_date` | string | Statement date (YYYY-MM-DD) |
| `lines` | array | Array of statement lines |

**Required Line Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `transaction_date` | string | Transaction date (YYYY-MM-DD) |
| `description` | string | Transaction description |
| `debit_credit` | string | "debit" or "credit" |
| `amount` | number | Absolute amount (positive) |

**Strongly Recommended Line Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `currency` | string | **Always include.** ISO currency code (e.g. "EUR", "USD"). Critical for multi-currency reconciliation. |
| `reference_number` | string | Bank reference / document number. Used for automated matching. |
| `metadata` | object | **All extra bank-specific data** — counterparty name, IBAN, BIC, FX info, document numbers. See "Enriched Bank Data" below. |

**Optional Line Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `line_number` | number | Line sequence number |
| `value_date` | string | Value date (if different) |
| `external_reference` | string | External system reference |
| `balance_after` | number | Running balance |

### CSV Import Format

Different banks have different CSV formats. When the user provides a CSV, you need to:

1. **Identify the bank** from the CSV structure (column headers, delimiter, date format)
2. **Map ALL columns** — core fields go to dedicated line fields, everything else goes to `metadata`
3. **Always include `currency`** — read from the CSV's currency column or ask the user

**Common bank CSV formats:**

**LHV (Estonia)** — semicolon-separated, 16 columns:
```
Customer account no;Document no;Date;Sender/receiver account;Sender/receiver name;Debit/Credit (D/C);Amount;Reference number;Archiving code;Description;Currency;Personal code or register code;Sender/receiver bank BIC;Ultimate debtor name;Transaction reference;Account servicer reference
```

**Wise** — comma-separated, varies by export type:
```
TransferWise ID,Date,Amount,Currency,Description,Payment Reference,Running Balance,Exchange From,Exchange To,Buy - Loss,Exchange Rate,Payer Name,Payee Name,Merchant
```

**Swedbank** — semicolon-separated, Estonian headers:
```
Kliendi konto;Kuupäev;Saaja/Maksja;Saaja/Maksja konto;Deebet/Kreedit;Summa;Viide;Arhiveerimiskood;Selgitus;Valuuta
```

**Signed amounts format** (any bank):
- Positive amounts = credits (money in)
- Negative amounts = debits (money out)
- No `debit_credit` column needed — the import system derives direction from amount sign

**Mapping rules:**

| CSV Column Type | Maps To | Notes |
|----------------|---------|-------|
| Date | `transaction_date` | Parse to YYYY-MM-DD |
| Description/Memo | `description` | Full transaction text |
| Amount | `amount` | Positive=credit, negative=debit (or use debit_credit) |
| D/C indicator | `debit_credit` | "debit" or "credit" |
| Reference/Doc no | `reference_number` | Bank reference number |
| Currency | `currency` | ISO code (EUR, USD) — **always include** |
| **Everything else** | `metadata.{field_name}` | Counterparty name, IBAN, BIC, FX info, etc. |

### Enriched Bank Data (CRITICAL for Reconciliation!)

When parsing bank CSVs, **you MUST preserve ALL available data from the bank**, not just the minimum required fields. This data is critical for:
- **Automated vendor/customer identification** (counterparty name eliminates guesswork)
- **Cross-currency reconciliation** (FX rates, original amounts)
- **Reference-based matching** (document numbers, archiving codes)
- **Internal transfer detection** (counterparty IBAN matching)

**How it works:** Put extra bank fields into the `metadata` object on each line. The system stores this in a JSONB column for downstream processing.

```javascript
{
  transaction_date: "2026-01-05",
  description: "DIGITALOCEAN.COM Amsterdam NLD",
  debit_credit: "debit",
  amount: 23.06,
  reference_number: "2026010501234567",   // Goes to dedicated column
  currency: "EUR",                         // Goes to dedicated column
  metadata: {                              // Goes to metadata JSONB column
    counterparty_name: "DigitalOcean",
    counterparty_account: "NL87DEUT0265191877",
    counterparty_bic: "DEUTNL2A",
    document_number: "TKO257746",
    original_amount: "24.00",              // Pre-FX conversion amount
    original_currency: "USD",              // Pre-FX conversion currency
    exchange_rate: "0.9608333"             // Applied FX rate
  }
}
```

Common metadata field names to use:

| Bank CSV Column | Map To Field | Description |
|----------------|--------------|-------------|
| Sender/receiver name, Beneficiary, Payer, Payee | `counterparty_name` | Name of the other party |
| Sender/receiver account, IBAN, Account no | `counterparty_account` | IBAN or account number |
| BIC, SWIFT, Sender/receiver bank BIC | `counterparty_bic` | Bank identifier code |
| Sender bank code, Bank code | `counterparty_bank_code` | Domestic bank code |
| Fee, Commission, Charges | `fee_amount` | Bank fee for this transaction (as number) |
| Personal code, Register code, Tax ID | `personal_code` | Counterparty tax/registration ID |
| Archiving code, Archive ref | `archiving_code` | Bank archiving reference |
| Document no, Doc number | `document_number` | Bank document number |
| Payer Name (Wise) | `payer_name` | For incoming payments |
| Payee Name (Wise) | `payee_name` | For outgoing payments |
| Merchant (Wise) | `merchant` | Card payment merchant |
| Transaction Type (Wise/Swedbank) | `bank_transaction_type` | Bank's own type code |
| Original currency | `original_currency` | Currency before conversion |
| Original amount | `original_amount` | Amount before conversion |
| Exchange rate, Rate | `exchange_rate` | FX conversion rate |

**Example — LHV bank (Estonia):**

LHV CSV has 16 columns. Map all of them:

```javascript
submit("bank_statement", "import", {
  legal_entity_id: 12,
  bank_account_id: 3,
  statement_date: "2026-01-31",
  source: "csv_upload",
  lines: [
    {
      transaction_date: "2026-01-01",
      description: "DIGITALOCEAN.COM Amsterdam NLD",
      debit_credit: "debit",
      amount: 24.00,
      reference_number: "011701",
      currency: "EUR",
      metadata: {
        counterparty_name: "DIGITALOCEAN.COM",
        counterparty_account: "NL87DEUT0265191877",
        counterparty_bic: "DEUTNL2A",
        document_number: "TKO257746",
        archiving_code: "2026010102766653",
        transaction_reference: "1202766653",
        account_servicer_reference: "2026010102766653",
        counterparty_reg_code: "860723393B01",
        customer_account: "EE1234567890123456"
      }
    }
  ]
})
```

**Example — Wise (card payments with embedded FX):**

Wise card descriptions contain FX data in parentheses — extract it into metadata:

```javascript
{
  transaction_date: "2025-11-30",
  description: "DIGITALOCEAN.COM (..0559) 2025-11-30 AMSTERDAM NLD (24.00 USD, rate 0.8654166)",
  debit_credit: "debit",
  amount: 20.77,
  currency: "EUR",
  metadata: {
    original_amount: "24.00",        // Extracted from description
    original_currency: "USD",        // Extracted from description
    exchange_rate: "0.8654166",      // Extracted from description
    bank_transaction_type: "CARD",
    merchant: "DIGITALOCEAN.COM"
  }
}
```

**Example — Wise (non-card transfers):**
```javascript
{
  transaction_date: "2026-02-05",
  description: "Cashback",
  debit_credit: "credit",
  amount: 1.43,
  currency: "EUR",
  metadata: {
    bank_transaction_type: "BALANCE_CASHBACK"
  }
}
```
> **Classification note:** The `bank_transaction_processor` agent classifies cashback / reward / rebate lines as `CASHBACK_REWARD` (its own transaction type code, posting profile `cashback_reward`, default counterpart account 4900 Other Operating Income). It is NOT classified as `BANK_INTEREST` — that's reserved for interest accrual on deposits or loan balances.

**Example — Swedbank:**
```javascript
{
  transaction_date: "2026-02-02",
  description: "'2026-01 Final pay Andrii Rudchuk",
  debit_credit: "credit",
  amount: 3867.15,
  reference_number: "D40247",
  currency: "EUR",
  metadata: {
    counterparty_name: "STARSHIP TECHNOLOGIES OÜ",
    archiving_code: "2026020200234368",
    bank_transaction_type: "MK"
  }
}
```

**Key principle:** Include EVERY field the bank provides. Put `currency` at the line level (not in metadata). Put everything else the bank provides into the `metadata` object. The transaction processor and reconciliation agent both use this data:
- **Counterparty names** → automatic vendor/customer identification (zero LLM calls needed)
- **IBANs/BICs** → internal transfer detection between own accounts
- **FX data** (original_amount, original_currency, exchange_rate) → cross-currency reconciliation matching
- **Document/reference numbers** → reference-based matching passes
- **All fields** → full audit trail preserved for compliance

### Listing Bank Statements

```javascript
// List all statements for a bank account
query("bank_statement", filters={
    bank_account_id: 1,
    legal_entity_id: 9
  },
  sort_by="statement_date",
  sort_order="desc")

// List by status
query("bank_statement", filters={
    legal_entity_id: 9,
    status: "imported"  // imported, in_progress, reconciled
  })
```

### Getting a Bank Statement

```javascript
get_entity("bank_statement", id=10)
```

**Response:**
```json
{
  "id": 10,
  "legal_entity_id": 9,
  "bank_account_id": 1,
  "bank_account_name": "Main Operating Account - Chase",
  "statement_number": "2026-01-CHASE",
  "statement_date": "2026-01-31",
  "opening_balance": 50000.00,
  "closing_balance": 67500.00,
  "source": "csv_upload",
  "status": "imported",
  "imported_at": "2026-02-01T10:00:00Z",
  "line_count": 15
}
```

> **Note:** `bank_account_name` is a virtual field resolved inline — no separate `get_entity("bank_account")` call needed.

---

## Bank Statement Lines

Statement lines are individual transactions within a statement.

### Listing Statement Lines

```javascript
// List all lines for a statement
query("bank_statement_line", filters={
    bank_statement_id: 10,
    legal_entity_id: 9
  },
  sort_by="line_number",
  sort_order="asc")

// List unmatched lines (for reconciliation)
query("bank_statement_line", filters={
    legal_entity_id: 9,
    bank_account_id: 1,
    recon_status: "unmatched"
  })

// List by date range
query("bank_statement_line", filters={
    legal_entity_id: 9,
    bank_account_id: 1,
    transaction_date: {gte: "2026-01-01", lte: "2026-01-31"}
  })

// List matched lines
query("bank_statement_line", filters={
    legal_entity_id: 9,
    recon_status: "matched"
  })

// List credits only
query("bank_statement_line", filters={
    legal_entity_id: 9,
    bank_account_id: 1,
    debit_credit: "credit"
  })
```

**Filter Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `legal_entity_id` | number | Legal entity ID |
| `bank_account_id` | number | Bank account ID |
| `bank_statement_id` | number | Statement ID |
| `recon_status` | string | unmatched, matched, reconciled |
| `debit_credit` | string | debit, credit |
### Getting a Statement Line

```javascript
get_entity("bank_statement_line", id=123)
```

**Response:**
```json
{
  "id": 123,
  "legal_entity_id": 9,
  "bank_statement_id": 10,
  "bank_account_id": 1,
  "bank_account_name": "Main Operating Account - Chase",
  "line_number": 1,
  "transaction_date": "2026-01-05",
  "description": "ACH CREDIT CUSTOMER PAYMENT - INV-001",
  "reference_number": "ACH123456",
  "debit_credit": "credit",
  "amount": 5000.00,
  "balance_after": 55000.00,
  "recon_status": "unmatched",
  "gl_transaction_id": null
}
```

> **Note:** `bank_account_name` is a virtual field resolved inline — no separate lookup needed.

### Searching Statement Lines

```javascript
// Search by description
query("bank_statement_line", query="ACME", filters={"legal_entity_id": 9, "bank_account_id": 1})

// Search by reference
query("bank_statement_line", query="ACH123456", filters={"legal_entity_id": 9})
```

---

## Refund detection (AP_REFUND / AR_REFUND)

When a bank statement line is the **opposite direction of a recently posted line for the same merchant + amount**, the bank processor classifies it as a refund automatically — *before* calling Haiku. This prevents the historical "vendor refund classified as AR_PAYMENT → fake customer record" failure mode.

Match rules (deterministic, runs first on every line):

- Same bank account
- Opposite `debit_credit` direction
- Same merchant (counterparty_name match, exact or substring)
- Amount within ±0.5% (or 0.01 in the line currency)
- Original posted within last 90 days, has a `gl_transaction_id`
- Original is not itself a refund

When matched, the refund posts:

- **AP_REFUND**: `DR Bank / CR <original counterpart>` (e.g., the original expense account for a card refund, or the AP account for an invoice-paid refund)
- **AR_REFUND**: `DR <original counterpart> / CR Bank`

The vendor/customer is inherited from the original transaction — no new entity is created, and `master_data_agent` is not invoked. If no matching original is found, the line falls through to normal classification (Memory → Haiku); if Haiku still produces an unusable classification, the triage path catches it.

This logic lives in `bank_transaction_processor._find_matching_original_transaction` and `_process_refund`. See `GUIDE_AGENT_BANK.md` § 4 (Tier 0 — Refund pre-detection) for full details.

---

## Reconciliation

Reconciliation links bank statement lines to GL transactions.

An organization may have explicit automatic workflows for line match, unmatch
and exclude. They return immediate executor results with workflow audit records
and no human approval task. Required IDs and existing access/source checks still
apply. Workflow configuration alone never processes or repairs existing lines;
check the organization's installed policy rather than assuming a template-wide
rollout.

### Matching a Statement Line to GL Transaction

When Claude identifies a matching GL transaction:

```javascript
submit("bank_statement_line", "match", {
  statement_line_id: 123,
  gl_transaction_id: 456,
  legal_entity_id: 9
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `statement_line_id` | number | Bank statement line ID |
| `gl_transaction_id` | number | GL transaction ID to match |
| `legal_entity_id` | number | Legal entity ID |

**Result:**
- Sets `bank_statement_lines.gl_transaction_id = 456`
- Sets `bank_statement_lines.recon_status = 'matched'`

### Unmatching a Statement Line

```javascript
submit("bank_statement_line", "unmatch", {
  statement_line_id: 123,
  legal_entity_id: 9,
  reason: "Matched to wrong transaction"
})
```

**Result:**
- Clears `bank_statement_lines.gl_transaction_id`
- Sets `bank_statement_lines.recon_status = 'unmatched'`

### Excluding a Statement Line

For lines that don't need a GL posting (e.g., duplicate entries, internal bank transfers already handled, non-business items):

```javascript
submit("bank_statement_line", "exclude", {
  statement_line_id: 123,
  legal_entity_id: 9,
  reason: "Duplicate entry - already processed in previous statement"
})
```

**Result:**
- Sets `bank_statement_lines.recon_status = 'excluded'`
- Records exclusion time, numeric actor ID and the optional string reason
  (JSON null when omitted); no accounting entry is created and any existing GL
  link is retained.
- Recomputes parent finalization using the existing balance, coverage and
  posting-bridge controls. Exclusion alone does not satisfy period-close checks.
- Refused with `same_day_journal_exists` (AR-477) when an unclaimed posted
  journal already moves the same bank account by the same signed amount on the
  line's `transaction_date`. The money was most likely booked by hand: match
  the line to the journal named in `detail.journal_ids` instead. A journal
  another source already owns, a reversed journal or a reversal entry, or a different amount or
  date does not refuse. Force-finalizing a statement applies the same rule to
  every unmatched line it would exclude.

### Reconciliation Workflow with Claude

Claude performs intelligent matching:

```javascript
// Step 1: Get unmatched statement lines
const unmatched = query("bank_statement_line", filters={
    legal_entity_id: 9,
    bank_account_id: 1,
    recon_status: "unmatched"
  })

// Step 2: For each line, Claude searches for matching GL transaction
// Claude uses intelligence to match on:
// - Amount (exact or within tolerance)
// - Date (within ±2 days)
// - Description keywords
// - Reference numbers

// Step 3: Claude proposes match
// "I found a matching payment to ACME SUPPLIES for $1,500.00 posted on 2026-01-10"

// Step 4: Submit match
submit("bank_statement_line", "match", {
  statement_line_id: 123,
  gl_transaction_id: 456,
  legal_entity_id: 9
})
```

---

## Voiding a Bank Statement

Voiding a bank statement reverses all GL transactions that were posted from its lines and resets all lines to "unmatched". This is useful when a statement was imported with errors and needs to be re-imported.

### When to Void

- Statement was imported with incorrect data
- Duplicate statement was accidentally imported
- Lines were matched to wrong GL transactions
- Need to re-import from a corrected source file

### Void Workflow

```javascript
submit("bank_statement", "void", {
  legal_entity_id: 9,
  statement_id: 123,           // Required: Bank statement ID
  reason: "Imported wrong CSV file, need to re-import with correct data"  // Required
  // reversal_date: "2026-02-01"  // Optional, defaults to today
})
```

**Result:**
```json
{
  "success": true,
  "statement_id": 123,
  "statement_number": "JAN-2026-001",
  "status": "voided",
  "total_lines": 15,
  "transactions_reversed": 12,
  "message": "Bank statement JAN-2026-001 voided. 12 GL transactions reversed."
}
```

### What Happens When You Void

1. All matched lines have their GL transactions reversed (creates reversing journal entries)
2. All lines reset to `recon_status = 'unmatched'`
3. Statement status set to `voided`
4. Void metadata (timestamp, user, reason) stored in each line's metadata
5. Already-reversed transactions are skipped (safe to void twice)

### Late lines and lapsed coverage (AR-478)

**Late lines and lapsed coverage (AR-478).** A line is new or already
imported by its bank transaction id (`external_reference`):
- When the file overlaps lines already on the account and **every** line has an
  `external_reference`, lines whose id is already on the account are skipped
  (`duplicate_lines_skipped`) and the rest are imported. When any line has no
  id, the overlap is refused as before: a line without an id cannot be told
  apart from one already imported. An overlapping file is also refused when it
  repeats an id, or when it carries foreign-currency lines: sibling currency
  accounts get no duplicate or coverage handling, so import the late lines per
  currency account. The new statement records `duplicate_lines_skipped`; its
  file balances cannot tie from its own lines alone, so it needs a reviewed
  outcome rather than auto-finalisation.
- A new line dated inside another statement's `complete_account` coverage
  interval contradicts that statement's claim. The old claim is kept as
  evidence with the reason `late_lines_imported` (`bank_coverage_declarations`
  / `bank_coverage_invalidations`, migrations 753/865), the coverage mark is
  removed and the statement status is recomputed, which reopens a reconciled
  statement. Period close then reports the gap until a complete statement for
  the period is imported or the provider re-confirms the day. A `locked`
  statement (closed month) keeps its stored evidence; only the finding is
  recorded. The affected ids are returned in
  `coverage_contradicted_statements`.
- The Revolut feed does the same when a delivery changes a day already marked
  complete: the old claim is kept with `provider_delivery_changed` or
  `provider_history_incomplete` instead of being erased, and a locked
  statement's balances and coverage are left untouched
  (`closed_period_delivery_changed`). A re-confirmation of the same claim
  (only `verified_at` re-stamped) records nothing.
- Every connector sync reports new lines on days whose statement was already
  reconciled or locked as `reconciled_day_changes` in the run stats, with a
  History line naming the statements; see the Sync monitor.

### After Voiding

After voiding, you can re-import a corrected statement for the same date range:

```javascript
// The overlap check excludes voided statements, so this works:
submit("bank_statement", "import", {
  legal_entity_id: 9,
  bank_account_id: 1,
  statement_date: "2026-01-31",
  // ... corrected data
})
```

### Important Notes

- Voiding creates reversing GL entries — it does NOT delete the original transactions
- The original transactions are marked as `reversed`, the new reversing entries are `posted`
- Voided statements cannot be voided again
- A reason is required for audit trail purposes

---

## Reconciliation Status Values

| Status | Description |
|--------|-------------|
| `unmatched` | Not yet matched to GL transaction |
| `matched` | Matched to GL transaction |
| `excluded` | Intentionally excluded (no GL posting needed) |
| `reconciled` | Statement finalized and locked |
| `voided` | Statement voided — all GL reversed, lines unmatched |

---

## Common Scenarios

### Scenario 1: Set Up Bank Account and Import First Statement

```javascript
// Step 1: Create bank account
submit("bank_account", "create", {
  legal_entity_id: 9,
  bank_account_code: "CASH-USD-001",
  account_name: "Operating Account - Chase",
  gl_account_number: "1010",
  bank_name: "JP Morgan Chase",
  currency: "USD",
  account_type: "checking",
  usage_type: "operating",
  is_operating: true,
  is_default_payments: true
})

// Step 2: Import first statement
submit("bank_statement", "import", {
  legal_entity_id: 9,
  bank_account_id: 1,  // ID from step 1
  statement_date: "2026-01-31",
  opening_balance: 50000.00,
  closing_balance: 67500.00,
  lines: [
    {
      transaction_date: "2026-01-05",
      description: "ACH CREDIT - CUSTOMER PAYMENT",
      debit_credit: "credit",
      amount: 5000.00
    },
    // ... more lines
  ]
})
```

### Scenario 2: Import Bank Statement from CSV

User provides CSV file:

```
I have a bank statement CSV from Chase. Here's the data:

transaction_date,description,reference,type,amount,balance
2026-01-05,ACH CREDIT ACME CORP,REF001,credit,5000.00,55000.00
2026-01-10,CHECK 1001,CHK1001,debit,1500.00,53500.00
```

Claude parses and imports:

```javascript
submit("bank_statement", "import", {
  legal_entity_id: 9,
  bank_account_id: 1,
  statement_date: "2026-01-31",
  lines: [
    {
      transaction_date: "2026-01-05",
      description: "ACH CREDIT ACME CORP",
      reference_number: "REF001",
      debit_credit: "credit",
      amount: 5000.00,
      balance_after: 55000.00
    },
    {
      transaction_date: "2026-01-10",
      description: "CHECK 1001",
      reference_number: "CHK1001",
      debit_credit: "debit",
      amount: 1500.00,
      balance_after: 53500.00
    }
  ]
})
```

### Scenario 3: Reconcile Bank Statement

```javascript
// Step 1: View unmatched lines
query("bank_statement_line", filters={
    legal_entity_id: 9,
    bank_account_id: 1,
    recon_status: "unmatched"
  })

// Step 2: Claude finds matching GL transactions
// For line: "CHECK 1001 - ACME SUPPLIES $1,500.00"
// Claude searches: query("transaction", query="ACME SUPPLIES 1500")

// Step 3: Match the line
submit("bank_statement_line", "match", {
  statement_line_id: 124,
  gl_transaction_id: 789,
  legal_entity_id: 9
})

// Step 4: Verify reconciliation progress
query("bank_statement_line", filters={
    bank_statement_id: 10,
    legal_entity_id: 9
  })
// Check how many are matched vs unmatched
```

### Scenario 4: View Bank Account Balances

```javascript
// List all bank accounts with current status
query("bank_account", filters={
    legal_entity_id: 9,
    is_active: true
  })

// Get latest statement for reconciliation status
query("bank_statement", filters={
    bank_account_id: 1
  },
  sort_by="statement_date",
  sort_order="desc",
  limit=1)
```

### Scenario 5: Import Statement for Unknown Bank Account

When a user provides a bank statement CSV but no matching bank account exists:

```javascript
// Step 1: Check if bank account exists
query("bank_account", filters={
    legal_entity_id: 9,
    is_active: true
  })

// Step 2: If not found, ask the user for details:
// - Bank name (e.g., "JP Morgan Chase", "Swedbank")
// - GL account number to map to (e.g., "1010" for Cash)
// - Currency (e.g., "USD", "EUR")
// - Account type: "checking", "savings", or "credit_card"

// Step 3: Create the bank account
submit("bank_account", "create", {
  legal_entity_id: 9,
  bank_account_code: "CASH-USD-CHASE",        // Generate from currency + bank name
  account_name: "Operating Account - Chase",   // Descriptive name
  gl_account_number: "1010",                   // From user
  bank_name: "JP Morgan Chase",               // From user
  currency: "USD",                             // From user
  account_type: "checking",                    // From user
  usage_type: "operating",
  is_operating: true
})

// Step 4: Import the statement using the new bank_account_id
submit("bank_statement", "import", {
  legal_entity_id: 9,
  bank_account_id: <new_bank_account_id>,
  statement_date: "2026-01-31",
  source: "csv_upload",
  lines: [...]  // Parsed from user's CSV
})
```

**Important:** Always confirm bank account details with the user before creating. The GL account mapping is critical — an incorrect mapping will cause all statement entries to post to the wrong account.

---

## Key Concepts

### GL Transaction Linking

When a statement line is matched:
- `bank_statement_lines.gl_transaction_id` stores the linked transaction
- `bank_statement_lines.recon_status` changes to "matched"
- The GL transaction is NOT modified (one-way link)

### Classification Fields

Statement lines can be auto-classified:
- `expense_item_id` - Expense category (from ML classification)
- `master_vendor_id` - Detected vendor (from ML classification)
- `project_id` - Project assignment

These are suggestions that help with matching but don't affect the GL.

### Connector Sync vs CSV Import

**Connector Sync** (automated):
- Transactions flow from the Revolut connector
- Automatic daily/hourly sync
- No manual import needed

**CSV Import** (manual):
- Download statement from bank website
- Upload CSV to Claude or admin panel
- Claude parses and imports

---

## Key Takeaways

- **Bank Accounts** represent physical bank accounts with GL mapping
- **Bank Statements** contain period information and transaction lines
- **Statement Lines** are individual transactions that can be matched to GL
- **Reconciliation** links statement lines to GL transactions (one-way)
- **Use `query`** with `recon_status: "unmatched"` to find lines needing reconciliation
- **Claude handles matching** using intelligent search and pattern matching
- **CSV Import** supported for manual statement upload
- **Void and re-import** — use `bank_statement.void` to reverse all GL and re-import corrected data
- **Duplicate prevention** — importing a statement for a date range that already has a non-voided statement is blocked
- **Agent processing** — the `bank_transaction_processor` agent automatically processes unmatched lines:
  - Creates **vendors** for debit lines (payments, fees, taxes — including the bank itself for fees)
  - Creates **customers** for credit lines (incoming payments, interest — including the bank itself for interest)
  - Every line gets a party (vendor or customer) except internal transfers between own accounts
  - Uses memory to cache mappings and avoid recreating parties on subsequent runs

---

*Last Updated: 2026-02-20*
*Related Resources:*
- [Corporate Cards Management](corporate-cards-management.md) - Card programs and transactions
- [Bank Accounts Management](bank-accounts-management.md) - Full bank account workflows
- [Transaction Processing](transaction-processing.md) - GL transactions


### Reading bank statement summaries

**Lines** separates bank lines from routed card transactions: `0 bank + 14 card`
means the bank header has no ordinary lines and includes 14 card sources handled
in card statements. Both participate in the bank balance check; do not import the
card sources again as bank lines. The bank-line match rate is shown as a dash when
there are no bank lines.

**Source interval** identifies the complete-account dates supported by provider
evidence, not the first and last transaction dates. **Awaiting feed verification**
means no verified interval is recorded. Revolut's current UTC day stays open until
a later full sync can verify the completed day. This is independent of whether all
known transactions are posted.

List status cells show only the status badge. Inspect stored statement
`metadata.controls.reasons` when explaining an open statement; absence of a
second status line does not mean the controls passed. Statement details identify
the connector by its configured name (provider fallback), rather than exposing
`connector_sync` as the import label.

### Provider balance and coverage controls

Statement finalisation is separate from line match rate. All source movements must tie opening to closing in account currency; missing balances, currency/scope inconsistencies or unresolved lines prevent finalisation. An excluded line still contributes its original movement to the balance check. No invoice write-off tolerance applies to the provider balance.

`bank_statement.import` accepts optional `coverage` containing `start`, `end` (YYYY-MM-DD), `scope: "complete_account"` and `source_reference` identifying the provider evidence. Supply the actual complete-account interval, not the first and last transaction dates. Original rows and balances remain unchanged; unknown coverage remains an explicit exception.

An empty `lines` list is valid for a genuine zero-activity statement with equal opening/closing balances and complete coverage. Month-end uses the union of explicit passing intervals; later activity does not prove earlier coverage.

**What `complete_account` claims.** "Between `start` and `end`, nothing on this
account is missing" — not "all time", and not "every movement is a line on this
statement". A partial extract is therefore expressible and honest: declare the
interval you actually have, and month-end still reports the rest of the period
as a gap.

**A split bank/card statement DOES declare complete coverage.** This reverses
earlier guidance, which said a bank-only subset of a mixed account could not,
and referred to a "forthcoming canonical movement bridge". That bridge exists:
`routed_card_source_ids`. When you split a Wise or Revolut export — transfers
into `lines`, card spend into `bank_card_transactions` — list the created card
ids in `metadata.routed_card_source_ids` and declare the interval normally.

The balance tie is what makes the claim true, so it is not a formality: the
finalisation check computes `opening + movement − closing` with the routed card
sources counted alongside the lines. A movement lost in either direction —
imported but not routed, dropped outright, or routed from another month —
breaks the tie and the statement cannot finalise. Declaring coverage without
routing the card ids does not hide a thing; it produces a balance gap the size
of the card spend.


## Revolut feed controls

A statement with zero bank lines may contain routed card movements. Read the routed
card count and control reasons alongside the bank-line match rate. A zero balance
difference does not imply every movement is posted or that source coverage is known.
Revolut fees are separate, provider-linked bank movements; use configured accounting.
Never force a statement reconciled or invent source coverage to clear a warning.
A full provider snapshot or verified original statement must support the interval.
Completed, fee-free zero-value card verifications are skipped non-financial evidence;
they do not need GL posting or a receipt. Provider `posted` and ERP `posting_status`
are different facts. Recovery must use the normal posting workflow and retain the
original ignored event history.


## Purchase evidence investigation (September 2026)

For CARD_EXPENSE-to-bill identity, compare original merchant amount/currency and
provider purchase-date evidence separately from settlement dates and fees.
Revolut uses `metadata.purchase_occurred_at`, or the retained routed
`metadata.original_source.transaction_date`. Do not substitute ingestion time,
change posted dates, or use nearest-date guessing. Same-day twins remain ambiguous.
The owner retries deterministic leftovers after applied matches remove competitors.

Only when the organization has opted in (`purchase_investigation_enabled: true`;
off by default), unresolved purchases with a vendor can enter a scoped reconciliation saga. It can
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

### Receipt and reversal pairs on a bank statement

A reversed original can satisfy the statement posting control when its reciprocal, posted and unreversed reversal is also matched on the same statement. Each transaction must be represented exactly once, with opposite equal amounts, matching entity/account/currency, matching posting dates and exact signed cash GL amounts. Balance and source-interval controls still apply. This does not allow orphaned reversals, mismatched entries or net-zero replacement journals. Pairs split across statements remain outside this exception and require review; card-source controls are unchanged.

### Missing imported balances

The statement import executor stores NULL when an opening or closing balance is
omitted or explicitly null, including foreign-currency sibling statements. A
stated numeric zero stays zero. The dashboard explains missing balances instead
of calculating a tie-out; explicit 0/0 with movement shows a real difference.
Finalization and period-close controls require both balances. Reconciliation
responses preserve missing closing balances as null. Older imports may have
stored an omitted balance as zero; there is no automatic backfill because those
rows cannot be distinguished reliably from genuine zeros. Review source evidence
before correcting them. The existing schema already permits NULL; no migration.

## Status report cutoff

`reconciliation_status` accepts ISO `as_of_date` and selects the latest statement
on or before it. Matching status is current, not a historical match-event snapshot.


### Bank worklist read bindings (QA branch, not deployed)

For `review_statement_lines` and `review_card_transactions`, request reads now
check stored `lines[].id` and `_bank_worklist.rows` keys against the corresponding
business rows in the request entity. Statement-ID lists must resolve in that
entity too. Missing, foreign or malformed references withhold the request and
its thread before returned rows, counts and pagination. Present worklist/snapshot
containers must have the expected object/array shape; absent legacy metadata
remains supported. Responses inherit the originating request action.

Linked GL/posting transaction IDs use the existing transaction-read policy,
including stored transaction type and reversal ancestry. A fingerprint is not
authority and these read checks do not certify freshness, approval or completion.
The checks do not introduce a new Bank permission or repair historical records.
Free-text classification remains separate acceptance work; hosted identity and performance acceptance
remain open.


### Bank snapshot parent bindings (QA branch, not deployed)

Creating or revalidating a Bank review snapshot requires the statement line and
its statement to name the same bank account. Card rows must reference a program
in their entity; explicitly configured funding and card bank accounts must also
resolve in that entity. Optional account references may remain absent. A broken
explicit reference is not treated as an unconfigured optional account.

An inconsistent row is refused before a new fingerprint is returned. Investigate
the source and configuration through authorized workflows; do not retag records,
change old fingerprints or bypass the refusal to force a retry. This correction
does not repair historical data or certify the read authority of previously
stored request narratives. Existing status/dispute and response gates remain.


### Historical Bank review parent authority (QA branch, not deployed)

Historical Bank review reads now also validate each row's stored parents. A
statement line must resolve to a statement in the request entity and use that
statement's bank account; the account must resolve in the same entity. Card
rows must resolve to a program in the request entity, and every explicit funding
or card-bank account must resolve there. Standalone statement-ID lists apply
the same account check. Absent optional program accounts remain supported.

These checks apply before request/thread rows, totals and pages, including
response metadata. They validate identity and entity authority, not current
operational eligibility: archived, voided or disputed history is not hidden
merely because it cannot be executed again. Arbitrary narratives, hosted identity acceptance and representative performance
remain open. No historical data is repaired by reading it.


### Linked re-ask request authority (QA branch, not deployed)

Admin/MCP stored request reads follow explicit `reask_of_request_id` values in
request and response metadata. Every reachable request and its thread siblings
must pass the existing source/domain/ownership checks in the same organization
and entity. Missing, malformed or forbidden links withhold the request/thread
before rows, totals and pagination. Readable self-links and mutual cycles are
supported: traversal deduplicates visited stored rows rather than expanding the
SQL builder recursively. Virtual execution metadata uses the same policy even
when it has no request ID or thread columns.

This validates stored read authority, not whether a re-ask completed successfully
or whether free-text narratives are safe. It does not repair references. Use
authorized source/configuration recovery rather than editing history to force a
read. Hosted identity, representative performance and arbitrary narrative
acceptance remain open.


### Missing loan GL account recovery

If loan disbursement or repayment cannot resolve its loans-receivable account,
the Bank service creates a configuration task with `action=create_account` and
`origin=bank_missing_loan_account_v1`. It asks for an asset/loan-receivable account
and preserves any suggested existing account number as a hint. Review the chart
first; a hint is not approval to create a duplicate, change accounting policy or
post the loan.

The source bank must exist in the current entity, and creator instance identity
is retained for configuration-completion callbacks. Request and dispatch event
are written in one transaction (or the caller's enclosing transaction), so an
event-write failure leaves no orphan task. Active requests are reused only for
the same creator, entity, bank and loan operation; separate creators keep their
own callbacks. An advisory transaction lock serializes competing creations.
The run cache is populated after successful writes, so failed attempts remain
retryable and another bank is not accidentally suppressed. Callback re-runs keep
the existing loop guard; unresolved configuration needs review rather than
another automatic escalation.

Admin/MCP request visibility follows the shared current-assignment and certified
entity-scope policy. It does not recursively traverse the source bank or returned
account to decide whether an assigned task is visible. Reading or acting on the
underlying business records retains normal business permissions and entity scope.
Completion separately requires the existing executed
account-create workflow evidence and a current active, non-header asset account
with subtype `loan_receivable`; wrong, inactive or foreign source/configuration
cannot complete the task. A suggested existing account alone is not an executed
creation receipt; do not create a duplicate merely to obtain completion.

Task creation performs no GL/account mutation. Hosted dispatch, approved account
creation, callback delivery and subsequent loan posting remain separate acceptance
steps; the isolated checks do not claim those end-to-end effects occurred.


## Close evidence update (b1, awaiting deployment)

Excluded bank lines retain the current failing close outcome. Evidence shows each amount, reason/blank reason, GL link, the same posting-bridge verdict used by statement controls, statement finalizability, and signed totals by account/currency. Exclusion leaves an existing GL link intact. A valid bridge is not a declaration that the line is resolved. AR-484 corrects the exclusion operation's SQL parameter typing without changing this close policy.


### Bank-line refusal evidence (AR-273, local; not deployed)

For `bank_statement_line.match`, `unmatch` and `exclude`, a direct or immediately
executed request can return a confirmed refusal after its own complete database
transaction has successfully rolled back. The original reason is preserved. The
proof applies only to that organization, entity, line, operation and payload;
a matching request identity replays its retained receipt without executing again.

This means the attempted line/parent-statement changes did not commit. It does
not mean a previous match, exclusion or posting disappeared, nor that no workflow
or audit record exists. A refusal must not be interpreted as a successful exclusion
or as permission to reverse a prior posting.

Nested savepoints, failed rollback/commit acknowledgements, database faults,
cancellation and failures after commit do not establish this proof. An unconfirmed
receipt write remains `posting_unknown`; preserve the identity and investigate
known source/workflow evidence.

Delayed approvals can also save this bank-specific proof with the rejected workflow
and its execution-failure audit action. A definitive approval response requires an
acknowledged outer receipt commit; a nested savepoint alone cannot establish that.
Same-intent Base, MCP and dashboard submission retries verify the exact saved
workflow, organization, operation, entity, line and payload before returning the
original reason without execution. Missing, malformed or contradictory receipts
remain unknown. An ordinary failure message or arbitrary refusal flag is not proof.

Country/accountant choices, matching/exclusion policy and close treatment remain
in their existing configuration. Saga is optional. No historical repair or automatic
claim reset is introduced.

Intermediate-review integrity: a non-final review assigns the next pending task;
it does not automatically execute the bank operation. If pending steps exist but
cannot be resolved through the saved workflow definition and organization, task
advancement is refused before execution. The current review decision rolls back;
resolve the workflow configuration through an authorized process before retrying.
This error is not a bank rollback receipt. Initial workflows with no pending steps
can still execute automatically; final-review bank failures use the saved proof
and recovery described above.

### Connector observation evidence

Authorized bank statement line and card transaction detail can return
`connector_observations` from the stored Revolut sync. `not_captured` means no
observation is available, not that no bank movement occurred. The projection is
bounded to 100 recent observations with `truncated` when more exist.

Treat `exact` as source amount/currency/type/account/lifecycle agreement only.
It is not posting authority, a cross-connector duplicate identity, date validation
or permission to close. Card timestamps remain explicitly unverified. All first
revision provider-account identities remain incomplete. Conflicts and ambiguous
legacy matches are evidence for investigation; do not silently select a source.
A failed sync may still have a durable run/audit record, and an observation does
not establish completion of the whole sync. External agents use the same detail
projection and shared authorization as built-in agents.

## Coverage evidence storage (local prerequisite, not activated)

Migration 753 and a private repository retain immutable, unattested coverage
snapshots, invalidations and history. This does not accept new coverage declarations,
change statement statuses, alter GL, switch current readers or make period close
pass. Existing coverage behavior remains in place. Country/accountant/business
requirements remain editable policy work in AR-477; full writer adoption remains
AR-478 work. Do not treat `legacy_migration` provenance as an attestation or proof
that workers were drained. Final backfill needs a separately reviewed deployment
controller and verified worker-output manifest; no production adapter exists yet.

Bank review notifications with no configured provider remain deferred, without a provider attempt. Each pending job receives its unavailable reason independently. If a stale feed fails the retained receipt guard, that job stays unchanged and other valid jobs can still be annotated. Do not interpret this reason as delivery or bypass the normal authority/content recheck when the provider returns.

Native lifecycle execution rechecks current run/definition authority and entity
scope. Its internal zero-key sentinel does not represent an API key or grant
permission; external key callers remain subject to current stored-key validity.


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

Automatic recomputation (after a line match, exclusion or unmatch) leaves a
`locked` or `voided` statement exactly as stored, including its retained controls
and reconciliation timestamps: passing checks do not unlock it and failing checks
do not rewrite its history. Manual finalization refuses both states too.
Recomputing an already reconciled statement with unchanged valid evidence keeps
its original `reconciled_at` and `reconciled_by`; a newly unresolved line still
reopens an unlocked statement and clears those fields.

Statement `metadata` must be a JSON object. A legacy array or scalar cannot prove
source coverage: finalization reports `source_coverage_unknown`, also with
`force=true`, and recomputation neither finalizes nor rewrites the malformed
metadata. Repairing that evidence is a separate, authorized action.

### Plaid prospective card routing

New Plaid feed sources with explicit original-description card evidence route
through the shared governed card importer only for a unique card in an activated
account/program in the same entity. Original description masked digits are
evidence; merchant names and payment channels are not card identity. Existing
bank imports stay in place. Unknown/ambiguous attribution remains bank evidence
with a routing reason, never a guessed employee. Refunds retain their inflow
sign. Descriptive enrichment is audited without rewriting imported sources.
Imported card financial/identity corrections or removals refuse the delta for explicit review;
never reset a cursor or reimport the movement to work around this protection.
See `docs/GUIDES/GUIDE_CONNECT_PLAID.md`, “Prospective Plaid card imports”, for
configuration, source ownership and recovery details.
