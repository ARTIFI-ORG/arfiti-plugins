---
name: cash-flow
description: Present the server's cash flow statement with its opening-to-closing cash bridge and reconciliation verdict. No formatter; the server's rows and totals are shown as returned.
---

# Cash Flow Statement

Presents the server's cash flow statement for a period. The server classifies every movement by account subtype and proves the bridge from opening to closing cash.

## Usage

```
/arfiti-core-financial-reports:cash-flow
```

Requires Python 3.9+ (`python3 --version`) when a formatter runs.

## Rules

- Add `"report_contract": 1` to every `generate_report` call and save the result **unchanged** as JSON. Never retype amounts, re-classify accounts, sum rows into totals or round them.
- A `null` amount is **Unavailable**, never zero. Show every evidence gap, warnings included.
- If the result is `success: false`, show its message (for example `REPORT_SCOPE_FORBIDDEN`: the user has no access to that entity) and stop.
- If the formatter exits with code 2, show its reason and fix the request; do not work around it.

## Step 1: Fetch

```
generate_report("cash_flow_statement", {"legal_entity_id": ID, "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "report_contract": 1})
```

The method defaults to indirect; pass `"method": "direct"` if asked. Cash flow has no comparison mode: for a prior period, make a second call.

## Step 2: Build the statement from the result

- Header: entity, `dates.effective` (and `dates.requested` if different), `currency.code`, `details.method`.
- Quality and every gap from `quality.evidence_gaps`; partial delivery from `coverage`.
- Rows: group by `section` (operating, investing, financing) in the server's order. Show `row_kind: "line"` rows with `movement_label` and `amount`; account rows (`row_kind: "account"`) are detail under their `parent_row_id`.
- Totals: the server's `opening_cash`, `operating`, `investing`, `financing`, `fx_effect_on_cash`, `other_cash_balance_adjustments`, `net_cash_flow`, `closing_cash`.
- Verdict: `details.reconciliation.status` (`tied`, `difference` with its amount, or `unavailable`) and `details.bridge.status`.
- List `details.unresolved_movements` and `details.non_cash_movements` if present.

Format amounts with `currency.decimal_places`; show a `null` as Unavailable.

## Present

Present the bridge as opening cash + operating + investing + financing + FX effect + other balance adjustments = closing cash, with the server's verdict. Don't recompute cash flow from balance sheet differences; if the user wants a cross-check, closing cash equals the balance sheet's cash accounts only for an unfiltered report.

Comment on operating cash flow against net income (from the same period's income statement) as analysis, not as a universal "healthy" rule.
