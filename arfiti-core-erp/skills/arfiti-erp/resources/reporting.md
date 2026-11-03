# Reporting Guide

This guide covers the unified reporting system in AI-Native ERP.

## Correctness rollout status

Shared report tools return `report_v1` after migration 630 and the matching server
release. Deployment is separate from code availability. For exact, nullable responses,
use `report_contract: 1` on supported reports, or `asset_register` / `budget_actual`.
Read currency, requested/effective dates, quality and coverage before interpreting
numbers. Money is a decimal string; null means unavailable, not zero. Reconciliation booleans are also null when unavailable; a successful request does not certify its figures. Follow
`coverage.next_cursor` with the identical parameters. Snapshot expiry requires a new
report; never mix pages from different tokens. Full totals are independent of pages.

Ledger eligibility, opening balances and functional currency come from shared SQL.
Missing currency is an error. Unconfirmed/defaulted timezones, unresolved posting evidence and ambiguous classification must be surfaced. Entity `metadata.reporting_timezone` or organization
`settings.reporting_timezone` supplies the business date. Missing/invalid timezone uses a disclosed country/UTC default; confirm it through entity settings or `legal_entity.update(reporting_timezone=...)`. Cash position and budget
actuals do not include future days. No account-number classification or currency fallback.

Cash flow supports evidenced movements; unclassified/mixed settlements remain
incomplete even if cash reconciles. Restricted cash counts in accounting cash (and in
`cash_days` / `cash_window`) and is excluded only from available cash. Income-statement expense credits reduce costs. Raw ledger
balances include closes; performance excludes transfers and BS exposes the unclosed
earnings bridge. Aging certification still requires dated application history and
a control tie-out. Historical asset book values may be unavailable.

Budget comparisons match all stored scopes, use custom/fiscal periods and require
functional currency. Overlapping scopes cannot be summed. Zero variance is neutral;
partial/future periods and balance-sheet movements have no favourable verdict.
Agent financial context loads these facts in one repeatable-read transaction, returning bounded summaries: up to 200 statement accounts, 500 recent transactions and 10 budget versions. Sections disclose truncation, full totals and evidence; separate budget versions must not be added.
Consolidated adapters accept one functional currency and explicitly return uncertified
aggregates before eliminations; translated consolidation is unsupported.

- Revenue/expense by customer, vendor, item or category and the dimension reports return `quality` and `evidence_gaps`. A gap means some lines were left out; say so and name the listed entries rather than presenting the totals as complete.
- `income_statement` section totals are null when the server could not certify them (an unclassified account, or an opening/closing journal that may hold earlier profit). Never add the account rows to make a total.
- `is_balanced` is true, false or null. Null means the evidence is incomplete, not that the ledger is out of balance. A proof ties only at zero.
- Errors with `"error": "report_unavailable"` carry a `message` to relay as it is; the report type itself is valid.
- A warning that ledger lines belong to a missing entry or another entity means those lines are outside the totals until corrected; name the listed lines and do not call the report complete.
---

## Overview

All reports are generated through a single unified interface. Two tools handle everything:

| Tool | Purpose |
|------|---------|
| `generate_report(report_type, params)` | Generate any report by type |
| `generate_report("list", {"category": ...})` | Discover available reports and their parameters |

Categories: financial, consolidated, tax, operational, banking, allocation, dimension, budget, fixed_assets, audit — `generate_report("list")` is the authoritative catalogue.

---

## Quick Start

```
# Generate a trial balance
generate_report("trial_balance", {
    "legal_entity_id": 9,
    "as_of_date": "2025-12-31"
})

# Generate an income statement
generate_report("income_statement", {
    "legal_entity_id": 9,
    "start_date": "2025-01-01",
    "end_date": "2025-12-31"
})

# Discover all available reports
generate_report("list")

# Discover reports in a category
generate_report("list", {"category": "financial"})
```

---

## Common Parameters

