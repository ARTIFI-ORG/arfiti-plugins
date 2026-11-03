# Dimensions Management

## Extending dimension applicability

Supported targets are `account`, `customer`, `vendor`, `employee`, `project`,
`fixed_asset` and `transaction`. A dimension named “project” does not automatically
apply to project records: its `applies_to` list must include `project`.

For an existing type, use `dimension_type.update` with its master ID or name and
`applies_to` containing the **complete existing list plus new targets**. Omit
`legal_entity_id`: applicability belongs to the organization-wide definition.
Removing existing targets is refused, even when no current assignment is known.
Concurrent updates are serialized; reload and retry if another update added targets.
No values, existing assignments or posted GL history are rewritten.

Example: `{"dimension_type_name":"department","applies_to":["account","customer","vendor","transaction","employee","project"]}`.
In Admin, open Records → Dimensions → the type → Overview → **Add targets**.
Approval rules still apply; an approval-pending response is not a completed update.
Creation and CSV imports accept the same target vocabulary. Import updates do not
change applicability; use the update workflow above.

Customer details resolve stored master dimension IDs and show entity-specific label
overrides when present. Global assignments do not require override rows, and entity
access restrictions still filter the displayed assignments.

> **MSEO implementation release:** Business identity is the master ID. Use type/value codes with legal-entity context in supported assignment payloads. Budget dimension IDs already reference masters. Do not translate them using an override ID. Legacy numeric commands must retain their endpoint namespace until its compatibility adapter is released; do not guess an ID by checking two tables.
>
> A required header dimension needs an explicit header value. Predominant-amount derivation requires an explicitly named workflow strategy. Posted reports use stored GL-line assignments, including inactive historical values and reversing entries. They must not rebuild history from current customer/vendor/employee/account defaults. A missing assignment is unassigned; an unresolved identity is an error requiring audit.


> **Required dimensions are now configured per workflow, not per dimension type.** (May 2026)
>
> The fields `master_dimension_types.is_required` and `dimension_types_per_entity.is_required` shown in many examples below are **deprecated**. The GL validator no longer reads them. Required dimensions for transaction posting live in `workflow_definitions.related_entity_rules.<transaction_type>.transaction_dimensions.required_dimension_types`, managed via the admin UI under **Workflows → transaction.post → Related entities → DimensionSelector**.
>
> To discover required dimensions for a transaction type today, query the workflow definition for `(organization_id, object_type='transaction', operation='post')` and read the JSONB at that path. Do **not** rely on `query("dimension_type", filters={"is_required": true})` — it will return stale legacy flags.

## Overview

**Dimensions** are custom analysis axes that allow multi-dimensional financial analysis beyond the standard chart of accounts. They enable slicing and dicing financial data by department, project, location, cost center, business segment, and other custom attributes.

**Key Features:**
- Multi-dimensional reporting and analysis
- Hierarchical structures (e.g., USA > West > California)
- Entity-specific overrides (MSEO pattern)
- Transaction-level dimension tagging
- Budget dimension support
- Workflow-based management

**Two-Level Structure:**
- **Dimension Types**: Define analysis categories (department, project, location)
- **Dimension Values**: Define specific options within each type (ENG, SALES, MKT)

## Common Use Cases

1. **Departmental Analysis**: Track revenue and expenses by department (Engineering, Sales, Marketing)
2. **Project Tracking**: Analyze profitability by project or engagement
3. **Geographic Analysis**: Report by location, region, or country hierarchy
4. **Cost Center Reporting**: Allocate expenses to cost centers
5. **Business Segment Analysis**: Split revenue by B2B, B2C, or product lines
6. **Customer Segmentation**: Track by customer segment, industry, or region
7. **Multi-dimensional P&L**: Report by any combination of dimensions

## Architecture

### MSEO Pattern (Two Levels)

Dimensions use a **two-level MSEO pattern**:

**Level 1: Dimension Types**
- `master_dimension_types` - Organization-wide type definitions
- `dimension_types_per_entity` - Entity-specific type overrides
- `master_dimension_types` plus scoped `dimension_types_per_entity` overrides — no `v_dimension_types_effective` exists in the audited schema

**Level 2: Dimension Values**
- `master_dimension_values` - Organization-wide value definitions
- `dimension_values_per_entity` - Entity-specific value overrides
- `v_dimension_values_effective` - Resolved values per entity

**Why Two Levels?**
- Types define *what* dimensions exist (department, project)
- Values define *which options* are available (ENG, SALES, MKT)
- Each level has its own MSEO pattern for flexibility

### Example Hierarchy

```
Organization (Company 63)
│
├── Dimension Type: department
│   ├── Value: ENG (Engineering)
│   ├── Value: SALES (Sales)
│   └── Value: MKT (Marketing)
│
├── Dimension Type: location
│   ├── Value: USA (United States)
│   │   ├── Child: WEST (West Region)
│   │   │   ├── Child: CA (California)
│   │   │   └── Child: OR (Oregon)
│   │   └── Child: EAST (East Region)
│   │       └── Child: NY (New York)
│   └── Value: EUR (Europe)
│       ├── Child: UK (United Kingdom)
│       └── Child: DE (Germany)
│
└── Dimension Type: project
    ├── Value: PROJ-001 (Website Redesign)
    └── Value: PROJ-002 (ERP Implementation)
```

---

## Dimension Types

### Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| **id** | integer | Auto | Primary key | Auto-generated |
| **organization_id** | integer | Yes | Organization | FK to organizations |
| **global_dimension_type_id** | varchar(50) | Auto | Global ID | Auto-generated: DIMT-XXXXXX |
| **name** | varchar(100) | Yes | Internal name | Lowercase, no spaces, alphanumeric |
| **display_name** | varchar(200) | Yes | Display name | 1-200 chars |
| **description** | text | No | Purpose description | Max 500 chars recommended |
| **applies_to** | varchar[] | Yes | Entity types | Array: account, customer, vendor, employee, project, fixed_asset, transaction |
| **is_required** | boolean | No | Mandatory flag | Default: false |
| **hierarchy_depth** | integer | No | Max hierarchy levels | 1-5, Default: 3 |
| **is_shared_across_entities** | boolean | No | Share values | Default: true |
| **is_global** | boolean | No | Global visibility | Default: true |
| **is_active** | boolean | No | Active status | Default: true |
| **metadata** | jsonb | No | Custom metadata | JSON object |
| **sort_order** | integer | No | Display order | Default: 0 |
| **created_at** | timestamp | Auto | Creation timestamp | Auto-set |
| **updated_at** | timestamp | Auto | Update timestamp | Auto-updated |
| **created_by** | integer | Auto | Creator user ID | From context |
| **updated_by** | integer | Auto | Updater user ID | From context |

