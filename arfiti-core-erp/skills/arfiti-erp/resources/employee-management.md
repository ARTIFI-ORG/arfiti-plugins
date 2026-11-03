# Employee Management Guide

> **MSEO release contract:** Master employee IDs identify people; payroll/compensation keep legal-entity employment scope even where their numeric IDs equal the master. A person ID is not a dimension value ID. See the dimensions-management resource for assignment, approval and compatibility rules.

This guide explains how to manage employees in the AI-Native ERP system.

---

## Overview

Employees are the people who work for your organization. The workflow system ensures proper HR authorization, audit trails, and risk-based approvals for all employee operations.

**What you can do:**
- Create new employees with bank accounts, addresses, and dimensions
- Update employee information (promotions, transfers, manager changes)
- Query employee data (single employee, search/filter)
- Terminate employees (soft delete) or remove test data (hard delete)

**Available Workflows:**

| Workflow | Purpose | When to Use |
|----------|---------|-------------|
| `employee.create` (fields: `get_submissions(action="schema", object_type, operation)`) | Create new employee | Onboarding new hire |
| `employee.update` (fields: `get_submissions(action="schema", object_type, operation)`) | Update employee data | Promotion, transfer, manager change |
| `employee.delete` (fields: `get_submissions(action="schema", object_type, operation)`) | Terminate employee | Resignation or termination |

**Available Query Tools:**

| Tool | Purpose |
|------|---------|
| `get_entity("employee", id=X)` | Get single employee (includes addresses, bank accounts, dimensions, direct reports) |
| `query("employee", filters)` | List employees with filters and pagination |
| `query("employee", query, filters)` | Search employees by text |
| `query("employee", filters, limit=1)` | Count matching employees (use `total_count` from response) |
| `get_submissions(action='schema', object_type="employee", operation="create")` | Get field schema before creating |
| `get_submissions(action='schema', object_type="employee", operation="update")` | Get update field schema |
| `query(entity_type, filters={...})` ×N | Fetch departments, dimensions, accounts (parallel calls) before creating employees |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

**Key notes:**
- `get_entity` defaults to `include_related=True` — addresses, bank accounts, dimensions, vendor mapping, direct reports included
- Search/list results now include: `employee_number`, `first_name`, `last_name`, `work_email`, `job_title`, `department`, `employment_type`, `hire_date`, `location`, `cost_center`, `status`
- Searchable fields: `first_name`, `last_name`, `work_email`, `personal_email`, `job_title`, `department`, `notes`, `global_employee_id`, `employee_number`
- Filter by: `legal_entity_id`, `status`, `department`, `location`, `employment_type`, `manager_employee_id`
- Sort by: `last_name`, `first_name`, `employee_number`, `hire_date`

---

## Custom Fields

