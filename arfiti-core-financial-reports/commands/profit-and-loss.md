---
name: profit-and-loss
description: Present the server's income statement with its subtype sections, server totals, optional comparison and labelled margins. Uses format_income_statement.py.
---

# Profit and Loss

Presents the server's income statement for a period. Sections, signs and totals are the server's; a refund on a cost stays a negative cost.

## Usage

```
/arfiti-core-financial-reports:profit-and-loss
```

Requires Python 3.9+ (`python3 --version`) when a formatter runs.

## Rules

- Add `"report_contract": 1` to every `generate_report` call and save the result **unchanged** as JSON. Never retype amounts, re-classify accounts, sum rows into totals or round them.
- A `null` amount is **Unavailable**, never zero. Show every evidence gap, warnings included.
- If the result is `success: false`, show its message (for example `REPORT_SCOPE_FORBIDDEN`: the user has no access to that entity) and stop.
- If the formatter exits with code 2, show its reason and fix the request; do not work around it.

## Step 1: Fetch

```
generate_report("income_statement", {"legal_entity_id": ID, "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "report_contract": 1})
```

For a comparison add `"comparison_mode": "prior_period"` or `"prior_year"`. Save the result to `/tmp/income_statement_{ENTITY_ID}_{START}_{END}.json`.

## Step 2: Format

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/format_income_statement.py" --input /tmp/income_statement_{ENTITY_ID}_{START}_{END}.json --output /tmp/income_statement_report.md --entity-name "ENTITY NAME"
```

Example input: `scripts/examples/income_statement.json`.

## Present

Show the generated markdown, then comment on the main movements using the figures shown.

Net income equals the balance sheet's current-year result only when the period is the fiscal year to date (the balance sheet's `details.earnings_bridge.fiscal_year_start` to its as-of date). For any other period, don't claim or test that tie.
