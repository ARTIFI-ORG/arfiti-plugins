# Budget Management

## Dimension selection (branch implementation)

The branch implementation (migration 644; not deployed) accepts the shared
`dimension_filter` on exact-contract budget reports. Actuals must match both the
stored budget scope and the report selection. Omitted budget dimensions are
wildcards. Fully included scopes retain their whole budget; disjoint scopes are
excluded. A partial intersection has selected actuals but a null, unallocated
budget and no variance verdict. Dependent aggregate budgets/variances remain null;
do not prorate or replace them with zero. Overlapping scopes inside the selection
still block additive totals.

## Report correctness contract (migration 630)

Variance reports now use the shared SQL report engine (migration 630). Require version and line currency to equal functional currency. Match every stored dimension, optional party and project; overlapping scopes are not additive. Custom periods take precedence over validated fiscal periods. Zero variance is neutral; future/partial periods are unassessed. Unbudgeted P&L residuals stay visible, while balance-sheet accounts appear only when budgeted. Prefer the exact `budget_actual` report; read its quality, coverage and effective cutoff.

Requires the matching migration/server release; code availability is not deployment evidence.

> **MSEO release contract:** Budget dimension IDs already identify masters. Preserve supplied amounts and classification IDs, including during version copy. Detailed variance uses stored classification scope and actual fiscal-period boundaries; overlapping scopes are not additive. See the dimensions-management resource for assignment, approval and compatibility rules.

Comprehensive guide to multi-version budgeting with approval workflows, variance analysis, dimension tagging, and project/employee budgeting.

## Available Workflows

**IMPORTANT:** Budget workflows use **separate operations** (not unified `manage` with `action` field) for granular permission control. This differs from project workflows which use the `manage` pattern.

| Object Type | Operation | Description | Typical lane |
|-------------|-----------|-------------|------|
| `budget_version` | `create` | Create new budget version | Green |
| `budget_version` | `update` | Update version metadata | Yellow |
| `budget_version` | `delete` | Delete draft/submitted budget | Red |
| `budget_line` | `create` | Add budget line | Green |
| `budget_line` | `update` | Update line amount/description | Yellow |
| `budget_line` | `delete` | Delete budget line | Red |
| `budget_line` | `bulk_upsert` | Insert/update multiple lines | Green |
| `budget_template` | `create` | Create reusable template | Green |
| `budget_template` | `update` | Update template | Yellow |
| `budget_template` | `delete` | Delete template | Red |
| `budget_period` | `create` | Add custom period | Green |
| `budget_period` | `update` | Update period | Yellow |
| `budget_period` | `delete` | Delete period | Red |
| `budget_import` | `create` | Start import batch | Green |
| `budget_import` | `update` | Update import progress | Green |
| `budget_import` | `cancel` | Cancel import | Yellow |
| `budget_line_dimension` | `create` | Add dimension to line | Green |
| `budget_line_dimension` | `delete` | Remove dimension | Yellow |
| `budget_line_dimension` | `bulk_set` | Replace all dimensions | Green |
| `budget_workflow` | `submit` | Submit for approval | Yellow |
| `budget_workflow` | `approve` | Approve budget | Yellow |
| `budget_workflow` | `reject` | Reject to draft | Yellow |
| `budget_workflow` | `lock` | Lock approved budget | Red |
| `budget_workflow` | `archive` | Archive budget | Red |
| `budget_workflow` | `reopen` | Reopen to draft | Red |

Lanes are assigned by your organisation's workflow rules; the submit() result is authoritative.

**Total:** 25 workflow operations

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

## Available Query Tools

| Tool | Purpose |
|------|---------|
| `get_entity("budget_version", id=X)` | Get single budget version (includes `entity_name` inline) |
| `query("budget_version", filters)` | List versions with filters and pagination |
| `query("budget_version", query, filters)` | Search versions by text |
| `query("budget_version", filters, limit=1)` | Count matching versions (use `total_count` from response) |
| `get_entity("budget_line", id=X)` | Get single budget line (includes `account_number_display`, `period_name` inline) |
| `query("budget_line", filters)` | List lines with filters |
| `query("budget_line", query, filters)` | Search budget lines |
| `generate_report("variance_summary", ...)` | Calculate budget vs actual variance |
| `query("budget_line", group_by, aggregates, filters)` | Aggregate budget lines (e.g., total by account, by period) |
| `query(entity_type, filters={...})` ×N | Fetch reference data (issue the calls in parallel) (accounts, periods, dimensions) |

