# Arfiti Estonian Year-End Bookkeeping

Full year-end bookkeeping for Estonian companies (OÜ and AS) in Arfiti, for business owners, freelancers and accountants. It builds a complete year of accounts from scratch in five phases: entity and chart of accounts setup, opening balances, bank statement processing month by month, gap filling with source documents and year-end adjustments, and reconciliation with period close. It prepares the entity for annual report filing.

## Requirements

- An Arfiti organisation and a user who can sign in to it.
- The **Arfiti** connector (`https://mcp.arfiti.com/streamable/mcp`). This plugin's `.mcp.json` points at the same server, so installing both shows one set of tools.

## Commands

| Command | What it does |
| --- | --- |
| `/setup-entity` | Phase 1: import the chart of accounts, create bank accounts and configure posting profiles. |
| `/upload-opening-balance` | Phase 2: import and verify opening balances from the prior year (skip for first-year companies). |
| `/process-bank-statements` | Phase 3: read bank statements, create vendors and customers, classify and post transactions, month by month. |
| `/fill-gaps` | Phase 4: find missing bills and invoices and post source documents and year-end adjustments. |
| `/reconcile-and-close` | Phase 5: verify the trial balance and balance sheet, reconcile bank accounts, close fiscal periods and hand off to the annual report plugin. |
| `/check-progress` | Show progress across all five phases, what is next and any issues. |

## What it runs and sends

This plugin contains skills and commands only. No scripts, hooks or local servers. Postings and period closes are submitted to your Arfiti organisation only through the connector's tools, under its authorization, approval and audit controls.

It sends data to the Arfiti MCP server over the authenticated connector. It runs no code of its own that contacts any other service.

## Support

support@arfiti.com · Documentation: https://arfiti.com/plugins/arfiti-ee-year-end-bookkeeping
