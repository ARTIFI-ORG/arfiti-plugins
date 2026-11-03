# Allocation Workflows

Cost allocation distributes shared costs to the departments, projects, or entities that benefit from them. Uses a **plugin-based architecture** — the backend stores runs + lines and validates integrity; plugins/agents calculate the allocation logic and submit results.

---

## Overview

| Aspect | Detail |
|--------|--------|
| **Entity type** | `allocation_run` |
| **Allocation types** | `cost_allocation`, `revenue_allocation`, `intercompany_charge` |
| **Two modes** | Standalone (no source doc) or document-linked (from source transaction) |
| **GL posting** | Allocation execution creates journal entries via `JournalEntryExecutor` |
| **Document chain** | Source Transaction -> Allocation Run -> Target Transaction (GL entry) |
| **Status flow** | `draft` -> `calculated` -> `approved` -> `posted` (or `rejected` / `voided`) |

### Architecture

```
Plugin/Agent                          Backend (MCP Server)
---------------------                 --------------------
1. Read GL balances / source tx
2. Apply allocation logic
3. Calculate DR/CR splits
4. submit(allocation_run, create)  -> Create draft run
5. submit(allocation_run,          -> Validate & store lines
       submit_lines, {lines})         (status -> calculated)
6. submit(allocation_run, approve) -> Approve (status -> approved)
7. submit(allocation_run, execute) -> Post GL journal entry
                                      (status -> posted)
```

> **IMPORTANT — Schema Discovery**: Before calling `submit()`, call `get_submissions(action='schema', object_type="allocation_run", operation)` to discover the exact required and optional fields for your organization.

---

## Workflow Operations

| Operation | Typical lane | Description |
|-----------|------|-------------|
| `allocation_run` + `create` | Green | Create draft run (optionally with `source_transaction_id`) |
| `allocation_run` + `submit_lines` | Green | Submit pre-calculated lines with full validation |
| `allocation_run` + `approve` | Yellow | Approve for GL posting |
| `allocation_run` + `execute` | Yellow | Post as GL journal entry |
| `allocation_run` + `void` | Red | Reverse posted allocation (creates reversing GL entry) |
| `allocation_run` + `reject` | Yellow | Reject during approval |

Lanes are assigned by your organisation's workflow rules; the submit() result is authoritative.

---

## Creating Allocation Runs

### Standalone (No Source Document)

Use when allocating GL balances without linking to a specific source transaction.

```
submit("allocation_run", "create", {
    "legal_entity_id": 12,
    "run_date": "2026-03-16",
    "period_name": "2026-03",
    "description": "March IT overhead allocation",
    "allocation_type": "cost_allocation"
})
```

### Document-Linked (From Source Transaction)

Use when allocating costs from a specific document (e.g., AP invoice). Provides full traceability and prevents double-allocation.

```
submit("allocation_run", "create", {
    "legal_entity_id": 12,
    "run_date": "2026-03-16",
    "period_name": "2026-03",
    "description": "Allocate Slack costs from EE-BILL000527",
    "allocation_type": "cost_allocation",
    "source_transaction_id": 1002
})
```

Returns `source_transaction_number` for confirmation.

### Create Fields

| Field | Required | Description |
|-------|----------|-------------|
| `legal_entity_id` | Yes | Legal entity ID |
| `run_date` | Yes | Run date (YYYY-MM-DD) |
| `period_name` | No | Fiscal period (e.g., `"2026-03"`) |
| `description` | No | Run description |
| `allocation_type` | No | `cost_allocation` (default), `revenue_allocation`, `intercompany_charge` |
| `source_transaction_id` | No | Source document transaction ID for document-linked allocation |
| `source_plugin` | No | Plugin that created this run |
| `source_agent` | No | Agent that created this run |
| `metadata` | No | Additional JSON metadata |

---

## Submitting Lines

### Line Format

| Field | Required | Description |
|-------|----------|-------------|
| `line_type` | Yes | `"source"` or `"target"` |
| `account_number` | Yes | GL account number (must exist in v_accounts_effective) |
| `amount` | Yes | Positive decimal string (e.g., `"5000.00"`) |
| `debit_credit` | Yes | `"DR"` or `"CR"` |
| `description` | No | Line description |
| `dimension_1_code` | No | First dimension code (e.g., `"DEPT"`) |
| `dimension_1_value` | No | First dimension value (e.g., `"SALES"`) |
| `dimension_2_code` | No | Second dimension code |
| `dimension_2_value` | No | Second dimension value |
| `dimension_3_code` | No | Third dimension code |
| `dimension_3_value` | No | Third dimension value |
| `source_reference` | No | Traceability reference |

### Validation Rules

**Basic (all allocation runs):**
- Total DR must equal total CR (tolerance: 0.01)
- At least one source line and one target line
- All accounts must exist and be active
- All amounts must be positive
- Run must be in `draft` or `calculated` status

**Source document validations (when `source_transaction_id` exists):**
- Source-type lines must use accounts from the source transaction's GL lines (`transaction_lines.gl_account_number`)
- Per-account: new allocation amount cannot exceed the remaining unallocated balance
- A multi-line source transaction can have separate allocations per account line

### Example: Fixed Percentage Split

