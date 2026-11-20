---
name: aged-payables
description: Present the server's AP aging with certification, overdue (1+ days) vendors, amounts coming due, credits and optional days payables outstanding over the real period. Uses format_aging.py.
---

# Aged Payables

Presents the server's accounts payable aging as of a date. Buckets, totals, overdue and the control-account tie-out are the server's.

## Usage

```
/arfiti-core-financial-reports:aged-payables
```

Requires Python 3.9+ (`python3 --version`) when a formatter runs.

## Rules

- Add `"report_contract": 1` to every `generate_report` call and save the result **unchanged** as JSON. Never retype amounts, re-classify accounts, sum rows into totals or round them.
- A `null` amount is **Unavailable**, never zero. Show every evidence gap, warnings included.
- If the result is `success: false`, show its message (for example `REPORT_SCOPE_FORBIDDEN`: the user has no access to that entity) and stop.
- If the formatter exits with code 2, show its reason and fix the request; do not work around it.

## Step 1: Fetch

```
generate_report("ap_aging", {"legal_entity_id": ID, "as_of_date": "YYYY-MM-DD", "report_contract": 1})
```

For days payables outstanding, also fetch an income statement whose period ends on the aging date (its cost of sales is the basis).

## Step 2: Format

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/format_aging.py" --input /tmp/ap_aging_{ENTITY_ID}_{DATE}.json --output /tmp/ap_aging_report.md --entity-name "ENTITY NAME" [--income-statement /tmp/income_statement_{ENTITY_ID}.json]
```

Example input: `scripts/examples/ap_aging.json`.

## Present

Show the generated markdown. Amounts are the server's signed figures, as amounts owed: positive is owed to the vendor, a negative vendor total is a credit or unapplied payment, listed for review. The overdue list shows vendors with a positive or unavailable past-due amount. This holds whatever the overall total nets to; a vendor whose total is unavailable is listed separately, as neither.

The overdue list and the amounts coming due in 7, 14 and 30 days come from the server's documents. Whether and when to pay is the business's decision (terms, disputes, cash); don't tell the user to "pay immediately", and don't schedule or make payments from this command.
