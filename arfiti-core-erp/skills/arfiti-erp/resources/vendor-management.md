# Vendor Management Guide

> **MSEO release contract:** Vendor business identity is the master ID. Supported dimension code commands retain entity scope; numeric legacy commands use the endpoint’s declared effective namespace. Explicit master dimension fields avoid numeric ambiguity. See the dimensions-management resource for assignment, approval and compatibility rules.

This guide explains how to manage vendors in the AI-Native ERP system.

---

## Overview

Vendors are the companies and individuals you pay for goods and services. The workflow system ensures proper authorization, audit trails, and risk-based approvals for all vendor operations.

**What you can do:**
- Create new vendors with bank accounts, addresses, currencies, and dimensions
- Update vendor information (contact details, payment terms, bank accounts)
- Query vendor data (single vendor, search/filter)
- Deactivate vendors (soft delete) or remove test data (hard delete)
- Bulk import vendors from CSV/API sources

**Available Workflows:**

| Workflow | Purpose | When to Use |
|----------|---------|-------------|
| `vendor.create` (fields: `get_submissions(action="schema", object_type, operation)`) | Create new vendor | Onboarding a new supplier |
| `vendor.update` (fields: `get_submissions(action="schema", object_type, operation)`) | Update vendor data | Changing payment terms, adding bank account |
| [`vendor.merge`](../definitions/vendor.merge.md) | Merge duplicate vendors | Two records exist for the same payee |
| `vendor.delete` (fields: `get_submissions(action="schema", object_type, operation)`) | Deactivate vendor | Vendor no longer used |

**Available Query Tools:**

| Tool | Purpose |
|------|---------|
| `get_entity("vendor", id=X)` | Get single vendor with all related data (addresses, bank accounts, currencies, dimensions) |
| `query("vendor", query, filters)` | Free-text search across vendor_name, email, tax_id, phone, website, notes |
| `query("vendor", filters)` | List/filter vendors with pagination and sorting |
| `query("vendor", filters, limit=1)` | Count vendors matching criteria (use `total_count` from response) |
| `get_submissions(action='schema', object_type="vendor", operation="create")` | Get field schema before submitting |
| `get_submissions(action='schema', object_type="vendor", operation="update")` | Get update field schema with examples |
| `query(entity_type, filters={...})` ×N | Fetch payment terms, tax codes, accounts (parallel calls) before creating vendors |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

**Key Notes:**
- **Display fields** (returned by `query`/`query`): `master_vendor_id`, `global_vendor_id`, `vendor_name`, `email`, `phone`, `payment_terms_code`, `currency`, `is_active`
- **Searchable fields**: `vendor_name`, `global_vendor_id`, `email`, `tax_id`, `phone`, `website`, `notes`
- **Filter fields**: `legal_entity_id`, `is_active`, `vendor_type`, `payment_terms_code`, `is_1099_vendor`, `payment_hold`, `currency`
- **Sort fields**: `vendor_name` (default), `global_vendor_id`, `created_at`, `updated_at`
- **Related data** (`get_entity` returns): addresses, bank_accounts, currencies, dimensions, linked_customer

---

## Complete Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

### Master Vendor Fields (master_vendors table)

**Required Fields:**
- `vendor_name` (string, 1-255 chars) - Vendor business or person name

> **Note:** Required fields are configurable per organization via workflow definitions. The fields listed here are the minimal defaults. Your organization may require additional fields such as `email`, `tax_id`, `payment_terms_code`, `credit_limit`, `website`, `tax_code`, `estimated_annual_spend`, `country`, `default_expense_account_id`, `vendor_type`, and others. Always call `get_submissions(action='schema', object_type="vendor", operation="create")` to discover the exact required fields for your setup.

**Recommended Fields:**
- `email` (string, valid email) - Primary contact email
- `payment_terms_code` (string, default: `net_30`) - Default payment terms (e.g., `NET_30` or `net_30` -- case-insensitive, underscore optional)
- `tax_id` (string, max 50) - Tax identification number (EIN, VAT, etc.)

**Business Information:**
- `vendor_type` (enum) - Vendor classification
  - Options: `supplier`, `contractor`, `service_provider`, `utility`, `government`, `employee`, `other`
- `phone` (string, max 50) - Primary phone number
- `website` (string, max 255) - Vendor website URL
- `billing_email` (string, max 255) - Separate email for invoices (if different from primary)
- `tax_code` (string, max 50) - Default VAT treatment for this vendor's purchases: the name of one of this organisation's tax codes. An unknown code is left unset on create (listed in `metadata.placeholder_fields`) and refused on update. It is a hint for bill lines, never applied blind.
- `notes` (text) - Internal notes about this vendor

**Payment & Credit:**
- `payment_method` (enum) - Preferred payment method
  - Options: `ach`, `wire`, `check`, `international`
