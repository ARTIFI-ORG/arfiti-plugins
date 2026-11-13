# Item Management

> **MSEO release contract:** AP/AR business lines store the validated master item ID directly. Master-only items and an item with overrides in two entities are supported; never resolve an item with an unscoped scalar `items WHERE id = ...` query. See the dimensions-management resource for assignment, approval and compatibility rules.

**Primary Use:** Managing product and service catalog (SKUs) for sales and purchasing

Items are the products and services your business sells or purchases. The workflow system ensures proper authorization, audit trails, and risk-based approvals for all item operations.

**What you can do:**
- Create new items (products, services) with GL account mappings and pricing
- Update item information (prices, GL accounts, descriptions, tiers)
- Query item data (single item, search/filter)
- Deactivate items (soft delete) or remove test data (hard delete)
- Bulk import items from CSV/templates

**Available Workflows:**

| Workflow | Purpose | When to Use |
|----------|---------|-------------|
| `item.create` | Create new item | Adding products or services to catalog |
| `item.update` | Update item data | Change pricing, GL accounts, descriptions |
| `item.delete` | Deactivate item | Item discontinued or test cleanup |
| `item.import` | Bulk import items | Chart of accounts templates, data migration |

**Available Query Tools:**

| Tool | Purpose |
|------|---------|
| `get_entity("item", id=X)` | Get single item (includes prices, pricing tiers by default) |
| `query("item", filters)` | List items with filters and pagination |
| `query("item", query, filters)` | Search/filter items by text |
| `query("item", filters, limit=1)` | Count matching items (use `total_count` from response) |

**Key notes:**
- `get_entity` defaults to `include_related=True` — returns item prices and pricing tiers automatically
- Search/list results now include: `category`, `unit_of_measure`, `cost_price`, `is_taxable` alongside the basic fields

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

---

## Complete Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

### Master Item Fields (master_items table)

**Required Fields:**
- `item_number` (string, 1-100 chars, unique per organization) - Item number/SKU (e.g., "WIDGET-001", "SERV-HR-001")
- `item_name` (string, 1-255 chars) - Item display name (e.g., "Premium Wireless Earbuds")

**Optional Classification:**
- `item_type` (enum) - Type of item:
  - `revenue_product` - Physical goods sold (has inventory)
  - `revenue_service` - Services provided (no inventory)
  - `expense_product` - Physical goods purchased (has inventory)
  - `expense_service` - Services purchased (no inventory)
- `category` (string, max 100 chars) - Item category for grouping:
  - `INVENTORY` - Physical goods held in inventory for resale
  - `SALES` - Items sold to customers
  - `SERVICES` - Professional services and consulting
  - `SOFTWARE` - Software licenses and digital downloads
  - `SUBSCRIPTION` - Recurring subscription-based products
  - `RAW_MATERIALS` - Components for manufacturing
  - `FINISHED_GOODS` - Completed manufactured products
  - `NON_INVENTORY` - Purchases not tracked in inventory
  - `LABOR` - Labor and contractor services
  - `SHIPPING` - Shipping, freight, and delivery
  - `OTHER` - Miscellaneous items
- `description` (text, max 2000 chars) - Detailed item description

**Pricing Defaults:**
- `unit_of_measure` (string, max 20 chars, default: `EA`) - Unit (EA, lb, hr, kg, gal, L, DZ, DAY, etc.)
- `unit_price` (decimal, >= 0) - Default selling price
- `cost_price` (decimal, >= 0) - Default cost price
- `is_taxable` (boolean, default: true) - Whether item is taxable by default

**GL Account Mappings:**
- `revenue_account_number` (string, max 50 chars) - Revenue GL account (AR side)
- `expense_account_number` (string, max 50 chars) - Expense GL account (AP side)
- `asset_account_number` (string, max 50 chars) - Inventory asset GL account
- `cogs_account_number` (string, max 50 chars) - Cost of Goods Sold GL account
- `tax_code` (string, max 50 chars) - Default tax code (SALES_TAX, VAT, EXEMPT, etc.)