| Parameter | Type | Used By | Description |
|-----------|------|---------|-------------|
| `legal_entity_id` | int | Single-entity reports | Required for most reports |
| `entity_ids` | list[int] | Consolidated reports | List of entity IDs to combine |
| `as_of_date` | str (YYYY-MM-DD) | Balance/point-in-time reports | Snapshot date |
| `start_date` | str (YYYY-MM-DD) | Activity/period reports | Period start |
| `end_date` | str (YYYY-MM-DD) | Activity/period reports | Period end |
| `top_n` | int | Ranking reports | Limit results (default: 20) |

---

## Financial Reports

Core financial statements and account analysis.

| Report Type | Description | Required Params |
|-------------|-------------|-----------------|
| `trial_balance` | All accounts with debit/credit balances | `legal_entity_id`, `as_of_date` |
| `balance_sheet` | Assets = Liabilities + Equity | `legal_entity_id`, `as_of_date` |
| `income_statement` | Revenue − COGS − Expenses = Net Income (with Gross Profit subtotal) | `legal_entity_id`, `start_date`, `end_date` |
| `cash_flow_statement` | Operating, investing, financing flows | `legal_entity_id`, `start_date`, `end_date` |
| `account_activity` | Transaction detail for one account | `legal_entity_id`, `account_number`, `start_date`, `end_date` |
| `general_ledger_detail` | All journal entries by account | `legal_entity_id`, `start_date`, `end_date` |
| `statement_of_changes_in_equity` | Equity component changes | `legal_entity_id`, `start_date`, `end_date` |
| `ar_aging` | Customer balances by aging bucket | `legal_entity_id`, `as_of_date` |
| `ap_aging` | Vendor balances by aging bucket | `legal_entity_id`, `as_of_date` |
| `vendor_aging_detail` | Single vendor invoice-level aging | `legal_entity_id`, `vendor_id`, `as_of_date` |

**Optional params:** `general_ledger_detail` accepts `account_number`. `ar_aging` accepts `customer_id`. `ap_aging` accepts `vendor_id`.

**Examples:**

```
# Trial Balance
generate_report("trial_balance", {
    "legal_entity_id": 9,
    "as_of_date": "2025-12-31"
})

# Income Statement for Q1
generate_report("income_statement", {
    "legal_entity_id": 9,
    "start_date": "2025-01-01",
    "end_date": "2025-03-31"
})

# AP Aging
generate_report("ap_aging", {
    "legal_entity_id": 9,
    "as_of_date": "2025-01-15"
})

# Account Activity for a specific account
generate_report("account_activity", {
    "legal_entity_id": 9,
    "account_number": "4000",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31"
})

# Vendor Aging Detail for a specific vendor
generate_report("vendor_aging_detail", {
    "legal_entity_id": 9,
    "vendor_id": 42,
    "as_of_date": "2025-01-15"
})
```

---

## Dated AP/AR aging and reversal history

AP/AR aging uses dated application history and booked functional control amounts.
AP includes AP documents only; card charges, payroll and reclassification journals
are not unpaid bills. Credits and unapplied payments can be negative open items.
Keep document currency separate from the report's functional `currency`.

Check `success`, `certified`, `balance_basis`, `application_history_exceptions` and
`control_tie_out` before stating that aging ties to the ledger. A party-filtered
report does not certify the whole control account. `totals.overdue` is the sum of
the four past-due buckets (1–30, 31–60, 61–90, 90+), computed by the server: quote
it instead of adding buckets. It is null when the buckets are withheld and can be
negative when credits exceed past-due documents. `truncated`/`returned_count`
describe row limits; summary totals cover the full result. Legacy reports before
`history_available_from` can refuse because a cutover snapshot cannot reconstruct
past applications. Do not substitute today's amount_due or invent a payment date.
New applications use the later document date as their effective date and retain
an independent recording timestamp; undo is effective when performed, except that a
reversed card settlement journal stops counting from the reversal's accounting date. A missing
pre-cutover history check warns at close and requires reviewed historical evidence;
a demonstrated control difference remains blocking.

GL reports include both original and reversing journals at their own dates.
Filtering out reversed originals while retaining reversals creates a false balance.

## Consolidated Reports

Multi-entity reports — raw cross-entity aggregation. Intercompany eliminations are NOT implemented: intercompany balances remain in the totals.

