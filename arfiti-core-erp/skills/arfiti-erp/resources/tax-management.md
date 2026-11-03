# Tax Management

## Dimension selection (branch implementation)

The branch implementation (migration 643; not deployed) selects whole booked
tax components through linked GL business lines. Reversals follow verified original
GL-line provenance. Selection is non-additive: a component can appear in more than
one dimension selection, and no departmental tax allocation is implied. Missing
link evidence makes dependent amounts unavailable with an explanation; never infer
attribution from current defaults or omit unknown components as if they were zero.

Comprehensive guide to tax calculation, compliance, and management for multi-jurisdictional tax operations.

## Available Workflows

| Workflow Type | Operation | Typical lane |
|--------------|-----------|------|
| `tax_code.create` | Create new master tax code | Green |
| `tax_code.update` | Update existing tax code | Yellow |
| `tax_code.delete` | Soft-delete tax code | Red |
| `tax_code_rate.create` | Create tax rate for date range | Green |
| `tax_code_rate.update` | Update existing tax rate | Yellow |
| `tax_code_rate.delete` | Soft-delete tax rate | Red |
| `tax_authority.create` | Create tax authority (IRS, FTB, etc.) | Green |
| `tax_authority.update` | Update tax authority details | Yellow |
| `tax_authority.delete` | Soft-delete tax authority | Red |
| `tax_jurisdiction.create` | Create tax jurisdiction (state, county, city) | Green |
| `tax_jurisdiction.update` | Update jurisdiction details | Yellow |
| `tax_jurisdiction.delete` | Soft-delete jurisdiction | Red |
| `tax_registration.create` | Register entity with tax authority | Green |
| `tax_registration.update` | Update registration details | Yellow |
| `tax_registration.delete` | Soft-delete registration | Red |
| `tax_return.create` | Create draft tax return from plugin calculations | Green |
| `tax_return.file` | Mark tax return as filed with confirmation number | Yellow |

Lanes are assigned by your organisation's workflow rules; the submit() result is authoritative.

> **Note:** Customer tax profiles are managed via `customer.create` or `customer.update` workflows with the `customer_tax_profiles` array parameter. See [Customer Management](customer-management.md) for details.

> **VAT Returns:** For the full tax return lifecycle (calculate → submit → journal entry → file → payment), see [VAT Return Management](vat-return-management.md).

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

## Available Query Tools

Use the unified query tools to find tax codes and related data:

| Tool Name | Purpose | Example |
|-----------|---------|---------|
| `query("tax_code", query, filters)` | Search tax codes | `query("tax_code", query="california")` |
| `query("tax_code", filters)` | List all tax codes | `query("tax_code", filters={"is_active": true})` |
| `get_entity("tax_code", id=X)` | Get single tax code by ID | `get_entity("tax_code", id=115)` |

**Valid filter fields for `tax_code` search/list:**

| Filter Field | Type | Description |
|-------------|------|-------------|
| `is_active` | boolean | Filter by active status |
| `is_recoverable` | boolean | Filter by input tax credit eligibility |
| `tax_type` | string | Filter by tax type (`"sales"`, `"vat"`, `"gst"`, `"use"`, `"excise"`) |

> **Note:** `legal_entity_id` is NOT a valid filter for tax codes. Tax codes are organization-wide (master records). Use entity-specific tax code overrides or tax registrations for entity-level filtering.

### Finding Tax Code IDs

**Problem**: Workflows require `tax_code_id` (integer), but you need to find valid IDs.

**Solution**: Use search or list to find tax codes first:

```python
# Option 1: Search by name or code
query("tax_code", query="california")
# Returns: [{"id": 115, "tax_code": "US_CA_TAX", "tax_name": "California Sales Tax", ...}]

# Option 2: List all active tax codes
query("tax_code", filters={"is_active": true})
# Returns: [{"id": 115, ...}, {"id": 119, ...}, ...]

# Option 3: Filter by tax type
query("tax_code", filters={"tax_type": "sales", "is_active": true})
# Returns: Only sales tax codes

# Then use the ID in your workflow:
submit("transaction", "post", {
    "transaction_type_code": "AR_INVOICE",
    "tax_code_id": 115,  # From search results above
    ...
})
```

### Common Tax Code Queries

```python
# Find US state sales taxes
query("tax_code", filters={
    "legal_entity_id": <US entity id>,   # tax codes are per entity; there is no country filter
    "tax_type": "sales",
    "is_active": true
})

# Find VAT tax codes
query("tax_code", filters={
    "tax_type": "vat",
    "is_active": true
})

# Find Canadian HST/GST
query("tax_code", query="hst")
query("tax_code", query="gst")

# Get specific tax code details
get_entity("tax_code", id=115)
# Returns full details including rates, jurisdiction, authority
```

---

## Complete Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

### Master Tax Codes Table (master_tax_codes)

| Field Name | Data Type | Required | Description | Example |
|------------|-----------|----------|-------------|---------|
| `id` | bigint | PK | System-generated ID | `123` |
| `organization_id` | integer | Yes | Organization ID | `63` |
| `tax_code` | varchar(50) | Yes | Unique tax code | `"SALES-US-CA"` |
| `tax_name` | varchar(255) | Yes | Display name | `"California Sales Tax"` |
| `tax_type` | varchar(50) | Yes | Type of tax | `"sales"`, `"use"`, `"vat"`, `"gst"`, `"excise"` |
| `calculation_method` | varchar(50) | No | Calculation method | `"rate"`, `"amount"`, `"tiered"` |
| `description` | text | No | Detailed description | `"CA state sales tax"` |
| `tax_scope` | varchar(50) | No | Applicability scope | `"goods"`, `"services"`, `"both"` |
| `jurisdiction_level` | varchar(20) | No | Jurisdiction level | `"federal"`, `"state"`, `"county"`, `"city"` |
| `country_code` | varchar(2) | No | ISO country code | `"US"`, `"CA"`, `"GB"` |
| `state_province` | varchar(50) | No | State/province | `"California"`, `"Ontario"` |
| `county` | varchar(50) | No | County name | `"Los Angeles"` |
| `city` | varchar(100) | No | City name | `"San Francisco"` |
| `postal_code` | varchar(20) | No | Postal code | `"94102"` |
| `tax_authority_name` | varchar(255) | No | Authority name | `"California Department of Tax and Fee Administration"` |
| `default_rate` | numeric(9,6) | No | Default tax rate (decimal) | `0.0725` (7.25%) |
| `default_tax_account_number` | varchar(50) | Yes | Legacy single account; the fallback for a side that has no account of its own | `"2210"` |
| `sales_account_number` | varchar(50) | No | Output-VAT account — AR invoices, credit memos. Onboarding fills it from the chart's `vat_payable` account | `"2300"` |
| `purchase_account_number` | varchar(50) | No | Input-VAT account — AP invoices. Onboarding fills it from the chart's `vat_recoverable` account, or the sales account when the chart has none | `"2310"` |
| `is_tax_inclusive` | boolean | No | Tax included in price | `false` |

A code needs BOTH sides: with one account, input VAT lands in the output-VAT account, and a default pointed at an input-VAT account "for AP" makes AR credit output VAT there (Hala Digital, 2026-09). AR refuses a code whose sales side resolves to an input-VAT account (`vat_recoverable` subtype) — set `sales_account_number` on the code.
| `is_compound` | boolean | No | Compound tax (tax on tax) | `false` |
| `is_recoverable` | boolean | No | Can claim input tax credit | `true` |
| `is_reverse_charge` | boolean | No | Reverse charge mechanism | `false` |
| `metadata` | jsonb | No | Additional structured data | `{"reporting_code": "01"}` |
| `external_reference` | varchar(100) | No | External system reference | `"AVALARA-CA-001"` |
| `is_global` | boolean | No | Available to all entities | `true` |
| `is_active` | boolean | No | Active status | `true` |
| `created_at` | timestamp | Auto | Creation timestamp | `2025-01-15 10:00:00-08` |
| `created_by` | integer | Auto | User ID who created | `30` |
| `updated_at` | timestamp | Auto | Last update timestamp | `2025-01-15 10:00:00-08` |
| `updated_by` | integer | Auto | User ID who updated | `30` |

### Tax Code Rates Table (tax_code_rates)