**Scope & Visibility (unified MSEO contract):**
`item.create` is `SCOPE_MODE='fanout'`. The combination of `is_global`, `legal_entity_id`, and `legal_entity_ids` resolves to a list of target entities — the executor writes a master row plus one `items` row per target entity.

- `is_global` (boolean, default: `true`) — when `true`, fans out to EVERY active legal_entity (one `items` row each, dependents written per entity). When `false`, entity targets come from the IDs.
- `legal_entity_id` (integer, optional) — single-entity attach. Implies `is_global=false`. Result: master + ONE `items` row.
- `legal_entity_ids` (integer[], optional) — multi-entity attach. Implies `is_global=false`. Result: master + N `items` rows.
- **No flag, no IDs** → defaults to `is_global=true` → fanout (legacy behaviour preserved).
- **`is_global=false` + no IDs** → master only (template); `item_prices`, `item_pricing_tiers`, `item_default_taxes` will be REJECTED loudly because they need an entity row to land in.

Always pick the shape that matches user intent. If they want "this item in entity X", pass `legal_entity_id=X`. If they want "this item everywhere", omit both flags or pass `is_global=true`. See GUIDE_MSEO_PATTERN.md for the full contract.

- `is_active` (boolean, default: true) - Active status (soft delete flag)

**System & Audit:**
- `global_item_id` (string, auto-generated) - Organization-wide unique identifier (ITEM-XXXXXX format)
- `metadata` (jsonb) - Custom JSON metadata for extensions
- `created_at`, `updated_at` (timestamp) - Audit trail timestamps
- `created_by`, `updated_by` (integer) - User IDs for audit trail

**Total**: 24 fields in master_items table

### Entity Override Fields (items table)

Entity overrides allow per-entity customization without affecting other entities. All override fields end with `_override` suffix.

**Customizable Fields (all optional):**
- `item_name_override` (string, max 255 chars) - Entity-specific item name
- `description_override` (text) - Entity-specific description
- `item_type_override` (enum) - Entity-specific item type
- `unit_of_measure_override` (string, max 20 chars) - Entity-specific unit
- `unit_price_override` (decimal) - Entity-specific default price
- `cost_price_override` (decimal) - Entity-specific default cost
- `is_taxable_override` (boolean) - Entity-specific tax status
- `revenue_account_number_override` (string, max 50 chars) - Entity-specific revenue account
- `expense_account_number_override` (string, max 50 chars) - Entity-specific expense account
- `asset_account_number_override` (string, max 50 chars) - Entity-specific asset account
- `cogs_account_number_override` (string, max 50 chars) - Entity-specific COGS account
- `tax_code_override` (string, max 50 chars) - Entity-specific tax code
- `category_override` (string, max 100 chars) - Entity-specific category
- `is_active_override` (boolean) - Entity-specific active status (hide from entity)
- `metadata_override` (jsonb) - Entity-specific metadata

**System Fields:**
- `master_item_id` (bigint, required) - FK to master_items
- `legal_entity_id` (integer, required) - FK to legal_entities
- `item_number` (string) - Denormalized for quick lookups
- `created_at`, `updated_at` (timestamp) - Audit trail
- `created_by`, `updated_by` (integer) - User IDs

**Total**: 23 fields in items table (15 override fields + 8 system fields)

### Item Prices Fields (item_prices table)

Entity-specific pricing with multi-currency support (NOT part of MSEO pattern).

**Required Fields:**
- `master_item_id` (bigint) - FK to master_items
- `legal_entity_id` (integer) - FK to legal_entities
- `currency` (string, 3 chars, default: USD) - Currency code (USD, EUR, GBP, etc.)
- `effective_from` (date, default: CURRENT_DATE) - Price effective start date