| Report Type | Description | Required Params |
|-------------|-------------|-----------------|
| `consolidated_trial_balance` | Combined trial balance | `entity_ids`, `as_of_date` |
| `consolidated_balance_sheet` | Combined balance sheet | `entity_ids`, `as_of_date` |
| `consolidated_income_statement` | Combined P&L | `entity_ids`, `start_date`, `end_date` |
| `entity_comparison` | Side-by-side entity metrics | `entity_ids`, `start_date`, `end_date` |

**Optional:** `reporting_currency` — convert every entity to one currency (a missing exchange rate is an error).

**Examples:**

```
# Consolidated Balance Sheet across 3 entities
generate_report("consolidated_balance_sheet", {
    "entity_ids": [9, 10, 11],
    "as_of_date": "2025-12-31"
})

# Entity Comparison - side by side
generate_report("entity_comparison", {
    "entity_ids": [9, 10],
    "start_date": "2025-01-01",
    "end_date": "2025-12-31"
})

# Consolidated P&L converted to one currency
generate_report("consolidated_income_statement", {
    "entity_ids": [9, 10, 11],
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "reporting_currency": "EUR"
})
```

---

## Tax Reports

Tax compliance and reporting.

| Report Type | Description | Required Params |
|-------------|-------------|-----------------|
| `sales_tax_summary` | Tax by jurisdiction | `legal_entity_id`, `start_date`, `end_date` |
| `tax_filing_worksheet` | Filing preparation data | `legal_entity_id`, `start_date`, `end_date`, `jurisdiction` |
| `vat_report` | VAT input/output summary | `legal_entity_id`, `start_date`, `end_date` |
| `1099_report` | 1099 vendor payments | `legal_entity_id`, `tax_year` |
| `tax_exemption` | Exempt transactions | `legal_entity_id`, `start_date`, `end_date` |

**Optional:** `1099_report` accepts `vendor_global_id` and `minimum_amount` (default: 600).

**Examples:**

```
# Sales Tax Summary for Q1
generate_report("sales_tax_summary", {
    "legal_entity_id": 9,
    "start_date": "2025-01-01",
    "end_date": "2025-03-31"
})

# 1099 Report for tax year
generate_report("1099_report", {
    "legal_entity_id": 9,
    "tax_year": 2025
})

# VAT Report
generate_report("vat_report", {
    "legal_entity_id": 9,
    "start_date": "2025-01-01",
    "end_date": "2025-03-31"
})
```

---

## Operational Reports

Business operations analysis.

| Report Type | Description | Required Params |
|-------------|-------------|-----------------|
| `revenue_by_customer` | Customer revenue ranking | `legal_entity_id`, `start_date`, `end_date` |
| `revenue_by_item` | Product/service revenue | `legal_entity_id`, `start_date`, `end_date` |
| `expense_by_vendor` | Vendor spend ranking | `legal_entity_id`, `start_date`, `end_date` |
| `expense_by_category` | Expense by account type | `legal_entity_id`, `start_date`, `end_date` |

**Optional:** `revenue_by_customer`, `revenue_by_item`, `expense_by_vendor` accept `top_n` (default: 20).

**Examples:**

```
# Top 10 Customers by Revenue
generate_report("revenue_by_customer", {
    "legal_entity_id": 9,
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "top_n": 10
})

# Expense by Category
generate_report("expense_by_category", {
    "legal_entity_id": 9,
    "start_date": "2025-01-01",
    "end_date": "2025-12-31"
})
```

---

## Banking Reports

Cash management and reconciliation.

| Report Type | Description | Required Params |
|-------------|-------------|-----------------|
| `cash_position` | Current cash across accounts | `legal_entity_id` |

**Optional:** `cash_position` accepts `as_of_date`. Reconciliation status is `generate_report("reconciliation_status", ...)`.

**Examples:**

```
# Cash Position
generate_report("cash_position", {
    "legal_entity_id": 9
})
```

---

## Allocation Reports

Cost allocation analysis.

| Report Type | Description | Required Params |
|-------------|-------------|-----------------|
| `allocation_waterfall` | Step-by-step allocation flow | `legal_entity_id`, `schedule_number` |

**Examples:**

