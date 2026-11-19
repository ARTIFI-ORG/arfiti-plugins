---
name: country-setup
description: Configures a live Arfiti company for its country — tax codes, tax authorities and jurisdictions, registrations, filing forms and calendars, withholding rates, payroll taxes and expense rates — by reading what the company already has, researching the gaps from official sources, confirming each value with the customer, writing it through the Arfiti submit gateway and reading it back. Also guides the customer in authoring their own country plugins (payroll calculator, VAT declaration). Use for "set up <country>", "configure tax for my entity", "add withholding rates", "fix our filing calendar", "author a payroll plugin for <country>".
---

# Country setup for a live company

This skill configures the customer's **own, live company** through the Arfiti
connector. Every value goes through `submit`, where validation, the entity
scope, approval rules and the audit trail apply, and is read back with `query`.
Nothing is written to a file in a code repository, and installing the plugin
configures nothing by itself.

Country policy — which taxes apply, their rates, thresholds and deadlines,
which account each amount posts to — is the customer's, researched with
sources and confirmed with them. Arfiti stores and validates it; it does not
decide it. Never fill a gap with a guess, a "typical" rate, a national rate
standing in for a regional one, a minimum number of entries, or an account
picked by its number.

## Trigger

Activate on: set up a country, country setup, configure tax for an entity,
VAT/GST/sales tax setup, withholding tax setup, payroll tax setup, filing
calendar or tax reporting periods, per-diem or mileage rates for a country,
author a country plugin, or `/set-up-country`, `/author-country-plugin`.

## Before you start

1. **Which organisation and entity?** `query("legal_entity")`. Confirm the
   legal entity, its country, functional currency and VAT registration with
   the customer. Organisation-wide records (tax codes, authorities,
   jurisdictions, filing forms, payment classifications, payroll taxes) are
   shared by every entity in the organisation; entity records (registrations,
   reporting periods, withholding rates, payroll vendor lines, per-diem and
   mileage rates) belong to one entity. Say which kind each change is before
   making it. `references/operations.md` lists the scope of each.
2. **Is onboarding complete?** `get_onboarding(action="check_status")`. While
   onboarding is open, `submit` accepts master data — of the country setup
   types, `tax_code`, `tax_authority`, `tax_jurisdiction`, `tax_registration`,
   `account` and `vendor` — and refuses the rest (withholding rates, reporting
   periods, filing forms, payroll taxes, expense rates…) with
   `organization_not_onboarded`. Finish onboarding first, or limit the session
   to the accepted types and say so.
3. **What did onboarding leave open?**
   `get_onboarding(action="get_checklist", status="skipped")` — without a
   category filter, because country tasks sit under `tax`, `payroll` and
   `master_data` (expense rates). Each task's `result` says what its last
   onboarding-wave run reported (a `rerun_onboarding_task` does not update
   it, so read the records themselves before deciding): `needs_configuration: true` with the `section` and `reason` means
   the country had no shipped data and nothing was generated — a gap to fill;
   `needs_configuration: false` means the section was deliberately empty (not
   applicable). Arfiti ships onboarding data for 37 countries. Shipped data is
   not certified either: its rates and dates were not re-verified per country,
   so review it with the customer too.
4. Read `references/operations.md` (operations, scope, units, read-back) and
   `references/checks.md` (what to check, and what a check does and does not
   prove) before the first write.

## The flow

Six steps, in order. Never skip the read-back: a submit receipt is not proof
of what was saved.

### 1. Read what exists

For each area in scope, read the current records before proposing anything —
the read queries are in `references/operations.md`. Show the customer one short
table per area: what exists, what is missing, what looks inconsistent (an
expired rate still active, a filing form naming no authority, a period
without a due date, two active withholding rules for one payment type).

Existing records are the customer's configuration. Never replace, end or
delete one without their explicit yes for that record.

### 2. Research the gaps

Research the areas the customer wants configured with the `tax-researcher` and
`payroll-specialist` subagents in parallel, or yourself with web search when
the agents are not available. Each finding carries:

- the value and its unit;
- the jurisdiction it applies to (national, state, region, municipality);
- `effective_from`, and `effective_to` when known;
- the official source (URL, page or section) and the date it was read;
- confidence — `high` only when an official source states the value directly;
- what depends on the company (registration, size, sector, employee
  circumstances) and is therefore a question for the customer.

