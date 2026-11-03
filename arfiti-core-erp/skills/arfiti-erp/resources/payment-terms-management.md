# Payment Terms Management

## Overview

**Payment terms** define when invoices are due and whether early payment discounts apply. They are universal reference data used across all customers, vendors, and invoices to ensure consistent payment expectations and automated due date calculations.

**Key Features:**
- Standard payment term definitions (NET_30, NET_60, etc.)
- Early payment discount support (e.g., 2% discount if paid within 10 days)
- Automatic due date calculation
- Cash flow management tools
- Organization-wide consistency (no entity-specific variations)

**Architecture**: Simple reference data table (no MSEO pattern) - same payment terms apply to all legal entities within an organization.

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for payment term operations, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

## Common Use Cases

1. **Standard B2B Terms**: NET_30, NET_60, NET_90 for business customers
2. **Cash Flow Improvement**: Early payment discounts (NET_30_2_10) to incentivize faster payment
3. **Retail/E-commerce**: Immediate payment terms (DUE_ON_RECEIPT, COD)
4. **Vendor Management**: Extended payment terms (NET_60, NET_90) for supplier relationships
5. **Industry-Specific**: Custom terms for construction, government, wholesale
6. **Seasonal Promotions**: Extended terms during slow periods

---

## Complete Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

### Payment Terms Fields (payment_terms table)

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| **id** | integer | Auto | Primary key | Auto-generated |
| **code** | varchar(20) | Yes | Unique identifier | 1-20 chars, auto-uppercased, unique |
| **description** | varchar(255) | Yes | Human-readable description | 1-255 chars |
| **days_until_due** | integer | Yes | Days until payment is due | >= 0 (0 = immediate) |
| **discount_days** | integer | No | Days to qualify for discount | >= 0, default: 0 |
| **discount_percent** | numeric(5,2) | No | Early payment discount % | 0.00-100.00, default: 0.00 |
| **is_active** | boolean | No | Active status | Default: true |
| **created_at** | timestamp | Auto | Creation timestamp | Auto-set |
| **created_by** | integer | Auto | Creator user ID | From context |
| **updated_at** | timestamp | Auto | Update timestamp | Auto-updated |
| **updated_by** | integer | Auto | Updater user ID | From context |

### Code Naming Conventions

> **Format flexibility:** Payment terms codes are case-insensitive and the underscore is optional. The system accepts both `NET_30` and `NET30`, as well as `net_30` or `Net30`. The canonical stored format uses underscores (e.g., `NET_30`), but input is normalized automatically.

**Standard Format:**
- `NET_X` - Payment due in X days (e.g., `NET_30`, `NET_60`; also accepted as `NET30`, `NET60`)
- `NET_X_Y_Z` - Net X days, Y% discount if paid within Z days (e.g., `NET_30_2_10`)
- `DUE_ON_RECEIPT` - Immediate payment
- `COD` - Cash on delivery
- `EOM` - End of month
- `EOM_X` - X days after end of month

**Examples:**
- `NET_30` - Payment due in 30 days
- `NET_30_2_10` - Net 30, 2% discount if paid within 10 days
- `NET_60_2_10` - Net 60, 2% discount if paid within 10 days
- `DUE_ON_RECEIPT` - Payment due immediately
- `COD` - Cash on delivery

### Standard Pre-Seeded Payment Terms

The system comes with 17 standard payment terms:

**Immediate Terms:**
- `DUE_ON_RECEIPT` (0 days)
- `COD` (0 days)

**Standard Net Terms:**
- `NET_7`, `NET_14`, `NET_15`, `NET_30`, `NET_45`, `NET_60`, `NET_90`, `NET_120`, `NET_180`

**Terms with Discounts:**
- `NET_30_1_10` (1% discount within 10 days)
- `NET_30_2_10` (2% discount within 10 days)
- `NET_45_2_15` (2% discount within 15 days)
- `NET_60_2_10` (2% discount within 10 days)