```
# Allocation Waterfall for specific rule
generate_report("allocation_waterfall", {
    "legal_entity_id": 9,
    "schedule_number": "ALLOC-0007"
})
```

---

## Dimension Reports

Analysis by dimension (department, location, project, cost center).

| Report Type | Description | Required Params |
|-------------|-------------|-----------------|
| `dimension_analysis` | Financials by dimension | `legal_entity_id`, `dimension_type_name`, `start_date`, `end_date` |
| `dimension_hierarchy` | Hierarchical rollup | `legal_entity_id`, `dimension_type_name`, `start_date`, `end_date` |

**Optional:** `dimension_analysis` accepts `account_type`.

**Examples:**

```
# Revenue by Department
generate_report("dimension_analysis", {
    "legal_entity_id": 9,
    "dimension_type_name": "department",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "account_type": "revenue"
})

# Expense Hierarchy by Cost Center
generate_report("dimension_hierarchy", {
    "legal_entity_id": 9,
    "dimension_type_name": "cost_center",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31"
})
```

---

## Budget Reports

Budget variance analysis. Uses `budget_version_id` instead of entity/date parameters. Find budget versions using `query("budget_version")`.

| Report Type | Description | Required Params |
|-------------|-------------|-----------------|
| `variance_summary` | High-level budget vs actual | `budget_version_id` |
| `variance_by_account` | Account-level variance | `budget_version_id` |
| `variance_by_period` | Variance trend by period | `budget_version_id` |

**Optional:** `variance_by_account` accepts `account_type`.

**`budget_actual` subtotals (exact contract).** Use the server's subtotals; never add rows:
- `totals.revenue` / `totals.cost` / `totals.net` cover the completed (elapsed) periods.
- `totals.by_period_section[]` gives `{period_sequence, section: "revenue"|"cost", budget, actual, variance}` for every period, ordered by period, then section. Revenue is `revenue`/`income` accounts and cost is `expense`/`cogs`.
- `totals.by_group_completed[]` gives `{group_key, budget, actual, variance}`: every budget scope, over the completed periods only. A scope with no completed period yet is listed with a real `0.00`, not left out.
- `variance` is actual − budget.
- A `by_period_section` figure is null when scopes overlap, when any figure in it is unavailable, or when the engine found ledger lines it cannot classify (gap `BUDGET_SOURCE_INCOMPLETE`): then every `by_period_section` figure is null. A `by_group_completed` figure is null when any completed part of it is unavailable. Both lists are absent when dimension evidence is incomplete: say the figure is unavailable, never 0.
- Never net revenue against cost per period from these lists. Colour or judge a variance only by a row's `verdict`. Subtotals carry none.

**Examples:**

```
# Budget Variance Summary
generate_report("variance_summary", {
    "budget_version_id": 5
})

# Variance by Account (expenses only)
generate_report("variance_by_account", {
    "budget_version_id": 5,
    "account_type": "expense"
})

# Variance Trend by Period
generate_report("variance_by_period", {
    "budget_version_id": 5
})
```

---

## Output Structure

All reports return a consistent structure:

### Success Response

```json
{
    "success": true,
    "data": { ... },
    "_report_metadata": {
        "report_type": "trial_balance",
        "display_name": "Trial Balance",
        "category": "financial"
    }
}
```

### Error Response

```json
{
    "success": false,
    "error": "Missing required parameters: legal_entity_id",
    "report_type": "trial_balance",
    "required_params": ["legal_entity_id", "as_of_date"],
    "optional_params": []
}
```

---

## Discovering Reports

Use `generate_report("list")` to explore available reports before generating:

```
# All reports
generate_report("list")

# Filter by category
generate_report("list", {"category": "financial"})
generate_report("list", {"category": "tax"})
generate_report("list", {"category": "consolidated"})
generate_report("list", {"category": "banking"})
generate_report("list", {"category": "allocation"})
generate_report("list", {"category": "dimension"})
generate_report("list", {"category": "budget"})
generate_report("list", {"category": "operational"})
```

Response includes report type identifier, display name, category, description, and required/optional parameters.

---

## Tips & Best Practices

1. **Discover first** - Use `generate_report("list")` to find available reports and required parameters before generating.