| Field Name | Data Type | Required | Description | Example |
|------------|-----------|----------|-------------|---------|
| `id` | bigint | PK | System-generated ID | `456` |
| `master_tax_code_id` | bigint | Yes | FK to master_tax_codes | `123` |
| `legal_entity_id` | integer | No | Entity-specific rate | `13` |
| `component_name` | varchar(100) | No | Rate component name | `"primary"`, `"surcharge"` |
| `component_type` | varchar(50) | No | Type of component | `"base"`, `"additional"`, `"surcharge"` |
| `rate` | numeric(9,6) | Yes | Tax rate (decimal) | `0.0725` (7.25%) |
| `calculation_order` | integer | No | Order for compound taxes | `1`, `2`, `3` |
| `applies_on_component` | varchar(100) | No | Base for compound tax | `"base_tax"` |
| `taxable_basis` | varchar(20) | No | What to tax | `"subtotal"`, `"total"`, `"tax"` |
| `effective_from` | date | Yes | Rate effective start date | `2025-01-01` |
| `effective_to` | date | No | Rate effective end date | `2025-12-31` |
| `tax_account_number` | varchar(50) | No | Override GL account | `"2211"` |
| `is_compound` | boolean | No | Is compound tax | `false` |
| `is_active` | boolean | No | Active status | `true` |
| `metadata` | jsonb | No | Additional data | `{"rate_change_reason": "legislation"}` |
| `created_at` | timestamp | Auto | Creation timestamp | `2025-01-15 10:00:00-08` |
| `created_by` | integer | Auto | User ID who created | `30` |
| `updated_at` | timestamp | Auto | Last update timestamp | `2025-01-15 10:00:00-08` |
| `updated_by` | integer | Auto | User ID who updated | `30` |

### Master Tax Authorities Table (master_tax_authorities)

| Field Name | Data Type | Required | Description | Example |
|------------|-----------|----------|-------------|---------|
| `id` | integer | PK | System-generated ID | `789` |
| `organization_id` | integer | Yes | Organization ID | `63` |
| `code` | varchar(50) | Yes | Unique authority code | `"IRS"`, `"CA-CDTFA"` |
| `name` | varchar(255) | Yes | Authority name | `"Internal Revenue Service"` |
| `jurisdiction_type` | varchar(50) | Yes | Type of jurisdiction | `"federal"`, `"state"`, `"county"`, `"city"` |
| `country_code` | char(2) | Yes | ISO country code | `"US"`, `"CA"`, `"GB"` |
| `region_code` | varchar(10) | No | State/province code | `"CA"`, `"ON"` |
| `authority_type` | varchar(50) | Yes | Authority type | `"tax"`, `"revenue"`, `"customs"` |
| `filing_frequency` | varchar(20) | No | How often to file | `"monthly"`, `"quarterly"`, `"annual"` |
| `website_url` | text | No | Authority website | `"https://www.irs.gov"` |
| `contact_info` | jsonb | No | Contact details | `{"phone": "800-829-1040"}` |
| `is_active` | boolean | No | Active status | `true` |
| `metadata` | jsonb | No | Additional data | `{"filing_portal": "https://..."}` |
| `created_at` | timestamp | Auto | Creation timestamp | `2025-01-15 10:00:00-08` |
| `created_by` | integer | Auto | User ID who created | `30` |
| `updated_at` | timestamp | Auto | Last update timestamp | `2025-01-15 10:00:00-08` |
| `updated_by` | integer | Auto | User ID who updated | `30` |

### Tax Jurisdictions Table (tax_jurisdictions)

| Field Name | Data Type | Required | Description | Example |
|------------|-----------|----------|-------------|---------|
| `id` | integer | PK | System-generated ID | `101` |
| `organization_id` | integer | Yes | Organization ID | `63` |
| `tax_authority_id` | integer | No | FK to master_tax_authorities | `789` |
| `parent_jurisdiction_id` | integer | No | Parent jurisdiction (for hierarchy) | `100` |
| `code` | varchar(50) | Yes | Unique jurisdiction code | `"US-CA-LA"` |
| `name` | varchar(255) | Yes | Jurisdiction name | `"Los Angeles County"` |
| `jurisdiction_type` | varchar(50) | Yes | Type of jurisdiction | `"federal"`, `"state"`, `"county"`, `"city"` |
| `country_code` | char(2) | Yes | ISO country code | `"US"` |
| `state_code` | varchar(10) | No | State/province code | `"CA"` |
| `county_code` | varchar(10) | No | County code | `"LA"` |
| `city_code` | varchar(50) | No | City code | `"LOS-ANGELES"` |
| `zip_code_pattern` | varchar(50) | No | ZIP pattern | `"90001-90899"` |
| `is_active` | boolean | No | Active status | `true` |
| `metadata` | jsonb | No | Additional data | `{"tax_district": "Central"}` |
| `created_at` | timestamp | Auto | Creation timestamp | `2025-01-15 10:00:00-08` |
| `created_by` | integer | Auto | User ID who created | `30` |
| `updated_at` | timestamp | Auto | Last update timestamp | `2025-01-15 10:00:00-08` |
| `updated_by` | integer | Auto | User ID who updated | `30` |

### Entity Tax Registrations Table (entity_tax_registrations)

| Field Name | Data Type | Required | Description | Example |
|------------|-----------|----------|-------------|---------|
| `id` | integer | PK | System-generated ID | `202` |
| `legal_entity_id` | integer | Yes | Legal entity ID | `13` |
| `tax_authority_id` | integer | No | FK to master_tax_authorities | `789` |
| `jurisdiction_id` | integer | No | FK to tax_jurisdictions | `101` |
| `registration_number` | varchar(100) | Yes | Tax registration number | `"123456789"` |
| `registration_type` | varchar(50) | Yes | Type of registration | `"sales_tax"`, `"vat"`, `"income_tax"` |
| `effective_from` | date | Yes | Registration start date | `2025-01-01` |
| `effective_to` | date | No | Registration end date | `2025-12-31` |
| `is_active` | boolean | No | Active status | `true` |
| `filing_frequency` | varchar(20) | No | Filing frequency | `"monthly"`, `"quarterly"`, `"annual"` |
| `next_filing_date` | date | No | Next filing due date | `2025-02-15` |
| `notes` | text | No | Additional notes | `"Registered for retail sales"` |
| `metadata` | jsonb | No | Additional data | `{"online_account": "active"}` |
| `created_at` | timestamp | Auto | Creation timestamp | `2025-01-15 10:00:00-08` |
| `created_by` | integer | Auto | User ID who created | `30` |
| `updated_at` | timestamp | Auto | Last update timestamp | `2025-01-15 10:00:00-08` |
| `updated_by` | integer | Auto | User ID who updated | `30` |

### Customer Tax Profiles Table (customer_tax_profiles)

> **Important:** Customer tax profiles are managed through `customer.create` and `customer.update` workflows, not standalone workflows. See [Customer Management](customer-management.md) for the correct workflow patterns.

| Field Name | Data Type | Required | Description | Example |
|------------|-----------|----------|-------------|---------|
| `id` | integer | PK | System-generated ID | `303` |
| `legal_entity_id` | integer | Yes | Legal entity ID | `13` |
| `customer_id` | integer | Yes | FK to customers | `456` |
| `tax_exempt` | boolean | No | Is tax exempt | `false` |
| `exemption_type` | varchar(50) | No | Type of exemption | `"resale"`, `"nonprofit"`, `"government"` |
| `exemption_certificate_number` | varchar(100) | No | Certificate number | `"EX-12345"` |
| `exemption_certificate_expiry` | date | No | Certificate expiry date | `2025-12-31` |
| `default_tax_code_id` | integer | No | Default tax code for customer | `123` |
| `default_jurisdiction_id` | integer | No | Default jurisdiction | `101` |
| `taxable_in_jurisdiction` | boolean | No | Is taxable in jurisdiction | `true` |
| `reverse_charge_eligible` | boolean | No | Eligible for reverse charge | `false` |
| `vat_number` | varchar(50) | No | VAT registration number | `"GB123456789"` |
| `tax_id_number` | varchar(50) | No | Tax ID | `"12-3456789"` |
| `is_active` | boolean | No | Active status | `true` |
| `notes` | text | No | Additional notes | `"Verified exempt status"` |
| `metadata` | jsonb | No | Additional data | `{"certificate_on_file": true}` |
| `created_at` | timestamp | Auto | Creation timestamp | `2025-01-15 10:00:00-08` |
| `created_by` | integer | Auto | User ID who created | `30` |
| `updated_at` | timestamp | Auto | Last update timestamp | `2025-01-15 10:00:00-08` |
| `updated_by` | integer | Auto | User ID who updated | `30` |

---

## Workflow Documentation

### Tax Code Workflows

#### Create Tax Code

Create a new master tax code for organization-wide use.

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="tax_code", operation="create")

