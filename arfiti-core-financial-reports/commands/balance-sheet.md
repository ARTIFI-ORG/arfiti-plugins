---
name: balance-sheet
description: Present the server's balance sheet with its reconciliation verdict, earnings bridge, optional comparison and labelled liquidity ratios. Uses format_balance_sheet.py.
---

# Balance Sheet

Presents the server's balance sheet as of a date. Sections and subtype groups come from the server's classification; the formatter adds labelled ratios.

## Usage

```
/arfiti-core-financial-reports:balance-sheet
```

Requires Python 3.9+ (`python3 --version`) when a formatter runs.

## Rules

- Add `"report_contract": 1` to every `generate_report` call and save the result **unchanged** as JSON. Never retype amounts, re-classify accounts, sum rows into totals or round them.
- A `null` amount is **Unavailable**, never zero. Show every evidence gap, warnings included.
- If the result is `success: false`, show its message (for example `REPORT_SCOPE_FORBIDDEN`: the user has no access to that entity) and stop.
- If the formatter exits with code 2, show its reason and fix the request; do not work around it.

## Step 1: Fetch

Ask for the legal entity and as-of date, and whether a comparison is wanted.

```
generate_report("balance_sheet", {"legal_entity_id": ID, "as_of_date": "YYYY-MM-DD", "report_contract": 1})
```

For a comparison add `"comparison_mode": "prior_year"`, or `"comparison_mode": "prior_period", "comparison_period_from": "YYYY-MM-DD"` (the comparison is as of the day before that date). Save the result to `/tmp/balance_sheet_{ENTITY_ID}_{DATE}.json`.

## Step 2: Format

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/format_balance_sheet.py" --input /tmp/balance_sheet_{ENTITY_ID}_{DATE}.json --output /tmp/balance_sheet_report.md --entity-name "ENTITY NAME"
```

Example input: `scripts/examples/balance_sheet.json`.

## Present

Show the generated markdown. The check row is the server's verdict: "Tied" only for a complete report the server reconciled. On a difference or an unavailable verdict, say so and list the gaps; do not explain it away.

The current-year result in equity covers the fiscal year to the as-of date (see the earnings bridge). Compare it with a P&L only for that same window.

Ratios use `scripts/ratio_policy.json`, which is example policy: describe a ratio against "the example band", never as "healthy" or "weak".
