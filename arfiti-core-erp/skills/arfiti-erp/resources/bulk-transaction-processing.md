# Bulk Transaction Processing

This resource explains how to process multiple transactions at once using the import workflow. Use this when a user provides a CSV file, PDF with multiple invoices, or verbally describes a batch of transactions.

> **CRITICAL: For 4+ transactions, ALWAYS use `submit("transaction", "import", {"records": [...], "legal_entity_id": 12})`.
> NEVER loop `submit("transaction", "post", {...})` for multiple transactions.
> The import system is 10x faster: pre-cached lookups, batch validation, async processing, dimension caching.
> Looping individual posts has no caching and processes each record from scratch.**

---

## Overview

The bulk import system handles ALL transaction types through a single entry point:

```
submit("transaction", "import", {"records": [...], "legal_entity_id": 12})
  -> ImportExecutor -> TransactionImporter -> Per-record executor -> GL Posting
```

**Key Concepts:**
- **One import call** processes N records of mixed transaction types
- **Pre-cached reference data** - vendors, customers, accounts resolved once
- **Flexible entity resolution** - identify parties by name, ID, tax_id, global_id, or external_id
- **Duplicate detection** - type + reference_number prevents re-import
- **Per-record error isolation** - one failed record doesn't block others
- **External ID support** - for data migration from external systems (QuickBooks, Xero, etc.)
- **Batch-level approval** - optional one-approval-per-batch (configurable per company)

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

---

## When to Use Bulk Import

| Scenario | Approach |
|----------|----------|
| User uploads CSV with 4+ transactions | Parse CSV → build records array → import |
| User uploads PDF with multiple invoices | Extract each invoice → build records → import |
| User verbally describes repetitive pattern | Identify pattern → generate records → preview → import |
| Data migration from external system | Map fields → use external_id references → import |
| Monthly recurring entries | Build from template → import batch |

**For 1-3 transactions**, use individual `submit("transaction", "post", {...})` calls instead.

---

## Import Payload Format

```javascript
// Step 1: Discover required fields for this transaction type
schema = get_submissions(action='schema', object_type="transaction", operation="import")

// Step 2: Submit with discovered fields
submit("transaction", "import", {
    legal_entity_id: 12,
    records: [
      {
        transaction_type_code: "AP_INVOICE",
        legal_entity_id: 12,
        vendor_name: "Acme Corp",         // Resolved to vendor_id automatically
        transaction_date: "2026-01-15",
        invoice_date: "2026-01-15",
        due_date: "2026-02-14",
        reference_number: "INV-2026-001",
        description: "January supplies",
        currency_code: "EUR",
        payment_term_code: "NET30",
        payment_method: "ach",
        dimensions: {
          cost_center: "CC-5000",
          location: "TLL"
        },
        lines: [{
          description: "Printer paper",
          quantity: 10,
          unit_price: 25.00,
          account_number: "6100",
          tax_code: "EU-EE-STD"
        }]
      },
      // ... more records
    ],
    options: {
      on_duplicate: "skip",       // skip | error (no update for transactions)
      batch_size: 50,
      stop_on_error: false,
      defaults: {                 // Applied to all records missing these fields
        currency_code: "EUR",
        dimensions: {
          location: "TLL"
        }
      }
    }
})
// Tip: Use validate_only=true to check payload before submitting
```

---

## Entity Resolution (Flexible Identifiers)

The importer resolves parties using **any** of these identifiers. Use whichever you have available:

### Vendor Resolution (AP types)

| Field | Example | Priority |
|-------|---------|----------|
| `vendor_id` | `45` | 1 (fastest) |
| `global_vendor_id` | `"VEND-000123"` | 2 |
| `external_vendor_id` | `"QB-VEND-1234"` | 3 (for migration) |
| `tax_id` | `"12-3456789"` | 4 |
| `vendor_name` | `"Acme Corp"` | 5 (case-insensitive) |

### Customer Resolution (AR types)

| Field | Example | Priority |
|-------|---------|----------|
| `customer_id` | `30` | 1 |
| `global_customer_id` | `"CUST-000456"` | 2 |
| `external_customer_id` | `"QB-CUST-5678"` | 3 |
| `customer_name` | `"Widget Inc"` | 4 (case-insensitive) |