// Step 2: Submit with discovered fields
submit("tax_code", "create", {
  tax_code: "SALES-US-CA",
  tax_name: "California Sales Tax",
  tax_type: "sales",
  calculation_method: "rate",
  description: "California state sales tax",
  tax_scope: "goods",
  jurisdiction_level: "state",
  country_code: "US",
  state_province: "California",
  default_rate: 0.0725,
  default_tax_account_number: "2210",
  is_tax_inclusive: false,
  is_compound: false,
  is_recoverable: true,
  is_reverse_charge: false,
  is_global: true,
  is_active: true
})
// Tip: Use validate_only=true to check payload before submitting
```

**Returns:**
```javascript
{
  success: true,
  tax_code_id: 123,
  workflow_id: "wf-uuid-here",
  lane: "green"
}
```

#### Update Tax Code

Update existing tax code details (not rates - use tax_code_rate workflows).

```javascript
submit("tax_code", "update", {
  tax_code: "SALES-US-CA",
  tax_name: "California Sales and Use Tax",
  description: "CA sales and use tax - updated description",
  tax_authority_name: "California Department of Tax and Fee Administration",
  metadata: {
    reporting_code: "01",
    tax_authority_website: "https://www.cdtfa.ca.gov"
  }
})
```

#### Delete Tax Code

Soft-delete tax code (sets `is_active = false`).

```javascript
submit("tax_code", "delete", {
  tax_code: "SALES-US-CA"
})
```

**Validation:**
- Cannot delete tax code used in active transactions
- Cannot delete if referenced by customer tax profiles
- Cannot delete if has active tax rates

---

### Tax Code Rate Workflows

#### Create Tax Code Rate

Create a new tax rate for a specific date range. Supports time-based rate changes and entity-specific rates.

```javascript
submit("tax_code_rate", "create", {
    master_tax_code_id: 123,
    legal_entity_id: null,  // null = applies to all entities
    component_name: "primary",
    component_type: "base",
    rate: 0.0725,
    calculation_order: 1,
    taxable_basis: "subtotal",
    effective_from: "2025-01-01",
    effective_to: null,  // null = no end date
    tax_account_number: null,  // null = use default from tax code
    is_compound: false,
    is_active: true
})
```

**Compound Tax Rate Example** (Canadian GST + PST):

```javascript
// Step 1: Create GST rate (base)
submit("tax_code_rate", "create", {
    master_tax_code_id: 456,
    component_name: "GST",
    component_type: "base",
    rate: 0.05,
    calculation_order: 1,
    taxable_basis: "subtotal",
    effective_from: "2025-01-01",
    is_compound: false
})

// Step 2: Create PST rate (compound on GST)
submit("tax_code_rate", "create", {
    master_tax_code_id: 456,
    component_name: "PST",
    component_type: "additional",
    rate: 0.07,
    calculation_order: 2,
    applies_on_component: "GST",
    taxable_basis: "total",  // Tax on subtotal + GST
    effective_from: "2025-01-01",
    is_compound: true
})
```

**Calculation:**
```
Subtotal:  $1,000.00
GST (5%):     $50.00
Subtotal + GST: $1,050.00
PST (7%):     $73.50
Total:     $1,123.50
```

#### Update Tax Code Rate

Update existing tax rate (typically to change end date when rate changes).

```javascript
submit("tax_code_rate", "update", {
    tax_code_rate_id: 789,
    effective_to: "2024-12-31",  // End old rate
    metadata: {
      superseded_by: "rate-id-999",
      change_reason: "State legislation AB-123"
    }
})
```

#### Delete Tax Code Rate

Soft-delete tax rate.

```javascript
submit("tax_code_rate", "delete", {
    tax_code_rate_id: 789
})
```

---

### Tax Authority Workflows

#### Create Tax Authority

Create a tax authority (government agency that collects taxes).

```javascript
submit("tax_authority", "create", {
    code: "CA-CDTFA",
    name: "California Department of Tax and Fee Administration",
    jurisdiction_type: "state",
    country_code: "US",
    region_code: "CA",
    authority_type: "tax",
    filing_frequency: "monthly",
    website_url: "https://www.cdtfa.ca.gov",
    contact_info: {
      phone: "800-400-7115",
      email: "cdtfa.servicedesk@cdtfa.ca.gov",
      address: "450 N Street, Sacramento, CA 95814"
    },
    is_active: true,
    metadata: {
      filing_portal: "https://onlineservices.cdtfa.ca.gov",
      payment_methods: ["ach", "check", "online"]
    }
})
```

#### Update Tax Authority

Update tax authority details.

```javascript
submit("tax_authority", "update", {
    code: "CA-CDTFA",
    filing_frequency: "quarterly",
    contact_info: {
      phone: "800-400-7115",
      email: "updated@cdtfa.ca.gov"
    },
    metadata: {
      filing_portal: "https://new-portal.cdtfa.ca.gov"
    }
})
```

#### Delete Tax Authority

Soft-delete tax authority.

```javascript
submit("tax_authority", "delete", {
    code: "CA-CDTFA"
})
```

---

### Tax Jurisdiction Workflows

#### Create Tax Jurisdiction

Create a tax jurisdiction (geographic area with specific tax rules).

```javascript
submit("tax_jurisdiction", "create", {
    tax_authority_id: 789,
    parent_jurisdiction_id: null,  // null = top-level jurisdiction
    code: "US-CA",
    name: "California",
    jurisdiction_type: "state",
    country_code: "US",
    state_code: "CA",
    is_active: true,
    metadata: {
      tax_district: "Statewide",
      special_rates: []
    }
})
```

**Hierarchical Jurisdiction Example** (County under State):

```javascript
// Parent: California state
submit("tax_jurisdiction", "create", {
    code: "US-CA",
    name: "California",
    jurisdiction_type: "state",
    country_code: "US",
    state_code: "CA"
})
// Returns: { jurisdiction_id: 100 }

// Child: Los Angeles County
submit("tax_jurisdiction", "create", {
    parent_jurisdiction_id: 100,
    code: "US-CA-LA",
    name: "Los Angeles County",
    jurisdiction_type: "county",
    country_code: "US",
    state_code: "CA",
    county_code: "LA"
})
```

#### Update Tax Jurisdiction

Update jurisdiction details.

```javascript
submit("tax_jurisdiction", "update", {
    code: "US-CA-LA",
    name: "Los Angeles County (Updated)",
    zip_code_pattern: "90001-90899,91001-91899",
    metadata: {
      tax_district: "Central LA",
      special_rates: ["tourism_tax"]
    }
})
```

#### Delete Tax Jurisdiction

Soft-delete jurisdiction.

```javascript
submit("tax_jurisdiction", "delete", {
    code: "US-CA-LA"
})
```

---

### Tax Registration Workflows

#### Create Tax Registration

Register a legal entity with a tax authority.

```javascript
submit("tax_registration", "create", {
    legal_entity_id: 13,
    tax_authority_id: 789,
    jurisdiction_id: 101,
    registration_number: "123456789",
    registration_type: "sales_tax",
    effective_from: "2025-01-01",
    effective_to: null,  // null = no expiration
    filing_frequency: "monthly",
    next_filing_date: "2025-02-15",
    is_active: true,
    notes: "Registered for retail sales in California",
    metadata: {
      online_account_id: "CA-123456",
      filing_method: "electronic",
      prepayment_required: false
    }
})
```

> **Note:** When `registration_type` is `"vat"`, the `registration_number` is automatically synced to `legal_entities.tax_id` (if not already set). This means `tax_registration.create` with a VAT type is equivalent to `legal_entity.update` with `is_vat_registered: true` and `tax_id`.

**Multiple Registration Types Example:**

```javascript
// Sales tax registration
submit("tax_registration", "create", {
    legal_entity_id: 13,
    tax_authority_id: 789,
    registration_number: "SR-123456789",
    registration_type: "sales_tax",
    filing_frequency: "monthly"
})

