# Cash Flow Statement

The server builds the cash flow statement; this plugin presents it. Don't rebuild it from balance sheet differences.

## What the server returns

`generate_report("cash_flow_statement", {"legal_entity_id": ID, "start_date": ..., "end_date": ..., "report_contract": 1[, "method": "direct"]})`:

- `details.method`: `indirect` (default) or `direct`. Both read the same per-entry section amounts, so the section totals agree.
- `rows`: lines by `section` (`operating`, `investing`, `financing`) with `movement_label`, `amount`, `row_kind` (`line` or `account`), `parent_row_id`, `cash_flow_line` and up to 20 `evidence_refs`. On the indirect basis operating starts from net income and adds the named components (depreciation and amortisation, gains and losses on disposal, working capital changes, other non-cash items, reviewed placements).
- `totals`: `opening_cash`, `operating`, `investing`, `financing`, `fx_effect_on_cash`, `other_cash_balance_adjustments`, `net_cash_flow`, `closing_cash`.
- `details.reconciliation` and `details.bridge`: whether opening + flows + FX + other adjustments = closing is proved (`tied`), disproved (`difference`) or not provable (`unavailable`).
- `details.unresolved_movements`: entries the server withheld (for example an account without a subtype, or a data defect), with blocking gaps.

Classification is by each account's subtype (`cash_flow_class`, `cash_flow_line`); there are no transaction-type rules.

## Presentation

1. Operating, investing and financing sections with the server's line labels and amounts.
2. The bridge: opening cash, the three sections, FX effect, other balance adjustments, closing cash, with the server's verdict.
3. Unresolved and non-cash movements, if any, with the gap messages.

A cash flow under a dimension selection covers whole transactions and publishes no opening or closing cash or bridge; say so if the user asked for one.

## Analysis

Operating cash flow against net income, large investing outflows and financing movements are worth commenting on. Present them as observations about the figures, not universal rules ("healthy", "concerning").
