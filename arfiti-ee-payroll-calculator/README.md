# Arfiti Estonian Payroll Calculator

Estonian payroll for Arfiti legal entities: gross-to-net calculation with income tax, social tax, unemployment insurance, funded pension and voluntary deductions, submitted to the ERP, and generation of the monthly TSD declaration XML for e-MTA from an approved payroll run. The XML is produced by a deterministic script against the official e-MTA schema, and you upload it yourself.

## Requirements

- An Arfiti organisation and a user who can sign in to it.
- The **Arfiti** connector (`https://mcp.arfiti.com/streamable/mcp`). This plugin's `.mcp.json` points at the same server, so installing both shows one set of tools.

## Commands

| Command | What it does |
| --- | --- |
| `/calculate-payroll` | Calculate gross-to-net payroll for an Estonian legal entity and submit the results to the ERP. |
| `/generate-tsd` | Generate the e-MTA TSD XML from a calculated or approved payroll run, ready for upload to maasikas.emta.ee. |

## What it runs and sends

This plugin contains skills, commands and one helper script under `scripts/`. The script uses only the Python standard library and opens no network connection.

- `generate_tsd.py` reads the JSON file you pass with `--input`, validates it, and writes one file, `TSD_<year><month>_<regcode>.xml`, to the folder you pass with `--output` (default: the current folder). It prints a tax summary to the terminal.
- `input_schema_tsd.json` describes the input and is not executed.

Payroll data is read from and submitted to your Arfiti organisation through the connector.

The only file the script writes is the output named above. Anything you upload to a government portal you upload yourself. The plugin sends data only to the Arfiti MCP server over the authenticated connector and runs no code of its own that contacts any other service.

## Support

support@arfiti.com · Documentation: https://arfiti.com/plugins/arfiti-ee-payroll-calculator