### Applies-To Options

| Value | Meaning | Use Case |
|-------|---------|----------|
| **account** | Can assign to GL accounts | Default dimensions for accounts |
| **customer** | Can assign to customers | Customer segmentation |
| **vendor** | Can assign to vendors | Vendor categorization |
| **transaction** | Can assign to transaction lines | Transaction-level tagging |

**Example**: `applies_to: ["account", "transaction"]` means dimension can be set on accounts and transaction lines.

### Standard Dimension Types

| Name | Display Name | Applies To | Hierarchy Depth | Use Case |
|------|--------------|------------|-----------------|----------|
| **department** | Department | account, transaction | 2 | Departmental P&L |
| **project** | Project | account, customer, transaction | 1 | Project tracking |
| **location** | Location | customer, vendor | 3 | Geographic analysis |
| **cost_center** | Cost Center | account, vendor, transaction | 2 | Cost allocation |
| **business_segment** | Business Segment | transaction | 1 | B2B vs B2C analysis |

### Business Rules

1. **Name uniqueness**: Dimension type name must be unique within organization
2. **Name format**: Lowercase, no spaces, alphanumeric only (use underscores)
3. **Applies-to required**: Must specify at least one entity type
4. **Hierarchy depth**: 1-5 levels (validates when creating values)
5. **Deletion rules**:
   - Soft delete: Sets is_active=false
   - Hard delete: Only allowed if type has NO values

---

## Dimension Values

### Field Reference

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| **id** | integer | Auto | Primary key | Auto-generated |
| **organization_id** | integer | Yes | Organization | FK to organizations |
| **global_dimension_value_id** | varchar(50) | Auto | Global ID | Auto-generated: DIMV-XXXXXX |
| **dimension_type_id** | integer | Yes | Parent type | FK to master_dimension_types |
| **code** | varchar(50) | Yes | Unique code | Uppercase, 1-50 chars |
| **name** | varchar(200) | Yes | Display name | 1-200 chars |
| **description** | text | No | Value description | Max 500 chars recommended |
| **parent_id** | integer | No | Parent value (hierarchy) | FK to master_dimension_values |
| **parent_code** | varchar(50) | No | Parent code | For reference only |
| **level** | integer | Auto | Hierarchy level | Auto-calculated: 1, 2, 3... |
| **full_path** | text | Auto | Complete path | Auto-calculated: USA/WEST/CA |
| **sort_order** | integer | No | Display order | Default: 0 |
| **is_global** | boolean | No | Global visibility | Default: true |
| **is_active** | boolean | No | Active status | Default: true |
| **metadata** | jsonb | No | Custom metadata | JSON object |
| **created_at** | timestamp | Auto | Creation timestamp | Auto-set |
| **updated_at** | timestamp | Auto | Update timestamp | Auto-updated |
| **created_by** | integer | Auto | Creator user ID | From context |
| **updated_by** | integer | Auto | Updater user ID | From context |

### Hierarchy Fields (Auto-Calculated)

| Field | Description | Example |
|-------|-------------|---------|
| **level** | Depth in hierarchy | 1 = root, 2 = child, 3 = grandchild |
| **full_path** | Complete path from root | "USA/WEST/CA" |
| **parent_id** | Foreign key to parent | Links to parent value |
| **parent_code** | Parent value code | "WEST" (parent of "CA") |

**How it works:**
1. Create root value (level=1, no parent)
2. Create child value with parent_code (level=2, full_path calculated)
3. Create grandchild value with parent_code (level=3, full_path extended)

### Business Rules

1. **Code uniqueness**: Code must be unique within dimension type
2. **Code format**: Uppercase recommended, alphanumeric + hyphen/underscore
3. **Parent validation**: parent_code must reference existing value in same type
4. **Hierarchy depth**: Cannot exceed dimension type's hierarchy_depth
5. **Circular references**: Prevented (A cannot be parent of B if B is ancestor of A)
6. **Deletion rules**:
   - Soft delete: Sets is_active=false
   - Hard delete: Only allowed if value is NOT used and has NO children

---

## Dimension Type Workflows

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

### dimension_type.create

**Purpose**: Create a new dimension type (e.g., department, project, location)

**Approval**: no approval step by default; the organisation's workflow configuration sets the lane and any approval, and the `status` and `lane` in the submit() result are authoritative.

**Use Cases**:
- Setting up standard dimension types (department, project, location, cost_center)
- Creating custom dimension types (product_line, customer_segment)
- Defining entity-specific dimension types (regional location types)

**Payload**:

```javascript
{
  // Required fields
  "name": "product_line",                 // Lowercase, no spaces, alphanumeric
  "display_name": "Product Line",         // UI display name
  "applies_to": ["account", "customer", "transaction"],  // Array of entity types

  // Optional fields
  "description": "Track revenue by product line",
  "hierarchy_depth": 2,                   // 1-5, default: 3
  "is_required": false,                   // Default: false
  "is_shared_across_entities": true,      // Default: true
  "sort_order": 5,                        // Default: 0
  "is_global": true,                      // Default: true
  "legal_entity_id": null                 // Required if is_global=false
}
```

**Example**:

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="dimension_type", operation="create")

