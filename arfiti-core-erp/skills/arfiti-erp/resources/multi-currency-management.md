# Multi-Currency Management

## Verified limitation: AP payment settlement (2026-10-06)

A same-currency foreign AP payment can mark an invoice paid while leaving a functional-currency AP residual when the payment-date rate differs from the invoice carrying rate. Production QA confirmed EUR100 carried at USD113.55 was cleared by an AP debit of USD112.04 without a realized FX gain entry. The QA payment was reversed through the normal workflow. Until corrected, do not treat a paid invoice or balanced payment journal alone as proof of complete FX settlement; reconcile the invoice carrying amount, payment, and realized FX entry. Cross-currency invoice applications are refused during execution, although transaction.post validate_only currently accepts them. FX revaluation is a separate workflow and is not a substitute for settlement accounting.


## Report correctness contract (migration 630)

Shared financial reports (migration 630) use booked functional amounts and exact decimal strings. A missing legacy header functional-currency label uses the entity currency; an explicit mismatch remains a gap. Missing functional GL amounts or entity currency configuration must not be replaced with document amounts or USD/EUR. Budgets must use the same functional currency. Consolidated adapters support one shared functional currency only and remain uncertified aggregates before eliminations; no spot-rate translation fallback.

Requires the matching migration/server release; code availability is not deployment evidence.

Comprehensive guide to multi-currency operations including exchange rate management, currency conversion, and multi-currency transaction handling.

## Available Workflows

| Object Type | Operation | Description | Typical lane |
|-------------|-----------|-------------|------|
| `exchange_rate` | `create` | Create exchange rate (with automatic inverse) | Green |
| `exchange_rate` | `update` | Update existing exchange rate | Yellow |
| `exchange_rate` | `delete` | Delete exchange rate (and its inverse) | Red |

Lanes are assigned by your organisation's workflow rules; the submit() result is authoritative.

**Total:** 3 workflow operations

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

## Available Query Tools

| Tool Name | Purpose | Returns |
|-----------|---------|---------|
| `get_entity("exchange_rate", id=X)` | Get single exchange rate by ID | Full exchange rate details |
| `query("exchange_rate", filters={...})` | List rates with filters | Array of exchange rates |
| `query("exchange_rate", filters={from_currency, to_currency, effective_date_from, effective_date_to})` | Search rate history for currency pair | Historical rates for specific pair |
| `convert_currency()` | Convert amount between currencies | Converted amount with rate |

---

## Complete Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

### Exchange Rates Table (exchange_rates)

| Field Name | Data Type | Required | Description | Example |
|------------|-----------|----------|-------------|---------|
| `id` | bigint | PK | System-generated ID | `42` |
| `organization_id` | integer | Yes | Organization ID | `63` |
| `legal_entity_id` | integer | No | Entity-specific rate (null = org-wide) | `13` or `null` |
| `from_currency` | varchar(3) | Yes | Source currency (ISO 4217) | `"EUR"` |
| `to_currency` | varchar(3) | Yes | Target currency (ISO 4217) | `"USD"` |
| `rate` | numeric(18,10) | Yes | Exchange rate (18 digits, 10 decimal) | `1.0850000000` |
| `rate_type` | varchar(50) | Yes | Rate type | `"spot"`, `"average"`, `"contract"`, `"budget"` |
| `effective_date` | date | Yes | Date rate becomes effective | `2025-01-15` |
| `source` | varchar(50) | Yes | Rate source | `"manual"`, `"ecb"`, `"fed"`, `"api"` |
| `created_by` | integer | Auto | User ID who created/updated | `30` |
| `created_at` | timestamp | Auto | Creation/update timestamp | `2025-01-15 10:00:00-08` |

**Unique Constraint:** `(organization_id, from_currency, to_currency, rate_type, effective_date)` WHERE `legal_entity_id IS NULL`

**Index:** Composite index on `(from_currency, to_currency, effective_date DESC)` for fast rate lookup

---

## Workflow Documentation

### Exchange Rate Workflows

#### Create Exchange Rate

Create a new exchange rate with automatic inverse rate calculation. When you create EUR→USD, the system automatically creates USD→EUR.

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="exchange_rate", operation="create")

// Step 2: Submit with discovered fields
submit("exchange_rate", "create", {
    from_currency: "EUR",
    to_currency: "USD",
    rate: "1.0850",
    effective_date: "2025-01-15",
    rate_type: "spot",
    source: "manual"
})
// Tip: Use validate_only=true to check payload before submitting