### Employee Resolution (Expense reports)

| Field | Example | Priority |
|-------|---------|----------|
| `employee_id` | `10` | 1 |
| `external_employee_id` | `"QB-EMP-100"` | 2 |
| `employee_name` | `"John Smith"` | 3 (first + last, case-insensitive) |

### Project Resolution

| Field | Example | Priority |
|-------|---------|----------|
| `project_id` | `5` | 1 |
| `external_project_id` | `"QB-PROJ-200"` | 2 |
| `project_name` | `"Website Redesign"` | 3 (case-insensitive) |

### Line-Level Resolution

Lines also support flexible identifiers:

| Field | Resolves to |
|-------|-------------|
| `account_number` | Account by number (e.g., `"6100"`) |
| `external_account_id` | Account by external ID (migration) |
| `item_number` | Item by item number |
| `item_id` | Item by ID |
| `external_item_id` | Item by external ID |
| `tax_code` | Tax code by code string |
| `external_tax_code_id` | Tax code by external ID |

### Custom Fields

A header column named `custom_fields.<key>` (or a `custom_fields` object)
sets the organisation's custom field on the posted document: invoices, credit
notes, bills and journals, or the types the field names. An empty cell sets
nothing; `yes`/`no` fills a boolean field. Required fields for the type apply
to every row. A value the register refuses (unknown key, wrong type, a type
the field does not cover) is a row error and nothing of that row is posted.
See the custom-fields resource.

---

## Supported Transaction Types

All 30+ types defined in the transaction workflow definition are supported. Common types:

| Type Code | Party Field | Description |
|-----------|-------------|-------------|
| `AP_INVOICE` | vendor | Vendor bills |
| `AP_CREDIT_MEMO` | vendor | Vendor credit notes |
| `AR_INVOICE` | customer | Customer invoices |
| `AR_CREDIT_MEMO` | customer | Customer credit notes |
| `AP_PAYMENT` | vendor | Vendor payments |
| `AR_PAYMENT` | customer | Customer receipts |
| `JOURNAL_ENTRY` | any (optional) | Manual GL entries |
| `EXPENSE_REPORT` | employee | Employee expense claims |
| `BANK_TRANSFER` | - | Internal bank transfers |
| `DEPRECIATION` | - | Asset depreciation |
| `PAYROLL` | employee | Payroll entries |

**Party fields are optional at the import level.** Required fields are enforced per transaction type from the workflow definition (e.g., AP_INVOICE requires vendor_id).

---

## Preflight Check

Before importing, run a preflight check to discover required fields for a transaction type. Required fields are company-specific (configured in the workflow definition), so always check before building records.

```javascript
submit("transaction", "import", {
    _operation: "preflight",
    transaction_type_code: "AP_INVOICE",
    legal_entity_id: 12
})
// Returns: required_header_fields, required_line_fields,
//          optional_header_fields, optional_line_fields
```

Include a sample record in `records` to validate it against the full pipeline and get specific error messages.

---

## Workflow: CSV File Upload

When a user provides a CSV file with transaction data:

### Step 0: Run Preflight Check

Run a preflight check for the target transaction type to discover required fields for this company. Use the results to map CSV columns correctly.

### Step 1: Parse and Understand the CSV

Read the CSV content. Identify columns and map them to transaction fields:

```
vendor_name, invoice_number, date, due_date, description, amount, account, tax_code
"Acme Corp", "INV-001", "2026-01-15", "2026-02-14", "Supplies", 250.00, "6100", "EU-EE-STD"
```

### Step 2: Resolve Required Context

Before building records, gather:

1. **Legal entity** - Ask user which entity if not obvious
2. **Transaction type** - Determine from context (AP bills = AP_INVOICE)
3. **Required dimensions** - Read from the org's `transaction.post` workflow definition: `workflow_definitions.related_entity_rules.<transaction_type>.transaction_dimensions.required_dimension_types`. The `is_required` flag on `dimension_type` is deprecated and no longer enforced.
4. **Default values** - Currency, payment method, common dimensions

### Step 3: Build Records Array

Map CSV rows to import records:

