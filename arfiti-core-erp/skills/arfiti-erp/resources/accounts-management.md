# Chart of Accounts Management

> **MSEO release contract:** Use master account identity with legal-entity context. Do not infer identity from effective-view fallback expressions. See the dimensions-management resource for assignment, approval and compatibility rules.

**Purpose:** Manage the organization's chart of accounts (GL accounts) used for financial transaction categorization and reporting

**Pattern:** MSEO (Master + Scopes + Entity Overrides + Effective Views)

---

## Overview

Accounts are the foundation of double-entry accounting. Each account in the Chart of Accounts (COA) represents a category of financial transactions (assets, liabilities, equity, revenue, expenses).

**What you can do:**
- Create master accounts visible to all entities
- Create entity-specific accounts for custom needs
- Update account properties or create entity overrides
- Query accounts using effective views
- Deactivate accounts (soft delete) or remove test accounts (hard delete)

**Available Workflows:**

| Workflow | Purpose | When to Use |
|----------|---------|-------------|
| `account.create` | Create new account | Adding new GL account to COA |
| `account.update` | Update account or create override | Changing account properties, entity customization |
| `account.delete` | Deactivate account | Account no longer needed |

**Query Tools:**

| Tool | Purpose | Example |
|------|---------|---------|
| `get_entity("account", id=123)` | Get single account | Get account by ID |
| `query("account", filters)` | Search accounts | Find all asset accounts |

---

## Database Schema

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

### Master Accounts Table (master_accounts)

Organization-wide account definitions visible to all entities by default.

**Required Fields:**
- `account_number` (string, max 50, unique per org) - Unique account identifier (e.g., "1000", "4100")
- `account_name` (string, max 255) - Account display name (e.g., "Cash", "Sales Revenue")
- `account_type` (enum, closed set of 6) - `asset`, `liability`, `equity`, `revenue`, `cogs`, `expense`. Note: `cogs` is its own top-level type (NOT a subtype of `expense`).
- `account_subtype` (enum, 89 canonical values) - **REQUIRED**. See "Canonical Subtype Taxonomy" below. The submit gateway rejects unknown values with an actionable error pointing at the canonical list.
- `normal_balance` (enum) - Normal balance: `debit` or `credit`
- `description` (text) - Purpose and usage description

### Canonical Subtype Taxonomy (Batch C, 2026-05-05)

Every `account_subtype` value must be one of 89 canonical codes seeded in `system.account_subtypes`. The submit gateway validates this at write time, the database FK enforces it, and the CI guardrail in `tests/test_c5_no_coa_coupling.py` blocks any code that classifies accounts by `account_number` prefix or `account_name` ILIKE.

**Most-used subtypes by parent type (full list: 89 entries — see Python constants module or GUIDE_COA.md):**

| account_type | Common subtypes |
|---|---|
| `asset` | `cash`, `bank`, `cash_equivalent`, `bank_clearing`, `accounts_receivable`, `allowance_doubtful_debts`, `prepaid_expense`, `inventory_finished_goods`, `vat_recoverable`, `employee_advance`, `other_current_asset`, `fixed_asset_cost`, `accumulated_depreciation`, `right_of_use_asset`, `intangible_asset`, `goodwill`, `accumulated_amortisation`, `investment_long_term`, `loan_receivable`, `security_deposit`, `other_non_current_asset` |
| `liability` | `accounts_payable`, `capex_payable` (investing), `accrued_expense`, `accrued_payroll`, `payroll_withholding`, `vat_payable`, `sales_tax_payable`, `tax_payable_income`, `customer_deposit`, `contract_liability`, `short_term_debt`, `lease_liability_current`, `dividend_payable`, `other_current_liability`, `long_term_debt`, `lease_liability_non_current`, `deferred_tax_liability`, `provision_legal`, `other_non_current_liability` |
| `equity` | `share_capital_ordinary`, `share_capital_preferred`, `share_premium`, `owner_contributions`, `treasury_shares`, `retained_earnings`, `revaluation_reserve`, `oci_other`, `non_controlling_interest`, `dividends_distributions` (financing; use it for any dividends or owner-distribution account) |
| `revenue` | `operating_revenue` (umbrella for primary business revenue — slice via dimensions, not subtypes), `other_revenue_interest`, `other_revenue_dividend`, `other_revenue_gain`, `fx_gain` (foreign exchange gains; its cash reads "Exchange differences on settlement"), `asset_disposal_gain_loss` (investing; use it for the disposal gain/loss account), `revenue_contra` |
| `cogs` | `cogs_materials`, `cogs_labour`, `cogs_overhead` |
| `expense` | `operating_expense`, `salaries_expense`, `employee_benefits_expense`, `depreciation_expense`, `amortisation_expense`, `interest_expense`, `bank_charges`, `bad_debt_expense`, `fx_loss`, `impairment_loss`, `tax_expense_current`, `tax_expense_deferred`, `other_expense`, `asset_disposal_loss` (investing; use it for an expense-type disposal loss account) |

**Cash-flow classification** — every subtype carries a `cash_flow_class` value (`cash_account` / `operating` / `investing` / `financing` / `income_statement` / `excluded`) on `system.account_subtypes`. The cash flow statement query JOINs that table — no inline subtype lists in CASE expressions.

**Reusable Python subset constants** in `mcp-server/src/constants/account_subtypes.py`:
- `CASH_SUBTYPES` = `{cash, bank, cash_equivalent}` — what counts as cash for cash-position reporting
- `ASSET_COST_SUBTYPES` = `{fixed_asset_cost, intangible_asset, right_of_use_asset, goodwill}`
- `CONTRA_ASSET_SUBTYPES` = `{allowance_doubtful_debts, accumulated_depreciation, accumulated_depreciation_rou, accumulated_amortisation, inventory_obsolescence_reserve}`

**Hierarchy and Organization:**
- `parent_account_number` (string, max 50) - Parent account for hierarchical structure
- `is_header` (boolean, default: false) - Header account (no posting allowed, subtotals only)

**Visibility and Control (unified MSEO contract):**
`account.create` is `SCOPE_MODE='fanout'`. The combination of `is_global`, `legal_entity_id`, and `legal_entity_ids` resolves to a list of target entities — the executor writes a master row plus one `accounts` row per target entity.