**End of Month:**
- `EOM` (30 days)
- `EOM_30` (60 days)

---

## Workflow Operations

### Available Workflows

| Workflow | Purpose | When to Use |
|----------|---------|-------------|
| `payment_term.create` | Create new payment term | Adding custom payment terms |
| `payment_term.update` | Update existing payment term | Modifying description, days, or discount |
| `payment_term.deactivate` | Deactivate payment term | Retiring unused terms |

### Query Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `query("payment_term", filters)` | List payment terms with filters | Browsing all terms, filtering by status or discount |
| `get_entity("payment_term", id=X)` | Get single payment term by ID | Looking up a specific known term (find the ID by searching its code with `query`) |
| `query("payment_term", query)` | Search payment terms by text | Finding terms by keyword (e.g., "discount", "NET_30") |

**When to use `query` vs `query`:**
- Use `filters` when browsing by structured fields (`legal_entity_id`, `is_active` are the only filters)
- Use `query` when looking up terms by text/keyword (e.g., searching for "discount" or "NET_30")

---

## Creating Payment Terms

### Workflow: payment_term.create

**Purpose**: Create a new payment term with optional early payment discount

**Approval**: no approval step by default; the organisation's workflow configuration sets the lane and any approval, and the `status` and `lane` in the submit() result are authoritative.

**Use Cases**:
- Setting up standard business payment terms
- Creating industry-specific terms
- Adding early payment discount incentives
- Defining custom terms for specific customers/vendors

**Payload**:

```javascript
{
  // Required fields
  "code": "NET_45",                          // Unique identifier (auto-uppercased)
  "description": "Payment due in 45 days",   // Human-readable description
  "days_until_due": 45,                      // Days until payment is due (>= 0)

  // Optional fields (for early payment discounts)
  "discount_days": 15,                       // Days to qualify for discount
  "discount_percent": 2.0                    // Discount percentage (0-100)
}
```

**Example: Standard NET 30**

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="payment_term", operation="create")

// Step 2: Submit with discovered fields
submit("payment_term", "create", {
    code: "NET_30",
    description: "Payment due in 30 days",
    days_until_due: 30
})
// Tip: Use validate_only=true to check payload before submitting
```

**Response**:
```javascript
{
  "success": true,
  "payment_term_id": 1,
  "code": "NET_30",
  "workflow_id": "wf-uuid-here",
  "message": "Payment term NET_30 created successfully"
}
```

**Example: Immediate Payment**

```javascript
submit("payment_term", "create", {
    code: "DUE_ON_RECEIPT",
    description: "Payment due immediately upon receipt",
    days_until_due: 0
})
```

**Example: With Early Payment Discount**

```javascript
submit("payment_term", "create", {
    code: "NET_30_2_10",
    description: "Net 30, 2% discount if paid within 10 days",
    days_until_due: 30,
    discount_days: 10,
    discount_percent: 2.0
})
```

**How Early Payment Discount Works:**
```
Invoice Amount: $10,000
Terms: NET_30_2_10

Timeline:
Day 0 (Jan 1)     Day 10 (Jan 10)       Day 30 (Jan 30)
Invoice Date      Discount Ends         Due Date

Pay within 10 days: $9,800 (2% discount = $200 savings)
Pay after 10 days:  $10,000 (full amount)
```

**Example: Aggressive Cash Flow Terms**

```javascript
submit("payment_term", "create", {
    code: "NET_30_5_7",
    description: "Net 30, 5% discount if paid within 7 days",
    days_until_due: 30,
    discount_days: 7,
    discount_percent: 5.0
})
```

**Example: Industry-Specific Terms**

```javascript
// Construction industry - progress payments
submit("payment_term", "create", {
    code: "NET_30_PROGRESS",
    description: "Net 30 from progress payment milestone",
    days_until_due: 30
})

// Government contracts
submit("payment_term", "create", {
    code: "NET_30_GOV",
    description: "Net 30 days (government contract)",
    days_until_due: 30
})

