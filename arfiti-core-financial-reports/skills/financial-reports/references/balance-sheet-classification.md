# Balance Sheet Classification

The server classifies the balance sheet; this reference explains what it returns and what the plugin adds. Never classify accounts by number or name.

## What the server returns

`generate_report("balance_sheet", {"legal_entity_id": ID, "as_of_date": "YYYY-MM-DD", "report_contract": 1})`:

- `rows`: one statement line per account, with `section` (`asset`, `liability`, `equity`), `account_type`, `account_subtype` and `display_amount` (presentation sign: assets, liabilities and equity positive in their sections). Two synthetic equity rows carry the unclosed results: `current_year_result` and `prior_years_unclosed` (`synthetic_kind`).
- `totals`: `assets`, `liabilities`, `equity`, `current_year_result`, `prior_years_unclosed`, and `groups`: one total per section and subtype. All totals cover the full selection.
- `details.reconciliation`: the server's assets = liabilities + equity verdict (`tied`, `difference`, `unavailable`).
- `details.earnings_bridge`: fiscal year, its start date, performance, closing transfers and unclosed results for the current and prior years.
- `details.comparison`: the comparison balance sheet when `comparison_mode` was requested.

Account subtypes come from the system catalogue (`account_subtype` on each account, `query("account", filters={"account_subtype": ...})`). An account without a subtype is a data gap the server reports; ask the user to set the subtype rather than placing the account yourself.

## Current and non-current: plugin policy

The catalogue has no current/non-current flag, and the split is a presentation choice. The plugin's ratios use the subtype lists in `scripts/ratio_policy.json` (`current_asset_subtypes`, `current_liability_subtypes`, `inventory_subtypes`, `cash_subtypes`). That file is example policy: a firm or client edits it. The formatter labels every ratio built on it.

## Checks

- Assets = liabilities + equity: use the server verdict. It is a pass only when the status is `tied` and quality is complete. For `difference` or `unavailable`, report it with the evidence gaps; don't recompute.
- The current-year result covers the fiscal year to the as-of date, from `earnings_bridge.fiscal_year_start`. It equals a P&L only for that same window.
- If quality is incomplete, the unavailable amounts are `null`: show "Unavailable" and the gap's message, and draw no conclusion from the remaining figures.