- `currency` (string, 3 chars) - Default currency code (USD, EUR, etc.)
- `credit_limit` (decimal 15,2) - Maximum unpaid balance allowed
- `payment_hold` (boolean, default: false) - Temporarily prevent payments
- `remittance_reference` (string, max 140) - Payment reference the institution requires on every payment (e.g. the tax office's personal reference number). Payment batches (including payroll-generated ones) use it as the default `payment_reference` on this vendor's lines instead of a synthetic reference.

**Accounting Defaults:**
- `posting_profile_id` (bigint, FK) - AP posting profile
- `default_expense_account_id` (bigint, FK) - Default expense GL account

**Contractor information reporting (where the jurisdiction requires it, e.g. US 1099 reporting):**
- `is_1099_vendor` (boolean, default: false) - Subject to US 1099 reporting; leave false where no such regime applies

**System & Audit:**
- `global_vendor_id` (string, auto-generated) - Organization-wide unique ID (e.g., VEND-000123)
- `is_active` (boolean, default: true) - Soft delete flag
- `metadata` (jsonb) - Custom fields (see [Metadata Best Practices](#metadata-best-practices))
- `created_at`, `updated_at`, `created_by`, `updated_by` - Audit fields

**Scope & Visibility (unified MSEO contract):**
`vendor.create` is `SCOPE_MODE='fanout'`. The combination of `is_global`, `legal_entity_id`, and `legal_entity_ids` resolves to a list of target entities — the executor writes a master row plus one `vendors` row per target entity.

- `is_global` (boolean, default: `true`) — when `true`, fans out to EVERY active legal_entity (one `vendors` row each, dependents written per entity). When `false`, entity targets come from the IDs.
- `legal_entity_id` (integer, optional) — single-entity attach. Implies `is_global=false`. Result: master + ONE `vendors` row + dependents attached to that row.
- `legal_entity_ids` (integer[], optional) — multi-entity attach.
- **No flag, no IDs** → defaults to `is_global=true` → fanout (today's behaviour preserved).
- **`is_global=false` + no IDs** → master only (template); `vendor_currencies`, `vendor_dimensions`, `bank_accounts`, `addresses` REJECTED loudly. (Pre-Batch C this was the implicit fanout fallback — now requires an explicit choice.)

Per-entity dependent payloads (`vendor_currencies`, `vendor_dimensions`, `bank_accounts`, `addresses`) are written for every target entity row. See GUIDE_MSEO_PATTERN.md for the full contract.

### Entity Override Fields (vendors table)

All master fields can be overridden per entity with `_override` suffix:
- `vendor_name_override`
- `email_override`
- `phone_override`
- `payment_terms_code_override`
- `tax_id_override`
- `tax_code_override`
- `billing_email_override`
- `posting_profile_id_override`
- `is_1099_vendor_override`
- `is_active_override`
- `currency_override`
- `payment_method_override`
- `metadata_override`

**Entity-Specific Fields:**
- `vendor_number` (string, auto-generated) - Entity-specific vendor number
- `entity_vendor_code` (string) - Custom entity code if needed
- `external_id` (string, max 100) - External system identifier

### Vendor Addresses (vendor_addresses table)

**Required:**
- `address_line_1` (string, max 255) - Street address
- `country` (string, max 100) - Country name
- `address_type` (enum) - Address classification
  - Options: `primary`, `billing`, `shipping`, `remit_to`, `physical`, `mailing`, `other`

**Optional:**
- `address_line_2` (string, max 255) - Apt/Suite/Floor
- `city` (string, max 100) - City name
- `state_province` (string, max 100) - State/province/region
- `postal_code` (string, max 50) - ZIP/postal code
- `notes` (text) - Address-specific notes

**Flags:**
- `is_primary` (boolean, default: false) - Primary address (only one per vendor/entity)
- `is_billing` (boolean, default: false) - Use for billing communications
- `is_shipping` (boolean, default: false) - Use for receiving shipments
- `is_remit_to` (boolean, default: false) - Use for payment remittance
- `is_active` (boolean, default: true) - Active address

**Tip:** Vendors typically use `remit_to` address for payment checks/wires. Use both `address_type` and boolean flags for flexibility.

### Vendor Bank Accounts (vendor_bank_accounts table)

Secure storage for vendor payment account details.

**Required:**
- `payment_method` (enum) - Type of payment
  - Options: `ach`, `wire_domestic`, `wire_international`, `sepa`, `swift`, `check`, `card`, `crypto`, `paypal`, `venmo`
- `currency_code` (string, 3 chars, default: USD) - Account currency
- `account_holder_name` (string, max 255) - Legal name on account

**US Bank Accounts (ACH/Wire Domestic):**
- `routing_number` (string, max 100) - 9-digit routing number
- `account_number` (string, max 100) - Account number
- `account_type` (enum) - Account classification
  - Options: `checking`, `savings`, `corporate`, `money_market`, `other`

**International Bank Accounts:**
- `iban` (string, max 50) - International Bank Account Number
- `swift_code` (string, max 20) - SWIFT/BIC code
- `bic_code` (string, max 20) - Bank Identifier Code
- `sort_code` (string, max 20) - UK sort code
- `bsb_number` (string, max 20) - Australian BSB number

**Intermediary Bank (for international wires):**
- `intermediary_bank_name` (string, max 255)
- `intermediary_swift_code` (string, max 20)
- `intermediary_account_number` (string, max 100)

**Account Holder Details:**
- `account_holder_address` (text) - Full address of account holder
- `account_holder_country` (string, 2 chars) - ISO country code

**Bank Information:**
- `bank_name` (string, max 255) - Name of financial institution
- `bank_country` (string, 2 chars) - ISO country code
- `account_nickname` (string, max 100) - Friendly name for identification

**Security & Verification:**
- `verification_status` (enum, default: unverified) - Account verification state
  - Options: `unverified`, `pending`, `verified`, `failed`, `expired`
- `verification_method` (string, max 50) - How account was verified
- `verified_at` (timestamp) - When verification completed
- `verified_by` (integer, FK) - User who verified

**Payment Limits:**
- `daily_limit` (decimal 15,2) - Maximum daily payment amount
- `monthly_limit` (decimal 15,2) - Maximum monthly payment amount
- `per_transaction_limit` (decimal 15,2) - Maximum single payment amount
- `requires_dual_approval` (boolean, default: false) - Needs two approvers

**System:**
- `usage_type` (enum) - Purpose of account
  - Options: `ap_invoice`, `expense_reimbursement`, `payroll`, `other`
- `is_active` (boolean, default: true) - Active for payments
- `is_default` (boolean, default: false) - Default account for this payment method/currency
- `connector_id` (uuid) - Banking connector ID if synced
- `external_account_id` (string, max 100) - External system identifier
- `metadata` (jsonb) - Additional account data
- `deleted_at`, `deleted_by` - Soft delete tracking

**Security:** Account numbers and routing numbers are encrypted at rest. Only authorized AP/Treasury users can view full account details.

### Vendor Currencies (vendor_currencies table)

Multi-currency payment support for international vendors.

**Required:**
- `currency` (string, 3 chars) - Currency code (USD, EUR, GBP, etc.)
- `effective_from` (date, default: today) - Start date

**Currency Configuration:**
- `is_primary` (boolean, default: false) - Primary currency for this vendor
- `rate_source` (enum) - How to determine exchange rate
  - Options: `SPOT`, `CONTRACT`, `FIXED`
- `fixed_rate` (decimal 15,6) - Fixed exchange rate (required if CONTRACT or FIXED)
- `rate_tolerance_percent` (decimal 5,2) - Acceptable variance from fixed rate

**Optional:**
- `effective_to` (date) - End date (null = no expiration)
- `payment_terms_override` (string, max 20) - Currency-specific payment terms

**Tips:**
- Use `SPOT` for daily market rates (most common)
- Use `CONTRACT` for negotiated fixed rate (e.g., 1 EUR = 1.10 USD)
- Use `FIXED` with tolerance for rates that can fluctuate within limits
- Only one primary currency per vendor per entity

### Vendor Dimensions (vendor_dimensions table)

Tag vendors with analytical dimensions for reporting and cost allocation.

**Required Fields:**
- `legal_entity_id` (integer, FK) - Which entity this dimension applies to
- `dimension_type` (string) - Dimension type name (e.g., "department", "location")
- `dimension_value` (string) - Dimension value code (e.g., "SALES", "NYC", "REMOTE")

**Alternative Lookup (using IDs - not recommended):**
- `dimension_type_id` (integer, FK) - Which dimension type (use name instead)
- `dimension_value_id` (bigint, FK) - Specific value (use code instead)

**Important:** Vendor dimensions are stored per legal entity. When adding dimensions, you must specify which `legal_entity_id` the dimension applies to. The system will automatically create the vendor-entity linkage if it doesn't exist.

**Dimensions are automatically applied to:**
- AP invoices created for this vendor
- Expense allocations
- Reports filtered by dimension

**Getting Reference Data:**
- Dimension Types: Use `query("dimension_type")` to see available dimension types and which entities they apply to
- Dimension Values: Use `query("dimension_value")` to get values for a specific type

---

## Custom Fields

Organisations define their own vendor fields (contract reference, payment
approval limit, preferred contact method…). Before putting a business fact
into `metadata`, check whether a custom field exists for it:

- `get_submissions(action="schema", object_type="vendor", operation="create")` →
  `custom_fields` lists each active field: key, label, description, type,
  limits, choice options and whether it is required.
- Set values with `"custom_fields": {"key": value}`; on update, keys you leave
  out are unchanged and `"custom_fields_clear": ["key"]` empties one. Never
  send `null` as a value.
- Types: text (string), decimal (numeric string within `scale`; a JSON number
  loses digits above about 15), boolean (true/false), date (`YYYY-MM-DD`),
  choice (one option `value`).
- Find vendors with `query("vendor", filters={"custom_fields.<key>": value})`
  — also lists, `None` (no value), `{"exists": true}` and, on decimal and date
  fields, `{"gte"|"lte"|"gt"|"lt": …}`.
- A field shared with customers holds separate values on each record.
- If the organisation requires a custom field on vendor creation, every new
  vendor you propose (including from bills and bank lines) must carry it;
  ask for the value rather than inventing one.
- A field the organisation needs but has not defined is created by an admin
  with `submit("custom_field", "create", …)`; do not invent `metadata` keys.

All rules (register, types, required fields, transactions, filters, import, merge): the custom-fields resource; full contract `docs/GUIDES/GUIDE_CUSTOM_FIELDS.md`.

## Metadata Best Practices

The `metadata` JSONB field allows storing custom data without schema changes.

### When to Use Metadata

✅ **Good use cases:**
- Vendor-specific attributes that vary widely (DUNS number, minority-owned status, certifications)
- Integration IDs from external systems (NetSuite vendor ID, Coupa supplier ID)
- Temporary attributes during migration or testing
- Rarely-queried supplementary information
- Custom fields specific to your industry

❌ **Bad use cases:**
- Frequently queried fields (use real columns for performance)
- Fields requiring complex validation (use Pydantic models)
- Fields that need database constraints or indexes
- Standard accounting data (use dedicated tables)

### Metadata Structure Tips

1. **Check existing vendors first** before adding new metadata fields:
   ```
   Use get_entity("vendor", id=123) to see existing metadata structure
   ```

2. **Use consistent field names** across all vendors:
   ```json
   {
     "netsuite_vendor_id": "V-12345",
     "duns_number": "123456789",
     "minority_owned": true,
     "small_business": false,
     "certifications": ["ISO9001", "SOC2"],
     "account_manager": "John Doe"
   }
   ```

3. **Namespace integration data** to avoid conflicts:
   ```json
   {
     "integrations": {
       "netsuite": {"vendor_id": "V-12345", "last_sync": "2025-01-15T10:30:00Z"},
       "coupa": {"supplier_id": "SUP-789", "status": "approved"}
     }
   }
   ```

4. **Document your metadata schema** in your organization's wiki or knowledge base

5. **Query metadata** using PostgreSQL JSON functions:
   ```sql
   SELECT * FROM master_vendors
   WHERE metadata->>'minority_owned' = 'true'
   ```

### Updating Metadata

**Add new field:**
```json
{
  "vendor_id": 123,
  "metadata": {
    "existing_field": "value",
    "new_field": "new_value"
  }
}
```

**Remove field:**
```json
{
  "vendor_id": 123,
  "metadata": {
    "existing_field": "value"
    // Simply omit the field you want to remove
  }
}
```

**Tip:** Metadata updates are full replacements, not merges. Always include all fields you want to keep.

---

## Creating a Vendor

Use the `vendor.create` workflow to add new vendors.

**See:** vendor.create definition (fields: `get_submissions(action="schema", object_type, operation)`) for complete field details

### Basic Vendor

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="vendor", operation="create")

// Step 2: Submit with discovered fields
submit("vendor", "create", '{...}')
// Tip: Use validate_only=true to check payload before submitting
```

```json
{
  "vendor_name": "Acme Corporation",
  "tax_id": "12-3456789",
  "email": "ap@acme.com",
  "phone": "+1-555-0100",
  "payment_terms_code": "NET_30",
  "currency": "USD",
  "vendor_type": "supplier"
}
```

**Getting Reference Data:**
- Payment Terms: Use `query("payment_term")` to get valid `payment_terms_code` values

### Vendor with Bank Account

For ACH or wire payments, include bank account details:

```json
{
  "vendor_name": "Office Supplies Inc",
  "tax_id": "98-7654321",
  "email": "billing@officesupplies.com",
  "payment_terms_code": "NET_45",
  "currency": "USD",
  "vendor_bank_accounts": [
    {
      "legal_entity_id": 13,
      "account_nickname": "Primary ACH",
      "payment_method": "ach",
      "currency_code": "USD",
      "bank_name": "Chase Bank",
      "routing_number": "021000021",
      "account_number": "123456789012",
      "account_type": "checking",
      "account_holder_name": "Office Supplies Inc",
      "is_default": true
    }
  ]
}
```

**Getting Reference Data:**
- Legal Entities: Use `query("legal_entity")` to get valid `legal_entity_id` values

### Vendor with Address

Include remit-to address for check payments:

```json
{
  "vendor_name": "Consulting Services LLC",
  "tax_id": "45-6789012",
  "email": "billing@consulting.com",
  "payment_terms_code": "NET_30",
  "vendor_addresses": [
    {
      "legal_entity_id": 13,
      "address_type": "remit_to",
      "address_line_1": "123 Payment Processing Center",
      "address_line_2": "Suite 400",
      "city": "New York",
      "state_province": "NY",
      "postal_code": "10001",
      "country": "USA",
      "is_primary": true,
      "is_remit_to": true
    }
  ]
}
```

### Multi-Currency Vendor

For international vendors accepting multiple currencies:

```json
{
  "vendor_name": "Global Supplies Ltd",
  "tax_id": "GB123456789",
  "email": "accounts@globalsupplies.co.uk",
  "payment_terms_code": "NET_30",
  "currency": "GBP",
  "vendor_currencies": [
    {
      "legal_entity_id": 13,
      "currency": "GBP",
      "is_primary": true,
      "rate_source": "SPOT"
    },
    {
      "legal_entity_id": 13,
      "currency": "USD",
      "is_primary": false,
      "rate_source": "CONTRACT",
      "fixed_rate": 1.25
    }
  ]
}
```

### Vendor with Dimensions

Tag vendors with departments, cost centers, or projects:

```json
{
  "vendor_name": "Engineering Supplies Co",
  "tax_id": "45-6789012",
  "email": "sales@engsupplies.com",
  "payment_terms_code": "NET_30",
  "vendor_dimensions": [
    { "legal_entity_id": 13, "dimension_type": "department", "dimension_value": "ENG" },
    { "legal_entity_id": 13, "dimension_type": "cost_center", "dimension_value": "CC-RD" }
  ]
}
```

**Important:**
- Use dimension type **name** (e.g., "department", "location") not IDs
- Use dimension value **code** (e.g., "ENG", "CC-RD") not IDs
- Dimension type names are lowercase with underscores (e.g., "cost_center", not "Cost Center")

**Getting Reference Data:**
- Dimensions: Use `query("dimension_type")` and `query("dimension_value")` to find available dimensions and values

### Vendor subject to contractor reporting (e.g. US 1099)

Where the jurisdiction requires information reporting on contractor payments (e.g. US 1099
reporting), flag the vendor:

```json
{
  "vendor_name": "John Smith Consulting",
  "tax_id": "123-45-6789",
  "email": "john@smithconsulting.com",
  "payment_terms_code": "NET_30",
  "is_1099_vendor": true,
  "vendor_type": "contractor",
  "vendor_addresses": [
    {
      "legal_entity_id": 13,
      "address_type": "remit_to",
      "address_line_1": "456 Contractor Lane",
      "city": "Austin",
      "state_province": "TX",
      "postal_code": "78701",
      "country": "USA",
      "is_remit_to": true
    }
  ]
}
```

### Vendor with Custom Metadata

Store integration IDs and custom attributes:

```json
{
  "vendor_name": "Enterprise Supplier Corp",
  "tax_id": "12-3456789",
  "email": "ap@enterprise.com",
  "payment_terms_code": "NET_60",
  "metadata": {
    "netsuite_vendor_id": "V-12345",
    "duns_number": "123456789",
    "minority_owned": true,
    "small_business": true,
    "certifications": ["ISO9001", "SOC2"],
    "preferred_contact": "Jane Smith",
    "contract_renewal_date": "2025-12-31"
  }
}
```

---

## Updating a Vendor

Use the `vendor.update` workflow to modify existing vendors.

**See:** vendor.update definition (fields: `get_submissions(action="schema", object_type, operation)`) for complete field details

### Update Basic Information

Only include fields you want to change:

```json
{
  "vendor_id": 123,
  "vendor_name": "Acme Corporation Ltd",
  "email": "newcontact@acme.com",
  "payment_terms_code": "NET_60"
}
```

### Managing Related Data (Action Pattern)

For bank accounts, addresses, currencies, and dimensions, use the `_action` field to specify what operation to perform:

| Action | When to Use | Required Fields |
|--------|-------------|-----------------|
| `add` | Create new record | All fields for new record |
| `update` | Modify existing | `id` + fields to change |
| `delete` | Remove record | `id` only |

**Important:** Always use `_action` (with underscore prefix) to specify the operation. The system also accepts `action` for backwards compatibility, but `_action` is preferred.

#### Add Bank Account

```json
{
  "vendor_id": 123,
  "vendor_bank_accounts": [
    {
      "_action": "add",
      "legal_entity_id": 13,
      "account_nickname": "Wire Account",
      "payment_method": "wire_domestic",
      "currency_code": "USD",
      "bank_name": "Wells Fargo",
      "routing_number": "121000248",
      "account_number": "9876543210",
      "account_type": "checking",
      "account_holder_name": "Acme Corporation"
    }
  ]
}
```

#### Update Bank Account

You can update any of the following fields on an existing bank account:

```json
{
  "vendor_id": 123,
  "vendor_bank_accounts": [
    {
      "_action": "update",
      "id": 456,
      "account_nickname": "Primary ACH (Updated)",
      "is_default": true
    }
  ]
}
```

**Updatable Bank Account Fields:**
- `account_nickname` - Friendly name
- `payment_method` - Payment type (ach, wire, etc.)
- `currency_code` - Account currency
- `bank_name` - Financial institution name
- `bank_country` - Bank's country code
- `routing_number` - US routing number
- `account_number` - Account number
- `account_type` - checking, savings, etc.
- `iban` - International Bank Account Number
- `swift_code` - SWIFT/BIC code
- `bic_code` - Bank Identifier Code
- `account_holder_name` - Legal name on account
- `account_holder_address` - Account holder's address
- `account_holder_country` - Account holder's country
- `usage_type` - ap_invoice, expense_reimbursement, etc.
- `is_active` - Whether account is active
- `is_default` - Default for payment method/currency

#### Delete Bank Account

```json
{
  "vendor_id": 123,
  "vendor_bank_accounts": [
    {
      "_action": "delete",
      "id": 789
    }
  ]
}
```

#### Add Currency

```json
{
  "vendor_id": 123,
  "vendor_currencies": [
    {
      "_action": "add",
      "legal_entity_id": 13,
      "currency": "EUR",
      "is_primary": false,
      "rate_source": "SPOT"
    }
  ]
}
```

#### Add Address

```json
{
  "vendor_id": 123,
  "vendor_addresses": [
    {
      "_action": "add",
      "legal_entity_id": 13,
      "address_type": "shipping",
      "address_line_1": "789 Warehouse Way",
      "city": "Phoenix",
      "state_province": "AZ",
      "postal_code": "85001",
      "country": "USA",
      "is_shipping": true
    }
  ]
}
```

#### Add/Update Dimensions

Dimensions use an upsert pattern - if the dimension type already exists for this vendor/entity, it will be updated. Otherwise it will be added.

```json
{
  "vendor_id": 123,
  "vendor_dimensions": [
    {
      "_action": "add",
      "legal_entity_id": 13,
      "dimension_type": "location",
      "dimension_value": "US"
    }
  ]
}
```

**Dimension reference forms (one per command; they must agree if combined):**
- Codes (preferred): `type_code` + `value_code` (aliases `dimension_type` + `dimension_value`)
- Explicit master ids: `master_dimension_type_id` + `master_dimension_value_id`
- Legacy ids: `dimension_type_id` + `dimension_value_id` — read in the vendor endpoint's EFFECTIVE namespace, never as master catalogue ids. The `id` in a validation error's `reference_data.dimension_values` is a master id: send it as `master_dimension_value_id`, or send the entry's `type_code`/`value_code`.

`legal_entity_id` on a command selects one of the entities the operation targets (required on vendor.update; on create, omit it to apply to every target). One command per type per entity; the type must apply to vendors.

#### Delete Dimension

```json
{
  "vendor_id": 123,
  "vendor_dimensions": [
    {
      "_action": "delete",
      "legal_entity_id": 13,
      "dimension_type": "location"
    }
  ]
}
```

#### Update Metadata

```json
{
  "vendor_id": 123,
  "metadata": {
    "netsuite_vendor_id": "V-12345",
    "duns_number": "123456789",
    "minority_owned": true,
    "certifications": ["ISO9001", "SOC2", "CMMC Level 2"],
    "last_audit_date": "2025-01-10"
  }
}
```

**Tip:** Metadata updates replace the entire metadata object. Include all fields you want to keep.

**Getting Reference Data:**
- Dimensions: Use `query("dimension_value")` to find available dimension values and their IDs

---

## Querying Vendors

### Get Single Vendor

Use the unified `get_entity` tool:

```javascript
get_entity("vendor", id=123)
```

**Response includes:**
- All master vendor fields (including `tax_code`)
- Entity-specific overrides applied
- Bank accounts array
- Addresses array
- Currencies array
- Dimensions

### Search Vendors

Use the unified `query` tool:

```javascript
query("vendor", query="Acme", filters={"is_active": true}, limit=50)
```

**Search capabilities:**
- Searches across: `vendor_name`, `global_vendor_id`, `email`, `tax_id`, `phone`, `website`, `notes`
- Filter by: `is_active`, `vendor_type`, `payment_terms_code`, `is_1099_vendor`, `payment_hold`, `currency`, `legal_entity_id`
- Sort by: `vendor_name` (default), `global_vendor_id`, `created_at`, `updated_at`

### List Vendors with Filters

Use `query` for paginated listing with sorting:

```javascript
query("vendor",
  filters={"is_active": true, "vendor_type": "supplier"},
  sort_by="vendor_name", sort_order="asc", limit=50
)
```

---

## Merging Duplicate Vendors

Use the `vendor.merge` workflow to consolidate two vendor records that represent the same payee into one. This commonly happens during agent-driven onboarding when a payee is created twice under slightly different names (e.g., "Google Cloud EMEA" as a duplicate of "Google Workspace").

**See:** [vendor.merge definition](../definitions/vendor.merge.md) for complete field details

### Winner vs Loser

- **Winning vendor** (`winning_vendor_id`) — the record you keep. Its identity and `global_vendor_id` are preserved.
- **Losing vendor** (`losing_vendor_id`) — the duplicate. Every reference is moved off it, then it is soft-deactivated.

```json
{
  "winning_vendor_id": 42,
  "losing_vendor_id": 87,
  "merge_reason": "duplicate"
}
```

### What gets reassigned

In a single transaction, **every reference** to the losing vendor is repointed to the winning vendor:
- Transactions, transaction lines, and GL lines
- Bank and card statement lines
- MSEO entity links (`vendors` rows), dimensions, and contracts
- Agent learned-mappings (vendor_mapping memories)
- Any polymorphic party reference

After all references are moved, the losing vendor is **soft-deactivated** (`is_active=false`) — its history is preserved, never hard-deleted. The winning vendor's identity and `global_vendor_id` are kept.

### Approval

`vendor.merge` runs in the **yellow lane**: it requires a single approval by the `admin` role (configurable per client) before it executes.

> **Tip:** Always call `get_submissions(action='schema', object_type="vendor", operation="merge")` to discover the exact fields before submitting.

---

## Deactivating a Vendor

Use the `vendor.delete` workflow to deactivate or remove vendors.

**See:** vendor.delete definition (fields: `get_submissions(action="schema", object_type, operation)`) for complete field details

### Soft Delete (Recommended)

Deactivates the vendor while preserving historical data:

```json
{
  "vendor_id": 123,
  "deletion_reason": "Vendor no longer providing services",
  "hard_delete": false
}
```

**What happens:**
- Vendor hidden from dropdowns and searches
- Cannot create new bills for this vendor
- Historical bills and payments remain visible
- Audit trail preserved
- Can be reactivated if needed

### Hard Delete (approval as configured)

Permanently removes all vendor data:

```json
{
  "vendor_id": 99,
  "deletion_reason": "Test vendor cleanup - duplicate record",
  "hard_delete": true
}
```

**Use only for:**
- Test vendor cleanup
- Duplicate records
- Data entry errors (never actually paid)

**Never use for vendors with transaction history.**

---

## Bulk Import

**Capabilities:**
- Import vendors from CSV files
- Sync vendors from procurement systems (Coupa, Ariba, etc.)
- Bulk create/update during data migration
- Validate before import (dry-run mode)
- Handle duplicates automatically (skip, update, or error)

### Import Workflow

Use the `vendor.import` workflow:

```javascript
submit("vendor", "import", {
    "records": [
      {
        "vendor_name": "Office Supplies Corp",
        "email": "ap@officesupplies.com",
        "phone": "+1-555-1000",
        "payment_terms_code": "NET_30",
        "tax_id": "12-3456789",
        "currency": "USD",
        "vendor_type": "supplier"
      },
      {
        "vendor_name": "Tech Services LLC",
        "email": "billing@techservices.com",
        "phone": "+1-555-2000",
        "payment_terms_code": "NET_45",
        "tax_id": "98-7654321",
        "currency": "USD",
        "vendor_type": "service_provider",
        "is_1099_vendor": true
      }
      // ... more records
    ],
    "options": {
      "on_duplicate": "update",  // or "skip" or "error"
      "batch_size": 100,
      "stop_on_error": false,
      "validate_only": false
    }
})
```

### Import Options

| Option | Description | Values | Default |
|--------|-------------|--------|---------|
| `on_duplicate` | How to handle duplicates | `skip`, `update`, `error` | `skip` |
| `batch_size` | Records per batch | 1-1000 | 100 |
| `stop_on_error` | Stop on first error | true/false | false |
| `validate_only` | Dry run (no changes) | true/false | false |

### Duplicate Detection

Vendors are considered duplicates if:
1. **tax_id** matches (if provided), OR
2. **email** matches (case-insensitive)

### Required Fields for Import

- `vendor_name` (1-255 chars)
- `email` (valid email format)
- `payment_terms_code` (must exist)

### Optional Fields for Import

- `phone` (max 50 chars)
- `tax_id` (tax identification number)
- `legal_entity_id` (creates entity linkage)
- `currency` (3-letter code)
- `vendor_type` (supplier, contractor, service_provider, utility, government, employee, other)
- `payment_method` (ach, wire, check, international)
- `tax_code` (default VAT treatment; must be one of the organisation's tax codes)
- `billing_email` (valid email)
- `posting_profile_id` (must exist)
- `default_expense_account_id` (must exist)
- `is_1099_vendor` (boolean, default: false)
- `credit_limit` (decimal, >= 0)
- `payment_hold` (boolean, default: false)
- `website` (max 255 chars)
- `notes` (text)
- `metadata` (JSONB)
- `is_active` (boolean, default: true)

### Validation Behavior

The importer performs comprehensive validation:
- **Field validation**: Data types, lengths, formats
- **Foreign key validation**: Verifies payment terms, entities, accounts, posting profiles exist
- **Business rule validation**: Credit limit >= 0, valid vendor/payment types, email format
- **Duplicate detection**: Checks tax_id and email
- **Warnings**: Large credit limits, similar vendor names, missing tax_id for 1099 vendors

### Import Response

```json
{
  "success": true,
  "import_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_records": 250,
  "imported": 240,
  "updated": 8,
  "skipped": 2,
  "errors": 0,
  "warnings": [
    {
      "row": 45,
      "field": "tax_id",
      "message": "1099 vendor should have tax_id",
      "record_identifier": "contractor@example.com"
    }
  ],
  "created_ids": [501, 502, 503, ...],
  "updated_ids": [125, 167, 189, ...],
  "duration_ms": 4560
}
```

### Validate Before Importing (Dry Run)

Test your import without making changes:

```javascript
submit("vendor", "import", {
    "records": [...],
    "options": {
      "validate_only": true
    }
})
```

This returns validation errors without creating any vendors.

### Common Import Scenarios

**Procurement System Sync:**
```javascript
{
  "object_type": "vendor",
  "records": vendors_from_coupa,
  "options": {
    "on_duplicate": "update",  // Update existing vendors
    "stop_on_error": false     // Continue even if some fail
  }
}
```

**Data Migration:**
```javascript
{
  "object_type": "vendor",
  "records": vendors_from_legacy_system,
  "options": {
    "on_duplicate": "skip",    // Don't overwrite existing
    "validate_only": true,     // Test first
    "stop_on_error": true      // Stop if validation fails
  }
}
```

**Contractor import (e.g. US 1099 contractors, where that reporting applies):**
```javascript
{
  "object_type": "vendor",
  "records": contractors_from_csv,
  "options": {
    "on_duplicate": "error",   // Flag duplicates
    "stop_on_error": true      // Stop if duplicate found
  }
}
```

**See:** PLAN_IMPORT.md for import system architecture

---

## Common Scenarios

### Creating Vendors from Bills (Extract Maximum Information)

When processing a bill (AP invoice) and the vendor does not yet exist in the system, **create the vendor first** using as much information as possible from the bill/invoice document. This ensures rich vendor records from the start.

**Extract these fields from the bill whenever available:**

| Bill Field | Vendor Field | Example |
|-----------|-------------|---------|
| Vendor/supplier name | `vendor_name` | "Acme Corporation OU" |
| Tax ID / VAT number | `tax_id` | "EE123456789" |
| Email on invoice | `email` | "billing@acme.ee" |
| Phone on invoice | `phone` | "+372-555-1234" |
| Bank account details | `vendor_bank_accounts` | IBAN, SWIFT, bank name |
| Remit-to / billing address | `vendor_addresses` | Full address from invoice |
| Currency of the bill | `currency` | "EUR" |
| Payment terms on invoice | `payment_terms_code` | "NET_30" |
| Website (if visible) | `website` | "https://acme.ee" |

**Best practice workflow for processing a new bill:**

1. **Check if vendor exists:** `query("vendor", query="Acme")` or search by tax ID
2. **If vendor not found, create it** with all available info from the bill:

```json
{
  "vendor_name": "Acme Corporation OU",
  "tax_id": "EE123456789",
  "email": "billing@acme.ee",
  "phone": "+372-555-1234",
  "payment_terms_code": "NET_30",
  "currency": "EUR",
  "vendor_type": "supplier",
  "website": "https://acme.ee",
  "vendor_bank_accounts": [
    {
      "legal_entity_id": 13,
      "account_nickname": "Primary EUR",
      "payment_method": "sepa",
      "currency_code": "EUR",
      "bank_name": "Swedbank",
      "iban": "EE382200221020145685",
      "swift_code": "HABAEE2X",
      "account_holder_name": "Acme Corporation OU",
      "is_default": true
    }
  ],
  "vendor_addresses": [
    {
      "legal_entity_id": 13,
      "address_type": "billing",
      "address_line_1": "Tartu mnt 83",
      "city": "Tallinn",
      "postal_code": "10115",
      "country": "Estonia",
      "is_primary": true,
      "is_billing": true,
      "is_remit_to": true
    }
  ]
}
```

3. **Then post the bill** using the newly created vendor's ID

**Why this matters:**
- Vendor records with complete info from day one reduce manual data entry later
- Bank account details from invoices enable faster payment processing
- Tax IDs are critical for VAT reporting and vendor duplicate detection
- Addresses ensure payment remittances reach the right destination

**Do NOT create sparse vendor records** (just name and email) when the bill contains more information. Every piece of data on the bill is valuable for the vendor record.

### Onboard New Supplier

1. Create vendor with basic info and payment terms
2. Add bank account for payments
3. Tag with department dimensions for reporting

```json
{
  "vendor_name": "Office Depot Business",
  "tax_id": "12-3456789",
  "email": "business@officedepot.com",
  "phone": "+1-800-463-3768",
  "payment_terms_code": "NET_45",
  "vendor_type": "supplier",
  "currency": "USD"
}
```

### International Vendor Setup

Set up vendor with multiple currencies and SWIFT payment:

```json
{
  "vendor_name": "European Supplier GmbH",
  "tax_id": "DE123456789",
  "email": "accounting@supplier.de",
  "payment_terms_code": "NET_30",
  "currency": "EUR",
  "vendor_bank_accounts": [
    {
      "legal_entity_id": 13,
      "account_nickname": "EUR SWIFT",
      "payment_method": "swift",
      "currency_code": "EUR",
      "bank_name": "Deutsche Bank",
      "iban": "DE89370400440532013000",
      "swift_code": "DEUTDEFF",
      "account_holder_name": "European Supplier GmbH",
      "account_holder_address": "Hauptstraße 123, 10115 Berlin, Germany",
      "account_holder_country": "DE"
    }
  ],
  "vendor_currencies": [
    {
      "legal_entity_id": 13,
      "currency": "EUR",
      "is_primary": true,
      "rate_source": "SPOT"
    }
  ]
}
```

### Change Payment Terms

When negotiating new terms with existing vendor:

```json
{
  "vendor_id": 123,
  "payment_terms_code": "NET_60"
}
```

**Getting Reference Data:**
- Payment Terms: Use `query("payment_term")` to see available payment term codes

### Payment Hold

Temporarily stop payments to vendor (e.g., dispute):

```json
{
  "vendor_id": 123,
  "payment_hold": true,
  "notes": "Payment hold due to quality issues with shipment INV-12345"
}
```

### Add ACH Payment Method

Convert vendor from check to ACH:

```json
{
  "vendor_id": 123,
  "vendor_bank_accounts": [
    {
      "_action": "add",
      "legal_entity_id": 13,
      "account_nickname": "ACH Primary",
      "payment_method": "ach",
      "currency_code": "USD",
      "bank_name": "Bank of America",
      "routing_number": "026009593",
      "account_number": "123456789",
      "account_type": "checking",
      "account_holder_name": "Vendor Name LLC",
      "is_default": true
    }
  ],
  "payment_method": "ach"
}
```

### Retire Inactive Vendor

When vendor is no longer used but has transaction history:

```json
{
  "vendor_id": 123,
  "deletion_reason": "Switched to different supplier",
  "hard_delete": false
}
```

---

## Getting Reference Data

Before constructing payloads, use query tools to get valid reference data:

| Data Type | How to Get | Example Values |
|-----------|-----------|----------------|
| Payment terms | `query("payment_term")` | `NET_30`, `NET_60`, `DUE_ON_RECEIPT` |
| Dimensions | `query("dimension_type")` then `query("dimension_value", filters={"dimension_type_id": X})` | Departments, Cost Centers, Projects |
| Legal entities | `query("legal_entity")` | Entity IDs for bank accounts |
| GL accounts | `query("account", query="expense")` or `query("account", filters={"account_type": "expense"})` | Default expense accounts |
| Tax codes | `query("tax_code")` | The organisation's tax codes (VAT rates, reverse charge, exemptions) |

**Tip:** Always query reference data dynamically rather than hardcoding values, as they may vary by organization and legal entity.

---

## Workflow Details

For complete field specifications, validation rules, and constraints:

- vendor.create (fields: `get_submissions(action="schema", object_type, operation)`) - All required and optional fields
- vendor.update (fields: `get_submissions(action="schema", object_type, operation)`) - Update operations and action patterns
- vendor.delete (fields: `get_submissions(action="schema", object_type, operation)`) - Soft and hard delete options

---

## Key Concepts

### Approval Workflow

All vendor changes go through the workflow system:
1. Submit workflow request
2. System validates payload
3. Routes to AP Manager then Controller for approval
4. Executes after approval

### MSEO Pattern

Vendors use the Master + Entity Override pattern:
- Master vendor record visible to all entities
- Entity-specific overrides for currency, payment terms
- Effective views show resolved values (master + any overrides)

### Bank Account Security

- Account numbers and routing numbers are encrypted at rest
- Bank details are entity-specific (not shared across entities)
- Only authorized users can view/modify bank information
- Verification workflow for new bank accounts

### Multi-Currency Support

- Support for multiple payment currencies per vendor
- Flexible exchange rate management (spot, contract, fixed)
- Currency-specific payment terms
- Automatic rate application during payment processing

### Related Entity Aliases

When updating related data, these field names are supported:
- `vendor_bank_accounts` - Bank account records
- `vendor_addresses` - Address records
- `vendor_currencies` - Currency configurations
- `vendor_dimensions` - Dimension assignments

---

## Tips & Best Practices

### 1. Metadata Usage
- Always check existing vendors' metadata structure before adding new fields
- Use consistent field names across all vendors
- Namespace integration data to avoid conflicts
- Document your metadata schema

### 2. Bank Account Management
- Verify bank account details before first payment
- Use account nickname for easy identification
- Set payment limits for security
- Mark primary account as `is_default=true`
- Encrypt sensitive data (automatic)

### 3. Address Management
- Use `remit_to` address type for payment destination
- Use `is_remit_to=true` flag for clarity
- Can have multiple addresses of different types
- Keep addresses up to date to avoid payment delays

### 4. Multi-Currency Vendors
- Set primary currency to vendor's preferred currency
- Use `SPOT` rate for most vendors (market rate)
- Use `CONTRACT` rate only when negotiated fixed rate
- Only one primary currency per vendor

### 5. Payment Terms
- Align payment terms with vendor contracts
- Consider early payment discounts (2/10 Net 30)
- Update terms when renegotiating contracts
- Use vendor-specific terms for strategic partners

### 6. Contractor information reporting (where the jurisdiction requires it)
- Only where the jurisdiction requires it (e.g. US 1099 reporting); otherwise skip this section
- e.g. in the US: mark reportable contractors `is_1099_vendor=true`, collect the forms that
  regime requires (W-9) and check the tax-ID format it uses (SSN / EIN)
- Keep remit-to addresses current for any year-end statements the regime requires

### 7. Dimensions
- Tag all vendors with relevant dimensions at creation
- Dimensions auto-flow to AP bills and expense allocations
- Update dimensions when vendor relationship changes
- Use for spend analysis and budget tracking

### 8. Query Performance
- Use `get_entity` for single vendor lookup (optimized effective view)
- Use `query` with filters for finding vendors
- Filter by `is_active=true` to exclude deactivated vendors
- Tax ID searches are faster than name searches

### 9. Data Quality
- Validate email addresses before creating vendors
- Standardize phone number format across all vendors
- Keep billing contact info updated
- Regular cleanup of duplicate or test vendors
- Verify tax IDs for vendors subject to contractor reporting (e.g. US 1099 vendors)

### 10. Payment Hold
- Use `payment_hold=true` to temporarily stop payments
- Document reason in `notes` field
- Remove hold promptly after issue resolved
- Communicate holds to AP team

---

## Customer-Vendor Links

Many business counterparties act as both a customer and a vendor. The customer-vendor linking feature connects these records at the organization level.

### Key Facts

- **1:1 constraint**: Each customer links to at most one vendor, and vice versa
- **Optional field sync**: Automatically keep name, email, phone, and tax_id in sync
- **Auto-suggestions**: Find potential links based on matching tax_id, email, or name

### Link a Vendor to a Customer

```
submit("customer_vendor_link", "create", {
  "master_customer_id": 42,
  "master_vendor_id": 15,
  "sync_direction": "bidirectional",
  "sync_fields": ["name", "email", "phone", "tax_id"],
  "link_reason": "Same business entity - Acme Corp"
})
```

**Sync directions**: `none` (default), `customer_to_vendor`, `vendor_to_customer`, `bidirectional`

### View Link

```
get_entity("vendor", 15)
```

The response includes a `linked_customer` object (`linked_customer_id`, `global_customer_id`, `customer_name`, `customer_email`) when a link exists.

### Find Potential Links

There is no dedicated suggestion tool. Manually search for a matching counterparty by the vendor's tax_id, email, or name, then review the results for a same-entity match:

```
query("customer", query="<vendor's tax_id>")
query("customer", query="<vendor's email>")
query("customer", query="<vendor's name>")
```

### Update Link

```
submit("customer_vendor_link", "update", {
  "master_vendor_id": 15,
  "sync_direction": "vendor_to_customer",
  "sync_fields": ["name", "tax_id"]
})
```

### Remove Link

```
submit("customer_vendor_link", "delete", {
  "master_vendor_id": 15,
  "deletion_reason": "No longer trading with this party"
})
```

Removing a link does **not** delete either the customer or vendor record.

### Automatic Sync on Update

When a vendor is updated and a link with sync enabled exists (`vendor_to_customer` or `bidirectional`), changed fields in the `sync_fields` list are automatically propagated to the linked customer.

---

## Query Field Reference

### Display Fields (returned by `query` / `query`)

| Field | Type | Description |
|-------|------|-------------|
| `master_vendor_id` | integer | Master vendor record ID |
| `global_vendor_id` | string | Organization-wide unique ID |
| `vendor_name` | string | Vendor business name |
| `email` | string | Primary contact email |
| `phone` | string | Primary phone number |
| `payment_terms_code` | string | Default payment terms |
| `currency` | string | Default currency code |
| `is_active` | boolean | Active status |

### Searchable Fields (text search via `query("vendor", query=...)`)

| Field | Description |
|-------|-------------|
| `vendor_name` | Vendor name (partial match) |
| `global_vendor_id` | Organization-wide vendor ID |
| `email` | Primary email address |
| `tax_id` | Tax identification number |
| `phone` | Phone number |
| `website` | Website URL |
| `notes` | Internal notes |

### Filter Fields (via `filters` parameter)

| Field | Type | Example |
|-------|------|---------|
| `legal_entity_id` | integer | `13` |
| `is_active` | boolean | `true` |
| `vendor_type` | string | `"supplier"` |
| `payment_terms_code` | string | `"NET_30"` |
| `is_1099_vendor` | boolean | `true` |
| `payment_hold` | boolean | `false` |
| `currency` | string | `"USD"` |

### Sort Fields (via `sort_by` parameter)

| Field | Default | Description |
|-------|---------|-------------|
| `vendor_name` | Yes | Alphabetical by name |
| `global_vendor_id` | | By vendor ID |
| `created_at` | | Newest first |
| `updated_at` | | Recently modified |

### Related Data (returned by `get_entity` with `include_related=True`)

| Related Entity | Description |
|----------------|-------------|
| `addresses` | Business, billing, remittance addresses |
| `bank_accounts` | Encrypted bank account details |
| `currencies` | Supported currencies for payments |
| `dimensions` | Department, project, cost center tags |
| `linked_customer` | Linked customer record (if any) |

---

## End of Guide

This guide covers complete vendor management including all database fields, workflows, query tools, metadata usage, and operational best practices for Claude.ai automation.


### Unreleased vendor-note access clarification

The Admin vendor detail page keeps Bill processing notes visible to existing
readers, but editing requires the server-derived `canEdit` hint: current membership
write access plus `master_data:write`. A Controller label alone is not a write grant.
Read-only users see no Save or approval prompt; save errors remain inline. The hint
does not replace current backend authorization or authorize payment execution.
Supplier notes remain low-authority context, submitted through `vendor.update`.
