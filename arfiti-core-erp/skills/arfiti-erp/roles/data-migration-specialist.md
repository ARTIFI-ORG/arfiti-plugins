# Data Migration Specialist

## Role Overview

The Data Migration Specialist orchestrates bulk data imports and system migrations. This role applies when a user needs to migrate from an external accounting system (QuickBooks, Xero, etc.), import large CSV/Excel datasets, or perform any bulk data operation exceeding normal transaction volumes.

## Key Responsibilities

### Migration Planning
- Assess source data structure and quality
- Map source fields to ERP target fields
- Plan import sequence (master data before transactions)
- Identify data cleanup and normalization needs
- Establish external ID mapping strategy

### Data Import Execution
- Import master data: accounts, dimensions, payment terms (small volume, via MCP)
- Import entities: customers, vendors, employees with external IDs (via MCP)
- Import transactions: AP invoices, AR invoices, journal entries (bulk via async import)
- Monitor async import progress and handle errors

### Data Quality
- Validate data before import (dry-run validation)
- Normalize inconsistent data (date formats, currency codes, naming)
- Deduplicate records across source and target systems
- Verify GL balance integrity after migration

---

## Migration Workflow

Follow this sequence for system migrations. Each phase must complete before the next begins.

### Phase 1: Reference Data (Small Volume)

Import configuration that other data depends on:

```javascript
// 1a. Chart of Accounts
submit("account", "import", {
  legal_entity_id: 12,
  records: [/* accounts with external_ids in metadata */],
  options: { on_duplicate: "skip" }
})

// 1b. Dimension Types and Values
submit("dimension_type", "import", { records: [...] })
submit("dimension_value", "import", { records: [...] })

// 1c. Payment Terms (if custom terms exist)
// Use individual submit("payment_term", "create", {...}) for each
```

### Phase 2: Master Entities (Medium Volume)

Import parties that transactions reference:

```javascript
// 2a. Vendors with external IDs
submit("vendor", "import", {
  legal_entity_id: 12,
  records: [{
    vendor_name: "Acme Corp",
    email: "ap@acme.com",
    payment_term_code: "NET30",
    metadata: { external_id: "QB-VEND-1234" }
  }, ...]
})

// 2b. Customers with external IDs
submit("customer", "import", {
  legal_entity_id: 12,
  records: [{
    customer_name: "Widget Inc",
    email: "ar@widget.com",
    metadata: { external_id: "QB-CUST-5678" }
  }, ...]
})

// 2c. Employees (if importing expense reports)
submit("employee", "import", { ... })

// 2d. Items (if importing line-item catalog)
submit("item", "import", { ... })
```

### Phase 2b: Opening Balances with Subledger Details

When migrating, opening balances should include individual open items (unpaid invoices/bills) and fixed asset details so that aging reports and depreciation schedules work properly.

```javascript
// Upload opening balances with subledger records
manage_imports("opening_balances_with_subledger", {
  legal_entity_id: 12,
  balances: [
    {"account_number": "1000", "debit": 50000, "credit": 0},  // Cash
    {"account_number": "1200", "debit": 25000, "credit": 0},  // AR (individual items below)
    {"account_number": "2110", "debit": 0, "credit": 30000},  // AP (individual items below)
    {"account_number": "1500", "debit": 40000, "credit": 0},  // Fixed assets
    {"account_number": "1600", "debit": 0, "credit": 15000},  // Accum depreciation
    {"account_number": "3000", "debit": 0, "credit": 70000},  // Equity
  ],
  fiscal_period_name: "2025-01",
  balancing_account_number: "3300",
  open_ar_items: [
    {"customer_name": "Acme Corp", "reference_number": "INV-001", "amount": 15000, "invoice_date": "2024-10-15", "due_date": "2024-11-15"},
    {"customer_name": "Widget Inc", "reference_number": "INV-002", "amount": 10000, "invoice_date": "2024-11-20", "due_date": "2024-12-20"},
  ],
  open_ap_items: [
    {"vendor_name": "Supplier Co", "reference_number": "BILL-042", "amount": 20000, "invoice_date": "2024-12-01", "due_date": "2025-01-15"},
    {"vendor_name": "Office Depot", "reference_number": "BILL-043", "amount": 10000, "invoice_date": "2024-12-10", "due_date": "2025-01-10"},
  ],
  fixed_assets_detail: [
    {"name": "Server Equipment", "acquisition_date": "2023-06-15", "original_cost": 25000, "accumulated_depreciation": 10000, "useful_life_months": 60},
    {"name": "Office Furniture", "acquisition_date": "2022-01-01", "original_cost": 15000, "accumulated_depreciation": 5000, "useful_life_months": 84},
  ]
})
```

