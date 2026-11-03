# Cost Accruals Management

This guide covers cost accruals, COGS posting, inventory costing methods, expense accruals, and prepaid expense amortization. Cost accruals ensure expenses are recognized in the period they are incurred (matching principle), enabling accurate profitability reporting and compliance with GAAP/IFRS.

---

## Overview

| Aspect | Detail |
|--------|--------|
| **Core principle** | Matching principle -- match costs to revenue in the same period |
| **COGS posting** | Not automatic: post COGS as a journal entry when you invoice inventory items |
| **Costing methods** | Standard, FIFO, Weighted Average, Specific Identification |
| **Expense accruals** | Recognize expenses before cash payment (utilities, rent, salaries) |
| **Prepaid amortization** | Spread prepaid costs over benefit periods via amortization schedules |
| **GL pattern (COGS)** | DR 5000 COGS / CR 1400 Inventory |
| **GL pattern (accrual)** | DR Expense / CR 2600 Accrued Expenses |
| **GL pattern (prepaid)** | DR Expense / CR 1400 Prepaid Assets |

### Cost Accrual Flow

```
COGS (posted by you or an agent on sale):
  AR Invoice with inventory items posts revenue only
      |
      v
  Revenue entry: DR 1200 AR / CR 4000 Revenue
      |
      v
  Post a journal entry for the cost of the units sold
  COGS entry:    DR 5000 COGS / CR 1400 Inventory
      |
      v
  Income statement shows accurate gross margin

Expense Accruals (manual at period end):
  Estimate expense incurred but not yet billed
      |
      v
  Post journal entry: DR Expense / CR 2600 Accrued Expenses
      |
      v
  Next period: Reverse accrual when actual bill received

Prepaid Amortization (schedule-based):
  Pay annual insurance premium
      |
      v
  Create amortization schedule: straight_line over 12 months
      |
      v
  Monthly: DR 6200 Insurance Expense / CR 1400 Prepaid Insurance
```

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

---

## Cost of Goods Sold (COGS)

### What is COGS?

Cost of inventory sold during a period. Calculated as:

```
COGS = Beginning Inventory + Purchases - Ending Inventory
```

Posting an AR invoice does not post COGS. The invoice posts the revenue entry only; you (or an agent) post the COGS entry as a journal entry.

### Posting COGS

When you invoice inventory items:

