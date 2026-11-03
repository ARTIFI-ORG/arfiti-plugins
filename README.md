# Arfiti Plugins

AI-powered plugins that give finance and accounting teams superpowers inside Claude, Cursor, and other AI tools. Each plugin packages domain knowledge — reporting formats, tax rules, compliance workflows — so your AI assistant handles the details correctly.

## Available Plugins

### Core

Universal plugins that work with any chart of accounts and any country.

| Plugin | What it does | Commands |
|--------|-------------|----------|
| [arfiti-core-financial-reports](./arfiti-core-financial-reports) | Financial reporting suite: Balance Sheet, P&L, Cash Flow, Trial Balance, Aging Analysis, and Dimension Analysis. Discovers account properties dynamically — works with any COA. | `/balance-sheet` `/profit-and-loss` `/cash-flow` `/trial-balance` `/aged-receivables` `/aged-payables` `/dimension-analysis` `/financial-summary` |
| [arfiti-core-budget-planning](./arfiti-core-budget-planning) | Budget planning: annual/quarterly budgets, forecasting from actuals, employee cost budgeting with burden rates, and project budgeting. | `/create-budget` `/forecast-budget` `/preview-budget` `/review-variance` |
| [arfiti-core-cost-allocation](./arfiti-core-cost-allocation) | Cost allocation across departments, projects, or dimensions. Standalone mode (from GL balances) and document-linked mode (from a specific bill/invoice with full traceability). | `/run-allocation` `/preview-allocation` |
| [arfiti-core-erp](./arfiti-core-erp) | The operating manual for the Arfiti ERP inside Claude: the `submit` write gateway and its approval lanes, the read tools, the `get_*` / `manage_*` tool pairs, and a domain guide for each area. Skills and reference documents only; generated from the monorepo skill templates. | Skill `arfiti-erp` (no slash commands) |
| [arfiti-core-implementation-consultant](./arfiti-core-implementation-consultant) | ERP migration consultant. Guides customers through the full migration journey: chart of accounts setup, opening balances with open transactions (individual AR invoices, AP bills, fixed assets), master data import, gap period transaction processing, and go-live verification. Supports 4 migration paths — Connector (Merit/QBO/SmartAccounts), CSV/Manual, Greenfield, and Hybrid. Features advisory intelligence that scans the balance sheet to detect what additional data is needed. | `/start-migration` `/migration-status` `/import-data` `/verify-migration` `/close-migration` |
| [arfiti-core-reconciliation](./arfiti-core-reconciliation) | Payment-to-invoice reconciliation. Automated 6-pass matching via reconciliation agent, then guided manual matching for complex cases — N:N splits, partial payments, rounding write-offs. Supports AR and AP. | `/reconcile` `/match-payment` `/reconciliation-status` |
| [arfiti-core-country-setup](./arfiti-core-country-setup) | Generates country-specific tax and payroll configuration templates. Researches VAT/GST rates, tax authorities, withholding taxes, and payroll rules to produce structured JSON for onboarding. | `/generate-country-template` |

### Estonia (EE)

| Plugin | What it does | Commands |
|--------|-------------|----------|
| [arfiti-ee-year-end-bookkeeping](./arfiti-ee-year-end-bookkeeping) | Builds a full year's accounting from scratch for Estonian companies (OÜ/AS). Guides through chart of accounts setup, opening balances, bank statement processing (month by month), source document posting, reconciliation, and period close — preparing the entity for annual report filing. | `/setup-entity` `/upload-opening-balance` `/process-bank-statements` `/fill-gaps` `/reconcile-and-close` `/check-progress` |
| [arfiti-ee-annual-report](./arfiti-ee-annual-report) | Prepares the full annual report (balance sheet, income statement, notes, management report) and generates XBRL for e-Business Register filing. Uses the et-gaap-2026 taxonomy. | `/prepare-annual-report` `/check-prerequisites` `/generate-xbrl-file` |
| [arfiti-ee-payroll-calculator](./arfiti-ee-payroll-calculator) | Calculates gross-to-net payroll with Estonian tax formulas (social tax, income tax, unemployment insurance, funded pension) and generates TSD declarations for EMTA. | `/calculate-payroll` `/generate-tsd` |
| [arfiti-ee-vat-declaration](./arfiti-ee-vat-declaration) | Prepares & validates VAT returns (KMD2 machine CSV + XML) and KMD INF annexes. Runs a pre-close validation gate, then generates. The EC Sales List (Form VD) is a separate filing. Dynamically discovers tax codes and maps to KMD lines. | `/prepare-vat-declaration` (add `validate` to run the gate only) `/prepare-ec-sales-list` |

More countries coming soon.

## Getting Started

### Option 1: Clone the repository

```bash
git clone https://github.com/ARTIFI-ORG/arfiti-plugins.git
```

Add the plugin directory to your Claude Desktop project or Cursor workspace.

### Option 2: Download ZIP