// Use tax registration (same authority, different type)
submit("tax_registration", "create", {
    legal_entity_id: 13,
    tax_authority_id: 789,
    registration_number: "UT-987654321",
    registration_type: "use_tax",
    filing_frequency: "quarterly"
})
```

#### Update Tax Registration

Update registration details (e.g., change filing frequency).

```javascript
submit("tax_registration", "update", {
    registration_id: 202,
    filing_frequency: "quarterly",
    next_filing_date: "2025-04-15",
    notes: "Changed to quarterly per revenue threshold",
    metadata: {
      threshold_change_date: "2025-01-01",
      new_threshold: "quarterly under $100k annual sales"
    }
})
```

#### Delete Tax Registration

Soft-delete (deactivate) registration.

```javascript
submit("tax_registration", "delete", {
    registration_id: 202
})
```

---

### Customer Tax Profile Management

Customer tax profiles are managed through the **customer.create** and **customer.update** workflows using the `customer_tax_profiles` array parameter. This ensures all customer-related data is managed atomically.

#### Create Customer With Tax Profile

When creating a new customer, include tax profiles in the `customer_tax_profiles` array:

```javascript
submit("customer", "create", {
    customer_name: "Acme Corp",
    global_customer_id: "CUST-000456",
    legal_entity_ids: [13],
    // ... other customer fields
    customer_tax_profiles: [
      {
        legal_entity_id: 13,
        tax_exempt: false,
        default_tax_code_id: 123,
        default_jurisdiction_id: 101,
        taxable_in_jurisdiction: true,
        reverse_charge_eligible: false,
        tax_id_number: "12-3456789",
        notes: "Standard taxable customer"
      }
    ]
})
```

**Tax-Exempt Customer Example** (Resale Certificate):

```javascript
submit("customer", "create", {
    customer_name: "Reseller Inc",
    global_customer_id: "CUST-000789",
    legal_entity_ids: [13],
    customer_tax_profiles: [
      {
        legal_entity_id: 13,
        tax_exempt: true,
        exemption_type: "resale",
        exemption_certificate_number: "RC-12345-CA",
        exemption_certificate_expiry: "2026-12-31",
        default_tax_code_id: null,  // null = no default tax
        taxable_in_jurisdiction: false,
        notes: "Valid resale certificate on file"
      }
    ]
})
```

**Reverse Charge VAT Example** (EU B2B):

```javascript
submit("customer", "create", {
    customer_name: "German GmbH",
    global_customer_id: "CUST-000999",
    legal_entity_ids: [13],
    customer_tax_profiles: [
      {
        legal_entity_id: 13,
        tax_exempt: false,
        default_tax_code_id: 456,  // VAT tax code
        taxable_in_jurisdiction: true,
        reverse_charge_eligible: true,
        vat_number: "DE123456789",
        notes: "EU B2B customer - reverse charge applies"
      }
    ]
})
```

#### Update Customer Tax Profile

Use `customer.update` with `_action: "update"` to modify existing tax profiles:

```javascript
submit("customer", "update", {
    global_customer_id: "CUST-000789",
    customer_tax_profiles: [
      {
        _action: "update",
        legal_entity_id: 13,  // Identifies which profile to update
        exemption_certificate_number: "RC-54321-CA",
        exemption_certificate_expiry: "2027-12-31",
        notes: "Updated resale certificate"
      }
    ]
})
```

#### Delete Customer Tax Profile

Use `customer.update` with `_action: "delete"` to soft-delete a tax profile:

```javascript
submit("customer", "update", {
    global_customer_id: "CUST-000789",
    customer_tax_profiles: [
      {
        _action: "delete",
        legal_entity_id: 13  // Identifies which profile to delete
      }
    ]
})
```

---

## Tax Calculation Methods

### Simple Tax Calculation

**Formula:** `tax_amount = taxable_amount × tax_rate`

**Example:**
```javascript
// Invoice details
const taxable_amount = 100.00;
const tax_rate = 0.07;  // 7% sales tax

// Calculation
const tax_amount = taxable_amount * tax_rate;
// tax_amount = $7.00

const total = taxable_amount + tax_amount;
// total = $107.00
```

**Database Representation:**
```javascript
// Tax code setup
submit("tax_code", "create", {
    tax_code: "SALES-US-NY",
    tax_name: "New York Sales Tax",
    tax_type: "sales",
    default_rate: 0.07,
    is_tax_inclusive: false,
    is_compound: false
})
```

---

### Compound Tax Calculation (Tax on Tax)

**Formula:**
```
Step 1: Calculate base tax
  base_tax = taxable_amount × base_tax_rate

Step 2: Calculate compound tax
  compound_taxable_basis = taxable_amount + base_tax
  compound_tax = compound_taxable_basis × compound_tax_rate

Total Tax = base_tax + compound_tax
```

**Example: Canadian GST + PST**
```javascript
// Invoice details
const taxable_amount = 1000.00;

// Step 1: GST (federal)
const gst_rate = 0.05;  // 5%
const gst_amount = taxable_amount * gst_rate;
// gst_amount = $50.00

// Step 2: PST (provincial, compound on GST)
const pst_rate = 0.07;  // 7%
const pst_taxable_basis = taxable_amount + gst_amount;
// pst_taxable_basis = $1,050.00
const pst_amount = pst_taxable_basis * pst_rate;
// pst_amount = $73.50

// Total tax
const total_tax = gst_amount + pst_amount;
// total_tax = $123.50

const invoice_total = taxable_amount + total_tax;
// invoice_total = $1,123.50
```

**Database Representation:**
```javascript
// Create master tax code
submit("tax_code", "create", {
    tax_code: "GST-PST-BC",
    tax_name: "BC GST + PST",
    tax_type: "sales",
    is_compound: true
})
// Returns: { tax_code_id: 456 }

// Create GST rate (base)
submit("tax_code_rate", "create", {
    master_tax_code_id: 456,
    component_name: "GST",
    component_type: "base",
    rate: 0.05,
    calculation_order: 1,
    taxable_basis: "subtotal",
    is_compound: false,
    effective_from: "2025-01-01"
})

// Create PST rate (compound)
submit("tax_code_rate", "create", {
    master_tax_code_id: 456,
    component_name: "PST",
    component_type: "additional",
    rate: 0.07,
    calculation_order: 2,
    applies_on_component: "GST",
    taxable_basis: "total",
    is_compound: true,
    effective_from: "2025-01-01"
})
```

---

### Tax-Inclusive Pricing

Only for prices quoted gross (consumer / retail price lists). Business
contracts, subscriptions and services are priced net, in the EU as everywhere
else, and need nothing from this section.

**Formula:** `net_amount = gross_amount / (1 + tax_rate)`

**Example: EU VAT (23%)**
```javascript
// Gross price (tax included)
const gross_amount = 123.00;
const tax_rate = 0.23;  // 23% VAT

// Back-calculate net amount
const net_amount = gross_amount / (1 + tax_rate);
// net_amount = 123.00 / 1.23 = €100.00

const tax_amount = gross_amount - net_amount;
// tax_amount = €23.00

console.log(`Net: €${net_amount.toFixed(2)}`);
console.log(`VAT: €${tax_amount.toFixed(2)}`);
console.log(`Gross: €${gross_amount.toFixed(2)}`);
// Output:
// Net: €100.00
// VAT: €23.00
// Gross: €123.00
```

**Database Representation:**
```javascript
submit("tax_code", "create", {
    tax_code: "VAT-EU-IE",
    tax_name: "Ireland VAT",
    tax_type: "vat",
    default_rate: 0.23,
    is_tax_inclusive: true,  // ← Key field
    is_compound: false
})
```

**Invoice Calculation:**
```javascript
// When creating invoice with tax-inclusive tax code
const line_amount = 123.00;  // Gross amount entered

// System calculates:
const tax_rate = 0.23;
const net_amount = line_amount / (1 + tax_rate);  // €100.00
const tax_amount = line_amount - net_amount;       // €23.00

// Journal entry:
// DR Accounts Receivable €123.00
// CR Revenue               €100.00
// CR VAT Payable           €23.00
```

---

### Reverse Charge VAT (EU B2B)

**Concept:** For B2B transactions in EU, supplier doesn't charge VAT. Customer self-assesses VAT.

**Example:**
```javascript
// German company sells to French company
const invoice_amount = 1000.00;

// Supplier (Germany) invoices:
// - Net amount: €1,000.00
// - VAT: €0.00 (reverse charge)
// - Total: €1,000.00

// Customer (France) accounting:
// DR Expense            €1,000.00
// DR Input VAT (asset)    €200.00
// CR Output VAT (liability) €200.00
// CR Accounts Payable   €1,000.00
// (Net effect: VAT-neutral, only expense is €1,000)
```

**Database Representation:**
```javascript
// Create reverse charge tax code
submit("tax_code", "create", {
    tax_code: "VAT-EU-RC",
    tax_name: "EU Reverse Charge VAT",
    tax_type: "vat",
    default_rate: 0.20,
    is_reverse_charge: true,  // ← Key field
    is_recoverable: true,
    is_active: true
})