// Response:
{
  "success": true,
  "exchange_rate_id": 42,
  "inverse_exchange_rate_id": 43,
  "from_currency": "EUR",
  "to_currency": "USD",
  "rate": "1.0850000000",
  "inverse_rate": "0.9216589861",  // Automatically calculated (1 / 1.085)
  "rate_type": "spot",
  "effective_date": "2025-01-15",
  "source": "manual"
}
```

**Required Payload Fields:**

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `from_currency` | string | Source currency | 3-letter ISO 4217 code |
| `to_currency` | string | Target currency | 3-letter ISO 4217 code, must differ from `from_currency` |
| `rate` | string/number | Exchange rate | Must be > 0, format: 1 from_currency = rate × to_currency |
| `effective_date` | string | Effective date | YYYY-MM-DD format |

**Optional Payload Fields:**

| Field | Type | Default | Description | Valid Values |
|-------|------|---------|-------------|--------------|
| `rate_type` | string | `"spot"` | Type of rate | `"spot"`, `"average"`, `"contract"`, `"budget"` |
| `source` | string | `"manual"` | Rate source | `"manual"`, `"ecb"`, `"fed"`, `"api"` |
| `legal_entity_id` | integer | `null` | Entity-specific rate | Valid entity ID or `null` for org-wide |

**Rate Type Descriptions:**

- **spot**: Daily market rate at transaction date (most common)
- **average**: Average rate for a period (e.g., monthly average for month-end valuations)
- **contract**: Fixed rate per contract or agreement (long-term contracts)
- **budget**: Budgeted or planned rate (forecasting and budget comparisons)

**Rate Source Descriptions:**

- **manual**: Manually entered by user
- **ecb**: European Central Bank rates (future integration)
- **fed**: Federal Reserve rates (future integration)
- **api**: External API rates (future integration)

**Key Features:**

- ✅ **Automatic inverse rate**: Creating EUR→USD automatically creates USD→EUR
- ✅ **Currency validation**: Ensures 3-letter ISO 4217 codes
- ✅ **Rate validation**: Must be positive, prevents same-currency rates
- ✅ **ON CONFLICT upsert**: Updates existing rate for same date/type
- ✅ **Organization-wide or entity-specific**: Supports both scopes

**Examples:**

```javascript
// Example 1: Create spot rate for EUR→USD
submit("exchange_rate", "create", {
    from_currency: "EUR",
    to_currency: "USD",
    rate: "1.0850",
    effective_date: "2025-01-15",
    rate_type: "spot",
    source: "manual"
})

// Example 2: Create monthly average rate
submit("exchange_rate", "create", {
    from_currency: "GBP",
    to_currency: "USD",
    rate: "1.2650",
    effective_date: "2025-01-01",
    rate_type: "average",
    source: "manual"
})

// Example 3: Create entity-specific contract rate
submit("exchange_rate", "create", {
    from_currency: "JPY",
    to_currency: "USD",
    rate: "0.0067",
    effective_date: "2025-01-01",
    rate_type: "contract",
    source: "manual",
    legal_entity_id: 13  // Entity-specific rate
})

// Example 4: Create budget rate for planning
submit("exchange_rate", "create", {
    from_currency: "CAD",
    to_currency: "USD",
    rate: "0.7400",
    effective_date: "2025-01-01",
    rate_type: "budget",
    source: "manual"
})
```

**Validation Errors:**

```javascript
// Error: Invalid currency code
{
  "error": "Currency codes must be 3-letter ISO 4217 codes (e.g., USD, EUR, GBP)",
  "details": "from_currency 'US' is invalid"
}

// Error: Same currency
{
  "error": "Cannot set exchange rate for same currency",
  "details": "from_currency and to_currency cannot both be 'USD'"
}

// Error: Invalid rate
{
  "error": "Exchange rate must be positive",
  "details": "rate must be > 0, got: -1.08"
}

// Error: Invalid date format
{
  "error": "Invalid date format. Use YYYY-MM-DD",
  "details": "effective_date '01/15/2025' is invalid"
}

// Error: Invalid rate type
{
  "error": "Invalid rate_type. Must be one of: spot, average, contract, budget",
  "details": "rate_type 'daily' is invalid"
}

// Error: Invalid source
{
  "error": "Invalid source. Must be one of: manual, ecb, fed, api",
  "details": "source 'yahoo' is invalid"
}
```

---

#### Update Exchange Rate

Update an existing exchange rate. When you update the `rate`, the system automatically recalculates and updates the inverse rate.

```javascript
submit("exchange_rate", "update", {
    exchange_rate_id: 42,
    rate: "1.0920",
    source: "ecb"
})