// Step 2: Submit with discovered fields
submit("dimension_type", "create", {
    name: "customer_segment",
    display_name: "Customer Segment",
    applies_to: ["customer", "transaction"],
    description: "Customer segmentation for analysis",
    hierarchy_depth: 2,
    is_required: false
})
// Tip: Use validate_only=true to check payload before submitting
```

**Validation**:
- name is lowercase, alphanumeric, no spaces (use underscores)
- name is unique within organization
- applies_to array contains valid values: account, customer, vendor, employee, project, fixed_asset, transaction
- hierarchy_depth is 1-5
- display_name is 1-200 chars

**Returns**:

```javascript
{
  "success": true,
  "dimension_type_id": 42,
  "global_dimension_type_id": "DIMT-000042",
  "name": "customer_segment",
  "workflow_id": "wf-uuid-here",
  "lane": "green",
  "status": "completed"
}
```

---

### dimension_type.update

**Purpose**: Update dimension type or create entity-specific override

**Approval**: no approval step by default (configurable per organisation; the submit() result is authoritative).

**Use Cases**:
- Update display name or description
- Change sort order
- Mark as required/optional
- Create entity-specific override (hide type from entity)
- Customize display name for specific entity

**Payload (Master Update)**:

```javascript
{
  // Identification (at least one required)
  "dimension_type_id": 42,                // OR
  "dimension_type_name": "department",    // OR
  "global_dimension_type_id": "DIMT-000042",

  // Optional fields to update
  "display_name": "Business Unit",
  "description": "Updated description",
  "is_required": true,
  "sort_order": 10,
  "is_active": true
}
```

**Payload (Entity Override)**:

```javascript
{
  "dimension_type_name": "department",
  "legal_entity_id": 9,                   // Creates entity override
  "is_visible": false,                     // Hide from Entity 9
  // OR
  "display_name": "Business Unit"         // Custom display name for Entity 9
}
```

**Example: Update Master**:

```javascript
submit("dimension_type", "update", {
    dimension_type_name: "project",
    description: "Updated: Project-based revenue tracking",
    is_required: true
})
```

**Example: Entity Override**:

```javascript
submit("dimension_type", "update", {
    dimension_type_name: "department",
    legal_entity_id: 13,
    display_name: "Business Unit"  // Entity 13 sees "Business Unit" instead
})
```

**Returns**:

```javascript
{
  "success": true,
  "dimension_type_id": 42,
  "override_created": false,  // true if entity override was created
  "workflow_id": "wf-uuid-here"
}
```

---

### dimension_type.delete

**Purpose**: Soft or hard delete dimension type

**Approval**: no approval step by default (configurable per organisation; the submit() result is authoritative).

**Use Cases**:
- Soft delete: Deactivate dimension type (preserves history)
- Hard delete: Remove unused dimension type completely
- Delete entity override only (revert to master)

**Payload**:

```javascript
{
  // Identification (at least one required)
  "dimension_type_id": 42,                // OR
  "dimension_type_name": "product_line",  // OR
  "global_dimension_type_id": "DIMT-000042",

  // Optional fields
  "legal_entity_id": null,                // If provided, only delete entity override
  "deletion_reason": "No longer tracking by product line",
  "hard_delete": false                    // Default: false (soft delete)
}
```

**Example: Soft Delete**:

```javascript
submit("dimension_type", "delete", {
    dimension_type_name: "product_line",
    deletion_reason: "Consolidating dimension types",
    hard_delete: false
})
```

**Example: Hard Delete**:

```javascript
submit("dimension_type", "delete", {
    dimension_type_name: "test_dimension",
    deletion_reason: "Test dimension - never used",
    hard_delete: true  // Fails if type has any values
})
```

**Example: Delete Entity Override**:

```javascript
submit("dimension_type", "delete", {
    dimension_type_name: "department",
    legal_entity_id: 9,  // Only delete Entity 9's override, master unchanged
    deletion_reason: "Reverting to standard department display"
})
```

**Validation**:
- Hard delete: Fails if dimension type has ANY values
- Soft delete: Always allowed (sets is_active=false)
- Entity override delete: Only deletes override for specified entity

**Returns**:

```javascript
{
  "success": true,
  "action": "soft_deleted",  // OR "hard_deleted" OR "override_deleted"
  "dimension_type_id": 42,
  "workflow_id": "wf-uuid-here"
}
```

---

## Dimension Value Workflows

### dimension_value.create

**Purpose**: Create a new dimension value (e.g., ENG, SALES, MKT)

**Approval**: no approval step by default (configurable per organisation; the submit() result is authoritative).

**Use Cases**:
- Create flat dimension values (departments, cost centers)
- Create hierarchical values (geographic hierarchy)
- Create entity-specific values (is_global=false)

**Payload**:

```javascript
{
  // Required fields
  "dimension_type_name": "department",    // Parent dimension type
  "code": "ENG",                          // Unique code within type (uppercase)
  "name": "Engineering",                  // Display name

  // Optional fields (for hierarchies)
  "parent_code": null,                    // Parent value code (for hierarchy)

  // Optional fields (general)
  "description": "Engineering department",
  "sort_order": 1,
  "metadata": {                           // Custom JSON metadata
    "manager": "Jane Smith",
    "budget_code": "B001"
  },
  "is_global": true,                      // Default: true
  "legal_entity_id": null                 // Required if is_global=false
}
```

**Example: Flat Value**:

```javascript
submit("dimension_value", "create", {
    dimension_type_name: "department",
    code: "ENG",
    name: "Engineering",
    description: "Engineering department",
    sort_order: 1
})
```

**Example: Hierarchical Values**:

```javascript
// Step 1: Create root value
submit("dimension_value", "create", {
    dimension_type_name: "location",
    code: "USA",
    name: "United States",
    sort_order: 1
})
// Result: level=1, full_path="USA"

// Step 2: Create child value
submit("dimension_value", "create", {
    dimension_type_name: "location",
    code: "WEST",
    name: "West Region",
    parent_code: "USA",  // Links to parent
    sort_order: 1
})
// Result: level=2, full_path="USA/WEST"

