# Bank Accounts Management

> **Note (2026-02):** This document covers bank account CRUD operations. For bank statements and reconciliation, see [Bank Statements Management](bank-statements-management.md). For corporate cards, see [Corporate Cards Management](corporate-cards-management.md).
>
> **Important (2026-02):** Every bank account MUST be linked to a GL account from the chart of accounts via `gl_account_number`. This is critical for bank-aware GL resolution — when processing bank transactions, the "bank side" of every GL entry comes from the bank account's `gl_account_number`. See [GL Account Requirement](#gl-account-requirement) below.
>
> **Deprecated (2026-02):** The following workflows have been removed as part of banking simplification:
> - `bank_account_change_request.*` - Now handled by standard workflow approval system
> - `bank_account_verification.*` - Verification status updated directly via `bank_account.verify`
> - `bank_account_integration.*` - Replaced by connector_registry system (see Connector Framework Guide)

**Available Workflows (12 total across 3 object types):**

| Object Type | Operation | Purpose | When to Use |
|-------------|-----------|---------|-------------|
| [`bank_account`](#company-bank-accounts) | `create` | Create company bank account | Setting up operating accounts, payroll accounts |
| `bank_account` | `update` | Update account details | Change account name, GL mapping, default flags |
| `bank_account` | `delete` | Deactivate account | Close account at bank, stop using account |
| `bank_account` | `verify` | Verify account status | Mark account as verified after validation |
| [`vendor_bank_account`](#vendor-bank-accounts) | `create` | Add vendor payment account | Set up vendor for ACH/wire payments |
| `vendor_bank_account` | `update` | Update vendor account | Change nickname, default flag, status |
| `vendor_bank_account` | `delete` | Deactivate vendor account | Vendor changed banks, close account |
| `vendor_bank_account` | `verify` | Verify vendor account | Mark verified after micro-deposits, bank letter |
| [`employee_bank_account`](#employee-bank-accounts) | `create` | Add employee bank account | Set up direct deposit, reimbursements |
| `employee_bank_account` | `update` | Update employee account | Employee changes banks |
| `employee_bank_account` | `delete` | Deactivate employee account | Close account, stop using |
| `employee_bank_account` | `verify` | Verify employee account | Mark verified after validation |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

**Available Query Tools:**

| Tool | Purpose |
|------|---------|
| `get_entity("bank_account", id=X)` | Get single company bank account |
| `get_entity("vendor_bank_account", id=X)` | Get single vendor bank account |
| `get_entity("employee_bank_account", id=X)` | Get single employee bank account |
| `query("bank_account", filters)` | List company bank accounts |
| `query("vendor_bank_account", filters)` | List vendor bank accounts |
| `query("employee_bank_account", filters)` | List employee bank accounts |
| `query("bank_account", query, filters)` | Search company bank accounts |

---

## Complete Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

### Company Bank Accounts Table (bank_accounts)

Company bank accounts are operating accounts owned by the legal entity, used for payments, payroll, and collections.

**Identification Fields:**
- `id` (bigint, PK) - Unique bank account identifier
- `legal_entity_id` (integer, FK to legal_entities, NOT NULL) - Legal entity owning this account
- `bank_account_code` (varchar(30), NOT NULL, unique per entity) - Short code (e.g., "CASH-USD-001")
- `account_name` (varchar(255), NOT NULL) - Display name (e.g., "Operating Account - USD")

**Bank Details:**
- `bank_name` (varchar(255), NULL) - Bank name (e.g., "Wells Fargo", "JP Morgan Chase")
- `bank_country` (varchar(2), NULL) - ISO 2-letter country code (e.g., "US", "GB")
- `account_holder_name` (varchar(255), NULL) - Name on account

**Account Numbers (Encrypted):**
- `account_number` (varchar(100), NULL) - Bank account number (encrypted)
- `routing_number` (varchar(20), NULL) - ACH routing number (9 digits for US) (encrypted)
- `iban` (varchar(34), NULL) - International Bank Account Number (encrypted)
- `swift_code` (varchar(20), NULL) - SWIFT/BIC code for international wire transfers

**Account Classification:**
- `currency` (varchar(3), NOT NULL) - ISO currency code (e.g., "USD", "EUR", "GBP")
- `account_type` (varchar(20), NOT NULL, default: "checking") - Account type
  - Valid values: checking, savings, credit_card, line_of_credit, investment, other
- `usage_type` (varchar(50), default: "operating") - Primary use case
  - Valid values: operating, payroll, tax, savings

**GL Integration:**
- `gl_account_number` (varchar(50), NOT NULL, FK to master_accounts) - GL account this bank account maps to
- `cash_flow_category` (varchar(50), NULL) - Cash flow statement category (e.g., "Operating", "Investing", "Financing")

**Default Flags:**
- `is_operating` (boolean, default: false) - Primary operating account
- `is_default_receipts` (boolean, default: false) - Default for customer payments/collections
- `is_default_payments` (boolean, default: false) - Default for vendor payments

**Transaction Limits:**
- `daily_limit` (numeric(15,2), NULL) - Daily transaction limit (NULL = no limit)
- `monthly_limit` (numeric(15,2), NULL) - Monthly transaction limit (NULL = no limit)

**Verification:**
- `verification_status` (varchar(50), default: "unverified") - Verification status
  - Valid values: unverified, pending, verified, failed
- `verified_at` (timestamp with time zone, NULL) - When account was verified

**Payment Methods:**
- `supported_payment_methods` (text[], NULL) - Payment methods this account can originate (e.g., `["ach", "wire"]`). Used by the payment proposal agent to match source bank accounts to vendor payment requirements when `preferred_source_bank_account_id` is not set on the vendor bank account. Common values: `ach`, `wire`, `sepa`, `swift`, `check`.

**Statement Import:**
- `statement_import_format` (varchar(50), NULL) - Import format (e.g., "OFX", "CSV", "QBO")

**Metadata & Status:**
- `metadata` (jsonb, NULL) - Custom fields, connector IDs, external references
- `is_active` (boolean, default: true) - Soft delete flag
- `created_at` (timestamp with time zone, default: now()) - Creation timestamp
- `created_by` (integer, FK to users, NULL) - User who created
- `updated_at` (timestamp with time zone, default: now()) - Last update timestamp
- `updated_by` (integer, FK to users, NULL) - User who last updated

**Unique Constraints:**
- `(legal_entity_id, bank_account_code)` - Bank account code unique per entity

**Indexes:**
- `legal_entity_id` - Query by entity
- `gl_account_number` - Query by GL account
- `(usage_type, legal_entity_id)` - Query by usage
- `(verification_status, legal_entity_id)` - Query verified accounts

**Referenced By:**
- `bank_statements.bank_account_id` - Bank statements for this account
- `bank_statement_lines.bank_account_id` - Individual statement transactions
- `bank_account_integrations.bank_account_id` - Banking provider integrations

---

### Vendor Bank Accounts Table (vendor_bank_accounts)

Vendor bank accounts store payment instructions for paying vendors via ACH, wire, check, or other methods.

**Identification Fields:**
- `id` (bigint, PK) - Unique vendor bank account identifier
- `master_vendor_id` (integer, FK to master_vendors, NOT NULL) - Vendor this account belongs to
- `legal_entity_id` (integer, FK to legal_entities, NOT NULL) - Legal entity relationship
- `account_nickname` (varchar(100), NULL) - Friendly name (e.g., "Primary USD Account")

**Payment Method:**
- `payment_method` (varchar(50), NOT NULL) - Payment method for this account
  - Valid values: ach, wire_domestic, wire_international, sepa, swift, check, card, crypto, paypal, venmo
- `currency_code` (varchar(3), NOT NULL, default: "USD") - Currency for payments
- `usage_type` (varchar(50), NULL) - Account purpose
  - Valid values: ap_invoice, expense_reimbursement, payroll, other, NULL

**Bank Details:**
- `bank_name` (varchar(255), NULL) - Bank name
- `bank_country` (varchar(2), NULL) - ISO 2-letter country code
- `account_holder_name` (varchar(255), NOT NULL) - Name on account (must match vendor)
- `account_holder_address` (text, NULL) - Account holder full address
- `account_holder_country` (varchar(2), NULL) - Account holder country

**US ACH Details (encrypted):**
- `routing_number` (varchar(100), NULL) - ACH routing number (9 digits)
- `account_number` (varchar(100), NULL) - Bank account number
- `account_type` (varchar(50), NULL) - Account type
  - Valid values: checking, savings, corporate, money_market, other

**International Wire Details (encrypted):**
- `iban` (varchar(50), NULL) - International Bank Account Number
- `swift_code` (varchar(20), NULL) - SWIFT code (8 or 11 characters)
- `bic_code` (varchar(20), NULL) - BIC code (alternative to SWIFT)
- `sort_code` (varchar(20), NULL) - UK sort code
- `bsb_number` (varchar(20), NULL) - Australia BSB number

**Intermediary Bank (for some international wires):**
- `intermediary_bank_name` (varchar(255), NULL) - Intermediary bank name
- `intermediary_swift_code` (varchar(20), NULL) - Intermediary SWIFT code
- `intermediary_account_number` (varchar(100), NULL) - Intermediary account number

**Default & Status:**
- `is_active` (boolean, default: true) - Account is active for payments
- `is_default` (boolean, default: false) - Default account for this vendor+entity+payment method+currency
- `preferred_source_bank_account_id` (integer, FK to bank_accounts, NULL) - Which of our bank accounts to use as the source when paying this vendor. Entity-scoped: entity A and entity B each have a separate `vendor_bank_accounts` row and can point to different source banks. When NULL, the payment proposal agent falls back to entity-level `bank_accounts.supported_payment_methods` matching. The source must be a bank account of the vendor bank account's own legal entity: a create or update naming another entity's bank is refused ("preferred source bank … must be a bank account of legal entity …"). On update the stored row's entity decides, not a `legal_entity_id` in the payload. `null` clears it. The same rule applies to `employee_bank_account.preferred_source_bank_account_id`.

**Verification:**
- `verification_status` (varchar(50), default: "unverified") - Verification status
  - Valid values: unverified, pending, verified, failed, expired
- `verification_method` (varchar(50), NULL) - How verified (e.g., "micro_deposits", "bank_letter", "plaid")
- `verified_at` (timestamp with time zone, NULL) - When verified
- `verified_by` (integer, FK to users, NULL) - User who verified

**Transaction Limits:**
- `daily_limit` (numeric(15,2), NULL) - Daily payment limit
- `monthly_limit` (numeric(15,2), NULL) - Monthly payment limit
- `per_transaction_limit` (numeric(15,2), NULL) - Per-transaction limit
- `requires_dual_approval` (boolean, default: false) - Require two approvers for payments

**Integration:**
- `connector_id` (uuid, NULL) - Banking connector UUID (if linked)
- `external_account_id` (varchar(100), NULL) - External system account ID

**Metadata & Audit:**
- `metadata` (jsonb, NULL) - Custom fields, integration data
- `created_at` (timestamp with time zone, default: now()) - Creation timestamp
- `created_by` (integer, FK to users, NULL) - User who created
- `updated_at` (timestamp with time zone, default: now()) - Last update timestamp
- `updated_by` (integer, FK to users, NULL) - User who last updated
- `deleted_at` (timestamp with time zone, NULL) - Soft delete timestamp
- `deleted_by` (integer, FK to users, NULL) - User who deleted

**Unique Constraints:**
- `(id, master_vendor_id)` - Unique ID per vendor (for partitioning)
- `(master_vendor_id, legal_entity_id, payment_method, currency_code)` WHERE is_default=true - Only one default per combination

**Indexes:**
- `(master_vendor_id, legal_entity_id)` - Query by vendor and entity
- `(master_vendor_id, legal_entity_id, is_active)` WHERE is_active=true - Query active accounts
- `connector_id` WHERE connector_id IS NOT NULL - Query by connector

---

### Employee Bank Accounts Table (employee_bank_accounts)

Employee bank accounts are used for payroll direct deposit, expense reimbursements, and other payments to employees.

**Identification Fields:**
- `id` (bigint, PK) - Unique employee bank account identifier
- `employee_id` (integer, FK to employees, NOT NULL) - Employee this account belongs to
- `legal_entity_id` (integer, FK to legal_entities, NOT NULL) - Legal entity relationship
- `account_nickname` (varchar(100), NULL) - Friendly name (e.g., "Personal Checking")

**Payment Method:**
- `payment_method` (varchar(50), NOT NULL, default: "ach") - Payment method
  - Valid values: ach, wire, check, paycard, other
- `currency_code` (varchar(3), NOT NULL, default: "USD") - Currency code
- `usage_type` (varchar(50), NOT NULL) - Account purpose
  - Valid values: payroll, benefit, stipend, reimbursement

**Bank Details:**
- `bank_name` (varchar(255), NULL) - Bank name
- `bank_country` (varchar(2), NULL) - ISO 2-letter country code
- `account_holder_name` (varchar(255), NOT NULL) - Name on account (should match employee)
- `account_holder_address` (text, NULL) - Account holder address

**US ACH Details (encrypted):**
- `routing_number` (varchar(100), NULL) - ACH routing number
- `account_number` (varchar(100), NULL) - Bank account number
- `account_type` (varchar(50), NULL) - Account type
  - Valid values: checking, savings, paycard, other

**International Details (encrypted):**
- `iban` (varchar(50), NULL) - International Bank Account Number
- `swift_code` (varchar(20), NULL) - SWIFT code

**Direct Deposit Allocation:**
- `deposit_allocation_type` (varchar(50), NULL) - How to split direct deposit
  - Valid values: amount, percentage, remainder, NULL
- `deposit_amount` (numeric(15,2), NULL) - Fixed dollar amount (if type=amount)
- `deposit_percentage` (numeric(5,2), NULL) - Percentage (0-100) (if type=percentage)
- `deposit_order` (integer, default: 1) - Order for multiple accounts (1=first)

**Default & Status:**
- `is_active` (boolean, default: true) - Account is active for payments
- `is_default` (boolean, default: false) - Default account for this employee+entity+usage type+currency

**Verification:**
- `verification_status` (varchar(50), default: "unverified") - Verification status
  - Valid values: unverified, pending, verified, failed
- `verification_method` (varchar(50), NULL) - How verified (e.g., "micro_deposits", "plaid", "voided_check")
- `verified_at` (timestamp with time zone, NULL) - When verified
- `verified_by` (integer, FK to users, NULL) - User who verified

**Prenote (ACH Pre-notification):**
- `prenote_sent_at` (timestamp with time zone, NULL) - When prenote was sent
- `prenote_cleared_at` (timestamp with time zone, NULL) - When prenote cleared (3 business days)
- `prenote_status` (varchar(50), NULL) - Prenote status (e.g., "sent", "cleared", "rejected")

**Integration:**
- `connector_id` (uuid, NULL) - Banking connector UUID
- `external_account_id` (varchar(100), NULL) - External system account ID

**Metadata & Audit:**
- `metadata` (jsonb, NULL) - Custom fields
- `created_at` (timestamp with time zone, default: now()) - Creation timestamp
- `created_by` (integer, FK to users, NULL) - User who created
- `updated_at` (timestamp with time zone, default: now()) - Last update timestamp
- `updated_by` (integer, FK to users, NULL) - User who last updated
- `deleted_at` (timestamp with time zone, NULL) - Soft delete timestamp
- `deleted_by` (integer, FK to users, NULL) - User who deleted

**Unique Constraints:**
- `(employee_id, legal_entity_id, usage_type, currency_code)` WHERE is_default=true - Only one default per combination

**Indexes:**
- `(employee_id, legal_entity_id)` - Query by employee and entity
- `(employee_id, is_active)` WHERE is_active=true - Query active accounts

---

## GL Account Requirement

**Every bank account MUST have a `gl_account_number`** that maps to a valid account in the chart of accounts. This account represents the bank balance on the balance sheet.

### Why This Matters

When the bank transaction processor posts GL entries for bank fees, interest, transfers, etc., it uses **bank-aware GL resolution**:
- The **bank side** of the GL entry always comes from the bank account's `gl_account_number` (not from the posting profile)
- The **counterpart side** (expense, income, clearing) comes from posting profiles

This means each bank account posts to its own specific GL account, which is critical for companies with multiple banks.

### Before Creating a Bank Account

**CRITICAL: Each bank account MUST have its own dedicated GL account.** Do NOT use generic "Cash" or "Cash and Cash Equivalents" accounts — those are summary/header accounts, not bank-specific ones.

1. **Search the chart of accounts** for an existing dedicated GL account for this bank:
   ```javascript
   query("account", query="LHV")  // Search by bank name
   // or browse the bank accounts
   query("account", filters={"account_subtype": "bank"})
   ```

2. **If a dedicated GL account already exists** for this specific bank (e.g., `1011 LHV Bank EUR`), use it. A dedicated account is one whose name references the specific bank — NOT a generic account like "1000 Cash and Cash Equivalents", "1001 Cash on Hand", or "1099 Other Cash". Generic/summary accounts must never be used as `gl_account_number`.

3. **If NO dedicated GL account exists**, create new ones:
   ```javascript
   // GL account for the bank account itself
   submit("account", "create", {
     account_number: "1011",  // Pick next available number in 10xx range
     account_name: "LHV Bank EUR",  // Name matching the bank
     account_type: "asset",
     account_subtype: "bank",
     is_active: true,
     normal_balance: "debit",
     description: "Bank account for LHV EUR operating account"
   })

   // If this bank has corporate cards, create ONE GL account for all cards of this bank
   submit("account", "create", {
     account_number: "1012",  // Next available number
     account_name: "LHV Bank Cards EUR",  // Bank name + "Cards"
     account_type: "asset",
     account_subtype: "bank",
     is_active: true,
     normal_balance: "debit",
     description: "Corporate card clearing for LHV EUR cards"
   })
   ```
   Then use the bank GL account number as `gl_account_number` when creating the bank account.

   **Note on card accounts:** Create ONE card GL account per bank, not per individual card. For example, all cards issued by one bank share a single card account such as `1012 LHV Bank Cards EUR`. This keeps the chart of accounts clean while maintaining proper bank-level separation.

### Example GL Account Patterns

An example layout only; the ranges and bank names below are illustrations, not a required
numbering. Follow the organisation's own chart of accounts.

| Bank Account Type | GL Account Range | Example |
|------------------|------------------|---------|
| Primary bank operating | 1010-1019 | 1011 LHV Bank EUR |
| Bank cards (per bank) | 1010-1019 | 1012 LHV Bank Cards EUR |
| Secondary bank | 1020-1029 | 1021 Wise USD |
| Secondary bank cards | 1020-1029 | 1022 Wise Cards USD |
| Payroll accounts | 1030-1039 | 1031 Payroll - Chase |
| Savings accounts | 1040-1049 | 1041 Savings - Wells Fargo |
| Payment processor clearing | 1060-1069 | 1061 Stripe Clearing |

**Rules:**
- Each physical bank account MUST have its own GL account number — do NOT share between banks
- Each bank that has corporate cards gets ONE dedicated card GL account (not per card)
- Do NOT assign a generic "Cash" account (e.g., 1000) as the `gl_account_number` — always create a bank-specific one
- Numbering convention: group related accounts together (bank + its cards = adjacent numbers)

---

## Company Bank Accounts

Company bank accounts are operating accounts owned by the legal entity for business operations.

### Creating a Company Bank Account

Use the `bank_account.create` workflow to create company bank accounts.

An owner or admin approves a submission from an agent, and anyone's submission
that carries an IBAN or an account number (the default definitions'
"Owner or admin approves" step, the same for `bank_account.update`). Such a
submit returns `status: "pending"` with a `workflow_id` and no
`bank_account_id`; the account exists once the task is approved. A person's
change of other fields (name, limits, default flags) runs at once.
Executing a create refuses a second active account with the same IBAN and
currency in the entity, so two waiting creates for one IBAN leave one account.

**Workflow: bank_account.create**

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="bank_account", operation="create")

// Step 2: Submit with discovered fields
submit("bank_account", "create", {
  // Required fields
  legal_entity_id: 13,
  bank_account_code: "CASH-USD-001",
  account_name: "Main Operating Account",
  gl_account_number: "1010",  // Must exist in chart of accounts

  // Bank details
  bank_name: "Wells Fargo",
  bank_country: "US",
  account_holder_name: "Acme Corp Inc",

  // Account numbers (will be encrypted)
  account_number: "1234567890",
  routing_number: "121000248",

  // Classification
  currency: "USD",
  account_type: "checking",
  usage_type: "operating",

  // Default flags
  is_operating: true,
  is_default_receipts: false,
  is_default_payments: true,

  // Limits (optional)
  daily_limit: 100000.00,
  monthly_limit: 2000000.00
})
// Tip: Use validate_only=true to check payload before submitting
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `legal_entity_id` | number | Legal entity ID (use `query("legal_entity")`) |
| `bank_account_code` | string | Short code, max 30 chars, unique per entity |
| `account_name` | string | Display name, max 255 chars |
| `gl_account_number` | string | GL account number (must exist, max 50 chars) |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `bank_name` | string | Bank name, max 255 chars |
| `bank_country` | string | ISO 2-letter country code (e.g., "US") |
| `account_holder_name` | string | Name on account, max 255 chars |
| `account_number` | string | Account number (encrypted), max 100 chars |
| `routing_number` | string | ACH routing number (encrypted), max 20 chars |
| `iban` | string | International account number (encrypted), max 34 chars |
| `swift_code` | string | SWIFT/BIC code, max 20 chars |
| `currency` | string | ISO currency code (default: "USD") |
| `account_type` | string | checking, savings, credit_card, line_of_credit, investment, other |

> **Credit Card accounts**: When a bank account has `account_type = 'credit_card'` and is linked to a card program via `card_bank_account_id`, imported statements are automatically routed to card transaction processing instead of regular bank statement lines.
| `usage_type` | string | operating, payroll, tax, savings (default: "operating") |
| `cash_flow_category` | string | Cash flow category, max 50 chars |
| `is_operating` | boolean | Primary operating account (default: false) |
| `is_default_receipts` | boolean | Default for collections (default: false) |
| `is_default_payments` | boolean | Default for payments (default: false) |
| `daily_limit` | number | Daily transaction limit (NULL = no limit) |
| `monthly_limit` | number | Monthly transaction limit (NULL = no limit) |
| `supported_payment_methods` | string[] | Payment methods this account can originate (e.g., `["ach", "wire"]`). Used by payment proposal agent for source bank matching when `preferred_source_bank_account_id` is not set on the vendor bank account. Common values: `ach`, `wire`, `sepa`, `swift`, `check` |
| `statement_import_format` | string | Import format (e.g., "OFX", "CSV") |
| `metadata` | object | Custom fields, connector IDs |

**Validation:**
- `legal_entity_id` must exist
- `bank_account_code` must be unique per entity
- `gl_account_number` must exist in chart of accounts
- `account_type` must be valid enum value
- `usage_type` must be valid enum value
- `currency` must be valid ISO code
- `daily_limit`, `monthly_limit` must be >= 0 if provided
- Only one account can have `is_default_payments=true` per currency

**Response:**
```json
{
  "success": true,
  "bank_account_id": 123,
  "bank_account_code": "CASH-USD-001",
  "account_name": "Main Operating Account",
  "verification_status": "unverified"
}
```

### Example: Create Primary Operating Account

```javascript
submit("bank_account", "create", {
    legal_entity_id: 13,
    bank_account_code: "CASH-USD-MAIN",
    account_name: "Wells Fargo Operating - USD",
    gl_account_number: "1010",
    bank_name: "Wells Fargo",
    account_number: "9876543210",
    routing_number: "121000248",
    currency: "USD",
    account_type: "checking",
    usage_type: "operating",
    is_operating: true,
    is_default_payments: true,
    daily_limit: 100000.00
})
```

**Result:** Primary operating account created

### Example: Create Payroll Account

```javascript
submit("bank_account", "create", {
    legal_entity_id: 13,
    bank_account_code: "CASH-USD-PAYROLL",
    account_name: "Payroll Account - Chase",
    gl_account_number: "1015",
    bank_name: "JP Morgan Chase",
    account_number: "5555666677",
    routing_number: "021000021",
    currency: "USD",
    account_type: "checking",
    usage_type: "payroll",
    monthly_limit: 500000.00
})
```

**Result:** Separate payroll account created

---

### Updating a Company Bank Account

Use the `bank_account.update` workflow to update bank account details.

**Workflow: bank_account.update**

```javascript
submit("bank_account", "update", {
    bank_account_id: 123,
    // Only include fields you want to change — every other field
    // stays untouched. Wire-instruction fields (iban, swift_code,
    // bank_country, account_number, routing_number, currency,
    // bank_name) ARE updateable; the AR invoice PDF's "Pay to"
    // block reads them from this row when the account is marked
    // is_default_receipts=true.
    iban: "BE12 1234 5678 9012",
    swift_code: "TRWIBEB1XXX",
    bank_country: "BE",
    currency: "EUR",
    is_default_receipts: true
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `bank_account_id` | number | Bank account ID to update |

**Optional Fields (any combination):**

| Field | Type | Notes |
|-------|------|-------|
| `account_name` | string | Display name (e.g. "Wise EUR — Operating") |
| `account_holder_name` | string | Legal name on the account — must match the legal_entity's name for invoice "Pay to" block |
| `account_type` | string | `checking`, `savings`, … |
| `usage_type` | string | `operating`, `payroll`, `tax`, `savings` |
| `cash_flow_category` | string | Cash-flow report category |
| `bank_name` | string | e.g. "Wise", "LHV", "Swedbank" |
| `bank_country` | string | ISO 2-letter code (e.g. `BE` for Wise EUR) |
| `iban` | string | International Bank Account Number — required for SEPA / cross-border EU payments |
| `swift_code` | string | SWIFT / BIC (e.g. `TRWIBEB1XXX`) |
| `account_number` | string | US ACH and other non-IBAN flows |
| `routing_number` | string | US ACH / wire routing number |
| `currency` | string | ISO 4217 (`EUR`, `USD`, …) |
| `gl_account_number` | string | Mapped GL cash account |
| `daily_limit` / `monthly_limit` | number | Transaction limits |
| `statement_import_format` | string | e.g. `wise_csv`, `lhv_camt053` |
| `supported_payment_methods` | array | Methods this account supports |
| `is_operating` | boolean | Primary operating account flag |
| `is_default_receipts` | boolean | **Default for AR collection — the row picked by the invoice PDF "Pay to" lookup when currency matches** |
| `is_default_payments` | boolean | Default for AP outflows |
| `is_active` | boolean | Active flag |
| `metadata` | object | Free-form JSONB metadata |

> **Not updateable:** `legal_entity_id` and `bank_account_code` (intentionally immutable — create a new account instead).

**Validation:**
- `bank_account_id` must exist
- Cannot change `legal_entity_id` or `bank_account_code`
- `iban`, `swift_code`, `bank_country`, `currency` are uppercased + stripped server-side
- All other validations same as create

**Response:**
```json
{
  "success": true,
  "bank_account_id": 123,
  "updated_fields": ["iban", "swift_code", "bank_country", "currency", "is_default_receipts"]
}
```

---

### Verifying a Company Bank Account

Use the `bank_account.verify` workflow to mark an account as verified.

**Workflow: bank_account.verify**

```javascript
submit("bank_account", "verify", {
    bank_account_id: 123,
    verification_status: "verified",
    verification_method: "bank_letter"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `bank_account_id` | number | Bank account ID |
| `verification_status` | string | New status: unverified, pending, verified, failed |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `verification_method` | string | How verified (e.g., "micro_deposits", "bank_letter", "plaid") |

**Validation:**
- `bank_account_id` must exist
- `verification_status` must be valid enum value

**Response:**
```json
{
  "success": true,
  "bank_account_id": 123,
  "verification_status": "verified",
  "verified_at": "2026-01-14T10:30:00Z"
}
```

---

### Deactivating a Company Bank Account

Use the `bank_account.delete` workflow to deactivate (soft delete) a bank account.

**Workflow: bank_account.delete**

```javascript
submit("bank_account", "delete", {
    bank_account_id: 123,
    deletion_reason: "Account closed at bank"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `bank_account_id` | number | Bank account ID to deactivate |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `deletion_reason` | string | Reason for deactivation (audit trail) |

**Validation:**
- `bank_account_id` must exist
- No pending transactions
- If default account, must set another account as default first

**Response:**
```json
{
  "success": true,
  "bank_account_id": 123,
  "is_active": false
}
```

**Note:** Bank accounts are never hard-deleted, only marked `is_active=false` to preserve historical data.

---

## Vendor Bank Accounts

Vendor bank accounts store payment instructions for paying vendors.

### Creating a Vendor Bank Account

Use the `vendor_bank_account.create` workflow to add vendor payment accounts.

**Workflow: vendor_bank_account.create**

```javascript
submit("vendor_bank_account", "create", {
    // Required fields
    master_vendor_id: 456,
    legal_entity_id: 13,
    payment_method: "ach",
    account_holder_name: "Acme Supplies Inc",

    // Bank details
    bank_name: "Chase Bank",
    bank_country: "US",

    // ACH details (encrypted)
    routing_number: "021000021",
    account_number: "9988776655",
    account_type: "checking",

    // Classification
    currency_code: "USD",
    account_nickname: "Primary USD Account",
    is_default: true,

    // Optional: which of our bank accounts to use as source when paying this vendor
    // Entity-scoped — each entity's vendor_bank_accounts row can point to a different bank
    // preferred_source_bank_account_id: 15,

    // Verification
    verification_status: "unverified",
    requires_dual_approval: false
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `master_vendor_id` | number | Vendor ID (use `query("vendor")`) |
| `legal_entity_id` | number | Legal entity ID |
| `payment_method` | string | ach, wire_domestic, wire_international, sepa, swift, check, card, crypto, paypal, venmo |
| `account_holder_name` | string | Name on account, max 255 chars |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `account_nickname` | string | Friendly name, max 100 chars |
| `currency_code` | string | ISO currency code (default: "USD") |
| `usage_type` | string | ap_invoice, expense_reimbursement, payroll, other, NULL |
| `bank_name` | string | Bank name, max 255 chars |
| `bank_country` | string | ISO 2-letter country code |
| `account_holder_address` | string | Full address |
| `account_holder_country` | string | ISO 2-letter country code |
| `routing_number` | string | ACH routing (encrypted), max 100 chars |
| `account_number` | string | Account number (encrypted), max 100 chars |
| `account_type` | string | checking, savings, corporate, money_market, other |
| `iban` | string | IBAN (encrypted), max 50 chars |
| `swift_code` | string | SWIFT code, max 20 chars |
| `bic_code` | string | BIC code, max 20 chars |
| `sort_code` | string | UK sort code, max 20 chars |
| `bsb_number` | string | Australia BSB, max 20 chars |
| `intermediary_bank_name` | string | Intermediary bank, max 255 chars |
| `intermediary_swift_code` | string | Intermediary SWIFT, max 20 chars |
| `intermediary_account_number` | string | Intermediary account, max 100 chars |
| `is_default` | boolean | Default for this vendor+entity+method+currency |
| `preferred_source_bank_account_id` | number | Which of our `bank_accounts` to use as source when paying this vendor. Must belong to the same legal entity as this vendor bank account (refused otherwise). NULL = fall back to entity-level `supported_payment_methods` matching. |
| `verification_status` | string | unverified, pending, verified, failed, expired (default: "unverified") |
| `verification_method` | string | How to verify (e.g., "micro_deposits", "bank_letter") |
| `daily_limit` | number | Daily payment limit |
| `monthly_limit` | number | Monthly payment limit |
| `per_transaction_limit` | number | Per-transaction limit |
| `requires_dual_approval` | boolean | Require two approvers (default: false) |
| `connector_id` | string | Banking connector UUID |
| `external_account_id` | string | External system account ID |
| `metadata` | object | Custom fields |

**Validation:**
- `master_vendor_id` must exist
- `legal_entity_id` must exist
- `payment_method` must be valid enum value
- `account_holder_name` is required
- For ACH: `routing_number` and `account_number` required
- For wire_international: `iban` or (`swift_code` and `account_number`) required
- `currency_code` must be valid ISO code
- Only one account can have `is_default=true` per vendor+entity+payment method+currency

**Response:**
```json
{
  "success": true,
  "bank_account_id": 789,
  "account_nickname": "Primary USD Account",
  "verification_status": "unverified"
}
```

### Example: Add ACH Vendor Account

```javascript
submit("vendor_bank_account", "create", {
    master_vendor_id: 456,
    legal_entity_id: 13,
    payment_method: "ach",
    account_holder_name: "Acme Supplies Inc",
    bank_name: "Bank of America",
    routing_number: "026009593",
    account_number: "9988776655",
    account_type: "checking",
    currency_code: "USD",
    account_nickname: "Primary ACH",
    is_default: true
})
```

**Result:** ACH vendor account created

### Example: Add International Wire Account

```javascript
submit("vendor_bank_account", "create", {
    master_vendor_id: 456,
    legal_entity_id: 13,
    payment_method: "wire_international",
    account_holder_name: "European Supplier GmbH",
    bank_name: "Deutsche Bank",
    bank_country: "DE",
    iban: "DE89370400440532013000",
    swift_code: "DEUTDEFF",
    currency_code: "EUR",
    account_nickname: "Wire - EUR",
    requires_dual_approval: true
})
```

**Result:** International wire account created with dual approval requirement

---

### Updating a Vendor Bank Account

Use the `vendor_bank_account.update` workflow.

**Workflow: vendor_bank_account.update**

```javascript
submit("vendor_bank_account", "update", {
    bank_account_id: 789,
    account_nickname: "Primary ACH - Verified",
    is_default: true
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `bank_account_id` | number | Vendor bank account ID |

**Optional Fields:** Any field from create except `master_vendor_id`, `legal_entity_id`

**Validation:** Same as create

**Response:**
```json
{
  "success": true,
  "bank_account_id": 789,
  "updated_fields": ["account_nickname", "is_default"]
}
```

---

### Verifying a Vendor Bank Account

Use the `vendor_bank_account.verify` workflow.

**Workflow: vendor_bank_account.verify**

```javascript
submit("vendor_bank_account", "verify", {
    bank_account_id: 789,
    verification_status: "verified",
    verification_method: "micro_deposits"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `bank_account_id` | number | Vendor bank account ID |
| `verification_status` | string | unverified, pending, verified, failed, expired |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `verification_method` | string | micro_deposits, bank_letter, plaid, voided_check |

**Response:**
```json
{
  "success": true,
  "bank_account_id": 789,
  "verification_status": "verified",
  "verified_at": "2026-01-14T11:00:00Z"
}
```

---

### Deactivating a Vendor Bank Account

Use the `vendor_bank_account.delete` workflow.

**Workflow: vendor_bank_account.delete**

```javascript
submit("vendor_bank_account", "delete", {
    bank_account_id: 789,
    deletion_reason: "Vendor changed banks"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `bank_account_id` | number | Vendor bank account ID |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `deletion_reason` | string | Reason for deactivation |

**Response:**
```json
{
  "success": true,
  "bank_account_id": 789,
  "is_active": false,
  "deleted_at": "2026-01-14T11:30:00Z"
}
```

---

## Employee Bank Accounts

Employee bank accounts are used for payroll direct deposit and expense reimbursements.

### Creating an Employee Bank Account

Use the `employee_bank_account.create` workflow.

**Workflow: employee_bank_account.create**

```javascript
submit("employee_bank_account", "create", {
    // Required fields
    employee_id: 100,
    legal_entity_id: 13,
    usage_type: "payroll",
    account_holder_name: "John Smith",

    // Bank details
    bank_name: "Bank of America",
    bank_country: "US",

    // ACH details (encrypted)
    routing_number: "026009593",
    account_number: "5551234567",
    account_type: "checking",

    // Classification
    payment_method: "ach",
    currency_code: "USD",
    account_nickname: "Personal Checking",

    // Direct deposit allocation
    deposit_allocation_type: "remainder",  // Gets remainder after other accounts

    // Default flag
    is_default: true,

    // Verification
    verification_status: "unverified"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `employee_id` | number | Employee ID (use `query("employee")`) |
| `legal_entity_id` | number | Legal entity ID |
| `usage_type` | string | payroll, benefit, stipend, reimbursement |
| `account_holder_name` | string | Name on account, max 255 chars |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `account_nickname` | string | Friendly name, max 100 chars |
| `payment_method` | string | ach, wire, check, paycard, other (default: "ach") |
| `currency_code` | string | ISO currency code (default: "USD") |
| `bank_name` | string | Bank name, max 255 chars |
| `bank_country` | string | ISO 2-letter country code |
| `account_holder_address` | string | Full address |
| `routing_number` | string | ACH routing (encrypted), max 100 chars |
| `account_number` | string | Account number (encrypted), max 100 chars |
| `account_type` | string | checking, savings, paycard, other |
| `iban` | string | IBAN (encrypted), max 50 chars |
| `swift_code` | string | SWIFT code, max 20 chars |
| `deposit_allocation_type` | string | amount, percentage, remainder, NULL |
| `deposit_amount` | number | Fixed amount (if type=amount) |
| `deposit_percentage` | number | Percentage 0-100 (if type=percentage) |
| `deposit_order` | number | Order for multiple accounts (default: 1) |
| `is_default` | boolean | Default for this employee+entity+usage type+currency |
| `verification_status` | string | unverified, pending, verified, failed (default: "unverified") |
| `verification_method` | string | micro_deposits, plaid, voided_check |
| `connector_id` | string | Banking connector UUID |
| `external_account_id` | string | External system account ID |
| `metadata` | object | Custom fields |

**Validation:**
- `employee_id` must exist
- `legal_entity_id` must exist
- `usage_type` must be valid enum value
- `account_holder_name` is required
- For ACH: `routing_number` and `account_number` required
- `deposit_percentage` must be 0-100 if provided
- Only one account can have `is_default=true` per employee+entity+usage type+currency

**Response:**
```json
{
  "success": true,
  "bank_account_id": 456,
  "account_nickname": "Personal Checking",
  "verification_status": "unverified"
}
```

### Example: Add Payroll Direct Deposit Account

```javascript
submit("employee_bank_account", "create", {
    employee_id: 100,
    legal_entity_id: 13,
    usage_type: "payroll",
    account_holder_name: "John Smith",
    bank_name: "Wells Fargo",
    routing_number: "121000248",
    account_number: "9999888877",
    account_type: "checking",
    deposit_allocation_type: "remainder",
    is_default: true
})
```

**Result:** Primary payroll account created

### Example: Add Split Direct Deposit

```javascript
// Account 1: Savings (fixed amount)
submit("employee_bank_account", "create", {
    employee_id: 100,
    legal_entity_id: 13,
    usage_type: "payroll",
    account_holder_name: "John Smith",
    bank_name: "Chase Bank",
    routing_number: "021000021",
    account_number: "1111222233",
    account_type: "savings",
    deposit_allocation_type: "amount",
    deposit_amount: 500.00,  // $500 to savings
    deposit_order: 1  // First
})

// Account 2: Checking (remainder)
submit("employee_bank_account", "create", {
    employee_id: 100,
    legal_entity_id: 13,
    usage_type: "payroll",
    account_holder_name: "John Smith",
    bank_name: "Wells Fargo",
    routing_number: "121000248",
    account_number: "9999888877",
    account_type: "checking",
    deposit_allocation_type: "remainder",  // Rest goes here
    deposit_order: 2,  // Second
    is_default: true
})
```

**Result:** Split direct deposit - $500 to savings, remainder to checking

---

### Updating an Employee Bank Account

Use the `employee_bank_account.update` workflow.

**Workflow: employee_bank_account.update**

```javascript
submit("employee_bank_account", "update", {
    bank_account_id: 456,
    account_nickname: "Personal Checking - Wells Fargo",
    deposit_allocation_type: "percentage",
    deposit_percentage: 80.00
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `bank_account_id` | number | Employee bank account ID |

**Optional Fields:** Any field from create except `employee_id`, `legal_entity_id`

**Validation:** Same as create

**Response:**
```json
{
  "success": true,
  "bank_account_id": 456,
  "updated_fields": ["account_nickname", "deposit_allocation_type", "deposit_percentage"]
}
```

---

### Verifying an Employee Bank Account

Use the `employee_bank_account.verify` workflow.

**Workflow: employee_bank_account.verify**

```javascript
submit("employee_bank_account", "verify", {
    bank_account_id: 456,
    verification_status: "verified",
    verification_method: "micro_deposits"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `bank_account_id` | number | Employee bank account ID |
| `verification_status` | string | unverified, pending, verified, failed |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `verification_method` | string | micro_deposits, plaid, voided_check |

**Response:**
```json
{
  "success": true,
  "bank_account_id": 456,
  "verification_status": "verified",
  "verified_at": "2026-01-14T12:00:00Z"
}
```

---

### Deactivating an Employee Bank Account

Use the `employee_bank_account.delete` workflow.

**Workflow: employee_bank_account.delete**

```javascript
submit("employee_bank_account", "delete", {
    bank_account_id: 456,
    deletion_reason: "Employee closed account"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `bank_account_id` | number | Employee bank account ID |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `deletion_reason` | string | Reason for deactivation |

**Response:**
```json
{
  "success": true,
  "bank_account_id": 456,
  "is_active": false,
  "deleted_at": "2026-01-14T12:30:00Z"
}
```

---

## ~~Change Request Workflows~~ (DEPRECATED 2026-02)

> **DEPRECATED:** The `bank_account_change_request` table and workflows have been removed. Sensitive bank account changes now go through the standard workflow approval system. Use `submit("bank_account", "update", {...})` which automatically routes through approval lanes based on risk.

~~Change request workflows handle sensitive bank account changes that require approval.~~

### Creating a Change Request

Use the `bank_account_change_request.create` workflow.

**Workflow: bank_account_change_request.create**

```javascript
submit("bank_account_change_request", "create", {
    legal_entity_id: 13,
    request_type: "add",  // or "update" or "delete"
    entity_type: "vendor",  // or "employee" or "bank_account"
    master_vendor_id: 456,  // If entity_type=vendor
    requested_changes: {
      payment_method: "wire_international",
      account_holder_name: "International Supplier SA",
      iban: "GB82WEST12345698765432",
      swift_code: "HSBCGB2L",
      currency_code: "GBP"
    },
    verification_method: "bank_letter",
    requires_dual_approval: true,
    request_reason: "New supplier in UK requires wire transfers"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `legal_entity_id` | number | Legal entity ID |
| `request_type` | string | add, update, delete |
| `entity_type` | string | vendor, employee, bank_account |
| `requested_changes` | object | Account details to add/update |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `master_vendor_id` | number | Vendor ID (if entity_type=vendor) |
| `employee_id` | number | Employee ID (if entity_type=employee) |
| `bank_account_id` | number | Account ID (if entity_type=bank_account) |
| `verification_method` | string | Verification method |
| `requires_dual_approval` | boolean | Require two approvers |
| `request_reason` | string | Reason for request (audit trail) |

**Validation:**
- `legal_entity_id` must exist
- `request_type`, `entity_type` must be valid
- If entity_type=vendor: `master_vendor_id` required
- If entity_type=employee: `employee_id` required
- `requested_changes` must be valid JSON object

**Response:**
```json
{
  "success": true,
  "request_id": 789,
  "status": "pending_approval",
  "assigned_to": "AP Manager",
  "created_at": "2026-01-14T13:00:00Z"
}
```

---

### Approving a Change Request

Use the `bank_account_change_request.approve` workflow.

**Workflow: bank_account_change_request.approve**

```javascript
submit("bank_account_change_request", "approve", {
    request_id: 789,
    approval_note: "Verified with vendor via email - bank letter attached"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `request_id` | number | Change request ID |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `approval_note` | string | Approval comment (audit trail) |

**Validation:**
- `request_id` must exist
- Request status must be "pending_approval"
- Approver cannot be the requester (dual control)

**Response:**
```json
{
  "success": true,
  "request_id": 789,
  "status": "approved",
  "approved_by": "Jane Manager",
  "approved_at": "2026-01-14T14:00:00Z"
}
```

---

### Rejecting a Change Request

Use the `bank_account_change_request.reject` workflow.

**Workflow: bank_account_change_request.reject**

```javascript
submit("bank_account_change_request", "reject", {
    request_id: 789,
    rejection_reason: "IBAN checksum appears invalid - please verify with vendor"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `request_id` | number | Change request ID |
| `rejection_reason` | string | Reason for rejection (required, min 10 chars) |

**Validation:**
- `request_id` must exist
- Request status must be "pending_approval"
- `rejection_reason` is required, min 10 chars

**Response:**
```json
{
  "success": true,
  "request_id": 789,
  "status": "rejected",
  "rejected_by": "Jane Manager",
  "rejected_at": "2026-01-14T14:30:00Z",
  "rejection_reason": "IBAN checksum appears invalid..."
}
```

---

### Canceling a Change Request

Use the `bank_account_change_request.cancel` workflow.

**Workflow: bank_account_change_request.cancel**

```javascript
submit("bank_account_change_request", "cancel", {
    request_id: 789,
    cancellation_reason: "Vendor provided updated account details"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `request_id` | number | Change request ID |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `cancellation_reason` | string | Reason for cancellation |

**Validation:**
- `request_id` must exist
- Request status must be "pending_approval" or "draft"
- Can only be canceled by requester or admin

**Response:**
```json
{
  "success": true,
  "request_id": 789,
  "status": "cancelled"
}
```

---

### Applying Approved Changes

Use the `bank_account_change_request.apply` workflow to execute approved changes.

**Workflow: bank_account_change_request.apply**

```javascript
submit("bank_account_change_request", "apply", {
    request_id: 789
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `request_id` | number | Change request ID |

**Validation:**
- `request_id` must exist
- Request status must be "approved"
- Request must not already be applied

**Response:**
```json
{
  "success": true,
  "request_id": 789,
  "status": "applied",
  "bank_account_id": 890,
  "applied_at": "2026-01-14T15:00:00Z"
}
```

---

## ~~Verification Workflows~~ (DEPRECATED 2026-02)

> **DEPRECATED:** The `bank_account_verification_events` table and workflows have been removed. Verification is now handled directly via `submit("bank_account", "verify", {...})`, `submit("vendor_bank_account", "verify", {...})`, or `submit("employee_bank_account", "verify", {...})`.

~~Verification workflows handle account verification processes (micro-deposits, Plaid, etc.).~~

### Creating a Verification Event

Use the `bank_account_verification.create` workflow.

**Workflow: bank_account_verification.create**

```javascript
submit("bank_account_verification", "create", {
    bank_account_id: 789,
    bank_account_type: "vendor",  // or "employee" or "bank_account"
    verification_method: "micro_deposits",
    micro_deposit_amounts: [0.17, 0.32]  // If method=micro_deposits
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `bank_account_id` | number | Bank account ID |
| `bank_account_type` | string | vendor, employee, bank_account |
| `verification_method` | string | micro_deposits, plaid, bank_letter, voided_check |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `micro_deposit_amounts` | array | Two amounts (if method=micro_deposits) |
| `plaid_link_token` | string | Plaid link token (if method=plaid) |
| `document_url` | string | Document URL (if method=bank_letter or voided_check) |

**Validation:**
- `bank_account_id` must exist
- `bank_account_type` must match actual account type
- `verification_method` must be valid
- If method=micro_deposits: `micro_deposit_amounts` must be array of 2 numbers

**Response:**
```json
{
  "success": true,
  "verification_id": 123,
  "bank_account_id": 789,
  "verification_method": "micro_deposits",
  "status": "pending",
  "expires_at": "2026-01-17T15:00:00Z"
}
```

---

### Updating Verification Progress

Use the `bank_account_verification.update` workflow.

**Workflow: bank_account_verification.update**

```javascript
submit("bank_account_verification", "update", {
    verification_id: 123,
    status: "in_progress",
    notes: "Micro-deposits sent, waiting for confirmation"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `verification_id` | number | Verification event ID |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | pending, in_progress, completed, failed |
| `notes` | string | Progress notes |

**Response:**
```json
{
  "success": true,
  "verification_id": 123,
  "status": "in_progress"
}
```

---

### Completing Verification

Use the `bank_account_verification.complete` workflow.

**Workflow: bank_account_verification.complete**

```javascript
submit("bank_account_verification", "complete", {
    verification_id: 123,
    verification_status: "verified",  // or "failed"
    confirmed_amounts: [0.17, 0.32]  // If method=micro_deposits
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `verification_id` | number | Verification event ID |
| `verification_status` | string | verified, failed |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `confirmed_amounts` | array | Confirmed amounts (if method=micro_deposits) |
| `failure_reason` | string | Reason for failure (if status=failed) |

**Validation:**
- `verification_id` must exist
- If method=micro_deposits and status=verified: `confirmed_amounts` must match sent amounts
- Max 3 attempts allowed

**Response:**
```json
{
  "success": true,
  "verification_id": 123,
  "bank_account_id": 789,
  "verification_status": "verified",
  "completed_at": "2026-01-14T16:00:00Z"
}
```

---

## ~~Integration Workflows~~ (DEPRECATED 2026-02)

> **DEPRECATED:** The `bank_account_integrations` table and workflows have been removed. Banking integrations are now handled via the connector_registry system. Use `bank_accounts.metadata.connector_id` to link accounts to connectors. See Connector Framework Guide.

~~Integration workflows manage connections to banking providers (Revolut, Stripe).~~

### Creating a Bank Integration

Use the `bank_account_integration.create` workflow.

**Workflow: bank_account_integration.create**

```javascript
submit("bank_account_integration", "create", {
    bank_account_id: 123,
    provider: "revolut",  // or "stripe"
    provider_account_id: "12345678",
    encrypted_credentials: {
      api_key: "sk_live_...",
      profile_id: "12345678"
    },
    sync_frequency: "daily",
    auto_sync_enabled: true
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `bank_account_id` | number | Company bank account ID |
| `provider` | string | revolut, stripe |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `provider_account_id` | string | External account ID |
| `encrypted_credentials` | object | API credentials (encrypted) |
| `sync_frequency` | string | hourly, daily, weekly |
| `auto_sync_enabled` | boolean | Enable auto-sync |
| `metadata` | object | Provider-specific settings |

**Validation:**
- `bank_account_id` must exist
- `provider` must be valid
- Cannot have multiple active integrations for same account

**Response:**
```json
{
  "success": true,
  "integration_id": "uuid-here",
  "bank_account_id": 123,
  "provider": "revolut",
  "status": "active"
}
```

---

### Updating Integration Settings

Use the `bank_account_integration.update` workflow.

**Workflow: bank_account_integration.update**

```javascript
submit("bank_account_integration", "update", {
    integration_id: "uuid-here",
    sync_frequency: "hourly",
    auto_sync_enabled: false
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `integration_id` | string | Integration UUID |

**Optional Fields:** Any field from create except `bank_account_id`, `provider`

**Response:**
```json
{
  "success": true,
  "integration_id": "uuid-here",
  "updated_fields": ["sync_frequency", "auto_sync_enabled"]
}
```

---

### Removing Integration

Use the `bank_account_integration.delete` workflow.

**Workflow: bank_account_integration.delete**

```javascript
submit("bank_account_integration", "delete", {
    integration_id: "uuid-here",
    deletion_reason: "Switching to different banking provider"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `integration_id` | string | Integration UUID |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `deletion_reason` | string | Reason for removal |

**Response:**
```json
{
  "success": true,
  "integration_id": "uuid-here",
  "status": "deleted"
}
```

---

### Triggering Integration Sync

Use the `bank_account_integration.sync` workflow.

**Workflow: bank_account_integration.sync**

```javascript
submit("bank_account_integration", "sync", {
    integration_id: "uuid-here",
    sync_type: "transactions",  // or "balance" or "both"
    start_date: "2026-01-01",
    end_date: "2026-01-14"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `integration_id` | string | Integration UUID |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `sync_type` | string | transactions, balance, both (default: "both") |
| `start_date` | string | Start date (YYYY-MM-DD) |
| `end_date` | string | End date (YYYY-MM-DD) |
| `force_refresh` | boolean | Force refresh cached data |

**Validation:**
- `integration_id` must exist and be active
- Date range must be valid if provided

**Response:**
```json
{
  "success": true,
  "integration_id": "uuid-here",
  "sync_id": "sync-uuid",
  "sync_status": "in_progress",
  "transactions_fetched": 42,
  "balance_updated": true
}
```

---

## Querying Bank Accounts

### Get Single Bank Account

**Company Bank Account:**
```javascript
get_entity("bank_account", id=123)
```

**Vendor Bank Account:**
```javascript
get_entity("vendor_bank_account", id=789)
```

**Employee Bank Account:**
```javascript
get_entity("employee_bank_account", id=456)
```

**Response Structure (company):**
```json
{
  "id": 123,
  "legal_entity_id": 13,
  "bank_account_code": "CASH-USD-001",
  "account_name": "Main Operating Account",
  "bank_name": "Wells Fargo",
  "currency": "USD",
  "account_type": "checking",
  "account_number_masked": "****7890",
  "routing_number_masked": "****0248",
  "gl_account_number": "1010",
  "is_operating": true,
  "is_default_payments": true,
  "verification_status": "verified",
  "is_active": true
}
```

**Security:** Sensitive fields (account numbers, routing numbers) are masked by default. Full values require elevated permissions.

---

### List Bank Accounts

**List Company Bank Accounts:**
```javascript
query("bank_account", filters={
    legal_entity_id: 13,
    is_active: true,
    currency: "USD"
  },
  sort_by="account_name",
  sort_order="asc")
```

**List Vendor Bank Accounts:**
```javascript
query("vendor_bank_account", filters={
    master_vendor_id: 456,
    legal_entity_id: 13,
    verification_status: "verified",
    is_active: true
  })
```

**List Employee Bank Accounts:**
```javascript
query("employee_bank_account", filters={
    employee_id: 100,
    usage_type: "payroll",
    verification_status: "verified"
})
```

**Filterable Fields:**

**Company Bank Accounts:**
- `legal_entity_id` (number)
- `currency` (string)
- `account_type` (string)
- `usage_type` (string)
- `verification_status` (string)
- `is_active` (boolean)
- `is_operating` (boolean)
- `is_default_receipts` (boolean)
- `is_default_payments` (boolean)

**Vendor Bank Accounts:**
- `master_vendor_id` (number)
- `legal_entity_id` (number)
- `payment_method` (string)
- `currency_code` (string)
- `verification_status` (string)
- `is_active` (boolean)
- `is_default` (boolean)

**Employee Bank Accounts:**
- `employee_id` (number)
- `legal_entity_id` (number)
- `usage_type` (string)
- `payment_method` (string)
- `currency_code` (string)
- `verification_status` (string)
- `is_active` (boolean)
- `is_default` (boolean)

---

### Search Bank Accounts

**Search Company Bank Accounts:**
```javascript
query("bank_account", query="operating", filters={"legal_entity_id": 13, "is_active": true})
```

**Search Vendor Bank Accounts:**
```javascript
query("vendor_bank_account", query="chase", filters={"legal_entity_id": 13, "verification_status": "verified"})
// Searches bank_name, account_nickname
```

**Searchable Fields:**
- Company: `bank_account_code`, `account_name`, `bank_name`
- Vendor: `account_nickname`, `bank_name`, `account_holder_name`
- Employee: `account_nickname`, `bank_name`, `account_holder_name`

---

## Common Scenarios

### Scenario 1: Set Up Primary Operating Account

**Goal:** Create and verify company's main operating account for payments.

```javascript
// Step 1: Create account
submit("bank_account", "create", {
    legal_entity_id: 13,
    bank_account_code: "CASH-USD-MAIN",
    account_name: "Wells Fargo Operating Account",
    gl_account_number: "1010",
    bank_name: "Wells Fargo",
    routing_number: "121000248",
    account_number: "1234567890",
    currency: "USD",
    account_type: "checking",
    usage_type: "operating",
    is_operating: true,
    is_default_payments: true,
    daily_limit: 100000.00
})

// Step 2: Verify account
submit("bank_account", "verify", {
    bank_account_id: 123,
    verification_status: "verified",
    verification_method: "bank_letter"
})
```

**Result:** Primary operating account set up and verified

---

### Scenario 2: Add Vendor for ACH Payments

**Goal:** Set up vendor with verified ACH account for payments.

```javascript
// Step 1: Create vendor bank account
submit("vendor_bank_account", "create", {
    master_vendor_id: 456,
    legal_entity_id: 13,
    payment_method: "ach",
    account_holder_name: "Acme Supplies Inc",
    bank_name: "Bank of America",
    routing_number: "026009593",
    account_number: "9988776655",
    account_type: "checking",
    currency_code: "USD",
    is_default: true
})

// Step 2: Verify account (replaces deprecated bank_account_verification workflows)
submit("vendor_bank_account", "verify", {
    bank_account_id: 789,
    verification_status: "verified",
    verification_method: "micro_deposits"
})
```

**Result:** Vendor account set up and verified for ACH payments

---

### Scenario 3: Set Up Employee Direct Deposit

**Goal:** Employee submits direct deposit for payroll.

```javascript
// Step 1: Employee creates account
submit("employee_bank_account", "create", {
    employee_id: 100,
    legal_entity_id: 13,
    usage_type: "payroll",
    account_holder_name: "John Smith",
    bank_name: "Chase Bank",
    routing_number: "021000021",
    account_number: "5551234567",
    account_type: "checking",
    deposit_allocation_type: "remainder",
    is_default: true
})

// Step 2: Verify account (replaces deprecated bank_account_verification workflows)
submit("employee_bank_account", "verify", {
    bank_account_id: 456,
    verification_status: "verified",
    verification_method: "plaid"
})
```

**Result:** Employee direct deposit set up and instantly verified via Plaid

---

### Scenario 4: Change Vendor Bank Account with Approval

**Goal:** Vendor changes bank account, requiring AP manager approval.

> **Note:** The deprecated `bank_account_change_request` workflow has been removed. Sensitive changes now go through the standard workflow approval system, which automatically routes through risk-based approval lanes.

```javascript
// Step 1: Update vendor bank account (automatically routes through approval if high-risk)
submit("vendor_bank_account", "update", {
    bank_account_id: 789,
    routing_number: "111000025",
    account_number: "7777888899",
    bank_name: "Wells Fargo",
    notes: "Vendor switched banks effective 2026-01-15"
})

// Step 2: Verify updated account
submit("vendor_bank_account", "verify", {
    bank_account_id: 789,
    verification_status: "verified",
    verification_method: "bank_letter"
})
```

**Result:** Vendor bank account updated through standard approval system, then verified

---

### Scenario 5: Connect Bank Account to Revolut Integration

**Goal:** Link company bank account to Revolut Business for automatic statement downloads.

> **Note:** The deprecated `bank_account_integration` workflow has been removed. Banking integrations are now managed via the connector_registry system. Use the Admin Dashboard to securely configure credentials. See Connector Framework Guide.

```javascript
// Step 1: Update bank account metadata to link to connector
submit("bank_account", "update", {
    bank_account_id: 123,
    metadata: {
      connector_id: "revolut-connector-uuid",
      external_account_id: "revolut-account-uuid",  // the Revolut account (one per currency)
      sync_frequency: "daily",
      auto_sync_enabled: true
    }
})

// Step 2: Configure credentials securely via Admin Dashboard
// NEVER pass API keys or secrets through Claude chat
// Use the Admin Dashboard: Connectors → Add connection → Revolut Business
// (wizard: certificate + OAuth consent + account linking — the "Link accounts" step writes this metadata for you)
```

**Result:** Bank account linked to Revolut via connector registry. Credentials managed securely in Admin Dashboard.

---

### Scenario 6: Employee Split Direct Deposit

**Goal:** Employee wants $500 to savings, remainder to checking.

```javascript
// Account 1: Savings - fixed amount
submit("employee_bank_account", "create", {
    employee_id: 100,
    legal_entity_id: 13,
    usage_type: "payroll",
    account_holder_name: "Jane Doe",
    bank_name: "Chase Bank - Savings",
    routing_number: "021000021",
    account_number: "1111222233",
    account_type: "savings",
    deposit_allocation_type: "amount",
    deposit_amount: 500.00,
    deposit_order: 1
})

// Account 2: Checking - remainder
submit("employee_bank_account", "create", {
    employee_id: 100,
    legal_entity_id: 13,
    usage_type: "payroll",
    account_holder_name: "Jane Doe",
    bank_name: "Chase Bank - Checking",
    routing_number: "021000021",
    account_number: "4444555566",
    account_type: "checking",
    deposit_allocation_type: "remainder",
    deposit_order: 2,
    is_default: true
})
```

**Result:** Payroll split: $500 → savings, remainder → checking

---

## Getting Reference Data

Use dynamic queries to retrieve related data:

**Legal Entities:**
```javascript
query("legal_entity")
```
Use for `legal_entity_id` field

**Vendors:**
```javascript
query("vendor")
```
Use for `master_vendor_id` field

**Employees:**
```javascript
query("employee")
```
Use for `employee_id` field

**GL Accounts:**
```javascript
query("account")
```
Use for `gl_account_number` field

---

## Security & Encryption

### Encrypted Fields

**All bank account tables encrypt:**
- Account numbers
- Routing numbers
- IBAN
- SWIFT/BIC codes

**Encryption:**
- Algorithm: AES-256-GCM
- A single global master key (env `ENCRYPTION_MASTER_KEY`), not per-organization derived keys — org-derived keys are a deferred roadmap item, not current behavior
- Decryption logged with user, timestamp, reason

**Masking:**
- Masked display: `****7890` (last 4 digits)
- Full view requires elevated permissions
- All access logged for audit

### Permission Levels

| Role | Company Accounts | Vendor Accounts | Employee Accounts |
|------|-----------------|----------------|-------------------|
| Treasury Admin | Full access, decrypt | View masked | View masked |
| AP Manager | View masked | Full access, approve changes | View masked |
| Payroll Manager | View masked | View masked | Full access, approve changes |
| AP Clerk | View masked | Create/update, view masked | No access |
| Payroll Clerk | View masked | No access | View masked |
| Employee | No access | No access | View own, masked |

---

## Best Practices

### Company Bank Accounts

1. **Create Separate Accounts by Purpose**
   - Operating account for general payments
   - Payroll account for payroll only
   - Tax account for tax payments
   - Separate accounts reduce risk

2. **Set Transaction Limits**
   - Configure `daily_limit` and `monthly_limit`
   - Prevents large unauthorized transactions
   - Review limits quarterly

3. **Verify All Accounts**
   - Mark accounts as `verified` after validation
   - Use bank letters or test transactions
   - Update verification status promptly

4. **Link to GL Accounts (Critical)**
   - Every bank account MUST map to its own unique, dedicated GL account
   - ALWAYS create a new GL account for each new bank — never reuse generic "Cash" or "Cash and Cash Equivalents" accounts
   - If the bank has corporate cards, also create ONE dedicated card GL account per bank (not per card)
   - Do NOT share a GL account between multiple bank accounts
   - Bank transaction processor uses this mapping for bank-aware GL resolution
   - See [GL Account Requirement](#gl-account-requirement) for naming conventions and numbering
   - Review mappings during month-end

### Vendor Bank Accounts

1. **Require Verification**
   - Use micro-deposits or bank letters
   - Never pay to unverified accounts
   - Set verification deadlines (e.g., 5 days)

2. **Use Change Request Workflow**
   - Require approval for account changes
   - Prevents fraud (CEO fraud, BEC attacks)
   - Maintain dual control (maker/checker)

3. **Set Payment Limits**
   - Configure per-transaction limits for high-risk vendors
   - Require dual approval for large vendors
   - Review limits during onboarding

4. **Keep Accounts Current**
   - Deactivate accounts when vendor changes banks
   - Regular vendor account audits (annually)
   - Remove inactive vendors

### Employee Bank Accounts

1. **Verify Before First Payroll**
   - Use Plaid for instant verification
   - Or micro-deposits 5+ days before payday
   - Block unverified accounts from payroll

2. **Prenote Before Live Payments**
   - Send ACH prenote 3 days before first payment
   - Wait for prenote to clear
   - Reduces NSF and return risk

3. **Monitor Split Deposits**
   - Validate allocation percentages sum to 100%
   - Test allocations before live payroll
   - Document employee consent

4. **Handle Changes Promptly**
   - Process account changes before payroll cutoff
   - Communicate change deadlines to employees
   - Update accounts within 1 pay period

### Security

1. **Enforce Dual Control**
   - Require approval for sensitive changes
   - Separate duties (requester ≠ approver)
   - Log all approvals with justification

2. **Limit Decryption Access**
   - Only decrypt when necessary
   - Log all decryption events
   - Require justification for each decrypt
   - Review decryption logs monthly

3. **Rotate Credentials**
   - Rotate integration API keys quarterly
   - Update credentials after staff changes
   - Use environment variables, not hardcoded

4. **Monitor for Fraud**
   - Alert on multiple account changes
   - Alert on unusual account details (offshore banks)
   - Alert on changes right before payday
   - Review alerts weekly

---

## Common Pitfalls

### Don't Create Without Verification Plan

❌ **Don't** create bank accounts without planning how to verify them
✅ **Do** determine verification method (micro-deposits, Plaid, bank letter) before creating account

### Don't Skip Approval Workflows

❌ **Don't** bypass change request workflows for "urgent" changes
✅ **Do** use emergency approval process with documentation

### Don't Store Credentials in Plain Text

❌ **Don't** store API keys, account numbers in plain text or metadata
✅ **Do** use encrypted fields, environment variables, KMS

### Don't Allow Same-Person Approval

❌ **Don't** let requester approve their own change requests
✅ **Do** enforce maker/checker separation (different users)

### Don't Ignore Verification Failures

❌ **Don't** proceed with payments to unverified accounts
✅ **Do** investigate failures, retry verification, or use alternative method

### Don't Overlook Limits

❌ **Don't** create accounts without transaction limits
✅ **Do** set appropriate limits based on account purpose and risk

---

## Workflow Details

All bank account workflows are registered in the system:

**Object Types:** `bank_account`, `vendor_bank_account`, `employee_bank_account`

**Total Workflows:** 12 across 3 object types

View workflow definitions in the admin dashboard at `https://app.arfiti.com/workflows/definitions`.

---

## Quick Reference

### Object Type Summary

| Object Type | Purpose | Count |
|-------------|---------|-------|
| `bank_account` | Company bank accounts | 4 workflows |
| `vendor_bank_account` | Vendor payment accounts | 4 workflows |
| `employee_bank_account` | Employee payroll/reimbursement accounts | 4 workflows |

### Common Workflows

| Use Case | Workflow |
|----------|----------|
| Create company account | `submit("bank_account", "create", {...})` |
| Create vendor account | `submit("vendor_bank_account", "create", {...})` |
| Create employee account | `submit("employee_bank_account", "create", {...})` |
| Verify account | `submit("[type]", "verify", {...})` |

---

## Key Takeaways

- **Three Account Types** - Company, vendor, employee (each with separate workflows)
- **12 Workflows** - 4 operations per account type (create, update, delete, verify)
- **Security First** - Field-level encryption, masked display, audit logging
- **Workflow Approvals** - Updates route through approval lanes based on risk
- **Connector Integration** - Link to connectors via `metadata.connector_id`
- **Transaction Limits** - Daily, monthly, per-transaction limits
- **Soft Deletes** - Never hard-delete, preserve historical data

**Bank account management provides secure, auditable, and compliant payment infrastructure.**

---

## Related Resources

- [Bank Statements Management](bank-statements-management.md) - Statement import and reconciliation
- [Corporate Cards Management](corporate-cards-management.md) - Card programs and transactions
- Connector Framework Guide - Banking integrations

---

*Last Updated: 2026-03-14*


## Exchange currency between own accounts (Revolut)

Only for bank accounts linked to a connector that supports FX (today: Revolut
Business). You can quote; you cannot execute. An exchange moves money, so
`submit("fx_exchange", "execute", …)`, and approving or editing
(`edit_payload`) a pending exchange, are refused through the connector with
`operation_not_available_via_mcp`. Give the
user the quote and tell them to exchange the currency at their bank. Rejecting
a pending exchange stays available.

```
# Quote (read only)
get_connectors(action="fx_quote", connector_id="<revolut connector>",
                  from_bank_account_id=60, to_bank_account_id=63, sell_amount="5000")
# → quote.rate, quote.fee, quote.to.amount … and a note that nothing moved
```

When the exchange happens at the bank, its two statement legs arrive on the
statements and post as an internal transfer.

If an account is not eligible the quote says so and lists `eligible_accounts`
— tell the user which accounts qualify instead of retrying.


### Bank-configuration reference reads (QA branch, not deployed)

The installed `create_bank_account` and `create_bank_account_for_currency`
producer metadata must name a stored `source_bank_account_id` in the request or
execution entity. Any returned `bank_account_id` must also resolve in that entity;
it may differ from the source account. A supplied `legal_entity_id` must match.
No additional Bank domain grant is introduced; existing outer read permissions
and entity scope still apply.

If `pending_statement` is supplied, it must be an object whose
`primary_statement_id` resolves to a statement in that entity on the same source
account. Missing, malformed, foreign or mismatched references withhold the
request/thread or virtual execution metadata before rows, totals and pages.
Responses inherit the originating action, including the source account when a
pending statement omits its own source reference. Empty responses and absent or
null optional pending statements remain supported. Unrelated actions do not gain
these field meanings.

This verifies stored reference authority, not the accuracy of copied names,
IBANs, balances or free-text line descriptions, nor account creation or queued
statement import completion. Use authorized source/configuration recovery for
broken bindings; do not edit history to force a read or retry. Other configuration
actions and hosted identity acceptance remain open.

## Bank-number reader compatibility

Bank account/routing-number masked readers accept legacy plaintext and ciphertext. An unreadable value is unknown (no mask), not a usable placeholder. A mask does not authorize payment or prove details are correct. Existing IBAN fields are separate. Reader compatibility does not imply importer writers have been migrated or stored data re-encrypted.

### Excluded source posting and adoption

The shared movement posting boundary checks the locked source before registering or adopting an effect. Bank sources marked `recon_status=excluded` and card sources marked `posting_status=excluded` return `source_excluded`. Review the exclusion before requesting new posting/adoption. The locally verified `revoke_exclusion` workflow described below requires its own configured authority and installed770 storage; until deployed, keep the source excluded and follow reviewed operational repair. Caller metadata cannot override this check. Existing financial journals remain unchanged; the refusal does not mean historical cash effects are absent. Ordinary replay of a non-excluded source continues to adopt its recorded effect. A previously recorded gateway response remains historical evidence, not permission for a new posting.

Local actual BankEntry controls cover ordinary posting, excluded posting, preserved existing effects and an exclusion winning while posting waits. Broader sibling-exclusion and writer compatibility acceptance remains tracked in the canonical bank/card plan.

An excluded authenticated representation also blocks new posting/adoption by another representation of the **same booked leg** (`sibling_excluded`). This remains true when authenticated identity is attached after the exclusion. The relationship comes from saved connector evidence, not caller metadata or matching amount/date. Distinct opposite transfer legs are not treated as the same leg. Concurrent sibling changes return a retryable contention error and roll back the attempted posting; retry only after that transaction has ended. Existing journals and exclusion remain unchanged.

Close-policy configuration does not authorize posting an excluded source or its authenticated same-leg sibling. Local checks populated the existing configuration store with `period_close.policy` → `card_lines_confirmed.excluded_rows=revalidate` and verified both posting refusals remain unchanged. This does not add a close-policy activation feature or change close treatment.

For an unchanged source with a previously committed AP payment, exact posting replay adopts the existing payment before checking depleted invoice capacity. It must not apply the invoice twice or create another payment. A different source cannot borrow that replay result: normal invoice state/capacity checks still run before allocating a new posting. Local acceptance includes a lost response after actual payment commit, unchanged invoice paid/due counters and one durable application; it does not authorize retry with a different economic instruction.

### Explicit existing journal anchors

A source's explicit journal pointers and exact source-linked journal take precedence over date/reference hints. Posting checks that they agree and that the journal represents the source's signed bank-account amount and currency using receipt-first cash evidence. An unposted draft returns `posting_in_flight`; conflicting, missing, wrong-scope, reversed or mismatched financial evidence returns `anchored_journal_mismatch`. Review the existing evidence rather than creating a replacement journal. A fitting posted anchor may still be adopted when descriptive date/reference hints differ; this does not certify provider ownership from those hints. Busy financial evidence refuses the attempted transaction without waiting in a conflicting lock order.

### Typed exclusion evidence (locally verified; undeployed)

The exclusion input accepts `exclusion_basis.kind=not_booked` for a ledger-no-live-owner assertion, or `duplicate_source` with an exact survivor source kind/ID. These inputs require the existing configured exclusion workflow and current authority; they are not a new approval policy. Saved provider metadata or reason text cannot substitute for authenticated identity. A later contradictory ledger owner is retained as `excluded_evidence_stale` review evidence and blocks settlement facts; the existing journal and exclusion are preserved. Do not automatically repost or clear the hold. Local workflow atomicity, replay, contradiction readers and scoped storage checks are verified; deployment remains pending in the canonical bank/card plan. Historical reversed ownership reservations are retained but are not counted as live ledger owners. Legacy free-text exclusions remain unclassified. Automatic card application rechecks the locked source and refuses `source_excluded` before changing the source or recording a reconciliation item.

### Journal ownership when matching a source

Supported manual and automatic matching validates a live, unreversed, report-eligible journal and its exact signed cash-account quantity/currency under source and journal admission. Distinct movements cannot reuse the same cash journal. Exact authenticated representations may share it; opposite transfer legs require the existing exact group and cash-leg evidence. A `void` journal remains unavailable even when it retains `posted_at`. Existing GL and historical links are preserved on refusal.

Legacy journals are supported only where document or functional currency supplies the exact known cash basis and the current mapped account is unique. Ambiguous historical links require review, not automatic repair. These controls govern the updated supported writers; raw SQL protection and old-worker rollout requirements remain separately tracked in the canonical implementation plan.

### Explicit exclusion revocation (locally verified; undeployed)

Submit `revoke_exclusion` on `bank_statement_line` or `card_statement_line` only through its configured workflow. Supply `legal_entity_id`, `source_id`, `expected_exclusion_hash`, the current `exclusion_decision_id` for a typed exclusion, a stable `request_key`, and a review `reason`. Scoped source readback supplies the fingerprint and typed decision. A legacy unclassified exclusion uses the fingerprint with no decision UUID. Missing configuration does not inherit exclude approval. Original key/entity scope and current permission are checked again at execution.

The operation atomically restores bank `unmatched` or card `pending_recon`, updates parent controls, and retains an immutable before/after receipt. Financial pointers, journals and review holds are preserved. A card with a retained pointer remains marked posted but requires reconciliation review; pointer presence does not certify current fit. Historical exclusion metadata remains history, while current status/readback determines whether the source is excluded. Complete any outstanding provenance review through its separate supported operation; revocation does not clear it automatically.

Exact retry returns the original revocation receipt plus separately current exclusion state. Changed source or decision requires a fresh reviewed proposal. Raw clearing or relinking of an excluded source is refused by the installed770 guard. Deployment and old-worker drain remain required operational steps; these local tests do not activate production.


### AR729 local ownership backstop (undeployed)

Draft771 adds database-maintained reservations for every journal assigned to a booked movement. Clearing a live source link does not free its historical journal for another movement. Exact original reattachment remains supported; replacing a retained target requires its verified reciprocal reversal. Actual settlement recovery and reconfirmation preserve every original through repeated cycles. Unsupported destructive deletion or unclassified legacy history returns an integrity refusal; no metadata or GUC authorizes bypass.

Protected mutations use READ COMMITTED and nonwaiting source/journal admission. Retry the whole owned operation after `bank_claim_busy`; do not retry a partial financial write. Raw GL/dimension changes and competing header anchors serialize with first claims. Shared receipt-first cash fit preserves authenticated same-leg and recorded opposite transfer sharing. Historical unrelated multilinks remain untouched by migration and descriptive edits, but do not authorize new ambiguous links. Pre-existing NULL-target movements remain unclassified until a reviewed migration census establishes their history.

Coverage evidence stores bank-account IDs, not GL account IDs. Account-configuration
review keeps the actual bank `gl_account_number` mapping in its reference census;
coverage identity columns do not themselves authorize or block a policy change.
Unknown account-bearing columns still require inventory review.


### Reviewed AP/AR payment effect receipts (local candidate)

Reviewed AP/AR payment creation checks the exact `transaction.post` authority
and records its causal effect inside the same database transaction. Receipt failure
rolls back the effect. AR approval intent is captured before execution normalization,
so normalization cannot silently change the approved intent. Enrolled adoption
continues to be refused by the existing fresh-effect contract; ordinary non-enrolled
adoption is unchanged. This grants no new authority and is not deployed.


### Transfer document amounts and cash valuation

For the direct `bank.transfer` executor, the transfer document uses the source
bank account currency. Both cash lines (and cross-entity intercompany lines)
use that document unit for their debit/credit amounts. The destination cash
valuation is calculated from the destination account currency and received
amount; its functional and reporting values are not calculated by treating
the received native amount as source currency. The recorded exchange rate on
each GL line describes its document-to-functional conversion. This does not
choose an FX-gain policy or bypass the existing journal balance checks.



### Valuation clone scope correction (local candidate)

Additive migration772 repairs the organization-scope literal in cloned cash
valuation validators. It preserves stored financial evidence and quotes and
leaves historical migration763 unchanged. This correction is not deployed.


### Claimed journal reconciliation projection (local candidate)

Additive migration773 allows the existing `recon_status` projection to change
on a claimed journal. Financial amounts, currency, source identity, GL rows and
dimensions remain protected, including combined status-plus-financial mutations.
Deferred owner and cash-fit checks remain active. Readiness recognizes only the
exact reviewed old and corrected function bodies during upgrade. This correction
is not deployed; historical771 remains unchanged.

### Connector observation identity references

Account-configuration review also classifies the exact connector source observation
`bank_account_id` and provider `external_account_id` as bank/provider identities,
not GL references. Named GL account numbers and master-account foreign keys remain
in the census; unclassified account-bearing columns still refuse preparation.

### Retained cash mapping reference evidence

Account-configuration review counts cash-leg `account_mapping` evidence by its
retained master-account ID or GL number, including configured number overrides.
Missing or malformed mapping identity blocks review; retained evidence is not
discarded when a bank's current mapping changes. These receipt tables remain
in the same native-table validation, locked apply census and frozen proposal
evidence as other GL references. Only exact bank-ID, currency and quantity
columns are classified as non-GL identities; unknown account fields still refuse.

### Saved Bank response contract identity

Bank response delivery compares each saved content field exactly, including a legacy null response contract. A missing contract field or a changed value is refused; null is not silently converted to an empty contract. This preserves the existing legacy response compiler and does not introduce a new response policy, authorize financial replay, or bypass current workflow authority.

### Final-review corrections — 2026-10-24 (local, not deployed)

The shared reversal helper refuses a second reversal of a journal already recorded
as a reciprocal in cash-leg or complete-valuation evidence. Such a second reversal
has no supported evidence protocol and would invalidate the original receipt.
This is an integrity limit, not an accounting policy; ordinary legacy reversals
remain supported. Do not bypass the refusal by removing receipts or source links.

Cross-entity transfer execution locks both entity currency configurations, selected
company/system exchange-rate rows and currency precision rows through the owning
posting transaction. Late lock acquisition is nonwaiting. It re-resolves economics
before recording success; changes made by the owning connection also abort both
journals. Prices, rate choices and rounding policy remain explicit editable inputs.

With migration774 installed, supported bank/card matches to an existing journal
record match-only provenance when there is no prior financial claim, authenticated
provider binding, shared movement or source-created journal. Unmatch requires a
reason for these recorded associations and atomically releases their active claim,
retaining immutable association/release history, the actual executor actor and the
source snapshot. A subsequent match can select the correct existing journal;
neither journal nor its GL is rewritten. Source and journal locks serialize
competing writers. Any failure rolls back the source change and claim release.

Existing configured authorization and approval controls still apply to match and
unmatch through every supported client; this does not require an internal saga.
There is no country or accountant-specific rule in the release mechanism.

Without migration774, existing conservative behavior remains. Older associations
without recorded provenance, source-created journals, authenticated provider
claims and shared/ambiguous movements are not automatically releasable. Unmatch
may clear their visible link while retaining financial ownership, so a different
journal remains refused. Use reviewed recovery; do not reverse a valid journal or
edit reservations directly merely to bypass that refusal. Partial or altered774
storage refuses the operation. These changes are locally verified, not deployed.
