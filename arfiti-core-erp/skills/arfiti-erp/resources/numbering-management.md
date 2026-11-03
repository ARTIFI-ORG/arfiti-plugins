# Numbering Management

## Overview

The numbering system automatically generates unique, sequential identifiers for all transactions and master data records. Numbers are entity-specific, concurrency-safe, and customizable per legal entity.

**Key Features:**
- Automatic sequential numbering for 28 transaction types and 11 master data types
- Entity-specific sequences (each legal entity has independent counters)
- Customizable prefixes and zero-padding per entity
- Concurrency-safe (uses PostgreSQL row locks to prevent duplicates)
- Two-table design: `transaction_type_settings` for transactions, `number_series` for master data

**Architecture**: Transaction counters live in `transaction_type_settings`; master data uses `number_series`.

Transaction numbers share one namespace per organization/entity, across transaction types. The allocator holds an entity-level transaction advisory lock, increments the configured type counter and skips numbers already present in `transactions`, including reversed records. Configured prefixes are preserved: if AP payment already uses PAY000001, payroll with the same prefix gets the next unused number. Use distinct prefixes for easier reading; counters need not be contiguous within one type when prefixes overlap. The insert and allocation must use the same database transaction; failure rolls back the counter advances. The database unique constraint remains the final guard for manual or external writers.



## Available Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `submit(object_type="number_series", operation="allocate", data={"legal_entity_id":.., "series_type":..})` | Get next number and increment counter (replaces `get_next_number(legal_entity_id, series_type)`, MCP registration removed) | Generating a master data number (rarely needed -- workflows auto-generate) |
| `query("number_series", filters)` | List number series with filters | Browsing configured master data series |
| `query("number_series", query)` | Search number series | Finding series by type or prefix |
| `get_entity("number_series", id=X)` | Get single number series | Looking up a specific series config |
| `submit("number_series", "create", {...})` | Create new number series | Adding a custom master data series |
| `get_submissions(action='schema', object_type="number_series", operation="create")` | Get creation field schema | Checking required fields before creating |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

---

## How Numbering Works

### Transaction Numbering (Automatic)

Transaction numbers are generated automatically by the workflow system when you submit transactions. You do not need to call any numbering tool -- the executor handles it.

**Example**: When you submit an AR invoice, the system:
1. Takes the entity-wide transaction lock.
2. Increments the configured type counter and formats prefix plus padding.
3. Skips any number already used by any transaction type in this entity.
4. Inserts the transaction before releasing the lock at commit.

```javascript
// You just submit -- numbering is automatic
submit("transaction", "post", {
    transaction_type_code: "AR_INVOICE",
    legal_entity_id: 9,
    // ... other fields
})
// Result includes transaction_number: "AR-000013"
```

### Master Data Numbering (Automatic via Workflows)

Master data numbers are also generated automatically by workflows. When you create a customer, vendor, employee, etc., the workflow executor calls the numbering system internally.

```javascript
// You just submit -- numbering is automatic
submit("vendor", "create", {
    vendor_name: "Acme Corp",
    email: "ap@acme.com"
})
// Result includes global_vendor_id: "VEND-000042"
```

### Manual Number Generation (Rare)

Use `submit(object_type="number_series", operation="allocate", data={...})` only when you need a number outside the normal workflow process:

```javascript
submit(object_type="number_series", operation="allocate", data={"legal_entity_id": 9, "series_type": "customer"})
// Response:
// {
//   "success": true,
//   "number": "CUST-000009",
//   "series_type": "customer",
//   "numeric_value": 9
// }
```

**Warning**: Calling this consumes the number permanently. The counter increments even if you do not use the number. Gaps are normal and expected in accounting.

---

## Configuring Transaction Type Settings

Per-entity configuration of a transaction type (enable/disable, number prefix and padding, auto-post, approval requirement, payment defaults) goes through the submit gateway:

```javascript
// Change the prefix and enable a type for one entity
submit(object_type="transaction_type_setting", operation="update",
       data={"transaction_type_setting_id": 12, "number_prefix": "INV-", "is_enabled": true})

// Add a settings row for a type this entity doesn't have configured yet
submit(object_type="transaction_type_setting", operation="create",
       data={"legal_entity_id": 9, "transaction_type_code": "AP_INVOICE", "is_enabled": true})
```

