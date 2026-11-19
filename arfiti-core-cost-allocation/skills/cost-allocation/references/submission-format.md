# Allocation Submission Format Reference

> **MSEO compatibility:** Existing numbered code fields remain the allocation adapter contract. Preserve every supplied split amount. Posted reports and reversal use stored line dimension master identity; never recalculate classifications from current defaults.

## Two Modes

### Mode 1: Standalone (No Source Document)

```python
result = submit("allocation_run", "create", {
    "legal_entity_id": 12,                    # Required: entity ID
    "run_date": "2026-03-16",                # Required: allocation date
    "period_name": "2026-03",                # Optional: fiscal period
    "description": "Q1 IT overhead split",   # Optional: human-readable description
    "allocation_type": "cost_allocation",    # Optional: cost_allocation (default), revenue_allocation, intercompany_charge
    "source_plugin": "arfiti-core-cost-allocation",  # Optional: identifies this plugin
    "metadata": {}                           # Optional: any additional data
})

# Returns:
# {
#   "success": true,
#   "allocation_run_id": 42,
#   "run_number": "ALLOC-0001",
#   "status": "draft"
# }
```

### Mode 2: Document-Linked (From Source Transaction)

```python
result = submit("allocation_run", "create", {
    "legal_entity_id": 12,
    "run_date": "2026-03-16",
    "period_name": "2026-03",
    "description": "Allocate Slack costs from EE-BILL000527 across teams",
    "allocation_type": "cost_allocation",
    "source_transaction_id": 1002,           # KEY: links to source document
    "source_plugin": "arfiti-core-cost-allocation"
})

# Returns:
# {
#   "success": true,
#   "allocation_run_id": 42,
#   "run_number": "ALLOC-0007",
#   "status": "draft",
#   "source_transaction_id": 1002,
#   "source_transaction_number": "EE-BILL000527"
# }
```

## Create Fields

| Field | Required | Description |
|-------|----------|-------------|
| `legal_entity_id` | Yes | Legal entity ID |
| `run_date` | Yes | Allocation date (YYYY-MM-DD) |
| `period_name` | No | Fiscal period (e.g., "2026-03") |
| `description` | No | Human-readable description |
| `allocation_type` | No | `cost_allocation` (default), `revenue_allocation`, `intercompany_charge` |
| `source_transaction_id` | No | Source document transaction ID (enables document-linked mode) |
| `source_plugin` | No | Plugin that created this run |
| `source_agent` | No | Agent that created this run |
| `metadata` | No | Additional JSON metadata |

---

## Submit Allocation Lines

### Standalone Example

```python
result = submit("allocation_run", "submit_lines", {
    "allocation_run_id": 42,
    "lines": [
        # SOURCE line(s) — what is being allocated
        {
            "line_type": "source",
            "account_number": "6900",
            "amount": "10000.00",
            "debit_credit": "CR",
            "description": "IT overhead to allocate",
            "dimension_1_code": "DEPT",
            "dimension_1_value": "IT",
            "source_reference": "Q1 2026 IT costs"
        },
        # TARGET lines — where costs go
        {
            "line_type": "target",
            "account_number": "6900",
            "amount": "6000.00",
            "debit_credit": "DR",
            "description": "IT allocation to Sales (60%)",
            "dimension_1_code": "DEPT",
            "dimension_1_value": "SALES"
        },
        {
            "line_type": "target",
            "account_number": "6900",
            "amount": "2500.00",
            "debit_credit": "DR",
            "description": "IT allocation to Marketing (25%)",
            "dimension_1_code": "DEPT",
            "dimension_1_value": "MARKETING"
        },
        {
            "line_type": "target",
            "account_number": "6900",
            "amount": "1500.00",
            "debit_credit": "DR",
            "description": "IT allocation to Finance (15%)",
            "dimension_1_code": "DEPT",
            "dimension_1_value": "FINANCE"
        }
    ]
})
```

### Document-Linked Example

**CRITICAL**: When the allocation run has a `source_transaction_id`, the source line `account_number` MUST match a `gl_account_number` from the source transaction's lines. Using a different account will be rejected.

```python
result = submit("allocation_run", "submit_lines", {
    "allocation_run_id": 42,
    "lines": [
        {
            "line_type": "source",
            "account_number": "60002",       # MUST match source transaction's GL line
            "amount": "120.00",
            "debit_credit": "CR",
            "description": "Slack Business+ - source"
        },
        {
            "line_type": "target",
            "account_number": "60002",
            "amount": "60.00",
            "debit_credit": "DR",
            "description": "Slack to Engineering (50%)",
            "dimension_1_code": "DEPT",
            "dimension_1_value": "ENGINEERING"
        },
        {
            "line_type": "target",
            "account_number": "60002",
            "amount": "36.00",
            "debit_credit": "DR",
            "description": "Slack to Product (30%)",
            "dimension_1_code": "DEPT",
            "dimension_1_value": "PRODUCT"
        },
        {
            "line_type": "target",
            "account_number": "60002",
            "amount": "24.00",
            "debit_credit": "DR",
            "description": "Slack to Sales (20%)",
            "dimension_1_code": "DEPT",
            "dimension_1_value": "SALES"
        }
    ]
})

# Returns:
# {
#   "success": true,
#   "allocation_run_id": 42,
#   "status": "calculated",
#   "line_count": 4,
#   "total_debit": 120.00,
#   "total_credit": 120.00
# }
```