// Step 3: Create grandchild value
submit("dimension_value", "create", {
    dimension_type_name: "location",
    code: "CA",
    name: "California",
    parent_code: "WEST",
    sort_order: 1
})
// Result: level=3, full_path="USA/WEST/CA"
```

**Example: Entity-Specific Value**:

```javascript
submit("dimension_value", "create", {
    dimension_type_name: "department",
    code: "APAC-OPS",
    name: "APAC Operations",
    is_global: false,         // Entity-specific
    legal_entity_id: 15       // Only visible to Entity 15
})
```

**Validation**:
- code is unique within dimension type
- dimension_type_name exists
- parent_code references existing value (if provided)
- Hierarchy depth does not exceed type's hierarchy_depth
- code is 1-50 chars
- name is 1-200 chars

**Returns**:

```javascript
{
  "success": true,
  "dimension_value_id": 128,
  "global_dimension_value_id": "DIMV-000128",
  "code": "ENG",
  "level": 1,                   // Auto-calculated
  "full_path": "ENG",           // Auto-calculated
  "workflow_id": "wf-uuid-here"
}
```

---

### dimension_value.update

**Purpose**: Update dimension value or create entity-specific override

**Approval**: no approval step by default (configurable per organisation; the submit() result is authoritative).

**Use Cases**:
- Update display name or description
- Update metadata
- Change sort order
- Create entity-specific override (custom name for entity)
- Hide value from specific entity

**Payload (Master Update)**:

```javascript
{
  // Identification (at least one required)
  "dimension_type_name": "department",    // Required
  "dimension_value_id": 128,              // OR
  "code": "ENG",                          // OR
  "global_dimension_value_id": "DIMV-000128",

  // Optional fields to update
  "name": "Engineering & Technology",
  "description": "Updated description",
  "sort_order": 5,
  "is_active": true,
  "metadata": {
    "manager": "John Doe",
    "cost_center": "CC-100"
  }
}
```

**Payload (Entity Override)**:

```javascript
{
  "dimension_type_name": "department",
  "code": "SALES",
  "legal_entity_id": 13,                  // Creates entity override
  "name_override": "Revenue Operations",  // Custom name for Entity 13
  "description_override": "Sales & Revenue team",
  // OR
  "is_active_override": false             // Hide from Entity 13
}
```

**Example: Update Master**:

```javascript
submit("dimension_value", "update", {
    dimension_type_name: "department",
    code: "ENG",
    name: "Engineering & Technology",
    metadata: {
      "manager": "Alice Johnson",
      "headcount": 45
    }
})
```

**Example: Entity Override**:

```javascript
submit("dimension_value", "update", {
    dimension_type_name: "department",
    code: "SALES",
    legal_entity_id: 13,
    name_override: "Revenue Operations",
    description_override: "Sales and revenue generation team"
})
```

**Returns**:

```javascript
{
  "success": true,
  "dimension_value_id": 128,
  "override_created": false,  // true if entity override was created
  "workflow_id": "wf-uuid-here"
}
```

---

### dimension_value.delete

**Purpose**: Soft or hard delete dimension value

**Approval**: no approval step by default (configurable per organisation; the submit() result is authoritative).

**Use Cases**:
- Soft delete: Deactivate dimension value (preserves history)
- Hard delete: Remove unused dimension value completely
- Delete entity override only (revert to master)

**Payload**:

```javascript
{
  // Identification (at least one required)
  "dimension_type_name": "department",    // Required
  "dimension_value_id": 128,              // OR
  "code": "OLD_DEPT",                     // OR
  "global_dimension_value_id": "DIMV-000128",

  // Optional fields
  "legal_entity_id": null,                // If provided, only delete entity override
  "deletion_reason": "Department merged with Engineering",
  "hard_delete": false                    // Default: false (soft delete)
}
```

**Example: Soft Delete**:

```javascript
submit("dimension_value", "delete", {
    dimension_type_name: "department",
    code: "OLD_DEPT",
    deletion_reason: "Department merged with Engineering",
    hard_delete: false
})
```

**Example: Hard Delete**:

```javascript
submit("dimension_value", "delete", {
    dimension_type_name: "department",
    code: "TEST",
    deletion_reason: "Test value - never used",
    hard_delete: true  // Fails if value is used or has children
})
```

**Example: Delete Entity Override**:

```javascript
submit("dimension_value", "delete", {
    dimension_type_name: "department",
    code: "SALES",
    legal_entity_id: 13,  // Only delete Entity 13's override
    deletion_reason: "Reverting to standard sales display"
})
```

**Validation**:
- Hard delete: Fails if value is used anywhere OR has children
- Soft delete: Always allowed (sets is_active=false)
- Entity override delete: Only deletes override for specified entity

**Returns**:

```javascript
{
  "success": true,
  "action": "soft_deleted",  // OR "hard_deleted" OR "override_deleted"
  "dimension_value_id": 128,
  "workflow_id": "wf-uuid-here"
}
```

---

## Bulk Import

### Dimension Type Import

Use the `dimension_type.import` workflow to bulk import dimension types.

**Workflow**: `dimension_type.import`

**Purpose**: Import multiple dimension types from templates, CSV files, or data migration

**Approval**: no approval step by default (configurable per organisation; the submit() result is authoritative).

**Use Cases**:
- Initial setup (import standard dimension types)
- Template-based imports (industry-standard dimensions)
- Data migration from legacy systems

**Payload**:

```javascript
{
  "object_type": "dimension_type",
  "records": [
    {
      "name": "department",
      "display_name": "Department",
      "applies_to": ["account", "transaction"],
      "description": "Departmental analysis",
      "hierarchy_depth": 2,
      "is_required": true
    },
    {
      "name": "project",
      "display_name": "Project",
      "applies_to": ["account", "customer", "transaction"],
      "description": "Project-based tracking",
      "hierarchy_depth": 1,
      "is_required": false
    }
  ],
  "options": {
    "on_duplicate": "update",    // skip, update, error
    "batch_size": 100,
    "stop_on_error": false,
    "validate_only": false
  }
}
```

**Example**:

```javascript
submit("dimension_type", "import", {
    records: [
      {
        name: "department",
        display_name: "Department",
        applies_to: ["account", "transaction"],
        hierarchy_depth: 2,
        is_required: true
      },
      {
        name: "location",
        display_name: "Location",
        applies_to: ["customer", "vendor"],
        hierarchy_depth: 3,
        is_required: false
      },
      {
        name: "project",
        display_name: "Project",
        applies_to: ["account", "customer", "transaction"],
        hierarchy_depth: 1,
        is_required: false
      }
    ],
    options: {
      on_duplicate: "update",
      validate_only: false
    }
})
```

**Import Options**:

| Option | Description | Values | Default |
|--------|-------------|--------|---------|
| `on_duplicate` | How to handle duplicates | `skip`, `update`, `error` | `skip` |
| `batch_size` | Records per batch | 1-1000 | 100 |
| `stop_on_error` | Stop on first error | true/false | false |
| `validate_only` | Dry run (no changes) | true/false | false |

**Validation Behavior**:

**Level 1: Field Validation**
- name is lowercase, alphanumeric, no spaces
- applies_to is a non-empty array
- hierarchy_depth is 1-5
- display_name is 1-200 chars

**Level 2: Business Rules**
- name is unique within organization
- applies_to contains valid values (account, customer, vendor, employee, project, fixed_asset, transaction)

**Level 3: Warnings**
- Missing description (warning, not error)
- hierarchy_depth > 3 (warning: may be too deep)

**Returns**:

```javascript
{
  "success": true,
  "import_id": "uuid-here",
  "object_type": "dimension_type",
  "imported": 3,
  "updated": 0,
  "skipped": 0,
  "errors_count": 0,
  "errors": [],
  "warnings": [],
  "created_ids": [42, 43, 44],
  "message": "Imported 3 records, updated 0, skipped 0, 0 errors"
}
```

---

### Dimension Value Import

Use the `dimension_value.import` workflow to bulk import dimension values.

**Workflow**: `dimension_value.import`

**Purpose**: Import multiple dimension values from templates, CSV files, or data migration

**Approval**: no approval step by default (configurable per organisation; the submit() result is authoritative).

**Use Cases**:
- Populate dimension values (departments, locations, projects)
- Import geographic hierarchies
- Data migration from legacy systems
- Template-based imports

**Payload**:

```javascript
{
  "object_type": "dimension_value",
  "records": [
    {
      "dimension_type_name": "department",
      "code": "ENG",
      "name": "Engineering",
      "description": "Engineering department",
      "sort_order": 1
    },
    {
      "dimension_type_name": "department",
      "code": "SALES",
      "name": "Sales",
      "description": "Sales department",
      "sort_order": 2
    }
  ],
  "options": {
    "on_duplicate": "update",
    "batch_size": 100,
    "stop_on_error": false,
    "validate_only": false
  }
}
```

**Example: Flat Values**:

```javascript
submit("dimension_value", "import", {
    records: [
      {
        dimension_type_name: "department",
        code: "ENG",
        name: "Engineering",
        sort_order: 1
      },
      {
        dimension_type_name: "department",
        code: "SALES",
        name: "Sales",
        sort_order: 2
      },
      {
        dimension_type_name: "department",
        code: "MKT",
        name: "Marketing",
        sort_order: 3
      },
      {
        dimension_type_name: "department",
        code: "FIN",
        name: "Finance",
        sort_order: 4
      }
    ],
    options: {
      on_duplicate: "skip"
    }
})
```

**Example: Hierarchical Values**:

```javascript
submit("dimension_value", "import", {
    records: [
      // Level 1: Root values
      {
        dimension_type_name: "location",
        code: "USA",
        name: "United States",
        sort_order: 1
      },
      {
        dimension_type_name: "location",
        code: "EUR",
        name: "Europe",
        sort_order: 2
      },

      // Level 2: Children of USA
      {
        dimension_type_name: "location",
        code: "WEST",
        name: "West Region",
        parent_code: "USA",
        sort_order: 1
      },
      {
        dimension_type_name: "location",
        code: "EAST",
        name: "East Region",
        parent_code: "USA",
        sort_order: 2
      },

      // Level 3: Children of WEST
      {
        dimension_type_name: "location",
        code: "CA",
        name: "California",
        parent_code: "WEST",
        sort_order: 1
      },
      {
        dimension_type_name: "location",
        code: "OR",
        name: "Oregon",
        parent_code: "WEST",
        sort_order: 2
      },

      // Level 3: Children of EAST
      {
        dimension_type_name: "location",
        code: "NY",
        name: "New York",
        parent_code: "EAST",
        sort_order: 1
      }
    ],
    options: {
      on_duplicate: "skip"
    }
})
```

**Import Options**:

| Option | Description | Values | Default |
|--------|-------------|--------|---------|
| `on_duplicate` | How to handle duplicates | `skip`, `update`, `error` | `skip` |
| `batch_size` | Records per batch | 1-1000 | 100 |
| `stop_on_error` | Stop on first error | true/false | false |
| `validate_only` | Dry run (no changes) | true/false | false |

**Validation Behavior**:

**Level 1: Field Validation**
- code is 1-50 chars
- name is 1-200 chars
- dimension_type_name is provided

**Level 2: Foreign Key Validation**
- dimension_type_name exists
- parent_code references existing value (if provided)

**Level 3: Business Rules & Duplicates**
- code is unique within dimension type
- Hierarchy depth does not exceed type's hierarchy_depth
- No circular references (A cannot be parent of B if B is ancestor of A)

**Warnings** (not errors):
- Missing description
- Missing sort_order

**Returns**:

```javascript
{
  "success": true,
  "import_id": "uuid-here",
  "object_type": "dimension_value",
  "imported": 10,
  "updated": 0,
  "skipped": 0,
  "errors_count": 0,
  "errors": [],
  "warnings": [
    {
      "row": 3,
      "field": "description",
      "message": "Missing description (optional)",
      "record_identifier": "MKT"
    }
  ],
  "created_ids": [128, 129, 130, 131, 132, 133, 134, 135, 136, 137],
  "message": "Imported 10 records, updated 0, skipped 0, 0 errors"
}
```

---

## Metadata Best Practices

### What to Store in Metadata

**Good Use Cases**:
- Budget codes: `{"budget_code": "B001"}`
- Manager information: `{"manager": "Jane Smith", "manager_email": "jane@company.com"}`
- External system IDs: `{"external_id": "EXT-123", "source_system": "legacy_erp"}`
- Custom attributes: `{"color": "#FF5733", "icon": "building"}`
- Project details: `{"start_date": "2025-01-01", "end_date": "2025-12-31", "budget": 150000}`

**Bad Use Cases** (use regular fields instead):
- Display names (use `name` field)
- Descriptions (use `description` field)
- Parent relationships (use `parent_code`)
- Active status (use `is_active`)

### Metadata Schema Example

```javascript
{
  // Department metadata
  "manager": "Alice Johnson",
  "manager_email": "alice@company.com",
  "budget_code": "B001",
  "cost_center": "CC-100",
  "headcount": 45
}

