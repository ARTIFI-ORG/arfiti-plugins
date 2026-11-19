# Arfiti Financial Reports

A financial reporting suite for Arfiti: Balance Sheet, Profit and Loss, Cash Flow, Trial Balance, AR and AP Aging, P&L by dimension and an executive Financial Summary. The server reports classify, total and reconcile the figures; this plugin requests their exact contract (`report_contract: 1`) and presents the results unchanged, with deterministic scripts, so no amount is retyped, re-rounded or rebuilt by the model.

## Requirements

- An Arfiti organisation and a user who can sign in to it.
- The **Arfiti** connector (`https://mcp.arfiti.com/streamable/mcp`). This plugin's `.mcp.json` points at the same server, so installing both shows one set of tools.

## Commands

| Command | What it does |
| --- | --- |
| `/balance-sheet` | Server balance sheet with its reconciliation verdict, earnings bridge, optional comparison and labelled liquidity ratios. |
| `/profit-and-loss` | Server income statement with subtype sections, optional comparison and labelled margins. |
| `/cash-flow` | Server cash flow statement with its opening-to-closing cash bridge and verdict. |
| `/trial-balance` | Server trial balance with full-selection totals and verdict; unusual balances flagged for review. |
| `/aged-receivables` | AR aging with certification, overdue (1+ days), credits, period-length DSO and example follow-up. |
| `/aged-payables` | AP aging with certification, overdue vendors, amounts coming due and period-length DPO. |
| `/dimension-analysis` | P&L by department, project or cost centre from one server income statement per value. |
| `/financial-summary` | Summary of the server income statement, balance sheet and cash flow with labelled ratios. |

## What it runs and sends

This plugin contains skills, commands and helper scripts under `scripts/`. All are Python 3, standard library only, and none opens a network connection or starts another process.

- `format_aging.py`, `format_balance_sheet.py`, `format_dimension_analysis.py`, `format_financial_summary.py` and `format_income_statement.py` each read the JSON file you pass with `--input`: a `generate_report` result requested with `report_contract: 1`, saved unchanged. They refuse anything else (exit code 2) and write a markdown report to the path you pass with `--output`. `format_aging.py` also takes `--income-statement` for days outstanding.
- `report_v1.py` is a helper imported by those scripts. It reads `ratio_policy.json` and nothing else. It shows unavailable amounts as "Unavailable", every evidence gap and partial delivery, and the server's own verdicts.
- `ratio_policy.json` is example presentation policy (which subtypes count as current, cash, receivables, payables and inventory; example ratio bands; example follow-up wording). Edit it for your firm or client; it does not change the server reports.
- `examples/` holds sample inputs; they are never executed.

Report data is read from your Arfiti organisation through the connector's read tools.

It sends data to the Arfiti MCP server over the authenticated connector. It runs no code of its own that contacts any other service. The scripts write only the markdown files you ask for, at the path you give.

## Support

support@arfiti.com · Documentation: https://arfiti.com/plugins/arfiti-core-financial-reports