// Set up customer for reverse charge (via customer.create or customer.update)
submit("customer", "update", {
    global_customer_id: "CUST-000999",
    customer_tax_profiles: [
      {
        _action: "add",
        legal_entity_id: 13,
        reverse_charge_eligible: true,  // ← Key field
        vat_number: "FR12345678901",
        taxable_in_jurisdiction: true
      }
    ]
})
```

**Invoice Behavior:**
```javascript
// When invoice created:
// 1. System checks: customer.reverse_charge_eligible == true
// 2. System checks: tax_code.is_reverse_charge == true
// 3. System applies: tax_amount = 0 on invoice
// 4. System notes: "Reverse charge applies - VAT self-assessment by customer"
```

---

### AP reverse-charge discounts

When a configured reverse-charge tax code applies to a negative AP line, posting
credits recoverable tax and debits output tax using positive amounts. Document,
functional and reporting debit/credit columns stay nonnegative; GL `tax_amount`
stores a magnitude. Signed document-line tax remains the declaration source in
`v_tax_lines`, so the discount still reduces the taxable base and tax. This is
posting arithmetic, not a decision about country-specific tax applicability.

This behavior applies to new AP postings only. Existing malformed negative-credit
tax rows need a separately reviewed historical repair. Do not recommend
`transaction.update` or reversal as a normalization recipe: invoice rebuild can
reject reverse-charge shapes or retranslate amounts, and reversal copies the
original amounts with debit/credit sides swapped.

## Tax Priority Waterfall

When multiple tax code sources exist, the system uses this priority order:

**Priority (Highest to Lowest):**
1. **Line-Level Override** - Explicit tax code on transaction line
2. **Item Default** - Tax code assigned to item/product
3. **Customer Default** - Tax code from customer tax profile
4. **Entity Default** - Legal entity's default tax code

**Example:**
```javascript
// Configuration:
const entity_default_tax_code = "SALES-US-CA";      // 7.25%
const customer_default_tax_code = "SALES-US-CA-LA"; // 9.50% (CA + LA county)
const item_default_tax_code = "SALES-US-FOOD";      // 0% (food exempt)
const line_override_tax_code = "SALES-US-CA";       // 7.25% (explicit override)

// Priority Resolution:
// Line override exists? → Use "SALES-US-CA" (7.25%)
// If no line override AND item default exists? → Use "SALES-US-FOOD" (0%)
// If no line override AND no item default AND customer default exists? → Use "SALES-US-CA-LA" (9.50%)
// If none of above? → Use "SALES-US-CA" (entity default 7.25%)
```

**Implementation:**
```sql
-- Tax resolution query
SELECT COALESCE(
  line.tax_code_override,           -- Priority 1
  item.default_tax_code,             -- Priority 2
  customer_profile.default_tax_code, -- Priority 3
  entity.default_tax_code            -- Priority 4
) as effective_tax_code
FROM transaction_lines line
LEFT JOIN items item ON item.id = line.item_id
LEFT JOIN customer_tax_profiles customer_profile
  ON customer_profile.customer_id = line.customer_id
LEFT JOIN legal_entities entity
  ON entity.id = line.legal_entity_id;
```

---

## Common Tax Scenarios

### Scenario 1: Multi-Jurisdictional Tax (State + County + City)

**Situation:** Selling goods in location with multiple overlapping tax jurisdictions.

**Example: Los Angeles, CA**
- State: 7.25%
- County: 1.00%
- City: 0.50%
- **Total: 8.75%**

**Implementation:**
```javascript
// Step 1: Create hierarchical jurisdictions
submit("tax_jurisdiction", "create", {
    code: "US-CA",
    name: "California",
    jurisdiction_type: "state",
    country_code: "US",
    state_code: "CA"
})
// Returns: { jurisdiction_id: 100 }

submit("tax_jurisdiction", "create", {
    parent_jurisdiction_id: 100,
    code: "US-CA-LA",
    name: "Los Angeles County",
    jurisdiction_type: "county",
    county_code: "LA"
})
// Returns: { jurisdiction_id: 101 }

submit("tax_jurisdiction", "create", {
    parent_jurisdiction_id: 101,
    code: "US-CA-LA-CITY",
    name: "City of Los Angeles",
    jurisdiction_type: "city",
    city_code: "LOS-ANGELES"
})
// Returns: { jurisdiction_id: 102 }

// Step 2: Create combined tax code
submit("tax_code", "create", {
    tax_code: "SALES-US-CA-LA-CITY",
    tax_name: "Los Angeles Combined Sales Tax",
    tax_type: "sales",
    jurisdiction_level: "city",
    country_code: "US",
    state_province: "California",
    county: "Los Angeles",
    city: "Los Angeles",
    default_rate: 0.0875,  // Combined rate
    default_tax_account_number: "2210"
})
// Returns: { tax_code_id: 789 }

// Step 3: Create component rates (for detailed reporting)
submit("tax_code_rate", "create", {
    master_tax_code_id: 789,
    component_name: "California State",
    component_type: "base",
    rate: 0.0725,
    calculation_order: 1,
    taxable_basis: "subtotal",
    effective_from: "2025-01-01",
    tax_account_number: "2210-CA-STATE"
})

submit("tax_code_rate", "create", {
    master_tax_code_id: 789,
    component_name: "LA County",
    component_type: "additional",
    rate: 0.01,
    calculation_order: 2,
    taxable_basis: "subtotal",
    effective_from: "2025-01-01",
    tax_account_number: "2210-CA-COUNTY"
})

submit("tax_code_rate", "create", {
    master_tax_code_id: 789,
    component_name: "LA City",
    component_type: "additional",
    rate: 0.005,
    calculation_order: 3,
    taxable_basis: "subtotal",
    effective_from: "2025-01-01",
    tax_account_number: "2210-CA-CITY"
})
```

**Invoice Calculation:**
```javascript
const invoice_subtotal = 1000.00;

// Component breakdown:
const ca_state_tax = 1000.00 * 0.0725; // $72.50
const la_county_tax = 1000.00 * 0.01;  // $10.00
const la_city_tax = 1000.00 * 0.005;   // $5.00

const total_tax = 72.50 + 10.00 + 5.00; // $87.50
const invoice_total = 1000.00 + 87.50;  // $1,087.50
```

---

### Scenario 2: Tax Exemption with Resale Certificate

**Situation:** Customer is tax-exempt due to valid resale certificate.

**Implementation:**
```javascript
// Step 1: Add tax profile with exemption to the existing customer
// (customer_tax_profiles is managed via customer.create/update, not a standalone object type)
submit("customer", "update", {
    customer_id: 456,
    customer_tax_profiles: [
      {
        _action: "add",
        legal_entity_id: 13,
        tax_exempt: true,
        exemption_type: "resale",
        exemption_certificate_number: "RC-CA-123456",
        exemption_certificate_expiry: "2026-12-31",
        default_tax_code_id: null,  // null = no tax
        taxable_in_jurisdiction: false,
        is_active: true,
        notes: "Valid CA resale certificate on file - wholesale customer",
        metadata: {
          certificate_file_id: "doc-uuid-here",
          verified_date: "2025-01-15",
          verified_by: 30,
          certificate_type: "CA Resale Certificate Form CDTFA-230",
          jurisdiction_scope: "California statewide"
        }
      }
    ]
})
```

**Invoice Behavior:**
```javascript
// When creating invoice for this customer:
// 1. System checks customer_tax_profile.tax_exempt == true
// 2. System applies tax_amount = 0
// 3. System adds note: "Tax exempt - Resale certificate RC-CA-123456 on file"

// Invoice:
const subtotal = 1000.00;
const tax_amount = 0.00;  // Exempt
const total = 1000.00;

// Journal entry:
// DR Accounts Receivable  $1,000.00
// CR Revenue              $1,000.00
// (No sales tax payable)
```

**Certificate Expiration Alert:**
```javascript
// Tax profiles aren't a standalone queryable entity -- they're a related
// sub-record on the customer. Pull exempt customers, then read each one's
// tax_profiles.exemption_certificate_expiry.
const exempt_customers = query("customer", filters={"tax_exempt": true})
// for each: get_entity("customer", id=X, include_related=True)
//   -> check .tax_profiles[].exemption_certificate_expiry against the 30-day window

// Alert user: "Certificate RC-CA-123456 expires 2026-12-31 - request renewal"
```

---

### Scenario 3: Tax Rate Change Mid-Period

**Situation:** State tax rate increases from 7% to 7.25% effective July 1st.

**Implementation:**
```javascript
// Step 1: End old rate on June 30th
submit("tax_code_rate", "update", {
    tax_code_rate_id: 100,
    effective_to: "2025-06-30",
    metadata: {
      superseded_by_rate_id: 101,
      change_reason: "State Bill SB-456 - rate increase"
    }
})

// Step 2: Create new rate effective July 1st
submit("tax_code_rate", "create", {
    master_tax_code_id: 123,
    component_name: "primary",
    component_type: "base",
    rate: 0.0725,  // New rate
    calculation_order: 1,
    taxable_basis: "subtotal",
    effective_from: "2025-07-01",
    effective_to: null,
    metadata: {
      supersedes_rate_id: 100,
      change_reason: "State Bill SB-456 - rate increase"
    }
})
```

**Transaction Behavior:**
```javascript
// Invoice dated June 30, 2025
const june_invoice_tax = 1000.00 * 0.07;   // $70.00 (old rate)

// Invoice dated July 1, 2025
const july_invoice_tax = 1000.00 * 0.0725; // $72.50 (new rate)

