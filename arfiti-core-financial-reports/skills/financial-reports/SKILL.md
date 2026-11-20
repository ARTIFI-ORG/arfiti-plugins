---
name: financial-reports
description: Present standard financial reports from Arfiti's server reports — Balance Sheet, Profit & Loss, Cash Flow Statement, Trial Balance, AR/AP Aging, P&L by dimension and a Financial Summary. The server classifies, totals and reconciles; this skill presents those results without rebuilding them.
---

## Trigger

Activate when the user mentions: balance sheet, profit and loss, P&L, income statement, cash flow, trial balance, financial statements, financial summary, aged receivables, aged payables, aging report, AR aging, AP aging, dimension analysis, department P&L, project profitability, or cost center analysis.

## Prerequisites

Determine:
1. **Legal entity ID**: the entity to report on. A report on an entity outside the user's access returns `code: REPORT_SCOPE_FORBIDDEN`; say they lack access to that entity instead of retrying.
2. **Date or period**: as-of date (balance sheet, trial balance, aging) or start and end date (P&L, cash flow).
3. **Comparison**: prior period or prior year, if wanted.

## Core principle: the server report is the source of truth

Always request the exact report contract by adding `"report_contract": 1` to every `generate_report` call, and pass the result **unchanged** to the formatter scripts. The server already returns:

- rows classified by account type and **account subtype** (never by account number);
- totals over the **full selection** (`coverage.totals_scope`), even when only one page of rows is delivered;
- the functional currency and its precision (`currency.code`, `currency.decimal_places`);
- a completeness status and every evidence gap, warnings included (`quality`);
- reconciliation verdicts (`details.reconciliation`), the balance sheet's earnings bridge and the cash flow bridge.

Never retype amounts into a hand-built JSON, re-classify accounts, sum displayed rows into totals, round to two decimals, or turn a `null` amount into zero. A `null` is **Unavailable**; say so and show the gap's message. If the formatter refuses the input (exit code 2), show the reason; do not work around it.

Show every evidence gap, including warnings on a complete report (for example a defaulted business timezone). When `coverage.has_more` is true, the rows are one page: the totals still cover everything, but row detail is not complete until the next page (`coverage.next_cursor`) is fetched.

## Reports

| Command | Server call (add `"report_contract": 1`) | Formatter |
|---|---|---|
| `/balance-sheet` | `generate_report("balance_sheet", {legal_entity_id, as_of_date[, comparison_mode]})` | `format_balance_sheet.py` |
| `/profit-and-loss` | `generate_report("income_statement", {legal_entity_id, start_date, end_date[, comparison_mode]})` | `format_income_statement.py` |
| `/cash-flow` | `generate_report("cash_flow_statement", {legal_entity_id, start_date, end_date[, method]})` | none: present the server rows and bridge |
| `/trial-balance` | `generate_report("trial_balance", {legal_entity_id, as_of_date})` | none: present the server rows and totals |
| `/aged-receivables`, `/aged-payables` | `generate_report("ar_aging" \| "ap_aging", {legal_entity_id, as_of_date})` | `format_aging.py` |
| `/dimension-analysis` | one `income_statement` per dimension value with a `dimension_filter` | `format_dimension_analysis.py` |
| `/financial-summary` | `income_statement`, `balance_sheet` (as of the period end) and `cash_flow_statement` | `format_financial_summary.py` |

`comparison_mode` is `"prior_period"` or `"prior_year"` for the income statement; for the balance sheet `"prior_year"`, or `"prior_period"` with `comparison_period_from`. The comparison arrives inside the same result (`details.comparison`) with its own quality; the formatters show it as a Prior column. Without a comparison there is no Prior column; never present a missing comparison as zeros.

## Ties between reports

- **Balance sheet**: use the server's reconciliation verdict. It is a pass only when the status is `tied` and quality is complete.
- **P&L and balance sheet**: the balance sheet's current-year result covers the **fiscal year to the as-of date** (`details.earnings_bridge`). Compare it with the P&L only when the P&L period is that same fiscal-year-to-date window; for any other period, don't assert a tie.
- **Cash flow**: present the server's opening cash + operating + investing + financing + FX effect + other balance adjustments = closing cash and its reconciliation verdict. Don't recompute cash flow from balance sheet differences.

## Plugin analysis and policy

Ratios, margins, days outstanding and follow-up suggestions are this plugin's analysis, not server facts, and the output labels them so. The plugin's classification of current items, cash, receivables, payables and inventory, its example ratio bands and its example follow-up wording live in `scripts/ratio_policy.json`. That file is example policy for a firm to edit; never present its bands as universal ("healthy") or its follow-up steps as instructions. Days outstanding use the actual length of the income statement period, never a fixed 365.

Overdue means more than 0 days past due, as the server counts it (`totals.overdue`, every past-due bucket). Both agings report amounts owed: positive is owed by the customer (AR) or to the vendor (AP). A party with a negative total is a credit or unapplied amount, by its own sign, never by comparison with the overall total; it keeps its sign and stays visible.

Collection and payment suggestions are advice for the user to decide on. This plugin sends no reminders and schedules no payments.

## Discovery

- Accounts: `query("account", filters={"legal_entity_id": ID, "account_type": "asset", "account_subtype": "cash"})`. The filter fields are `account_type`, `account_subtype`, `is_active`, `is_header`, `allow_manual_entries`.
- Dimension types: `query("dimension_type")` gives the type names and IDs. Dimension values: `query("dimension_value", filters={"legal_entity_id": ID, "dimension_type_id": TYPE_ID})` returns a flat list. Each row carries `master_dimension_value_id`, `dimension_type_id`, `code`, `name` and `is_active`; inactive values remain valid for historical periods.
- Budgets: `variance_summary` needs `budget_version_id`; find the version first.

## Output

1. Run the formatter and present its markdown as it is. Its header carries the entity, dates (requested and effective), currency, business date and timezone source; then quality, gaps and coverage; then the figures.
2. Commentary refers to the figures shown. Mention unavailable figures and gaps first.
3. For trial balance and cash flow (no formatter), follow the same rules by hand: server rows and totals, the currency's decimal places, every gap, the server's verdict.

## Errors

- `success: false` with a `code`: show the server's message (for example `REPORT_SCOPE_FORBIDDEN`, or `report_unavailable` with its reason).
- No rows: say so; check the period and entity. An empty complete report shows real zeros.
- Formatter refusal (`REPORT_CONTRACT_REQUIRED`, `REPORT_CURRENCY_MISMATCH`, `REPORT_PERIOD_MISMATCH`, `REPORT_SCOPE_MISMATCH`): fix the request (add `report_contract: 1`, use the same entity, currency and period) and run it again.