Rules:
- The `transaction_type_code` must already exist in the platform catalog (`system.transaction_types`). Adding a genuinely **new** transaction type is a platform code change — you cannot create one from here; ask the platform team.
- `next_number` is **not** editable through this path. Rewinding the counter would issue duplicate document numbers; the counter only moves forward via number allocation.
- Use `query` on `transaction_type_settings` to find the `transaction_type_setting_id` for an update.

---

## Transaction Type Prefixes

All 28 transaction types have numbering configured in `transaction_type_settings`:

### Accounts Receivable

| Transaction Type | Default Prefix | Example |
|-----------------|---------------|---------|
| `AR_INVOICE` | `AR-` | AR-000013 |
| `AR_CREDIT_MEMO` | `CRM-` | CRM-000001 |
| `AR_DEBIT_MEMO` | `DBM-` | DBM-000001 |
| `AR_PAYMENT` | `RCV-` | RCV-000001 |
| `RECURRING_INVOICE` | `RCI-` | RCI-000001 |
| `WALLET_TOPUP` | `WLT-` | WLT-000001 |

### Accounts Payable

| Transaction Type | Default Prefix | Example |
|-----------------|---------------|---------|
| `AP_INVOICE` | `AP-` | AP-000001 |
| `AP_CREDIT_MEMO` | `VCM-` | VCM-000001 |
| `AP_DEBIT_MEMO` | `VDM-` | VDM-000001 |
| `AP_PAYMENT` | `APAY-` | APAY-000001 |

### Banking

| Transaction Type | Default Prefix | Example |
|-----------------|---------------|---------|
| `BANK_DEPOSIT` | `DEP-` | DEP-000001 |
| `BANK_WITHDRAWAL` | `WD-` | WD-000001 |
| `BANK_TRANSFER` | `TRF-` | TRF-000001 |
| `BANK_FEE` | `FEE-` | FEE-000001 |
| `BANK_INTEREST` | `INT-` | INT-000001 |

### Journal Entries & Adjustments

| Transaction Type | Default Prefix | Target Table | Example |
|-----------------|---------------|-------------|---------|
| `JOURNAL_ENTRY` | `JE-` | `journal_entries` | JE-000007 |
| `RECLASSIFICATION` | `RCL-` | `transactions` | RCL-000001 |
| `OPENING_ENTRY` | `OB-` | `transactions` | OB-000001 |
| `CLOSING_ENTRY` | `CLS-` | `transactions` | CLS-000001 |
| `DEPRECIATION` | `DEPR-` | `transactions` | DEPR-000001 |

### Tax

| Transaction Type | Default Prefix | Example |
|-----------------|---------------|---------|
| `TAX_PAYMENT` | `TAXPAY-` | TAXPAY-000001 |
| `TAX_ADJUSTMENT` | `TAD-` | TAD-000001 |

### Allocations

| Transaction Type | Default Prefix | Example |
|-----------------|---------------|---------|
| `COST_ALLOCATION` | `CAL-` | CAL-000001 |
| `REVENUE_ALLOCATION` | `RAL-` | RAL-000001 |
| `INTERCOMPANY_CHARGE` | `ICC-` | ICC-000001 |

### Other

| Transaction Type | Default Prefix | Example |
|-----------------|---------------|---------|
| `USAGE_ACCRUAL` | `USA-` | USA-000001 |
| `FOREIGN_EXCHANGE_GAIN` | `FXG-` | FXG-000001 |
| `FOREIGN_EXCHANGE_LOSS` | `FXL-` | FXL-000001 |
| `INVENTORY_ADJUSTMENT` | `INVADJ-` | INVADJ-000001 |

**Table Routing**: All transaction types go to the `transactions` table except `JOURNAL_ENTRY`, which goes to `journal_entries`. This is enforced by a database check constraint.

---

## Master Data Number Series

The `number_series` table stores numbering for master data. All 11 series types are created automatically for every new legal entity.