// System automatically selects correct rate based on transaction date
```

**Rate Lookup Query:**
```sql
SELECT rate
FROM tax_code_rates
WHERE master_tax_code_id = 123
  AND effective_from <= '2025-06-30'
  AND (effective_to IS NULL OR effective_to >= '2025-06-30')
  AND is_active = true
ORDER BY effective_from DESC
LIMIT 1;
-- Returns: 0.07

SELECT rate
FROM tax_code_rates
WHERE master_tax_code_id = 123
  AND effective_from <= '2025-07-01'
  AND (effective_to IS NULL OR effective_to >= '2025-07-01')
  AND is_active = true
ORDER BY effective_from DESC
LIMIT 1;
-- Returns: 0.0725
```

---

### Scenario 4: EU Reverse Charge VAT (B2B)

**Situation:** UK company sells services to German company (both VAT registered).

**Implementation:**
```javascript
// Step 1: Create reverse charge tax code
submit("tax_code", "create", {
    tax_code: "VAT-EU-RC",
    tax_name: "EU Reverse Charge VAT",
    tax_type: "vat",
    tax_scope: "services",
    default_rate: 0.20,
    is_reverse_charge: true,
    is_recoverable: true,
    default_tax_account_number: "2220",
    is_active: true
})

// Step 2: Add reverse-charge tax profile to the existing customer
submit("customer", "update", {
    customer_id: 999,
    customer_tax_profiles: [
      {
        _action: "add",
        legal_entity_id: 13,
        tax_exempt: false,
        reverse_charge_eligible: true,
        vat_number: "DE123456789",
        default_tax_code_id: null,  // Will use item/line default
        taxable_in_jurisdiction: true,
        is_active: true,
        notes: "EU B2B customer - reverse charge applies",
        metadata: {
          eu_member_state: "Germany"
        }
      }
    ]
})
```

**Invoice Behavior:**
```javascript
// UK company invoices German company
const service_amount = 10000.00;

// Supplier (UK) invoice:
// - Net amount: €10,000.00
// - VAT: €0.00 (reverse charge notation)
// - Total: €10,000.00

// Invoice note: "VAT reverse charge applies - Customer to self-assess VAT under Article 196 EU VAT Directive"

// Supplier accounting (UK):
// DR Accounts Receivable  €10,000.00
// CR Revenue              €10,000.00
// (No output VAT)

// Customer accounting (Germany):
// DR Expense              €10,000.00
// DR Input VAT (asset)     €2,000.00  // 20% self-assessed
// CR Output VAT (liability) €2,000.00  // 20% self-assessed
// CR Accounts Payable     €10,000.00
// (VAT-neutral, net expense €10,000)
```

**VAT Number Validation:**
```javascript
// There is no VAT-number verification tool in ARTIFI (no VIES or national
// register lookup). Check the number with the official service yourself, keep
// the evidence (e.g. the VIES confirmation PDF as a document), and tell the
// user what you checked. Metadata keys claiming a validation
// (vat_validation_status, validation_source, vies_*) are dropped on save:
// nothing verified them.

```

---

### Scenario 5: Compound Tax (Canadian GST + PST)

**Situation:** Canadian province with PST calculated on subtotal + GST.

**Implementation:**
```javascript
// Step 1: Create master tax code
submit("tax_code", "create", {
    tax_code: "GST-PST-BC",
    tax_name: "British Columbia GST + PST",
    tax_type: "sales",
    jurisdiction_level: "state",
    country_code: "CA",
    state_province: "British Columbia",
    is_compound: true,
    default_tax_account_number: "2210"
})
// Returns: { tax_code_id: 456 }

// Step 2: Create GST rate (federal base tax)
submit("tax_code_rate", "create", {
    master_tax_code_id: 456,
    component_name: "GST",
    component_type: "base",
    rate: 0.05,
    calculation_order: 1,
    taxable_basis: "subtotal",
    effective_from: "2025-01-01",
    is_compound: false,
    tax_account_number: "2210-GST"
})

// Step 3: Create PST rate (provincial compound tax)
submit("tax_code_rate", "create", {
    master_tax_code_id: 456,
    component_name: "PST",
    component_type: "additional",
    rate: 0.07,
    calculation_order: 2,
    applies_on_component: "GST",
    taxable_basis: "total",  // Tax on subtotal + GST
    effective_from: "2025-01-01",
    is_compound: true,
    tax_account_number: "2210-PST"
})
```

**Invoice Calculation:**
```javascript
const subtotal = 1000.00;

// Step 1: Calculate GST (base)
const gst_rate = 0.05;
const gst_amount = subtotal * gst_rate;
// gst_amount = $50.00

// Step 2: Calculate PST (compound)
const pst_rate = 0.07;
const pst_taxable_basis = subtotal + gst_amount;
// pst_taxable_basis = $1,050.00
const pst_amount = pst_taxable_basis * pst_rate;
// pst_amount = $73.50

// Total
const total_tax = gst_amount + pst_amount;
// total_tax = $123.50
const invoice_total = subtotal + total_tax;
// invoice_total = $1,123.50

// Invoice breakdown:
console.log(`Subtotal:     $${subtotal.toFixed(2)}`);
console.log(`GST (5%):     $${gst_amount.toFixed(2)}`);
console.log(`PST (7%):     $${pst_amount.toFixed(2)}`);
console.log(`Total:        $${invoice_total.toFixed(2)}`);
// Output:
// Subtotal:     $1,000.00
// GST (5%):     $50.00
// PST (7%):     $73.50
// Total:        $1,123.50
```

**Journal Entry:**
```javascript
// DR Accounts Receivable  $1,123.50
// CR Revenue              $1,000.00
// CR GST Payable            $50.00
// CR PST Payable            $73.50
```

---

### Scenario 6: Tax-Inclusive Pricing (EU VAT)

**Situation:** A consumer price list where the displayed price includes VAT. (A B2B contract or subscription is priced net — do not use an inclusive code for it.)

**Implementation:**
```javascript
// Step 1: Create VAT tax code
submit("tax_code", "create", {
    tax_code: "VAT-EU-IE",
    tax_name: "Ireland VAT Standard Rate",
    tax_type: "vat",
    default_rate: 0.23,
    is_tax_inclusive: true,  // ← Key field
    is_recoverable: true,
    default_tax_account_number: "2220",
    country_code: "IE",
    is_active: true
})
```

**Invoice Calculation:**
```javascript
// Displayed price (tax-inclusive)
const gross_price = 123.00;
const tax_rate = 0.23;

// Back-calculate net amount
const net_amount = gross_price / (1 + tax_rate);
// net_amount = 123.00 / 1.23 = €100.00

const vat_amount = gross_price - net_amount;
// vat_amount = €23.00

// Invoice:
console.log(`Net Amount:   €${net_amount.toFixed(2)}`);
console.log(`VAT (23%):    €${vat_amount.toFixed(2)}`);
console.log(`Gross Total:  €${gross_price.toFixed(2)}`);
// Output:
// Net Amount:   €100.00
// VAT (23%):    €23.00
// Gross Total:  €123.00
```

**Journal Entry:**
```javascript
// DR Accounts Receivable  €123.00
// CR Revenue              €100.00
// CR VAT Payable          €23.00
```

**Line Item Entry:**
```javascript
// User enters gross amount on invoice line
const line_gross_amount = 123.00;

// System calculates:
const line_net = line_gross_amount / (1 + 0.23);  // €100.00
const line_vat = line_gross_amount - line_net;     // €23.00

// Store in database:
// {
//   line_amount: 100.00,      // Net amount (stored)
//   tax_amount: 23.00,        // VAT (stored)
//   gross_amount: 123.00,     // Gross (calculated)
//   tax_inclusive: true       // Flag
// }
```

---

## Query Examples

### Get Tax Code

Find a tax code by its code (text search), then read it by ID.

```javascript
query("tax_code", query="SALES-US-CA", filters={legal_entity_id: 13})
get_entity("tax_code", id=123)

// Returns fields such as:
// { tax_code: "SALES-US-CA", tax_name: "California Sales Tax", default_rate: 0.0725,
//   is_tax_inclusive: false, is_recoverable: ..., is_active: true }
```

### List Tax Codes

Tax codes are read per legal entity. Filters: `legal_entity_id`, `is_active`, `tax_type`, `is_recoverable` (there is no country filter).

```javascript
query("tax_code", filters={legal_entity_id: 13, is_active: true})
query("tax_code", filters={legal_entity_id: 13, tax_type: "vat", is_active: true})
```

### Rates and calculation

There is no separate tool for a tax code's rate history or for calculating tax on a line. The rate in force is applied when a transaction is posted through `submit("transaction", "post", ...)`; validate a line first with `submit(..., validate_only=true)`, and read the posted `tax_amount` from `get_entity("transaction", id=...)`.

---

## Best Practices

### Tax Code Naming Convention

Use consistent naming pattern: `{TYPE}-{COUNTRY}-{STATE}-{ADDITIONAL}`

**Examples:**
- `SALES-US-CA` - California sales tax
- `SALES-US-NY-NYC` - New York City sales tax
- `VAT-EU-IE` - Ireland VAT
- `GST-PST-BC` - British Columbia GST+PST
- `USE-US-CA` - California use tax
- `VAT-EU-RC` - EU reverse charge VAT

### Tax Rate Date Ranges

Always use effective date ranges to handle rate changes:

```javascript
// DO: End old rate, create new rate
submit("tax_code_rate", "update", {
    tax_code_rate_id: 100,
    effective_to: "2025-06-30"  // End old rate
})