- `is_global` (boolean, default: `true`) — when `true`, fans out to EVERY active legal_entity (one `accounts` row each, dimensions written per entity). When `false`, entity targets come from the IDs.
- `legal_entity_id` (integer, optional) — single-entity attach. Implies `is_global=false`. Result: master + ONE `accounts` row + `account_dimensions` attached to that row.
- `legal_entity_ids` (integer[], optional) — multi-entity attach.
- **No flag, no IDs** → defaults to `is_global=true` → fanout (legacy behaviour).
- **`is_global=false` + no IDs** → master only (template); `account_dimensions` will be REJECTED loudly. (Pre-Batch C, dimensions were silently dropped here — see GUIDE_MSEO_PATTERN.md Bug 5d.)

`account_dimensions` are entity-scoped — they need an `accounts.id` to attach to. With `is_global=true`, dimensions land on every per-entity row; with `legal_entity_id=X`, they land only on entity X.

- `is_active` (boolean, default: true) - Active status (false = deactivated)
- `allow_manual_entries` (boolean, default: true) - Allow manual journal entries

**Special Properties:**
- `is_reconcilable` (boolean, default: false) - Enable bank reconciliation (for cash/bank accounts)
- `currency_code` (string, 3 chars) - Foreign currency code (e.g., "EUR", "GBP")
- `global_account_id` (string, max 50, unique) - Global identifier across organizations

**Administrative:**
- `metadata` (jsonb) - Custom JSONB data for flexible attributes
- `created_at` (timestamp) - Creation timestamp
- `updated_at` (timestamp) - Last update timestamp
- `created_by` (integer) - User ID who created
- `updated_by` (integer) - User ID who last updated
- `organization_id` (integer) - Organization owner

**Total Fields**: 21

### Entity Override Table (accounts)

Entity-specific account overrides (sparse - only when customization needed).

**Core Fields:**
- `master_account_id` (integer) - Reference to master account
- `legal_entity_id` (integer) - Entity ID for this override

**Override Fields** (NULL = use master value):
- `account_number_override` (string, max 50) - Override account number for this entity
- `account_name_override` (string, max 255) - Override account name for this entity
- `description_override` (text) - Override description for this entity
- `is_active_override` (boolean) - Override active status for this entity
- `allow_manual_entries_override` (boolean) - Override manual entry permission for this entity

**Administrative:**
- `created_at` (timestamp) - Override creation timestamp
- `updated_at` (timestamp) - Last update timestamp
- `created_by` (integer) - User ID who created override
- `updated_by` (integer) - User ID who last updated override

**Total Fields**: 12

### Account Dimensions Table (account_dimensions)

Default dimension assignments for accounts (applied to transactions using this account).

**Fields:**
- `account_id` (bigint) - Account ID (from accounts or master_accounts)
- `legal_entity_id` (integer) - Entity ID
- `dimension_type_id` (integer) - Dimension type (e.g., Department, Cost Center)
- `dimension_value_id` (bigint) - Dimension value (e.g., "Engineering", "ADMIN-001")
- `created_at` (timestamp) - Creation timestamp
- `created_by` (integer) - User ID who created

**Total Fields**: 6

**How to manage account dimensions:**
- Via `account.create` workflow: pass `account_dimensions` array in the payload
- Via `account.update` workflow: pass `account_dimensions` array with `_action: "add"` (default), `"update"` or `"delete"` — `delete` needs only the type
- Via `account_dimension.assign` workflow: standalone dimension assignment to an existing account

See [Dimensions Management](./dimensions-management.md) for full details on dimension types and values.

---

## Workflows

### 1. Create Account (`account.create`)

**Purpose**: Create new master account (organization-wide) or entity-specific account

**Approval**: Green lane by default for standard accounts (Yellow by default for an entity-specific or header account); completes without an approval step unless the organisation has configured one. The `status` and `lane` in the submit() result are authoritative.

**Payload Structure**:

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="account", operation="create")