// Wholesale with discount
submit("payment_term", "create", {
    code: "NET_30_2_10_WHOLESALE",
    description: "Net 30, 2% discount within 10 days (wholesale customers)",
    days_until_due: 30,
    discount_days: 10,
    discount_percent: 2.0
})
```

**Validation**:
- code: Required, 1-20 chars, auto-uppercased, must be unique
- description: Required, 1-255 chars
- days_until_due: Required, must be >= 0 (0 = immediate payment)
- discount_days: Optional, must be >= 0, must be < days_until_due
- discount_percent: Optional, 0.00-100.00

**Returns**:

```javascript
{
  "success": true,
  "payment_term_id": 8,
  "code": "NET_45",
  "workflow_id": "wf-uuid-here",
  "message": "Payment term NET_45 created successfully"
}
```

---

## Updating Payment Terms

### Workflow: payment_term.update

**Purpose**: Update existing payment term properties (description, days, discount)

**Approval**: no approval step by default (configurable per organisation; the submit() result is authoritative).

**Use Cases**:
- Updating description for clarity
- Adjusting discount percentage
- Changing due date period
- Reactivating deactivated terms

**Payload**:

```javascript
{
  // Required field
  "payment_term_id": 2,             // Payment term ID to update

  // Optional fields to update
  "description": "...",             // New description
  "days_until_due": 35,             // New days until due
  "discount_days": 12,              // New discount days
  "discount_percent": 2.5,          // New discount percentage
  "is_active": true                 // Active status
}
```

**Note**: Cannot update the `code` field (it's the unique identifier). To change a code, deactivate the old term and create a new one.

**Example: Update Description**

```javascript
submit("payment_term", "update", {
    payment_term_id: 2,
    description: "Payment due in 30 days from invoice date"
})
```

**Example: Update Discount**

```javascript
submit("payment_term", "update", {
    payment_term_id: 8,
    discount_percent: 2.5  // Increase from 2.0% to 2.5%
})
```

**Example: Update Due Date Period**

```javascript
submit("payment_term", "update", {
    payment_term_id: 3,
    days_until_due: 35  // Change from 30 to 35 days
})
```

**Example: Reactivate Deactivated Term**

```javascript
submit("payment_term", "update", {
    payment_term_id: 9,
    is_active: true  // Make available again
})
```

**Returns**:

```javascript
{
  "success": true,
  "payment_term_id": 2,
  "updated_fields": ["description"],
  "workflow_id": "wf-uuid-here",
  "message": "Payment term updated successfully"
}
```

---

## Deactivating Payment Terms

### Workflow: payment_term.deactivate

**Purpose**: Soft delete payment term (hide from selection but preserve history)

**Approval**: no approval step by default (configurable per organisation; the submit() result is authoritative).

**Use Cases**:
- Retiring unused payment terms
- Discontinuing promotional terms
- Cleaning up test/duplicate terms

**Payload**:

```javascript
{
  "code": "NET_90"  // Required: Payment term code to deactivate
}
```

**Example: Deactivate Unused Term**

```javascript
submit("payment_term", "deactivate", {
    code: "NET_90"
})
```

**What Happens When Deactivated:**

**Hidden From:**
- Payment term selection dropdowns (customer/vendor setup)
- New invoice creation
- `query("payment_term", filters={"is_active": true})` queries

**Still Visible In:**
- Existing customer/vendor records (unchanged)
- Historical invoices (preserved)
- `query("payment_term")` queries (without active filter)
- Audit logs
- Payment history reports

**Returns**:

```javascript
{
  "success": true,
  "code": "NET_90",
  "deactivated_at": "2025-01-14T10:30:00Z",
  "workflow_id": "wf-uuid-here",
  "message": "Payment term NET_90 deactivated successfully"
}
```

**Best Practices:**

1. **Don't delete** - Always deactivate instead of deleting (preserves audit trail)
2. **Check usage first** - Verify how many customers/vendors use the term before deactivating
3. **Migrate customers** - Update customers to new terms before deactivating old ones
4. **Document reason** - Note why term was deactivated (can add to description before deactivating)

**Example: Check Usage Before Deactivating**

```javascript
// Step 1: Check how many customers use this term
query("customer", filters={"payment_terms_code": "NET_90"})
// Result: 5 customers found