// Response:
{
  "success": true,
  "exchange_rate_id": 42,
  "from_currency": "EUR",
  "to_currency": "USD",
  "updated_fields": ["rate", "source"]
}
```

**Required Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `exchange_rate_id` | integer | Exchange rate ID to update |

**Optional Payload Fields:**

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `rate` | string/number | New exchange rate | Must be > 0, automatically updates inverse |
| `rate_type` | string | New rate type | Must be one of: spot, average, contract, budget |
| `source` | string | New rate source | Must be one of: manual, ecb, fed, api |

**Note:** At least one optional field must be provided. You cannot update `from_currency`, `to_currency`, `effective_date`, or `legal_entity_id` - create a new rate instead.

**Inverse Rate Update:** When you update the `rate` field, the system automatically finds and updates the inverse rate. For example:
- Update EUR→USD from 1.0850 to 1.0920
- System automatically updates USD→EUR from 0.9217 to 0.9158

**Examples:**

```javascript
// Example 1: Update rate only
submit("exchange_rate", "update", {
    exchange_rate_id: 42,
    rate: "1.0920"
})

// Example 2: Update source only
submit("exchange_rate", "update", {
    exchange_rate_id: 42,
    source: "ecb"
})

// Example 3: Update multiple fields
submit("exchange_rate", "update", {
    exchange_rate_id: 42,
    rate: "1.0920",
    rate_type: "average",
    source: "ecb"
})
```

**Validation Errors:**

```javascript
// Error: Exchange rate not found
{
  "error": "Exchange rate 42 not found"
}

// Error: No fields to update
{
  "error": "No fields to update",
  "details": "Must provide at least one field: rate, rate_type, or source"
}

// Error: Invalid rate
{
  "error": "Exchange rate must be positive",
  "details": "rate must be > 0, got: 0"
}
```

---

#### Delete Exchange Rate

Delete an exchange rate and its automatic inverse. **Warning:** This operation deletes both the forward rate (e.g., EUR→USD) and the inverse rate (USD→EUR).

```javascript
submit("exchange_rate", "delete", {
    exchange_rate_id: 42
})

// Response:
{
  "success": true,
  "exchange_rate_id": 42,
  "from_currency": "EUR",
  "to_currency": "USD",
  "deleted_count": 2  // Forward + inverse
}
```

**Required Payload Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `exchange_rate_id` | integer | Exchange rate ID to delete |

**Important Notes:**

- Deletes both forward and inverse rates
- Cannot be undone - must recreate the rate
- Does not cascade to transactions (historical rates preserved on transactions)
- ✅ Safe to delete: Transactions store rates at creation time, so historical transactions are unaffected

**Example:**

```javascript
// Delete EUR→USD rate (also deletes USD→EUR inverse)
submit("exchange_rate", "delete", {
    exchange_rate_id: 42
})
```

**Validation Errors:**

```javascript
// Error: Exchange rate not found
{
  "error": "Exchange rate 42 not found"
}
```

---

## Query Tool Documentation

### Get Exchange Rate by ID

Retrieve a single exchange rate by its ID.

```javascript
get_entity("exchange_rate", id=42)

// Response:
{
  "success": true,
  "exchange_rate": {
    "id": 42,
    "from_currency": "EUR",
    "to_currency": "USD",
    "rate": "1.0850000000",
    "rate_type": "spot",
    "effective_date": "2025-01-15",
    "source": "manual",
    "legal_entity_id": null,
    "created_at": "2025-01-15T10:30:00-08:00"
  }
}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Exchange rate ID |

---

### List Exchange Rates

List exchange rates with optional filters.

```javascript
query("exchange_rate", filters={"from_currency": "EUR", "rate_type": "spot"})

// Response:
{
  "success": true,
  "exchange_rates": [
    {
      "id": 42,
      "from_currency": "EUR",
      "to_currency": "USD",
      "rate": "1.0850000000",
      "rate_type": "spot",
      "effective_date": "2025-01-15",
      "source": "manual",
      "legal_entity_id": null,
      "created_at": "2025-01-15T10:30:00-08:00"
    },
    {
      "id": 38,
      "from_currency": "EUR",
      "to_currency": "GBP",
      "rate": "0.8580000000",
      "rate_type": "spot",
      "effective_date": "2025-01-15",
      "source": "manual",
      "legal_entity_id": null,
      "created_at": "2025-01-15T10:35:00-08:00"
    }
  ],
  "count": 2
}
```

**Filter Parameters:**

| Filter Key | Type | Required | Description |
|-----------|------|----------|-------------|
| `from_currency` | string | No | Filter by source currency (3-letter ISO code) |
| `to_currency` | string | No | Filter by target currency (3-letter ISO code) |
| `rate_type` | string | No | Filter by rate type |
| `source` | string | No | Filter by source |
| `legal_entity_id` | integer | No | Filter by legal entity (null = org-wide) |

**Date Filters** (separate `date_filters` parameter, not inside `filters`):