```javascript
const records = csvRows.map(row => ({
  transaction_type_code: "AP_INVOICE",
  legal_entity_id: 12,
  vendor_name: row.vendor_name,
  transaction_date: row.date,
  invoice_date: row.date,
  due_date: row.due_date,
  reference_number: row.invoice_number,
  description: row.description,
  currency_code: "EUR",
  payment_term_code: "NET30",
  payment_method: "ach",
  dimensions: { cost_center: "CC-1000", location: "TLL" },
  lines: [{
    description: row.description,
    quantity: 1,
    unit_price: row.amount,
    account_number: row.account,
    tax_code: row.tax_code
  }]
}));
```

### Step 4: Preview and Confirm

**Always show a preview before submitting:**

```
I've parsed 32 AP invoices from your CSV:
- Total amount: EUR 45,670.00
- Vendors: Acme Corp (15), Office Plus (10), Tech Solutions (7)
- Date range: 2026-01-01 to 2026-01-31
- All using entity: Arfiti Technologies OÜ (ID: 12)

Shall I proceed with the import?
```

### Step 5: Submit Import

```javascript
submit("transaction", "import", {
    legal_entity_id: 12,
    records: records,
    options: {
      on_duplicate: "skip",
      stop_on_error: false,
      defaults: {
        currency_code: "EUR",
        dimensions: { location: "TLL" }
      }
    }
})
```

### Step 6: Report Results

```
Import complete:
- 30 of 32 transactions posted successfully
- 2 skipped (duplicate reference numbers: INV-2026-015, INV-2026-022)
- 0 errors

Import ID: abc-123-def for tracking.
```

---

## Workflow: PDF Invoice Processing

When a user uploads a PDF containing one or more invoices:

### Step 1: Extract Invoice Data

Parse the PDF to extract:
- Vendor name/details
- Invoice number, date, due date
- Line items (description, quantity, unit price)
- Tax information
- Total amount

### Step 2: Post with Attachment

For PDF invoices, process one at a time with attachment:

```javascript
// For each extracted invoice:
// 1. Post the transaction
submit("transaction", "post", { ... })

// 2. Create attachment metadata
submit("attachment", "create", { ... })

// 3. Generate upload link
submit("attachment", "generate_upload_url", { ... })
```

**See**: [Document Attachments](document-attachments.md) for the complete 5-step attachment workflow.

**For bulk PDFs without attachments** (e.g., pre-processed data), use the import workflow described above.

---

## Workflow: Verbal / Repetitive Pattern

When a user describes transactions verbally:

### Step 1: Identify the Pattern

```
User: "I need to post 12 monthly rent invoices for 2026,
       EUR 3,500 each from Landlord LLC, account 6400"
```

### Step 2: Generate Records

```javascript
const records = Array.from({length: 12}, (_, i) => ({
  transaction_type_code: "AP_INVOICE",
  legal_entity_id: 12,
  vendor_name: "Landlord LLC",
  transaction_date: `2026-${String(i+1).padStart(2,'0')}-01`,
  invoice_date: `2026-${String(i+1).padStart(2,'0')}-01`,
  due_date: `2026-${String(i+1).padStart(2,'0')}-15`,
  reference_number: `RENT-2026-${String(i+1).padStart(2,'0')}`,
  description: `Office rent - ${monthNames[i]} 2026`,
  currency_code: "EUR",
  payment_term_code: "NET15",
  payment_method: "wire",
  dimensions: { cost_center: "CC-1000", location: "TLL" },
  lines: [{
    description: `Office rent - ${monthNames[i]} 2026`,
    quantity: 1,
    unit_price: 3500.00,
    account_number: "6400",
    tax_code: "EU-EE-STD"
  }]
}));
```

### Step 3: Preview and Submit

Show a summary table to the user before submitting, then use the import workflow.

---

## Data Migration (External ID Support)

When migrating from an external system (QuickBooks, Xero, etc.):

### Step 1: Import Master Data First

Import vendors, customers, employees, accounts with `external_id` in metadata:

```javascript
// Import vendors with external IDs
submit("vendor", "import", {
    records: [{
      vendor_name: "Acme Corp",
      email: "ap@acme.com",
      payment_terms_code: "NET30",
      metadata: { external_id: "QB-VEND-1234" }
    }]
})
```

### Step 2: Import Transactions Using External IDs

