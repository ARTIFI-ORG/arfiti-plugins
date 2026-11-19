# Income Statement Structure

The server classifies the income statement by account subtype (`system.account_subtypes.income_statement_section`); this reference explains what it returns.

## What the server returns

`generate_report("income_statement", {"legal_entity_id": ID, "start_date": ..., "end_date": ..., "report_contract": 1})`:

- `rows`: one line per account with `section` (`revenue`, `cogs`, `operating_expenses`, `other_income`, `finance_costs`, `income_tax`, or a section the server adds later), `balance_signed` (debit minus credit) and `display_amount` (income positive, cost positive).
- `totals`: `revenue`, `cogs`, `gross_profit`, `operating_expenses`, `operating_profit`, `other_income`, `finance_costs`, `income_tax`, `net_income`, over the full selection.
- `details.comparison`: the comparison period when `comparison_mode` (`prior_period` or `prior_year`) was requested.
- `calculation.closing_entry_treatment`: closing transfers are excluded from performance.

## Presentation rules

- Keep the server's sections and order. `other_income` sits below operating profit. Operating gains are inside revenue when the subtype says so; don't move lines between sections.
- A credit on a cost account (a refund, rebate or contra amount) is a negative cost. It stays negative and increases profit; never show it as a positive cost or a dash.
- Use the server totals. Don't recompute gross, operating or net profit.
- Margins (gross, operating, net, each divided by revenue) are plugin analysis. They are unavailable when revenue is zero or an amount is null.
- A nature-of-expense or function-of-expense layout, or a country's statutory format, is policy for the firm. Present it from the server's subtypes in a separate, labelled view if asked; the server statement stays the source.