**Optional Pricing:**
- `unit_price` (decimal, >= 0) - Selling price in this currency
- `cost_price` (decimal, >= 0) - Cost price in this currency
- `effective_to` (date) - Price expiration date (null = no expiration)

**System Fields:**
- `created_at`, `updated_at` (timestamp) - Audit trail
- `created_by`, `updated_by` (integer) - User IDs

**Total**: 12 fields in item_prices table

### Item Pricing Tiers Fields (item_pricing_tiers table)

Volume-based pricing (entity-specific, not global).

**Required Fields:**
- `legal_entity_id` (integer) - FK to legal_entities
- `item_id` (bigint) - FK to items (entity-level linkage, not master)
- `tier_name` (string, max 100 chars) - Tier description (e.g., "1-10 units", "Bulk: 50+")
- `min_quantity` (decimal, > 0) - Minimum quantity for this tier
- `price` (decimal, >= 0) - Price per unit at this tier
- `effective_from` (date, default: CURRENT_DATE) - Tier effective start date

**Optional Tier Configuration:**
- `max_quantity` (decimal, > min_quantity) - Maximum quantity (null = no maximum)
- `discount_percent` (decimal, 0-100) - Discount percentage from base price
- `effective_to` (date) - Tier expiration date (null = no expiration)

**System Fields:**
- `created_at`, `updated_at` (timestamp) - Audit trail
- `created_by`, `updated_by` (integer) - User IDs

**Total**: 14 fields in item_pricing_tiers table

---

## Custom Fields

Organisations define their own item fields. Before putting a business fact
into `metadata`, check `get_submissions(action="schema", object_type="item", operation="create")`
→ `custom_fields` (key, type, limits, options, required). Set values with
`"custom_fields": {"key": value}`; on update keys you leave out are unchanged
and `"custom_fields_clear": ["key"]` empties one; never send `null`. Decimals
as numeric strings, dates `YYYY-MM-DD`, choice = one option `value`. Filter
with `query("item", filters={"custom_fields.<key>": value}).
All rules (register, types, required fields, transactions, filters, import, merge): the custom-fields resource; full contract `docs/GUIDES/GUIDE_CUSTOM_FIELDS.md`.

## Metadata Best Practices

The `metadata` JSONB field allows storing custom data without schema changes.

### When to Use Metadata

**Good use cases:**
- External system IDs (product catalogs, e-commerce platforms)
- Integration-specific data (Shopify product ID, SKU mappings)
- Temporary operational flags (promotion indicators, seasonal tags)
- Custom attributes specific to your organization (brand, warranty info, supplier codes)

**Bad use cases:**
- Data that should be in dedicated columns (use schema fields instead)
- Critical operational data (risk of being overwritten)
- Data needed for queries or reports (poor performance)

### Structure Tips

**Use namespacing:**
```json
{
  "metadata": {
    "shopify": {
      "product_id": "7234567890123",
      "variant_id": "42345678901234",
      "last_sync": "2025-01-14T10:30:00Z"
    },
    "stripe": {
      "price_id": "price_1234567890ABC"
    },
    "internal": {
      "brand": "TechCo",
      "warranty_months": 12,
      "supplier_code": "SUP-001"
    }
  }
}
```

### Updating Metadata

**Important:** Metadata updates REPLACE the entire object. Always:
1. Get current metadata first using `get_entity("item", id=X)`
2. Merge your changes into the existing metadata object
3. Send complete updated object in workflow payload

---

## Creating an Item

Use the `item.create` workflow:

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="item", operation="create")

// Step 2: Submit with discovered fields
submit("item", "create", '{...}')
// Tip: Use validate_only=true to check payload before submitting
```