// Step 2: Submit with discovered fields
submit("account", "create", '{...}')
// Tip: Use validate_only=true to check payload before submitting
```

```javascript
submit("account", "create", {
    // Required fields
    "account_number": "1050",
    "account_name": "Petty Cash",
    "account_type": "asset",
    "normal_balance": "debit",
    "account_subtype": "cash",
    "description": "Cash fund for small office expenses under $50",

    // Optional - Hierarchy
    "parent_account_number": "1000",  // Parent: Cash

    // Optional - Visibility and control
    "is_global": true,  // Default: true (visible to all entities)
    "is_active": true,  // Default: true
    "allow_manual_entries": true,  // Default: true
    "is_header": false,  // Default: false

    // Optional - Special properties
    "is_reconcilable": true,  // For bank/cash accounts
    "currency_code": "EUR",  // For foreign currency accounts

    // Optional - Custom data
    "metadata": {"location": "front_desk", "limit": 500}
})
```

**Required Fields**:
- `account_number` (string, max 50)
- `account_name` (string, max 255)
- `account_type` (enum: asset, liability, equity, revenue, expense)
- `normal_balance` (enum: debit, credit)
- `account_subtype` (required canonical subtype, max 50)
- `description` (text)

**Optional Fields**:
- `parent_account_number` (string, max 50)
- `is_global` (boolean, default: true)
- `is_active` (boolean, default: true)
- `allow_manual_entries` (boolean, default: true)
- `is_header` (boolean, default: false)
- `is_reconcilable` (boolean, default: false)
- `currency_code` (string, 3 chars)
- `metadata` (jsonb)

**Response**:

```json
{
  "success": true,
  "account_id": 123,
  "account_number": "1050",
  "workflow_id": "wf-uuid-here",
  "lane": "green",
  "status": "completed"
}
```

### 2. Update Account (`account.update`)

**Purpose**: Update master account properties OR create entity-specific override

**Approval**: Green lane by default for most updates (Yellow by default when deactivating or changing account dimensions); completes without an approval step unless the organisation has configured one.

**Payload Structure**:

```javascript
submit("account", "update", {
    // Identifier (ONE of these required)
    "account_number": "1050",  // OR
    "account_id": 123,

    // Optional - Entity override
    "legal_entity_id": 13,  // If provided, creates entity override instead of updating master

    // Fields to update (master account)
    "account_name": "Petty Cash - Updated",
    "description": "Updated description",
    "is_active": true,
    "allow_manual_entries": false,

    // OR Fields for entity override (when legal_entity_id provided)
    "account_name_override": "Petty Cash EUR",
    "description_override": "Euro petty cash for Paris office",
    "is_active_override": true,
    "allow_manual_entries_override": false
})
```

**Identifier** (ONE required):
- `account_number` (string) - Account number to update
- `account_id` (integer) - Account ID to update

**Updatable Master Fields**:
- `account_name` (string, max 255)
- `description` (text)
- `account_subtype` (canonical subtype) - reclassifies the account **within its `account_type`** (e.g. an imported card account `other_current_asset` → `bank`; a migrated trade-creditor account `other_current_liability` → `accounts_payable`). A subtype of another type is refused. Reports read all posted history under the new subtype (cash scope, receivable/payable control), so confirm the account's real role first. The response's `account_subtype_change` shows `{from, to}`.
- `is_active` (boolean)
- `allow_manual_entries` (boolean)
- `is_reconcilable` (boolean)
- `currency_code` (string, 3 chars)
- `metadata` (jsonb)

**Entity Override Fields** (when `legal_entity_id` provided):
- `account_number_override` (string, max 50)
- `account_name_override` (string, max 255)
- `description_override` (text)
- `is_active_override` (boolean)
- `allow_manual_entries_override` (boolean)

**Non-Updatable Fields**:
- `account_type` (cannot change after creation)
- `normal_balance` (cannot change after creation)
- `parent_account_number`, `is_header` (not part of `account.update`)
- `is_global` (cannot change after creation)

**Response**:

```json
{
  "success": true,
  "account_id": 123,
  "account_number": "1050",
  "override_created": false,
  "workflow_id": "wf-uuid-here",
  "lane": "green",
  "status": "completed"
}
```

### 3. Delete Account (`account.delete`)

**Purpose**: Soft delete (deactivate) or hard delete (remove) accounts

**Approval**: Red lane by default for hard delete; soft delete's lane is set by the organisation's workflow configuration. Approval steps are configured per organisation; report the `status` and `lane` from the submit() result.

**Payload Structure**:

```javascript
submit("account", "delete", {
    // Identifier (ONE required)
    "account_number": "1050",  // OR
    "account_id": 123,

    // Optional
    "deletion_reason": "Account no longer needed",
    "hard_delete": false  // Default: false (soft delete)
})
```

**Soft Delete** (default):
- After migrations 665–668, refused for used accounts until a reviewed transition is available
- Sets `is_active = false`
- Account still visible in history/reports
- Can be reactivated
- Preserves transaction history

**Hard Delete** (`hard_delete: true`):
- Permanently removes account record
- Red lane by default (approval steps as the organisation has configured them)
- Only allowed if NO transactions exist
- Cannot be undone

**Response**:

```json
{
  "success": true,
  "account_id": 123,
  "account_number": "1050",
  "deletion_type": "soft",
  "workflow_id": "wf-uuid-here",
  "lane": "yellow",
  "status": "completed"
}
```

---

## Query Tools

| Tool | Purpose |
|------|---------|
| `get_entity("account", id=X)` | Get single account (all fields, override resolved) |
| `query("account", filters)` | List accounts with filters and pagination |
| `query("account", query, filters)` | Search accounts by text |
| `query("account", filters, limit=1)` | Count matching accounts (use `total_count` from response) |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

**Key notes:**
- Search/list results now include `parent_account_number` alongside the standard fields
- `get_entity` defaults to `include_related=True` — includes account dimensions automatically

### Get Single Account

```javascript
get_entity("account", id=123)
```

**Returns**: Single account with all fields (master + override resolved)

### Search/List Accounts

```javascript
// Get all asset accounts
query("account", filters={"account_type": "asset", "is_active": true})

// Get header (parent) accounts
query("account", filters={"is_header": true, "legal_entity_id": 13})

// Get cash and bank accounts (classify by subtype, never by number;
// a list value means "any of")
query("account", filters={"account_subtype": ["cash", "bank", "cash_equivalent"], "legal_entity_id": 13})

// Search by text
query("account", query="revenue", filters={"is_active": true})
```

**Filters** (the complete list; any other key is refused; pinned to the entity registry by a test):
- `legal_entity_id`
- `account_type` (asset, liability, equity, revenue, expense)
- `account_subtype` (one of 89 canonical values: `cash`, `bank`, `accounts_receivable`, `fixed_asset_cost`, `operating_revenue`, `operating_expense`, etc. — see "Canonical Subtype Taxonomy" section)
- `is_active` (true/false)
- `is_header` (true/false)
- `allow_manual_entries` (true/false)

**Returns**: Array of accounts matching filters

---

## Account Types and Normal Balance

### The Six Account Types

| Type | Normal Balance | Increase | Decrease | Examples |
|------|----------------|----------|----------|----------|
| **Asset** | Debit | Debit | Credit | Cash, AR, Inventory, Equipment |
| **Liability** | Credit | Credit | Debit | AP, Loans, Accrued Expenses |
| **Equity** | Credit | Credit | Debit | Share Capital, Retained Earnings |
| **Revenue** | Credit | Credit | Debit | Sales, Service Income, Interest Income |
| **COGS** | Debit | Debit | Credit | Cost of Goods Sold, Direct Labour, Freight In |
| **Expense** | Debit | Debit | Credit | Salaries, Rent, Utilities |

Contra accounts carry the opposite side of their type: accumulated depreciation and the doubtful-debt allowance
are credit-normal assets, dividends/distributions and treasury shares debit-normal equity, sales returns and
discounts debit-normal revenue.

### Account Subtypes by Type (examples)

`account_subtype` is always a canonical subtype that belongs to the account's type (the full list is in
GUIDE_COA.md §3); a missing one becomes the type's default (marked *default* below).

**Asset**:
- `cash`, `bank`, `bank_clearing` - Cash on hand, bank and card accounts, clearing
- `accounts_receivable`, `prepaid_expense`, `inventory_finished_goods` - Current assets
- `fixed_asset_cost`, `accumulated_depreciation` - Property, plant and equipment and its contra
- `intangible_asset`, `investment_long_term` - Non-current assets
- `other_current_asset` (*default*), `other_non_current_asset`

**Liability**:
- `accounts_payable`, `accrued_expense`, `vat_payable`, `short_term_debt` - Current liabilities
- `long_term_debt`, `lease_liability_non_current` - Non-current liabilities
- `other_current_liability` (*default*), `other_non_current_liability`

**Equity**:
- `share_capital_ordinary`, `share_premium` - Share capital, additional paid-in capital
- `retained_earnings` (*default*) - Accumulated earnings
- `dividends_distributions` - Dividends, owner's draw (debit-normal)

**Revenue**:
- `operating_revenue` (*default*) - Sales and service revenue
- `other_revenue_interest`, `fx_gain`, `asset_disposal_gain_loss` - Other income
- `revenue_contra` - Sales returns and discounts (debit-normal)

**COGS**:
- `cogs_materials` (*default*), `cogs_labour`, `cogs_overhead` - Cost of goods sold, direct labour, overhead

**Expense**:
- `operating_expense` (*default*), `salaries_expense`, `depreciation_expense` - Operating expenses
- `interest_expense`, `fx_loss`, `asset_disposal_loss`, `other_expense` - Other expenses

---

## Account Numbering Conventions

### Example Number Ranges

One common convention, shown as an example only. Follow the organisation's own chart of accounts;
reports and agents classify accounts by `account_type` / `account_subtype`, never by number.

| Range | Type | Examples |
|-------|------|----------|
| 1000-1999 | Assets | Cash, AR, Inventory, Fixed Assets |
| 2000-2999 | Liabilities | AP, Loans, Accrued Expenses |
| 3000-3999 | Equity | Common Stock, Retained Earnings |
| 4000-4999 | Revenue | Sales, Service Income |
| 5000-5999 | Cost of Sales | COGS, Direct Labor |
| 6000-6999 | Operating Expenses | Salaries, Rent, Utilities |
| 7000-7999 | Other Income | Interest Income, Gains |
| 8000-8999 | Other Expenses | Interest Expense, Losses |

### Hierarchical Numbering Example

```
1000        Cash (Parent)
1000-01       Cash - USD
1000-02       Cash - EUR
1000-03       Cash - GBP

