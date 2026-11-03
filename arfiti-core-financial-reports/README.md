# Arfiti Financial Reports

A financial reporting suite for Arfiti: Balance Sheet, Profit and Loss, Cash Flow, Trial Balance, AR and AP Aging, Dimension Analysis and an executive Financial Summary. It works with any chart of accounts by discovering account properties from the data instead of assuming account numbers, and formats the reports with deterministic scripts so the numbers are never re-typed by the model.

## Requirements

- An Arfiti organisation and a user who can sign in to it.
- The **Arfiti** connector (`https://mcp.arfiti.com/streamable/mcp`). This plugin's `.mcp.json` points at the same server, so installing both shows one set of tools.

## Commands

| Command | What it does |
| --- | --- |
| `/balance-sheet` | Balance Sheet with classification validation, comparative periods and liquidity ratios. |
| `/profit-and-loss` | Profit and Loss with margin analysis and period-over-period comparison. |
| `/cash-flow` | Cash Flow Statement by the indirect method, reconciled to the balance sheet. |
| `/trial-balance` | Trial Balance with debit/credit validation and unusual balance detection. |
| `/aged-receivables` | AR aging with collection priorities, DSO and concentration risk. |
| `/aged-payables` | AP aging with payment scheduling and early payment discount analysis. |
| `/dimension-analysis` | P&L by department, project or cost centre with profitability ranking. |
| `/financial-summary` | Executive summary combining balance sheet, P&L, cash flow and ratios. |

## What it runs and sends

This plugin contains skills, commands and six helper scripts under `scripts/`. All are Python 3, standard library only, and none opens a network connection or starts another process.

- `format_aging.py`, `format_balance_sheet.py`, `format_dimension_analysis.py`, `format_financial_summary.py` and `format_income_statement.py` each read the JSON report file you pass with `--input`, validate it, and write a formatted markdown report to the path you pass with `--output` (creating its parent folder if needed). `format_aging.py` also takes `--type ar|ap`.
- `report_evidence.py` is a helper imported by those five scripts. It reads nothing from disk and writes nothing. It renders unavailable amounts as "Unavailable" instead of inventing totals.
- The `input_schema_*.json` files describe the input shape and are never executed.

Report data is read from your Arfiti organisation through the connector's read tools.

It sends data to the Arfiti MCP server over the authenticated connector. It runs no code of its own that contacts any other service. The scripts write only the markdown files you ask for, at the path you give.

## Support

support@arfiti.com · Documentation: https://arfiti.com/plugins/arfiti-core-financial-reports