**How it works:**
- Creates individual AR_INVOICE / AP_INVOICE transactions for each open item
- Uses a clearing account (0000) so the OPENING_ENTRY stays balanced
- Creates fixed asset register records so depreciation can resume
- Open item totals should match the corresponding control account balances in the trial balance

**If subledger details are not available**, fall back to basic opening balances:

```javascript
manage_imports("opening_balances", {
  legal_entity_id: 12,
  balances: [...],
  fiscal_period_name: "2025-01",
  balancing_account_number: "3300"
})
```

### Phase 3: Transactions (Large Volume, Async)

Import historical transactions referencing entities by external ID:

```javascript
// For >50 records, this runs asynchronously
submit("transaction", "import", {
  legal_entity_id: 12,
  records: [{
    transaction_type_code: "AP_INVOICE",
    external_vendor_id: "QB-VEND-1234",    // Resolved via metadata
    transaction_date: "2025-06-15",
    reference_number: "INV-001",
    lines: [{
      description: "Supplies",
      quantity: 1,
      unit_price: 250.00,
      external_account_id: "QB-ACCT-6100"  // Resolved via metadata
    }]
  }, ...],
  options: {
    on_duplicate: "skip",
    batch_size: 50,
    stop_on_error: false
  }
})
// Returns: { import_id: "uuid", async: true, status: "importing" }
```

### Phase 4: Monitor and Verify

```javascript
// Poll import progress
get_imports(action="status", import_id="uuid")
// Returns: { status: "importing", progress_pct: 65, processed_records: 130/200 }

// When completed, verify:
// 1. Check import result for errors
// 2. Run trial balance to verify GL integrity
// 3. Compare totals with source system
```

---

## Async Import Behavior

Imports are automatically routed based on record count:

| Records | Behavior | Response |
|---------|----------|----------|
| 1-50 | Synchronous | Full result with counts and errors |
| 51+ | Asynchronous | Returns import_id immediately |

### Polling Pattern for Large Imports

When an import returns `async: true`:

1. Note the `import_id` from the response
2. Wait 5-10 seconds
3. Call `get_imports(action="status", import_id)` to check progress
4. Repeat until `status` is `"completed"` or `"failed"`
5. Report final results to user

### Concurrent Import Limit

Only **one background import per organization** can run at a time: large record imports, CSV imports and approved batches, across server processes. A second one is refused with an error and leaves no import record; check import history and start it when the first finishes. Small record imports (<=50 records) are not affected by this limit.

### Approval Gate and Idempotent Re-runs

Both `submit(object_type, "import", ...)` and `manage_imports(action, ...)` route through the same import executor, so both are subject to any org-configured `import_batch.review` approval workflow — a large migration batch may land in `pending_approval` before it runs rather than executing immediately.

A zero-error run always reports `success: true` — this includes re-running the same batch after everything already imported: every record resolves as a duplicate skip (`imported: 0, updated: 0, skipped: N`), which is still success, not a failure. Don't treat `imported: 0` alone as a sign something went wrong — check `error_count` / `errors_detail` instead. Partial success (`success: true` with errors present) only happens when `stop_on_error=false` and at least one record imported.

---

## Data Cleanup Guidelines

### Before Import
- Normalize date formats to YYYY-MM-DD
- Standardize currency codes to 3-letter ISO (EUR, USD, GBP)
- Trim whitespace from names and codes
- Remove duplicate records from source data
- Verify all referenced entities exist (accounts, vendors, etc.)

### Entity Resolution
The import system resolves entities flexibly. Use the most reliable identifier available:

1. **Internal ID** (fastest): `vendor_id: 45`
2. **Global ID**: `global_vendor_id: "VEND-000123"`
3. **External ID** (for migration): `external_vendor_id: "QB-VEND-1234"`
4. **Tax ID**: `tax_id: "12-3456789"`
5. **Name** (least reliable): `vendor_name: "Acme Corp"`

### Error Recovery
If some records fail during import:
1. Check `errors_detail` in the import result
2. Fix the problematic records
3. Re-submit with `on_duplicate: "skip"` to skip already-imported records
4. Successfully imported records are NOT rolled back

---

## Escalation Path

1. **Field mapping questions**: Senior Accountant
2. **GL balance discrepancies**: Controller
3. **Tax code mapping**: Tax Manager (the organisation's tax role)
4. **Technical import errors**: System Administrator

---

**Version**: 1.0
**Last Updated**: 2026-01-31
**Related Resources**:
- [Bulk Transaction Processing](../resources/bulk-transaction-processing.md) - Import payload format and options
- [Transaction Processing](../resources/transaction-processing.md) - Single transaction posting
- [Vendor Management](../resources/vendor-management.md) - Vendor import and external IDs
- [Customer Management](../resources/customer-management.md) - Customer import and external IDs
- [Accounts Management](../resources/accounts-management.md) - Chart of accounts import