```javascript
submit("item", "create", {
    // Required
    "item_number": "WIDGET-001",
    "item_name": "Premium Wireless Earbuds",

    // Optional classification
    "item_type": "revenue_product",  // revenue_service, expense_product, expense_service
    "category": "SALES",
    "description": "Bluetooth 5.0 wireless earbuds with active noise cancellation",
    "unit_of_measure": "EA",

    // Pricing defaults
    "unit_price": 149.99,
    "cost_price": 45.00,
    "is_taxable": true,

    // GL account mappings
    "revenue_account_number": "4000",  // Sales Revenue
    "cogs_account_number": "5000",     // Cost of Goods Sold
    "asset_account_number": "1200",    // Inventory
    "tax_code": "SALES_TAX",

    // Scope (default: visible to all entities)
    "is_global": true,

    // Custom metadata
    "metadata": {
      "brand": "TechCo",
      "warranty_months": 12,
      "supplier_code": "SUP-TECH-001"
    }
})
```

**Create Service Item:**

```javascript
submit("item", "create", {
    "item_number": "CONS-HR-001",
    "item_name": "Consulting - Hourly Rate",
    "item_type": "revenue_service",
    "category": "SERVICES",
    "description": "Professional consulting services billed per hour",
    "unit_of_measure": "HR",
    "unit_price": 200.00,
    "cost_price": 80.00,
    "revenue_account_number": "4100",  // Service Revenue
    "expense_account_number": "5200",  // Contract Labor
    "tax_code": "EXEMPT"
})
```

**Create Entity-Specific Item:**

```javascript
submit("item", "create", {
    "item_number": "EU-MUG-001",
    "item_name": "Artisan Ceramic Coffee Mug",
    "item_type": "revenue_product",

    // Entity-specific: visible ONLY to Entity 9
    "is_global": false,
    "legal_entity_id": 9,

    "revenue_account_number": "4000",
    "cogs_account_number": "5000",
    "tax_code": "VAT"
})

// Result:
// - Entity 9 sees this item
// - Other entities do NOT see this item
```

**Create Item with Pricing:**

```javascript
submit("item", "create", {
    "item_number": "WIDGET-001",
    "item_name": "Premium Widget",
    "item_type": "revenue_product",

    // Entity-specific pricing (multi-currency)
    "item_prices": [
      {
        "legal_entity_id": 13,
        "currency": "USD",
        "unit_price": 149.99,
        "cost_price": 45.00
      },
      {
        "legal_entity_id": 9,
        "currency": "EUR",
        "unit_price": 129.99,
        "cost_price": 39.00
      },
      {
        "legal_entity_id": 14,
        "currency": "GBP",
        "unit_price": 119.99,
        "cost_price": 35.00
      }
    ]
})
```

**Create Item with Volume Pricing Tiers:**

```javascript
submit("item", "create", {
    "item_number": "BULK-WIDGET-001",
    "item_name": "Bulk Widget",
    "item_type": "revenue_product",
    "unit_price": 100.00,

    // Volume-based pricing tiers
    "item_pricing_tiers": [
      {
        "legal_entity_id": 13,
        "tier_name": "Tier 1: 1-10 units",
        "min_quantity": 1,
        "max_quantity": 10,
        "price": 100.00,
        "discount_percent": 0
      },
      {
        "legal_entity_id": 13,
        "tier_name": "Tier 2: 11-50 units (10% off)",
        "min_quantity": 11,
        "max_quantity": 50,
        "price": 90.00,
        "discount_percent": 10
      },
      {
        "legal_entity_id": 13,
        "tier_name": "Tier 3: 51+ units (20% off)",
        "min_quantity": 51,
        "max_quantity": null,  // No maximum
        "price": 80.00,
        "discount_percent": 20
      }
    ]
})
```

---

## Updating an Item

Use the `item.update` workflow:

**Update Master Item:**

```javascript
submit("item", "update", {
    // Identifier (at least one required)
    "item_number": "WIDGET-001",
    // OR "item_id": 42,
    // OR "global_item_id": "ITEM-000042",

    // Fields to update
    "item_name": "Premium Wireless Earbuds Pro",
    "description": "Updated with new features",
    "unit_price": 159.99,
    "cost_price": 48.00
})
```