// Step 2: Migrate customers to NET_60
// ... update each customer's payment_terms_code ...

// Step 3: Deactivate the term
submit("payment_term", "deactivate", {
    code: "NET_90"
})
```

---

## Query Tools

### List Payment Terms

Use `query()` to query payment terms:

```javascript
// List all active payment terms
query("payment_term", filters={"is_active": true})
```

**Response**:
```javascript
{
  "success": true,
  "payment_terms": [
    {
      "id": 1,
      "code": "NET_15",
      "description": "Payment due in 15 days",
      "days_until_due": 15,
      "discount_days": 0,
      "discount_percent": 0.00,
      "is_active": true
    },
    {
      "id": 2,
      "code": "NET_30",
      "description": "Payment due in 30 days",
      "days_until_due": 30,
      "discount_days": 0,
      "discount_percent": 0.00,
      "is_active": true
    },
    {
      "id": 8,
      "code": "NET_30_2_10",
      "description": "Net 30, 2% discount if paid within 10 days",
      "days_until_due": 30,
      "discount_days": 10,
      "discount_percent": 2.00,
      "is_active": true
    }
    // ... more terms
  ],
  "count": 17
}
```

**List all payment terms (including inactive):**

```javascript
query("payment_term")
```

**Discount availability** (not a query filter: list the active terms and read each term's discount fields):

```javascript
query("payment_term", filters={"is_active": true})
```

### Get Single Payment Term

Use `get_entity()` to get a specific payment term:

```javascript
// Get by code
get_entity("payment_term", global_id="NET_30")
```

**Response**:
```javascript
{
  "success": true,
  "payment_term": {
    "id": 2,
    "code": "NET_30",
    "description": "Payment due in 30 days",
    "days_until_due": 30,
    "discount_days": 0,
    "discount_percent": 0.00,
    "is_active": true,
    "created_at": "2025-01-01T00:00:00Z",
    "created_by": 1
  }
}
```

**Get by ID:**

```javascript
get_entity("payment_term", id=2)
```

### Search Payment Terms

Use `query()` tool for dynamic queries:

```javascript
// Search for NET terms
query("payment_term", query="NET_30")

// Search for discount terms
query("payment_term", query="discount")

// Search for immediate payment terms
query("payment_term", query="due on receipt")
```

---

## Early Payment Discounts

### How Discounts Work

Early payment discounts incentivize customers to pay faster, improving your organization's cash flow.

**Example: NET_30_2_10**

```
Invoice Amount: $10,000
Terms: NET_30_2_10 (Net 30, 2% discount if paid within 10 days)
Invoice Date: January 1

Timeline:
+-----------------------------------------------------+
|  Jan 1          Jan 10              Jan 30          |
|  Invoice Date   Discount Ends       Due Date        |
|                                                     |
|  |--------------|------------------|               |
|  Discount Period   Regular Period                  |
|  Pay $9,800       Pay $10,000                      |
|  (2% savings)     (full amount)                    |
+-----------------------------------------------------+

Paid on Jan 8 (within discount period):
  Discount Amount = $10,000 × 2% = $200
  Amount Due = $10,000 - $200 = $9,800

Paid on Jan 15 (after discount period):
  Discount Amount = $0
  Amount Due = $10,000
