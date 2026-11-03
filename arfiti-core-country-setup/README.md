# Arfiti Country Setup

Generates a country-specific onboarding template for Arfiti from a country code: VAT or GST rates and tax codes, tax authorities, withholding taxes, payroll deductions and government payment vendors, with the sources used. A tax researcher and a payroll specialist subagent research in parallel and the skill validates their findings into one structured JSON template.

## Requirements

- An Arfiti organisation and a user who can sign in to it.
- The **Arfiti** connector (`https://mcp.arfiti.com/streamable/mcp`). This plugin's `.mcp.json` points at the same server, so installing both shows one set of tools.

## Commands

| Command | What it does |
| --- | --- |
| `/generate-country-template` | Generate a country-specific onboarding template (tax codes, authorities, payroll configuration) for a given country code. |

## What it runs and sends

This plugin contains skills, one command and two subagents (`tax-researcher` and `payroll-specialist`). There are no scripts, hooks or local servers. Unlike the other plugins, the two subagents are declared with the web tools `WebSearch` and `WebFetch` (and the read-only `Read`, `Glob` and `Grep`). When you run the command they search the public web and fetch public pages, such as tax-authority and government sites, for the country you named. The only data in those requests is the country code and the search terms the agent writes; no organisation data is included by the plugin.

The finished template is returned to you as JSON. Whether and how it is saved into your organisation is a step you approve through the connector. Claude Code asks for permission before web tools run unless you have allowed them.

## Support

support@arfiti.com · Documentation: https://arfiti.com/plugins/arfiti-core-country-setup