**Update GL Account Mappings:**

```javascript
submit("item", "update", {
    "item_number": "WIDGET-001",
    "revenue_account_number": "4100",  // Change to Service Revenue
    "cogs_account_number": "5100"      // Change COGS account
})
```

**Create Entity Override (Rename for Entity):**

```javascript
submit("item", "update", {
    "item_number": "WIDGET-001",
    "legal_entity_id": 9,  // Create entity-specific override
    "item_name": "Premium Earbuds - EU Edition"
})

// Result:
// - Entity 9 sees: "Premium Earbuds - EU Edition"
// - All other entities see: "Premium Wireless Earbuds" (master)
```

**Hide Item from Entity:**

```javascript
submit("item", "update", {
    "item_number": "WIDGET-002",
    "legal_entity_id": 13,
    "is_active": false  // Entity-specific deactivation
})

// Result:
// - Entity 13 won't see item WIDGET-002
// - All other entities still see WIDGET-002
```

**Update Item Pricing (Related Entity Operations):**

Use `_action` field for CRUD operations on related entities:

```javascript
submit("item", "update", {
    "item_number": "WIDGET-001",

    "item_prices": [
      // Add new price
      {
        "_action": "add",
        "legal_entity_id": 14,
        "currency": "GBP",
        "unit_price": 119.99,
        "cost_price": 35.00
      },
      // Update existing price
      {
        "_action": "update",
        "price_id": 12,
        "unit_price": 124.99
      },
      // Delete price
      {
        "_action": "delete",
        "price_id": 8
      }
    ]
})
```

**Update Volume Pricing Tiers:**

```javascript
submit("item", "update", {
    "item_number": "BULK-WIDGET-001",

    "item_pricing_tiers": [
      // Add new tier
      {
        "_action": "add",
        "legal_entity_id": 14,
        "tier_name": "UK Volume Tier",
        "min_quantity": 10,
        "max_quantity": 100,
        "price": 85.00,
        "discount_percent": 15
      },
      // Update existing tier
      {
        "_action": "update",
        "tier_id": 5,
        "price": 82.00
      },
      // Delete tier
      {
        "_action": "delete",
        "tier_id": 3
      }
    ]
})
```

---

## Deactivating an Item

Use the `item.delete` workflow to deactivate or remove items.

**Soft delete (default):**

```javascript
submit("item", "delete", {
    "item_number": "WIDGET-001",
    "deletion_reason": "Product discontinued",
    "hard_delete": false  // Default - preserves historical data
})
```

**Hard delete (use with caution):**

```javascript
submit("item", "delete", {
    "item_number": "TEST-WIDGET-001",
    "deletion_reason": "Test item - never used in transactions",
    "hard_delete": true  // Will fail if item has transaction history
})
```

**Delete Entity Override Only:**

```javascript
submit("item", "delete", {
    "item_number": "WIDGET-001",
    "legal_entity_id": 9,  // Only delete Entity 9's override
    "deletion_reason": "Reverting to master values"
})

// Result:
// - Entity 9 now sees master name "Premium Wireless Earbuds"
// - Override removed from database
```

**When to use:**
- Soft delete: Item has transaction history (preserves audit trail)
- Hard delete: Test data, duplicates, data entry errors (never actually used)

**Never use hard delete for items with transaction history.**

---

## Bulk Import

For importing multiple items at once:
- Chart of Accounts template imports (US GAAP, IFRS)
- Data migration from legacy systems
- CSV file uploads
- Validate before import (dry-run mode)
- Handle duplicates automatically (skip, update, or error)

### Import Workflow

Use the `item.import` workflow:

```javascript
submit("item", "import", {
    "records": [
      {
        "item_number": "WIDGET-001",
        "item_name": "Premium Wireless Earbuds",
        "item_type": "revenue_product",
        "category": "SALES",
        "description": "Bluetooth 5.0 wireless earbuds",
        "unit_of_measure": "EA",
        "unit_price": 149.99,
        "cost_price": 45.00,
        "revenue_account_number": "4000",
        "cogs_account_number": "5000",
        "tax_code": "SALES_TAX",
        "is_global": true
      },
      {
        "item_number": "SERV-HR-001",
        "item_name": "Consulting - Hourly",
        "item_type": "revenue_service",
        "category": "SERVICES",
        "unit_of_measure": "HR",
        "unit_price": 200.00,
        "revenue_account_number": "4100",
        "tax_code": "EXEMPT"
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

Items are considered duplicates if:
- **item_number** matches (unique per organization)

### Required Fields for Import

- `item_number` (1-100 chars, unique per organization)
- `item_name` (1-255 chars)

### Optional Fields for Import

All master_items table fields:
- `item_type` (revenue_product, revenue_service, expense_product, expense_service)
- `category`, `description`, `unit_of_measure`
- `unit_price`, `cost_price`, `is_taxable`
- `revenue_account_number`, `expense_account_number`, `asset_account_number`, `cogs_account_number`
- `tax_code`
- `is_global` (default: true)
- `metadata`

### Validation Behavior

The importer performs comprehensive validation:
- **Field validation**: Data types, lengths, formats, required fields, enum values
- **Foreign key validation**: Verifies GL accounts exist (if provided)
- **Business rule validation**: Item number uniqueness, price >= 0, valid item types
- **Duplicate detection**: Checks item_number (unique per organization)
- **Warnings**: Missing description, missing GL accounts, price without cost

### Import Response

```json
{
  "success": true,
  "import_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_records": 150,
  "imported": 145,
  "updated": 3,
  "skipped": 2,
  "errors": 0,
  "warnings": [
    {
      "row": 23,
      "field": "description",
      "message": "Missing item description",
      "record_identifier": "WIDGET-023"
    },
    {
      "row": 45,
      "field": "revenue_account_number",
      "message": "Missing revenue account for revenue item",
      "record_identifier": "SERV-045"
    }
  ],
  "created_ids": [301, 302, 303, ...],
  "updated_ids": [125, 167, 189],
  "duration_ms": 2840
}
```

### Validate Before Importing (Dry Run)

Test your import without making changes:

```javascript
submit("item", "import", {
    "records": [...],
    "options": {
      "validate_only": true
    }
})
```

This returns validation errors without creating any items.

### Common Import Scenarios

**Product Catalog Import:**
```javascript
{
  "object_type": "item",
  "source_type": "catalog",
  "source_id": "product-catalog-2025-01.csv",
  "records": items_from_catalog,
  "options": {
    "on_duplicate": "update",  // Update existing items
    "stop_on_error": false     // Continue even if some fail
  }
}
```

**Data Migration from Legacy System:**
```javascript
{
  "object_type": "item",
  "source_type": "migration",
  "source_id": "legacy-erp-migration",
  "records": items_from_legacy_system,
  "options": {
    "on_duplicate": "skip",    // Don't overwrite existing
    "validate_only": true,     // Test first
    "stop_on_error": true      // Stop if validation fails
  }
}
```

**CSV File Import:**
```javascript
{
  "object_type": "item",
  "source_type": "csv",
  "source_id": "items-import-2025-01-14.csv",
  "records": items_from_csv,
  "options": {
    "on_duplicate": "error",   // Flag duplicates
    "stop_on_error": true      // Stop if duplicate found
  }
}
```

---

## Common Scenarios

### Standard Product Catalog

Set up product catalog visible to all entities:

```javascript
submit("item", "create", {
    "item_number": "WIDGET-001",
    "item_name": "Premium Wireless Earbuds",
    "description": "Bluetooth 5.0 earbuds with ANC",
    "item_type": "revenue_product",
    "unit_of_measure": "EA",
    "revenue_account_number": "4000",
    "cogs_account_number": "5000",
    "asset_account_number": "1200",
    "tax_code": "SALES_TAX",
    "is_global": true  // Visible to all entities
})
```

### Regional Products (Entity-Specific)

Create products visible only to specific entities:

```javascript
// US-only product
submit("item", "create", {
    "item_number": "US-WIDGET-001",
    "item_name": "US-Market Widget",
    "item_type": "revenue_product",
    "is_global": false,
    "legal_entity_id": 13,  // US entity
    "revenue_account_number": "4000",
    "tax_code": "SALES_TAX"
})