2. **Point-in-time vs Period** - Balance reports (`trial_balance`, `balance_sheet`, `ar_aging`) use `as_of_date`. Activity reports (`income_statement`, `account_activity`) use `start_date`/`end_date`.

3. **Single-entity vs Consolidated** - Use `legal_entity_id` for single-entity reports. Use `entity_ids` array for consolidated reports across multiple entities.

4. **Date format** - Always use YYYY-MM-DD format (e.g., "2025-12-31").

5. **Check the response** - Always check `success` field before processing data. Error responses include `required_params` to help fix missing parameters.

6. **Budget reports** - Budget reports use `budget_version_id` instead of entity/date parameters. Find budget versions using `query("budget_version")`.

7. **Aging reports** - AR/AP aging shows balances grouped by aging buckets (current, 1-30, 31-60, 61-90, 90+ days). Use `vendor_aging_detail` for invoice-level detail on a specific vendor.

8. **SaaS metrics** - MRR/ARR reports are point-in-time. Churn is a period report. CLV and cohort are cumulative analyses.

### Interpreting AP/AR report evidence

Only documents with AP/AR control exposure belong in the respective subledger.
Bank-only refunds and prepayments without such control entries are excluded;
refunds/prepayments that do touch the control remain included. Missing control
currency evidence on invoices or payments remains an exception.

`amount_paid` is an invoice/debit-memo header counter, not a payment's consumed
capacity. Payment-side availability comes from application evidence; a zero payment
header does not by itself prove that a payment is unapplied. Check the report's
`certified`, `application_history_exceptions` and `control_tie_out` fields.


### Cash-flow opening balance fields

OPENING_ENTRY is shown separately in opening_balance_adjustments, not operating cash flow. opening_balance + opening_balance_adjustments + net_change_in_cash = closing_balance. Reversals follow original transaction-type classification. Generic journals still require classification review.


### Balance-sheet asset classification

The single-entity `balance_sheet` maps canonical account subtypes into its existing
presentation groups. Cash, bank, cash equivalents, bank clearing, trade/related-party
receivables (including doubtful-debt allowances), contract assets, prepayments,
inventory (including obsolescence reserves), recoverable VAT/tax, employee advances
and other current assets appear in `current_asset`. Fixed-asset cost and right-of-use
assets appear in `fixed_asset`; ROU accumulated depreciation joins
`accumulated_depreciation`. Goodwill and accumulated amortisation join
`intangible_asset`.

Legacy group subtypes remain supported. Restricted cash, maturity-dependent assets
such as loans/security deposits, other non-current assets and unknown/custom subtypes
remain in `other_asset`; this report does not infer maturity or use account numbers.
Each account retains its original subtype and signed balance. Contra balances reduce
their group subtotal. Overall totals, suspense handling and the flat `assets.accounts`
compatibility list are unchanged. This is report presentation only: no account or
journal data migration is needed. Consolidated report output is unchanged.

GL search filters rows after balance calculation. Read `details.balance_scope`, matching totals and matching line count separately from account opening/closing totals. Budget summary tiles cover completed periods; grids may include future plan periods. Legacy NULL header currency uses the entity label, while explicit mismatches or missing GL functional amounts remain gaps.

## Ledger audit diagnostics

The repository operations script `mcp-server/scripts/audit_ledger_invariants.py` is
a read-only census, not an MCP report or repair tool. Its exact structural counts
are distinct from report eligibility and reviewed dispositions. `unsupported` and
`error` checks are unresolved, not zero defects. `checks_clean` covers only the
implemented checks; `production_acceptance` remains false. Continue to interpret
each report's quality and nullable amounts independently. Never present an audit
as authorization to repair or as proof of a production release.

## Dimension conditions (backend rollout)

For supported exact reports, supply `report_contract: 1` and `dimension_filter`:
`{"conditions":[{"dimension_type_id":1,"operator":"is_any_of","value_ids":[10]}],"connectors":[]}`.
IDs are entity-valid master identities; parent IDs include current effective
descendants. Operators: `is_any_of`, `is_none_of`, `is_empty`, `is_not_empty`; AND
binds before OR. Negative membership includes untagged lines. Never drop an invalid
filter, replace it with an empty selection, or combine it with `dimension_value_code`.

