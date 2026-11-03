# Plugins Guide

Arfiti ERP has a plugin system that extends the base skill with specialized, domain-specific workflows. Plugins provide more structured, deterministic guidance for complex multi-step processes — like building a full year's accounting from scratch, preparing tax declarations, or migrating from another system.

## Plugins vs. Base Skill

You can accomplish most ERP tasks using just the base skill and its 37 resource guides. Plugins are an **optional enhancement** that provide deeper, step-by-step workflows for specific domains.

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

Plugins are available from the Arfiti plugin repository:

**Repository:** `https://github.com/ARTIFI-ORG/arfiti-plugins`

Plugins are automatically installed during onboarding based on the organization's country and needs. Users can also install additional plugins from the admin dashboard (Settings → Plugins) or request them via Claude.

To check which plugins are installed:
```
get_organization(action="list_plugins")
```

## Available Plugins

### Core Plugins (Country-Agnostic)

These work with any chart of accounts and any country.

#### Financial Reports (`arfiti-core-financial-reports`)
**Purpose:** Comprehensive financial reporting — Balance Sheet, P&L, Cash Flow, Trial Balance, Aging Analysis, Dimension Analysis.

**When to recommend:** User asks for formatted financial statements, comparative reports, or dimension-based analysis. While the base skill can run `generate_report()` for raw data, this plugin produces polished, presentation-ready reports with proper formatting, notes, and comparatives.

**Commands:** `/balance-sheet`, `/profit-and-loss`, `/cash-flow`, `/trial-balance`, `/aged-receivables`, `/aged-payables`, `/dimension-analysis`

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

#### Country Setup (`arfiti-core-country-setup`)
**Purpose:** Generates country-specific tax and payroll configuration templates. Researches a country's tax system (VAT/GST rates, authorities, withholding taxes) and payroll rules to produce structured JSON templates.

**When to recommend:** When setting up a new country that doesn't have a pre-built template yet, or when verifying/updating tax rates for an existing country.

**Commands:** `/generate-country-template`

---

### Estonia-Specific Plugins

These are designed for Estonian companies (OÜ/AS) and handle Estonian compliance requirements.

#### Year-End Bookkeeping (`arfiti-ee-year-end-bookkeeping`)
**Purpose:** Builds a complete year's accounting from scratch for an Estonian company. Covers chart of accounts setup, opening balances, bank statement processing (month by month), source document posting, reconciliation, and period close.

**When to recommend:** Estonian company needs to build accounting for a full fiscal year — common for new clients of accounting firms, companies switching accountants, or businesses that haven't kept proper books. This is a 5-phase guided workflow with 10 mandatory checkpoints.

**Commands:** `/setup-entity`, `/upload-opening-balance`, `/process-bank-statements`, `/fill-gaps`, `/reconcile-and-close`, `/check-progress`

---

#### Annual Report (`arfiti-ee-annual-report`)
**Purpose:** Prepares the Estonian annual report (majandusaasta aruanne) for filing at ariregister.rik.ee. Generates financial statements, notes, management report, and XBRL files.

**When to recommend:** Estonian entity has completed year-end close and needs to prepare the annual report for the Estonian Business Register. Typically follows the year-end-bookkeeping plugin.

**Commands:** `/prepare-annual-report`, `/check-prerequisites`, `/generate-xbrl-file`, `/generate-xbrl-mapping`

---

#### VAT Declaration (`arfiti-ee-vat-declaration`)
**Purpose:** Prepares the monthly Estonian VAT declaration (KMD) for EMTA filing, including KMD INF annex and EC Sales List (Form VD).

**When to recommend:** Estonian VAT-registered company needs to file their monthly KMD. Generates the XML files for upload to e-MTA.

**Commands:** `/prepare-vat-declaration` (add `validate` to run the pre-close gate only), `/prepare-ec-sales-list`

---

#### Payroll Calculator (`arfiti-ee-payroll-calculator`)
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