A value without an official source, or one only an accountant can decide
(which account, which method, whether an exemption applies), is a question,
not a finding. A case the platform cannot store or calculate is reported as
unsupported (see "What core does not do").

### 3. Confirm with the customer

Present the findings next to what exists, area by area, with sources. The
customer confirms, corrects or excludes each row. An area that does not apply
(no VAT registration, no employees, no non-resident payments) is recorded as
not applicable, not filled. A company outside VAT may still owe sales or other
indirect taxes; ask rather than assume there is nothing.

Accounts are the customer's choice from `query("account")`, filtered by
`account_type` and `account_subtype` (for example a liability with subtype
`payroll_withholding` for a payroll tax payable). Never pick or create an
account because of its number. If the account they want does not exist,
propose `account.create` with the type and subtype and let them choose the
number.

Keep a note of each confirmation (who, what, when) for the hand-off.

### 4. Apply through the gateway

For each confirmed record:

1. Read the operation's fields:
   `get_submissions(action="schema", object_type="<type>", operation="<op>")`.
2. Check the payload with `submit(..., validate_only=true)`. This is the
   machine validation; a payload that fails it is not sent.
3. Submit. Where the operation has `metadata`, record the source and the
   confirmation in it (`source_url`, `source_read_on`, `confirmed_by`).
4. Report the receipt as it came back: created, refused (with the reason),
   waiting for approval (with the request), or replayed —
   `idempotent_replay: true` returns the first result and writes nothing new.

Order matters where records refer to each other: authorities before
jurisdictions, filing forms and registrations; tax codes before their rate
components; accounts and vendors before the payroll vendor lines and
withholding rates that name them.

Stop at the first unexpected refusal in a chain and show it. Do not work
around it with a different operation.

### 5. Read back

After each area, query it again and compare field by field with what was
confirmed. Report counts from the read-back — created, already present and
unchanged, changed, refused, left open — not the number of submissions. A
difference between the read-back and the confirmation is a finding to show,
never a reason to re-submit silently.

### 6. Hand off

Give the customer:

- what was configured, per area and entity, with record ids;
- what was left open and why (unconfirmed, not applicable, unsupported, needs
  an accountant);
- the sources used and when they were read;
- what has to be built as a country plugin (next section).

## What core does not do — the country plugin does

Arfiti's core stores country data. Two things are left to the customer's
country plugin:

- **Payroll arithmetic.** No core code calculates income-tax brackets or
  social contributions. `payroll_tax_jurisdiction.tax_brackets` and the rates
  are reference data; a payroll run takes its amounts from the caller. The
  country's payroll calculator plugin does gross-to-net.
- **The VAT return's box mapping.** No core operation stores it. The country's
  VAT declaration plugin maps tax codes to the form's boxes (the Estonian pack
  maps them to KMD lines itself).

When the customer needs either, offer `/author-country-plugin`
(`references/country-plugins.md`).

## Correcting what is already there

- **A rate changed:** for dated records (withholding, payroll taxes, per-diem,
  mileage) add a record from the new `effective_from` and end the old one
  (`effective_to`, or `withholding_tax_rate.deactivate`), so history keeps the
  old rate. Tax codes have no dates: create a new code for the new rate and
  deactivate the old one when it stops being used; posted documents keep the
  code they were posted with. Do not overwrite a rate in place.
- **A wrong reporting period:** `tax_reporting_period.update` and `.delete`
  work on open periods. A locked or filed period is refused; a period a tax
  return refers to keeps its dates and is never deleted.
- **Account filing categories** live in the account's `metadata`.
  `account.update` replaces the whole `metadata` object: read the account,
  merge the change into its current metadata, send the merged object, and
  never drop keys you did not mean to change.
- **Re-running an onboarding task** (`legal_entity.rerun_onboarding_task`,
  owner or admin only) keeps existing records and filing categories and reports what it created
  and what it kept. Read back after it anyway; a re-run is not a second
  application of new values.

## Error handling

- **Refused by validation:** show the field and the message, fix the payload
  with the customer, check with `validate_only` again.
- **Waiting for approval:** say who approves and where. Do not resubmit.
- **Conflicting sources:** show both with their dates; the customer decides,
  and the chosen source goes into `metadata`.
- **No official source:** leave the value open and say so.