The current branch implements ledger/TB, statements/trend, cash, AP/AR aging, assets,
sales tax and budget actuals, with controls on the eleven report pages. Unsupported
types reject the filter. Deployment requires migrations 649–656 and matching server code.
Read `details.dimension_selection`: aging uses full document balances after all
dated payments; cash flow uses whole transactions. These selections are non-additive
and do not certify a dimensional control/cash bridge. Cash position uses tagged
cash lines, in its totals and its 30-day series. Statement/ledger reconciliation
compares selected lines only, not the whole entity. Keep the same request and cursor
for later pages and exports.


### Extended dimension selection (branch implementation, not deployed)

Exact-contract asset, sales-tax and budget reports accept the same strict
`dimension_filter`. Read `details.dimension_selection`: asset selection uses current
assignments; tax selects whole linked components, including evidenced reversals;
budget actuals intersect stored scopes, while partially selected budgets remain
unallocated. Preserve nulls and disclose non-additivity where indicated. Retained CSV
exports include selection metadata even for empty results. Report-page controls preserve selections through comparisons, paging, browser
navigation and statement-to-GL links. Representative release performance verification
remains open. No production rollout is claimed.


The optional database identity certificate (migrations 665–668) changes performance only.
Do not infer report completeness from certification: continue reading `quality` and
all evidence gaps. Uncertified tenants run the full dimension evidence scan.
Certification does not change AP/AR membership or dimension-selection semantics.

Query-planning changes in the unreleased 669–670 follow-up do not alter this contract.
A dated application uses its latest effective history version, including undo and
retargeting. Continue honoring server quality/evidence fields and selection disclosure.
The subsequent 671 tax evidence probe preserves all completeness rules; a faster
incomplete response is still incomplete and must not be presented as certified.


The unreleased ledger-hardening audit's `account_document_impacts` is a read-only
transition inventory, not a new report membership rule. Its whole-document balances
come from the existing aging report. Never use the manual-only or mixed categories
to subtract amounts from an aging report or claim that a scope change was applied.
Mixed/unresolved documents require reviewed historical treatment; incomplete source
reports withhold inventory amounts. No change to `is_reconcilable` is required.


Account-policy migrations 672–673 add a shared calculation used by the impact audit.
`proposed_subledger_scope` is a proposal, not evidence of live aging membership.
Inactive accounts retain resolvable history but cannot receive new postings under
the proposed policy. Do not infer authorization from the helper or apply account flag
changes as an ad hoc historical repair; entity-scoped activation remains planned.


`preview_account_scope_transition.py` is an operator read-only review tool. A successful
preview still has `status=review_required` and `apply_supported=false`; neither its
configuration fingerprint nor its conditional entity-override options authorize
changes. Do not execute those options through generic account.update. Fresh financial
checks and a guarded transition remain required, and live aging membership is unchanged.


`check_account_scope_transition.py` is a privileged maintenance check, distinct from
the read-only preview. It temporarily blocks relevant tenant writes and always rolls
back. Even `limited_checks_passed` has `activation_ready=false` and
`valid_for_later_apply=false`; do not treat it as permission to change flags or as a
permanent integrity certificate. Incomplete/uncertified AP/AR reports require source
review. Operator/environment authorization is required before running it.

`guard_posting_accounts.py` is an unreleased operator tool for the narrower rule that
GL references cannot point to header/grouping accounts. Default mode audits only;
installation requires environment authorization and a maintenance window. An installed
guard also refuses turning a GL-referenced account into a header. This is not evidence
that AP/AR scope has changed or that the ledger is otherwise complete. Preserve source
gaps and existing report-quality disclosures. New clones need their own installation
check and dimension recertification after this DDL; template trigger enforcement is
not inherited in full. Never repair a refusal by deleting posted GL or toggling manual
flags. Manual-entry enforcement and reviewed account transitions remain unfinished.


The header-account guard now also checks populated posting-profile sides. Its aggregate
status can be incomplete while the earlier GL guard remains installed; use the
per-reference operator evidence. Invalid existing profiles require configuration
review, not a report adjustment or an automatic header/manual-flag change. Template
initialization exposes skipped profiles in `summary.posting_profile_setup_gaps`.