Use `date_filters={"effective_date": {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"}}` for date range queries.

**Examples:**

```javascript
// Example 1: List all EUR rates
query("exchange_rate", filters={"from_currency": "EUR"})

// Example 2: List spot rates only
query("exchange_rate", filters={"rate_type": "spot"})

// Example 3: List entity-specific rates
query("exchange_rate", filters={"legal_entity_id": 13})

// Example 4: List all rates (including future-dated)
query("exchange_rate")

// Example 5: List EUR→USD spot rates
query("exchange_rate", filters={"from_currency": "EUR", "to_currency": "USD", "rate_type": "spot"})
```

---

### Search Exchange Rate History

Search historical exchange rates for a specific currency pair using `query` with date range filters.

```javascript
query("exchange_rate",
  filters={"from_currency": "EUR", "to_currency": "USD", "rate_type": "spot"},
  date_filters={"effective_date": {"from": "2024-12-15", "to": "2025-01-15"}}
)

// Response:
{
  "success": true,
  "from_currency": "EUR",
  "to_currency": "USD",
  "rate_type": "spot",
  "exchange_rates": [
    {
      "id": 42,
      "rate": "1.0850000000",
      "effective_date": "2025-01-15",
      "source": "manual",
      "legal_entity_id": null,
      "created_at": "2025-01-15T10:30:00-08:00"
    },
    {
      "id": 38,
      "rate": "1.0820000000",
      "effective_date": "2025-01-10",
      "source": "manual",
      "legal_entity_id": null,
      "created_at": "2025-01-10T09:00:00-08:00"
    },
    {
      "id": 35,
      "rate": "1.0790000000",
      "effective_date": "2025-01-05",
      "source": "manual",
      "legal_entity_id": null,
      "created_at": "2025-01-05T08:45:00-08:00"
    }
  ],
  "count": 3
}
```

**Filter Parameters:**

| Filter Key | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `from_currency` | string | Yes | - | Source currency (3-letter ISO code) |
| `to_currency` | string | Yes | - | Target currency (3-letter ISO code) |
| `rate_type` | string | No | `"spot"` | Rate type filter |
| `effective_date_from` | string | No | All | Start date for history (YYYY-MM-DD) |
| `effective_date_to` | string | No | All | End date for history (YYYY-MM-DD) |
| `legal_entity_id` | integer | No | All | Filter by legal entity |

**Returns:** Historical rates ordered by `effective_date DESC` (newest first)

**Examples:**

```javascript
// Example 1: Get last 30 days of EUR→USD rates
query("exchange_rate",
  filters={"from_currency": "EUR", "to_currency": "USD", "rate_type": "spot"},
  date_filters={"effective_date": {"from": "2024-12-15", "to": "2025-01-15"}}
)

// Example 2: Get all historical rates for GBP→USD
query("exchange_rate", filters={
    from_currency: "GBP",
    to_currency: "USD",
    rate_type: "spot"
  })

// Example 3: Get monthly average rates for Q4 2024
query("exchange_rate", filters={
    from_currency: "EUR",
    to_currency: "USD",
    rate_type: "average"
  },
  date_filters={effective_date: {from: "2024-10-01", to: "2024-12-31"}})

// Example 4: Get entity-specific contract rates
query("exchange_rate", filters={
    from_currency: "JPY",
    to_currency: "USD",
    rate_type: "contract",
    legal_entity_id: 13
  })
```

---

### Convert Currency

Convert an amount from one currency to another using the most recent exchange rate.

```javascript
convert_currency(amount=10000.00, from_currency="EUR", to_currency="USD", effective_date="2025-01-15")

// Response:
{
  "success": true,
  "amount": "10000.00",
  "from_currency": "EUR",
  "to_currency": "USD",
  "rate": "1.0850000000",
  "converted_amount": "10850.00",
  "effective_date": "2025-01-15",
  "source": "manual"
}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `amount` | number | Yes | Amount to convert (must be ≥ 0) |
| `from_currency` | string | Yes | Source currency (3-letter ISO code) |
| `to_currency` | string | Yes | Target currency (3-letter ISO code) |
| `effective_date` | string | Yes | Date for exchange rate lookup (YYYY-MM-DD) |

**Rate Lookup Logic:**

1. If `from_currency` = `to_currency`, return rate of 1.0 (no conversion)
2. Otherwise, lookup most recent rate on or before `effective_date`:
   - `WHERE from_currency = ? AND to_currency = ?`
   - `AND effective_date <= ?`
   - `ORDER BY effective_date DESC LIMIT 1`
3. If no rate found, return error with suggestion to create rate

> **Note:** The tool returns the latest available rate on or before the requested date. If exchange rates have not been updated recently, the returned rate may be stale (e.g., requesting today's rate may return a rate from days or weeks ago). Check the `effective_date` in the response to verify the rate's age. If rates are out of date, use `manage_connectors(action="sync_exchange_rates")` to fetch current rates or create a manual rate.

**Examples:**

```javascript
// Example 1: Convert €10,000 to USD
convert_currency(amount=10000.00, from_currency="EUR", to_currency="USD", effective_date="2025-01-15")
// Returns: $10,850.00 (at rate 1.085)

