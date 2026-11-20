# Budget Submission Format Reference

> **MSEO compatibility:** Budget dimension IDs already identify masters. Preserve supplied amounts and classification IDs, including during version copy. Detailed variance uses stored classification scope and actual fiscal-period boundaries; overlapping scopes are not additive. project_id/customer_id/vendor_id retain their endpoint meanings and legal-entity scope; do not pass dimension value IDs in those fields.

## Create Budget Version

```python
result = submit(object_type="budget_version", operation="create", data=json.dumps({
    "legal_entity_id": 12,                         # Required: entity ID
    "version_name": "FY2026 Operating Budget",     # Required: human-readable name
    "fiscal_year": 2026,                           # Required: year (2000-2100)
    "scenario": "budget",                          # Optional: budget (default), forecast, stretch, actual_snapshot
    "version_type": "monthly",                     # Required: annual, quarterly, monthly or rolling
    "currency_code": "EUR",                        # Required: normally the entity's functional currency
    "template_id": 1,                              # Optional: budget template reference
    "notes": "Built from 2025 actuals + 5% growth"  # Optional: saved with the version
}))
# A field not listed here (for example copy_from_version_id) is refused.
# To copy a budget, read its lines and bulk_upsert them into the new version.

# Returns:
# {
#   "success": true,
#   "budget_version_id": 8,
#   "version_number": "BUD-000008",
#   "status": "draft"
# }
```

### Create Fields

| Field | Required | Description |
|-------|----------|-------------|
| `legal_entity_id` | Yes | Legal entity ID |
| `version_name` | Yes | Budget name (max 100 chars) |
| `fiscal_year` | Yes | Year (2000-2100) |
| `scenario` | No | `budget` (default), `forecast`, `stretch`, `actual_snapshot` |
| `version_type` | Yes | `annual`, `quarterly`, `monthly` or `rolling` |
| `currency_code` | Yes | ISO currency code, normally the entity's functional currency |
| `template_id` | No | FK to budget_templates |
| `notes` | No | Assumptions and source of the budget; saved with the version |

### Constraint
Only ONE active (non-archived) version per `(legal_entity_id, fiscal_year, scenario)`. Archive old versions first if needed.

---

## Submit Budget Lines (Bulk)

The primary way to submit budget lines — handles both insert and update:

```python
result = submit(object_type="budget_line", operation="bulk_upsert", data=json.dumps({
    "budget_version_id": 8,
    "lines": [
        {
            "account_number": "4000",
            "period_sequence": 1,
            "amount": 45000.00,
            "description": "January Revenue",
            "memo": "Based on 2025 actual + 10% growth",
            "source": "formula",
            "project_id": None,
            "customer_id": None,
            "vendor_id": None,
            "dimensions": {"department": "SALES", "cost_center": "CC001"}
        },
        {
            "account_number": "4000",
            "period_sequence": 2,
            "amount": 47000.00,
            "description": "February Revenue"
        },
        {
            "account_number": "6000",
            "period_sequence": 1,
            "amount": 25000.00,
            "description": "January Salaries",
            "dimensions": {"department": "ENG"}
        }
    ]
}))

# Returns:
# {
#   "success": true,
#   "inserted": 3,
#   "updated": 0,
#   "total": 3
# }
```

### Line Fields

