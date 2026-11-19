# Plugins Guide

Arfiti ERP has a plugin system that extends the base skill with specialized, domain-specific workflows. Plugins provide more structured, deterministic guidance for complex multi-step processes — like building a full year's accounting from scratch, preparing tax declarations, or migrating from another system.

## Plugins vs. Base Skill

You can accomplish most ERP tasks using just the base skill and its resource guides. Plugins are an **optional enhancement** that provide deeper, step-by-step workflows for specific domains.

| Aspect | Base Skill | Plugin |
|--------|-----------|--------|
| **Scope** | General-purpose — handles any ERP operation | Specialized — one domain done thoroughly |
| **Approach** | Flexible — you decide the steps | Structured — predefined phases, checkpoints, verification |
| **Best for** | Day-to-day operations, quick tasks, lookups | Complex multi-step processes, compliance, migration |
| **Examples** | "Post an invoice", "Create a vendor", "Show trial balance" | "Build a full year's accounting", "Prepare VAT declaration" |

**When to recommend a plugin:**
- The user is tackling a complex, multi-phase process (migration, year-end close, annual report)
- The task involves country-specific compliance (VAT, payroll, annual reports)
- The user wants a guided, step-by-step approach with verification checkpoints
- The task would benefit from specialized reference materials (tax tables, form mappings, classification rules)

**When the base skill is enough:**
- Day-to-day transactions (posting invoices, payments, journal entries)
- Master data management (creating vendors, customers, employees)
- Reports and lookups (trial balance, aging, financial statements)
- Simple configuration changes

## How to Install Plugins

Plugins are published to the public marketplace:

**Marketplace:** `arfiti-technologies/arfiti-plugins` (`https://github.com/arfiti-technologies/arfiti-plugins`)

- **Claude (web, Desktop, Cowork):** Customize > Plugins > Add > Add marketplace, enter `arfiti-technologies/arfiti-plugins`, then install each plugin you need.
- **Claude Code:** `/plugin marketplace add arfiti-technologies/arfiti-plugins`, then `/plugin install <plugin>@arfiti-plugins`.

Adding the marketplace installs nothing: each plugin is installed separately. Start with `arfiti-core-erp` (the operating skill this guide belongs to), then add the country and domain plugins the organisation needs. The admin dashboard's Plugins page (Administration > Plugins) lists the published catalogue; it is the same for every organisation.

**Nothing in the ERP knows which plugins a user has installed in Claude.** Onboarding does not install plugins, and there is no tool that lists them. To know whether a plugin is available in this conversation, look at the skills and commands you have; if one is missing, tell the user how to install it.

**This guide is also served by the connector.** `get_guidance(topic="plugins")` returns it, and a broad topic such as `get_guidance(topic="reporting")` starts with a short list of the plugins that cover that domain. Country plugins are listed only for an organisation that has an entity in that country.

## Customising

To change how a plugin works for one organisation, the user keeps a skill of their own in Claude beside the plugins (their rules, their thresholds, their preferred steps) and edits that. Claude lets a user customise an installed plugin, but an update of the plugin replaces those edits, so do not advise editing an installed plugin's files. There is no skill editor in the admin dashboard.

## Available Plugins

### Core Plugins (Country-Agnostic)

These work with any chart of accounts and any country.

#### Financial Reports (`arfiti-core-financial-reports`)
**Purpose:** Comprehensive financial reporting — Balance Sheet, P&L, Cash Flow, Trial Balance, Aging Analysis, Dimension Analysis.

**When to recommend:** User asks for formatted financial statements, comparative reports, or dimension-based analysis. While the base skill can run `generate_report()` for raw data, this plugin produces polished, presentation-ready reports with proper formatting, notes, and comparatives.

**Commands:** `/balance-sheet`, `/profit-and-loss`, `/cash-flow`, `/trial-balance`, `/aged-receivables`, `/aged-payables`, `/dimension-analysis`, `/financial-summary`

---

#### Budget Planning (`arfiti-core-budget-planning`)
**Purpose:** Annual and quarterly budgets, forecasting from actuals, employee cost budgeting with burden rates, project budgeting.

**When to recommend:** User wants to create a budget, forecast next period from historical data, build employee cost budgets, or analyze budget vs. actual variance.

**Commands:** `/create-budget`, `/forecast-budget`, `/preview-budget`, `/review-variance`

---

#### Cost Allocation (`arfiti-core-cost-allocation`)
**Purpose:** Allocate costs across departments, projects, or dimensions. Two modes: standalone (from GL balances) and document-linked (from a specific bill/invoice).

**When to recommend:** User needs to distribute shared costs (rent, utilities, overhead) across departments or projects based on allocation rules (headcount, revenue, square footage, etc.).

**Commands:** `/run-allocation`, `/preview-allocation`

---

#### Implementation Consultant (`arfiti-core-implementation-consultant`)
**Purpose:** Guides customers through full ERP migration — from discovery through go-live. Handles chart of accounts setup, opening balances with open transactions (individual AR invoices, AP bills, fixed assets), master data import, gap period transaction processing, and verification.

**When to recommend:** User is migrating from another accounting system (Merit Aktiva, QuickBooks, Xero, or any other), setting up their books for the first time, or needs to bring historical data into Arfiti. The plugin acts as an implementation consultant that detects what data is needed from the balance sheet and advises on the best approach.