// Example 2: Convert £5,000 to USD
convert_currency(amount=5000.00, from_currency="GBP", to_currency="USD", effective_date="2025-01-15")
// Returns: $6,325.00 (at rate 1.265)

// Example 3: Same currency (no conversion)
convert_currency(amount=1000.00, from_currency="USD", to_currency="USD", effective_date="2025-01-15")
// Returns: $1,000.00 (rate 1.0, note: "Same currency - no conversion")

// Example 4: Convert small amount (JPY to USD)
convert_currency(amount=150000.00, from_currency="JPY", to_currency="USD", effective_date="2025-01-15")
// Returns: $1,005.00 (at rate 0.0067)
```

**Error Handling:**

```javascript
// Error: No rate found
{
  "error": "Exchange rate not found",
  "message": "No rate available for EUR/USD on or before 2025-01-15",
  "suggestion": "Use submit('exchange_rate', 'create', {...}) to create the rate"
}

// Error: Invalid amount
{
  "error": "Amount cannot be negative",
  "details": "amount must be >= 0, got: -1000"
}

// Error: Invalid currency code
{
  "error": "Currency codes must be 3-letter ISO 4217 codes",
  "details": "from_currency 'US' is invalid"
}

// Error: Invalid date
{
  "error": "Invalid date format. Use YYYY-MM-DD",
  "details": "effective_date '01/15/2025' is invalid"
}
```

---

## Common Use Cases

### Use Case 1: Daily Exchange Rate Entry

As a finance team member, I need to enter daily spot rates for all currency pairs we trade in.

```javascript
// Step 1: Create EUR→USD rate for today
submit("exchange_rate", "create", {
    from_currency: "EUR",
    to_currency: "USD",
    rate: "1.0850",
    effective_date: "2025-01-15",
    rate_type: "spot",
    source: "manual"
})

// Step 2: Create GBP→USD rate for today
submit("exchange_rate", "create", {
    from_currency: "GBP",
    to_currency: "USD",
    rate: "1.2650",
    effective_date: "2025-01-15",
    rate_type: "spot",
    source: "manual"
})

// Step 3: Create JPY→USD rate for today
submit("exchange_rate", "create", {
    from_currency: "JPY",
    to_currency: "USD",
    rate: "0.0067",
    effective_date: "2025-01-15",
    rate_type: "spot",
    source: "manual"
})

// All inverse rates (USD→EUR, USD→GBP, USD→JPY) are created automatically!
```

---

### Use Case 2: Month-End Revaluation

As an accountant, I need to revalue foreign currency balances using monthly average rates.

```javascript
// Step 1: Create monthly average rate for January 2025
submit("exchange_rate", "create", {
    from_currency: "EUR",
    to_currency: "USD",
    rate: "1.0820",  // Average of all daily rates in January
    effective_date: "2025-01-31",
    rate_type: "average",
    source: "manual"
})

// Step 2: Find the open EUR balances to revalue: the receivables and
// payables still owed at month end. The aging reports list them with their
// amount due; keep the EUR-denominated items (open means amount_due > 0,
// never status alone).
generate_report("ar_aging", {"legal_entity_id": 13, "as_of_date": "2025-01-31"})
generate_report("ap_aging", {"legal_entity_id": 13, "as_of_date": "2025-01-31"})

// Step 3: Convert each EUR balance to USD using average rate
convert_currency(amount=50000.00, from_currency="EUR", to_currency="USD", effective_date="2025-01-31")
// Uses rate_type: "average" for month-end
```

---

### Use Case 3: Long-Term Contract with Fixed Rate

As a procurement manager, I have a 1-year contract with a UK supplier at a locked-in rate.

```javascript
// Create contract rate for the full year
submit("exchange_rate", "create", {
    from_currency: "GBP",
    to_currency: "USD",
    rate: "1.2800",  // Locked-in contract rate
    effective_date: "2025-01-01",
    rate_type: "contract",
    source: "manual",
    legal_entity_id: 13  // Entity-specific contract
})