// EU-only product
submit("item", "create", {
    "item_number": "EU-WIDGET-001",
    "item_name": "EU-Market Widget",
    "item_type": "revenue_product",
    "is_global": false,
    "legal_entity_id": 9,  // EU entity
    "revenue_account_number": "4000",
    "tax_code": "VAT"
})
```

### Service Items with Hourly Rates

Track professional services by hour:

```javascript
submit("item", "create", {
    "item_number": "CONS-SR",
    "item_name": "Senior Consultant",
    "description": "Senior-level consulting services",
    "item_type": "revenue_service",
    "unit_of_measure": "HR",
    "revenue_account_number": "4100",
    "expense_account_number": "5200",
    "tax_code": "EXEMPT",
    "item_prices": [
      { "legal_entity_id": 9, "currency": "EUR", "unit_price": 180.00, "cost_price": 75.00 },
      { "legal_entity_id": 13, "currency": "USD", "unit_price": 200.00, "cost_price": 80.00 }
    ]
})
```

### Multi-Currency Pricing

Set entity-specific pricing in different currencies:

```javascript
submit("item", "update", {
    "item_number": "WIDGET-001",
    "item_prices": [
      { "_action": "add", "legal_entity_id": 9, "currency": "EUR", "unit_price": 129.99, "cost_price": 39.00 },
      { "_action": "add", "legal_entity_id": 13, "currency": "USD", "unit_price": 149.99, "cost_price": 45.00 }
    ]
})
```

### Entity-Specific GL Account Mappings

Different entities use different GL accounts for same item:

```javascript
// Create master item with standard GL accounts
submit("item", "create", {
    "item_number": "WIDGET-001",
    "item_name": "Premium Widget",
    "item_type": "revenue_product",
    "revenue_account_number": "4000",
    "cogs_account_number": "5000",
    "is_global": true
})

// Create entity override with different GL accounts
submit("item", "update", {
    "item_number": "WIDGET-001",
    "legal_entity_id": 10,  // Create override for Entity 10
    "revenue_account_number": "4100"  // Override revenue account
})

// Result:
// - Entity 10: Revenue -> 4100
// - Other entities: Revenue -> 4000
```

---

## Getting Reference Data

All reference data should be queried dynamically using search tools:

**Item Types:**
Use enum values directly:
- `revenue_product` - Physical goods sold
- `revenue_service` - Services provided
- `expense_product` - Physical goods purchased
- `expense_service` - Services purchased

**GL Accounts:**
Use `query("account")` to get valid account numbers

**Tax Codes:**
Use `query("tax_code")` to get valid tax codes

**Legal Entities:**
Use `query("legal_entity")` to get valid `legal_entity_id` values

**Tip:** Always query reference data dynamically rather than hardcoding values, as they may vary by organization and legal entity.

---

## Common Pitfalls

### Duplicate Prevention
❌ **Don't** create multiple items with same item_number
✅ **Do** search first to check if item exists using `query("item", query="WIDGET-001")`

### Foreign Key References
❌ **Don't** hardcode GL account numbers from other systems
✅ **Do** use `query("account")` to find current account numbers dynamically

### Metadata Overwrites
❌ **Don't** update metadata without reading current value first
✅ **Do** get → merge → update pattern:
```javascript
// 1. Get current item
let item = get_entity("item", id=42)

