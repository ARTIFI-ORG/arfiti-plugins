# Arfiti Estonian Annual Report

Prepares the Estonian annual report (majandusaasta aruanne) for the e-Business Register. It guides step by step through the balance sheet, income statement, notes and management report from your Arfiti ledger, then generates the XBRL instance and companion schema files using the et-gaap 2026 taxonomy. You upload the files to ariregister.rik.ee yourself.

## Requirements

- An Arfiti organisation and a user who can sign in to it.
- The **Arfiti** connector (`https://mcp.arfiti.com/streamable/mcp`). This plugin's `.mcp.json` points at the same server, so installing both shows one set of tools.

## Commands

| Command | What it does |
| --- | --- |
| `/prepare-annual-report` | Prepare the full annual report for a legal entity. |
| `/check-prerequisites` | Check whether the legal entity is ready for annual report preparation. |
| `/generate-xbrl-mapping` | Generate the account-to-XBRL element mapping table for portal data entry. |
| `/generate-xbrl-file` | Generate the `.xbrl` and `.xsd` files for upload to ariregister.rik.ee. |

## What it runs and sends

This plugin contains skills, commands and one helper script under `scripts/`. `generate_xbrl.py` (Python 3, standard library only) reads the JSON file you pass with `--input`, checks the balance sheet and cash flow, and writes two files to the folder you pass with `--output`: `Vormid_<regcode>.xsd` and `Aruanne_<regcode>.xbrl`. It builds them entirely from the input and hardcoded namespaces; the taxonomy URLs in the output are identifiers written into the files and are never downloaded. `input_schema.json` describes the input and is not executed. The report data itself is read from your Arfiti organisation through the connector.

The scripts open no network connection and the only files they write are the outputs named above. Anything you upload to a government portal you upload yourself. It sends data to the Arfiti MCP server over the authenticated connector. It runs no code of its own that contacts any other service.

## Support

support@arfiti.com · Documentation: https://arfiti.com/plugins/arfiti-ee-annual-report