// When creating AP invoices for this supplier, use contract rate
// The system will use rate_type: "contract" for entity 13
```

---

### Use Case 4: Budget Planning with Assumed Rates

As a finance director, I'm creating the FY2026 budget and need to use assumed exchange rates.

```javascript
// Create budget rates for FY2026
submit("exchange_rate", "create", {
    from_currency: "EUR",
    to_currency: "USD",
    rate: "1.1000",  // Budgeted rate
    effective_date: "2026-01-01",
    rate_type: "budget",
    source: "manual"
})

submit("exchange_rate", "create", {
    from_currency: "GBP",
    to_currency: "USD",
    rate: "1.3000",  // Budgeted rate
    effective_date: "2026-01-01",
    rate_type: "budget",
    source: "manual"
})

// Use budget rates for variance analysis:
// Compare actual spot rates vs budget rates to see FX impact on budget
```

---

### Use Case 5: Correct an Incorrect Rate

As a finance team member, I entered the wrong exchange rate and need to correct it.

```javascript
// Step 1: Find the incorrect rate
query("exchange_rate", filters={ from_currency: "EUR", to_currency: "USD" }, date_filters={ effective_date: { to: "2025-01-15" } })
// Response shows exchange_rate_id: 42 with rate: "1.0850"

// Step 2: Update the rate
submit("exchange_rate", "update", {
    exchange_rate_id: 42,
    rate: "1.0920"  // Corrected rate
})
// Inverse rate (USD→EUR) is automatically recalculated
```

---

### Use Case 6: View Rate History for Audit

As an auditor, I need to see all historical rates for a currency pair to verify compliance.

```javascript
// Get complete EUR→USD rate history for 2024
query("exchange_rate", filters={
    from_currency: "EUR",
    to_currency: "USD",
    rate_type: "spot"
  },
  date_filters={effective_date: {from: "2024-01-01", to: "2024-12-31"}})

// Response shows all rates with:
// - Rate value
// - Effective date
// - Source (manual, ecb, etc.)
// - Created timestamp
// - Created by user
```

---

### Use Case 7: Multi-Currency Invoice Conversion

As an AR clerk, I'm creating a EUR invoice for a customer, and I need to record it in our USD functional currency.

```javascript
// Step 1: Check if rate exists for today
query("exchange_rate", filters={
    from_currency: "EUR",
    to_currency: "USD",
    rate_type: "spot"
  },
  date_filters={effective_date: {from: "2025-01-15", to: "2025-01-15"}})

// Step 2: If no rate exists, create it
submit("exchange_rate", "create", {
    from_currency: "EUR",
    to_currency: "USD",
    rate: "1.0850",
    effective_date: "2025-01-15",
    rate_type: "spot",
    source: "manual"
})

// Step 3: Convert invoice amount
convert_currency(amount=10000.00, from_currency="EUR", to_currency="USD", effective_date="2025-01-15")
// Returns: $10,850.00

// Step 4: Create AR invoice with both currencies
// (This is handled by transaction workflow, which uses the rate automatically)
```

---

## Three-Currency Architecture

Every transaction in the system stores amounts in **three currencies**:

1. **Document Currency** - The currency the transaction was entered in (e.g., EUR invoice)
2. **Functional Currency** - The legal entity's base operating currency (e.g., USD)
3. **Reporting Currency** - The group consolidation currency (e.g., USD for parent company)

### How Exchange Rates Are Applied

```
User creates transaction in EUR (document currency)
         ↓
System looks up legal entity → functional_currency = USD
         ↓
System looks up exchange rate: EUR→USD = 1.085 (spot)
         ↓
System calculates:
  - document_amount: €10,000 (entered)
  - functional_amount: $10,850 (€10,000 × 1.085)
  - reporting_amount: $10,850 (same as functional in this example)
  - document_to_functional_rate: 1.085 (stored on transaction)
  - rate_type: 'spot' (stored on transaction)
  - rate_source: 'system' (stored on transaction)