**Virtual fields (resolved inline — no extra lookups needed):**
- `budget_version`: `entity_name` — legal entity name
- `budget_line`: `account_number_display` — e.g., "4000 - Sales Revenue", `period_name` — e.g., "January 2025"

**Key notes:**
- `get_entity` defaults to `include_related=True` — related data is included automatically
- Use `query` (not `query`) for filter-based queries without text search

---

## Complete Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

### Budget Versions Table (budget_versions)

| Field Name | Data Type | Required | Description | Example |
|------------|-----------|----------|-------------|---------|
| `id` | bigint | PK | System-generated ID | `5` |
| `legal_entity_id` | integer | Yes | Legal entity ID | `13` |
| `version_name` | varchar(100) | Yes | Budget name | `"FY2025 Operating Budget"` |
| `version_type` | varchar(20) | Auto | Granularity | `"annual"`, `"quarterly"`, `"monthly"` |
| `fiscal_year` | integer | Yes | Fiscal year | `2025` |
| `status` | varchar(20) | Auto | Approval status | `"draft"`, `"submitted"`, `"approved"`, `"locked"`, `"archived"` |
| `is_active` | boolean | Auto | Active flag | `true` |
| `scenario` | varchar(50) | No | Budget scenario | `"budget"`, `"forecast"`, `"stretch"`, `"actual_snapshot"` |
| `template_id` | bigint | No | FK to budget_templates | `1` |
| `currency_code` | varchar(3) | Auto | Currency | `"USD"` |
| `version_number` | integer | Auto | Sequential version | `1`, `2`, `3` |
| `owner_user_id` | integer | No | Budget owner | `30` |
| `notes` | text | No | Description/notes | `"Annual operating budget"` |
| `submitted_at` | timestamp | Auto | Submission timestamp | `2025-01-15 10:00:00-08` |
| `submitted_by` | integer | Auto | User ID who submitted | `30` |
| `approved_at` | timestamp | Auto | Approval timestamp | `2025-01-16 14:00:00-08` |
| `approved_by` | integer | Auto | User ID who approved | `12` |
| `locked_at` | timestamp | Auto | Lock timestamp | `2025-02-01 09:00:00-08` |
| `locked_by` | integer | Auto | User ID who locked | `12` |
| `created_at` | timestamp | Auto | Creation timestamp | `2025-01-15 10:00:00-08` |
| `created_by` | integer | Auto | User ID who created | `30` |
| `updated_at` | timestamp | Auto | Last update timestamp | `2025-01-15 10:00:00-08` |
| `updated_by` | integer | Auto | User ID who updated | `30` |

### Budget Lines Table (budget_lines)

| Field Name | Data Type | Required | Description | Example |
|------------|-----------|----------|-------------|---------|
| `id` | bigint | PK | System-generated ID | `42` |
| `budget_version_id` | bigint | Yes | FK to budget_versions | `5` |
| `legal_entity_id` | integer | Yes | Legal entity ID | `13` |
| `account_number` | varchar(50) | Yes | GL account | `"4000"`, `"6100"` |
| `amount` | numeric(15,2) | Yes | Budgeted amount | `50000.00` |
| `period_sequence` | integer | No | Period (1-12 for monthly) | `1` (January) |
| `currency_code` | varchar(3) | Auto | Currency | `"USD"` |
| `description` | text | No | Line description | `"Q1 Revenue - Product Sales"` |
| `memo` | text | No | Additional notes | `"Based on 10% YoY growth"` |
| `source` | varchar(50) | Auto | Source type | `"manual"`, `"formula"`, `"import"`, `"template"`, `"copy"` |
| `project_id` | integer | No | FK to projects | `45` |
| `customer_id` | integer | No | FK to customers | `123` |
| `vendor_id` | integer | No | FK to vendors | `456` |
| `dimension_combo_json` | jsonb | Auto | Dimension snapshot | `{"department":"ENG","location":"NYC"}` |
| `dimension_combo_hash` | text | Auto | Hash for uniqueness | `"a1b2c3d4..."` |
| `created_at` | timestamp | Auto | Creation timestamp | `2025-01-15 10:00:00-08` |
| `created_by` | integer | Auto | User ID who created | `30` |
| `updated_at` | timestamp | Auto | Last update timestamp | `2025-01-15 10:00:00-08` |
| `updated_by` | integer | Auto | User ID who updated | `30` |