[Download latest ZIP](https://github.com/ARTIFI-ORG/arfiti-plugins/archive/refs/heads/main.zip)

### Option 3: Via Arfiti admin dashboard

If you use [Arfiti](https://arfiti.com), plugins are available directly from the admin dashboard under **Administration > Plugins** with one-click download.

## How Plugins Work

Each plugin is a self-contained package that extends your AI assistant with domain-specific knowledge:

```
plugin-name/
  .claude-plugin/plugin.json    # Plugin manifest (name, version, description)
  .mcp.json                     # MCP server connection (links to Arfiti backend)
  commands/                     # Slash commands (e.g. /prepare-annual-report)
  skills/                       # Detailed workflow instructions + reference data
    skill-name/
      SKILL.md                  # Step-by-step workflow with checkpoints
      references/               # Tax tables, form structures, filing guides
  scripts/                      # Deterministic generators (XML, XBRL, etc.)
```

**Commands** are entry points — the user types `/prepare-vat-declaration` and the AI follows the workflow defined in the skill.

**Skills** contain the actual knowledge — multi-step workflows with mandatory checkpoints, validation rules, and reference data.

**References** are the source of truth — tax formulas, XBRL element mappings, regulatory form structures. The AI reads these instead of guessing.

**Scripts** generate deterministic output (XBRL, XML declarations) where AI generation would be unreliable. Claude builds compact JSON, the script produces valid XML with hardcoded namespaces and validated structure.

## Contributing a Country Plugin

We welcome contributions for new countries. A typical compliance plugin needs:

1. **Annual report** — Balance sheet and income statement formats, local GAAP taxonomy, filing portal instructions
2. **VAT/GST/Sales tax** — Return form structure, tax codes and rates, filing format
3. **Payroll** — Tax formulas (income tax, social contributions, pension), payslip format, declaration forms

See any existing country plugin for the structure. Open an issue or PR to get started.

## MCP transport config (checked in CI)

Each plugin's `.mcp.json` points at the Arfiti MCP server. The `type` field must
be a real transport — `http` (alias `streamable-http`), `sse`, `ws`, or `stdio`.
A remote endpoint uses `"type": "http"`:

```json
{ "mcpServers": { "arfiti": { "type": "http", "url": "https://mcp.arfiti.com/streamable/mcp" } } }
```

`"type": "url"` is **not** a transport. It shipped from April to 2026-08-19 and
cost five weeks of outage: Claude Code tolerated it, but Cowork's stricter sync
rejected the entire marketplace with a generic "Marketplace sync failed", so no
plugin was installable there. `claude plugin validate` does not read `.mcp.json`,
so nothing caught it. `plugins/scripts/check_mcp_configs.py` now runs in the
publish workflow and fails the build on an invalid transport.

The canonical production endpoint is `https://mcp.arfiti.com/streamable/mcp`.
After the October 2026 migration, update installed plugins to the new patch
versions; cached earlier releases still contain the old `/mcp` URL. Reconnect
the MCP connection if prompted. Updating source does not rewrite installed caches.

## Support

support@arfiti.com · Documentation: https://arfiti.com/docs

## Publishing to the Anthropic directory

This repository's contents are submitted to the Anthropic directory from `ARTIFI-ORG/arfiti-plugins`, which the publish workflow syncs and nobody edits by hand. Each plugin folder needs a README with a "What it runs and sends" section, a LICENSE and a `license` in `plugin.json`, all checked by `plugins/scripts/check_mcp_configs.py`. `arfiti-core-erp` is generated: edit `mcp-server/skill-templates/base`, run `plugins/scripts/build_core_plugin.py`, and commit both. The full process is in [GUIDE_PLUGINS.md](../docs/GUIDES/GUIDE_PLUGINS.md#anthropic-directory).

## Versioning (required on every content change)

Claude.ai caches installed plugins **by version** — shipping changed content under an
unchanged version means users keep the stale cached copy even after reinstalling.
Whenever you change anything inside a plugin, bump its version:

```bash
python3 plugins/scripts/plugin_versions.py --bump <plugin-name> <major|minor|patch>
```

- **major** — breaking: commands removed/renamed, output format changed
- **minor** — new commands or features
- **patch** — fixes, doc/text updates

The bump updates `plugin.json`, `marketplace.json`, and `versions.lock.json` together.
CI (`publish-plugins.yml`) runs `plugin_versions.py --check` before syncing to the
public marketplace repo and **fails the publish** if content changed without a bump.

Why this exists (per the official plugin-marketplace docs): when `version` is set,
clients pin the cached plugin to that exact string — *"you must bump it every time you
want users to receive changes; pushing new commits alone is not enough."* The docs also
advise against setting `version` in both `plugin.json` and the marketplace entry
(the marketplace entry wins when set — see code.claude.com/docs/en/plugins, version
management); we deliberately keep both **because the CI check enforces they are
identical**, which removes the masking risk while every client surface sees the same
version. Do not remove one of them without updating the checker.

## License

[MIT](./LICENSE) - Arfiti Technologies OU