{
  // Project metadata
  "project_manager": "Bob Smith",
  "start_date": "2025-01-01",
  "end_date": "2025-06-30",
  "budget": 150000,
  "status": "active",
  "client": "ACME Corp"
}

{
  // Location metadata
  "timezone": "America/Los_Angeles",
  "country_code": "US",
  "currency": "USD",
  "office_address": "123 Main St, San Francisco, CA 94105"
}
```

---

## Query Tools

### Dimension Types

| Tool | Purpose |
|------|---------|
| `get_entity("dimension_type", id=X)` | Get single dimension type |
| `query("dimension_type", filters)` | List dimension types with filters |
| `query("dimension_type", query)` | Search by name or display name |

### Dimension Values

| Tool | Purpose |
|------|---------|
| `get_entity("dimension_value", id=X)` | Get single dimension value |
| `query("dimension_value", filters)` | List values with filters |
| `query("dimension_value", query, filters)` | Search by code or name |

**Key notes:**
- `get_entity` defaults to `include_related=True` — related data included automatically
- Use `query` for filter-based queries, `query` for text-based

**Example Queries**:

```javascript
// List all dimension types
query("dimension_type")

// Find required dimensions
query("dimension_type", filters={"is_required": true})

// Find all department values
query("dimension_value", filters={"dimension_type_id": <id from query("dimension_type")>})