### Budget Templates Table (budget_templates)

| Field Name | Data Type | Required | Description | Example |
|------------|-----------|----------|-------------|---------|
| `id` | bigint | PK | System-generated ID | `1` |
| `legal_entity_id` | integer | Yes | Legal entity ID | `13` |
| `template_name` | varchar(255) | Yes | Template name | `"Standard Operating Budget"` |
| `template_code` | varchar(50) | Yes | Unique code | `"OPEX-STD"` |
| `description` | text | No | Description | `"Standard template for OPEX budgets"` |
| `granularity` | varchar(50) | Yes | Period granularity | `"monthly"`, `"quarterly"`, `"annual"` |
| `fiscal_year` | integer | No | Template year | `2025` |
| `dimension_coverage` | jsonb | No | Dimensions used | `{"department":["SALES","ENG"],"location":["NYC"]}` |
| `is_active` | boolean | Auto | Active status | `true` |
| `created_at` | timestamp | Auto | Creation timestamp | `2025-01-15 10:00:00-08` |
| `created_by` | integer | Auto | User ID who created | `30` |
| `updated_at` | timestamp | Auto | Last update timestamp | `2025-01-15 10:00:00-08` |
| `updated_by` | integer | Auto | User ID who updated | `30` |

### Budget Line Dimensions Table (budget_line_dimensions)

| Field Name | Data Type | Required | Description | Example |
|------------|-----------|----------|-------------|---------|
| `budget_line_id` | bigint | PK | FK to budget_lines | `42` |
| `dimension_type_id` | integer | PK | FK to master_dimension_types | `1` |
| `dimension_value_id` | bigint | Yes | FK to master_dimension_values | `10` |
| `dimension_type_name` | varchar(100) | Auto | Type name (denormalized) | `"DEPARTMENT"` |
| `dimension_value_code` | varchar(100) | Auto | Value code (denormalized) | `"ENG"` |
| `created_at` | timestamp | Auto | Creation timestamp | `2025-01-15 10:00:00-08` |

---

## Workflow Documentation

### Budget Version Workflows

#### Create Budget Version

Create a new budget version for a fiscal year.

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="budget_version", operation="create")

