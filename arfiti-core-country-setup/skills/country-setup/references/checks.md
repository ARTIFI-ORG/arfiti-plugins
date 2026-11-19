# Checks

Three kinds of check, and what each one proves. Report them separately; never
summarise them as "all checks pass".

| Check | Who runs it | Proves | Does not prove |
|---|---|---|---|
| Machine validation | `submit(..., validate_only=true)` and the real submit | The payload has the fields, types, units, references and scope the operation accepts | That the value is right for the country or the company |
| Read-back | `query` after the write, compared field by field | What was saved | That it is legally correct |
| Research checks | You, before confirming with the customer | That each value has an official, dated source and fits the rest | Anything about what is saved |

A customer's confirmation is a decision, not a validation. Keep it, and keep
the evidence it was based on.

## Research checks — before presenting findings

Run these on the findings and show the result per check: passed, failed (with
the rows), or not applicable (with why).

**Sources**
- Every value has an official source (tax authority, ministry, official
  gazette, statute) and the date it was read. A secondary source (an
  accounting firm's summary, a news article) is labelled as such and the
  value stays `medium` or `low` confidence.
- `effective_from` is stated by the source. If the source states none, say so
  and ask the customer; do not use 1 January or today.
- No placeholder or made-up URL.

**Units**
- Tax code and withholding rates are percentage points (`19` for 19 %).
- Payroll rates and bracket rates are fractions (`0.19` for 19 %).
- Money amounts carry their currency.

**References**
- Every jurisdiction, filing form and registration names an authority that
  exists or is being created in the same session.
- Every payroll vendor line names a vendor and accounts the customer chose.
- Every withholding rule's account is an active account of the entity.

**Consistency**
- One active rule per thing: no two active withholding rules for the same
  payment type, no two overlapping reporting periods for the same authority,
  no two active per-diem rates for the same place and date.
- Rates that changed during the year are separate records with their own
  dates, the old one ended.
- Regional taxes are regional records; a national record does not stand in
  for a regional rate.

**Applicability** — no minimum counts
- Each area is configured, marked not applicable with the reason, or left
  open with the reason. Zero records is a valid answer when the area does not
  apply.
- Plausibility is a prompt to look again, not a rule: a rate far outside what
  the source suggests means re-reading the source, not changing the rate.

## Comparing with what exists

Before writing an area, compare the confirmed findings with the records that
are already there:

| Situation | Action |
|---|---|
| Same value, same dates | Nothing to write; report "already present" |
| Existing record, different value | Show both; the customer chooses keep, end-and-replace from a date, or correct (open records only) |
| Existing record the research did not find | Keep it; ask whether it still applies |
| Missing | Create after confirmation |

Never change an existing record because it differs from research alone.

## Read-back report

Per area, after writing:

```
Withholding tax rates — entity 12 (Example OÜ)
  created: 3     already present: 1     changed: 0
  refused: 1     (dividends — 0.2 refused as a likely fraction; waiting for the customer to confirm 20)
  left open: 1   (royalties — no official source found)
  read back: 4 active rules, values match the confirmation
```

Counts come from the read-back, never from the number of submissions sent.
