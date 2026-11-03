# Arfiti Budget Planning

Budget planning for finance teams working in Arfiti: build annual, quarterly or monthly budgets, copy a prior year forward, forecast the remainder of the year from actuals, budget employee cost with burden rates, and compare budget against actual. It reads general ledger data, employee records and project details through the connector, calculates the amounts, and submits budget versions through the Arfiti workflow system after you confirm.

## Requirements

- An Arfiti organisation and a user who can sign in to it.
- The **Arfiti** connector (`https://mcp.arfiti.com/streamable/mcp`). This plugin's `.mcp.json` points at the same server, so installing both shows one set of tools.

## Commands

| Command | What it does |
| --- | --- |
| `/create-budget` | Build a new budget from scratch, copy forward from the prior year, or create from a template, at monthly, quarterly or annual granularity. |
| `/forecast-budget` | Create a mid-year forecast by blending year-to-date actuals with projected amounts for the remaining months. |
| `/preview-budget` | Calculate and preview budget amounts without submitting them, for what-if scenarios. |
| `/review-variance` | Analyse budget against actual variances with drill-down and corrective action suggestions. |

## What it runs and sends

This plugin contains skills and commands only. No scripts, hooks or local servers. Budget data is read from and submitted to your Arfiti organisation only through the connector's tools; submissions go through the Arfiti submit gateway, which applies your organisation's validation and approval rules.

It sends data to the Arfiti MCP server over the authenticated connector. It runs no code of its own that contacts any other service.

## Support

support@arfiti.com · Documentation: https://arfiti.com/plugins/arfiti-core-budget-planning
