---
name: aged-receivables
description: Present the server's AR aging with certification, overdue (1+ days) figures, credits, optional days sales outstanding over the real period, and labelled example follow-up. Uses format_aging.py.
---

# Aged Receivables

Presents the server's accounts receivable aging as of a date. Buckets, totals, overdue and the control-account tie-out are the server's.

## Usage

```
/arfiti-core-financial-reports:aged-receivables
```

Requires Python 3.9+ (`python3 --version`) when a formatter runs.

## Rules

- Add `"report_contract": 1` to every `generate_report` call and save the result **unchanged** as JSON. Never retype amounts, re-classify accounts, sum rows into totals or round them.
- A `null` amount is **Unavailable**, never zero. Show every evidence gap, warnings included.
- If the result is `success: false`, show its message (for example `REPORT_SCOPE_FORBIDDEN`: the user has no access to that entity) and stop.
- If the formatter exits with code 2, show its reason and fix the request; do not work around it.

## Step 1: Fetch

```
generate_report("ar_aging", {"legal_entity_id": ID, "as_of_date": "YYYY-MM-DD", "report_contract": 1})
```

For days sales outstanding, also fetch an income statement whose period ends on the aging date (for example the last 90 days or the year to date):

```
generate_report("income_statement", {"legal_entity_id": ID, "start_date": "YYYY-MM-DD", "end_date": "AGING-DATE", "report_contract": 1})
```

## Step 2: Format

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/format_aging.py" --input /tmp/ar_aging_{ENTITY_ID}_{DATE}.json --output /tmp/ar_aging_report.md --entity-name "ENTITY NAME" [--income-statement /tmp/income_statement_{ENTITY_ID}.json]
```

Example input: `scripts/examples/ar_aging.json`.

## Present

Show the generated markdown. Overdue means 1 or more days past due, as the server counts it. Amounts are amounts owed: positive is owed by the customer, and a negative customer total is a credit or unapplied amount that stays visible and is listed for review, whatever the overall total nets to. A customer whose total is unavailable is listed separately, as neither.

If the aging is not certified, say so first: its totals do not agree with the control account or some payment applications are incomplete.

The follow-up column is example policy from `scripts/ratio_policy.json`, which the firm edits. Present it as suggestions; this plugin sends no reminders.