// Step 2: Submit with discovered fields
submit("budget_version", "create", {
    legal_entity_id: 13,
    version_name: "FY2025 Operating Budget",
    fiscal_year: 2025,
    scenario: "budget",
    version_type: "monthly",
    currency_code: "USD",
    notes: "Annual operating budget for 2025"
})
// Tip: Use validate_only=true to check payload before submitting
```

**Returns:**
```javascript
{
  success: true,
  budget_version_id: 5,
  version_number: 1,
  status: "draft"
}
```

**Scenarios:**
- `budget` - Baseline annual budget (start of fiscal year)
- `forecast` - Updated projections (mid-year revisions)
- `stretch` - Aspirational targets (goal setting)
- `actual_snapshot` - Point-in-time actuals (historical comparison)

**Version Types:**
- `annual` - 1 period (high-level planning)
- `quarterly` - 4 periods (Q1-Q4, executive reporting)
- `monthly` - 12 periods (detailed operations)

#### Copy Budget from Previous Year

Create a new budget by copying from previous version.

```javascript
submit("budget_version", "create", {
    legal_entity_id: 13,
    version_name: "FY2025 Operating Budget",
    fiscal_year: 2025,
    scenario: "budget",
    copy_from_version_id: 3,  // 2024 budget
    copy_lines: true,  // Copy all budget lines
    notes: "Rolled forward from 2024 baseline"
})
```

**Returns:**
```javascript
{
  success: true,
  budget_version_id: 6,
  version_number: 2,
  copied_lines: true,
  source_version_id: 3
}
```

#### Create Forecast from Budget

Create mid-year forecast based on approved budget.

```javascript
submit("budget_version", "create", {
    legal_entity_id: 13,
    version_name: "FY2025 Q2 Forecast",
    fiscal_year: 2025,  // Same year
    scenario: "forecast",  // Different scenario
    copy_from_version_id: 5,  // Current budget
    copy_lines: true,
    notes: "Q2 forecast based on Q1 actuals"
})
```

#### Update Budget Version

Update metadata (name, notes, owner).

```javascript
submit("budget_version", "update", {
    budget_version_id: 5,
    version_name: "FY2025 Operating Budget v2",
    notes: "Revised operating budget after Q1 review",
    owner_user_id: 12
})
```

**Validation:**
- Can only update if status = `draft` or `submitted`
- Cannot update if status = `approved`, `locked`, or `archived`

#### Delete Budget Version

Soft-delete budget version (sets is_active = false).

```javascript
submit("budget_version", "delete", {
    budget_version_id: 5
})
```

**Validation:**
- Can only delete if status = `draft` or `submitted`
- Cannot delete if status = `approved`, `locked`, or `archived`
- Cascades to budget lines and dimensions

---

### Budget Workflow Operations

#### Submit for Approval

Submit draft budget for approval.

```javascript
submit("budget_workflow", "submit", {
    budget_version_id: 5,
    comments: "FY2025 budget ready for CFO review"
})
```

**Status Change:** `draft` → `submitted`

**Validation:**
- Budget version must exist
- Current status must be `draft`
- Budget must have at least one line

#### Approve Budget

Approve submitted budget.

```javascript
submit("budget_workflow", "approve", {
    budget_version_id: 5,
    comments: "Approved by CFO"
})
```

**Status Change:** `submitted` → `approved`

**Validation:**
- Current status must be `submitted`
- Requires approve permission

#### Reject Budget

Reject submitted budget, return to draft.

```javascript
submit("budget_workflow", "reject", {
    budget_version_id: 5,
    rejection_reason: "Need to revise Q3 revenue projections"
})
```

**Status Change:** `submitted` → `draft`

**Validation:**
- Current status must be `submitted`
- rejection_reason is required

#### Lock Budget

Lock approved budget (prevent edits).

```javascript
submit("budget_workflow", "lock", {
    budget_version_id: 5,
    comments: "Locked for FY2025"
})
```

**Status Change:** `approved` → `locked`

**Effect:**
- Cannot add/update/delete budget lines
- Cannot update version metadata
- Prevents accidental modifications

#### Archive Budget

Archive old budget (historical record).

```javascript
submit("budget_workflow", "archive", {
    budget_version_id: 5,
    comments: "Archived - superseded by v2"
})
```

**Status Change:** `draft`/`approved`/`locked` → `archived`

**Effect:**
- Removes from active budget list
- Preserves historical data
- Can be reopened if needed

#### Reopen Budget

Reopen archived/submitted budget to draft.

```javascript
submit("budget_workflow", "reopen", {
    budget_version_id: 5,
    comments: "Reopened for corrections"
})
```

**Status Change:** `submitted`/`archived` → `draft`

**Validation:**
- Cannot reopen `locked` budgets (must unlock via delete/archive)

---

### Budget Status Lifecycle

```
draft → submitted → approved → locked → archived
  ↑         ↓                      ↓
  └─────(reject)              (archive)