| Series Type | Default Prefix | Padding | Example |
|------------|---------------|---------|---------|
| `customer` | `CUST-` | 6 | CUST-000001 |
| `vendor` | `VEND-` | 6 | VEND-000001 |
| `employee` | `EMP-` | 6 | EMP-000001 |
| `item` | `ITEM-` | 6 | ITEM-000001 |
| `fixed_asset` | `FA-` | 6 | FA-000001 |
| `expense_report` | `EXPR-` | 6 | EXPR-000001 |
| `recurring_contract` | `CON-` | 6 | CON-000001 |
| `sale` | `SALE-` | 6 | SALE-000001 |
| `bank_statement` | `BS-` | 6 | BS-000001 |
| `budget_version` | `BV-` | 4 | BV-0001 |
| `journal_entry` | `JE-` | 6 | JE-000001 |

**Country-code prefixes**: Entities onboarded with a country code (e.g., Estonia `EE`) may have entity-code-prefixed series such as `EE-CUST-`, `EE-VEND-`, `EE-FA-`. These are stored in the `prefix` column and take precedence over defaults.

### Number Series Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer | Auto | Primary key |
| `legal_entity_id` | integer | Yes | Which entity this series belongs to |
| `series_type` | string(50) | Yes | Type: `customer`, `vendor`, `employee`, etc. |
| `prefix` | string(20) | Yes | Number prefix (e.g., `CUST-`, `VEND-`) |
| `next_number` | integer | No | Next number to generate (default: 1) |
| `padding` | integer | No | Zero-padding width (default: 6, range: 1-10) |

**Display fields** (returned by `query`/`query`): `id`, `legal_entity_id`, `series_type`, `prefix`, `next_number`, `padding`

**Filter fields**: `legal_entity_id`, `series_type`

**Sort fields**: `series_type` (default), `prefix`, `created_at`

**Requires legal_entity_id filter**: Yes

---

## Querying Number Series

### List All Series for an Entity

```javascript
query("number_series", filters={"legal_entity_id": 9})
```

**Response:**

```javascript
{
  "success": true,
  "number_series": [
    {"id": 1, "legal_entity_id": 9, "series_type": "customer", "prefix": "CUST-", "next_number": 9, "padding": 6},
    {"id": 2, "legal_entity_id": 9, "series_type": "vendor", "prefix": "VEND-", "next_number": 42, "padding": 6},
    {"id": 3, "legal_entity_id": 9, "series_type": "employee", "prefix": "EMP-", "next_number": 15, "padding": 6}
    // ... all 11 series types
  ],
  "total_count": 11
}
```

### Search for a Specific Series Type

```javascript
query("number_series", query="vendor")
```

### Get a Single Series

```javascript
get_entity("number_series", id=2)
```

### Preview Next Numbers

To see what the next number will be without consuming it, query the series and calculate:

```javascript
// List series to see current state
query("number_series", filters={"legal_entity_id": 9, "series_type": "customer"})
// Result: prefix="CUST-", next_number=9, padding=6
// Next number will be: CUST-000009
```

---

## Creating Custom Number Series

### Workflow: number_series.create

Use this when you need a number series for a custom master data type that is not covered by the 11 default series.

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="number_series", operation="create")

