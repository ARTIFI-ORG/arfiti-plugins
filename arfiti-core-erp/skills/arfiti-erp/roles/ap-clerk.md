

## Card purchase policy

Use the backend purchase workspace and shared matching decision; do not implement a competing card matcher in conversation. Preserve provider rows and show net purchase spend. Reference conflicts and competing candidates require review. A paid/settled item can still lack documentation; attach missing source evidence to the existing bill. Evidence review, waiver and grouping use `card_purchase.manage` with current version, evidence fingerprint and reason. Never infer write-off authority from matching tolerance.

Receipt follow-up belongs to the purchase obligation, with one owner and deduplicated reminder stages. Automation and delivery are report-only until the entity rollout settings are explicitly enabled. Statement coverage and opening/movement/closing balance controls must pass independently of agent match counts. August deletion/replay requires its own reviewed manifest and explicit authorization through transaction.delete; implementation permission does not authorize it.

Legacy payment-pass descriptions below apply to non-card AP/AR behavior. Card rows use the shared purchase policy and cannot use nearest-date refund pairing, fuzzy amount identity or adjusting-journal workarounds.

# Accounts Payable Clerk

## Role Overview

The AP Clerk is responsible for processing vendor invoices (bills), managing vendor records, and preparing payment batches. This role requires understanding of capitalization thresholds, VAT/tax handling, and proper GL account coding.

## Key Responsibilities

### Daily Tasks
- Process incoming vendor invoices (bills)
- Match invoices to purchase orders
- Code invoices to correct GL accounts (expense vs. asset)
- Apply correct tax codes based on vendor and transaction type
- Verify invoice accuracy and approvals
- Respond to vendor inquiries

### Weekly Tasks
- Prepare payment batch proposals
- Process approved payment runs
- Reconcile vendor statements
- Follow up on aged invoices
- Update vendor records

### Monthly Tasks
- Assist with AP aging review
- Prepare accrual entries for unbilled items
- Support period-end close activities
- Compile vendor information-return data where the entity's jurisdiction requires it (ask the tax role)
- Assist Tax Manager with VAT-related queries

---

## Bill Processing Rules

When processing incoming bills (AP invoices), evaluate each line item to determine proper accounting treatment.

### Step 1: Retrieve Vendor Master Data

**Before processing a bill, always fetch vendor details to use defaults:**

```javascript
get_entity(entity_type="vendor", id=<vendor_id>)
```

**Key fields to extract from vendor master data:**

| Field | Purpose | Usage |
|-------|---------|-------|
| `default_expense_account_number` | Default GL account for expenses | Use when bill line doesn't specify account |
| `tax_code` | Vendor's default tax code | A hint only: resolve each line's tax from the document; never apply it blind |
| `payment_term_code` | Payment terms | Calculate due date |
| `currency` | Default transaction currency | Set bill currency |
| `dimensions` | Pre-assigned dimensions (cost_center, location, etc.) | Apply to all bill lines |

### Step 2: Apply Vendor Defaults

When creating a bill, use vendor defaults as follows:

1. **Default Expense Account** - If a bill line doesn't specify an account AND it is below the organisation's capitalisation threshold, use `default_expense_account_number`
2. **Tax Code** - A vendor `tax_code` is a hint. Decide each line's tax from the document (rate shown, reverse-charge wording, supplier country); the bill pipeline never applies the vendor default blind
3. **Dimensions** - Copy vendor dimensions to the transaction (cost_center, location, department, project)
4. **Currency** - Use vendor's default currency unless invoice specifies otherwise
5. **Payment Terms** - Use `payment_term_code` to calculate due date from invoice date

**Example: Using Vendor Defaults**