```

**Valid Transitions:**
- `submit`: draft → submitted
- `approve`: submitted → approved
- `reject`: submitted → draft
- `lock`: approved → locked
- `archive`: draft/approved/locked → archived
- `reopen`: submitted/archived → draft

---

### Budget Line Workflows

#### Create Budget Line

Add a single budget line.

```javascript
submit("budget_line", "create", {
    budget_version_id: 5,
    account_number: "4000",
    amount: 50000.00,
    period_sequence: 1,  // January (1-12)
    currency_code: "USD",  // Optional, defaults to version currency
    description: "Q1 Revenue - Product Sales",
    memo: "Based on 10% YoY growth",
    source: "manual"
})
```

**Returns:**
```javascript
{
  success: true,
  budget_line_id: 42
}
```

**Period Sequence:**
- `1-12` for monthly budgets (1=Jan, 12=Dec)
- `1-4` for quarterly budgets (1=Q1, 4=Q4)
- `1` for annual budgets

**Source Types:**
- `manual` - Hand-entered
- `formula` - Calculated from other lines
- `import` - Bulk imported from file
- `template` - Generated from template
- `copy` - Copied from another version

#### Create Budget Line with Dimensions

Budget line with department and project tags.

```javascript
submit("budget_line", "create", {
    budget_version_id: 5,
    account_number: "6100",
    amount: 25000.00,
    period_sequence: 1,
    description: "January Salaries - Engineering",
    project_id: 45,  // Website Redesign project
    dimensions: {
      department: "ENG",
      cost_center: "ENG-001",
      location: "NYC"
    }
})
```

#### Update Budget Line

Update amount or description.

```javascript
submit("budget_line", "update", {
    budget_line_id: 42,
    amount: 55000.00,
    description: "Q1 Revenue - Revised",
    memo: "Updated after sales forecast review"
})
```

**Validation:**
- Can only update if budget status = `draft` or `submitted`
- Cannot update if budget is `locked` or `archived`

#### Delete Budget Line

Remove budget line.

```javascript
submit("budget_line", "delete", {
    budget_line_id: 42
})
```

**Validation:**
- Can only delete if budget status = `draft` or `submitted`
- Cascades to budget_line_dimensions

#### Bulk Upsert Budget Lines

Insert or update multiple lines at once (import/batch operation).

```javascript
submit("budget_line", "bulk_upsert", {
    budget_version_id: 5,
    lines: [
      {
        account_number: "4000",
        period_sequence: 1,
        amount: 50000.00,
        description: "January Revenue"
      },
      {
        account_number: "4000",
        period_sequence: 2,
        amount: 52000.00,
        description: "February Revenue"
      },
      {
        account_number: "6100",
        period_sequence: 1,
        amount: 25000.00,
        description: "January Salaries",
        dimensions: {
          department: "ENG"
        }
      }
    ]
})
```

**Returns:**
```javascript
{
  success: true,
  inserted: 2,
  updated: 1,
  total: 3
}
```

**Matching Logic:**
Lines are matched by:
- `budget_version_id`
- `account_number`
- `period_sequence`
- `project_id` (if specified)
- `customer_id` (if specified)
- `vendor_id` (if specified)
- `dimension_combo_hash` (if dimensions specified)

If match exists → UPDATE amount/description
If no match → INSERT new line

---

### Budget Template Workflows

#### Create Template

Create reusable budget structure.

```javascript
submit("budget_template", "create", {
    legal_entity_id: 13,
    template_name: "Standard Operating Budget",
    template_code: "OPEX-STD",
    granularity: "monthly",
    description: "Standard monthly OPEX budget template",
    dimension_coverage: {
      department: ["SALES", "ENG", "HR", "ADMIN"],
      cost_center: ["CC001", "CC002", "CC003"]
    },
    is_active: true
})
```

**Returns:**
```javascript
{
  success: true,
  template_id: 1
}
```

#### Update Template

Update template details.

```javascript
submit("budget_template", "update", {
    template_id: 1,
    template_name: "Standard Operating Budget v2",
    dimension_coverage: {
      department: ["SALES", "ENG", "HR", "ADMIN", "LEGAL"],
      cost_center: ["CC001", "CC002", "CC003", "CC004"]
    }
})
```

#### Delete Template

Soft-delete template (sets is_active = false).

```javascript
submit("budget_template", "delete", {
    template_id: 1
})
```

**Validation:**
- Cannot delete if referenced by active budget versions

#### Using a Template

Reference template when creating budget version.

```javascript
submit("budget_version", "create", {
    legal_entity_id: 13,
    version_name: "FY2025 OPEX",
    fiscal_year: 2025,
    scenario: "budget",
    template_id: 1  // Reference to template
})
```

---

### Budget Period Workflows

#### Create Custom Period

Define custom fiscal period (non-standard calendar).

```javascript
submit("budget_period", "create", {
    budget_version_id: 5,
    period_name: "Q1-2025",
    period_start: "2025-01-01",
    period_end: "2025-03-31",
    period_number: 1
})
```

**Use Cases:**
- 4-4-5 retail calendar
- 4-5-4 fiscal calendar
- Custom quarters (non-calendar)

#### Update Period

Update period dates or name.

```javascript
submit("budget_period", "update", {
    period_id: 10,
    period_end: "2025-04-05",  // Extend period
    period_name: "Q1-2025 Extended"
})
```

#### Delete Period

Remove custom period definition.

```javascript
submit("budget_period", "delete", {
    period_id: 10
})
```

---

### Budget Import Workflows

#### Create Import Batch

Start bulk import operation (Excel/CSV).

```javascript
submit("budget_import", "create", {
    legal_entity_id: 13,
    budget_version_id: 5,
    import_type: "excel",
    file_name: "budget_2025.xlsx",
    file_size: 45678,
    total_rows: 150
})
```

**Returns:**
```javascript
{
  success: true,
  import_batch_id: 12,
  status: "processing"
}
```

**Import Types:**
- `excel` - Excel file (.xlsx, .xls)
- `csv` - CSV file
- `api` - API import
- `manual` - Manual bulk entry

#### Update Import Progress

Track import progress and errors.

```javascript
submit("budget_import", "update", {
    import_batch_id: 12,
    successful_rows: 148,
    failed_rows: 2,
    status: "partially_completed",
    validation_errors: {
      row_45: "Invalid account number: 9999",
      row_89: "Amount must be numeric"
    }
})
```

**Import Status:**
- `processing` - In progress
- `completed` - All rows succeeded
- `failed` - Import failed
- `partially_completed` - Some rows failed

#### Cancel Import

Cancel running import operation.

```javascript
submit("budget_import", "cancel", {
    import_batch_id: 12,
    cancellation_reason: "Incorrect file uploaded"
})
```

---

### Budget Line Dimension Workflows

#### Add Dimension to Line

Tag budget line with single dimension.

```javascript
submit("budget_line_dimension", "create", {
    budget_line_id: 42,
    dimension_type_code: "DEPARTMENT",
    dimension_value_code: "ENG"
})
```

#### Remove Dimension from Line

Remove specific dimension tag.

```javascript
submit("budget_line_dimension", "delete", {
    budget_line_id: 42,
    dimension_type_code: "DEPARTMENT"
})
```

#### Bulk Set Dimensions

Replace all dimensions on a line at once.

```javascript
submit("budget_line_dimension", "bulk_set", {
    budget_line_id: 42,
    dimensions: [
      {
        dimension_type_code: "DEPARTMENT",
        dimension_value_code: "ENG"
      },
      {
        dimension_type_code: "COST_CENTER",
        dimension_value_code: "ENG-001"
      },
      {
        dimension_type_code: "LOCATION",
        dimension_value_code: "NYC"
      }
    ]
})
```

**Effect:**
- Removes all existing dimensions
- Adds new dimensions from array
- Updates `dimension_combo_json` and `dimension_combo_hash`

---

## Variance Analysis

### Overview

Budget variance analysis compares budgeted amounts to actual GL transactions. The shared `budget_actual` report calculates actuals from functional ledger amounts. Stored party/project IDs are master IDs. Match every stored dimension; unspecified dimensions are unconstrained. Headline totals compare completed periods only. Partial/future periods and exactly-on-budget rows have no favorable/unfavorable verdict. Overlapping scopes retain individual comparisons but have unavailable aggregate totals. The old `v_budget_vs_actual` view remains only for rollout compatibility.

### Favorable vs Unfavorable Logic

**Revenue Accounts:**
- Actual > Budget = **Favorable** (earned more than expected ✅)
- Actual < Budget = **Unfavorable** (earned less than expected ❌)

**Expense Accounts:**
- Actual < Budget = **Favorable** (spent less than expected ✅)
- Actual > Budget = **Unfavorable** (spent more than expected ❌)

### Variance Calculation Example

```javascript
// Revenue Account 4000
const budget = 50000.00;
const actual = 52500.00;
const variance = actual - budget;  // +2,500
const variance_percent = (variance / budget) * 100;  // +5%
const is_favorable = true;  // Earned more ✅