```

### Common Discount Structures

| Code | Regular Terms | Discount Offer | Annual Interest Rate Equivalent |
|------|---------------|----------------|----------------------------------|
| **NET_30_2_10** | 30 days | 2% off if paid in 10 days | ~36.7% APR |
| **NET_30_1_10** | 30 days | 1% off if paid in 10 days | ~18.4% APR |
| **NET_60_2_10** | 60 days | 2% off if paid in 10 days | ~14.7% APR |
| **NET_45_2_15** | 45 days | 2% off if paid in 15 days | ~24.5% APR |

**Why take the discount?** The annual interest rate equivalent is usually much higher than borrowing costs, making it financially attractive for customers to pay early.

### Creating Aggressive Discount Terms

```javascript
// High discount for very fast payment
submit("payment_term", "create", {
    code: "NET_30_5_7",
    description: "Net 30, 5% discount if paid within 7 days",
    days_until_due: 30,
    discount_days: 7,
    discount_percent: 5.0
})

// Graduated discounts (create multiple terms)
submit("payment_term", "create", {
    code: "NET_30_3_10",
    description: "Net 30, 3% discount if paid within 10 days",
    days_until_due: 30,
    discount_days: 10,
    discount_percent: 3.0
})
```

### Discount Calculation Examples

**Example 1: Standard 2/10 Net 30**
```
Invoice: $50,000
Terms: NET_30_2_10
Invoice Date: Feb 1

Discount Period: Feb 1-10
  If paid by Feb 10: $50,000 - ($50,000 × 2%) = $49,000
  Savings: $1,000

Regular Period: Feb 11-Mar 3
  If paid after Feb 10: $50,000 (full amount)
```

**Example 2: Aggressive 5/7 Net 30**
```
Invoice: $100,000
Terms: NET_30_5_7
Invoice Date: Mar 1

Discount Period: Mar 1-7
  If paid by Mar 7: $100,000 - ($100,000 × 5%) = $95,000
  Savings: $5,000

Regular Period: Mar 8-30
  If paid after Mar 7: $100,000 (full amount)
```

---

## Common Scenarios

### Scenario 1: Standard B2B Payment Terms

**Goal**: Set up typical business-to-business payment terms

```javascript
// Create standard NET 30
submit("payment_term", "create", {
    code: "NET_30",
    description: "Payment due in 30 days",
    days_until_due: 30
})

// Create NET 60 for larger customers
submit("payment_term", "create", {
    code: "NET_60",
    description: "Payment due in 60 days (approved customers only)",
    days_until_due: 60
})

// Create NET 15 for smaller orders
submit("payment_term", "create", {
    code: "NET_15",
    description: "Payment due in 15 days",
    days_until_due: 15
})
```

**Result**: 3 standard B2B payment terms available for customer assignment

---

### Scenario 2: Cash Flow Improvement with Discounts

**Goal**: Incentivize early payment to improve cash flow

```javascript
// Create attractive 2/10 Net 30
submit("payment_term", "create", {
    code: "NET_30_2_10",
    description: "Net 30, 2% discount if paid within 10 days",
    days_until_due: 30,
    discount_days: 10,
    discount_percent: 2.0
})

// Create aggressive 5/7 Net 30 for priority customers
submit("payment_term", "create", {
    code: "NET_30_5_7",
    description: "Net 30, 5% discount if paid within 7 days (VIP customers)",
    days_until_due: 30,
    discount_days: 7,
    discount_percent: 5.0
})
```

**Result**: Early payment discounts incentivize faster payment, improving cash flow

---

### Scenario 3: Retail/E-commerce Immediate Payment

**Goal**: Require immediate payment for retail/online sales

```javascript
// Create immediate payment terms
submit("payment_term", "create", {
    code: "DUE_ON_RECEIPT",
    description: "Payment due immediately upon receipt",
    days_until_due: 0
})

submit("payment_term", "create", {
    code: "COD",
    description: "Cash on delivery",
    days_until_due: 0
})
```

**Result**: Immediate payment terms for retail customers

---

### Scenario 4: Vendor Payment Terms

**Goal**: Set up payment terms for vendors/suppliers

```javascript
// Negotiate favorable terms with vendors
submit("payment_term", "create", {
    code: "NET_60",
    description: "Payment due in 60 days",
    days_until_due: 60
})