Reference entities by their external IDs:

```javascript
submit("transaction", "import", {
    legal_entity_id: 12,
    records: [{
      transaction_type_code: "AP_INVOICE",
      external_vendor_id: "QB-VEND-1234",     // Resolved via metadata
      transaction_date: "2026-01-15",
      invoice_date: "2026-01-15",
      due_date: "2026-02-14",
      reference_number: "INV-001",
      lines: [{
        description: "Supplies",
        quantity: 1,
        unit_price: 250.00,
        external_account_id: "QB-ACCT-6100",  // Resolved via metadata
        external_tax_code_id: "QB-TAX-STD"    // Resolved via metadata
      }]
    }],
    options: { on_duplicate: "skip" }
})
```

**Supported external ID fields:**
- `external_vendor_id`, `external_customer_id`, `external_employee_id`
- `external_project_id`
- Line-level: `external_account_id`, `external_item_id`, `external_tax_code_id`

---

## Import Options

| Option | Default | Description |
|--------|---------|-------------|
| `on_duplicate` | `"skip"` | `"skip"` = ignore duplicates, `"error"` = fail on duplicate |
| `batch_size` | `100` | Records per batch (transaction boundary) |
| `stop_on_error` | `false` | Stop entire import on first error |
| `defaults` | `{}` | Default values merged into every record |
| `defaults.currency_code` | - | Default currency for all records |
| `defaults.dimensions` | - | Default dimensions merged into all records |

**Note:** `on_duplicate: "update"` is NOT supported for transactions. Posted transactions are immutable financial records.

---

## Error Handling

### Import Response

```json
{
  "success": true,
  "import_id": "uuid-here",
  "object_type": "transaction",
  "total_records": 32,
  "imported": 30,
  "updated": 0,
  "skipped": 2,
  "errors": 0,
  "errors_detail": [],
  "warnings": [
    {
      "row": 5,
      "field": "amount",
      "message": "Large transaction: 150000",
      "record_identifier": "INV-2026-005"
    }
  ],
  "message": "Imported 30 records, updated 0, skipped 2, 0 errors"
}
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Vendor not found: 'X'` | Name doesn't match any vendor | Check spelling, use vendor_id instead |
| `Account 'X' not found` | Invalid account number | Verify account exists for this entity |
| `Type 'X' not configured` | Type not enabled for entity | Check transaction_type_settings |
| `Required field missing` | Missing field per workflow definition | Add the missing field to record |
| `Invalid date format` | Date not YYYY-MM-DD | Fix date format |
| `No executor for type 'X'` | Transaction type not yet implemented | Use a supported type |

### Recovery from Partial Failures

If some records fail:
1. Check `errors_detail` for specific issues
2. Fix the problematic records
3. Re-submit with `on_duplicate: "skip"` to skip already-imported records
4. Successfully imported records are NOT rolled back

---

## Pre-Submit Checklist

Before submitting a bulk import, verify:

