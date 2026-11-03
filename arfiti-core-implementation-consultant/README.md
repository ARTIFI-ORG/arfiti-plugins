# Arfiti Implementation Consultant

A guided ERP migration partner for Arfiti. It sets up the chart of accounts, loads opening balances with individual open invoices, bills and fixed assets, imports master data, handles gap-period transactions and verifies go-live. It supports connector, CSV or manual, greenfield and hybrid paths, and scans your balance sheet to detect what additional data the migration needs.

## Requirements

- An Arfiti organisation and a user who can sign in to it.
- The **Arfiti** connector (`https://mcp.arfiti.com/streamable/mcp`). This plugin's `.mcp.json` points at the same server, so installing both shows one set of tools.

## Commands

| Command | What it does |
| --- | --- |
| `/start-migration` | Begin a guided migration: discover your situation, choose a path and build a step-by-step plan. |
| `/migration-status` | Show progress across all migration phases, what is next and any blockers. |
| `/import-data` | Import vendors, customers, items, employees, transactions or opening balances with format guidance. |
| `/verify-migration` | Run the verification suite: trial balance, balance sheet, aging reports, bank balances and fixed assets. |
| `/close-migration` | Final verification, migration summary and go-live advice. |

## What it runs and sends

This plugin contains skills, commands and one subagent (`balance-sheet-analyzer`). There are no scripts, hooks or local servers. The `balance-sheet-analyzer` subagent is declared with `Read`, `Glob`, `Grep` and `WebFetch`: it reads the balance sheet or trial balance file you give it and may fetch a public web page if you point it at one. Its parsed output is passed back to the migration skill, which writes to your organisation only through the connector's tools and your approvals.

It sends data to the Arfiti MCP server over the authenticated connector. It runs no code of its own that contacts any other service. The one exception is the optional `WebFetch` of a public URL that you supply to the analyzer subagent.

## Support

support@arfiti.com · Documentation: https://arfiti.com/plugins/arfiti-core-implementation-consultant