4000        Sales Revenue (Parent)
4100          Product Sales
4200          Service Revenue
4300          Subscription Revenue

6000        Operating Expenses (Parent)
6100          Salaries and Wages
6200          Rent and Occupancy
6300          Utilities
```

---

## MSEO Pattern (Master + Entity Overrides)

### How It Works

**Master Account** (organization-wide):
- Created once in `master_accounts` table
- `is_global = true` → Visible to ALL entities
- `is_global = false` → Only visible to specific entities

**Entity Override** (sparse customization):
- Created in `accounts` table when entity needs custom values
- Only stores fields that differ from master
- NULL = use master value
- Non-NULL = use override value

**Effective View** (what each entity sees):
- Automatically resolved via `v_accounts_effective` view
- Shows master + override merged
- Query this view for entity-specific account data

### Example: Master Account Visible to All

```javascript
// Create master account (visible to all entities)
submit("account", "create", {
    "account_number": "1000",
    "account_name": "Cash",
    "account_type": "asset",
    "normal_balance": "debit",
    "account_subtype": "cash",
    "description": "Cash on hand and in bank",
    "is_global": true  // All entities see this
})

// Result: All entities (9, 13, 10, etc.) see "1000 - Cash" with same properties
```

### Example: Entity-Specific Name Override

```javascript
// Entity 13 wants different name for account 1000
submit("account", "update", {
    "account_number": "1000",
    "legal_entity_id": 13,
    "account_name_override": "Cash - EUR Operations"
})

// Result:
// - Entity 9, 10: See "1000 - Cash" (master)
// - Entity 13: See "1000 - Cash - EUR Operations" (override)
```

### Example: Entity-Specific Account

```javascript
// Create account visible ONLY to entity 10
submit("account", "create", {
    "account_number": "1055",
    "account_name": "Petty Cash - London Office",
    "account_type": "asset",
    "normal_balance": "debit",
    "account_subtype": "cash",
    "description": "GBP petty cash for London office",
    "is_global": false,  // NOT visible to all
    "legal_entity_id": 10  // Only entity 10
})