```

### Rate Lookup Priority

When a transaction needs an exchange rate, the system searches in this order:

1. **Entity-specific rate** (if `legal_entity_id` is set)
   - `WHERE legal_entity_id = ? AND from_currency = ? AND to_currency = ?`
   - `AND effective_date <= ? AND rate_type = ?`
   - `ORDER BY effective_date DESC LIMIT 1`

2. **Organization-wide rate** (if no entity-specific rate found)
   - `WHERE legal_entity_id IS NULL AND from_currency = ? AND to_currency = ?`
   - `AND effective_date <= ? AND rate_type = ?`
   - `ORDER BY effective_date DESC LIMIT 1`

3. **Error if no rate found** - Transaction cannot proceed without a rate

### Rate Type Selection by Transaction Type

| Transaction Type | Recommended Rate Type | Reason |
|------------------|----------------------|--------|
| AR Invoice | `spot` | Daily transaction uses spot rate |
| AP Invoice | `spot` | Daily transaction uses spot rate |
| Payment | `spot` | Daily transaction uses spot rate |
| Manual Journal | `spot` or `manual` | Depends on entry purpose |
| Month-End JE | `average` | Use monthly average for revaluation |
| Budget Entry | `budget` | Use budgeted rates for planning |
| Contract Invoice | `contract` | Use locked-in contract rate |

---

## Best Practices

### 1. Enter Rates Daily

Enter exchange rates daily (or fetch from API when integration is available) to ensure all transactions can be processed.

```javascript
// Daily rate entry routine
["EUR", "GBP", "JPY", "CAD", "CHF"].forEach(currency => {
  submit("exchange_rate", "create", {
      from_currency: currency,
      to_currency: "USD",
      rate: getRateFromExternalSource(currency),
      effective_date: today,
      rate_type: "spot",
      source: "manual"
  })
})
```

### 2. Use Appropriate Rate Types

- **spot**: Daily transactions (AR, AP, payments)
- **average**: Month-end revaluations
- **contract**: Long-term contracts with fixed rates
- **budget**: Budget planning and variance analysis

### 3. Store Rates on Transactions

Always store the exchange rate on the transaction itself. Never recalculate rates later - this violates audit requirements.

```javascript
// ✅ CORRECT: Transaction stores rate at creation time
{
  "document_currency": "EUR",
  "functional_currency": "USD",
  "amount": 10000.00,
  "functional_amount": 10850.00,
  "document_to_functional_rate": 1.085,  // Stored forever
  "rate_type": "spot",
  "rate_source": "system"
}

// ❌ WRONG: Don't recalculate rate later
// This violates audit requirements for historical rate preservation
```

### 4. Entity-Specific Rates for Contracts

Use entity-specific rates for long-term contracts to avoid affecting other entities.

```javascript
// ✅ CORRECT: Entity-specific contract rate
submit("exchange_rate", "create", {
    from_currency: "GBP",
    to_currency: "USD",
    rate: "1.2800",
    effective_date: "2025-01-01",
    rate_type: "contract",
    source: "manual",
    legal_entity_id: 13  // Only applies to entity 13
})
```

### 5. Automatic Inverse Rates

The system automatically creates inverse rates. Never manually create inverse rates.

```javascript
// ✅ CORRECT: Create one direction only
submit("exchange_rate", "create", {
    from_currency: "EUR",
    to_currency: "USD",
    rate: "1.0850"
})
// System automatically creates USD→EUR = 0.9217

// ❌ WRONG: Don't manually create inverse
submit("exchange_rate", "create", {
    from_currency: "USD",
    to_currency: "EUR",
    rate: "0.9217"  // Don't do this!
})
```

### 6. Rate Precision

Exchange rates are stored with 10 decimal places (`numeric(18,10)`) for maximum precision. When creating rates, provide as many decimal places as available.

```javascript
// ✅ CORRECT: Maximum precision
rate: "1.0850123456"  // 10 decimal places

// ACCEPTABLE: Fewer decimals (will be padded)
rate: "1.0850"  // Stored as 1.0850000000

// ❌ WRONG: Too many decimals (will be rounded)
rate: "1.085012345678901"  // Exceeds precision
```

---

## Future Enhancements

### Planned: ECB Integration

Future releases will support automatic exchange rate fetching from the European Central Bank (ECB).

```javascript
// Future: Automatic ECB rate fetch
fetch_exchange_rates_from_api({
  source: "ecb",
  effective_date: "2025-01-15",
  base_currency: "EUR"
})
// Will automatically create all EUR→XXX rates from ECB daily rates
```

### Planned: Federal Reserve Integration

Future releases will support automatic exchange rate fetching from the Federal Reserve.

```javascript
// Future: Automatic Fed rate fetch
fetch_exchange_rates_from_api({
  source: "fed",
  effective_date: "2025-01-15",
  base_currency: "USD"
})
// Will automatically create all USD→XXX rates from Fed H.10 release
```

### Planned: Scheduled Rate Updates

Future releases will support scheduled automatic rate updates.

```javascript
// Future: Schedule daily rate updates
schedule_exchange_rate_updates({
  source: "ecb",
  currency_pairs: ["EUR/USD", "GBP/USD", "JPY/USD"],
  schedule: "daily",
  time: "09:00 UTC"
})
```

---

## Troubleshooting

### Problem: Rate Not Found Error

**Symptom:** When creating a transaction, you get "No exchange rate found for EUR/USD on 2025-01-15"

**Solution:**
```javascript
// Create the missing rate
submit("exchange_rate", "create", {
    from_currency: "EUR",
    to_currency: "USD",
    rate: "1.0850",
    effective_date: "2025-01-15",
    rate_type: "spot",
    source: "manual"
})
```

---

### Problem: Wrong Rate Applied

**Symptom:** Transaction used rate 1.08 but current rate is 1.085

**Explanation:** This is correct behavior. Transactions store the rate that was active on the transaction date, not the current rate. Historical rates must be preserved for audit compliance.

**To verify:**
```javascript
// Check what rate was active on transaction date
query("exchange_rate", filters={
    from_currency: "EUR",
    to_currency: "USD"
  },
  date_filters={effective_date: {from: "2025-01-10", to: "2025-01-10"}})