// Search dimension values by text
query("dimension_value", query="Engineering")
```

---

## Common Scenarios

### Scenario 1: Set Up Standard Dimensions

**Goal**: Create department, project, and location dimensions

```javascript
// Step 1: Create dimension types
submit("dimension_type", "import", {
    records: [
      {
        name: "department",
        display_name: "Department",
        applies_to: ["account", "transaction"],
        hierarchy_depth: 2,
        is_required: true
      },
      {
        name: "project",
        display_name: "Project",
        applies_to: ["account", "customer", "transaction"],
        hierarchy_depth: 1,
        is_required: false
      },
      {
        name: "location",
        display_name: "Location",
        applies_to: ["customer", "vendor"],
        hierarchy_depth: 3,
        is_required: false
      }
    ]
})

// Step 2: Create department values
submit("dimension_value", "import", {
    records: [
      {
        dimension_type_name: "department",
        code: "ENG",
        name: "Engineering",
        sort_order: 1
      },
      {
        dimension_type_name: "department",
        code: "SALES",
        name: "Sales",
        sort_order: 2
      },
      {
        dimension_type_name: "department",
        code: "MKT",
        name: "Marketing",
        sort_order: 3
      },
      {
        dimension_type_name: "department",
        code: "FIN",
        name: "Finance",
        sort_order: 4
      }
    ]
})

// Step 3: Create location hierarchy
submit("dimension_value", "import", {
    records: [
      // Level 1
      { dimension_type_name: "location", code: "USA", name: "United States", sort_order: 1 },
      // Level 2
      { dimension_type_name: "location", code: "WEST", name: "West Region", parent_code: "USA", sort_order: 1 },
      { dimension_type_name: "location", code: "EAST", name: "East Region", parent_code: "USA", sort_order: 2 },
      // Level 3
      { dimension_type_name: "location", code: "CA", name: "California", parent_code: "WEST", sort_order: 1 },
      { dimension_type_name: "location", code: "NY", name: "New York", parent_code: "EAST", sort_order: 1 }
    ]
})
```

**Result**:
- 3 dimension types created
- 4 department values created
- 5 location values created (hierarchical)

---

### Scenario 2: Entity-Specific Customization

**Goal**: Hide "project" dimension from Entity 9, rename "Sales" to "Revenue Operations" for Entity 13

```javascript
// Step 1: Hide project dimension from Entity 9
submit("dimension_type", "update", {
    dimension_type_name: "project",
    legal_entity_id: 9,
    is_visible: false
})

// Step 2: Rename department value for Entity 13
submit("dimension_value", "update", {
    dimension_type_name: "department",
    code: "SALES",
    legal_entity_id: 13,
    name_override: "Revenue Operations",
    description_override: "Sales and revenue generation team"
})
```

**Result**:
- Entity 9: Does NOT see "project" dimension
- Entity 13: Sees "Revenue Operations" instead of "Sales"
- Other entities: See standard "Sales" department

---

### Scenario 3: Regional Dimension Types

**Problem**: 450 location values (100 US + 200 EU + 150 APAC). Don't show all 450 to every entity.

**Solution**: Create regional dimension types, hide irrelevant ones per entity.

```javascript
// Step 1: Create 3 regional dimension types
submit("dimension_type", "import", {
    records: [
      {
        name: "location_us",
        display_name: "Location (US)",
        applies_to: ["transaction", "customer", "vendor"],
        hierarchy_depth: 3
      },
      {
        name: "location_eu",
        display_name: "Location (EU)",
        applies_to: ["transaction", "customer", "vendor"],
        hierarchy_depth: 3
      },
      {
        name: "location_apac",
        display_name: "Location (APAC)",
        applies_to: ["transaction", "customer", "vendor"],
        hierarchy_depth: 3
      }
    ]
})

// Step 2: Populate values (100 US, 200 EU, 150 APAC)
// ... bulk import for each region ...

// Step 3: Hide irrelevant types per entity

// US entities (9, 13) - hide EU and APAC
submit("dimension_type", "update", {
    dimension_type_name: "location_eu",
    legal_entity_id: 9,
    is_visible: false
})
submit("dimension_type", "update", {
    dimension_type_name: "location_apac",
    legal_entity_id: 9,
    is_visible: false
})

// EU entities (10, 14) - hide US and APAC
submit("dimension_type", "update", {
    dimension_type_name: "location_us",
    legal_entity_id: 10,
    is_visible: false
})
submit("dimension_type", "update", {
    dimension_type_name: "location_apac",
    legal_entity_id: 10,
    is_visible: false
})
```

**Result**:
- Entity 9 (US): Sees 100 US locations only
- Entity 10 (EU): Sees 200 EU locations only
- Entity 15 (APAC): Sees 150 APAC locations only

---

### Scenario 4: Migrate from Legacy System

**Goal**: Import 500 dimension values from legacy ERP

```javascript
// Import from CSV/JSON data
const legacyData = [
  // ... 500 records from legacy system ...
]

submit("dimension_value", "import", {
    records: legacyData.map(record => ({
      dimension_type_name: "cost_center",
      code: record.cost_center_code,
      name: record.cost_center_name,
      description: record.description,
      metadata: {
        external_id: record.legacy_id,
        source_system: "legacy_erp",
        imported_date: new Date().toISOString()
      }
    })),
    options: {
      on_duplicate: "update",
      batch_size: 100,
      stop_on_error: false
    }
})
```

**Result**:
- 500 cost center values imported
- Legacy IDs preserved in metadata
- Duplicates updated (not skipped)
- Batch processing for performance

---

## Transaction Dimension Scenarios

### How Dimensions Apply to Transactions

**Every transaction line** can have dimensions assigned, enabling multi-dimensional P&L reporting.

### Example: Sales Invoice with Dimensions

**Business Case**: Customer invoice with multi-dimensional tracking

```
Customer: ACME Corp
Invoice: INV-001234
Date: Oct 15, 2025
Total: $10,000

Line 1: Consulting Services ($6,000)
- Account: 4100 (Consulting Revenue)
- Dimensions:
  - Department: SALES
  - Location: US-NYC
  - Project: PROJ-ALPHA
  - Business Segment: B2B

Line 2: Training Services ($4,000)
- Account: 4200 (Training Revenue)
- Dimensions:
  - Department: ENG
  - Location: US-NYC
  - Project: PROJ-ALPHA
  - Business Segment: B2B

GL Posting:
DR 1200 (AR) $10,000
CR 4100 (Consulting Revenue) $6,000
   Dimensions: SALES, US-NYC, PROJ-ALPHA, B2B
CR 4200 (Training Revenue) $4,000
   Dimensions: ENG, US-NYC, PROJ-ALPHA, B2B
```

**Reporting Enabled**:
- Revenue by Department: Sales $6k, Engineering $4k
- Revenue by Project: Project Alpha $10k
- Revenue by Location: US-NYC $10k
- Revenue by Segment: B2B $10k

### Example: Expense with Multiple Departments

**Business Case**: Shared cloud expense allocated across departments

```
Vendor: Cloud Provider
Invoice: $12,000
Date: Oct 31, 2025