```javascript
// Step 1: Get vendor details
const vendor = get_entity(entity_type="vendor", id=45);
// Returns: {
//   default_expense_account_number: "<expense account>",
//   tax_code: "<standard-rate code>",
//   payment_term_code: "NET30",
//   currency: "EUR",
//   dimensions: [
//     { dimension_type: "cost_center", dimension_value: "CC-1000" },
//     { dimension_type: "location", dimension_value: "HQ" }
//   ]
// }

// Step 2: Create bill using vendor defaults
submit(
  object_type="transaction",
  operation="post",
  data=JSON.stringify({
    transaction_type_code: "AP_INVOICE",
    legal_entity_id: 1,
    vendor_id: 45,
    currency_code: vendor.currency,          // From vendor
    invoice_date: "2026-01-27",
    due_date: "2026-02-26",                   // Calculated from payment_term_code
    dimensions: {
      cost_center: "CC-1000",                 // From vendor dimensions
      location: "HQ"                          // From vendor dimensions
    },
    lines: [
      {
        description: "Consulting services",
        quantity: 1,
        unit_price: 500.00,
        account_number: vendor.default_expense_account_number,
        tax_code: vendor.tax_code             // Hint only: confirmed against the invoice line
        // Note: 'amount' is auto-calculated as quantity × unit_price
      }
    ]
  })
)
```

**Note:** See [Transaction Processing](../resources/transaction-processing.md) for auto-calculated fields (amount, fiscal_period_id) and dimension format requirements.

### Step 3: Evaluate Capitalization Threshold

**Key Rule:** An item at or above the organisation's capitalisation threshold, with a useful life
beyond one year, is capitalised as a fixed asset. The threshold is the organisation's accounting
policy, not a product constant: read it from the organisation's accounting policy or
configuration (the bill processor and asset creator agents carry it as
`capitalization_threshold`), and ask the user when none is set. Never assume a figure.

| Amount | Useful Life | Account | Example |
|--------|-------------|---------|---------|
| At or above the threshold | > 1 year | A fixed-asset account of the entity | Server, vehicle, furniture |
| Below the threshold | Any | An expense account, or the vendor default | Office supplies, small tools |
| At or above the threshold | <= 1 year | An expense account (or prepaid, see Subscription Bills) | Annual software licence |

**Account Selection Logic:**

1. **Check total line amount** - Is it at or above the organisation's capitalisation threshold?
2. **Assess asset nature** - Will this item provide benefit for more than 1 year?
3. **Select account** - Find the entity's accounts by classification, never by number range:
   - Fixed asset → `query("account", filters={"legal_entity_id": <entity>, "account_type": "asset", "account_subtype": "fixed_asset_cost"})`
   - Expense → `vendor.default_expense_account_number`, or `query("account", filters={"legal_entity_id": <entity>, "account_type": "expense"})`
4. **Apply tax code** - Per line from the document; `vendor.tax_code` only as a hint (see Tax Integration section)

### Examples

| Description | Useful Life | Account (by classification) | Reasoning |
|-------------|-------------|-----------------------------|-----------|
| Server, above the threshold | 3+ years | `fixed_asset_cost` account | Capitalisable asset |
| Office chair, below the threshold | 5+ years | Expense account (vendor default) | Below threshold |
| Annual SaaS licence | 1 year | `prepaid_expense` account, amortised | No benefit beyond the year |
| Company vehicle, above the threshold | 5+ years | `fixed_asset_cost` account | Capitalisable asset |

---

## Tax Integration

AP Clerks apply the tax code that matches the entity's jurisdiction and the purchase. Tax codes,
rates and their reporting lines are configured per organisation and entity, so never assume a
code name or a rate: look them up.

### Finding the right tax code

1. **Start from the document.** Decide each line's tax from what the invoice shows (rate,
   reverse-charge wording, supplier country). `vendor.tax_code` is a hint, never applied blind.
2. **Look up the entity's tax codes** to find the code that matches each line:

```javascript
query(entity_type="tax_code", filters={"is_active": true})
```

   Read each code's name, rate and description, and match it to what the invoice shows (the
   rate printed on the invoice, whether the vendor is domestic or foreign, goods or services).