// Expense Account 6000
const budget = 60000.00;
const actual = 65000.00;
const variance = actual - budget;  // +5,000
const variance_percent = (variance / budget) * 100;  // +8.3%
const is_favorable = false;  // Spent more ❌
```

### Read authoritative comparisons

```python
generate_report("budget_actual", params={"legal_entity_id": 9, "budget_version_id": 5, "report_contract": 1})
```

Use `report_v1.totals` for completed-period revenue, cost and net comparisons.
`details.periods` identifies the actual custom/fiscal dates. Inspect
`details.overlap_groups` and `quality.evidence_gaps` before aggregating. Never SUM
legacy variance-view rows across overlapping parties, projects or dimensions.
Individual future-period budgets remain available in `rows`.

### Get Budget Version

```javascript
get_entity("budget_version", id=5)

// Returns (includes entity_name virtual field inline):
// {
//   id: 5,
//   legal_entity_id: 13,
//   entity_name: "US Operations",   ← resolved inline, no extra lookup
//   version_name: "FY2025 Operating Budget",
//   fiscal_year: 2025,
//   status: "approved",
//   scenario: "budget",
//   currency_code: "USD",
//   ...
// }
```

### List Budget Versions

```javascript
query("budget_version", filters={"legal_entity_id": 13, "fiscal_year": 2025, "status": "approved"})

