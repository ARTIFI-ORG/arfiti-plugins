# Arfiti Cost Allocation

Cost allocation for Arfiti: split costs across departments, projects or other dimensions. Standalone mode allocates from general ledger balances; document-linked mode allocates a specific bill or invoice with full traceability, validates the source document and prevents double allocation. You can preview the split without submitting, then run it.

## Requirements

- An Arfiti organisation and a user who can sign in to it.
- The **Arfiti** connector (`https://mcp.arfiti.com/streamable/mcp`). This plugin's `.mcp.json` points at the same server, so installing both shows one set of tools.

## Commands

| Command | What it does |
| --- | --- |
| `/run-allocation` | Create and execute an allocation from start to finish, standalone from GL balances or linked to a specific bill or invoice. |
| `/preview-allocation` | Calculate and preview an allocation without submitting it. |

## What it runs and sends

This plugin contains skills and commands only. No scripts, hooks or local servers. Allocation runs are submitted to your Arfiti organisation only through the connector's tools, under its authorization and approval controls.

It sends data to the Arfiti MCP server over the authenticated connector. It runs no code of its own that contacts any other service.

## Support

support@arfiti.com · Documentation: https://arfiti.com/plugins/arfiti-core-cost-allocation
