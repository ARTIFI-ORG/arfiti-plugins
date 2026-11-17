---
name: arfiti-account-choice
description: Choose the ledger account for one purchase in Arfiti - a card charge the bank agent posts or a line of a supplier bill - from the records, in a fixed order of authority (client rule, vendor default, vendor history, vendor notes, the chart of accounts), and say which evidence decided it. Use whenever a posting needs an expense, cost or asset account that the caller's skill does not already fix.
---

> **Without a roster (Cowork, Claude Code).** Where this skill hands work to the
> master-data or configuration agent, no such agent is available: follow the
> `arfiti-master-data` or `arfiti-configuration` skill in this plugin yourself, with
> the same brief, and come back here with its result block. Step 0 (confirm the
> organisation) still applies: your own sign-in decides which organisation you are in.

# Choose the account for a purchase

One procedure for every agent that books a purchase: the bank agent in card
mode and the bill agent, and a person following either in Cowork. It is
written once so a card charge and the bill for the same purchase are decided
the same way.

It chooses an account. It does not post, create a vendor or change master
data; the calling skill does that. Plain bank lines (vendor payments, customer
receipts, transfers, fees) do not come here: their counterpart is the payable,
the receivable, the other bank account or a posting profile.

## What you need before you start

- `legal_entity_id` X and what is being bought: for a card charge the
  merchant name, category (`merchant_category_code` and description), city
  and country, amount, currency, date, cardholder, and the receipt if one is
  attached (`get_entity("card_transaction", C)`, then `read_attachment`); for
  a bill line the line text, the document and the supplier.
- The vendor, if there is one. Find it first, the way the calling skill says
  (tax or registration number, then name and aliases). A merchant name is
  often a trading name plus a city: search the distinctive part
  (`query("vendor", query="<name>", filters={"legal_entity_id": X})`), and
  compare country. Exactly one match: use it. No vendor yet is normal for a
  first card charge; go on without one. The calling skill creates the vendor
  through the master-data agent before it posts.
- The client rules: the stored rules the calling skill read with
  `query("agent_rules", ...)`, plus any `client_rules` block the session was
  given and the agent definition's `managed_agent_rules`.
- The chart, loaded once per session:
  `query("account", filters={"legal_entity_id": X, "is_active": true})`
  (page with `offset` until a short page). Classify by `account_type` and
  `account_subtype`, never by number ranges.

## Which accounts are allowed

- **Card charge:** an `expense` or `cogs` account. The posting is
  provisional: when the bill or receipt for the purchase is posted, settlement
  moves the charge out of this account and the bill carries the final
  account. So an equipment purchase on a card still goes to the expense
  account that best describes it now; do not post a card charge to an asset
  account and do not ask whether it is a capital item.
- **Bill line:** `expense` or `cogs`, or the asset subtypes
  `fixed_asset_cost`, `intangible_asset`, `right_of_use_asset`,
  `prepaid_expense`. An asset account needs a client rule or the vendor's
  history behind it; the calling skill's threshold rule decides when to ask.

Never a header account, an inactive account, or one outside the allowed set.

## Order of authority

Stop at the first step that gives one allowed account. Note the step and the
evidence; you report them.

1. **Client rule.** A rule that names the account for this vendor, merchant or
   kind of purchase.
2. **Vendor default.** `get_entity("vendor", V)`: `default_expense_account_id`
   set means every purchase from this vendor uses it (a pin).
3. **Vendor history.** What this vendor's posted purchases used:
   `query("transaction_line", filters={"legal_entity_id": X, "vendor_id": V}, limit=50)`
   and, for cards, the card expenses of the same merchant
   (`query("card_transaction", query="<merchant>", filters={"legal_entity_id": X})`,
   then `get_entity("transaction", <posted_transaction_id>)` for the debit
   account). Consistent history for the same kind of purchase decides. Mixed
   history (a shop that sells many things) does not; go on.
4. **Vendor notes.** The vendor record's notes or policy text, when it says
   what this vendor's purchases are and where they go.
5. **Same kind of purchase elsewhere.** When the vendor is new, what posted
   purchases of the same kind used (for hosting: the other hosting vendors'
   card charges). Name the precedents you used. Two or more that agree
   decide; one alone supports step 6 but does not replace it.
6. **The chart.** What the merchant or line is, from everything you have: the
   merchant name and what that business sells, the category code, the
   receipt or document text and its `visual_evidence` (a logo or platform
   name shown only as an image), the amount, the cardholder. Match it to the
   account whose name and subtype describe that purchase. Decide only when one
   account clearly fits better than the others. "Other", "Miscellaneous" or
   "General" accounts are not a fit; they are what is left when nothing fits,
   and nothing is posted there without a client rule that says so.
7. **Fallback named by a rule.** A stored client rule that names the account
   for unclear purchases. No such rule: no account. A default account number
   in an agent definition's settings or a posting profile is not such a rule.

There is no learned merchant memory in the public tools today. Steps 2 and 3
are the memory: once a vendor exists and its purchases are posted against it,
the next purchase is settled there.

## When there is no answer

Do not guess and do not post. The calling skill raises a `question` task.

**Write the question for someone who does not know accounting.** The person
answering may be the cardholder or an office manager. Never ask "which
account" and never show account numbers as the choices. Ask what was bought
and what it was for, in plain words: "What was bought at Mustamae Elamusspa
on 25 October (83.20 EUR), and what was it for?" `title`: "What was this
purchase". Offer plain choices drawn from what the merchant could be (for a
spa: "Team event or staff benefit", "Client entertainment", "Personal, not a
company expense") plus the free answer. What you will do with each choice,
including the account you would use, goes in the option's note and the task
details, for the accountant who reads them later.

Ask too, even with a candidate account, when the purchase may not be a
company expense at all: a personal-looking purchase, a tax or loan payment, a
fine, a transfer to a person.

## After a person answers

Any answer is enough to act on. You asked a person, not an accountant:

- They name or choose an account: use it.
- They describe the purchase ("server hosting for CI", "team spa day"): that
  is new evidence. Run the order again with it; it settles at step 5 or 6.
- They say it is a company expense and leave the account to you ("post it to
  the right account", "whatever fits"): choose. Take the account that fits
  best from step 6, even if you would not have called it a clear fit before
  asking; the person has confirmed the purchase is legitimate and has handed
  you the choice. Report it as `judged` with your reason.
- They say it is not a company expense: post nothing, leave the line open and
  report it as the calling skill says.

Never answer a person's reply with the same question again, and never ask
them for an account. A second task is right only when the reply leaves open
whether the purchase is a company expense at all, or contradicts the
records; then ask that one thing.

Do not set the vendor's default account on your own: a default pins every
later purchase from that vendor. Ask the master-data agent to set it only
when the person or a client rule says this vendor always goes to that
account.

## What you report

For each purchase, one line in the calling skill's result:

```
account_choice: <subject> -> <account number> <account name> | step <n> <name> | evidence: <the rule, the vendor field, the precedent journals, or what the merchant sells> | <settled | judged>
```

`settled` for steps 1 to 3 and 7; `judged` for steps 4 to 6, so a person can
see which postings rest on your reading. No account: `account_choice:
<subject> -> none | closest: <accounts> | task <request_id>`.
