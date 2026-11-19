# Arfiti Country Setup

Configures your live Arfiti company for its country, through the Arfiti connector: tax codes, tax authorities and jurisdictions, tax registrations, filing forms and reporting calendars, withholding tax rates, payroll taxes and government payees, and per-diem and mileage rates. It reads what your company already has and what onboarding left for configuration, researches the gaps from official sources, confirms every value with you, writes each one through the Arfiti submit gateway and reads it back. It also helps you design your own country plugins for payroll and the VAT return.

Installing the plugin changes nothing in your company. Every change is a submission you see and confirm; it goes through the same validation, entity scope, approval rules and audit trail as any other write.

## Requirements

- An Arfiti organisation with at least one legal entity, and a user who can sign in to it and write to that entity.
- Onboarding completed for the full set of operations. While onboarding is open, of the country setup records only tax codes, authorities, jurisdictions, registrations, accounts and vendors can be written.
- The **Arfiti** connector (`https://mcp.arfiti.com/streamable/mcp`). This plugin's `.mcp.json` points at the same server, so installing both shows one set of tools.

## Commands

| Command | What it does |
| --- | --- |
| `/set-up-country` | Configure a legal entity's country setup: read what exists, research the gaps with sources, confirm with you, apply through the connector, read back. |
| `/author-country-plugin` | Design your own payroll calculator or VAT declaration plugin for a country, using the Estonia country pack as the worked example. |

## What it does not do

- It does not decide country policy. Rates, thresholds, deadlines and accounts are researched and confirmed with you; a value without an official source is left open.
- It does not calculate payroll or prepare the VAT return. Arfiti stores the country data; a country plugin does the arithmetic and the filing (for Estonia, `arfiti-ee-country-pack`).
- It does not change an existing record without your yes for that record.

## What it runs and sends

This plugin contains one skill, two commands and two subagents (`tax-researcher` and `payroll-specialist`). There are no scripts, hooks or local servers. The two subagents are declared with the web tools `WebSearch` and `WebFetch` (and the read-only `Read`, `Glob` and `Grep`); when they run they search the public web and fetch public pages, such as tax-authority and government sites. Those requests carry the country, the facts about your entity you give them for the research (for example whether it is VAT registered) and the search terms the agent writes; no records from your organisation are sent to the web. Writes go only to your Arfiti organisation, through the connector. Claude Code asks for permission before web tools run unless you have allowed them.

## Support

support@arfiti.com · Documentation: https://arfiti.com/plugins/arfiti-core-country-setup