// Step 2: Submit with discovered fields
submit("number_series", "create", {
    legal_entity_id: 9,
    series_type: "work_order",
    prefix: "WO-",
    starting_number: 1,
    padding: 6
})
// Tip: Use validate_only=true to check payload before submitting
```

**Response:**

```javascript
{
  "success": true,
  "series_id": 45,
  "legal_entity_id": 9,
  "series_type": "work_order",
  "prefix": "WO-",
  "next_number": 1,
  "padding": 6,
  "next_number_preview": "WO-000001"
}
```

**Validation:**
- `series_type`: Required, 1-50 chars, must be unique per entity
- `prefix`: Required, max 20 chars
- `starting_number`: Optional, must be >= 1 (default: 1)
- `padding`: Optional, 1-10 (default: 6)

**Note**: You cannot create a series if one already exists for the same entity + series_type combination.

---

## Number Format Customization

### Prefix Customization

Each entity can customize prefixes independently. The default prefix comes from `system.transaction_types.default_document_prefix` and is copied to entity settings during setup.

**Examples of per-entity customization:**

| Entity | Type | Default Prefix | Custom Prefix | Result |
|--------|------|---------------|--------------|--------|
| Entity 9 | AR_INVOICE | `AR-` | (uses default) | AR-000001 |
| Entity 10 | AR_INVOICE | `AR-` | `INV` | INV000001 |
| Entity 13 | AR_INVOICE | `AR-` | `INVOICE-` | INVOICE-000001 |

### Padding Customization

Padding controls zero-padding width:

| Padding | Format | Range |
|---------|--------|-------|
| 4 | `AR-0001` to `AR-9999` | 9,999 numbers |
| 6 | `AR-000001` to `AR-999999` | 999,999 numbers |
| 8 | `AR-00000001` to `AR-99999999` | 99,999,999 numbers |

---

## Common Scenarios

### Scenario 1: Check Current Numbering State

```javascript
// See all number series for an entity
query("number_series", filters={"legal_entity_id": 9})

// Result shows next_number for each type, so you can predict:
// customer: next will be CUST-000009
// vendor: next will be VEND-000042
// employee: next will be EMP-000015
```

### Scenario 2: Understand Why Numbers Have Gaps

Gaps are normal and expected in accounting systems. They occur when:
- A transaction fails validation after the number was allocated
- A workflow is rejected after number generation
- A user cancels a transaction in progress

Gaps do not indicate data loss or errors.

### Scenario 3: Create a Custom Series for a New Record Type

```javascript
// Create a project numbering series
submit("number_series", "create", {
    legal_entity_id: 9,
    series_type: "project",
    prefix: "PRJ-",
    starting_number: 1,
    padding: 4
})
// First number: PRJ-0001
```

### Scenario 4: Check How Many Transactions Have Been Created

```javascript
// The next_number minus 1 tells you how many numbers have been issued
// If next_number for AR_INVOICE is 14, then 13 AR invoices have been numbered
query("number_series", filters={"legal_entity_id": 9, "series_type": "customer"})
```

### Scenario 5: Manually Generate a Number

```javascript
// Only use this when you need a number outside the workflow system
submit(object_type="number_series", operation="allocate", data={"legal_entity_id": 9, "series_type": "expense_report"})
// Response: {"success": true, "number": "EXPR-000003", "numeric_value": 3}
```

---

## Important Design Details

### Concurrency Safety

Transaction allocation uses the entity-wide advisory lock plus atomic counter updates; master-data allocation uses atomic row updates. Only one transaction allocator per entity proceeds at a time.

### Uniqueness Guarantees

- Transaction numbers: Unique per `(legal_entity_id, transaction_number)` via database constraint
- Master data numbers: Generated atomically within a transaction

### Table Routing Enforcement

A database check constraint prevents `JOURNAL_ENTRY` transactions from being inserted into the `transactions` table. They must go to `journal_entries`. This is enforced at the database level.

### Number Consumption is Permanent

Once the `number_series` allocate call is made, the counter increments and the number is consumed. There is no "undo" or "return unused number" operation. This is standard accounting practice.

---

## Key Takeaways

1. **Numbering is automatic** -- workflows generate numbers for you during create/post operations
2. **Two tables**: `transaction_type_settings` for transaction numbering, `number_series` for master data numbering
3. **Entity-specific**: Each legal entity has independent number sequences
4. **Concurrency-safe**: PostgreSQL transaction locks and unique constraints protect numbering
5. **Customizable**: Prefixes and padding can be configured per entity
6. **Gaps are normal**: Expected in accounting and do not indicate errors
7. **11 master data series** are auto-created for every new entity (customer, vendor, employee, item, fixed_asset, expense_report, recurring_contract, sale, bank_statement, budget_version, journal_entry)
8. **28 transaction types** have numbering built into `transaction_type_settings`
9. **`submit(object_type="number_series", operation="allocate", ...)`** (replaces `get_next_number`, MCP registration removed) is rarely needed -- use it only for manual number generation outside workflows

---

**End of Numbering Management Guide**