// Shows rate was 1.08 on that date
```

---

### Problem: Need to Correct Historical Rate

**Symptom:** Realized we entered the wrong rate yesterday, and transactions already use it

**Solution:** You have two options:

**Option 1: Update the rate (affects future transactions only)**
```javascript
// Update the rate going forward
submit("exchange_rate", "update", {
    exchange_rate_id: 42,
    rate: "1.0850"  // Corrected rate
})
// Note: This does NOT update existing transactions
```

**Option 2: Manual journal entry to correct transactions**
```javascript
// Create correcting journal entry for FX difference
submit("transaction", "post", {
    transaction_type_code: "JOURNAL_ENTRY",
    transaction_date: "2025-01-15",
    description: "FX rate correction for EUR→USD",
    lines: [
      {
        account_number: "1200",  // AR
        debit: 50.00,  // Difference: (1.085 - 1.08) × €10,000
        credit: 0
      },
      {
        account_number: "7500",  // FX Gain/Loss
        debit: 0,
        credit: 50.00
      }
    ]
})
```

---

### Problem: Rate Lookup Returns Wrong Rate Type

**Symptom:** Transaction uses spot rate when contract rate should apply

**Explanation:** Rate type must match between the rate and the transaction logic. If a transaction requests a `contract` rate, but only `spot` rates exist, it will not find a match.

**Solution:** Create the appropriate rate type:
```javascript
submit("exchange_rate", "create", {
    from_currency: "GBP",
    to_currency: "USD",
    rate: "1.2800",
    effective_date: "2025-01-01",
    rate_type: "contract",  // Must match transaction request
    source: "manual",
    legal_entity_id: 13
})
```

---

## Summary

### Key Concepts

- **Automatic inverse rates**: System maintains bidirectional rates automatically
- **Rate types**: spot, average, contract, budget for different use cases
- **Organization-wide vs entity-specific**: Flexible rate scope
- **Historical preservation**: Rates stored on transactions for audit compliance
- **Three-currency architecture**: Document, functional, reporting currencies

### Workflow Operations

- **Create**: Add new rates with automatic inverse calculation
- **Update**: Modify rates with automatic inverse recalculation
- **Delete**: Remove rates (and their inverses)

### Query Tools

- **get_entity("exchange_rate", id=X)**: Retrieve single rate by ID
- **query("exchange_rate", filters={...})**: List with filters (including date ranges for history)
- **convert_currency()**: Convert amounts using current rate

### Implementation Checklist

✅ **Exchange rates workflow**: Create, update, delete operations
✅ **Automatic inverse rates**: Bidirectional rates maintained
✅ **Query tools**: Get, list, search, convert operations
✅ **Rate types**: spot, average, contract, budget supported
✅ **Rate sources**: manual, ecb, fed, api (manual only for now)
✅ **Entity-specific rates**: Optional legal_entity_id scope
✅ **Historical preservation**: Rates stored on transactions
✅ **Audit trail**: All operations logged with user/timestamp

Multi-currency exchange rate management is complete and ready for use.


## Explicit AP invoice settlement (implementation, deployment pending)

AP payments submitted with invoice applications release each invoice's original AP carrying value in functional and reporting currencies. Cash remains valued at the payment-date rate. Realized differences are GL-only lines on the same payment, with zero document-currency amounts and inherited payment dimensions. Partial applications use cumulative rounding; reversing a payment reverses these lines and restores its applications. The application record stores the functional amount actually released.

The invoice and payment currencies must match, including during preflight. A rate difference requires an active, unambiguous `fx_gain_loss` posting profile in the payment entity and available configured accounts. Missing configuration refuses the entire payment; no account or balancing journal is silently created. Outstanding unreversed FX revaluation and historical foreign applications without carrying-release evidence require review before further settlement. Use normal reversal/reconciliation procedures; never alter posted GL directly.

This change covers explicit `AP_PAYMENT.applications`. It does not claim equivalent realized-FX behavior for AR receipts or later matching of standalone payments. Previously posted residuals are not repaired automatically. Production verification is tracked in the workflow/permission QA plan.