1. Post the AR invoice (revenue entry)
2. For each product line, take the unit cost (the item's `cost_price`, or the cost from your costing method)
3. Calculate COGS: `quantity * unit cost`
4. Post a `JOURNAL_ENTRY`: debit the item's `cogs_account_number`, credit inventory

**Revenue entry (posted by the AR invoice):**
```
DR  1200 Accounts Receivable       $1,000
CR  4000 Revenue                   $1,000
```

**COGS entry (the journal entry you post):**
```
DR  5000 Cost of Goods Sold        $600   (10 units * $60 unit cost)
CR  1400 Inventory                 $600
```

The COGS amount is the unit cost multiplied by the quantity on each invoice line. The platform does not calculate it.

### Multi-Line Invoice COGS

Each line is calculated independently:

```
Line 1: 10 x Widget A ($60 cost)  -> COGS $600
Line 2:  5 x Widget B ($80 cost)  -> COGS $400
Line 3: 20 x Widget C ($40 cost)  -> COGS $800
                            Total COGS: $1,800
```

You can post all COGS lines in a single journal entry.

### Service Items (No COGS)

Service items (`item_type = revenue_service`) carry no COGS entry. Costs for service items are recorded when expenses are incurred, not when revenue is billed.

---

## Inventory Costing Methods

The platform does not store a costing method. Choose one and use it to work out the COGS amount you post.

### 1. Standard Costing

Predetermined cost per unit. Most common for manufacturing.

```
Standard cost per widget: $60

Sale of 10 widgets:
  COGS = 10 * $60 = $600

If actual cost differs:
  Actual: $58 -> $2 favorable variance
  Actual: $62 -> $2 unfavorable variance

Variance entry:
  DR  5100 Cost Variance    $20
  CR  1400 Inventory        $20
```

**Best for:** Manufacturing, budgeted costs, stable pricing, variance analysis.

### 2. FIFO (First-In, First-Out)

Sell oldest inventory first.

```
Inventory:
  Purchase 1: 50 units @ $55 (Jan 5)
  Purchase 2: 50 units @ $65 (Feb 10)

Sale: 75 units (Mar 1)

COGS (FIFO):
  First 50 units @ $55 = $2,750
  Next  25 units @ $65 = $1,625
  Total COGS: $4,375

Remaining: 25 units @ $65 = $1,625
```

**Best for:** Perishable goods, rising prices, physical flow matching.

### 3. Weighted Average

Average cost of all units available.

```
Inventory:
  Purchase 1: 100 units @ $50 = $5,000
  Purchase 2: 200 units @ $60 = $12,000
  Total: 300 units, $17,000

Average cost: $17,000 / 300 = $56.67

Sale: 150 units
  COGS = 150 * $56.67 = $8,500

Remaining: 150 units @ $56.67 = $8,500
```

**Best for:** Interchangeable goods, simplicity, moderate price fluctuations.

### 4. Specific Identification

Track actual cost of each unit individually.

```
Inventory:
  Car VIN-001: Cost $45,000
  Car VIN-002: Cost $47,000
  Car VIN-003: Cost $46,000

Sale: VIN-002
  COGS = $47,000 (actual cost of that specific unit)
```

**Best for:** High-value items, unique items, serial number tracking.

---

## Item Master Data for Costing

### Key Fields on master_items

| Field | Description |
|-------|-------------|
| `cost_price` | Cost per unit, a starting point for the COGS amount you post |
| `item_type` | `revenue_product`, `revenue_service`, `expense_product` or `expense_service` |
| `cogs_account_number` | GL account to debit in your COGS journal entry (e.g., `5000`) |
| `asset_account_number` | GL account for the inventory asset (e.g., `1400`) |

### Querying Item Costs

```
get_entity("item", id=42)
```

Returns item details including `cost_price` and `item_type`.

```
query("item", filters={
    "item_type": "revenue_product",
    "legal_entity_id": 9
})
```

```
query("item", query="WIDGET-001")
```

---

## Expense Accruals

### What are Expense Accruals?

Expenses incurred in the current period but not yet billed or paid. Accruals ensure the period's income statement reflects all costs, even if invoices have not arrived.

### Common Accrued Expenses

| Expense Type | Typical Timing | Example |
|-------------|----------------|---------|
| Utilities | Monthly usage billed next month | Oct electricity billed Nov 15 |
| Rent | Occupancy cost, sometimes paid in arrears | Monthly office rent |
| Salaries | Days worked but not yet in payroll | 3 days worked after last payroll |
| Interest | Loan interest accrued daily | Monthly interest on credit line |
| Professional fees | Services received, invoice pending | Audit fees for Q4 |

### Creating Expense Accruals

Expense accruals are posted as journal entries via the transaction workflow.

**Month-end accrual:**
```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="transaction", operation="post")

// Step 2: Submit with discovered fields
```
```
submit("transaction", "post", {
    "transaction_type_code": "JOURNAL_ENTRY",
    "legal_entity_id": 9,
    "description": "Oct 2026 utility accrual",
    "lines": [
        {"account_number": "6300", "debit": 2500.00, "credit": 0, "description": "Utilities expense - Oct estimate"},
        {"account_number": "2600", "debit": 0, "credit": 2500.00, "description": "Accrued expenses - utilities"}
    ]
})
// Tip: Use validate_only=true to check payload before submitting
```

**GL pattern:**
```
DR  6300 Utilities Expense         $2,500
CR  2600 Accrued Expenses          $2,500
```

### Reversing Accruals

When the actual bill arrives, reverse the accrual and book the real expense.

**Reversal entry (next period):**
```
submit("transaction", "post", {
    "transaction_type_code": "JOURNAL_ENTRY",
    "legal_entity_id": 9,
    "description": "Reverse Oct utility accrual",
    "lines": [
        {"account_number": "2600", "debit": 2500.00, "credit": 0, "description": "Reverse accrual"},
        {"account_number": "6300", "debit": 0, "credit": 2500.00, "description": "Reverse accrual"}
    ]
})
```

Then post the actual AP invoice for $2,450 through the normal billing workflow. Net effect: October shows the estimated expense, November shows the small $50 variance.

### Salary Accrual Example

```
Oct 31: 3 working days after last bi-weekly payroll
Daily salary cost: $5,000

submit("transaction", "post", {
    "transaction_type_code": "JOURNAL_ENTRY",
    "legal_entity_id": 9,
    "description": "Salary accrual - 3 days Oct 29-31",
    "lines": [
        {"account_number": "6500", "debit": 15000.00, "credit": 0, "description": "Salary expense accrual"},
        {"account_number": "2600", "debit": 0, "credit": 15000.00, "description": "Accrued salaries"}
    ]
})
```

---

## Prepaid Expense Amortization

### What are Prepaid Expenses?

Costs paid in advance for future benefit periods. Examples: annual insurance premiums, software licenses, prepaid rent.

### GL Pattern

**Initial payment (full amount to prepaid asset):**
```
DR  1400 Prepaid Insurance         $24,000
CR  1000 Bank                      $24,000
```

**Monthly amortization (spread over 12 months):**
```
DR  6200 Insurance Expense         $2,000
CR  1400 Prepaid Insurance         $2,000
```

### Source identity, splits and recognition dates

Read the posted source transaction and its GL before creating a schedule. Provide
`source_transaction_id` and, when needed, `source_gl_line_id` to identify exactly
one line in the entity/source account. `source_transaction_line_id` denotes the
source document line, not a GL ID. Ambiguous source lines are refused. The schedule
currency must match the source GL document currency. A source-less schedule cannot
provide this source-capacity protection; do not omit a known source to bypass it.

A second allocation requires `allow_source_split: true` and must fit remaining
source capacity. Changing the destination account does not create new capacity.
Paused commitments and posted portions of cancelled schedules still count.
Cancellation voids unposted lines; it does not undo recognition journals. Inspect
posted lines before replacing a cancelled schedule.

Use `schedule_type: "straight_line"`; unsupported calculation methods are refused.
Monthly amounts use daily proration and may vary. Creation returns `total_amount`,
`first_period_amount` and `period_amounts`; `amount_per_period` is populated only
when all periods are equal. Do not multiply the first stub by the period count.

Recognition keeps service dates and posts on the earliest open, unlocked date on
or after service-period end, no later than `as_of_date` or today. If none exists,
the line requires remediation/review. Journal posting and line consumption commit
atomically, including concurrent recognizers. A no-work scan is not a failure.


### Using Amortization Schedules for Prepaid Amortization

Create a straight-line amortization schedule to automate monthly amortization.
(Note: this uses the `amortization_schedule` object type, not `allocation_schedule` —
the older `allocation_schedule.*` workflow was a V1 allocation engine retired in
favor of the plugin-based `allocation_run.*` model and has no executor; the
`allocation_schedules` table itself lives on under `amortization_schedule.*` for
deferred revenue/expense amortization instead.)

```
submit("amortization_schedule", "create", {
    "kind": "expense",
    "legal_entity_id": 9,
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
    "total_amount": 24000.00,
    "source_account_id": 1400,
    "target_account_id": 6200,
    "schedule_type": "straight_line",
    "frequency": "monthly"
})
```

Then recognize the lines that have come due (run monthly, or as part of month-end close):

```
submit("amortization_schedule", "recognize", {
    "legal_entity_id": 9,
    "as_of_date": "2026-01-31"
})
```

### Software License Prepaid

```
submit("amortization_schedule", "create", {
    "kind": "expense",
    "legal_entity_id": 9,
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
    "total_amount": 36000.00,
    "source_account_id": 1400,
    "target_account_id": 6400,
    "schedule_type": "straight_line",
    "frequency": "monthly"
})
```

---

## Common Scenarios

### Scenario 1: Monthly Close with Accruals

Complete month-end with expense accruals before closing the period.

```
-- 1. Post expense accruals for incurred but unbilled costs
submit("transaction", "post", {
    "transaction_type_code": "JOURNAL_ENTRY",
    "legal_entity_id": 9,
    "description": "Jan 2026 month-end accruals",
    "lines": [
        {"account_number": "6300", "debit": 2500.00, "credit": 0, "description": "Utilities accrual"},
        {"account_number": "6400", "debit": 10000.00, "credit": 0, "description": "Rent accrual"},
        {"account_number": "6500", "debit": 5000.00, "credit": 0, "description": "Salary accrual"},
        {"account_number": "2600", "debit": 0, "credit": 17500.00, "description": "Accrued expenses"}
    ]
})

-- 2. Recognize prepaid amortization schedules due this period
submit("amortization_schedule", "recognize", {
    "legal_entity_id": 9,
    "as_of_date": "2026-01-31"
})

-- 3. Review income statement for completeness
-- 4. Close the period
```

### Scenario 2: Product Sale, then COGS

Sell inventory items, then post the COGS entry yourself.

```
-- Post AR invoice with inventory items
submit("transaction", "post", {
    "transaction_type_code": "AR_INVOICE",
    "legal_entity_id": 9,
    "customer_id": 42,
    "lines": [
        {"item_id": 10, "quantity": 100, "unit_price": 50.00, "description": "Standard Widgets"}
    ]
})

-- The invoice posts the revenue entry only:
-- Revenue: DR 1200 AR $5,000 / CR 4000 Revenue $5,000

-- Then post COGS (100 units * $30 unit cost):
submit("transaction", "post", {
    "transaction_type_code": "JOURNAL_ENTRY",
    "legal_entity_id": 9,
    "lines": [
        {"account_number": "5000", "debit": 3000.00, "credit": 0, "description": "COGS - Standard Widgets"},
        {"account_number": "1400", "debit": 0, "credit": 3000.00, "description": "Inventory relief - Standard Widgets"}
    ]
})

-- Verify with:
get_entity("transaction", id=<transaction_id>)
```

### Scenario 3: Mixed Invoice (Inventory + Service Items)

```
submit("transaction", "post", {
    "transaction_type_code": "AR_INVOICE",
    "legal_entity_id": 9,
    "customer_id": 42,
    "lines": [
        {"item_id": 10, "quantity": 50, "unit_price": 100.00, "description": "Widgets"},
        {"item_id": 20, "quantity": 10, "unit_price": 150.00, "description": "Consulting Hours"}
    ]
})

-- The invoice posts revenue for both lines.
-- Post a COGS journal entry for the Widget line only (product item);
-- Consulting Hours is a service item and carries no COGS.
```

### Scenario 4: Cost Variance Analysis

When actual costs differ from standard costs:

```
-- Standard cost: $60/unit, actual purchase at $62/unit for 100 units

-- Record variance via journal entry
submit("transaction", "post", {
    "transaction_type_code": "JOURNAL_ENTRY",
    "legal_entity_id": 9,
    "description": "Purchase price variance - Widget batch 2026-01",
    "lines": [
        {"account_number": "5100", "debit": 200.00, "credit": 0, "description": "Unfavorable price variance (100 * $2)"},
        {"account_number": "1400", "debit": 0, "credit": 200.00, "description": "Inventory adjustment"}
    ]
})
```

---

## Key Accounts Reference

| Account | Name | Usage |
|---------|------|-------|
| 1200 | Accounts Receivable | Customer balance on sale |
| 1400 | Inventory / Prepaid Assets | Inventory value, prepaid expenses |
| 2100 | Accounts Payable | Vendor bills |
| 2600 | Accrued Expenses | Expenses incurred but not yet paid |
| 4000 | Revenue | Sales revenue |
| 5000 | Cost of Goods Sold | Inventory cost when sold |
| 5100 | Cost Variance | Standard vs actual cost difference |
| 6200 | Insurance / Travel Expense | Insurance, prepaid amortization target |
| 6300 | Utilities Expense | Utility costs |
| 6400 | Software / Rent Expense | Software licenses, rent |
| 6500 | Salary Expense | Payroll costs |

---

## COGS Components

For manufacturing or landed-cost scenarios, total item cost may include multiple components:

| Component | Description | Example |
|-----------|-------------|---------|
| Product Cost | Direct manufacturing or purchase cost | $50/unit |
| Freight-In | Shipping to receive inventory | $3/unit |
| Customs/Duties | Import fees | $2/unit |
| Direct Labor | Manufacturing labor | $3/unit |
| Manufacturing Overhead | Factory costs | $2/unit |
| **Total Landed Cost** | **Sum of all components** | **$60/unit** |

Use the total landed cost as the unit cost when you work out the COGS amount; keep the item's `cost_price` in line with it.

---

*Last Updated: 2026-03-14*
*Related Resources:*
- [Items Management](items-management.md) - Item master data, cost fields, inventory settings
- [Transaction Processing](transaction-processing.md) - AR invoice posting and GL entries
- [Allocation Workflows](allocation-workflows.md) - Schedule-based prepaid amortization
- [Financial Period Management](financial-period-management.md) - Period close and month-end procedures
- [Accounts Management](accounts-management.md) - Chart of accounts for expense and asset accounts