| Field | Required | Description |
|-------|----------|-------------|
| `account_number` | Yes | An active, non-header account of the version's entity |
| `period_sequence` | Yes | Period number: 1-12 (monthly), 1-4 (quarterly), 1 (annual), or the version's custom period numbers |
| `amount` | Yes | Finite budget amount, entered positive for revenue and for expenses alike (the report's convention: revenue 200, expenses 120, net 80); never negative for credit-normal accounts |
| `description` | No | Human-readable line description |
| `memo` | No | Internal notes (calculation basis, assumptions) |
| `source` | No | `manual` (default), `formula`, `import`, `template`, `copy` |
| `currency_code` | No | Defaults to version currency |
| `project_id` | No | First-class project reference; must be a project of the version's entity |
| `customer_id` | No | First-class customer reference; must be a customer of the version's entity |
| `vendor_id` | No | First-class vendor reference; must be a vendor of the version's entity |
| `dimensions` | No | Flexible dimensions as JSON: `{"department": "SALES", "cost_center": "CC001"}` |

### Matching Logic (Upsert)
Lines are matched by: `budget_version_id + account_number + period_sequence + project_id + customer_id + vendor_id + dimension_combo_hash`

If a match is found, the line is **updated**. Otherwise, it is **inserted**.

---

## Submit Single Budget Line

For adding individual lines:

```python
result = submit(object_type="budget_line", operation="create", data=json.dumps({
    "budget_version_id": 8,
    "account_number": "6500",
    "period_sequence": 4,
    "amount": 5000.00,
    "description": "Q2 Training Budget",
    "dimensions": {"department": "ENG"}
}))

# Returns: {"success": true, "budget_line_id": 142}
```

---

## Set Line Dimensions

Add or replace dimension tags on a budget line:

```python
submit(object_type="budget_line_dimension", operation="bulk_set", data=json.dumps({
    "budget_line_id": 142,
    "dimensions": [
        {"dimension_type_code": "DEPARTMENT", "dimension_value_code": "SALES"},
        {"dimension_type_code": "COST_CENTER", "dimension_value_code": "CC001"}
    ]
}))
```

This **replaces** all existing dimensions on the line.

---

## Status Transitions

```python
# Submit for approval (draft -> submitted)
submit(object_type="budget_workflow", operation="submit", data=json.dumps({
    "budget_version_id": 8,
    "comments": "Ready for CFO review"
}))

# Approve (submitted -> approved)
submit(object_type="budget_workflow", operation="approve", data=json.dumps({
    "budget_version_id": 8,
    "comments": "Approved by CFO"
}))

# Reject (submitted -> draft)
submit(object_type="budget_workflow", operation="reject", data=json.dumps({
    "budget_version_id": 8,
    "rejection_reason": "Need to revise Q3 projections"  # Required
}))

# Lock (approved -> locked)
submit(object_type="budget_workflow", operation="lock", data=json.dumps({
    "budget_version_id": 8
}))

# Archive (draft/approved/locked -> archived)
submit(object_type="budget_workflow", operation="archive", data=json.dumps({
    "budget_version_id": 8
}))

# Reopen (submitted/archived -> draft)
submit(object_type="budget_workflow", operation="reopen", data=json.dumps({
    "budget_version_id": 8
}))
```

### Status Flow
```
draft -> submitted -> approved -> locked -> archived
          |                         |
        draft (if rejected)     archived
```

---

## Validation Rules

The server checks every line before anything is saved, in a dry run
(`validate_only=True`) and in the write alike; a refused request saves nothing
and lists every reason.

1. **Version editable**: `bulk_upsert` and dimensions need a `draft` or `submitted` version; single `create`/`update` refuse `locked` and `archived` ones
2. **Account**: an active, non-header account of the version's entity
3. **Amount**: a finite number (`"NaN"`, `"Infinity"` and text are refused)
4. **Period**: valid for the version's granularity (or one of its custom period numbers)
5. **No duplicates**: the same account + period + scope (project, customer, vendor, dimensions) cannot appear twice in a request, and `create` refuses one the version already has
6. **Currency match**: a line currency, when given, equals the version currency
7. **Dimensions valid**: dimension types and values must be eligible for the entity
8. **Parties**: a customer, vendor or project must belong to the version's entity
9. **Unique version**: one version per entity, fiscal year and scenario that is not archived (draft, submitted, approved and locked all count); query for it before `budget_version.create`, and on an uncertain outcome follow the recovery order in SKILL.md (Error Handling) before trying again
10. **Declared fields only**: a field the operation does not declare is refused, never ignored

---

## Common Submission Patterns

### Full Monthly Budget (12 months x N accounts)
Build all lines in a single `bulk_upsert` call. A typical operating budget might have 10-20 accounts x 12 months = 120-240 lines.

### Copy + Adjust
1. Read every source line with `query("budget_line", filters={"budget_version_id": <source>})`, page by page
2. Show the adjusted amounts and get the user's confirmation
3. `budget_version.create` (with `version_type` and `currency_code`), then one `budget_line.bulk_upsert` with every adjusted line, keeping each line's project, party and dimensions

### Employee Budget with Dimensions
Each employee gets separate lines tagged with the organisation's own dimension codes, for example `dimensions: {"employee": "EMP-JSMITH", "department": "ENG"}`, only where those dimension types and values exist and are eligible for the entity (discover them with `query("dimension_value", ...)`). An employee or payroll record ID is not a dimension value: the write refuses it. Without an employee dimension, name the person in `memo`. Multiple cost categories per employee (salary, taxes, benefits).

### Project Budget with First-Class IDs
Use `project_id` field (not dimensions) for project budgets — it's a first-class column with FK constraint and fast querying.