// Result:
// - Entity 10: Sees "1055 - Petty Cash - London Office"
// - Entity 9, 13: Do NOT see account 1055
```

---

## Metadata Best Practices

The `metadata` field allows flexible JSONB storage for custom attributes.

### Common Use Cases

**Cost Center Tracking**:
```json
{
  "metadata": {
    "default_cost_center": "ADMIN-001",
    "requires_cost_center": true
  }
}
```

**Department Assignment**:
```json
{
  "metadata": {
    "default_department": "Engineering",
    "department_required": true
  }
}
```

**Approval Thresholds**:
```json
{
  "metadata": {
    "approval_threshold": 5000,
    "approval_required": true,
    "approver_role": "Controller"
  }
}
```

**Budget Tracking**:
```json
{
  "metadata": {
    "budget_tracked": true,
    "budget_category": "Operations",
    "monthly_budget": 10000
  }
}
```

**Physical Location**:
```json
{
  "metadata": {
    "location": "front_desk",
    "physical_limit": 500,
    "custodian": "Office Manager"
  }
}
```

**Tax Classification**:
```json
{
  "metadata": {
    "tax_deductible": true,
    "tax_category": "Office Expense",
    "1099_reportable": false
  }
}
```

### Querying Metadata

Metadata fields cannot be filtered directly via `query()` or `query()` filters. Instead, retrieve accounts by other criteria and inspect metadata in the response:

```javascript
// Get expense accounts, then inspect metadata in results
query("account", filters={"account_type": "expense", "is_active": true})
// Then check metadata.budget_tracked in each returned account
```

---

## Bulk Import

For importing multiple accounts at once:
- Chart of Accounts template imports (US GAAP, IFRS)
- Data migration from legacy systems
- CSV file uploads
- Validate before import (dry-run mode)
- Handle duplicates automatically (skip, update, or error)

### Import Workflow

Use the `account.import` workflow:

```javascript
submit("account", "import", {
    "object_type": "account",
    "records": [
      {
        "account_number": "1000",
        "account_name": "Cash - Operating",
        "account_type": "asset",
        "normal_balance": "debit",
        "account_subtype": "bank",
        "description": "Primary operating cash account",
        "is_reconcilable": true,
        "is_global": true
      },
      {
        "account_number": "4000",
        "account_name": "Sales Revenue",
        "account_type": "revenue",
        "normal_balance": "credit",
        "account_subtype": "operating_revenue",
        "description": "Revenue from product and service sales",
        "is_global": true
      },
      {
        "account_number": "6100",
        "account_name": "Salaries and Wages",
        "account_type": "expense",
        "normal_balance": "debit",
        "account_subtype": "operating_expense",
        "description": "Employee compensation",
        "parent_account_number": "6000"
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

Accounts are considered duplicates if:
- **account_number** matches (unique per organization)

### Required Fields for Import

- `account_number` (1-50 chars, unique per organization)
- `account_name` (1-255 chars)
- `account_type` (asset, liability, equity, revenue, expense)
- `normal_balance` (debit or credit)

### Optional Fields for Import

- `account_subtype` (one of 89 canonical values: `cash`, `bank`, `accounts_receivable`, `fixed_asset_cost`, `operating_revenue`, `operating_expense`, etc. — see "Canonical Subtype Taxonomy" section)
- `description` (text, recommended for all accounts)
- `parent_account_number` (for hierarchical structure)
- `is_global` (boolean, default: true - visible to all entities)
- `is_active` (boolean, default: true)
- `allow_manual_entries` (boolean, default: true)
- `is_header` (boolean, default: false - subtotal-only account)
- `is_reconcilable` (boolean, default: false - for cash/bank accounts)
- `currency_code` (3-letter ISO code for foreign currency accounts)
- `global_account_id` (string, cross-org identifier)
- `metadata` (JSONB)

### Validation Behavior

The importer performs comprehensive validation:
- **Field validation**: Data types, lengths, formats, required fields, enum values
- **Foreign key validation**: Verifies parent_account_number exists (if provided)
- **Business rule validation**: Account number uniqueness, normal balance conventions, header account rules
- **Duplicate detection**: Checks account_number (unique per organization)
- **Warnings**: Missing description, missing subtype, normal balance mismatch with account type convention

### Import Response

```json
{
  "success": true,
  "import_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_records": 102,
  "imported": 102,
  "updated": 0,
  "skipped": 0,
  "errors": 0,
  "warnings": [
    {
      "row": 15,
      "field": "description",
      "message": "Missing account description",
      "record_identifier": "1500"
    },
    {
      "row": 23,
      "field": "normal_balance",
      "message": "WARNING: revenue accounts typically have credit normal balance, got debit",
      "record_identifier": "4100"
    }
  ],
  "created_ids": [201, 202, 203, ...],
  "updated_ids": [],
  "duration_ms": 2150
}
```

### Validate Before Importing (Dry Run)

Test your import without making changes:

```javascript
submit("account", "import", {
    "object_type": "account",
    "records": [...],
    "options": {
      "validate_only": true
    }
})
```

This returns validation errors without creating any accounts.

### Common Import Scenarios

**US GAAP Chart of Accounts Template:**
```javascript
{
  "object_type": "account",
  "source_type": "template",
  "source_id": "us_gaap_standard",
  "records": accounts_from_us_gaap_template,
  "options": {
    "on_duplicate": "skip",    // Don't overwrite existing
    "stop_on_error": false     // Continue even if some fail
  }
}
```

**Data Migration from Legacy System:**
```javascript
{
  "object_type": "account",
  "source_type": "migration",
  "source_id": "legacy-erp-migration",
  "records": accounts_from_legacy_system,
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
  "object_type": "account",
  "source_type": "csv",
  "source_id": "coa-import-2025-01-14.csv",
  "records": accounts_from_csv,
  "options": {
    "on_duplicate": "error",   // Flag duplicates
    "stop_on_error": true      // Stop if duplicate found
  }
}
```

**Update Existing Accounts:**
```javascript
{
  "object_type": "account",
  "records": accounts_with_updates,
  "options": {
    "on_duplicate": "update",  // Update existing accounts
    "stop_on_error": false     // Continue even if some fail
  }
}
```

**See:** PLAN_IMPORT.md for import system architecture

---

## Common Scenarios

### Create Cash Account

Standard cash account for bank account tracking:

```javascript
submit("account", "create", {
    "account_number": "1000",
    "account_name": "Cash - Operating Account",
    "account_type": "asset",
    "normal_balance": "debit",
    "account_subtype": "bank",
    "description": "Primary operating cash account",
    "is_reconcilable": true,  // Enable bank reconciliation
    "allow_manual_entries": true
})
```

### Create Foreign Currency Cash Account

For multi-currency operations:

```javascript
submit("account", "create", {
    "account_number": "1020",
    "account_name": "Cash - EUR",
    "account_type": "asset",
    "normal_balance": "debit",
    "account_subtype": "bank",
    "description": "Euro-denominated cash account",
    "currency_code": "EUR",
    "is_reconcilable": true,
    "parent_account_number": "1000"
})
```

### Create Header Account (Subtotal)

For organizing COA with subtotals:

```javascript
submit("account", "create", {
    "account_number": "6000",
    "account_name": "Operating Expenses",
    "account_type": "expense",
    "normal_balance": "debit",
    "account_subtype": "operating_expense",
    "description": "Header for all operating expense accounts",
    "is_header": true,  // No posting allowed
    "allow_manual_entries": false
})
```

### Rename Account for Specific Entity

Entity-specific name while keeping master unchanged:

```javascript
submit("account", "update", {
    "account_number": "4000",
    "legal_entity_id": 13,
    "account_name_override": "Product Revenue - EMEA"
})
```

### Deactivate Unused Account

Soft delete (can be reactivated):

```javascript
submit("account", "delete", {
    "account_number": "1055",
    "deletion_reason": "Account consolidated into 1000",
    "hard_delete": false
})
```

### Remove Test Account

Hard delete (permanent removal):

```javascript
submit("account", "delete", {
    "account_number": "9999",
    "deletion_reason": "Test account cleanup",
    "hard_delete": true
})
```

**Use only for:**
- Test accounts with no transactions
- Duplicate accounts created by mistake
- Never-used accounts

**Never use for accounts with transaction history.**

---

## Getting Reference Data

Before constructing payloads, use search tools to get valid reference data:

| Data Type | How to Get | Example Values |
|-----------|-----------|----------------|
| Account numbers | `query("account")` | `1000`, `4000`, `6100` |
| Parent accounts | `query("account", filters={"is_header": true})` | Header accounts for hierarchy |
| Entity IDs | `query("legal_entity")` | Entity IDs for overrides |
| Currency codes | Fixed list | `USD`, `EUR`, `GBP`, `JPY` |
| Account types | Fixed enum | `asset`, `liability`, `equity`, `revenue`, `expense` |
| Normal balance | Fixed enum | `debit`, `credit` |

**Tip:** Always query reference data dynamically rather than hardcoding values, as they may vary by organization.

---

## Tips & Best Practices

### Account Creation
- **Follow the organisation's numbering**: Number new accounts consistently with the existing chart; classification comes from `account_type` / `account_subtype`, not the number
- **Set parent accounts**: Build hierarchy for better reporting
- **Mark header accounts**: Use `is_header: true` for subtotal-only accounts
- **Enable reconciliation**: Set `is_reconcilable: true` for bank/cash accounts
- **Provide descriptions**: Clear descriptions help users understand account purpose

### Entity Overrides
- **Use sparingly**: Only override when entity truly needs different value
- **Document overrides**: Add reason in `metadata` field
- **Test effective view**: Query `v_accounts_effective` to verify merged result
- **Prefer master updates**: Update master if change applies to all entities

### Foreign Currency Accounts
- **Set currency_code**: Always specify for non-default currency accounts
- **Use hierarchy**: Group under parent cash account
- **Name clearly**: Include currency in account name (e.g., "Cash - EUR")

### Account Deactivation
- **Soft delete first**: Use `hard_delete: false` unless truly necessary
- **Check transactions**: Hard delete only possible if no transactions exist
- **Document reason**: Always provide `deletion_reason`

### Hierarchy Management
- **Parent before children**: Create parent accounts first
- **Logical grouping**: Group related accounts under common parent
- **Limit depth**: Keep hierarchy 2-3 levels max for simplicity

### Metadata Usage
- **Standard keys**: Use consistent key names across accounts
- **Required flags**: Set flags like `requires_cost_center` for validation
- **Default values**: Store defaults for dimension auto-assignment
- **Document structure**: Add comment in description about metadata schema

### Query Optimization
- **Use filters**: Always filter by entity, type, or active status
- **Query effective view**: Use `v_accounts_effective` for entity-specific data
- **Limit results**: Add reasonable limits for large account lists
- **Cache reference data**: Cache account lists for repeated lookups

### Compliance and Audit
- **Classification corrections**: Use the account workflow for subtype/normal-balance corrections. Type changes require no GL history except cogs ↔ expense. Recheck historical reports.
- **Audit trail**: All changes tracked via `updated_by` and `updated_at`
- **Transaction history**: Never hard delete accounts with transaction history
- **Approval workflow**: Critical changes route through approval workflow

---

## Additional Reference

For extended documentation including architecture diagrams, migration examples, and advanced MSEO override patterns, see the full guide:

- GUIDE_ACCOUNTS_MANAGEMENT.md - Extended account management reference (architecture, advanced patterns)

---

## Key Concepts

### Normal Balance

Every account has a "normal balance" (debit or credit) that determines:
- Which side increases the account (debit or credit)
- Which side decreases the account
- How the account appears on financial statements

**Debit Normal Balance** (Assets, Expenses):
- Increase: Debit
- Decrease: Credit

**Credit Normal Balance** (Liabilities, Equity, Revenue):
- Increase: Credit
- Decrease: Debit

### Account Hierarchy

Accounts can be organized hierarchically using `parent_account_number`:

```
1000        Cash (Parent)
1000-01       Cash - USD (Child)
1000-02       Cash - EUR (Child)
```

**Benefits**:
- Organized reporting with subtotals
- Easier navigation in account picker
- Clear relationship between accounts

### Header Accounts

Header accounts (`is_header: true`) serve as subtotal containers:
- Cannot receive journal entry postings
- Used for organizing COA structure
- Show sum of child accounts on reports
- Set `allow_manual_entries: false`

### Reconcilable Accounts

Cash and bank accounts should be marked `is_reconcilable: true`:
- Enables bank statement reconciliation
- Links to bank feed connectors
- Tracks cleared vs. uncleared transactions
- Required for cash management features

### Multi-Currency Accounts

For organizations with foreign currency operations:
- Set `currency_code` field (e.g., "EUR", "GBP")
- Transactions in this account must use specified currency
- Revaluation runs to adjust for FX rate changes
- Separate account per currency recommended

### Entity Overrides

The MSEO pattern allows entity-specific customization:
- Master account defines default for all entities
- Entity override provides custom value for one entity
- Effective view merges master + override
- Only create overrides when truly entity-specific

---

## Query Field Reference

### Display Fields (returned by `query` / `query`)

| Field | Type | Description |
|-------|------|-------------|
| `account_number` | string | Unique account identifier |
| `account_name` | string | Account display name |
| `account_type` | string | asset, liability, equity, revenue, expense |
| `account_subtype` | string | Subtype classification |
| `normal_balance` | string | debit or credit |
| `is_active` | boolean | Active status |
| `is_header` | boolean | Header account (no posting) |
| `is_reconcilable` | boolean | Bank reconciliation enabled |
| `parent_account_number` | string | Parent account for hierarchy |
| `currency_code` | string | Foreign currency code |

### Searchable Fields (text search via `query("account", query=...)`)

| Field | Description |
|-------|-------------|
| `account_number` | Account number (partial match) |
| `account_name` | Account name (partial match) |
| `description` | Account description |
| `global_account_id` | Global identifier |

### Filter Fields (via `filters` parameter)

| Field | Type | Example |
|-------|------|---------|
| `account_type` | string | `"asset"` |
| `account_subtype` | string | `"cash"`, `"bank"`, `"accounts_receivable"`, etc. (one of 89 canonical values — see "Canonical Subtype Taxonomy" above) |
| `is_active` | boolean | `true` |
| `is_header` | boolean | `false` |
| `is_reconcilable` | boolean | `true` |
| `is_global` | boolean | `true` |
| `allow_manual_entries` | boolean | `true` |
| `currency_code` | string | `"EUR"` |
| `parent_account_number` | string | `"1000"` |
| `legal_entity_id` | integer | `13` |

### Sort Fields (via `sort_by` parameter)

| Field | Default | Description |
|-------|---------|-------------|
| `account_number` | Yes | By account number |
| `account_name` | | Alphabetical by name |
| `created_at` | | Newest first |
| `updated_at` | | Recently modified |

### Related Data (returned by `get_entity` with `include_related=True`)

| Related Entity | Description |
|----------------|-------------|
| `account_dimensions` | Default dimension assignments |

---

## Account Dimensions Workflows

Account dimensions allow you to assign default dimension values to accounts, so transactions using those accounts automatically inherit the dimension tags.

### Assign Dimension via Account Create

Pass `account_dimensions` array when creating an account:

```javascript
submit("account", "create", {
    "account_number": "6100",
    "account_name": "Salaries and Wages",
    "account_type": "expense",
    "normal_balance": "debit",
    "account_subtype": "operating_expense",
    "account_dimensions": [
      {"type_code": "department", "value_code": "ENG"}
      // or {"master_dimension_type_id": 81, "master_dimension_value_id": 377};
      // legacy {"dimension_type_id", "dimension_value_id"} are read in the EFFECTIVE namespace
    ]
})
```

### Assign Dimension via Account Update

Use `_action` field to add or remove dimension assignments:

```javascript
submit("account", "update", {
    "account_number": "6100",
    "account_dimensions": [
      {"_action": "add", "type_code": "department", "value_code": "ENG"},
      {"_action": "delete", "type_code": "location"}   // delete needs only the type
    ]
})
```

### Standalone Dimension Assignment

Use the `account_dimension.assign` workflow for assigning dimensions to an existing account without modifying other account properties:

```javascript
submit("account_dimension", "assign", {
    "account_id": 123,
    "legal_entity_id": 13,
    "dimension_type": "department",
    "dimension_value": "ENG"
    // legacy "dimension_type_id"/"dimension_value_id" are still read, in the EFFECTIVE namespace
})
```

---

## End of Guide

This guide covers complete chart of accounts management including all database fields, workflows, query tools, metadata usage, MSEO pattern, and operational best practices for Claude.ai automation.


### Default depreciation classifications

The shipped US GAAP accounts 6510–6560 and IFRS depreciation lines 6410–6470 are expenses (`depreciation_expense`, normal debit). Accumulated-depreciation accounts remain contra assets with normal credit. Corrected templates affect future template imports; they do not silently reclassify existing organizations.

For existing accounts created from the faulty defaults, first verify exact identity and classification against the applicable template. `account.update` accepts subtype corrections, normal-balance corrections and type changes without GL history (plus cogs ↔ expense with history). The maintenance recovery documented in the fixed-assets resource/guide supports one explicitly selected, exact-matching default account at a time, with preview, environment guards, and atomic audit logging. Custom charts must be reviewed separately; never infer a correction from a number alone. Recheck income statement and balance sheet after classification changes because historical presentation changes even though GL debit/credit amounts are unchanged.

### Header posting checks (hardening branch, unreleased)

Journal validation and its direct account lookup reject inactive/header accounts.
Posting-profile create/update rejects those selections too. The optional native
header-account guard protects GL and both populated posting-profile sides; a referenced
account cannot become a header. These changes do not yet enforce ordinary manual-entry
permissions or activate the planned AP/AR membership transition. Use the structured
flags, never account names, and do not change historical flags to bypass a refusal.

### Mandatory account subtype

A canonical subtype must be stored on every account, including headers and inactive accounts.
The account-create workflow requires an explicit subtype. Import/onboarding/connector paths
use the shared type-specific resolver when input omits it; imports disclose the default.
Import updates preserve an existing subtype when the input is derived or omitted. Explicit
incompatible classifications fail. Migration 674 enforces stored non-null/nonblank values;
legacy gaps require reviewed classification and constraint validation.

### Account policy changes after first use

Migrations 675–680 protect used-account scope, identity and deletion. Migration 681
reconciles those guards with PR #233: canonical subtype and normal-balance corrections
are allowed with history; cogs ↔ expense is the only type change allowed with GL lines.
Other type changes require no GL lines across the master account's entities. The database
serializes type changes with first postings. These corrections change historical report
presentation, not posted amounts. Recheck affected statements and control-account purposes.

Used-account header/activity/manual-entry/reconciliation flags, currency, global visibility,
organization and identity remain protected. Entity overrides cannot change effective
activity/manual-entry scope. A usage marker cannot be cleared, and deletion remains refused
after references disappear. The operator correction path below applies to other settings
only with no retained financial evidence. This does not activate AP/AR aging membership.

### Reviewed configuration corrections (operator maintenance)

`review_account_configuration_transition.py prepare` is read-only and produces an exact
proposal/hash. After a real accounting review, a separately authorized operator can apply
that exact proposal with an approval reference/reason. Never invent approval, self-approve,
write a claimed reviewer identity, disable a guard, or remove evidence to satisfy the checks.
The tool records the authenticated database actor; its review reference is supplied by the
operator, not independently authenticated against a workflow system.

This path is limited to master configuration with no retained GL/document evidence or
other blocking account references. Category GL fields, item expense fields, vendor/customer
defaults and allocation source/target account IDs are included even when their column names
do not contain `account_number`. Physical bank numbers are excluded. Unknown account-bearing
columns or unsupported types require operator review of the inventory, never automatic
exclusion. Old unapplied proposals must be prepared/reviewed again after the inventory update.
It rechecks under locks, audits atomically and leaves
no lasting permit. Source references, stale evidence or unsupported source-table shapes
refuse the operation. Normal account/import workflows cannot use the permit. Entity-override changes, retirement with history and AP/AR activation remain separate
unfinished transitions. Classification corrections follow the rules above. An idempotent receipt is not proof the account was never changed later;
read `current_state_matches_receipt` too.


Unreleased migrations 686–694 add reviewed per-entity enforcement for ordinary
`JOURNAL_ENTRY` accounts. Installation leaves it disabled. When activated, accounts
must be active, non-header and effectively `allow_manual_entries=true`; both executor
preflight and DB commit enforce this. Caller metadata cannot override a refusal.
Use a supported subledger operation for control-account adjustments; never toggle flags
to force a posting. Exact, reciprocally linked dated reversals and the evidence-backed residual write-off
path below have checked exceptions; other control adjustments remain refused.
The operator activation receipt is permanent and source changes invalidate a proposal.
This does not activate AP/AR aging membership or certify other typed posting routes.


Shared service journal posting checks explicit master account IDs as well as numbers
against the selected entity. Both identifiers must agree when supplied together;
missing, ambiguous, inactive and header accounts are refused before journal creation.
An ID is not a permission bypass. Non-finite, negative or two-sided amounts are refused.
Automated callers retain their typed operation semantics; these checks do not authorize
control-account journals where the reviewed manual-entry policy would refuse them.

Activation review and database enforcement use the same exact-reversal permission
check. Valid historical reversals alone no longer block a proposal. Missing reciprocal
links, wrong dates, incomplete or non-finite amounts remain unresolved. This exception
does not authorize a write-off, FX journal or arbitrary control-account correction.

Profile-transition proposals now bind a streamed SHA-256 fingerprint of retained
entity headers, GL rows and application history, not only counts. Same-count edits
refuse apply; regenerate older proposals and obtain a new exact review. Apply locks
these source tables before taking its snapshot. This does not expand the supported
operations beyond reviewed unused replacement and narrow acquisition retirement.

### Controlled-reversal currency permission (unreleased)

Migration 690 requires the original and reversal functional currencies to agree
with the entity before granting the exact-reversal exception. A NULL header
functional currency inherits the entity currency; an explicit mismatch or missing
entity currency fails the permission check. Equal numeric amounts alone do not
establish a valid reversal across currencies. Activation review uses this same
check and old proposals must be regenerated after installation. No policy or aging
membership is activated by this migration.

### Audited residual write-off permission (unreleased, migrations 692–694)

For an entity with reviewed ordinary-journal enforcement enabled,
`reconciliation.write_off_item` can now post a same-currency residual against the
invoice's booked AP/AR control account. The database validates the existing applied
settlement, completed run in the same entity/scope, posted unreversed payment and
invoice, matching party, entity currency, configured limit, remaining invoice amount
and booked control-account basis. The journal must contain the exact two residual
lines, dated no earlier than either document, with a canonical P&L counterpart.
Revenue, expense and COGS counterparts are supported with the correct debit/credit
direction; names do not determine permission. A valid configured gain can credit an
expense account. This evidenced operation also supports a non-manual P&L account.

Successful validation creates a private, immutable receipt bound to that journal
and settlement item. Commit requires the invoice to be settled and source ledgers
to match the captured evidence. Failure rolls back the journal, receipt and
settlement together. Caller metadata or direct receipt insertion cannot grant
permission. Changing a permitted journal invalidates its permission; use supported
reversal/correction workflows rather than editing the receipt.

This exception currently supports `AP_PAYMENT`/`AR_PAYMENT` against the matching
invoice type. It does not authorize FX, credit-memo/prepayment/refund/card-funded
write-offs, multi-control allocations or arbitrary control-account corrections.
Those routes require their own evidence and permission work before entity activation.
Existing journals receive no automatic receipts. Installation leaves entity policy
and live aging membership unchanged.

The gateway dates the adjustment at the later document date and still refuses a
closed period. The shared writer records header `functional_amount` equal to the
functional GL debit total it books; this does not introduce currency conversion.

### Full-settlement FX permission (unreleased, migration 695)

A separate database-validated exception now covers a first full AP/AR payment
and invoice settlement across document currencies. Both documents must use the
same active controlled account and party; the exact journal clears their booked
functional difference against a canonical P&L counterpart. Account names and
`is_reconcilable` do not grant this exception. The immutable FX receipt and final
settlement are checked atomically. Partial allocations, previously applied
documents, other funding routes and historical backfills remain outside this
permission. Installation does not activate entity enforcement or change aging
membership. Review required routes before activating an entity.

### Owner contributions (requires migration 735)

Use equity subtype `owner_contributions` for contributed reserves, excluding share capital,
share premium, OCI, shareholder loans and distributions. Its cash-flow classification is
financing on the equity line; a noncash equity transfer produces no cash flow or P&L.
Adding the catalog entry does not reclassify existing accounts. Obtain approval for an existing
account change after rehearsing historical reports and any source-bound review invalidation.
Migration 735 is applied in production; application deployment is pending. Check tool availability before submitting this subtype.

## Account and reporting-decision observability (deployed 2026-10-14)

Migration 737 exposes `master_updated_at` and `entity_updated_at` on account reads.
`updated_at` is the later timestamp; `updated_by` follows that source (master wins
on equal timestamps). An old override timestamp no longer masks a master update.
No stored timestamps are rewritten.

`query(entity_type="reporting_decision", filters={"legal_entity_id": ENTITY,
"transaction_id": TRANSACTION})` and `get_entity` expose read-only decision status.
`is_latest` identifies superseded decisions. `header_matches` checks the saved header;
`ledger_decision_applies` requires both a matching header and the latest decision.
`performance_evidence_matches` checks the saved line/classification evidence;
`performance_review_valid` also requires the latest decision and the existing report
predicate. A false performance flag does not invalidate an otherwise matching ledger
eligibility decision. It does not prove a report needs that performance exception:
ordinary classification may already resolve the ambiguity. Review-note attachments
are separate. These diagnostics do not renew decisions or change report calculations.

Account master updates write `account_updated` to the organization-scoped audit log
in the same transaction, with actor, account ID and before/after master fields. Audit
failure rolls back the change. Query `audit_log` by `record_id` and `table_name` to
find it. This adds future audit entries; it does not fabricate missing historical
entries. Existing workflow history remains the record for earlier changes.


### New-company manual-journal default

Migration 738 and the matching PR328 application changes are deployed and verified.
Company/legal-entity creation can resume.
The database now ensures each newly inserted legal entity receives enabled manual-journal
permission enforcement in the same transaction as creation. This includes the
onboarding wizard, the normal legal-entity workflow, and future tenant clones.
The receipt identifies `new_entity_default_v1`, the entity and database actor;
it records automatic initialization, not a human review of historical books.

The standard IFRS and US GAAP chart seeders create AP/AR control accounts and
headers with manual entries disabled. Ordinary expense and other eligible leaf
accounts remain available for manual journals. Existing master accounts are not
updated on template replay. A new entity inside an existing organization still
inherits that organization's account configuration; existing shared flags are
not silently rewritten. Custom charts must explicitly configure their control
accounts and supported posting routes before first financial use.

The policy enforces the effective account configuration; it does not infer control
status from an account's name or number. Invoice/payment and supported typed
adjustment routes retain their existing checks and exceptions. Missing or invalid
manual-journal account setup fails closed. Caller metadata cannot disable the
policy. Creation failure rolls back its policy receipt too.

Existing entities retain their current enabled/disabled state and receipts. They
require a separately approved reviewed transition. There is no blanket activation,
account reclassification, journal posting, report-decision renewal, aging change,
or September work in this implementation.