Usage Breakdown:
- Sales team: 30% = $3,600
- Engineering team: 50% = $6,000
- Operations team: 20% = $2,400

Transaction Lines:
Line 1: $3,600, Account: 6100, Dimensions: {department: SALES, cost_center: CC-100}
Line 2: $6,000, Account: 6100, Dimensions: {department: ENG, cost_center: CC-200}
Line 3: $2,400, Account: 6100, Dimensions: {department: OPS, cost_center: CC-300}

GL Posting:
DR 6100 $3,600 (SALES dimension)
DR 6100 $6,000 (ENG dimension)
DR 6100 $2,400 (OPS dimension)
CR 2100 (AP) $12,000
```

**Reporting Enabled**:
- Cloud expense by Department
- Cost center P&L
- Budget variance by team

---

## Integration Points

### Accounts

Dimensions can be assigned to GL accounts as defaults. There are two approaches:

**Approach 1: Via `account.create` or `account.update` workflows**

Pass `account_dimensions` in the payload to assign default dimensions during account creation or update:

```javascript
// Create account with default dimensions
submit("account", "create", {
    account_number: "6100",
    account_name: "Cloud Infrastructure",
    account_type: "expense",
    normal_balance: "debit",
    is_global: false,
    legal_entity_id: 13,
    account_dimensions: [
      { type_code: "department", value_code: "ENG" },
      { type_code: "cost_center", value_code: "CC-200" }
      // also accepted: { master_dimension_type_id, master_dimension_value_id },
      // or legacy { dimension_type_id, dimension_value_id } read in the EFFECTIVE namespace
    ]
})

// Update account dimensions (_action: add | update | delete — delete needs only the type)
submit("account", "update", {
    account_number: "6100",
    legal_entity_id: 13,
    account_dimensions: [
      { _action: "add", type_code: "location", value_code: "TLL" },
      { _action: "delete", type_code: "cost_center" }
    ]
})
```

**Approach 2: Via `account_dimension.assign` workflow**

Use the dedicated workflow for standalone dimension assignment:

```javascript
submit("account_dimension", "assign", {
    account_id: 45,
    legal_entity_id: 13,
    dimension_type: "department",
    dimension_value: "ENG"          // legacy dimension_type_id/dimension_value_id still accepted (effective namespace)
})
```

**Result**: All transactions to account 6100 default to department=ENG, cost_center=CC-200

### Customers

Dimensions can be assigned to customers for automatic transaction tagging:

```javascript
// Create customer with dimensions
submit("customer", "create", {
    customer_name: "ACME Corp",
    dimensions: {
      location: "US-NYC",
      business_segment: "B2B",
      customer_segment: "Enterprise"
    }
})
```

**Result**: All customer transactions inherit these dimensions (can be overridden at transaction level)

### Vendors

Dimensions can be assigned to vendors:

```javascript
// Create vendor with dimensions
submit("vendor", "create", {
    vendor_name: "Cloud Provider Inc",
    dimensions: {
      cost_center: "CC-300",
      location: "US-CA"
    }
})
```

### Budgets

Budget lines support dimensions for multi-dimensional budgeting:

```javascript
{
  "budget_version_id": 32,
  "lines": [
    {
      "account_number": "6000",
      "period_sequence": 1,
      "amount": 140000,
      "dimensions": {"department": "ENG"},
      "memo": "Engineering salaries Q1"
    },
    {
      "account_number": "6000",
      "period_sequence": 1,
      "amount": 95000,
      "dimensions": {"department": "SALES"},
      "memo": "Sales salaries Q1"
    }
  ]
}
```

**Result**: Budget variance analysis by dimension

---

## Reporting Examples

### Multi-Dimensional P&L

```sql
SELECT
  d_dept.name AS department,
  d_location.name AS location,
  SUM(jl.credit - jl.debit) AS amount
FROM journal_lines jl
JOIN dimension_values d_dept ON jl.dimension_department_id = d_dept.id
JOIN dimension_values d_location ON jl.dimension_location_id = d_location.id
WHERE jl.account_id IN (SELECT id FROM accounts WHERE account_type = 'Revenue')
  AND jl.posting_date BETWEEN '2025-10-01' AND '2025-10-31'
GROUP BY d_dept.name, d_location.name
ORDER BY amount DESC;
```

**Output**:
```
Department   | Location | Amount
-------------|----------|----------
Engineering  | US-NYC   | $150,000
Sales        | US-SF    | $120,000
Engineering  | EU-LON   | $100,000
Sales        | US-NYC   | $80,000
```

### Project Profitability

```sql
SELECT
  d_project.name AS project,
  SUM(CASE WHEN a.account_type = 'Revenue' THEN jl.credit - jl.debit ELSE 0 END) AS revenue,
  SUM(CASE WHEN a.account_type = 'Expense' THEN jl.debit - jl.credit ELSE 0 END) AS expenses,
  SUM(CASE WHEN a.account_type = 'Revenue' THEN jl.credit - jl.debit ELSE 0 END) -
  SUM(CASE WHEN a.account_type = 'Expense' THEN jl.debit - jl.credit ELSE 0 END) AS profit