submit("payment_term", "create", {
    code: "NET_90",
    description: "Payment due in 90 days",
    days_until_due: 90
})

// Take advantage of vendor early payment discounts
submit("payment_term", "create", {
    code: "NET_60_2_10",
    description: "Net 60, 2% discount if paid within 10 days",
    days_until_due: 60,
    discount_days: 10,
    discount_percent: 2.0
})
```

**Result**: Extended payment terms for vendor relationships, with discount options

---

### Scenario 5: Seasonal Payment Terms

**Goal**: Offer extended terms during slow seasons

```javascript
// Extended terms for slow season
submit("payment_term", "create", {
    code: "NET_90_SEASONAL",
    description: "Net 90 days (seasonal promotion)",
    days_until_due: 90
})

// Deactivate after season ends
submit("payment_term", "deactivate", {
    code: "NET_90_SEASONAL"
})
```

**Result**: Temporary extended terms for seasonal promotions

---

### Scenario 6: Industry-Specific Terms

**Goal**: Create payment terms for specific industries

```javascript
// Construction industry - progress payments
submit("payment_term", "create", {
    code: "NET_30_PROGRESS",
    description: "Net 30 from progress payment milestone",
    days_until_due: 30
})

// Government contracts - standard terms
submit("payment_term", "create", {
    code: "NET_30_GOV",
    description: "Net 30 days (government contract)",
    days_until_due: 30
})

// Wholesale - standard terms with discount
submit("payment_term", "create", {
    code: "NET_30_2_10_WHOLESALE",
    description: "Net 30, 2% discount within 10 days (wholesale customers)",
    days_until_due: 30,
    discount_days: 10,
    discount_percent: 2.0
})
```

**Result**: Industry-specific payment terms for specialized business types

---

## Getting Reference Data

Payment terms are universal reference data - use dynamic queries instead of hardcoded values.

**Dynamic Queries:**

```javascript
// Get all active payment terms
query("payment_term", filters={"is_active": true})

// Terms with early payment discounts: list active terms, then read each
// term's discount fields (discount is not a query filter)
query("payment_term", filters={"is_active": true})

// Find specific term
query("payment_term", query="NET_30")

