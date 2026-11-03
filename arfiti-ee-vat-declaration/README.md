# Arfiti Estonian VAT Declaration

Prepares the monthly Estonian VAT return (KMD) for e-MTA from your Arfiti ledger. It discovers and classifies tax codes instead of assuming them, runs a pre-close validation gate that blocks or warns, then generates the KMD2 machine CSV and an XSD-validated XML with the KMD INF annexes. The EC Sales List (Form VD) is prepared separately as a data table for portal entry. The tax period is locked after filing.

## Requirements

- An Arfiti organisation and a user who can sign in to it.
- The **Arfiti** connector (`https://mcp.arfiti.com/streamable/mcp`). This plugin's `.mcp.json` points at the same server, so installing both shows one set of tools.

## Commands

| Command | What it does |
| --- | --- |
| `/prepare-vat-declaration` | Run the validation gate, then generate the KMD2 CSV and XML with the KMD INF annex. Add `validate` to run the gate only. |
| `/prepare-ec-sales-list` | Prepare the EC Sales List (Form VD) for intra-EU B2B supplies as a KMD-reconciled table for portal entry. |

## What it runs and sends

This plugin contains skills, commands and one helper script under `scripts/`. `generate_kmd.py` (Python 3, standard library only) reads the JSON file you pass with `--input` and writes two files to the folder you pass with `--output` (default: the current folder): `KMD_<yyyymm>_<regcode>.csv` and `vatDeclaration_<yyyymm>_<regcode>.xml`. Before writing the XML it validates it against the bundled `vatdeclaration.xsd` by running the local `xmllint` program (libxml2) on a temporary file, which it deletes afterwards; if `xmllint` is not installed it prints a warning and skips validation. `input_schema_kmd.json` describes the input and is not executed. The ledger data is read from your Arfiti organisation through the connector, and locking the tax period after filing is a write you confirm through the connector.

The scripts open no network connection and the only files they write are the outputs named above. Anything you upload to a government portal you upload yourself. It sends data to the Arfiti MCP server over the authenticated connector. It runs no code of its own that contacts any other service.

## Support

support@arfiti.com · Documentation: https://arfiti.com/plugins/arfiti-ee-vat-declaration