// Returns paginated array of versions with entity_name inline
```

### Get Budget Lines

```javascript
query("budget_line", filters={"budget_version_id": 5})

// Returns lines with virtual fields:
// - account_number_display: "4000 - Sales Revenue"
// - period_name: "January 2025"
```

### Search Budget Lines

```javascript
query("budget_line", query="revenue", filters={"budget_version_id": 5})
```

### Aggregate Budget Data

Use `query` for quick budget analytics:

**Total budget by account:**
```javascript
query(
  entity_type="budget_line",
  group_by=["account_number"],
  aggregates={"amount": "sum"},
  filters={"budget_version_id": 5}
)
```

**Budget totals by period:**
```javascript
query(
  entity_type="budget_line",
  group_by=["period_sequence"],
  aggregates={"amount": "sum", "id": "count"},
  filters={"budget_version_id": 5}
)
```

---

## Best Practices

### 1. Budget Organization

**DO:**
- Use consistent granularity within fiscal year
- Tag all lines with relevant dimensions
- Create templates for recurring structures
- Document significant variances in memo fields

**DON'T:**
- Mix monthly and quarterly in same version
- Create duplicate lines (same account/period/dimensions)
- Skip dimension tagging (reduces drill-down capability)

### 2. Approval Workflow

**Recommended Flow:**
```
1. Budget owner creates draft
2. Department review and revisions
3. Submit for approval
4. Finance/CFO review
5. Approve and communicate
6. Lock at period close
```

### 3. Variance Management

**Review Cadence:**
- Monthly: Detailed variance by account
- Quarterly: Executive summary
- Annual: Full-year reconciliation

**Thresholds:**
- Flag variances above the organisation's thresholds (e.g. a percentage and an amount it sets; ask when none are set)
- Investigate unfavorable variances first
- Document explanations for audit trail

### 4. Dimension Strategy

**Common Patterns:**
```javascript
// By department and location
dimensions = {
  department: "ENG",
  location: "NYC"
}

// By project and customer
dimensions = {
  project_id: "45",
  customer_id: "123"
}

// By product and region
dimensions = {
  product: "PROD-SaaS",
  region: "NORTHEAST"
}
```

### 5. Technical Best Practices

- **Use bulk_upsert for imports** - Much faster than individual inserts
- **Lock approved budgets** - Prevents accidental modifications
- **Use templates** - Consistent structure across fiscal years
- **Track dimensions** - Enables drill-down variance
- **Version naming** - Include fiscal year and scenario
- **Import batches** - Track source files for audit trail
- **Status workflow** - Enforce approval process
- **Separate permissions** - Use granular access control

---

## Common Pitfalls

### ❌ Pitfall 1: Editing Locked Budget

**Wrong:**
```javascript
// Try to update line in locked budget
submit("budget_line", "update", {
    budget_line_id: 42,
    amount: 55000
})
// ERROR: Cannot modify locked budget
```

**Correct:**
```javascript
// Reopen budget first (requires admin permission)
submit("budget_workflow", "reopen", {
    budget_version_id: 5,
    comments: "Reopening for correction"
})

// Now update line
submit("budget_line", "update", {
    budget_line_id: 42,
    amount: 55000
})

// Re-submit and approve
```

---

### ❌ Pitfall 2: Missing Currency Validation

**Wrong:**
```javascript
// Create budget in USD
submit("budget_version", "create", {
    fiscal_year: 2025,
    currency_code: "USD"
})

// Try to add line in GBP
submit("budget_line", "create", {
    budget_version_id: 5,
    account_number: "4000",
    amount: 50000,
    currency_code: "GBP"  // Mismatch!
})
// ERROR: Currency must match version
```

**Correct:**
```javascript
// Create multi-currency budgets separately
submit("budget_version", "create", {
    version_name: "FY2025 UK Budget",
    fiscal_year: 2025,
    currency_code: "GBP"
})
```

---

### ❌ Pitfall 3: Duplicate Budget Lines

**Wrong:**
```javascript
// Create two lines with same account/period
submit("budget_line", "create", {
    budget_version_id: 5,
    account_number: "4000",
    period_sequence: 1,
    amount: 50000
})