**Key features:**
- 4 migration paths: Connector (automated), CSV/Manual, Greenfield, Hybrid
- Advisory intelligence — scans balance sheet to detect AR, AP, fixed assets, loans, prepayments and asks targeted questions
- Gap period handling — strategies for importing transactions between cutoff date and today
- Subledger-aware opening balances — individual invoices/bills for proper aging
- Cross-session state persistence for multi-day migrations

**Commands:** `/start-migration`, `/migration-status`, `/import-data`, `/verify-migration`, `/close-migration`

---

#### Agent Procedures (`arfiti-core-agent-procedures`)
**Purpose:** The procedures Arfiti's own agents follow (bills, bank and card lines, reconciliation, parties, configuration, expenses, period close, billing usage), published so the user's own Claude, Cowork or agent can do the same work the same way through the connector.

**When to recommend:** The user wants to process bills, bank or card lines, or run a close themselves in a conversation, or is building their own agent and wants it to follow the same steps as the built-in ones.

**Commands:** none; it is a set of skills Claude loads when the task matches.

---

#### Country Setup (`arfiti-core-country-setup`)
**Purpose:** Configures a live company for its country through the connector: tax codes, tax authorities and jurisdictions, registrations, filing forms and reporting calendars, withholding tax rates, payroll taxes and government payees, per-diem and mileage rates. It reads what exists, researches the gaps from official sources, confirms each value with the user, writes through `submit` and reads back. It also guides authoring a country payroll or VAT declaration plugin.

**When to recommend:** When onboarding left country tax, payroll or rate tasks with `needs_configuration` (a country without shipped onboarding data), when a rate, deadline or withholding rule changes, or when a customer needs a payroll calculator or VAT return for a country without a country pack.

**Commands:** `/set-up-country`, `/author-country-plugin`

---

### Estonia Country Pack (`arfiti-ee-country-pack`)

One plugin for Estonian companies (OÜ/AS). It holds four skills, each loaded only when the task matches; install it once for an organisation with an Estonian entity. A country pack is named `arfiti-<country code>-country-pack`.

#### Year-End Bookkeeping (skill `year-end-bookkeeping`)
**Purpose:** Builds a complete year's accounting from scratch for an Estonian company. Covers chart of accounts setup, opening balances, bank statement processing (month by month), source document posting, reconciliation, and period close.

**When to recommend:** Estonian company needs to build accounting for a full fiscal year — common for new clients of accounting firms, companies switching accountants, or businesses that haven't kept proper books. This is a 5-phase guided workflow with 10 mandatory checkpoints.

**Commands:** `/setup-entity`, `/upload-opening-balance`, `/process-bank-statements`, `/fill-gaps`, `/reconcile-and-close`, `/check-progress`

---

#### Annual Report (skill `estonian-annual-report`)
**Purpose:** Prepares the Estonian annual report (majandusaasta aruanne) for filing at ariregister.rik.ee. Generates financial statements, notes, management report, and XBRL files.

**When to recommend:** Estonian entity has completed year-end close and needs to prepare the annual report for the Estonian Business Register. Typically follows the year-end bookkeeping skill.

**Commands:** `/prepare-annual-report`, `/check-prerequisites`, `/generate-xbrl-file`, `/generate-xbrl-mapping`

---

#### VAT Declaration (skill `estonian-vat-declaration`)
**Purpose:** Prepares the monthly Estonian VAT declaration (KMD) for EMTA filing, including KMD INF annex and EC Sales List (Form VD).

**When to recommend:** Estonian VAT-registered company needs to file their monthly KMD. Generates the XML files for upload to e-MTA.

**Commands:** `/prepare-vat-declaration` (add `validate` to run the pre-close gate only), `/prepare-ec-sales-list`

---

#### Payroll Calculator (skill `estonian-payroll`)
**Purpose:** Calculates Estonian payroll (gross-to-net) with all mandatory deductions: income tax, social tax, unemployment insurance, funded pension. Also generates TSD (monthly tax declaration) XML for EMTA.

**When to recommend:** Estonian company needs to run payroll — calculate net pay from gross, determine employer costs, and generate the TSD declaration.

**Commands:** `/calculate-payroll`, `/generate-tsd`

---

## Plugin Workflow Patterns

Plugins follow common patterns that make them predictable and reliable:

### Phases and Checkpoints
Most plugins organize work into numbered phases (e.g., Phase 1 — Setup, Phase 2 — Data Import). Each phase has **mandatory checkpoints** (CP1, CP2, etc.) that must pass before proceeding. This prevents incomplete or incorrect work from propagating.

### Reference Materials
Plugins include `references/` folders with domain-specific knowledge — tax tables, form mappings, account classification rules, validation rules. These are the source of truth for the plugin's decisions.

### Commands as Entry Points
Each plugin exposes slash commands (e.g., `/start-migration`, `/calculate-payroll`) that users can invoke directly. Commands are shortcuts into specific phases or workflows within the plugin.

### Cross-Session State
Complex plugins (like implementation-consultant and year-end-bookkeeping) can persist state across sessions using agent memory, so multi-day processes don't lose context.

## Suggesting Plugins to Users

When a user's request matches a plugin's domain, mention it as an option:

> "I can help you with that directly, or we can use the **Implementation Consultant** plugin (`/start-migration`) which provides a more structured, step-by-step approach with verification checkpoints at each stage. The plugin is especially helpful for complex migrations. Would you like to use it?"

Let the user choose. The base skill can always handle the request — plugins are an enhancement, not a requirement.