1. **Legal entity ID** is correct for all records
2. **Required dimensions** are included — read from `workflow_definitions.related_entity_rules.<transaction_type>.transaction_dimensions.required_dimension_types` on the org's `transaction.post` workflow (the legacy `is_required` filter on dimension types is no longer enforced).
3. **Vendors/customers exist** for all referenced parties
4. **Account numbers** are valid for the entity
5. **Tax codes** are appropriate for the entity/vendor type
6. **Dates** are in YYYY-MM-DD format
7. **Reference numbers** are unique (to avoid duplicates)
8. **Currency** is set (a record without one takes its legal entity's functional currency; one whose entity has none is refused)
9. **Payment method** and **payment_term_code** are included where required
10. **Preview** shown to user with totals before submitting

---

## Async Import (Large Batches)

Imports are automatically routed based on record count:

| Records | Behavior | MCP Response |
|---------|----------|--------------|
| 1-50 | **Synchronous** | Full result with counts, errors, created_ids |
| 51+ | **Asynchronous** | Returns `import_id` immediately for polling |

### Why Async?

MCP has a 30-second timeout. Each transaction involves 30-50 database queries (validation, entity resolution, GL posting). Dimension lookups are cached across records, reducing repeated SELECTs by ~30%. For 100+ records, synchronous processing would exceed this limit.

### Async Import Flow

```javascript
// Step 1: Submit large import (>50 records)
const result = submit("transaction", "import", {
    legal_entity_id: 12,
    records: largeRecordArray,  // 200 records
    options: { on_duplicate: "skip" }
})
// Returns: { success: true, import_id: "uuid", async: true, status: "importing",
//            message: "Import of 200 transaction records started in background..." }

// Step 2: Poll for progress (wait 5-10 seconds between polls)
get_imports(action="status", import_id="uuid")
// Returns: { status: "importing", progress_pct: 45, processed_records: 90,
//            imported_count: 85, error_count: 3, message: "Processing: 90/200 records (45%)" }

// Step 3: Check final result
get_imports(action="status", import_id="uuid")
// Returns: { status: "completed", progress_pct: 100, imported_count: 190,
//            skipped_count: 5, error_count: 5, errors_detail: [...], duration_ms: 45000 }
```

### Concurrent Import Limit

Only **one background import per organization** runs at a time (large record imports, CSV imports and approved batches, across server processes). Small record imports (<=50 records) are unaffected. A refused submission leaves no import record. When the running import is on the same server process the error names it:

```json
{
  "success": false,
  "error": "Organization already has a running import: <import_id>. Wait for it to complete or check status with get_imports(action='status', import_id='<import_id>')."
}
```

Otherwise it reads "Organization already has a running import. Wait for it to complete and check import history before trying again."

### Communicating Results to User

After an async import completes, report:

```
Import completed (45 seconds):
- 190 of 200 transactions posted successfully
- 5 skipped (duplicate reference numbers)
- 5 errors:
  - Row 34: Vendor "Unknown Corp" not found
  - Row 89: Account "9999" not found for entity 12
  - Row 112: Invalid date format "Jan 15 2026"
  - Row 156: Missing required field: lines
  - Row 198: Unbalanced journal entry (debits != credits)

Import ID: abc-123-def for reference.
```

---

## Batch-Level Approval (Optional)

Companies can enable batch-level approval for bulk imports. When enabled, imports require one approval per batch (not per record) before processing.

### How It Works

1. User submits import → ImportExecutor checks if `import_batch.review` workflow is active
2. If active: records are stored, ONE approval workflow is created for the entire batch
3. Approver reviews summary: "Import 200 AP_INVOICE records for entity 12"
4. On approval: ImportExecutor processes all records with full batch optimizations
5. On rejection: batch marked as rejected, nothing imported

### Configuration

- **Approval OFF** (default): imports process immediately — best for migrations and trusted operations
- **Approval ON**: enable the `import_batch.review` workflow definition in the admin dashboard
  - Which lane the batch gets, and whether that lane has approval steps, is your organisation's workflow configuration
  - A lane with no approval step completes at once (useful for an audit trail without blocking); a lane with approval steps waits for them before processing. The `status` in the result is authoritative

### Response When Approval Required

```json
{
  "success": true,
  "import_id": "uuid",
  "workflow_id": "uuid",
  "status": "pending_approval",
  "lane": "yellow",
  "total_records": 200,
  "message": "Import of 200 transaction records submitted for approval in yellow lane. Use workflow_my_tasks to view pending approvals."
}
```

Note: the `message` string above is emitted verbatim by the server and still names the deprecated `workflow_my_tasks` tool — the canonical call is `get_submissions(action='my_tasks')`.

Poll `get_imports(action="status", import_id)` to track status: `pending_approval` → `importing` → `completed`.

> `get_submissions(action='my_tasks')` only shows tasks for the session's **current** organization. If the approver works multiple orgs, `manage_organization(action="switch", organization_id=X)` to select the org that owns the import batch, then verify `get_organization(action="get_info")` reports it before checking pending approvals. A pinned connection may require reconnecting to the intended company.

---

**Version**: 1.2
**Last Updated**: January 2026
**Related Resources**:
- [Transaction Processing](transaction-processing.md) - Single transaction posting
- [Document Attachments](document-attachments.md) - Attaching PDFs/images to transactions
- [Vendor Management](vendor-management.md) - Vendor master data
- [Customer Management](customer-management.md) - Customer master data
- The `arfiti-core-implementation-consultant` plugin - Full system migration workflow