---

## Line Fields

| Field | Required | Description |
|-------|----------|-------------|
| `line_type` | Yes | `"source"` or `"target"` |
| `account_number` | Yes | GL account number (must exist in chart of accounts) |
| `amount` | Yes | Positive decimal string (e.g., `"5000.00"`) |
| `debit_credit` | Yes | `"DR"` or `"CR"` |
| `description` | No | Human-readable line description |
| `dimension_1_code` | No | First dimension code (e.g., `"DEPT"`) |
| `dimension_1_value` | No | First dimension value (e.g., `"SALES"`) |
| `dimension_2_code` | No | Second dimension code |
| `dimension_2_value` | No | Second dimension value |
| `dimension_3_code` | No | Third dimension code |
| `dimension_3_value` | No | Third dimension value |
| `source_reference` | No | Traceability reference (e.g., `"Q1 IT costs"`) |
| `metadata` | No | Any additional JSON data |

---

## Validation Rules

### Payload shape (all operations)

0. **No unknown top-level keys.** Every `allocation_run.*` payload rejects keys
   not listed in the tables above. A misspelled optional field used to be
   silently dropped — misspell `source_transaction_id` and the run is created
   standalone instead of document-linked, skipping the source checks and
   the per-account limit in rules 9–12 below. Send the exact field names.

   Line dicts inside `lines` are *not* restricted this way — extra per-line keys
   are still accepted, since per-line rules are enforced by the executor.

### Basic (all allocation runs)

1. **Balance**: Total DR amounts must equal total CR amounts exactly — there is no tolerance
2. **Exact amounts**: Every amount is > 0 with no more decimals than the run's currency carries (at most 2). Excess precision is refused, not rounded: put any rounding remainder on a line yourself
3. **Accounts**: All account numbers must exist in `v_accounts_effective` for the entity
4. **Active**: All accounts must be active (not deactivated)
5. **Dimensions**: Every dimension code/value pair must resolve for the entity; an unknown dimension is refused at `submit_lines`
6. **Source + Target**: At least one `source` line and one `target` line required
7. **Minimum lines**: At least 2 lines total
8. **Run status**: Run must be in `draft` or `calculated` status

### Document-linked validations (when `source_transaction_id` exists)

9. **Eligible source**: The source must be posted and not reversed, voided or cancelled (checked at create, submit_lines and execute). Error: "Source transaction X is reversed …; it has no cost left to allocate."
10. **Cost side only**: Capacity per account is what the source posted on the cost side (net debit; net credit for `revenue_allocation`). The offset side (cash, payables) is not allocatable. Error: "Account X carries no allocatable amount in source Y. Allocatable accounts: …"
11. **Direction**: Source lines are `CR` for a cost allocation, `DR` for a revenue allocation. Error: "Source line for account X must be CR …"
12. **Per-account limit**: All source lines for an account are summed and cannot exceed what is left after other runs that are not voided or rejected. One cent left is allocatable; one cent over is not. Errors: "Account X from source Y is already fully allocated (A of B) by: ALLOC-NNNN" / "Source lines for account X total A, more than the B left of source Y …"
13. **Partial allocation**: A multi-line source transaction can have separate allocations per account line. E.g., allocate account 60002 in one run, account 61000 in another.

Execute re-checks rules 9–12. A run that can no longer post (for example its source was reversed after approval) is released with `reject`.

---

## Approve

```python
submit("allocation_run", "approve", {"allocation_run_id": 42})
# Status: calculated -> approved
```

## Execute (Post GL Entry)

```python
result = submit("allocation_run", "execute", {"allocation_run_id": 42})
# Status: approved -> posted
# Creates GL journal entry (COST_ALLOCATION, REVENUE_ALLOCATION, or INTERCOMPANY_CHARGE)
# Returns: transaction_id, transaction_number
```

## Void (Reverse)

```python
submit("allocation_run", "void", {
    "allocation_run_id": 42,
    "void_reason": "Incorrect percentages, will recalculate"
})
# Creates reversing GL journal entry
# Frees up source account amounts for re-allocation
```

## Reject

```python
submit("allocation_run", "reject", {
    "allocation_run_id": 42,
    "rejection_reason": "Percentages don't match board-approved split"
})
```

---

## Common Patterns

### Same-account department reallocation
Source and targets use the same account but different department dimensions.
The GL impact is zero net change per account, but costs move between departments.

### Cross-account allocation
Source is an overhead account (e.g., 6900), targets are expense accounts per department (e.g., 6100, 6200).

### Document-linked bill allocation
Link to a source AP invoice and redistribute its expense line(s) across departments.
Source line account must match the invoice's GL account.

### Partial allocation from multi-line invoice
Allocate one line from an invoice now, another line later. Each creates a separate allocation run linked to the same source transaction but using different accounts.

### Intercompany charge
Use `allocation_type: "intercompany_charge"`.

### Document chain
After posting, the admin dashboard shows a full chain:
**Source Transaction** -> **Allocation Run** -> **Target GL Entry** (-> **Reversal** if voided)
Navigate between all documents from the allocation detail page or from either transaction's "Allocation GL Impact" section.