3. **Check input-tax recovery.** Whether the tax on a purchase is recoverable is set by the
   tax code configuration and the organisation's tax role, not by the clerk.

### Processing Bills with Tax

When processing a bill:

1. **Identify vendor origin** - Domestic, cross-border within a trade area, or foreign
2. **Determine transaction type** - Goods, services, or a special category
3. **Select tax code** - From the vendor default or the entity's tax codes (above)
4. **Escalate anything uncertain** - See "Tax Questions and Escalation" below

**Example Bill Processing:**

```javascript
// Tax codes come from query(entity_type="tax_code"); the values below are placeholders.
submit(
  object_type="transaction",
  operation="post",
  data=JSON.stringify({
    transaction_type_code: "AP_INVOICE",
    legal_entity_id: 1,   // Example Trading Ltd (your entity id)
    vendor_id: 45,        // Domestic vendor
    invoice_date: "2026-01-27",
    due_date: "2026-02-26",
    lines: [
      {
        description: "Office Computer - Dell XPS",
        quantity: 1,
        unit_price: 1500.00,
        account_number: "<fixed_asset_cost account>",  // At or above the capitalisation threshold
        tax_code: "<standard-rate code>"
      },
      {
        description: "Office supplies",
        quantity: 1,
        unit_price: 85.00,
        account_number: "<expense account>",  // Below the threshold
        tax_code: "<standard-rate code>"
      }
    ]
  })
)
```

### Tax Questions and Escalation

Tax treatment questions go to the organisation's tax role (the Tax Manager role (the organisation's tax role)
in an organisation's generated skill package, which carries its country's rules):
- Uncertain tax code selection
- Reverse charge transactions
- Cross-border goods and services
- Exemption questions
- Tax return and reporting queries

---

## Document Type Detection

When a user uploads a document (image or PDF), you must determine whether it is a **bill/invoice** (from a vendor) or a **receipt** (employee expense). These require different processing flows.

### RECEIPT (Employee Expense)

**Indicators:**
- Small amounts
- Retail merchants (restaurants, shops, transport, hotels)
- Employee is the purchaser (their name may be on receipt)
- No formal invoice number or structured layout
- Often paid by corporate card
- Point-of-sale (POS) format - thermal paper, short format
- No payment terms (already paid)

**Typical Merchants:**
- Restaurants and cafes
- Grocery stores
- Gas stations
- Taxis and rideshare (Bolt, Uber)
- Hotels (for small employee travel)
- Office supply retail stores
- Coffee shops

**Action for Receipts:**

1. **If corporate card transaction exists** - Link receipt to the card transaction:
```javascript
// Check if there's a matching card transaction (compare amounts in the results;
// card_transaction has no amount filter)
query(entity_type="card_transaction",
      filters={"legal_entity_id": <entity_id>},
      date_filters={"transaction_date": {"from": "<receipt_date - 3 days>",
                                         "to": "<receipt_date + 3 days>"}})

// If a match is found, file the receipt on that charge, then submit it
// (see receipts-management.md for the upload step and the full lifecycle)
submit(object_type="card_transaction", operation="attach_receipt", data=JSON.stringify({
    card_transaction_id: <matched_id>,
    legal_entity_id: <entity_id>,
    file_name: "<file name>",
    content_type: "<MIME type>",
    source_url: "<stored file reference>",
    business_purpose: "<user_description>"
}))
submit(object_type="card_transaction", operation="submit_receipt", data=JSON.stringify({
    card_transaction_id: <matched_id>,
    legal_entity_id: <entity_id>
}))
```

2. **If no card transaction (petty cash/personal expense)** - Create an expense report for the employee (see [Expense Management](../resources/expense-management.md); check the fields with `get_submissions(action="schema", object_type="expense_report", operation="create")` first):
```javascript
submit(object_type="expense_report", operation="create", data=JSON.stringify({
    legal_entity_id: <entity_id>,
    employee_id: <employee_id>,
    title: "Expense reimbursement: <merchant>",
    lines: [
      {
        line_type: "reimbursement",
        spend_date: "<receipt_date>",
        amount: <receipt_amount>,
        merchant_name: "<merchant>",
        description: "<item_description>"
      }
    ]
}))
```

