---
name: financial-summary
description: Present a one-page summary from the server's income statement, balance sheet and cash flow for one period, with labelled ratios and period-length days outstanding. Uses format_financial_summary.py.
---

# Financial Summary

Combines three server reports for one entity and period into a summary. All figures are the server's; ratios are labelled plugin analysis.

## Usage

```
/arfiti-core-financial-reports:financial-summary
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
generate_report("balance_sheet", {"legal_entity_id": ID, "as_of_date": "END-DATE", "report_contract": 1})
generate_report("cash_flow_statement", {"legal_entity_id": ID, "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "report_contract": 1})
```

## Step 2: Build the input and format

```json
{"income_statement": <result>, "balance_sheet": <result>, "cash_flow_statement": <result>}
```

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/format_financial_summary.py" --input /tmp/summary_{ENTITY_ID}_{END}.json --output /tmp/financial_summary.md --entity-name "ENTITY NAME"
```

The formatter refuses reports in different currencies or for different entities. Example input: `scripts/examples/financial_summary.json`.

## Present

Show the generated markdown, then a short narrative based on the figures shown.

Days sales and payables outstanding use the closing balance and the actual number of days in the period (a 30-day month is 30 days, not 365). They are an approximation, not an average balance. Ratio bands and the classification behind current, cash, receivables, payables and inventory come from `scripts/ratio_policy.json`, which is example policy: describe results against "the example band", not as universal judgements.
