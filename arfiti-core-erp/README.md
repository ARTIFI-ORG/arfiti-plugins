# Arfiti ERP core skill

The operating manual for the Arfiti ERP inside Claude. It teaches Claude how to use the Arfiti
MCP connector: the `submit` write gateway and its approval lanes; the `query`, `get_entity` and
`generate_report` read tools; and the paired `get_*` / `manage_*` tools for submissions,
workflow configuration, agents, connectors, imports, onboarding and organisation settings. A
domain guide covers each area: transactions, sales and purchase orders, master data, banking,
payroll, expenses, fixed assets, budgets, projects, billing, reconciliation, tax and period close.

## Requirements

- An Arfiti organisation and a user who can sign in to it.
- The **Arfiti** connector (`https://mcp.arfiti.com/streamable/mcp`). This plugin's `.mcp.json` points at the same
  server, so installing both shows one set of tools.

## What it runs and sends

Skills and reference documents only: no scripts, no hooks, no local servers. Valid accounts,
tax codes, payment terms, dimensions and legal entities are looked up live through the
connector's read tools instead of shipping a copy of any organisation's data. All data goes to
the Arfiti MCP server over the authenticated connector and nowhere else.

## Generated

This folder is generated from `mcp-server/skill-templates/base` in the Arfiti monorepo by
`plugins/scripts/build_core_plugin.py`. Edit the template, not this folder.

## Support

support@arfiti.com · Documentation: https://arfiti.com/plugins/arfiti-core-erp