### Dated reversals of applied documents

From a posted reversal's accounting date, applications involving the reversed
invoice, credit or payment no longer consume either document's open amount.
Before that date the recorded application remains effective. This applies to AP
and AR in both operational open-item queries and report snapshots. Ordinary
unapply still takes effect when performed; the immutable application history is
not rewritten. Rerun aging after migration 648 to obtain a fresh snapshot; an
existing report snapshot retains its original result. Control mismatches and
missing history remain explicit failures of certification.

A card settlement against a bill is undone by reversing its settlement journal (the
card reclass). An ordinary undo is dated on the day it is done; a historical undo can
date the reversal earlier. From that reversal's accounting date the settlement no
longer consumes the bill, even when the match itself is recorded as voided later, on
the day the undo was done. A re-match therefore counts once in an aging as of any
date (migration 868). This applies to card settlements only; reversing a
write-off or FX journal does not undo the payment it adjusts.


Migration 685 adds operator-only before/after calculation via
`preview_account_scope_transition.py --compare-reports`. It selects all historical
documents using canonical AP/AR subtype and effective `allow_manual_entries=false`;
inactive control history stays visible and `is_reconcilable` is not a membership gate.
Confirmed manual-only documents leave the candidate; mixed/unresolved documents keep
an evidence gap. Current report source gaps also prevent candidate certification.
`comparison_complete` is comparison evidence only: `apply_supported=false` and
`membership_activated=false` remain. Live reports still use existing membership.
Do not present candidate totals as deployed reports or alter flags to force a tie-out.

For deployments including migration 691, new settlement history keeps later write-off
and FX journals out of earlier aging dates. An application created with a later
adjustment records both the application-only and adjusted states. Older captured
history is unchanged and needs operator review where the adjustment predates its
journal. Do not describe installation as historical repair or AP/AR scope activation.

### Month-end close evidence

A completed dry-run means checks finished, not that the period is ready to close.
Direct fiscal_period.close rejects dry-run evidence and completed runs with missing
or failed blocking checks. Use the live close workflow after resolving findings;
an owner override remains explicit and audited. Posted depreciation counts as run
coverage; settled invoices count for billing only when linked to the actual
contract. AP/AR control lines are excluded from document tax validation. Bank
statement differences and incomplete payroll settlements must still be resolved.

### Dimension-selection labels (unreleased integration)

MCP and dashboard use identical report labels. A control comparison that does not
apply is labelled “Not compared for this selection”, covering both party and
dimension selection. Filter/contract refusals use explanatory sentences. Internal
error identifiers remain diagnostic fields rather than user-facing replacement text.


### Native carrying receipts in dated aging (unreleased, migration 700)

Aging consumes exact functional allocations from native payment GL receipts after
checking document/functional/reporting totals, currencies and dated application
history. Later reversal or unapply events affect only their effective dates onward.
Do not recompute a receipt-backed balance using the invoice's original FX ratio.
If receipt/application evidence is inconsistent, respect the withheld balance and
incomplete totals; request review rather than supplying an estimated amount.
Entirely receiptless legacy payments keep the existing calculation; no legacy
repair or agent partial-FX authority is implied. Live account membership, candidate
activation rules and full-document dimension selection are unchanged. Rerun after
deployment; immutable saved snapshots retain their original result.


### GL display precision and totals

GL and Account activity retain every selected row in their snapshot. Displayed
amounts use functional-currency precision; matching totals and running balances
are calculated from unrounded ledger values first. Do not recompute server totals
by adding rounded displayed rows. Search filters displayed lines after running
balances are computed. Missing evidence keeps amounts unavailable. Migration 723
changes formatting cost only, not eligibility, dimensions, signs or row coverage.


### Aging settlement-history extraction

Migration 724 reduces repeated JSON extraction in the reporting AP/AR open-item
helpers. The latest dated history, reversal exclusions, independent source/target
amounts and missing-basis rules remain authoritative. It changes no live aging
membership, allocation evidence requirement or activation policy. Performance
acceptance is separate from report equality; incomplete evidence stays incomplete.