// 2. Merge changes
let updated_metadata = {
  ...item.metadata,
  "new_field": "new_value"
}

// 3. Update with complete metadata
submit("item", "update", {
    "item_id": 42,
    "metadata": updated_metadata
})
```

### Entity-Specific Items
❌ **Don't** create global item then hide from N-1 entities (wasteful)
✅ **Do** use `is_global: false` with `legal_entity_id` (efficient 2-row pattern)

### Pricing Updates
❌ **Don't** forget to specify `_action` field when updating related entities
✅ **Do** use `_action: "add"`, `"update"`, or `"delete"` in nested arrays

---

## Tips & Best Practices

**Item Numbering:**
- Use consistent prefixes (PROD-, SERV-, SUP-)
- Include category or type in number (WIDGET-001, CONS-HR-001)
- Keep numbers short but meaningful
- Don't reuse numbers (soft delete instead)

**GL Account Mapping:**
- Set revenue_account_number for all revenue items
- Set expense_account_number for all expense items
- Set asset_account_number for inventory items
- Set cogs_account_number for products with inventory

**Pricing Strategy:**
- Use item_prices for multi-currency pricing
- Use item_pricing_tiers for volume discounts
- Set effective_from dates for future price changes
- Track price history with multiple effective date records

**MSEO Pattern:**
- Create global items (is_global=true) for organization-wide catalog
- Create entity-specific items (is_global=false) only when truly needed
- Use overrides (legal_entity_id) for entity customizations
- Delete overrides to revert to master values

**Metadata Usage:**
- Namespace by system (shopify, stripe, internal)
- Store external IDs for integration tracking
- Avoid storing critical operational data
- Always get → merge → update to prevent overwrites

---

## Query Field Reference

### Display Fields (returned by `query` / `query`)

| Field | Type | Description |
|-------|------|-------------|
| `item_number` | string | Unique item identifier (SKU) |
| `item_name` | string | Item display name |
| `item_type` | string | revenue_product, revenue_service, expense_product, expense_service |
| `category` | string | Item category (INVENTORY, SALES, SERVICES, etc.) |
| `unit_of_measure` | string | Unit (EA, HR, kg, etc.) |
| `unit_price` | decimal | Default selling price |
| `cost_price` | decimal | Default cost price |
| `is_taxable` | boolean | Whether item is taxable |
| `is_active` | boolean | Active status |

### Searchable Fields (text search via `query("item", query=...)`)

| Field | Description |
|-------|-------------|
| `item_number` | Item number/SKU (partial match) |
| `item_name` | Item display name (partial match) |
| `description` | Detailed description |
| `global_item_id` | Organization-wide unique ID |

### Filter Fields (via `filters` parameter)

| Field | Type | Example |
|-------|------|---------|
| `legal_entity_id` | integer | `13` |
| `is_active` | boolean | `true` |
| `item_type` | string | `"revenue_product"` |
| `category` | string | `"SERVICES"` |
| `is_global` | boolean | `true` |
| `is_taxable` | boolean | `true` |

### Sort Fields (via `sort_by` parameter)

| Field | Default | Description |
|-------|---------|-------------|
| `item_number` | Yes | By item number/SKU |
| `item_name` | | Alphabetical by name |
| `created_at` | | Newest first |
| `updated_at` | | Recently modified |

### Related Data (returned by `get_entity` with `include_related=True`)

| Related Entity | Description |
|----------------|-------------|
| `item_prices` | Entity-specific pricing with multi-currency support |
| `item_pricing_tiers` | Volume-based pricing tiers |

---

## End of Guide

This guide covers complete item management including all database fields, workflows, query tools, metadata usage, and operational best practices for Claude.ai automation.