// Immediate payment terms: sort by days_until_due (not a filter)
query("payment_term", filters={"is_active": true}, sort_by="days_until_due", sort_order="asc")
```

**Tip**: Always query payment terms dynamically rather than hardcoding values, as organizations may have custom terms beyond the standard 17 pre-seeded terms.

---

## Integration Points

### Customers

Payment terms are assigned to customers as default terms for invoices:

```javascript
// Create customer with payment terms
submit("customer", "create", {
    customer_name: "ACME Corp",
    payment_terms_code: "NET_30"  // Default payment terms for this customer
})
```

**Result**: All AR invoices for ACME Corp default to NET_30 terms

### Vendors

Payment terms are assigned to vendors for AP invoice management:

```javascript
// Create vendor with payment terms
submit("vendor", "create", {
    vendor_name: "Office Supplies Inc",
    payment_terms_code: "NET_60"  // We pay vendor in 60 days
})
```

**Result**: All AP invoices from Office Supplies Inc default to NET_60 terms

### AR Invoices

Payment terms calculate due dates and early payment discounts:

```javascript
// AR Invoice with payment terms
{
  "customer_id": 1001,
  "invoice_date": "2025-01-15",
  "payment_terms_code": "NET_30_2_10",
  "total_amount": 10000.00,
  // System auto-calculates:
  // - due_date: 2025-02-14 (30 days from invoice date)
  // - discount_date: 2025-01-25 (10 days from invoice date)
  // - discount_amount: 200.00 (2% of 10000)
}
```

### AP Invoices

Payment terms manage when vendor payments are due:

```javascript
// AP Invoice with payment terms
{
  "vendor_id": 2001,
  "invoice_date": "2025-01-15",
  "payment_terms_code": "NET_60_2_10",
  "total_amount": 50000.00,
  // System auto-calculates:
  // - due_date: 2025-03-16 (60 days from invoice date)
  // - discount_date: 2025-01-25 (10 days from invoice date)
  // - discount_amount: 1000.00 (2% of 50000)
}
```

---

## Validation Rules

### Code Validation

- Required field
- 1-20 characters maximum
- Automatically converted to uppercase
- Must be unique across organization
- No spaces allowed (use underscores instead)

### Description Validation

- Required field
- 1-255 characters maximum
- Should be clear and descriptive

### Days Until Due Validation

- Required field
- Must be >= 0 (0 = immediate payment)
- Typically 0, 7, 10, 15, 30, 45, 60, 90, 120, 180 days

### Discount Days Validation

- Optional field
- Must be >= 0
- Must be < days_until_due (discount period must end before due date)
- Default: 0 (no discount)

### Discount Percent Validation

- Optional field
- Range: 0.00 to 100.00
- Typically 1.0%, 2.0%, 3.0%, 5.0%
- Default: 0.00 (no discount)

---

## Best Practices

### Code Naming

**Good Examples:**
- `NET_30` - Clear and standard
- `NET_30_2_10` - Describes both net period and discount
- `DUE_ON_RECEIPT` - Descriptive of immediate payment
- `NET_30_WHOLESALE` - Indicates customer segment

**Bad Examples:**
- `n30` - Not descriptive, lowercase
- `TERMS_1` - Generic, not self-documenting
- `NET 30` - Contains space (invalid)

### Description Best Practices

**Good Examples:**
- "Payment due in 30 days"
- "Net 30, 2% discount if paid within 10 days"
- "Payment due immediately upon receipt"
- "Net 60 days (approved wholesale customers only)"

**Bad Examples:**
- "NET_30" - Just repeating the code
- "Standard terms" - Not specific
- "Terms" - Too vague

### Early Payment Discounts

1. **Use standard discount percentages**: 1%, 2%, 3%, 5% are most common
2. **Balance discount period and due date**: Typical ratio is 10 days discount / 30 days net
3. **Consider your cash flow needs**: Higher discounts = faster payment but lower revenue
4. **Analyze the economics**: 2/10 Net 30 ≈ 36.7% APR equivalent - often worth taking

### Deactivation Strategy

1. **Check usage before deactivating**: Find all customers/vendors using the term
2. **Migrate users to new terms**: Update customer/vendor records before deactivating
3. **Never hard delete**: Always use soft delete (deactivation) to preserve audit trail
4. **Document the reason**: Update description before deactivating if needed

### Metadata Usage

The payment_terms table doesn't have a metadata field, but you can use the description field to add context:

```javascript
submit("payment_term", "create", {
    code: "NET_45_SPECIAL",
    description: "Net 45 days (Q1 2025 promotion - ends March 31)",
    days_until_due: 45
})
```

---

## Key Takeaways

1. **Universal Reference Data**: Payment terms are organization-wide, not entity-specific (no MSEO pattern)
2. **Pre-Seeded Terms**: System comes with 17 standard payment terms covering most business needs
3. **All Writes Use Workflows**: `payment_term.create`, `payment_term.update`, `payment_term.deactivate`
4. **Early Payment Discounts**: Powerful tool for improving cash flow (e.g., NET_30_2_10)
5. **Soft Delete Only**: Deactivated terms preserved for historical records and audit trail
6. **Code Normalization**: Automatically converts to uppercase for consistency
7. **Dynamic Due Dates**: System automatically calculates due dates based on invoice date + days_until_due
8. **Discount Calculation**: System automatically calculates discount amounts and discount expiration dates

**Financial Data is Immutable**: Deactivation hides payment terms from operations but preserves for audit and historical reporting.

---

**End of Payment Terms Management Guide**


The create/deactivate gateway validates the **normalized** code at 1–20
characters, matching storage. Longer codes (including uppercase expansion)
are refused before execution; dry-run/schema validation uses the same limit.