Migration 726 (unreleased) accelerates native receipt lookup using a partial GL
index. It changes neither receipt validation nor eligibility, amounts or evidence
gaps. Do not treat the presence of the index as accounting certification or full
benchmark acceptance. Operators must follow the concurrent prebuild and post-DDL
certification procedure in platform operations.

### Reviewed mixed-journal performance (migration 730; application rollout pending)

A balanced ordinary journal can mix current-period income/expense and a separate
retained-earnings adjustment. A privileged operator may explicitly confirm
`current_period_pnl` using `scripts/report_disposition.py --performance-treatment
current_period_pnl`. This confirms that its P&L lines belong to their existing
accounting date; it does not date-shift amounts or assert that every source amount
is economically correct. Closing/opening/reversal entries are ineligible.

The latest review must match the stable transaction header, exact functional GL
amounts, account identities and effective account classifications. A mismatch
restores the ambiguity block. Other source gaps remain blocking. The normal
reviewed-disposition warning remains visible. The treatment never changes GL,
eligibility, closing status, cash classification or aging membership. Existing
cash-flow decisions are preserved. Do not use a closing-year decision to suppress
this ambiguity: that would remove current-period P&L.


### Account activity and general-ledger reconciliation (migration 731; production SQL verified 2026-10-12)

For account activity and general-ledger detail, `details.reconciliation` checks
opening balance + period debits - period credits = closing balance for each
selected account. It does not require an individual account balance to be zero.
`basis` is `account_roll_forward`; `difference` is the sum of absolute per-account
residuals, so opposite errors cannot cancel. Search affects displayed rows only;
the proof covers the complete account selection. A missing required amount or a
blocking totals gap yields `unavailable`, never a false tie. Trial-balance
reconciliation keeps its existing debit/credit rule. This arithmetic proof does
not certify completeness or economic correctness of the underlying journals.

## Account and reporting-decision observability (deployed 2026-10-14)

Migration 737 exposes `master_updated_at` and `entity_updated_at` on account reads.
`updated_at` is the later timestamp; `updated_by` follows that source (master wins
on equal timestamps). An old override timestamp no longer masks a master update.
No stored timestamps are rewritten.

`query(entity_type="reporting_decision", filters={"legal_entity_id": ENTITY,
"transaction_id": TRANSACTION})` and `get_entity` expose read-only decision status.
`is_latest` identifies superseded decisions. `header_matches` checks the saved header;
`ledger_decision_applies` requires both a matching header and the latest decision.
`performance_evidence_matches` checks the saved line/classification evidence;
`performance_review_valid` also requires the latest decision and the existing report
predicate. A false performance flag does not invalidate an otherwise matching ledger
eligibility decision. It does not prove a report needs that performance exception:
ordinary classification may already resolve the ambiguity. Review-note attachments
are separate. These diagnostics do not renew decisions or change report calculations.

Account master updates write `account_updated` to the organization-scoped audit log
in the same transaction, with actor, account ID and before/after master fields. Audit
failure rolls back the change. Query `audit_log` by `record_id` and `table_name` to
find it. This adds future audit entries; it does not fabricate missing historical
entries. Existing workflow history remains the record for earlier changes.


### Dashboard error guidance (QA branch)

Shared list, report, account-activity and agent-settings fallback messages refer
to your assistant, without prescribing Claude. Use the page’s assistant chooser
where available, or ask in your connected client. Existing retry actions and
report error classification are unchanged: raw internal report errors stay
hidden, while authored report refusals retain their specific explanation.
Opening an assistant does not repair data or certify a report.

Bespoke cash-position, sales-tax, asset-register, general-ledger, balance-sheet,
income-statement and budget-versus-actual guidance also refers to your assistant.
These copy changes do not certify incomplete results or change report refusal,
retry, budget creation or permission behavior.


## Close evidence update (b1, awaiting deployment)

Close financial sums use the reporting ledger eligibility view, including applicable reviewed dispositions. A posted timestamp alone is not eligibility. Dated original/reversal pairs remain in historical balances; live settlement additionally needs an unreversed eligible document. Structural checks still inspect retained invalid journals. This can change a close result in either direction; require the deployment impact preview.