### BILL/INVOICE (Vendor Bill)

**Indicators:**
- Business-to-business transaction
- Has formal invoice number (e.g., "INV-2026-0001")
- Has payment terms (NET30, NET60, due date)
- Vendor details present (VAT/tax number, full address)
- Larger amounts
- Structured format with line items
- May reference PO number or contract

**Typical Sources:**
- Software subscriptions (Microsoft, AWS, Adobe)
- Professional services (consulting, legal, accounting)
- Equipment purchases
- Utility providers
- Telecommunications
- Wholesale suppliers
- Contractors and freelancers

**Action for Bills:**

Process as AP_INVOICE using standard bill processing workflow (see "Bill Processing Rules" section above):

```javascript
submit(
  object_type="transaction",
  operation="post",
  data=JSON.stringify({
    transaction_type_code: "AP_INVOICE",
    legal_entity_id: <entity_id>,
    vendor_id: <vendor_id>,
    invoice_number: "<from_document>",
    invoice_date: "<from_document>",
    due_date: "<calculated_from_terms>",
    lines: [/* line items from invoice */]
  })
)
```

### Decision Tree

```
Document Uploaded
    │
    ├── Has invoice number + vendor VAT number?
    │   └── YES → BILL → Create AP_INVOICE
    │
    ├── Has payment terms (NET30, due date)?
    │   └── YES → BILL → Create AP_INVOICE
    │
    ├── Large amount + formal structure (invoice layout, vendor details)?
    │   └── YES → BILL → Create AP_INVOICE
    │
    ├── Retail merchant (restaurant, shop, taxi)?
    │   └── YES → RECEIPT → Link to card transaction or expense claim
    │
    ├── POS/thermal paper format?
    │   └── YES → RECEIPT → Link to card transaction or expense claim
    │
    └── UNCLEAR → Ask user:
        "Is this a vendor invoice (bill) for the company to pay,
         or a receipt for an expense you already paid?"
```

### Subscription Bills (Special Handling)

12-month subscriptions require special treatment - they should be **prepaid expenses**, not direct expenses:

**Detection:**
- Annual/yearly subscription language
- Software/SaaS vendors
- Billing period spans 12 months

**Example:**
```javascript
// Adobe Creative Cloud Annual - 1,200.00
// Don't expense immediately - create prepaid expense
submit(
  object_type="transaction",
  operation="post",
  data=JSON.stringify({
    transaction_type_code: "AP_INVOICE",
    legal_entity_id: 1,
    vendor_id: <adobe_vendor_id>,
    lines: [
      {
        description: "Adobe CC Annual Subscription (12 months)",
        amount: 1200.00,
        account_number: "<prepaid_expense account>",  // account_subtype prepaid_expense, NOT an expense account
        tax_code: "<standard-rate code>",
        amortization: {
          periods: 12,
          start_date: "2026-02-01"
        }
      }
    ]
  })
)
// This creates monthly amortization entries:
// DR: Software expense account  100.00
// CR: Prepaid expense account   100.00
```

---

## System Permissions

### Workflows Accessible

| Workflow | Permission Level |
|----------|-----------------|
| `vendor.create` | Submit (typically Yellow lane) |
| `vendor.update` | Submit (typically Green lane for contact info) |
| `transaction.post` (AP_INVOICE) | Submit and Execute |
| `transaction.post` (AP_CREDIT_MEMO) | Submit and Execute |
| `payment_batch.create` | Submit (approval as configured) |

Lanes are assigned by your organisation's workflow rules; the submit() result is authoritative.