```
submit("allocation_run", "submit_lines", {
    "allocation_run_id": 42,
    "lines": [
        {
            "line_type": "source",
            "account_number": "60002",
            "amount": "120.00",
            "debit_credit": "CR",
            "description": "Slack subscription - source"
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
```

---

## Approving, Executing, Voiding, Rejecting

### Approve

```
submit("allocation_run", "approve", {"allocation_run_id": 42})
```

### Execute (Post GL Entry)

```
submit("allocation_run", "execute", {"allocation_run_id": 42})
```

Maps allocation_type to transaction type:
- `cost_allocation` -> `COST_ALLOCATION`
- `revenue_allocation` -> `REVENUE_ALLOCATION`
- `intercompany_charge` -> `INTERCOMPANY_CHARGE`

Returns `transaction_id` and `transaction_number` of the posted GL journal entry.

### Void (Reverse)

```
submit("allocation_run", "void", {
    "allocation_run_id": 42,
    "void_reason": "Incorrect percentages, will recalculate"
})
```

Creates a reversing GL journal entry. Frees up source account amounts for re-allocation.

### Reject

```
submit("allocation_run", "reject", {
    "allocation_run_id": 42,
    "rejection_reason": "Percentages don't match board-approved split"
})
```

---

## Partial Allocation (Multi-Line Invoices)

A source transaction with multiple expense lines can be allocated independently per account:

```
# Invoice has: Account 60002 = 120.00, Account 61000 = 350.00

# Allocation run 1: Allocate only account 60002
submit("allocation_run", "create", {
    "legal_entity_id": 12,
    "run_date": "2026-03-16",
    "source_transaction_id": 2001
})
# Submit lines with source account_number: "60002"

# Allocation run 2: Allocate only account 61000 (later)
submit("allocation_run", "create", {
    "legal_entity_id": 12,
    "run_date": "2026-03-20",
    "source_transaction_id": 2001  # Same source, different account
})
# Submit lines with source account_number: "61000"
```

---

## Common Scenarios

### Month-End Cost Allocation

1. Read GL balances for shared cost centers
2. Calculate allocation splits based on drivers (headcount, revenue, etc.)
3. Create allocation run per cost pool
4. Submit lines, approve, execute
5. Review in admin dashboard

### Allocating from a Bill/Invoice

1. Identify the source transaction (AP invoice)
2. Check which accounts and amounts are available
3. Create document-linked allocation run
4. Submit lines using the correct source account
5. Approve and execute to create the GL journal entry
6. Both documents now show cross-references in admin dashboard

### Correcting an Allocation

1. Void the incorrect allocation (creates reversing GL entry)
2. Create a new allocation run (from same source if document-linked)
3. Submit corrected lines
4. Approve and execute

---

## Document Chain (Admin Dashboard)

The generic MCP `get_entity` tool does not currently support `allocation_run`.
Use the Admin allocation detail for the run and chain, and
`get_entity(entity_type="transaction", id=...)` for the posted journal.
Do not present the Admin `getTransactionAllocations` API as an MCP tool.

When an allocation links documents, the admin dashboard provides navigation:

- **Allocation run detail** (`/runs/allocations/[id]`): Document Chain section with visual flow Source -> Run -> Target -> Reversal
- **Transaction detail** (`/transactions/journal-entries/[id]`): "Allocation GL Impact" section showing the allocation relationship and lines
  - Source documents show "Allocated" badge with link to allocation and target
  - Target documents show "Created by allocation" badge with link to allocation and source

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `allocation_runs` | Run headers (status, amounts, document links, timestamps) |
| `allocation_run_lines` | Individual DR/CR lines with accounts and dimensions |
| `allocation_history` | Execution audit trail (who ran what, when, amounts) |

### Key Columns on `allocation_runs`

| Column | Purpose |
|--------|---------|
| `source_transaction_id` | Links to the source document (e.g., AP invoice) |
| `transaction_id` | Links to the target GL journal entry |
| `reversal_transaction_id` | Links to the reversal GL entry (if voided) |

---

*Last Updated: 2026-03-16*
*Related Resources:*
- [Transaction Processing](transaction-processing.md) - GL posting and journal entries
- [Financial Period Management](financial-period-management.md) - Period close and month-end
- [Dimensions Management](dimensions-management.md) - Dimension codes and values
- [Accounts Management](accounts-management.md) - Chart of accounts


### Currency and dimension repair (deployed in PR #224, October 2026)

Document-linked posting interprets document-linked allocation amounts in the source
transaction's document currency; standalone runs use the entity functional currency.
Missing currency is refused. Dimension slot pairs are converted to the shared
journal dimension map; incomplete or duplicate type slots are rejected. Posted
history is not rewritten. Historical allocations created with the old EUR default
need reviewed reversal/recreation; the original evidence must be retained.

Allocation posting and run/history updates now share one database transaction and
lock the run. Void uses the common reversal service on the actual posted journal,
retaining its original currency amounts and dimensions even if run inputs changed.
The reversal is linked to the original and dated in an open period. Admin presents
allocation documents as journals in GL impact, avoiding a misleading invoice-style
comparison of both debit and credit line totals. This repair is pending deployment.
