# Customer Management Guide

> **MSEO release contract:** Customer business identity is the master ID. Supported dimension code commands retain entity scope; numeric legacy commands use the endpoint’s declared entity namespace. Explicit master dimension fields avoid numeric ambiguity. See the dimensions-management resource for assignment, approval and compatibility rules.

This guide explains how to manage customers in the AI-Native ERP system.

---

## Overview

Customers are the businesses and individuals who buy your products or services. The workflow system ensures proper authorization, audit trails, and risk-based approvals for all customer operations.

**What you can do:**
- Create new customers with addresses, pricing tiers, tax profiles, and dimensions
- Update customer information (credit limits, payment terms, pricing, addresses)
- Query customer data (single customer, search/filter)
- Deactivate customers (soft delete) or remove test data (hard delete)
- Bulk import customers from CSV/API sources

**Available Workflows:**

| Workflow | Purpose | When to Use |
|----------|---------|-------------|
| `customer.create` (fields: `get_submissions(action="schema", object_type, operation)`) | Create new customer | Onboarding new client |
| `customer.update` (fields: `get_submissions(action="schema", object_type, operation)`) | Update customer data | Change credit limit, pricing, addresses |
| [`customer.merge`](../definitions/customer.merge.md) | Merge duplicate customers | Two records exist for the same client |
| `customer.delete` (fields: `get_submissions(action="schema", object_type, operation)`) | Deactivate customer | Customer no longer active |

**Available Query Tools:**

| Tool | Purpose |
|------|---------|
| `get_entity("customer", id=X)` | Get single customer (includes addresses, dimensions, pricing, tax profiles) |
| `query("customer", filters)` | List customers with filters and pagination |
| `query("customer", query, filters)` | Search customers by text |
| `query("customer", filters, limit=1)` | Count matching customers (use `total_count` from response) |
| `get_submissions(action='schema', object_type="customer", operation="create")` | Get field schema before creating |
| `get_submissions(action='schema', object_type="customer", operation="update")` | Get update field schema |
| `query(entity_type, filters={...})` ×N | Fetch payment terms, tax codes, dimensions (parallel calls) before creating customers |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

**Key notes:**
- `get_entity` defaults to `include_related=True` — addresses, dimensions, item pricing, tax profiles included automatically
- Search/list results now include: `customer_name`, `email`, `phone`, `customer_type`, `payment_terms_code`, `currency`, `tax_id`, `credit_limit`, `is_active`
- Searchable fields: `customer_name`, `email`, `tax_id`, `phone`, `website`, `billing_email`, `notes`, `global_customer_id`
- Sort by: `customer_name`, `global_customer_id`, `created_at`, `updated_at`

---

## Complete Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

### Master Customer Fields (master_customers table)

**Required Fields:**
- `customer_name` (string, 1-255 chars) - Customer business or person name
- `email` (string, valid email) - Primary contact email
- `legal_entity_id` (integer) - Which entity owns this customer
- `currency` (string, 3 chars) - Default currency code (USD, EUR, etc.)

> **Note:** Required fields are configurable per organization. The fields listed here are the defaults. Always call `get_submissions(action='schema', object_type="customer", operation="create")` to discover the exact required fields for your setup.

**Business Information:**
- `customer_type` (enum) - Customer classification
  - Options: `retail`, `wholesale`, `distributor`, `enterprise`, `government`, `nonprofit`, `other`
- `phone` (string, max 50) - Primary phone number
- `website` (string, max 255) - Customer website URL
- `billing_email` (string, max 255) - Separate email for invoices (if different from primary)
- `tax_id` (string, max 50) - Tax identification number (EIN, VAT, etc.)
- `notes` (text) - Internal notes about this customer

**Credit & Payment:**
- `credit_limit` (decimal 15,2) - Maximum outstanding AR balance allowed
- `payment_terms_code` (string) - Default payment terms (e.g., `NET_30` or `net_30` -- case-insensitive, underscore optional; `NET30` also accepted)
- `payment_method_id` (integer, FK) - Preferred payment method
- `currency` (string, 3 chars) - Default currency code (USD, EUR, etc.)

**Accounting Defaults:**
- `default_revenue_account_id` (bigint, FK) - Default revenue GL account
- `default_ar_account_number` (string) - Default AR account number