### Read Access
- Vendor master data
- Invoice history
- Payment history
- Chart of accounts
- Purchase orders
- Tax codes and rates

### No Access To
- Customer data
- Payroll information
- Financial reports (except AP aging)
- Tax code configuration (read-only)

---

## Workflow Guidelines

### Existing Bill review tasks

If a bill already has a review task, continue that task rather than using the
manual `transaction.post` examples below. Read its latest question, candidate
and outcome; submit the user's instruction with the offered response action.
A comment or read-only question is not permission to change the bill.

Where agent-owned resolution is enabled, missing master data/configuration is
delegated and the Bill agent resumes after verification. Save-only instructions
do not authorize posting or master-data creation. A request to remember one
vendor attribute does not authorize saving other defaults.

Check the recorded transaction and follow-up outcomes before reporting success.
A posted bill with unfinished PO matching, asset creation or vendor rules is
partial; do not create a second invoice to finish those steps. The new loop is
gated and off by default. See [Agent requests](../resources/agent-management.md#agent-requests).

### Creating Vendor Invoices (Bills)

1. **Verify vendor exists** in system
2. **Fetch vendor master data** - Get defaults (expense account, tax code, dimensions, currency)
3. **Match to PO** if applicable
4. **Evaluate each line** against capitalization threshold
5. **Code to correct accounts** - Use vendor default for expenses, or override for assets
6. **Apply dimensions** - Copy vendor dimensions to transaction (cost_center, location, etc.)
7. **Apply correct tax code** - Use vendor default or override per line
8. **Attach supporting documentation** (PDF/image of invoice)
9. **Submit for approval** if over threshold

### Bulk Bill Processing

For processing 5+ bills at once (CSV upload, batch entry, or data migration), use the **bulk import workflow** instead of individual posting:

```javascript
submit(
  object_type="transaction",
  operation="import",
  data=JSON.stringify({
    legal_entity_id: 1,
    records: [ /* array of AP_INVOICE records */ ],
    options: { on_duplicate: "skip" }
  })
)
```

**See**: [Bulk Transaction Processing](../resources/bulk-transaction-processing.md) for complete workflow, entity resolution, and CSV parsing guidance.

**For system migrations** (importing from QuickBooks, Xero, etc.), defer to the [Data Migration Specialist](data-migration-specialist.md) role which handles the full migration sequence: master data first, then transactions with external ID mapping.

### Processing Bill Credits

When processing vendor credit memos:

1. Reference the original invoice
2. Use `AP_CREDIT_MEMO` with positive lines, `original_transaction_id`, and the supplier credit reference; do not post a negative invoice
3. Apply the same tax code as the original invoice
4. Post to the same GL accounts as the original

### Preparing Payments

1. Review aged payables
2. Select invoices for payment
3. Verify payment terms and discounts
4. Submit payment batch for approval
5. Process approved batch

---

## Key Metrics

- Invoice processing time
- Invoice accuracy rate
- Early payment discounts captured
- On-time payment percentage
- Tax code accuracy rate

## Escalation Path

1. **Questions about coding**: Senior Accountant
2. **Tax code questions**: Tax Manager (the organisation's tax role)
3. **Vendor disputes**: AP Supervisor
4. **Payment issues**: Accounting Manager
5. **Policy questions**: Controller

---

**Version**: 1.6
**Last Updated**: 2026-10-31
**Related Resources**:
- [Vendor Management](../resources/vendor-management.md) - Vendor defaults, dimensions, bank accounts
- [Tax Management](../resources/tax-management.md) - Tax code configuration
- Tax Manager Role (the organisation's tax role) - The organisation's country tax rules and escalation
- [Transaction Processing](../resources/transaction-processing.md) - AP/AR invoice posting
- [Bulk Transaction Processing](../resources/bulk-transaction-processing.md) - Bulk bill import from CSV, batch processing, data migration
- [Receipts Management](../resources/receipts-management.md) - Corporate card receipts, expense claims, receipt collection