FROM journal_lines jl
JOIN accounts a ON jl.account_id = a.id
JOIN dimension_values d_project ON jl.dimension_project_id = d_project.id
WHERE jl.posting_date BETWEEN '2025-01-01' AND '2025-12-31'
GROUP BY d_project.name
ORDER BY profit DESC;
```

**Output**:
```
Project         | Revenue  | Expenses | Profit
----------------|----------|----------|----------
PROJ-ALPHA      | $500,000 | $300,000 | $200,000
PROJ-BETA       | $300,000 | $250,000 | $50,000
```

---

## Migration from Old Tools

The dimension management system has migrated from individual tools to workflows.

### Deprecated Dimension Type Tools

| Old Tool | Workflow | Notes |
|----------|----------|-------|
| `create_master_dimension_type` | `dimension_type.create` | Organization-wide type |
| `update_master_dimension_type` | `dimension_type.update` | Omit `legal_entity_id` |
| `create_dimension_type_per_entity` | `dimension_type.update` | Include `legal_entity_id` |
| `update_dimension_type_per_entity` | `dimension_type.update` | Include `legal_entity_id` |
| `delete_dimension_type_per_entity` | `dimension_type.delete` | Include `legal_entity_id` |

### Deprecated Dimension Value Tools

| Old Tool | Workflow | Notes |
|----------|----------|-------|
| `create_master_dimension_value` | `dimension_value.create` | Organization-wide value |
| `update_master_dimension_value` | `dimension_value.update` | Omit `legal_entity_id` |
| `delete_master_dimension_value` | `dimension_value.delete` | Soft delete |
| `create_dimension_value_per_entity` | `dimension_value.update` | Include `legal_entity_id` |
| `update_dimension_value_per_entity` | `dimension_value.update` | Include `legal_entity_id` |
| `delete_dimension_value_per_entity` | `dimension_value.delete` | Include `legal_entity_id` |

---

## Key Takeaways

1. **Two-Level Structure**: Types define categories, values define options
2. **MSEO Pattern**: Both types and values use MSEO (master + overrides + effective views)
3. **Hierarchical Support**: Parent/child relationships with auto-calculated level and full_path
4. **Entity Overrides**: Customize types and values per entity without changing master
5. **Applies-To**: Controls which entities can use each dimension type (account, customer, vendor, employee, project, fixed_asset, transaction)
6. **Transaction Dimensions**: Line-level tagging enables multi-dimensional P&L
7. **Budget Dimensions**: Multi-dimensional budgeting with automatic JSON sync
8. **Bulk Import**: Import dimension types and values in batches
9. **Soft Delete Default**: Hard delete only for unused types/values
10. **Global IDs**: DIMT-XXXXXX for types, DIMV-XXXXXX for values

**Dimensions enable deep financial analysis beyond the chart of accounts, supporting project tracking, cost center reporting, location analysis, customer segments, and custom business intelligence.**

---

**End of Dimensions Management Guide**

## Transaction desired state, version 1

`dimension_state` is an additive transaction submission/edit contract. The header and each selected line are replacement scopes. Omitted scopes are unchanged, `[]` clears supplied assignments, null is invalid. Lines use zero-based `line_index`; they do not carry or change amounts. A cleared explicit line may still inherit a header or receive a configured workflow default.

```json
{
  "dimension_state": {
    "version": 1,
    "header": [],
    "lines": [
      {"line_index": 0, "values": [{"type_code": "department", "value_code": "SALES"}]},
      {"line_index": 1, "values": []}
    ]
  }
}
```

On initial submission include the ordinary transaction fields and lines. Do not combine desired state with a competing dimension representation in the same scope. For a pending workflow, read `get_submissions(action="task_details", task_id=...)`, then send the returned `payload_hash` as `expected_payload_hash` to `manage_submissions(action="edit_payload", ...)`. Versioned edits require it. The row lock and revision comparison refuse stale changes; a material change after any recorded approval requires rejection and resubmission.

## Workflow policy and approval

Workflow `related_entity_rules.<transaction_type_code>.dimension_policy` supports:

```json
{
  "version": 1,
  "dimensions": [{
    "type_code": "department",
    "header": "optional",
    "line": "required",
    "inherit_header_to_lines": true,
    "allow_line_override": true,
    "header_derivation": "none",
    "line_roles": ["business"],
    "default_sources": ["vendor", "account"]
  }]
}
```

Explicit line values take precedence; permitted header inheritance and explicit legacy line defaults follow. Configured source defaults fill missing line types in their listed order. Supported sources are vendor, customer, employee and account. They select classifications, never amounts or allocations. Invalid selected defaults fail. Record workflows support `record: "required"`; header/line/default-source settings belong to transaction workflows.

Required headers must be explicit unless `predominant_amount` is configured. A tie fails; it does not pick an arbitrary department. Legacy relation requirements are enforced only when that relation is required. Deprecated catalogue `is_required` flags do not define workflow requirements.

Before approval, the payload freezes resolved master identities, per-line provenance and policy hash. Posting rechecks eligibility and policy while holding the policy/catalogue lock. Changed defaults cannot replace approved classifications. Policy changes or ineligible approved values require review. Reversal copies original line identity, provenance, currency amounts and source-line linkage, including inactive historical values.

Database triggers validate required-policy satisfiability at activation and after catalogue/entity/transaction-setting changes. They are deferred so a single transaction can replace the last eligible value or amend policy and catalogue together. Changes serialize per organisation. Current-date checks do not predict future scheduled expiry; posting also validates the transaction date.

## Reporting and content delivery

Reports aggregate stored GL-line identities, include unassigned rows and reversing entries, and never join through today's default assignments to reconstruct history. Unresolved identity is an audit error. Budget comparison uses stored classifications, supplied amounts, entity, account, currency and actual fiscal-period boundaries. Overlapping budget scopes are independently evaluated and their actuals are not additive.

Base-template refresh preserves customized active files and creates pending candidates for conflicts. Pristine replacements retain archived rollback copies. A conflicted refresh does not advance the installed version. Generated IDE resources include this contract through the dimensions/transaction resources. Plugin publishing and remote template refresh remain release operations.

## Configure transaction dimension defaults

Default sources are set through Claude, not in the admin dashboard: the workflow pages show which dimension types a transaction type requires but have no editor for default sources. Use `manage_workflow` on Transaction Posting (`get` for the revision, then `draft` or `update`) with `changes.related_rules` = `{"transaction_type_code": "AP_INVOICE", "rules": {}, "dimension_policy": {"version": 1, "dimensions": [{"type_code": "department", "default_sources": ["employee", "vendor"]}]}}`, or set an entity override's `override_config.dimension_policy` for one legal entity. Vendor, Customer, Employee and Account are the sources; they are consulted in the listed order. A change applies only to the named transaction type. Dashboard saves keep the stored policy as it is.

An empty source list enables no defaults. Explicit values take precedence. Employee defaults for card purchases and linked receipts use the verified cardholder context; they do not extract dimension codes from business-purpose prose. Configure AP_INVOICE and CARD_EXPENSE separately when both should inherit employee defaults. A project classification must be explicitly supplied unless it exists in an eligible configured source.

A policy change through `manage_workflow` replaces the dimension policy you send; read it with `get_workflow(action="get")` first and send it back with only the source order changed, so required header/line rules, inheritance and override restrictions stay as they were. Other related-entity rules are unchanged. It does not automatically enable defaults for existing tenants or rewrite posted records. Approved snapshots remain frozen; changes to policy can require pending submissions to be reviewed again.

Release verification: editor tests and type checking passed locally; production deployment and fresh card receipt verification are pending.


Supplied record dimension commands are validated during a workflow dry run even
when that workflow has no optional collection rules configured. Valid dimensions
remain optional; invalid codes, identities, scope or eligibility are refused.
Omitting a collection does not add a requirement to supply it.