submit("tax_code_rate", "create", {
    master_tax_code_id: 123,
    rate: 0.0725,  // New rate
    effective_from: "2025-07-01"
})

// DON'T: Update existing rate in place
// This loses historical rate information
```

### Tax Exemption Certificates

Always track exemption certificates with expiration:

```javascript
submit("customer", "update", {
    customer_id: 456,
    customer_tax_profiles: [
      {
        _action: "add",
        legal_entity_id: 13,
        tax_exempt: true,
        exemption_certificate_number: "RC-CA-123456",
        exemption_certificate_expiry: "2026-12-31",  // ← Required!
        metadata: {
          certificate_file_id: "doc-uuid",
          verified_date: "2025-01-15",
          verified_by: 30
        }
      }
    ]
})

// Set up alerts for expiring certificates (30 days before)
```

### Compound Tax Setup

Use `calculation_order` and `applies_on_component` for clarity:

```javascript
// Base tax (order 1)
submit("tax_code_rate", "create", {
    component_name: "GST",
    rate: 0.05,
    calculation_order: 1,
    taxable_basis: "subtotal",
    is_compound: false
})

// Compound tax (order 2, applies on GST)
submit("tax_code_rate", "create", {
    component_name: "PST",
    rate: 0.07,
    calculation_order: 2,
    applies_on_component: "GST",
    taxable_basis: "total",  // subtotal + GST
    is_compound: true
})
```

### Tax Authority Registration

Always track registration with filing frequency:

```javascript
submit("tax_registration", "create", {
    legal_entity_id: 13,
    tax_authority_id: 789,
    registration_number: "123456789",
    registration_type: "sales_tax",
    filing_frequency: "monthly",  // ← Important for compliance
    next_filing_date: "2025-02-15",
    metadata: {
      online_account_id: "CA-123456",
      filing_method: "electronic"
    }
})
```

### Multi-Jurisdiction Tax

Break down component rates for accurate reporting:

```javascript
// Combined rate (for quick calculation)
submit("tax_code", "create", {
    tax_code: "SALES-US-CA-LA-CITY",
    default_rate: 0.0875  // Combined: 7.25% + 1% + 0.5%
})

// Component rates (for detailed reporting)
submit("tax_code_rate", "create", {
    component_name: "California State",
    rate: 0.0725,
    tax_account_number: "2210-CA-STATE"  // Separate GL account
})

submit("tax_code_rate", "create", {
    component_name: "LA County",
    rate: 0.01,
    tax_account_number: "2210-CA-COUNTY"  // Separate GL account
})
```

### Tax-Inclusive Pricing

`is_tax_inclusive` says whether the prices you enter already contain the tax.
It follows how prices are quoted, not the country:

```javascript
// Business-to-business (contracts, SaaS, services): prices are NET, tax on top.
// This is the default — leave the flag off, in the EU as everywhere else.
submit("tax_code", "create", {
    tax_code: "VAT-EE-STD",
    default_rate: 24
    // is_tax_inclusive defaults to false
})

// Consumer / retail price lists where the shelf price includes VAT:
submit("tax_code", "create", {
    tax_code: "VAT-EE-RETAIL",
    default_rate: 24,
    is_tax_inclusive: true  // ← only when the entered amounts are gross
})
```

Resolution when an invoice line is posted: an explicit `is_tax_inclusive` on
the line wins, otherwise the tax code's flag, otherwise net. The billing run
never sets the flag itself: recurring contract prices are net unless the tax
code says otherwise.

### Reverse Charge VAT

Set up both tax code and customer profile:

```javascript
// Tax code with reverse charge flag
submit("tax_code", "create", {
    tax_code: "VAT-EU-RC",
    is_reverse_charge: true,
    is_recoverable: true
})

// Customer profile with VAT number
submit("customer", "update", {
    customer_id: 999,
    customer_tax_profiles: [
      {
        _action: "add",
        legal_entity_id: 13,
        reverse_charge_eligible: true,
        vat_number: "DE123456789",  // ← Required
      }
    ]
})
```

---

## Common Pitfalls

### ❌ Pitfall 1: Updating Tax Rate In Place

**Wrong:**
```javascript
// DON'T: Update existing rate
submit("tax_code_rate", "update", {
    tax_code_rate_id: 100,
    rate: 0.0725  // Changed from 0.07
})
// Problem: Loses historical rate, affects past transactions
```

**Correct:**
```javascript
// DO: End old rate, create new rate
submit("tax_code_rate", "update", {
    tax_code_rate_id: 100,
    effective_to: "2025-06-30"
})

submit("tax_code_rate", "create", {
    master_tax_code_id: 123,
    rate: 0.0725,
    effective_from: "2025-07-01"
})
// Result: Historical transactions use 0.07, new transactions use 0.0725
```

---

### ❌ Pitfall 2: Marking a B2B Tax Code Tax-Inclusive

**Wrong:**
```javascript
// DON'T: treat "EU" as "prices include VAT"
submit("tax_code", "create", {
    tax_code: "VAT-EE-STD",
    default_rate: 24,
    is_tax_inclusive: true
})
// Problem: a €7/user contract billed as 72 × €7 = €504.00 GROSS
//   → net €406.45 + VAT €97.55. The customer is under-billed by 24%.
```

**Correct:**
```javascript
// DO: B2B prices are net; VAT goes on top
submit("tax_code", "create", {
    tax_code: "VAT-EE-STD",
    default_rate: 24
    // is_tax_inclusive stays false
})
// Result: 72 × €7 = €504.00 net + €120.96 VAT = €624.96 (correct!)
```

Set `is_tax_inclusive: true` only for a code used on consumer price lists
where the amounts you enter are the shelf price including VAT.

---

### ❌ Pitfall 3: Compound Tax Wrong Order

**Wrong:**
```javascript
// DON'T: Create compound tax without calculation_order
submit("tax_code_rate", "create", {
    component_name: "PST",
    rate: 0.07,
    is_compound: true
    // Missing: calculation_order, applies_on_component
})
// Problem: System doesn't know which tax to compound on
```

**Correct:**
```javascript
// DO: Specify calculation_order and applies_on_component
submit("tax_code_rate", "create", {
    component_name: "PST",
    rate: 0.07,
    calculation_order: 2,  // ← After GST (order 1)
    applies_on_component: "GST",  // ← Tax on GST
    taxable_basis: "total",  // ← Subtotal + GST
    is_compound: true
})
```

---

### ❌ Pitfall 4: Missing Exemption Certificate Expiry

**Wrong:**
```javascript
// DON'T: Create exemption without expiry
submit("customer", "update", {
    customer_id: 456,
    customer_tax_profiles: [
      {
        _action: "add",
        legal_entity_id: 13,
        tax_exempt: true,
        exemption_certificate_number: "RC-CA-123456"
        // Missing: exemption_certificate_expiry
      }
    ]
})
// Problem: No alert when certificate expires
```

**Correct:**
```javascript
// DO: Always set expiry date
submit("customer", "update", {
    customer_id: 456,
    customer_tax_profiles: [
      {
        _action: "add",
        legal_entity_id: 13,
        tax_exempt: true,
        exemption_certificate_number: "RC-CA-123456",
        exemption_certificate_expiry: "2026-12-31",  // ← Required
        metadata: {
          certificate_file_id: "doc-uuid",
          alert_days_before_expiry: 30
        }
      }
    ]
})
```

---

### ❌ Pitfall 5: Reverse Charge Without VAT Number Validation

**Wrong:**
```javascript
// DON'T: Enable reverse charge without validating VAT number
submit("customer", "update", {
    customer_id: 999,
    customer_tax_profiles: [
      {
        _action: "add",
        legal_entity_id: 13,
        reverse_charge_eligible: true,
        vat_number: "DE123456789"  // Not validated!
      }
    ]
})
// Problem: Invalid VAT number = compliance risk
```

**Correct:**
```javascript
// DO: confirm the VAT number with the official service first.
// There is no VAT-number verification tool in ARTIFI (no VIES or national
// register lookup). Check the number with the official service yourself, keep
// the evidence (e.g. the VIES confirmation PDF as a document), and tell the
// user what you checked. Metadata keys claiming a validation
// (vat_validation_status, validation_source, vies_*) are dropped on save:
// nothing verified them.