submit("budget_line", "create", {
    budget_version_id: 5,
    account_number: "4000",
    period_sequence: 1,  // Same!
    amount: 60000
})
// ERROR: Duplicate line (unique constraint)
```

**Correct:**
```javascript
// Use different dimensions or update existing
submit("budget_line", "create", {
    budget_version_id: 5,
    account_number: "4000",
    period_sequence: 1,
    amount: 50000,
    dimensions: {
      department: "SALES"
    }
})

submit("budget_line", "create", {
    budget_version_id: 5,
    account_number: "4000",
    period_sequence: 1,
    amount: 60000,
    dimensions: {
      department: "ENG"  // Different dimension
    }
})
```

---

## Getting Reference Data

### Get Organization Budget Versions

**CORRECT - Use dynamic query:**
```javascript
// List approved versions for a specific entity/year
query("budget_version", filters={"legal_entity_id": 13, "fiscal_year": 2025, "status": "approved"})
// Returns entity_name inline (no extra lookup needed)
```

**DO NOT - Use static references:**
```javascript
// ❌ WRONG: Don't hardcode IDs
const budget_version_id = 5;
```

---

### Get Budget Templates

**CORRECT - Use search:**
```javascript
query("budget_template", query="", filters={"legal_entity_id": 13, "is_active": true})
```

---

## Quick Reference

### Budget Status

| Status | Description | Can Edit Lines? | Can Submit? | Can Approve? |
|--------|-------------|-----------------|-------------|--------------|
| `draft` | Initial state | Yes | Yes | No |
| `submitted` | Awaiting approval | No | No | Yes |
| `approved` | Approved, active | No | No | No |
| `locked` | Locked, read-only | No | No | No |
| `archived` | Historical | No | No | No |

### Budget Scenarios

| Scenario | Purpose | When to Use |
|----------|---------|-------------|
| `budget` | Baseline annual budget | Start of fiscal year |
| `forecast` | Updated projections | Mid-year revisions |
| `stretch` | Aspirational targets | Goal setting |
| `actual_snapshot` | Point-in-time actuals | Historical comparison |

### Version Types

| Type | Periods | Use Case |
|------|---------|----------|
| `annual` | 1 period | High-level planning |
| `quarterly` | 4 periods | Executive reporting |
| `monthly` | 12 periods | Detailed operations |

---

## Key Takeaways

1. **25 Separate Workflows**: Budget uses separate operations (not unified `manage`) for granular permission control

2. **Status Lifecycle**: draft → submitted → approved → locked → archived (with rejection/reopen paths)

3. **Dimension Tagging**: Tag lines with department, project, employee, location for drill-down variance

4. **Project & Employee Budgeting**: Available via Budget Planning plugin (`arfiti-core-budget-planning`) — project profitability, employee cost planning, burden rates

5. **Forecasting**: Mid-year forecast methods (run rate, trend, seasonal) available via Budget Planning plugin

6. **Variance Analysis**: Real-time budget vs actual with favorable/unfavorable logic by account type

7. **Database Triggers**: Enforce status transitions, currency validation, lock protection

8. **Bulk Operations**: Use bulk_upsert for efficient imports and batch updates

9. **Template System**: Reusable budget structures with dimension coverage

10. **Multi-Scenario**: Compare budget vs forecast vs stretch for scenario planning

---

**Version**: 2.0
**Last Updated**: 2026-03-17
**Related Resources**: [Projects](projects-management.md), [Dimensions](dimensions-management.md), [Accounts](accounts-management.md), Unified Transactions


### Dimension-aware bulk upsert (deployed in PR #224, October 2026)

Bulk upsert matches a line by version, account, period, party/project scope,
and its canonical dimension combination. Different departments are separate lines;
repeating the same combination updates its amount. Dimension codes resolve through
the shared master-dimension boundary and persist in budget_line_dimensions. The
whole batch is atomic and serializes edits to the same budget version. Only draft
and submitted budgets are editable. No automatic repair of previously overwritten
amounts is performed; recover those from the original import or approved plan.
Database verification and production retest evidence are tracked in PLAN_USER_WORKFLOWS_AND_PERMISSIONS.
