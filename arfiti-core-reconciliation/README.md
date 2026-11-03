# Arfiti Reconciliation

Payment-to-invoice reconciliation for Arfiti, covering accounts payable and accounts receivable. The Arfiti reconciliation agent runs automated matching passes; you then work through the remaining cases with guided matching for split payments, partial payments and rounding write-offs. It also covers card purchase review with separate evidence obligations and provider coverage controls.

## Requirements

- An Arfiti organisation and a user who can sign in to it.
- The **Arfiti** connector (`https://mcp.arfiti.com/streamable/mcp`). This plugin's `.mcp.json` points at the same server, so installing both shows one set of tools.

## Commands

| Command | What it does |
| --- | --- |
| `/reconcile` | Run full payment-to-invoice reconciliation, then guide manual matching of complex cases. |
| `/match-payment` | Manually match a payment to one or more invoices: 1:1, 1:N, partial, with rounding write-offs. |
| `/reconciliation-status` | Show matched, unmatched and partial counts for AP and AR with recommendations. |

## What it runs and sends

This plugin contains skills and commands only. No scripts, hooks or local servers. Matching runs and manual matches are submitted to your Arfiti organisation only through the connector's tools, under its authorization and audit controls.

It sends data to the Arfiti MCP server over the authenticated connector. It runs no code of its own that contacts any other service.

## Support

support@arfiti.com · Documentation: https://arfiti.com/plugins/arfiti-core-reconciliation