submit("customer", "update", {
    customer_id: 999,
    customer_tax_profiles: [
      {
        _action: "add",
        legal_entity_id: 13,
        reverse_charge_eligible: true,
        vat_number: "DE123456789",
      }
    ]
})
```

---

### ❌ Pitfall 6: Deleting Tax Code Instead of Deactivating

**Wrong:**
```javascript
// DON'T: Hard delete tax code
submit("tax_code", "delete", {
  tax_code: "SALES-US-CA"
})
// Problem: Breaks historical transactions
```

**Correct:**
```javascript
// DO: Soft delete (deactivate)
submit("tax_code", "update", {
    tax_code: "SALES-US-CA",
    is_active: false  // ← Soft delete
})
// Result: Historical transactions still reference valid code
```

---

## Getting Reference Data

### Get Organization Tax Codes

**CORRECT - Use dynamic search:**
```javascript
const tax_codes = query("tax_code", query="", filters={"is_active": true})
```

**DO NOT - Use static references:**
```javascript
// ❌ WRONG: Don't hardcode tax code IDs
const tax_code_id = 123;  // Will break if data changes
```

---

### Get Tax Authorities

**CORRECT - Use dynamic search:**
```javascript
const authorities = query("tax_authority", query="", filters={"country_code": "US", "is_active": true})
```

---

### Get Customer Tax Profiles

**CORRECT - Use get or search:**
```javascript
// Tax profiles aren't a standalone entity -- they're a related sub-record
// on the customer. Get a specific customer's profile:
const customer = await get_entity("customer", id=456, include_related=True);
// customer.tax_profiles has the tax_exempt / exemption_certificate fields

// Search customers by tax-exempt status
const exempt_customers = query("customer",
  filters={"legal_entity_id": 13, "tax_exempt": true, "is_active": true}
)
```

---

## Quick Reference

### Tax Types

| Tax Type | Description | Example Regions |
|----------|-------------|-----------------|
| `sales` | Sales tax (US, Canada) | California, Texas, Ontario |
| `use` | Use tax (untaxed purchases) | US states |
| `vat` | Value-Added Tax | EU, UK, Australia |
| `gst` | Goods & Services Tax | Canada, Australia, India |
| `excise` | Excise tax (specific goods) | Alcohol, tobacco, fuel |
| `withholding` | Withholding tax | International payments |

### Jurisdiction Levels

| Level | Description | Example |
|-------|-------------|---------|
| `federal` | National level | US Federal, Canadian GST |
| `state` | State/province | California, Ontario |
| `county` | County/region | Los Angeles County |
| `city` | City/municipal | San Francisco, Toronto |

### Exemption Types

| Type | Description | Certificate Required |
|------|-------------|---------------------|
| `resale` | Reselling goods | Yes |
| `nonprofit` | Non-profit organization | Yes |
| `government` | Government entity | Yes |
| `export` | International export | Yes |
| `agricultural` | Agricultural use | Yes |
| `manufacturing` | Manufacturing inputs | Yes |

### Registration Types

| Type | Description | Filing Frequency |
|------|-------------|------------------|
| `sales_tax` | Sales tax registration | Monthly/Quarterly |
| `use_tax` | Use tax registration | Quarterly/Annual |
| `vat` | VAT registration | Monthly/Quarterly |
| `income_tax` | Income tax | Annual |
| `payroll_tax` | Payroll withholding | Monthly |

---

## Entity VAT Registration

VAT registration status determines how the transaction executor handles tax posting for each legal entity. Entities without active VAT registration have different tax behavior (tax rolled into expense lines, reverse charge blocked).

### Checking VAT Status

VAT registration is NOT a column on `legal_entities`. It lives in `entity_tax_registrations`. To check VAT status, look at active registrations for the entity:

```
query("tax_registration", filters={"legal_entity_id": 13, "is_active": true, "registration_type": "vat"})
```

For the transaction date, require an active `vat` registration with
`effective_from <= transaction_date` and no `effective_to` before that date.
An active registration today alone is insufficient for a historical deduction.

### Enabling VAT Registration

Use `submit("tax_registration", "create", ...)` — NOT `legal_entity.update` (there is no `is_vat_registered` field on the legal entity).

```
submit("tax_registration", "create", {
    "legal_entity_id": 13,
    "registration_type": "vat",
    "registration_number": "IE1234567T",
    "effective_from": "2026-04-01"
})
```

If the user is creating a new entity via `add_entity`, pass `is_vat_registered=true` + `tax_id="..."` at creation time — `add_entity` will insert the `entity_tax_registrations` row for you.

### Disabling VAT Registration

Soft-deactivate the active registration:

```
submit("tax_registration", "update", {
    "registration_id": <id>,
    "is_active": false,
    "effective_to": "2026-04-24"
})
```

### Non-VAT Entity Behavior

| Transaction Type | Tax Posting Change |
|-----------------|-------------------|
| AP Invoice | Tax rolled into expense GL line (no separate Input VAT) |
| AR Invoice | Tax posting skipped — non-VAT seller cannot charge VAT |
| Journal Entry | Tax rolled into original GL line |

**Reverse charge tax codes are blocked** for non-VAT entities (validation error).

The VAT check uses the **transaction date**, so backdated entries respect historical VAT status.

See [Entity Management](entity-management.md) for the full `submit("legal_entity", "update", ...)` docs (note: VAT is managed via `tax_registration`, not via `legal_entity.update`).

---

## Key Takeaways

1. **Tax Codes are Master Records**: Use MSEO pattern (master + entity overrides)

2. **Tax Rates Have Date Ranges**: Always use effective_from/effective_to for rate changes

3. **Priority Waterfall**: Line override → Item default → Customer default → Entity default

4. **Compound Taxes Need Order**: Use calculation_order and applies_on_component

5. **Tax-Inclusive Pricing**: Prices are net by default (B2B everywhere, EU included); set is_tax_inclusive only on codes for consumer price lists quoted gross

6. **Reverse Charge Requires VAT Number**: Validate VAT number before enabling

7. **Exemption Certificates Expire**: Track expiry dates and alert before expiration

8. **Soft Delete Only**: Never hard-delete tax codes (breaks historical transactions)

9. **Component Rates for Reporting**: Break down multi-jurisdiction tax into components

10. **Registration Tracking**: Track tax registrations with filing frequency and due dates

11. **VAT Registration**: Managed via `submit("tax_registration", "create" | "update", ...)` (NOT `legal_entity.update`) — affects tax posting behavior for the entity

---

**Version**: 1.1
**Last Updated**: 2026-04-24
**Related Resources**: [Transaction Processing](transaction-processing.md), [Multi-Currency](multi-currency-management.md), [Accounts](accounts-management.md), [Entity Management](entity-management.md)

## Dated tax evidence and VAT control reconciliation

VAT reports and filing readers use the canonical tax-line view. Effective VAT
registration intervals govern deductible input; an active registration today is
not evidence of registration on the historical transaction date. Review
`registration_exceptions` rather than silently claiming pre-registration input tax.
Zero-rated sales remain taxable-turnover evidence even when their tax amount is zero.

AP credits reduce input tax and reversals contribute on their own posting dates;
originals remain in earlier periods. Use booked functional currency and preserve
source line rounding. Missing conversion evidence must be investigated rather than
replaced by today's FX rate. A filed return alone does not prove the VAT control
balance: the close gate compares it with a retained period-end authority account
statement covering the configured VAT control accounts.

### Legacy currency evidence and reverse-charge totals

A legacy document with a missing header functional amount can use rate 1 only
when its document currency equals its recorded functional currency (or the entity's
functional currency when that field is absent). Foreign-currency evidence without
a recorded conversion basis remains uncertified; never substitute today's FX.

Reverse-charge tax contributes input and output rows. Keep both directions for
VAT/worksheet presentation, but count its base once in an undirected taxable total.
Sales-tax collected totals count output tax rather than adding input and output.

### Manual journal tax-account routing

**Journal-entry tax routing:** automatic tax on `expense` and `cogs` lines uses
`purchase_account_number`; `revenue` lines use `sales_account_number`. Each falls
back only to the effective `default_tax_account_number`, never to the opposite
side. The account type determines the side even for a reversing line: a credit
to an expense reverses input VAT. Entity tax-code overrides apply. Other account
types retain the configured default; balance-sheet classification alone does
not identify a purchase or sale. For those adjustments, select a tax code with
the intended default or enter the reviewed tax lines explicitly. Missing or
inactive effective codes and missing, inactive or header tax accounts refuse
the journal atomically. This changes new postings only; it does not reclassify
historical journals or add reverse-charge/non-recoverable-tax support.