**System & Audit:**
- `global_customer_id` (string, auto-generated) - Organization-wide unique ID (e.g., CUST-000123)
- `is_active` (boolean, default: true) - Soft delete flag
- `metadata` (jsonb) - Custom fields (see [Metadata Best Practices](#metadata-best-practices))
- `created_at`, `updated_at`, `created_by`, `updated_by` - Audit fields

**Scope & Visibility (unified MSEO contract):**
`customer.create` is `SCOPE_MODE='fanout'`. The combination of `is_global`, `legal_entity_id`, and `legal_entity_ids` resolves to a list of target entities — the executor writes a master row plus one `customers` row per target entity.

- `is_global` (boolean, default: `true` — note: the unified contract default is True for fanout entities, replacing the older "default false" guidance) — when `true`, fans out to EVERY active legal_entity. When `false`, entity targets come from the IDs.
- `legal_entity_id` (integer, optional) — single-entity attach. Implies `is_global=false`. Result: master + ONE `customers` row.
- `legal_entity_ids` (integer[], optional) — multi-entity attach. Replaces the old implicit array-resolution logic.
- **No flag, no IDs** → defaults to `is_global=true` → fanout to all entities.
- **`is_global=false` + no IDs** → master only (template); `customer_dimensions`, `customer_item_pricing`, `customer_tax_profiles`, `addresses`/`customer_addresses` REJECTED loudly.

Per-customer dependent payloads carry their own `legal_entity_id` keys; the executor filters them to match the current target entity row during fanout. See GUIDE_MSEO_PATTERN.md for the full contract.

### Entity Override Fields (customers table)

All master fields can be overridden per entity with `_override` suffix:
- `customer_name_override`
- `email_override`
- `phone_override`
- `payment_terms_code_override`
- `credit_limit_override`
- `tax_id_override`
- `currency_override`
- `is_active_override`
- `metadata_override`
- `payment_method_id_override`

**Entity-Specific Fields:**
- `customer_number` (string, auto-generated) - Entity-specific customer number
- `entity_customer_code` (string) - Custom entity code if needed

### Customer Addresses (customer_addresses table)

**Required:**
- `address_line_1` (string, max 255) - Street address
- `country` (string, max 100) - Country name
- `address_type` (enum) - Address classification
  - Options: `primary`, `billing`, `shipping`, `headquarters`, `branch`, `warehouse`, `other`

**Optional:**
- `address_line_2` (string, max 255) - Apt/Suite/Floor
- `city` (string, max 100) - City name
- `state_province` (string, max 100) - State/province/region
- `postal_code` (string, max 50) - ZIP/postal code
- `notes` (text) - Address-specific notes

**Flags:**
- `is_primary` (boolean, default: false) - Primary address (only one per customer/entity)
- `is_billing` (boolean, default: false) - Use for billing
- `is_shipping` (boolean, default: false) - Use for shipping
- `is_active` (boolean, default: true) - Active address

**Tip:** You can have multiple addresses of different types. Use both `address_type` and boolean flags for flexibility:
- Set `address_type="billing"` and `is_billing=true` for explicit billing address
- Set `is_primary=true` for default address when type is unspecified

**Changing addresses with `customer.update`:** send `customer_addresses` as operations with `_action`:
- `add` needs `address_line_1`, plus `legal_entity_id` unless the customer is linked to one entity only.
- `update` needs `id` and sets only the fields you name; a field sent as `null` is emptied.
- `delete` needs `id`.

The `id` must be one of this customer's addresses (`get_entity("customer", id=X)` lists them). An operation that cannot apply refuses the whole update, so nothing is half-changed.

### Customer Item Pricing (customer_item_pricing table)

Customer-specific pricing tiers for volume discounts or negotiated rates.

> **Optional during customer create:** The `customer_item_pricing` array is optional (min_required: 0). You can create a customer without any item pricing and add it later via `customer.update`.

**Required (per pricing record):**
- `item_id` (bigint, FK) - Which item/product
- `price` (decimal 15,2) - Fixed price OR
- `discount_percent` (decimal 9,6, 0-100) - Percentage discount from list price
- `effective_from` (date, defaults to today if not provided) - Start date

**Optional:**
- `effective_to` (date) - End date (null = no expiration)
- `notes` (text) - Pricing notes

**Tips:**
- Use `price` for fixed negotiated pricing (e.g., $8.50/unit)
- Use `discount_percent` for percentage off list price (e.g., 15% off)
- Cannot use both price and discount_percent on same record
- Only one active pricing record per item/customer/entity/date combination
- Invoicing automatically applies customer pricing when available

### Customer Tax Profiles (customer_tax_profiles table)

> **Optional during customer create:** The `customer_tax_profiles` array is optional (min_required: 0). You can create a customer without any tax profiles and add them later via `customer.update`.

Tax exemptions, special tax codes, and VAT/reverse charge settings.

**Tax Exemption:**
- `tax_exempt` (boolean, default: false) - Customer has tax exemption
- `exemption_type` (string, max 50) - Type of exemption (resale, nonprofit, government, etc.)
- `exemption_certificate_number` (string, max 100) - Certificate/license number
- `exemption_certificate_expiry` (date) - When certificate expires

**Tax Configuration:**
- `default_tax_code_id` (integer, FK) - Default tax code for this customer
- `default_jurisdiction_id` (integer, FK) - Tax jurisdiction
- `taxable_in_jurisdiction` (boolean, default: true) - Subject to local tax
- `reverse_charge_eligible` (boolean, default: false) - VAT reverse charge applies

**Tax IDs:**
- `vat_number` (string, max 50) - VAT registration number (EU)
- `tax_id_number` (string, max 50) - Tax ID for this profile

**System:**
- `is_active` (boolean, default: true) - Active profile
- `notes` (text) - Tax-related notes
- `metadata` (jsonb) - Additional tax data

**Important:** Only one tax profile per customer per entity. For multi-jurisdiction scenarios, use metadata or separate profiles per entity.

### Customer Dimensions (customer_dimensions table)

> **Optional during customer create:** The `customer_dimensions` array is optional (min_required: 0). You can create a customer without dimensions and add them later via `customer.update`.

Tag customers with analytical dimensions for reporting and analytics.

**Required Fields:**
- `legal_entity_id` (integer, FK) - Which entity this dimension applies to
- `dimension_type` (string) - Dimension type name (e.g., "department", "location")
- `dimension_value` (string) - Dimension value code (e.g., "SALES", "NYC", "REMOTE")

**Other accepted references:** `type_code`/`value_code` (canonical spellings), explicit `master_dimension_type_id`/`master_dimension_value_id`, or legacy `dimension_type_id`/`dimension_value_id` read in the customer endpoint's ENTITY namespace (never master catalogue ids).

**Important:**
- Customer dimensions are stored per legal entity. When adding dimensions, you must specify which `legal_entity_id` the dimension applies to
- Use dimension type **name** (e.g., "department", "location") and value **code** (e.g., "SALES", "NYC") instead of IDs
- Only types whose `applies_to` includes `customer` can be assigned — `query("dimension_type")` shows each type's `applies_to` for this org; the dry run (`validate_only`) refuses the others
- The system will automatically create the customer-entity linkage if it doesn't exist

**Dimensions are automatically applied to:**
- AR invoices created for this customer
- Revenue recognition entries
- Reports filtered by dimension

**Getting Reference Data:**
- Dimension Types: Use `query("dimension_type")` to see available dimension types and which entities they apply to
- Dimension Values: Use `query("dimension_value", filters={"dimension_type_id": <id from query("dimension_type")>})` to get values for a specific type

---

## Custom Fields

Organisations define their own customer fields (contract number, review
date, preferred contact method…). Before putting a business fact into
`metadata`, check whether a custom field exists for it:

- `get_submissions(action="schema", object_type="customer", operation="create")` → `custom_fields` lists each
  active field: key, label, description, type, limits, choice options and
  whether it is required.
- Set values with `"custom_fields": {"key": value}`; on update, keys you leave
  out are unchanged and `"custom_fields_clear": ["key"]` empties one. Never
  send `null` as a value.
- Types: text (string), decimal (numeric string within `scale`; a JSON number
  loses digits above about 15),
  boolean (true/false), date (`YYYY-MM-DD`), choice (one option `value`).
- Find customers with `query("customer", filters={"custom_fields.<key>": value})`
  — also lists, `None` (no value), `{"exists": true}` and `{"gte"|"lte"|"gt"|"lt": n}`.
- A field the organisation needs but has not defined is created by an admin
  with `submit("custom_field", "create", …)`; do not invent `metadata` keys
  for it. A list that classifies customers for reporting is a dimension.

All rules (register, types, required fields, transactions, filters, import, merge): the custom-fields resource; full contract `docs/GUIDES/GUIDE_CUSTOM_FIELDS.md`.

## Metadata Best Practices

The `metadata` JSONB field allows storing custom data without schema changes.

### When to Use Metadata

✅ **Good use cases:**
- Customer-specific attributes that vary widely (industry, SIC code, account manager notes)
- Integration IDs from external systems (Salesforce ID, Stripe customer ID)
- Temporary attributes during migration or testing
- Rarely-queried supplementary information
- Custom fields specific to your industry

❌ **Bad use cases:**
- Frequently queried fields (use real columns for performance)
- Fields requiring complex validation (use Pydantic models)
- Fields that need database constraints or indexes
- Standard accounting data (use dedicated tables)

### Metadata Structure Tips

1. **Check existing customers first** before adding new metadata fields:
   ```
   Use get_entity("customer", id=123) to see existing metadata structure
   ```

2. **Use consistent field names** across all customers:
   ```json
   {
     "salesforce_id": "001xx000003DGb2",
     "industry_code": "SIC-7372",
     "account_manager": "Jane Smith",
     "customer_since": "2020-01-15",
     "preferred_shipping_carrier": "FedEx"
   }
   ```

3. **Namespace integration data** to avoid conflicts:
   ```json
   {
     "integrations": {
       "salesforce": {"account_id": "001xx000003DGb2", "last_sync": "2025-01-15T10:30:00Z"},
       "stripe": {"customer_id": "cus_123456", "subscription_id": "sub_789"}
     }
   }
   ```

4. **Document your metadata schema** in your organization's wiki or knowledge base

5. **Query metadata** using PostgreSQL JSON functions:
   ```sql
   SELECT * FROM master_customers
   WHERE metadata->>'industry_code' = 'SIC-7372'
   ```

### Updating Metadata

**Add new field:**
```json
{
  "customer_id": 123,
  "metadata": {
    "existing_field": "value",
    "new_field": "new_value"
  }
}
```

**Remove field:**
```json
{
  "customer_id": 123,
  "metadata": {
    "existing_field": "value"
    // Simply omit the field you want to remove
  }
}
```

**Tip:** Metadata updates are full replacements, not merges. Always include all fields you want to keep.

---

## Creating a Customer

Use the `customer.create` workflow to add new customers.

**See:** customer.create definition (fields: `get_submissions(action="schema", object_type, operation)`) for complete field details

### Basic Customer

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="customer", operation="create")

// Step 2: Submit with discovered fields
submit("customer", "create", '{...}')
// Tip: Use validate_only=true to check payload before submitting
```

```json
{
  "customer_name": "Acme Corporation",
  "email": "billing@acme.com",
  "phone": "+1-555-0100",
  "legal_entity_id": 13,
  "credit_limit": 50000.00,
  "payment_terms_code": "NET_30",
  "currency": "USD"
}
```

**Getting Reference Data:**
- Payment Terms: Use `query("payment_term")` to get valid `payment_terms_code` values
- Legal Entities: Use `query("legal_entity")` to get valid `legal_entity_id` values

### Customer with Addresses

Include billing and shipping addresses. You can use either `addresses` or `customer_addresses` as the field name - both work:

```json
{
  "customer_name": "Acme Headquarters",
  "email": "billing@acme.com",
  "legal_entity_id": 13,
  "credit_limit": 50000.00,
  "payment_terms_code": "NET_30",
  "customer_type": "wholesale",
  "addresses": [
    {
      "address_type": "billing",
      "address_line_1": "123 Corporate Blvd",
      "address_line_2": "Suite 500",
      "city": "San Francisco",
      "state_province": "CA",
      "postal_code": "94102",
      "country": "USA",
      "is_primary": true,
      "is_billing": true
    },
    {
      "address_type": "shipping",
      "address_line_1": "456 Warehouse Way",
      "city": "Oakland",
      "state_province": "CA",
      "postal_code": "94612",
      "country": "USA",
      "is_shipping": true
    }
  ]
}
```

**Address Field Name Options:**
- `addresses` - Workflow standard field name (recommended)
- `customer_addresses` - Alternative, also accepted

**Important:** The first address in the array becomes the primary address by default. Set `is_primary: true` explicitly if you want a different address to be primary.

### Customer with Tax Exemption

For nonprofits or tax-exempt organizations:

```json
{
  "customer_name": "Nonprofit Organization",
  "email": "accounting@nonprofit.org",
  "legal_entity_id": 13,
  "tax_id": "12-3456789",
  "credit_limit": 25000.00,
  "payment_terms_code": "NET_15",
  "customer_tax_profiles": [
    {
      "legal_entity_id": 13,
      "tax_exempt": true,
      "exemption_type": "nonprofit",
      "exemption_certificate_number": "EX-2025-001",
      "exemption_certificate_expiry": "2025-12-31",
      "notes": "501(c)(3) tax exempt organization"
    }
  ]
}
```

**Important:** Each tax profile requires `legal_entity_id` because tax exemptions are entity-specific. The system creates a linkage record (`customers.id`) for the entity, and the tax profile references that linkage ID.

**Getting Reference Data:**
- Tax Codes: Use `query("tax_code")` to get valid tax codes including exemptions

### Customer with Volume Pricing

For customers with negotiated pricing:

```json
{
  "customer_name": "Volume Buyer Inc",
  "email": "procurement@volumebuyer.com",
  "legal_entity_id": 13,
  "credit_limit": 100000.00,
  "payment_terms_code": "NET_45",
  "customer_item_pricing": [
    {
      "legal_entity_id": 13,
      "item_id": 25,
      "price": 8.50,
      "effective_from": "2025-01-01",
      "notes": "Negotiated volume discount"
    }
  ]
}
```

**Important:** Each pricing record requires `legal_entity_id` because pricing is entity-specific. This allows different pricing for the same customer across different legal entities.

### Customer with Dimensions

Tag customers with department, location, or other applicable dimensions:

```json
{
  "customer_name": "West Coast Retail",
  "email": "orders@westcoastretail.com",
  "legal_entity_id": 10,
  "credit_limit": 75000.00,
  "customer_dimensions": [
    { "legal_entity_id": 10, "dimension_type": "department", "dimension_value": "SALES" },
    { "legal_entity_id": 10, "dimension_type": "location", "dimension_value": "NYC" }
  ]
}
```

**Important:**
- Use dimension type **name** (e.g., "department", "location") not IDs
- Use dimension value **code** (e.g., "SALES", "NYC") not IDs
- Only certain dimension types apply to customers (department, location)
- Always include `legal_entity_id` for each dimension

**Getting Reference Data:**
- Dimension Types: Use `query("dimension_type")` to find types that apply to customers (`applies_to` contains "customer")
- Dimension Values: Use `query("dimension_value", filters={"dimension_type_id": <id from query("dimension_type")>})` to get available values

### Customer with Custom Metadata

Store integration IDs and custom attributes:

```json
{
  "customer_name": "Enterprise Customer Inc",
  "email": "ar@enterprise.com",
  "legal_entity_id": 13,
  "credit_limit": 250000.00,
  "metadata": {
    "salesforce_account_id": "001xx000003DGb2",
    "industry": "Technology",
    "sic_code": "7372",
    "customer_tier": "platinum",
    "account_manager": "Jane Smith",
    "customer_since": "2020-06-15"
  }
}
```

### Complete Customer with All Related Entities

A comprehensive example with addresses, dimensions, tax profile, and pricing:

```json
{
  "customer_name": "Veriff OÜ",
  "email": "sales@veriff.com",
  "phone": "+372 5551234",
  "website": "https://www.veriff.com",
  "legal_entity_id": 10,
  "credit_limit": 50000.00,
  "payment_terms_code": "NET_30",
  "currency": "EUR",
  "customer_type": "enterprise",
  "notes": "Identity verification provider from Estonia",
  "addresses": [
    {
      "legal_entity_id": 10,
      "address_type": "billing",
      "address_line_1": "Niine 11",
      "city": "Tallinn",
      "state_province": "Harju",
      "postal_code": "10414",
      "country": "Estonia",
      "is_primary": true,
      "is_billing": true
    }
  ],
  "customer_dimensions": [
    {
      "legal_entity_id": 10,
      "dimension_type": "department",
      "dimension_value": "SALES"
    },
    {
      "legal_entity_id": 10,
      "dimension_type": "location",
      "dimension_value": "REMOTE"
    }
  ],
  "customer_tax_profiles": [
    {
      "legal_entity_id": 10,
      "tax_exempt": false,
      "vat_number": "EE123456789",
      "reverse_charge_eligible": true
    }
  ],
  "customer_item_pricing": [
    {
      "legal_entity_id": 10,
      "item_id": 25,
      "price": 8.50,
      "effective_from": "2025-01-01",
      "notes": "Negotiated enterprise rate"
    }
  ],
  "metadata": {
    "salesforce_id": "001xx000003DGb2",
    "industry": "Technology",
    "segment": "Enterprise"
  }
}
```

**Key Points:**
- All related entities (addresses, dimensions, tax_profiles, pricing) require `legal_entity_id`
- Use `addresses` or `customer_addresses` - both work
- Dimensions use **name** and **code** lookups (`dimension_type`/`dimension_value`), not IDs
- Only `department` and `location` dimension types apply to customers
- Tax profiles are 1:1 per customer per entity
- Item pricing allows multiple records per item with different effective dates

---

## Updating a Customer

Use the `customer.update` workflow to modify existing customers.

**See:** customer.update definition (fields: `get_submissions(action="schema", object_type, operation)`) for complete field details

### Update Basic Information

Only include fields you want to change:

```json
{
  "customer_id": 123,
  "customer_name": "Acme Corporation Ltd",
  "email": "newbilling@acme.com",
  "credit_limit": 75000.00
}
```

### Clear a Contact Field

A missing or null field means "leave unchanged", so it cannot empty a stored
value. To remove one, name it in `clear_fields`; it is set to empty (NULL) and
the change is audited like any other update. Only these fields can be cleared:
`email`, `billing_email`, `phone`, `website`, `notes`, `tax_id`. A field cannot
be set and cleared in the same update.

```json
{
  "customer_id": 123,
  "clear_fields": ["email"]
}
```

### Managing Related Data (Action Pattern)

For addresses, pricing, tax profiles, and dimensions, use the `_action` field:

| Action | When to Use | Required Fields |
|--------|-------------|-----------------|
| `add` | Create new record | All fields for new record |
| `update` | Modify existing | `id` + fields to change |
| `delete` | Remove record | `id` only |

#### Add Pricing Tier

```json
{
  "customer_id": 123,
  "customer_item_pricing": [
    {
      "_action": "add",
      "legal_entity_id": 13,
      "item_id": 30,
      "discount_percent": 15.00,
      "effective_from": "2025-01-01",
      "notes": "15% volume discount"
    }
  ]
}
```

#### Update Pricing Tier

```json
{
  "customer_id": 123,
  "customer_item_pricing": [
    {
      "_action": "update",
      "id": 456,
      "price": 11.50,
      "effective_from": "2025-02-01"
    }
  ]
}
```

#### Delete Pricing Tier

```json
{
  "customer_id": 123,
  "customer_item_pricing": [
    {
      "_action": "delete",
      "id": 789
    }
  ]
}
```

#### Add Tax Exemption

```json
{
  "customer_id": 123,
  "customer_tax_profiles": [
    {
      "_action": "add",
      "legal_entity_id": 13,
      "tax_exempt": true,
      "exemption_type": "government",
      "exemption_certificate_number": "EX-2025-100",
      "exemption_certificate_expiry": "2025-12-31",
      "notes": "Government entity - tax exempt"
    }
  ]
}
```

#### Add/Update/Delete Address

```json
{
  "customer_id": 123,
  "addresses": [
    {
      "_action": "add",
      "legal_entity_id": 13,
      "address_type": "shipping",
      "address_line_1": "789 New Warehouse Rd",
      "city": "Phoenix",
      "state_province": "AZ",
      "postal_code": "85001",
      "country": "USA",
      "is_shipping": true
    },
    {
      "_action": "update",
      "id": 45,
      "address_line_1": "123 Updated Corporate Blvd",
      "city": "San Jose"
    },
    {
      "_action": "delete",
      "id": 46
    }
  ]
}
```

#### Add/Update Dimension

Use `dimension_type` (name) and `dimension_value` (code) for dimension assignments:

```json
{
  "customer_id": 123,
  "customer_dimensions": [
    {
      "_action": "add",
      "legal_entity_id": 10,
      "dimension_type": "department",
      "dimension_value": "SALES"
    },
    {
      "_action": "add",
      "legal_entity_id": 10,
      "dimension_type": "location",
      "dimension_value": "NYC"
    }
  ]
}
```

**Important:**
- Use dimension type **name** (e.g., "department", "location"), not IDs
- Use dimension value **code** (e.g., "SALES", "NYC", "REMOTE"), not IDs
- Only `department` and `location` apply to customers (not `project` or `cost_center`)
- Dimensions upsert automatically - if customer already has that dimension type, it updates the value

#### Update Metadata

```json
{
  "customer_id": 123,
  "metadata": {
    "salesforce_account_id": "001xx000003DGb2",
    "industry": "Healthcare",
    "sic_code": "8062",
    "customer_tier": "gold",
    "last_contract_renewal": "2025-01-10"
  }
}
```

**Tip:** Metadata updates replace the entire metadata object. Include all fields you want to keep.

**Getting Reference Data:**
- Dimensions: Use `query("dimension_value")` to find available dimension values and their IDs

---

## Querying Customers

### Get Single Customer (Recommended)

Use the unified `get_entity` tool:

```javascript
get_entity("customer", id=123)
```

**Response includes:**
- All master customer fields
- Entity-specific overrides applied
- Addresses array
- Item pricing tiers
- Tax profiles
- Dimensions


### Search Customers (Recommended)

Use the unified `query` tool:

```javascript
query("customer", query="Acme", filters={"legal_entity_id": 13, "is_active": true}, limit=50)
```

**Search capabilities:**
- Searches across: customer_name, email, tax_id, phone, website, billing_email, notes, global_customer_id
- Filter by: legal_entity_id, is_active, customer_type, payment_terms_code, tax_exempt, currency
- Sort by: customer_name (default), global_customer_id, created_at, updated_at
- Pagination: limit and offset supported

---

## Merging Duplicate Customers

Use the `customer.merge` workflow to consolidate two customer records that represent the same client into one. This commonly happens during agent-driven onboarding when a client is created twice under slightly different names.

**See:** [customer.merge definition](../definitions/customer.merge.md) for complete field details

### Winner vs Loser

- **Winning customer** (`winning_customer_id`) — the record you keep. Its identity and `global_customer_id` are preserved.
- **Losing customer** (`losing_customer_id`) — the duplicate. Every reference is moved off it, then it is soft-deactivated.

```json
{
  "winning_customer_id": 42,
  "losing_customer_id": 87,
  "merge_reason": "duplicate"
}
```

### What gets reassigned

In a single transaction, **every reference** to the losing customer is repointed to the winning customer:
- Transactions, transaction lines, and GL lines
- Bank and card statement lines
- MSEO entity links (`customers` rows), dimensions, and contracts
- Agent learned-mappings (customer_mapping memories)
- Any polymorphic party reference

After all references are moved, the losing customer is **soft-deactivated** (`is_active=false`) — its history is preserved, never hard-deleted. The winning customer's identity and `global_customer_id` are kept.

### Approval

`customer.merge` runs in the **yellow lane**: it requires a single approval by the `admin` role (configurable per client) before it executes.

> **Tip:** Always call `get_submissions(action='schema', object_type="customer", operation="merge")` to discover the exact fields before submitting.

---

## Deactivating a Customer

Use the `customer.delete` workflow to deactivate or remove customers.

**See:** customer.delete definition (fields: `get_submissions(action="schema", object_type, operation)`) for complete field details

**Accepted Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `customer_id` | integer | Yes* | Numeric customer ID |
| `global_customer_id` | string | Yes* | Global customer ID (e.g., `"CUST-000123"`) |
| `deletion_reason` | string | Yes | Reason for deletion (audit trail) |
| `hard_delete` | boolean | No | `true` for permanent delete, `false` (default) for soft delete |

*Either `customer_id` or `global_customer_id` can be used to identify the customer.

### Soft Delete (Recommended)

Deactivates the customer while preserving historical data:

```json
{
  "customer_id": 123,
  "deletion_reason": "Customer business closed",
  "hard_delete": false
}
```

**What happens:**
- Customer hidden from dropdowns and searches
- Cannot create new invoices for this customer
- Historical invoices and payments remain visible
- Audit trail preserved
- Can be reactivated if needed

### Hard Delete (approval as configured)

Permanently removes all customer data:

```json
{
  "customer_id": 99,
  "deletion_reason": "Test customer cleanup - duplicate record",
  "hard_delete": true
}
```

**Use only for:**
- Test customer cleanup
- Duplicate records
- Data entry errors (never actually invoiced)

**Never use for customers with transaction history.**

---

## Bulk Import

**Capabilities:**
- Import customers from CSV files
- Sync customers from CRM systems (Salesforce, HubSpot)
- Bulk create/update during data migration
- Validate before import (dry-run mode)
- Handle duplicates automatically (skip, update, or error)

### Import Workflow

Use the `customer.import` workflow:

```javascript
submit("customer", "import", {
    "records": [
      {
        "customer_name": "Acme Corp",
        "email": "billing@acme.com",
        "phone": "+1-555-0100",
        "legal_entity_id": 13,
        "payment_terms_code": "NET_30",
        "credit_limit": 50000.00,
        "currency": "USD"
      },
      {
        "customer_name": "Tech Solutions Inc",
        "email": "ar@techsolutions.com",
        "phone": "+1-555-0200",
        "legal_entity_id": 13,
        "payment_terms_code": "NET_45",
        "credit_limit": 75000.00,
        "currency": "USD"
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

Customers are considered duplicates if:
1. **tax_id** matches (if provided), OR
2. **email** matches (case-insensitive)

### Required Fields for Import

- `customer_name` (1-255 chars)
- `email` (valid email format)

### Optional Fields for Import

- `phone` (max 50 chars)
- `legal_entity_id` (creates entity linkage)
- `payment_terms_code` (must exist)
- `credit_limit` (decimal, >= 0)
- `currency` (3-letter code)
- `customer_type` (retail, wholesale, distributor, enterprise, government, nonprofit, other)
- `tax_id` (tax identification number)
- `website` (max 255 chars)
- `billing_email` (valid email)
- `default_revenue_account_id` (must exist)
- `payment_method_id` (must exist)
- `notes` (text)
- `metadata` (JSONB)
- `is_active` (boolean, default: true)

### Validation Behavior

The importer performs comprehensive validation:
- **Field validation**: Data types, lengths, formats
- **Foreign key validation**: Verifies payment terms, entities, accounts exist
- **Business rule validation**: Credit limit >= 0, valid customer type, email format
- **Duplicate detection**: Checks tax_id and email
- **Warnings**: Large credit limits, similar customer names

### Import Response

```json
{
  "success": true,
  "import_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_records": 100,
  "imported": 95,
  "updated": 3,
  "skipped": 2,
  "errors": 0,
  "warnings": [
    {
      "row": 15,
      "field": "credit_limit",
      "message": "Large credit limit: $2,500,000.00",
      "record_identifier": "enterprise@bigcorp.com"
    }
  ],
  "created_ids": [101, 102, 103, ...],
  "updated_ids": [45, 67],
  "duration_ms": 2340
}
```

### Validate Before Importing (Dry Run)

Test your import without making changes:

```javascript
submit("customer", "import", {
    "records": [...],
    "options": {
      "validate_only": true
    }
})
```

This returns validation errors without creating any customers.

### Common Import Scenarios

**CRM Sync:**
```javascript
{
  "object_type": "customer",
  "records": customers_from_salesforce,
  "options": {
    "on_duplicate": "update",  // Update existing customers
    "stop_on_error": false     // Continue even if some fail
  }
}
```

**Data Migration:**
```javascript
{
  "object_type": "customer",
  "records": customers_from_legacy_system,
  "options": {
    "on_duplicate": "skip",    // Don't overwrite existing
    "validate_only": true,     // Test first
    "stop_on_error": true      // Stop if validation fails
  }
}
```

**See:** PLAN_IMPORT.md for import system architecture

---

## Common Scenarios

### Onboard New Customer

1. Create customer with basic info, entity, and credit terms
2. Add addresses for invoicing and shipping
3. Tag with dimensions for reporting

```json
{
  "customer_name": "New Client Inc",
  "email": "ar@newclient.com",
  "phone": "+1-555-9999",
  "legal_entity_id": 13,
  "credit_limit": 25000.00,
  "payment_terms_code": "NET_30",
  "currency": "USD"
}
```

### Volume Pricing Customer

Set up customer with multiple pricing tiers:

```json
{
  "customer_name": "Big Box Retailer",
  "email": "procurement@bigbox.com",
  "legal_entity_id": 13,
  "credit_limit": 500000.00,
  "payment_terms_code": "NET_45",
  "customer_item_pricing": [
    {
      "legal_entity_id": 13,
      "item_id": 25,
      "discount_percent": 10.00,
      "effective_from": "2025-01-01",
      "notes": "10% volume discount tier 1"
    },
    {
      "legal_entity_id": 13,
      "item_id": 25,
      "discount_percent": 15.00,
      "effective_from": "2025-01-01",
      "notes": "15% volume discount tier 2 - min qty 500"
    }
  ]
}
```

**Note:** Quantity-based tier logic is handled during invoicing based on item quantity.

### Tax-Exempt Customer

Create customer with tax exemption certificate:

```json
{
  "customer_name": "Nonprofit Foundation",
  "email": "accounting@nonprofit.org",
  "legal_entity_id": 13,
  "tax_id": "12-3456789",
  "credit_limit": 10000.00,
  "customer_tax_profiles": [
    {
      "legal_entity_id": 13,
      "tax_exempt": true,
      "exemption_type": "nonprofit",
      "exemption_certificate_number": "EX-2025-501",
      "exemption_certificate_expiry": "2025-12-31"
    }
  ]
}
```

### Credit Limit Increase

When customer requests higher credit:

```json
{
  "customer_id": 123,
  "credit_limit": 100000.00
}
```

### Customer Dimension Tagging

Tag customer with department and location for analytics:

```json
{
  "customer_id": 123,
  "customer_dimensions": [
    {
      "_action": "add",
      "legal_entity_id": 10,
      "dimension_type": "department",
      "dimension_value": "SALES"
    },
    {
      "_action": "add",
      "legal_entity_id": 10,
      "dimension_type": "location",
      "dimension_value": "NYC"
    }
  ]
}
```

**Available dimension types for customers:** `department`, `location`

### Seasonal Pricing

Add time-limited promotional pricing:

```json
{
  "customer_id": 123,
  "customer_item_pricing": [
    {
      "_action": "add",
      "legal_entity_id": 13,
      "item_id": 30,
      "price": 12.00,
      "effective_from": "2025-11-01",
      "effective_to": "2025-12-31",
      "notes": "Holiday promotion"
    }
  ]
}
```

### Customer Closure

Deactivate customer while preserving history:

```json
{
  "customer_id": 123,
  "deletion_reason": "Customer went out of business",
  "hard_delete": false
}
```

---

## Related Entities Summary

All customer-related entities require `legal_entity_id` because they are stored per-entity:

| Related Entity | Field Name Options | Required Fields |
|----------------|-------------------|-----------------|
| Addresses | `addresses` or `customer_addresses` | `legal_entity_id`, `address_line_1`, `country` |
| Dimensions | `customer_dimensions` | `legal_entity_id`, `dimension_type`, `dimension_value` |
| Tax Profiles | `customer_tax_profiles` | `legal_entity_id` |
| Item Pricing | `customer_item_pricing` | `legal_entity_id`, `item_id`, `price` |

**Key Points:**
1. **All related entities require `legal_entity_id`** - This ensures proper entity isolation
2. **The system creates linkage records automatically** - When you add related data, the system creates the `customers` linkage record (mapping master_customer to legal_entity) if it doesn't exist
3. **Related entity FKs use linkage IDs** - `customer_dimensions`, `customer_tax_profiles`, and `customer_item_pricing` store `customer_id` which references `customers.id` (the linkage table), not `master_customers.id`
4. **Dimensions use names, not IDs** - Use `dimension_type` (e.g., "department") and `dimension_value` (e.g., "SALES") instead of numeric IDs
5. **Only certain dimension types apply to customers** - Valid types: `department`, `location` (not `project` or `cost_center`)

---

## Getting Reference Data

Before constructing payloads, use search/list tools to get valid reference data:

| Data Type | How to Get | Example Values |
|-----------|-----------|----------------|
| Payment terms | `query("payment_term")` | `NET_30`, `NET_60`, `DUE_ON_RECEIPT` |
| Dimension types | `query("dimension_type")` | `department`, `location`, `project`, `cost_center` |
| Dimension values | `query("dimension_value", filters={"dimension_type_id": <id from query("dimension_type")>})` | `SALES`, `ENGINEERING`, `MARKETING` |
| Legal entities | `query("legal_entity")` | Entity IDs for customer assignment |
| Tax codes | `query("tax_code")` | Tax rates and exemption codes |
| Items | `query("item")` | Products/services for pricing tiers |
| Payment Methods | `query("payment_method")` | ACH, Wire, Check, etc. |

**Tip:** Always query reference data dynamically rather than hardcoding values, as they may vary by organization and legal entity.

**Customer-applicable dimension types:** When checking dimension types, look for types where `applies_to` contains "customer" - typically `department` and `location`.

---

## Workflow Details

For complete field specifications, validation rules, and constraints:

- customer.create (fields: `get_submissions(action="schema", object_type, operation)`) - All required and optional fields
- customer.update (fields: `get_submissions(action="schema", object_type, operation)`) - Update operations and action patterns
- customer.delete (fields: `get_submissions(action="schema", object_type, operation)`) - Soft and hard delete options

---

## Key Concepts

### Approval Workflow

All customer changes go through the workflow system:
1. Submit workflow request
2. System validates payload
3. Routes to AR Manager then Controller for approval
4. Executes after approval

### MSEO Pattern

Customers use the Master + Entity Override pattern:
- Master customer record contains organization-wide data
- Entity-specific overrides for credit limits, payment terms
- Effective views show resolved values (master + any overrides)

### Customer Pricing

- Price tiers are customer-specific and item-specific
- Support for fixed price OR percentage discount
- Effective dates for time-limited pricing
- Automatically applied during invoice creation

### Tax Profiles

- Support for tax exemptions with certificate tracking
- Expiry dates for certificate validity
- VAT/reverse charge configuration for international customers
- One profile per customer per entity

### Addresses

- Normalized address storage (separate records)
- Support for multiple address types: primary, billing, shipping, headquarters, branch, warehouse
- Entity-specific addresses (not shared across entities)
- Use both `address_type` and boolean flags for flexibility

### Related Entity Aliases

When updating related data, these field names are supported:
- `customer_addresses` - Address records
- `customer_dimensions` - Dimension assignments
- `customer_item_pricing` - Customer-specific pricing tiers
- `customer_tax_profiles` - Tax exemptions and profiles

---

## Tips & Best Practices

### 1. Metadata Usage
- Always check existing customers' metadata structure before adding new fields
- Use consistent field names across all customers
- Namespace integration data to avoid conflicts
- Document your metadata schema

### 2. Address Management
- Use `is_primary=true` for default address
- Use `is_billing=true` and `is_shipping=true` for explicit flags
- Can have multiple addresses of same type (e.g., multiple shipping locations)
- Inactive addresses remain in history but hidden from selection

### 3. Pricing Tiers
- Use `price` for fixed negotiated pricing
- Use `discount_percent` for percentage off list price
- Cannot use both on same record
- Set `effective_to` for time-limited promotions
- Pricing automatically applies during invoicing

### 4. Tax Exemptions
- Always capture certificate number and expiry date
- Set reminders to renew expiring certificates
- Use `notes` field to document exemption reason
- Check certificate validity before processing tax-exempt orders

### 5. Credit Limits
- Set conservative initial limits for new customers
- Document reason for increases in workflow comments
- Monitor AR aging to ensure limits are appropriate
- Consider payment history when adjusting limits

### 6. Dimensions
- Tag all customers with relevant dimensions at creation
- Dimensions auto-flow to invoices and reports
- Update dimensions when account ownership changes
- Use for revenue attribution and commission calculations

### 7. Query Performance
- Use `get_entity` for single customer lookup (optimized effective view)
- Use `query` with filters for finding customers
- Filter by `is_active=true` to exclude deactivated customers
- Customer number searches are faster than name searches

### 8. Data Quality
- Validate email addresses before creating customers
- Standardize phone number format across all customers
- Keep billing_email updated for automated invoice delivery
- Regular cleanup of duplicate or test customers

---

## Customer-Vendor Links

Many business counterparties act as both a customer and a vendor. The customer-vendor linking feature connects these records at the organization level.

### Key Facts

- **1:1 constraint**: Each customer links to at most one vendor, and vice versa
- **Optional field sync**: Automatically keep name, email, phone, and tax_id in sync
- **Auto-suggestions**: Find potential links based on matching tax_id, email, or name

### Link a Customer to a Vendor

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
get_entity("customer", 42)
```

The response includes a `linked_vendor` object (`linked_vendor_id`, `global_vendor_id`, `vendor_name`, `vendor_email`) when a link exists.

### Find Potential Links

There is no dedicated suggestion tool. Manually search for a matching counterparty by the customer's tax_id, email, or name, then review the results for a same-entity match:

```
query("vendor", query="<customer's tax_id>")
query("vendor", query="<customer's email>")
query("vendor", query="<customer's name>")
```

### Update Link

```
submit("customer_vendor_link", "update", {
  "master_customer_id": 42,
  "sync_direction": "customer_to_vendor",
  "sync_fields": ["name", "tax_id"]
})
```

### Remove Link

```
submit("customer_vendor_link", "delete", {
  "master_customer_id": 42,
  "deletion_reason": "No longer trading with this party"
})
```

Removing a link does **not** delete either the customer or vendor record.

### Automatic Sync on Update

When a customer is updated and a link with sync enabled exists (`customer_to_vendor` or `bidirectional`), changed fields in the `sync_fields` list are automatically propagated to the linked vendor.

---

## Query Field Reference

### Display Fields (returned by `query` / `query`)

| Field | Type | Description |
|-------|------|-------------|
| `customer_name` | string | Customer business or person name |
| `email` | string | Primary contact email |
| `phone` | string | Primary phone number |
| `customer_type` | string | Classification (retail, wholesale, etc.) |
| `payment_terms_code` | string | Default payment terms |
| `currency` | string | Default currency code |
| `tax_id` | string | Tax identification number |
| `credit_limit` | decimal | Maximum outstanding AR balance |
| `is_active` | boolean | Active status |

### Searchable Fields (text search via `query("customer", query=...)`)

| Field | Description |
|-------|-------------|
| `customer_name` | Customer name (partial match) |
| `email` | Primary email address |
| `tax_id` | Tax identification number |
| `phone` | Phone number |
| `website` | Website URL |
| `billing_email` | Billing email address |
| `notes` | Internal notes |
| `global_customer_id` | Organization-wide unique ID |

### Filter Fields (via `filters` parameter)

| Field | Type | Example |
|-------|------|---------|
| `legal_entity_id` | integer | `13` |
| `is_active` | boolean | `true` |
| `customer_type` | string | `"wholesale"` |
| `payment_terms_code` | string | `"NET_30"` |
| `tax_exempt` | boolean | `true` |
| `currency` | string | `"USD"` |

### Sort Fields (via `sort_by` parameter)

| Field | Default | Description |
|-------|---------|-------------|
| `customer_name` | Yes | Alphabetical by name |
| `global_customer_id` | | By customer ID |
| `created_at` | | Newest first |
| `updated_at` | | Recently modified |

### Related Data (returned by `get_entity` with `include_related=True`)

| Related Entity | Description |
|----------------|-------------|
| `addresses` | Billing, shipping, headquarters addresses |
| `item_pricing` | Customer-specific pricing tiers |
| `tax_profiles` | Tax exemptions and profiles |
| `dimensions` | Department, location tags |
| `linked_vendor` | Linked vendor record (if any) |

---

## End of Guide

This guide covers complete customer management including all database fields, workflows, query tools, metadata usage, and operational best practices for Claude.ai automation.