Organisations define their own employee fields. Before putting a business fact
into `metadata`, check `get_submissions(action="schema", object_type="employee", operation="create")`
→ `custom_fields` (key, type, limits, options, required). Set values with
`"custom_fields": {"key": value}`; on update keys you leave out are unchanged
and `"custom_fields_clear": ["key"]` empties one; never send `null`. Decimals
as numeric strings, dates `YYYY-MM-DD`, choice = one option `value`. Filter
with `query("employee", filters={"custom_fields.<key>": value}). Do not store personal data in a custom field: its values appear in the change history in full.
All rules (register, types, required fields, transactions, filters, import, merge): the custom-fields resource; full contract `docs/GUIDES/GUIDE_CUSTOM_FIELDS.md`.

## Complete Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

### Master Employee Fields (master_employees table)

**Required Fields:**
- `first_name` (string, 1-100 chars) - Employee first name
- `last_name` (string, 1-100 chars) - Employee last name
- `work_email` (string, valid email, unique) - Company email address
- `hire_date` (date, YYYY-MM-DD) - First day of employment

**Personal Information:**
- `preferred_name` (string, max 100) - Preferred or nickname
- `personal_email` (string, max 255) - Personal email address
- `personal_phone` (string, max 50) - Personal phone number
- `date_of_birth` (date, YYYY-MM-DD) - Birth date
- `gender` (string, max 20) - Gender identity
- `nationality` (string, max 100) - Nationality/citizenship
- `notes` (text) - Internal HR notes

**Emergency Contact:**
- `emergency_contact_name` (string, max 255) - Emergency contact full name
- `emergency_contact_phone` (string, max 50) - Emergency contact phone
- `emergency_contact_relationship` (string, max 100) - Relationship (spouse, parent, sibling, friend)

**Employment Status:**
- `status` (enum, default: active) - Current employment status
  - Options: `active`, `terminated`, `on_leave`
- `termination_date` (date) - Last day of employment (if terminated)
- `termination_reason` (text) - Reason for termination

**System & Audit:**
- `global_employee_id` (string, auto-generated) - Organization-wide unique ID (e.g., EMP-000001)
- `user_id` (integer, FK) - Link to user account (if applicable)
- `metadata` (jsonb) - Custom fields (see [Metadata Best Practices](#metadata-best-practices))
- `created_at`, `updated_at`, `created_by`, `updated_by` - Audit fields

**Scope & Visibility (unified MSEO contract — single mode):**
`employee.create` is `SCOPE_MODE='single'` — every employee attaches to exactly ONE legal_entity. The base class rejects every other shape:

- `legal_entity_id` (integer, **required**) — the entity this employee attaches to. The auth path auto-fills this for new hires created during user provisioning (`auth_unified.py`).
- `is_global=true` → **REJECTED** ("is_global=True is not allowed for employee").
- `legal_entity_ids=[a,b]` → **REJECTED** ("employee attaches to one entity — pass legal_entity_id (singular)").
- `is_global=false` + neither ID → **REJECTED** ("legal_entity_id is required when is_global=False"). Pre-Batch C this silently produced a master-only employee — was Bug 7.

Per-employee dependent payloads (`employee_dimensions`, `employee_bank_accounts`, `employee_vendor_mappings`) all attach to the single entity row. See GUIDE_MSEO_PATTERN.md for the full contract.

### Entity Assignment Fields (employees table)

Employees can be assigned to one or more legal entities with different roles:

**Assignment Fields:**
- `employee_number` (string, auto-generated) - Entity-specific employee number
- `job_title` (string, max 255) - Position title
- `department` (string, max 100) - Department name
- `cost_center` (string, max 50) - Cost center code
- `location` (string, max 100) - Work location
- `employment_type` (enum) - Employment classification
  - Options: `full_time`, `part_time`, `contractor`, `intern`

**Manager Hierarchy:**
- `manager_employee_id` (integer, FK) - Direct manager's entity employee ID
- `manager_path` (integer array) - Full management chain (auto-calculated)
- `manager_level` (integer) - Depth in org chart (auto-calculated)

**Assignment Period:**
- `effective_from` (date, default: today) - Assignment start date
- `effective_to` (date) - Assignment end date (null = current)
- `status` (enum, default: active) - Assignment status
  - Options: `active`, `inactive`, `on_leave`

**System:**
- `created_at`, `updated_at`, `created_by`, `updated_by` - Audit fields

### Employee Addresses (employee_addresses table)

**Required:**
- `address_line_1` (string, max 255) - Street address
- `country` (string, max 100) - Country name
- `address_type` (enum, default: home) - Address classification
  - Options: `home`, `mailing`, `work`, `emergency`, `tax`, `other`

**Optional:**
- `address_line_2` (string, max 255) - Apt/Suite/Floor
- `city` (string, max 100) - City name
- `state_province` (string, max 100) - State/province/region
- `postal_code` (string, max 50) - ZIP/postal code
- `notes` (text) - Address-specific notes

**Flags:**
- `is_primary` (boolean, default: false) - Primary address (only one per employee/entity)
- `is_mailing` (boolean, default: false) - Use for mail delivery
- `is_active` (boolean, default: true) - Active address

**Period:**
- `effective_from` (date, default: today) - Address valid from
- `effective_to` (date) - Address valid until (null = current)

**System:**
- `created_at`, `updated_at`, `created_by`, `updated_by` - Audit fields

**Tip:** You can have multiple addresses of different types. Use both `address_type` and boolean flags for flexibility.

**How to write one:** either the `employee_addresses` block on
`submit("employee", "create"|"update", ...)` (with `_action`: add / update /
delete), or the dedicated `submit("employee_address", "create"|"update"|"delete", ...)`
workflow when the employee already exists. Both write the same rows. Setting
`is_primary` clears the flag on the employee's other addresses.

### Employee Bank Accounts (employee_bank_accounts table)

Secure storage for employee payment account details (payroll, reimbursements).

**Required:**
- `payment_method` (enum, default: ach) - Type of payment
  - Options: `ach`, `wire`, `check`, `paycard`, `other`
- `usage_type` (enum) - Purpose of account
  - Options: `payroll`, `benefit`, `stipend`, `reimbursement`
- `currency_code` (string, 3 chars, default: USD) - Account currency
- `account_holder_name` (string, max 255) - Legal name on account

**US Bank Accounts (ACH):**
- `bank_name` (string, max 255) - Name of financial institution
- `routing_number` (string, max 100) - 9-digit ABA routing number
- `account_number` (string, max 100) - Account number (encrypted at rest)
- `account_type` (enum) - Account classification
  - Options: `checking`, `savings`, `paycard`, `other`

**International Bank Accounts:**
- `iban` (string, max 50) - International Bank Account Number
- `swift_code` (string, max 20) - SWIFT/BIC code
- `bank_country` (string, 2 chars) - ISO country code
- `account_holder_address` (text) - Full address of account holder

**Deposit Configuration:**
- `account_nickname` (string, max 100) - Friendly name for identification
- `deposit_allocation_type` (enum) - How to split deposit
  - Options: `amount` (fixed dollar amount), `percentage` (% of net pay), `remainder` (rest after other accounts)
- `deposit_amount` (decimal 15,2) - Fixed amount (if allocation_type = amount)
- `deposit_percentage` (decimal 5,2) - Percentage 0-100 (if allocation_type = percentage)
- `deposit_order` (integer, default: 1) - Order for split deposit processing

**Verification:**
- `verification_status` (enum, default: unverified) - Account verification state
  - Options: `unverified`, `pending`, `verified`, `failed`
- `verification_method` (string, max 50) - How account was verified
- `verified_at` (timestamp) - When verification completed
- `verified_by` (integer, FK) - User who verified
- `prenote_sent_at` (timestamp) - When prenote ACH was sent
- `prenote_cleared_at` (timestamp) - When prenote cleared successfully
- `prenote_status` (string, max 50) - Prenote processing status

**Flags:**
- `is_default` (boolean, default: false) - Primary account for this usage type
- `is_active` (boolean, default: true) - Active for payments

**Integration:**
- `connector_id` (uuid) - Banking connector ID if synced
- `external_account_id` (string, max 100) - External system identifier
- `metadata` (jsonb) - Additional account data

**System:**
- `created_at`, `updated_at`, `created_by`, `updated_by` - Audit fields
- `deleted_at`, `deleted_by` - Soft delete tracking

**Security:** Account numbers and routing numbers are encrypted at rest. Only authorized payroll/HR users can view full account details.

**Split Deposits:** Configure multiple bank accounts with different allocation types:
- Account 1: `amount` = $500 (savings, order 1)
- Account 2: `percentage` = 10% (401k contribution, order 2)
- Account 3: `remainder` (checking, order 3 - gets the rest)

### Employee Dimensions (employee_dimensions table)

Tag employees with analytical dimensions for reporting and cost allocation.

**Command fields** — one command per dimension type, e.g. `{ "type_code": "department", "value_code": "ENG" }`:
**Dimension reference forms** (one per command; several spellings in one command must agree):
- Codes (preferred): `type_code` + `value_code` (aliases `dimension_type` + `dimension_value`)
- Explicit master ids: `master_dimension_type_id` + `master_dimension_value_id`
- Legacy ids: `dimension_type_id` + `dimension_value_id` — read in the endpoint's EFFECTIVE namespace, never as master catalogue ids. The `id` a validation error's `reference_data.dimension_values` returns is a master id: send it as `master_dimension_value_id`, or send the entry's `type_code`/`value_code`.
- `_action`: `add` (default), `update` or `delete` on `employee.update` — `delete` needs only the type
- The type must apply to employees (`master_dimension_types.applies_to`), which the dry run (`validate_only`) checks too

**Dimensions are automatically applied to:**
- Payroll entries for this employee
- Expense reports submitted by employee
- Time tracking and project allocation
- Reports filtered by dimension

**Getting Reference Data:**
- Dimensions: `query("dimension_type")` lists the types (with `applies_to`); `query("dimension_value", filters={"dimension_type_id": X})` lists a type's values. Send their **codes** (`type_code`/`value_code`) or the ids as `master_dimension_*_id` — the `id` these return is the master catalogue id, not a legacy `dimension_value_id`

### Employee Vendor Mappings (employee_vendor_mappings table)

Link contractor employees to vendor records for 1099 payment tracking.

**Fields:**
- `vendor_id` (integer, FK) - Entity-specific vendor ID
- `global_vendor_id` (string) - Global vendor identifier (e.g., VEND-000123)
- `is_primary` (boolean, default: false) - Primary vendor for this employee
- `is_active` (boolean, default: true) - Active mapping

**System:**
- `created_at`, `updated_at`, `created_by`, `updated_by` - Audit fields

**Use Case:** Contractor employees with `employment_type='contractor'` should be mapped to vendor records. Payments flow through AP (vendor payments) for proper 1099 tracking.

---

## Metadata Best Practices

The `metadata` JSONB field allows storing custom data without schema changes.

### When to Use Metadata

✅ **Good use cases:**
- Employee-specific attributes that vary widely (employee ID from legacy system, badge number)
- Integration IDs from external systems (Workday, ADP, BambooHR)
- Temporary attributes during migration or testing
- Rarely-queried supplementary information
- Custom fields specific to your organization

❌ **Bad use cases:**
- Frequently queried fields (use real columns for performance)
- Fields requiring complex validation (use Pydantic models)
- Fields that need database constraints or indexes
- Standard HR data (use dedicated tables)

### Metadata Structure Tips

1. **Check existing employees first** before adding new metadata fields:
   ```
   Use get_entity("employee", id=123) to see existing metadata structure
   ```

2. **Use consistent field names** across all employees:
   ```json
   {
     "workday_id": "WD-12345",
     "badge_number": "BADGE-789",
     "shirt_size": "M",
     "parking_spot": "P-123",
     "dietary_restrictions": ["vegetarian", "gluten-free"]
   }
   ```

3. **Namespace integration data** to avoid conflicts:
   ```json
   {
     "integrations": {
       "workday": {"employee_id": "WD-12345", "last_sync": "2025-01-15T10:30:00Z"},
       "adp": {"file_number": "ADP-789", "payroll_code": "P123"}
     }
   }
   ```

4. **Document your metadata schema** in your organization's wiki or knowledge base

5. **Query metadata** using PostgreSQL JSON functions:
   ```sql
   SELECT * FROM master_employees
   WHERE metadata->>'badge_number' = 'BADGE-789'
   ```

### Updating Metadata

**Add new field:**
```json
{
  "global_employee_id": "EMP-000001",
  "metadata": {
    "existing_field": "value",
    "new_field": "new_value"
  }
}
```

**Remove field:**
```json
{
  "global_employee_id": "EMP-000001",
  "metadata": {
    "existing_field": "value"
    // Simply omit the field you want to remove
  }
}
```

**Tip:** Metadata updates are full replacements, not merges. Always include all fields you want to keep.

---

## Creating an Employee

Use the `employee.create` workflow to add new employees.

**See:** employee.create definition (fields: `get_submissions(action="schema", object_type, operation)`) for complete field details

### Basic Employee

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="employee", operation="create")

// Step 2: Submit with discovered fields
submit("employee", "create", '{...}')
// Tip: Use validate_only=true to check payload before submitting
```

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "work_email": "john.doe@company.com",
  "hire_date": "2025-01-15",
  "legal_entity_id": 13,
  "job_title": "Software Engineer",
  "department": "Engineering",
  "employment_type": "full_time"
}
```

**Getting Reference Data:**
- Legal Entities: Use `query("legal_entity")` to get valid `legal_entity_id` values

### Employee with Manager

Assign a reporting manager using their global employee ID:

```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "work_email": "jane.smith@company.com",
  "hire_date": "2025-02-01",
  "legal_entity_id": 13,
  "job_title": "Junior Developer",
  "department": "Engineering",
  "manager_global_employee_id": "EMP-000005"
}
```

### Employee with Bank Account (Direct Deposit)

For payroll direct deposit:

```json
{
  "first_name": "Michael",
  "last_name": "Johnson",
  "work_email": "mjohnson@company.com",
  "hire_date": "2025-01-20",
  "legal_entity_id": 13,
  "job_title": "Accountant",
  "department": "Finance",
  "employee_bank_accounts": [
    {
      "legal_entity_id": 13,
      "account_nickname": "Payroll Direct Deposit",
      "bank_name": "Chase Bank",
      "routing_number": "021000021",
      "account_number": "1234567890",
      "account_type": "checking",
      "usage_type": "payroll",
      "is_default": true
    }
  ]
}
```

### Employee with Address

Include home or work addresses:

```json
{
  "first_name": "Emily",
  "last_name": "Chen",
  "work_email": "echen@company.com",
  "hire_date": "2025-02-15",
  "legal_entity_id": 13,
  "job_title": "HR Coordinator",
  "department": "Human Resources",
  "date_of_birth": "1990-05-15",
  "gender": "female",
  "nationality": "USA",
  "personal_phone": "+1-555-1234",
  "personal_email": "emily.chen@personal.com",
  "emergency_contact_name": "David Chen",
  "emergency_contact_phone": "+1-555-5678",
  "emergency_contact_relationship": "spouse",
  "employee_addresses": [
    {
      "address_type": "home",
      "address_line_1": "456 Oak Street",
      "address_line_2": "Apt 12B",
      "city": "Portland",
      "state_province": "OR",
      "postal_code": "97201",
      "country": "USA",
      "is_primary": true,
      "is_mailing": true
    }
  ]
}
```

### Employee with Dimensions

Tag employees with location, cost center, or project:

```json
{
  "first_name": "Sarah",
  "last_name": "Williams",
  "work_email": "swilliams@company.com",
  "hire_date": "2025-03-01",
  "legal_entity_id": 13,
  "job_title": "Marketing Manager",
  "department": "Marketing",
  "employee_dimensions": [
    { "dimension_value_id": 35 },
    { "dimension_value_id": 42 }
  ]
}
```

**Getting Reference Data:**
- Dimensions: Use `query("dimension_type")` and `query("dimension_value", filters={"dimension_type_id": X})` to find available dimensions and values

### Contractor with Vendor Mapping

For contractors paid through the vendor system (1099 tracking):

```json
{
  "first_name": "Alex",
  "last_name": "Brown",
  "work_email": "abrown@consultant.com",
  "hire_date": "2025-01-10",
  "legal_entity_id": 13,
  "job_title": "Consultant",
  "department": "IT",
  "employment_type": "contractor",
  "vendor_mappings": [
    {
      "legal_entity_id": 13,
      "global_vendor_id": "VEND-000123",
      "is_primary": true
    }
  ]
}
```

**Getting Reference Data:**
- Vendors: Use `query("vendor")` to find existing vendor records for contractor mapping

### Employee with Custom Metadata

Store integration IDs and custom attributes:

```json
{
  "first_name": "David",
  "last_name": "Martinez",
  "work_email": "dmartinez@company.com",
  "hire_date": "2025-01-25",
  "legal_entity_id": 13,
  "job_title": "Operations Manager",
  "department": "Operations",
  "metadata": {
    "workday_id": "WD-12345",
    "badge_number": "BADGE-789",
    "shirt_size": "L",
    "parking_spot": "P-045",
    "dietary_restrictions": ["vegetarian"]
  }
}
```

---

## Updating an Employee

Use the `employee.update` workflow to modify existing employees.

**See:** employee.update definition (fields: `get_submissions(action="schema", object_type, operation)`) for complete field details

### Update Basic Information

Only include fields you want to change:

```json
{
  "global_employee_id": "EMP-000001",
  "preferred_name": "Johnny",
  "personal_phone": "+1-555-9999"
}
```

### Promotion (Job Title Change)

```json
{
  "global_employee_id": "EMP-000001",
  "legal_entity_id": 13,
  "job_title": "Senior Software Engineer",
  "cost_center": "ENG-002"
}
```

### Manager Change

```json
{
  "global_employee_id": "EMP-000001",
  "legal_entity_id": 13,
  "manager_global_employee_id": "EMP-000010"
}
```

Manager hierarchy is automatically rebuilt when managers change.

### Transfer to Different Entity

```json
{
  "global_employee_id": "EMP-000001",
  "legal_entity_id": 11,
  "job_title": "Engineering Lead - EMEA",
  "department": "Engineering",
  "cost_center": "ENG-UK-001",
  "manager_global_employee_id": "EMP-000050"
}
```

**Getting Reference Data:**
- Legal Entities: Use `query("legal_entity")` to find valid entity IDs for transfers

### Managing Related Data (Action Pattern)

For addresses, bank accounts, dimensions, and vendor mappings, use the `_action` field:

| Action | When to Use | Required Fields |
|--------|-------------|-----------------|
| `add` | Create new record | All fields for new record |
| `update` | Modify existing | `id` + fields to change |
| `delete` | Remove record | `id` only |

#### Add Bank Account

```json
{
  "global_employee_id": "EMP-000001",
  "employee_bank_accounts": [
    {
      "_action": "add",
      "legal_entity_id": 13,
      "account_nickname": "Secondary Account",
      "bank_name": "Wells Fargo",
      "routing_number": "121000248",
      "account_number": "9876543210",
      "account_type": "savings",
      "usage_type": "payroll",
      "is_default": false
    }
  ]
}
```

#### Update Address

```json
{
  "global_employee_id": "EMP-000001",
  "employee_addresses": [
    {
      "_action": "update",
      "id": 45,
      "address_line_1": "789 New Home Street",
      "city": "Austin"
    }
  ]
}
```

#### Delete Bank Account

```json
{
  "global_employee_id": "EMP-000001",
  "employee_bank_accounts": [
    {
      "_action": "delete",
      "id": 789
    }
  ]
}
```

#### Add Dimension

```json
{
  "global_employee_id": "EMP-000001",
  "employee_dimensions": [
    {
      "_action": "add",
      "dimension_value_id": 50
    }
  ]
}
```

**Getting Reference Data:**
- Dimensions: Use `query("dimension_value", filters={"dimension_type_id": X})` to find available dimension values and their IDs

> **Note:** Employee dimensions use `dimension_value_id` (numeric ID), not dimension names. Use `query("dimension_value", filters={"dimension_type_id": X})` to find valid IDs. For delete operations, use `dimension_type` (e.g., `"department"`) instead of an ID.

#### Update Metadata

```json
{
  "global_employee_id": "EMP-000001",
  "metadata": {
    "workday_id": "WD-12345",
    "badge_number": "BADGE-999",
    "shirt_size": "XL",
    "parking_spot": "P-100"
  }
}
```

**Tip:** Metadata updates replace the entire metadata object. Include all fields you want to keep.

---

## Querying Employees

### Get Single Employee (Recommended)

Use the unified `get_entity` tool:

```javascript
get_entity("employee", id=123)
```

**Response includes:**
- All master employee fields (name, email, hire date, personal info, emergency contact)
- Entity-specific assignment (job title, department, manager)
- Addresses array
- Bank accounts array (account numbers masked for security)
- Dimensions
- Vendor mappings (if contractor)

### Search Employees (Recommended)

Use the unified `query` tool:

```javascript
query("employee", query="John", filters={"legal_entity_id": 13, "status": "active"}, limit=50)
```

**Search capabilities:**
- Searches across: first_name, last_name, work_email, personal_email, job_title, department, notes, global_employee_id, employee_number
- Filter by: legal_entity_id, status, department, location, employment_type, manager_employee_id
- Sort by: last_name (default), first_name, employee_number, hire_date
- Pagination: limit and offset supported

---

## Terminating an Employee

Use the `employee.delete` workflow to terminate or remove employees.

**See:** employee.delete definition (fields: `get_submissions(action="schema", object_type, operation)`) for complete field details

### Soft Delete / Termination (Recommended)

Sets employment status to 'terminated' while preserving historical data:

```json
{
  "global_employee_id": "EMP-000001",
  "termination_date": "2025-12-31",
  "termination_reason": "Resigned - new opportunity",
  "hard_delete": false
}
```

**What happens:**
- Employee hidden from dropdowns and searches
- Cannot submit new expense reports or timesheets
- Historical payroll and expense data remains visible
- Audit trail preserved
- Can be reactivated if rehired

### Hard Delete (approval as configured)

Permanently removes all employee data:

```json
{
  "global_employee_id": "EMP-000099",
  "termination_reason": "Test employee cleanup - never actually hired",
  "hard_delete": true
}
```

**Use only for:**
- Test employee cleanup
- Duplicate records
- Data entry errors (never actually hired)

**Never use for employees with payroll or transaction history.**

---

## Reactivating an Employee

If a terminated employee is rehired, use the `employee.reactivate` workflow:

```javascript
submit("employee", "reactivate", '{
    "global_employee_id": "EMP-000001",
    "legal_entity_id": 13
}')
```

**What happens:**
- Employee status changes from `terminated` back to `active`
- Employee becomes visible in searches and dropdowns again
- Only works for employees with status `terminated`

---

## Rebuilding Employee Hierarchy

If manager assignments become out of sync (e.g., after bulk imports or manager changes), rebuild the hierarchy tree:

```javascript
submit("employee_hierarchy", "rebuild", '{
    "legal_entity_id": 13
}')
```

**What happens:**
- Recalculates `manager_path` and `manager_level` for all employees in the entity
- Fixes any broken hierarchy chains
- Safe to run at any time (idempotent)

---

## Bulk Import

For importing multiple employees at once:
- HRIS system synchronization
- Data migration from legacy systems
- CSV file uploads
- Validate before import (dry-run mode)
- Handle duplicates automatically (skip, update, or error)

### Import Workflow

Use the `employee.import` workflow:

```javascript
submit("employee", "import", {
    "legal_entity_id": 13,
    "records": [
      {
        "first_name": "Sarah",
        "last_name": "Johnson",
        "work_email": "sarah.johnson@company.com",
        "hire_date": "2025-02-01",
        "job_title": "Software Engineer",
        "department": "Engineering",
        "employment_type": "full_time",
        "personal_email": "sarah.j@gmail.com",
        "personal_phone": "+1-555-1234"
      },
      {
        "first_name": "Michael",
        "last_name": "Chen",
        "work_email": "michael.chen@company.com",
        "hire_date": "2025-02-15",
        "job_title": "Product Manager",
        "department": "Product",
        "employment_type": "full_time",
        "manager_global_employee_id": "EMP-000001"
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

Employees are considered duplicates if:
- **work_email** matches (case-insensitive)

### Required Fields for Import

- `first_name` (1-100 chars)
- `last_name` (1-100 chars)
- `work_email` (valid email format, unique)
- `hire_date` (date in YYYY-MM-DD format)

### Optional Fields for Import

- `preferred_name` (max 100 chars)
- `personal_email` (valid email, max 255 chars)
- `personal_phone` (max 50 chars)
- `date_of_birth` (date in YYYY-MM-DD format)
- `gender` (max 20 chars)
- `nationality` (max 100 chars)
- `emergency_contact_name` (max 255 chars)
- `emergency_contact_phone` (max 50 chars)
- `emergency_contact_relationship` (max 100 chars)
- `status` (active, terminated, on_leave, default: active)
- `termination_date` (date in YYYY-MM-DD format)
- `termination_reason` (text)
- `job_title` (max 255 chars)
- `department` (max 100 chars)
- `cost_center` (max 50 chars)
- `location` (max 255 chars)
- `employment_type` (full_time, part_time, contractor, intern)
- `manager_global_employee_id` (must exist)
- `notes` (text)
- `metadata` (JSONB)

### Validation Behavior

The importer performs comprehensive validation:
- **Field validation**: Data types, lengths, formats, required fields
- **Foreign key validation**: Verifies legal entity and manager exist
- **Business rule validation**: Email format, termination_date > hire_date, employment types/statuses
- **Duplicate detection**: Checks work_email (case-insensitive)
- **Warnings**: Missing emergency contact, similar employee names, terminated status on new import

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
      "field": "emergency_contact_name",
      "message": "Missing emergency contact information",
      "record_identifier": "john.doe@company.com"
    }
  ],
  "created_ids": [301, 302, 303, ...],
  "updated_ids": [125, 167, 189],
  "duration_ms": 3240
}
```

### Validate Before Importing (Dry Run)

Test your import without making changes:

```javascript
submit("employee", "import", {
    "legal_entity_id": 13,
    "records": [...],
    "options": {
      "validate_only": true
    }
})
```

This returns validation errors without creating any employees.

### Common Import Scenarios

**HRIS System Sync (Workday, BambooHR, ADP):**
```javascript
{
  "object_type": "employee",
  "legal_entity_id": 13,
  "records": employees_from_hris,
  "options": {
    "on_duplicate": "update",  // Update existing employees
    "stop_on_error": false     // Continue even if some fail
  }
}
```

**Data Migration:**
```javascript
{
  "object_type": "employee",
  "legal_entity_id": 13,
  "records": employees_from_legacy_system,
  "options": {
    "on_duplicate": "skip",    // Don't overwrite existing
    "validate_only": true,     // Test first
    "stop_on_error": true      // Stop if validation fails
  }
}
```

**New Hire Batch Import:**
```javascript
{
  "object_type": "employee",
  "legal_entity_id": 13,
  "records": new_hires_from_csv,
  "options": {
    "on_duplicate": "error",   // Flag duplicates
    "stop_on_error": true      // Stop if duplicate found
  }
}
```

**See:** PLAN_IMPORT.md for import system architecture

---

## Common Scenarios

### Onboard New Hire

1. Create employee with basic info, entity, and manager (`employee.create`)
2. Add bank account for payroll (after approval)
3. Tag with department/cost center dimensions
4. **Set up payroll** (required before employee can be included in payroll runs):
   - Create compensation record (`employee_compensation.create`) — salary/hourly rate
   - **Create tax settings** (`employee_tax_settings.create`) — **CRITICAL**: sets `country_code` which determines tax formula
     - For Estonia: set `pension_tier` ('2%', '4%', '6%', or NULL), `basic_exemption_applied`
     - For US: set `state_code`, `filing_status`
   - Create deductions (`employee_deduction.create`) — optional: pension III, health insurance, etc.

```json
{
  "first_name": "Alice",
  "last_name": "Johnson",
  "work_email": "alice.johnson@company.com",
  "hire_date": "2025-02-01",
  "legal_entity_id": 13,
  "job_title": "Product Manager",
  "department": "Product",
  "cost_center": "PROD-001",
  "manager_global_employee_id": "EMP-000010"
}
```

### Promote Employee

Update job title and optionally cost center:

```json
{
  "global_employee_id": "EMP-000001",
  "legal_entity_id": 13,
  "job_title": "Senior Software Engineer",
  "cost_center": "ENG-002"
}
```

### International Transfer

Transfer employee to different legal entity with new role:

```json
{
  "global_employee_id": "EMP-000001",
  "legal_entity_id": 11,
  "job_title": "Engineering Lead - EMEA",
  "department": "Engineering",
  "manager_global_employee_id": "EMP-000050"
}
```

### Add Direct Deposit

After employee provides bank details:

```json
{
  "global_employee_id": "EMP-000001",
  "employee_bank_accounts": [
    {
      "_action": "add",
      "legal_entity_id": 13,
      "account_nickname": "Payroll",
      "bank_name": "Chase",
      "routing_number": "021000021",
      "account_number": "1234567890",
      "account_type": "checking",
      "usage_type": "payroll",
      "is_default": true
    }
  ]
}
```

### Configure Split Deposit

Set up multiple bank accounts with different allocations:

```json
{
  "global_employee_id": "EMP-000001",
  "employee_bank_accounts": [
    {
      "_action": "add",
      "legal_entity_id": 13,
      "account_nickname": "Savings - $500",
      "bank_name": "Chase",
      "routing_number": "021000021",
      "account_number": "1111111111",
      "account_type": "savings",
      "usage_type": "payroll",
      "deposit_allocation_type": "amount",
      "deposit_amount": 500.00,
      "deposit_order": 1
    },
    {
      "_action": "add",
      "legal_entity_id": 13,
      "account_nickname": "Checking - Remainder",
      "bank_name": "Chase",
      "routing_number": "021000021",
      "account_number": "2222222222",
      "account_type": "checking",
      "usage_type": "payroll",
      "deposit_allocation_type": "remainder",
      "deposit_order": 2,
      "is_default": true
    }
  ]
}
```

### Employee Resignation

Terminate with future date:

```json
{
  "global_employee_id": "EMP-000001",
  "termination_date": "2025-12-31",
  "termination_reason": "Resigned"
}
```

---

## Getting Reference Data

Before constructing payloads, use search tools to get valid reference data:

| Data Type | How to Get | Example Values |
|-----------|-----------|----------------|
| Legal entities | `query("legal_entity")` | Entity IDs for assignments |
| Dimension types | `query("dimension_type")` | `department`, `location`, `cost_center` |
| Dimension values | `query("dimension_value", filters={"dimension_type_id": X})` | `SALES`, `ENGINEERING`, `MARKETING` |
| Vendors | `query("vendor", query)` | For contractor vendor mappings |
| Employees | `query("employee", query)` | For manager assignments |

**Tip:** Always query reference data dynamically rather than hardcoding values, as they may vary by organization and legal entity.

---

## Workflow Details

For complete field specifications, validation rules, and constraints:

- employee.create (fields: `get_submissions(action="schema", object_type, operation)`) - All required and optional fields
- employee.update (fields: `get_submissions(action="schema", object_type, operation)`) - Update operations and action patterns
- employee.delete (fields: `get_submissions(action="schema", object_type, operation)`) - Termination and hard delete options

---

## Key Concepts

### Approval Workflow

All employee changes go through the workflow system:
1. Submit workflow request
2. System validates payload
3. Routes to HR Manager then Controller for approval
4. Executes after approval

### MSEO Pattern

Employees use the Master + Entity Assignment pattern:
- Master employee record contains personal info (name, email, hire date)
- Entity assignments contain job-specific info (title, department, manager)
- Employees can work across multiple entities

### Manager Hierarchy

- Manager assignments are entity-specific
- Changing managers automatically rebuilds the hierarchy
- Use `manager_global_employee_id` to specify reporting relationships
- System calculates `manager_path` and `manager_level` automatically

### Bank Account Security

- Account numbers and routing numbers are encrypted at rest
- Bank details are entity-specific
- Only authorized users can view/modify bank information
- Prenote verification process for ACH accounts

### Employment Types

- `full_time` - Standard full-time employee
- `part_time` - Part-time employee
- `contractor` - Independent contractor (use vendor mapping for 1099)
- `intern` - Temporary intern

### Related Entity Aliases

When updating related data, these field names are supported:
- `employee_bank_accounts` - Bank account records
- `employee_addresses` - Address records
- `employee_dimensions` - Dimension assignments
- `vendor_mappings` - Contractor-to-vendor linkages

---

## Tips & Best Practices

### 1. Metadata Usage
- Always check existing employees' metadata structure before adding new fields
- Use consistent field names across all employees
- Namespace integration data to avoid conflicts
- Document your metadata schema

### 2. Address Management
- Use `is_primary=true` for default address
- Use `is_mailing=true` for mail delivery address
- Can have multiple addresses of different types (home, work, emergency)
- Keep addresses up to date for payroll tax purposes

### 3. Bank Account Management
- Verify bank account details before first payroll
- Use account nickname for easy identification
- Set up prenote ACH verification for new accounts
- Mark primary account as `is_default=true`
- Use split deposits for automatic savings allocation

### 4. Manager Hierarchy
- Manager assignments are entity-specific (same employee can have different managers in different entities)
- System automatically rebuilds `manager_path` and `manager_level` when managers change
- Cannot create circular manager relationships (validation prevents this)
- Use `manager_global_employee_id` not `manager_employee_id` when creating/updating

### 5. Employment Status
- Use soft delete (termination) for all employees with payroll history
- Hard delete only for test data, duplicates, or data entry errors
- Set `termination_date` for future resignations (allows planning)
- Document `termination_reason` for compliance and reporting

### 6. Dimensions
- Tag all employees with relevant dimensions at creation
- Dimensions auto-flow to payroll, expenses, and time tracking
- Update dimensions when employee changes cost center or project
- Use for financial reporting and cost allocation

### 7. Query Performance
- Use `get_entity` for single employee lookup (optimized effective view)
- Use `query` with filters for finding employees
- Filter by `status="active"` to exclude terminated employees
- Employee number and global_employee_id searches are faster than name searches

### 8. Data Quality
- Validate email addresses before creating employees
- Standardize phone number format across all employees
- Keep emergency contact info updated
- Regular cleanup of duplicate or test employees
- Verify work_email is unique organization-wide

### 9. Contractor Management
- Map contractors to vendor records using `vendor_mappings`
- Set `employment_type="contractor"` for proper classification
- Ensure 1099 tracking through vendor payment system
- Link to existing vendor or create new vendor first

### 10. Multi-Entity Employees
- Employees can work across multiple legal entities
- Each entity assignment has its own job title, manager, and effective dates
- Transfer employees by updating `legal_entity_id` (doesn't remove old assignment)
- Track assignment periods with `effective_from` and `effective_to` dates

### 11. Payroll Setup
- After creating an employee, create `employee_compensation` and `employee_tax_settings` before running payroll
- `employee_tax_settings.country_code` is CRITICAL — determines which tax formula the calculator uses
- Without tax settings, employees default to US formulas (wrong for non-US employees)
- For Estonian employees: set `pension_tier` (NULL = not enrolled, '2%', '4%', '6%') and `basic_exemption_applied`
- See [Payroll Management](./payroll-management.md) for full payroll documentation

---

## Query Field Reference

### Display Fields (returned by `query` / `query`)

| Field | Type | Description |
|-------|------|-------------|
| `employee_number` | string | Entity-specific employee number |
| `first_name` | string | Employee first name |
| `last_name` | string | Employee last name |
| `work_email` | string | Company email address |
| `job_title` | string | Position title |
| `department` | string | Department name |
| `employment_type` | string | full_time, part_time, contractor, intern |
| `hire_date` | date | First day of employment |
| `location` | string | Work location |
| `cost_center` | string | Cost center code |
| `status` | string | active, terminated, on_leave |

### Searchable Fields (text search via `query("employee", query=...)`)

| Field | Description |
|-------|-------------|
| `first_name` | First name (partial match) |
| `last_name` | Last name (partial match) |
| `work_email` | Company email address |
| `personal_email` | Personal email address |
| `job_title` | Position title |
| `department` | Department name |
| `notes` | Internal HR notes |
| `global_employee_id` | Organization-wide employee ID |
| `employee_number` | Entity-specific employee number |

### Filter Fields (via `filters` parameter)

| Field | Type | Example |
|-------|------|---------|
| `legal_entity_id` | integer | `13` |
| `status` | string | `"active"` |
| `department` | string | `"Engineering"` |
| `location` | string | `"San Francisco"` |
| `employment_type` | string | `"full_time"` |
| `manager_employee_id` | integer | `45` |

### Sort Fields (via `sort_by` parameter)

| Field | Default | Description |
|-------|---------|-------------|
| `last_name` | Yes | Alphabetical by last name |
| `first_name` | | Alphabetical by first name |
| `employee_number` | | By employee number |
| `hire_date` | | By hire date |

### Related Data (returned by `get_entity` with `include_related=True`)

| Related Entity | Description |
|----------------|-------------|
| `addresses` | Home, mailing, work addresses |
| `bank_accounts` | Payroll direct deposit accounts (masked) |
| `dimensions` | Department, location, cost center tags |
| `vendor_mappings` | Contractor-to-vendor linkages |
| `direct_reports` | Employees reporting to this manager |

---

## Tax-filing metadata convention (`master_employees.metadata.tax_filing.*`)

Universal JSONB shape that country tax-filing plugins read at filing time. No per-country branching in core code — every country uses the same key names; plugins translate to country-specific external codes.

```jsonc
{
  "country": "EE",                  // ISO 3166-1 alpha-2
  "residency": "resident",          // resident | non_resident — drives Annex routing
  "country_of_residence": "EE",     // For non-residents, drives treaty-rate lookup
  "is_pensioner": false,            // Pensioners exempt from employee-side unemployment
  "basic_exemption_code": "610",    // EE: c1150 sub-record code (610 = standard basic exemption)
  "pension_fund_id": 47,            // FK to master_vendors (the pension fund)
  "tax_treaty_country": null,       // For non-residents
  "treaty_rate_override": null      // Per-employee rate override (rare)
}
```

**Set it via update:**

```python
submit("employee", "update", {
    "employee_id": <id>,
    "metadata": { "tax_filing": { "country": "EE", "residency": "resident", "basic_exemption_code": "610" } }
})
```

Visible on the employee detail page → Payroll tab → "Tax filing settings" card.

For the architectural pattern, see GUIDE_TAX_FILING_PLUGINS.md.

## End of Guide

This guide covers complete employee management including all database fields, workflows, query tools, metadata usage, and operational best practices for Claude.ai automation.


### Employee read authority (Admin and MCP)

Dashboard membership read access alone does not grant employee access. Employee
list, search, detail, and history reads require at least one of `hr:read`,
`payroll:read`, `master_data:read`, `ap:read`, or `expenses:read`, with existing
owner/wildcard rules. Entity scope remains independently enforced. This aligns
Admin's employee router with the MCP employee registry; it does not introduce a
new field-level HR privacy policy for otherwise authorized employee readers.
Payroll compensation, tax settings, and deductions still require `payroll:read`.
The employee Payroll tab distinguishes access restrictions and load failures from
successfully loaded empty data and does not render cached payroll data on error.


Employee payroll mutations (`employee_compensation`, `employee_tax_settings`, and
`employee_deduction`) require `payroll:write`, independently of workflow configuration.
Employee create/update commands containing compensation or tax-setting collections
also require `payroll:write`; ordinary employee/address writes retain their existing
policy. The permission floor runs before validation, direct execution and idempotent
replay, and at workflow start. Master-data write permission alone is insufficient.


### Employee numbering across imports and creation (E2E-041)

Employee creation and imports without a supplied `global_employee_id` use the
same tenant `master_employee_seq` through the shared employee allocator. IDs
are organization-wide, formatted `EMP-` plus at least six digits; separate legal
entities do not restart this master ID sequence. Allocation skips IDs already
occupied by earlier or explicit imports, without resetting the counter or
renumbering existing records. Concurrent generated allocations use PostgreSQL
`nextval`; rolled-back or failed operations may leave normal gaps.

Explicit IDs in imports are preserved and still subject to duplicate detection
and database uniqueness checks. They do not change the configured sequence.
Do not manually reset the counter to recover a collision; retry the failed
creation after deploying the shared allocator. Custom source IDs need not have
a numeric EMP suffix. Numbers beyond six digits are preserved, not truncated.
