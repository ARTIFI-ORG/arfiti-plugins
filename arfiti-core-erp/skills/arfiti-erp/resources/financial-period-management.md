

## Report correctness contract (migration 630)

The updated application rejects ordinary cancellation of posted history; migration 628 adds a per-entity guard activated only after compatible writers deploy, and migration 630 supplies shared reporting facts; use an explicitly dated reversal. Financial controls reuse reporting eligibility, while structural integrity checks inspect retained journals. Raw balances retain closes; performance excludes closing transfers and the balance sheet exposes unclosed current/prior earnings. Closing-year attribution requires reviewed metadata. No new automatic year-end closing workflow is introduced.

Requires the matching migration/server release; code availability is not deployment evidence.

## Card purchase policy

Use the backend purchase workspace and shared matching decision; do not implement a competing card matcher in conversation. Preserve provider rows and show net purchase spend. Reference conflicts and competing candidates require review. A paid/settled item can still lack documentation; attach missing source evidence to the existing bill. Evidence review, waiver and grouping use `card_purchase.manage` with current version, evidence fingerprint and reason. Never infer write-off authority from matching tolerance.

Receipt follow-up belongs to the purchase obligation, with one owner and deduplicated reminder stages. Automation and delivery are report-only until the entity rollout settings are explicitly enabled. Statement coverage and opening/movement/closing balance controls must pass independently of agent match counts. August deletion/replay requires its own reviewed manifest and explicit authorization through transaction.delete; implementation permission does not authorize it.

Legacy payment-pass descriptions below apply to non-card AP/AR behavior. Card rows use the shared purchase policy and cannot use nearest-date refund pairing, fuzzy amount identity or adjusting-journal workarounds.

# Financial Period Management

**Available Workflows:**

| Workflow | Purpose | When to Use |
|----------|---------|-------------|
| [`fiscal_period.create`](#creating-a-fiscal-period) | Create new fiscal period | Setting up accounting periods for transaction posting |
| [`fiscal_period.close`](#closing-a-fiscal-period) | Close period with validation | Month-end close, finalize period for reporting |
| [`fiscal_period.reopen`](#reopening-a-fiscal-period) | Reopen closed period | Post late transactions, correct period errors |
| [`fiscal_period.lock`](#locking-a-fiscal-period) | Lock period for audit | Freeze period after audit, prevent any reopening |
| [`fiscal_period.unlock`](#unlocking-a-fiscal-period) | Emergency unlock | Material corrections; approval steps, if any, are your organisation's workflow configuration |

**Available Query Tools:**

| Tool | Purpose |
|------|---------|
| `get_entity("fiscal_period", id=X)` | Get single fiscal period details |
| `query("fiscal_period", filters)` | List fiscal periods with filtering |
| `query("fiscal_period", query, filters)` | Search fiscal periods dynamically |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

---

## Complete Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

### Fiscal Periods Table (fiscal_periods)

**Identification Fields:**
- `id` (bigint, PK) - Unique fiscal period identifier
- `legal_entity_id` (integer, FK to legal_entities, NOT NULL) - Legal entity this period belongs to
- `period_name` (varchar(50), NOT NULL) - Period name (e.g., "2025-01", "2025-Q1")
- `period_type` (varchar(20), NOT NULL) - Period type: "month", "quarter", "year"

**Date Range Fields:**
- `start_date` (date, NOT NULL) - Period start date (inclusive)
- `end_date` (date, NOT NULL) - Period end date (inclusive)
- `fiscal_year` (integer, NOT NULL) - Fiscal year this period belongs to
- `period_number` (integer, NULL) - Sequential period number within fiscal year (optional)

**Period Status Fields:**
- `is_closed` (boolean, default: false) - Period is closed for new transactions
- `closed_at` (timestamp with time zone, NULL) - When period was closed
- `closed_by` (integer, FK to users, NULL) - User who closed the period

**Period Lock Fields:**
- `is_locked` (boolean, default: false) - Period is locked and cannot be reopened
- `locked_at` (timestamp with time zone, NULL) - When period was locked
- `locked_by` (integer, FK to users, NULL) - User who locked the period
- `lock_reason` (text, NULL) - Required reason for locking (audit trail)
- `unlocked_at` (timestamp with time zone, NULL) - When period was last unlocked (if ever)
- `unlocked_by` (integer, FK to users, NULL) - User who unlocked the period
- `unlock_reason` (text, NULL) - Required reason for unlocking (audit trail)

**System & Audit:**
- `created_at` (timestamp with time zone, default: now()) - Period creation timestamp

**Unique Constraints:**
- `(legal_entity_id, period_name)` - Period name must be unique per entity
- `(legal_entity_id, start_date, end_date)` - Date range must be unique per entity

**Indexes:**
- `fiscal_periods_legal_entity_id_idx` - Query by entity
- `fiscal_periods_fiscal_year_idx` - Query by fiscal year
- `fiscal_periods_start_date_end_date_idx` - Query by date range

**Referenced By:**
- `transactions.fiscal_period_id` - All transactions link to fiscal periods
- `account_balances.fiscal_period_id` - Account balances track per period

---

## Period Status Flow

Financial periods progress through a controlled status flow:

```
┌──────────┐
│  Future  │ Period not yet started (start_date > today)
└────┬─────┘
     │
     ▼
┌──────────┐
│   Open   │ Accepting transactions (is_closed = false)
└────┬─────┘
     │ fiscal_period.close
     ▼
┌──────────┐
│  Closed  │ No new transactions (is_closed = true, is_locked = false)
└────┬─────┘
     │ fiscal_period.lock
     ▼
┌──────────┐
│  Locked  │ Frozen, cannot reopen (is_locked = true)
└──────────┘
```

**Status Rules:**

| Status | New Transactions | Edit Existing | Reopen Allowed | Lock Allowed |
|--------|-----------------|---------------|----------------|--------------|
| **open** | ✅ Allow | ✅ Allow | N/A (already open) | ❌ No (close first) |
| **closed** | ❌ Block | ❌ Block (reopen first) | ✅ Yes | ✅ Yes |
| **locked** | ❌ Block | ❌ Block | ❌ No (unlock first) | N/A (already locked) |

---

## Creating a Fiscal Period

Use the `fiscal_period.create` workflow to create new accounting periods.

### Workflow: fiscal_period.create

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="fiscal_period", operation="create")

// Step 2: Submit with discovered fields
submit("fiscal_period", "create", {
    legal_entity_id: 13,
    period_name: "2025-01",
    period_type: "month",
    start_date: "2025-01-01",
    end_date: "2025-01-31",
    fiscal_year: 2025,
    period_number: 1
})
// Tip: Use validate_only=true to check payload before submitting
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `legal_entity_id` | number | Legal entity ID (use `query("legal_entity")` to find) |
| `period_name` | string | Period name (e.g., "2025-01", "2025-Q1", "FY2025") |
| `period_type` | string | Type: "month", "quarter", or "year" |
| `start_date` | string | Start date in YYYY-MM-DD format |
| `end_date` | string | End date in YYYY-MM-DD format (inclusive) |
| `fiscal_year` | number | Fiscal year (e.g., 2025) |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `period_number` | number | Sequential number within fiscal year (e.g., 1-12 for months) |

**Validation:**
- `legal_entity_id` must reference existing legal entity
- `period_name` must be unique for this legal entity
- `end_date` must be after `start_date`
- Date ranges cannot overlap with existing periods of same type
- `period_type` must be one of: "month", "quarter", "year"

**Response:**
```json
{
  "success": true,
  "fiscal_period_id": 42,
  "period_name": "2025-01",
  "period_type": "month",
  "fiscal_year": 2025,
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "is_closed": false,
  "is_locked": false
}
```

### Example: Create Monthly Period

```javascript
submit("fiscal_period", "create", {
    legal_entity_id: 13,
    period_name: "2025-01",
    period_type: "month",
    start_date: "2025-01-01",
    end_date: "2025-01-31",
    fiscal_year: 2025,
    period_number: 1
})
```

**Result:** January 2025 period created, open for transaction posting

### Creating Periods for Opening Balance Migration

When a user provides a balance sheet from a prior year (e.g., 31.12.2024), you need fiscal periods for the **new** fiscal year to post the opening balances.

**Rule:** A balance sheet dated 31.12.2024 means opening balances as of 01.01.2025 — post to period **2025-01**.

**Check first:**
```javascript
query("fiscal_period", filters={"legal_entity_id": 12}, limit=50)
```

**If the target period doesn't exist, create it before posting:**
```javascript
submit("fiscal_period", "create", {
    legal_entity_id: 12,
    period_name: "2025-01",
    period_type: "month",
    start_date: "2025-01-01",
    end_date: "2025-01-31",
    fiscal_year: 2025,
    period_number: 1
})
```

**IMPORTANT:**
- Do NOT post opening balances to a different year's period just because it's the only one that exists
- Create the correct period first, then upload opening balances to it
- See [Bulk Import: Opening Balance](bulk-import.md#opening-balance-import) for the complete upload workflow

### Example: Create Quarterly Period

```javascript
submit("fiscal_period", "create", {
    legal_entity_id: 13,
    period_name: "2025-Q1",
    period_type: "quarter",
    start_date: "2025-01-01",
    end_date: "2025-03-31",
    fiscal_year: 2025,
    period_number: 1
})
```

**Result:** Q1 2025 period created (Jan-Mar)

### Example: Create Annual Period

```javascript
submit("fiscal_period", "create", {
    legal_entity_id: 13,
    period_name: "FY2025",
    period_type: "year",
    start_date: "2025-01-01",
    end_date: "2025-12-31",
    fiscal_year: 2025
})
```

**Result:** Annual fiscal year 2025 period created

---

## Closing a Fiscal Period

Use the `fiscal_period.close` workflow to close accounting periods after month-end procedures are complete.

### Workflow: fiscal_period.close

```javascript
submit("fiscal_period", "close", {
    legal_entity_id: 13,
    period_name: "2025-01",
    create_closing_entries: false
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `legal_entity_id` | number | Legal entity ID |
| `period_name` | string | Period name to close (e.g., "2025-01") |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `create_closing_entries` | boolean | Create closing journal entries (default: false) |

**Validation:**
- Period must exist and be open (`is_closed = false`)
- No draft transactions in period
- Trial balance must balance (debits = credits)
- All required reconciliations complete (if configured)

**Response:**
```json
{
  "success": true,
  "fiscal_period_id": 42,
  "period_name": "2025-01",
  "closed_at": "2025-02-05T14:30:00Z",
  "closed_by": 30,
  "closing_entry_id": null
}
```

### Example: Standard Month-End Close

```javascript
// Close January 2025 after month-end procedures
submit("fiscal_period", "close", {
    legal_entity_id: 13,
    period_name: "2025-01"
})
```

**Result:** January 2025 closed, no new transactions allowed

### Example: Year-End Close with Closing Entries

```javascript
// Close December 2025 with closing entries
submit("fiscal_period", "close", {
    legal_entity_id: 13,
    period_name: "2025-12",
    create_closing_entries: true
})
```

**Result:** December 2025 closed, closing journal entries created to zero out income statement accounts

---

## Reopening a Fiscal Period

Use the `fiscal_period.reopen` workflow to reopen closed periods (if not locked) to post corrections or late transactions.

### Workflow: fiscal_period.reopen

```javascript
submit("fiscal_period", "reopen", {
    legal_entity_id: 13,
    period_name: "2025-01",
    reopen_reason: "Need to post late expense report dated January"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `legal_entity_id` | number | Legal entity ID |
| `period_name` | string | Period name to reopen |

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `reopen_reason` | string | Reason for reopening (recommended for audit trail) |

**Validation:**
- Period must exist and be closed (`is_closed = true`)
- Period must NOT be locked (`is_locked = false`)
- User must have `delete` permission (senior accountant or higher)

**Response:**
```json
{
  "success": true,
  "fiscal_period_id": 42,
  "period_name": "2025-01",
  "reopened_at": "2025-02-06T09:15:00Z",
  "reopened_by": 30,
  "reopen_reason": "Need to post late expense report dated January"
}
```

### Example: Reopen for Late Transaction

```javascript
submit("fiscal_period", "reopen", {
    legal_entity_id: 13,
    period_name: "2025-01",
    reopen_reason: "Late vendor invoice dated January 28 received February 6"
})
```

**Result:** January 2025 reopened, can post transactions

**Process:**
1. Reopen period
2. Post correcting/late transactions
3. Re-close period using `fiscal_period.close`

---

## Locking a Fiscal Period

Use the `fiscal_period.lock` workflow to lock closed periods to prevent reopening (for audit, tax filing, SOX compliance).

### Workflow: fiscal_period.lock

```javascript
submit("fiscal_period", "lock", {
    legal_entity_id: 13,
    period_name: "2025-12",
    lock_reason: "Year-end 2025 audit complete - SOX compliance"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `legal_entity_id` | number | Legal entity ID |
| `period_name` | string | Period name to lock |
| `lock_reason` | string | Required reason for locking (min 10 chars, audit trail) |

**Validation:**
- Period must exist and be closed (`is_closed = true`)
- Period must NOT already be locked (`is_locked = false`)
- Requires the permission your organisation configured for `fiscal_period.lock` (none by default)
- `lock_reason` is required and must be at least 10 characters

**Response:**
```json
{
  "success": true,
  "fiscal_period_id": 54,
  "period_name": "2025-12",
  "locked_at": "2026-02-15T14:30:00Z",
  "locked_by": 1,
  "lock_reason": "Year-end 2025 audit complete - SOX compliance",
  "warning": "Locked period cannot be reopened until it is unlocked with fiscal_period.unlock; approval steps, if any, are your organisation's workflow configuration"
}
```

### Example: Lock After Year-End Audit

```javascript
submit("fiscal_period", "lock", {
    legal_entity_id: 13,
    period_name: "2025-12",
    lock_reason: "Year-end 2025 audit complete - SOX compliance - Audit report dated 2026-02-15"
})
```

**Result:** December 2025 locked; reopening it first needs `fiscal_period.unlock` (approval steps, if any, are your organisation's workflow configuration)

### Example: Lock After Tax Filing

```javascript
submit("fiscal_period", "lock", {
    legal_entity_id: 13,
    period_name: "2025-Q4",
    lock_reason: "Q4 2025 tax return filed - Form 1120 submitted to IRS on 2026-03-15"
})
```

**Result:** Q4 2025 locked after tax filing

### When to Lock Periods

**Common Reasons:**
1. **External Audit Complete** - After auditors issue opinion
2. **Tax Filing** - After tax returns filed with authorities
3. **Year-End Close** - After annual financial statements finalized
4. **SOX Compliance** - Quarterly/annual periods for public companies
5. **Management Review** - After board approval of financials

**Permission Required:** the permission your organisation configured for `fiscal_period.lock` (none by default)

---

## Unlocking a Fiscal Period

Use the `fiscal_period.unlock` workflow for emergency unlock of locked periods. Any approval step (e.g. the CFO) is the organisation's workflow configuration; the `status` in the submit() result says whether the unlock ran or is waiting for approval.

### Workflow: fiscal_period.unlock

```javascript
submit("fiscal_period", "unlock", {
    legal_entity_id: 13,
    period_name: "2025-12",
    unlock_reason: "Material revenue misstatement $50K found - CFO approved correction per email 2026-02-20 10:30 AM"
})
```

**Required Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `legal_entity_id` | number | Legal entity ID |
| `period_name` | string | Period name to unlock |
| `unlock_reason` | string | Detailed reason (min 20 chars, must include CFO approval reference) |

**Validation:**
- Period must exist and be locked (`is_locked = true`)
- Requires the permission your organisation configured for `fiscal_period.unlock` (none by default)
- `unlock_reason` is required and must be at least 20 characters
- Should include CFO approval reference or documentation

**Response:**
```json
{
  "success": true,
  "fiscal_period_id": 54,
  "period_name": "2025-12",
  "unlocked_at": "2026-02-20T15:45:00Z",
  "unlocked_by": 1,
  "unlock_reason": "Material revenue misstatement $50K found - CFO approved correction per email 2026-02-20 10:30 AM",
  "warning": "Period must be re-closed and re-locked after corrections are made"
}
```

### Example: Emergency Audit Adjustment

```javascript
// Step 1: Unlock period (approval as the organisation has configured it)
submit("fiscal_period", "unlock", {
    legal_entity_id: 13,
    period_name: "2025-12",
    unlock_reason: "Material revenue misstatement $50K found during Q1 review - CFO approved correction per email 2026-02-20 10:30 AM - Ticket #AUD-2026-015"
})

// Step 2: Reopen period (now that it's unlocked)
submit("fiscal_period", "reopen", {
    legal_entity_id: 13,
    period_name: "2025-12",
    reopen_reason: "Emergency audit adjustment - unlocked by CFO"
})

// Step 3: Post correcting journal entries
// (use transaction workflows)

// Step 4: Re-close period
submit("fiscal_period", "close", {
    legal_entity_id: 13,
    period_name: "2025-12"
})

// Step 5: Re-lock period
submit("fiscal_period", "lock", {
    legal_entity_id: 13,
    period_name: "2025-12",
    lock_reason: "Re-locked after audit adjustment - 2026-02-20"
})
```

**Result:** Period unlocked → reopened → corrected → closed → re-locked with full audit trail

### Valid Reasons for Unlocking

**Emergency situations only:**
- Critical audit adjustments
- Material errors discovered after lock
- Regulatory compliance corrections
- Restatement requirements

**Must include:**
- CFO approval reference (email, meeting notes, ticket number)
- Detailed explanation of issue
- Dollar impact (if applicable)
- Date and time of approval

**Never unlock for:**
- Routine adjustments
- Convenience
- Late transaction posting
- Minor reclassifications

---

## Querying Fiscal Periods

### Get Single Fiscal Period

Use the unified `get_entity` tool:

```javascript
get_entity(
  entity_type="fiscal_period",
  id=42
)
```

**Response:**
```json
{
  "id": 42,
  "legal_entity_id": 13,
  "period_name": "2025-01",
  "period_type": "month",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "fiscal_year": 2025,
  "period_number": 1,
  "is_closed": true,
  "closed_at": "2025-02-05T14:30:00Z",
  "closed_by": 30,
  "is_locked": false,
  "locked_at": null,
  "locked_by": null,
  "lock_reason": null,
  "unlocked_at": null,
  "unlocked_by": null,
  "unlock_reason": null,
  "created_at": "2024-12-15T10:00:00Z"
}
```

### List Fiscal Periods

Use the unified `query` tool:

```javascript
query(
  entity_type="fiscal_period",
  filters={
    "legal_entity_id": 13,
    "fiscal_year": 2025,
    "is_closed": false
  },
  sort_by="start_date",
  sort_order="asc"
)
```

**Response:** Array of fiscal period objects

**Filterable Fields:**
- `legal_entity_id` (number) - Filter by legal entity
- `fiscal_year` (number) - Filter by fiscal year
- `period_type` (string) - Filter by type: "month", "quarter", "year"
- `is_closed` (boolean) - Filter by closed status (use `is_closed: false` for open periods, NOT `status: "open"`)
- `is_locked` (boolean) - Filter by locked status

> **Important:** There is no `status` filter field. To find open periods, use `is_closed: false`. To find closed-but-not-locked periods, use `is_closed: true, is_locked: false`.

**Sortable Fields:**
- `start_date` - Sort by period start
- `end_date` - Sort by period end
- `period_name` - Sort alphabetically
- `fiscal_year` - Sort by year

### Search Fiscal Periods

Use the unified `query` tool:

```javascript
query(
  entity_type="fiscal_period",
  query="2025",
  filters={
    "legal_entity_id": 13,
    "is_closed": true
  }
)
```

**Search capabilities:**
- Searches across: `period_name`, `period_type`
- Filter by: all fields listed above
- Sort by: all sortable fields
- Pagination: `limit` and `offset` supported

### Common Queries

**Get Current Open Period:**
```javascript
query("fiscal_period", filters={
    legal_entity_id: 13,
    is_closed: false
  },
  sort_by="start_date",
  sort_order="desc",
  limit=1)
```

**Get All 2025 Monthly Periods:**
```javascript
query("fiscal_period", filters={
    legal_entity_id: 13,
    fiscal_year: 2025,
    period_type: "month"
  },
  sort_by="period_number",
  sort_order="asc")
```

**Get All Locked Periods:**
```javascript
// is_locked is not a query filter: list closed periods and read is_locked
query("fiscal_period", filters={
    legal_entity_id: 13,
    is_closed: true
  },
  sort_by="start_date",
  sort_order="desc")
```

**Check if Period Exists:**
```javascript
query(
  entity_type="fiscal_period",
  query="2025-01",          // period_name is searched, not filtered
  filters={
    "legal_entity_id": 13
  }
)
```

---

## Common Scenarios

### Scenario 1: Standard Month-End Close

**Timeline:**
- Days 1-28: Normal operations
- Days 29-31: Pre-close activities (accruals, reconciliations)
- Days 1-3 (next month): Close process
- Days 4-5: Review and approval
- Day 6: Close period

**Implementation:**

```javascript
// Pre-close: Verify trial balance
const trialBalance = query("transaction", filters={
    legal_entity_id: 13
  },
  date_filters={transaction_date: {from: "2025-10-01", to: "2025-10-31"}})
// Manually verify debits = credits

// Close the period
submit("fiscal_period", "close", {
    legal_entity_id: 13,
    period_name: "2025-10"
})
```

**Result:** October 2025 closed successfully

### Scenario 2: Year-End Close with Lock

**Timeline:**
- Jan 1-15: External audit fieldwork
- Jan 16-20: Tax provision calculation
- Jan 21-31: Annual report preparation
- Feb 1-5: Board review and approval
- Feb 6: Lock period

**Implementation:**

```javascript
// Step 1: Close December (already done in January)
// (Period closed on January 3)

// Step 2: After audit is complete, lock the period
submit("fiscal_period", "lock", {
    legal_entity_id: 13,
    period_name: "2025-12",
    lock_reason: "Year-end 2025 audit complete - SOX compliance - Audit opinion dated 2026-02-01"
})
```

**Result:** December 2025 locked, frozen for audit compliance

### Scenario 3: Reopen and Correct

**Situation:** Found error in closed October period - vendor invoice dated October posted to November

**Implementation:**

```javascript
// Step 1: Check if period is locked
const period = query("fiscal_period", query="2025-10", filters={
    "legal_entity_id": 13
  }, limit=1)

// If is_locked = true, must unlock first (fiscal_period.unlock; approval as configured)

// Step 2: Reopen period
submit("fiscal_period", "reopen", {
    legal_entity_id: 13,
    period_name: "2025-10",
    reopen_reason: "Correction: vendor invoice #INV-2345 dated October 28 was incorrectly posted to November - needs to be in October"
})

// Step 3: Post correcting entry
// (use transaction workflow to move from November to October)

// Step 4: Re-close period
submit("fiscal_period", "close", {
    legal_entity_id: 13,
    period_name: "2025-10"
})
```

**Result:** October corrected and re-closed with audit trail

### Scenario 4: Create Full Fiscal Year

**Goal:** Set up all 12 monthly periods for 2025

**Implementation:**

```javascript
// Create January
submit("fiscal_period", "create", {
    legal_entity_id: 13,
    period_name: "2025-01",
    period_type: "month",
    start_date: "2025-01-01",
    end_date: "2025-01-31",
    fiscal_year: 2025,
    period_number: 1
})

// Create February
submit("fiscal_period", "create", {
    legal_entity_id: 13,
    period_name: "2025-02",
    period_type: "month",
    start_date: "2025-02-01",
    end_date: "2025-02-28",
    fiscal_year: 2025,
    period_number: 2
})

// ... continue for all 12 months
```

**Result:** 12 monthly periods created for 2025

### Scenario 5: Create Quarterly Periods

**Goal:** Set up quarterly reporting periods

**Implementation:**

```javascript
// Q1 2025
submit("fiscal_period", "create", {
    legal_entity_id: 13,
    period_name: "2025-Q1",
    period_type: "quarter",
    start_date: "2025-01-01",
    end_date: "2025-03-31",
    fiscal_year: 2025,
    period_number: 1
})

// Q2 2025
submit("fiscal_period", "create", {
    legal_entity_id: 13,
    period_name: "2025-Q2",
    period_type: "quarter",
    start_date: "2025-04-01",
    end_date: "2025-06-30",
    fiscal_year: 2025,
    period_number: 2
})

// Q3 2025
submit("fiscal_period", "create", {
    legal_entity_id: 13,
    period_name: "2025-Q3",
    period_type: "quarter",
    start_date: "2025-07-01",
    end_date: "2025-09-30",
    fiscal_year: 2025,
    period_number: 3
})

// Q4 2025
submit("fiscal_period", "create", {
    legal_entity_id: 13,
    period_name: "2025-Q4",
    period_type: "quarter",
    start_date: "2025-10-01",
    end_date: "2025-12-31",
    fiscal_year: 2025,
    period_number: 4
})
```

**Result:** 4 quarterly periods created for 2025

### Scenario 6: Fiscal Year Different from Calendar Year

**Goal:** Set up fiscal year April 2024 - March 2025 (FY2025)

**Implementation:**

```javascript
// FY2025 runs from April 2024 to March 2025

// April 2024 (Period 1 of FY2025)
submit("fiscal_period", "create", {
    legal_entity_id: 13,
    period_name: "2025-04",
    period_type: "month",
    start_date: "2024-04-01",
    end_date: "2024-04-30",
    fiscal_year: 2025,
    period_number: 1
})

// May 2024 (Period 2 of FY2025)
submit("fiscal_period", "create", {
    legal_entity_id: 13,
    period_name: "2025-05",
    period_type: "month",
    start_date: "2024-05-01",
    end_date: "2024-05-31",
    fiscal_year: 2025,
    period_number: 2
})

// ... continue through March 2025 (Period 12 of FY2025)

// March 2025 (Period 12 of FY2025)
submit("fiscal_period", "create", {
    legal_entity_id: 13,
    period_name: "2025-03",
    period_type: "month",
    start_date: "2025-03-01",
    end_date: "2025-03-31",
    fiscal_year: 2025,
    period_number: 12
})
```

**Result:** Fiscal year 2025 spans April 2024 - March 2025

---

## Period Naming Conventions

### Recommended Patterns

**Monthly Periods:**
- Format: `YYYY-MM` (e.g., "2025-01", "2025-02")
- Benefit: Sorts chronologically, internationally recognized

**Quarterly Periods:**
- Format: `YYYY-QN` (e.g., "2025-Q1", "2025-Q2")
- Benefit: Clear quarter identification

**Annual Periods:**
- Format: `FYYYYYYY` (e.g., "FY2025")
- Benefit: Distinguishes from calendar year

**Custom Periods:**
- Format: Descriptive (e.g., "2025-W01" for weekly, "2025-P01" for 4-4-5)
- Benefit: Flexibility for non-standard calendars

**Key Rules:**
- Keep period names consistent within organization
- Avoid special characters (use alphanumeric, hyphen only)
- Max 50 characters
- Must be unique per legal entity

---

## Getting Reference Data

Use dynamic queries to retrieve reference data:

**Legal Entities:**
```javascript
query("legal_entity")
```
Use returned `id` values for `legal_entity_id` field

**Who closed/locked a period:**
```javascript
get_entity("fiscal_period", id=42)
```
There is no separate user-lookup entity -- `closed_by` and `closed_at` are
returned directly on the fiscal period record.

**Transactions in Period:**
```javascript
query("transaction", filters={
  "legal_entity_id": 13,
  "fiscal_period_id": 42
})
```
Check transactions before closing period

**Account Balances for Period:**
```javascript
query("transaction_line", filters={
  "legal_entity_id": 13,
  "fiscal_period_id": 42
}, group_by=["account_number"], aggregates={"debit": "sum", "credit": "sum"})
```
Review balances before finalizing period

---

## Best Practices

### Period Setup Best Practices

1. **Create Periods in Advance**
   - Set up entire fiscal year at once
   - Create both monthly and quarterly periods if needed for reporting
   - Establish annual period for year-end reporting

2. **Consistent Naming**
   - Use standardized naming convention (e.g., "YYYY-MM")
   - Maintain consistency across all entities
   - Document naming convention for future reference

3. **Sequential Period Numbers**
   - Assign `period_number` sequentially (1-12 for months)
   - Enables easy sorting and reporting
   - Helps identify missing periods

4. **Date Range Accuracy**
   - Verify end dates match actual month end (28/29/30/31 days)
   - Ensure no gaps between periods
   - Ensure no overlaps between periods

### Month-End Close Best Practices

1. **Pre-Close Checklist**
   - All transactions entered and posted
   - Bank reconciliations complete
   - Credit card reconciliations complete
   - Accounts receivable aging reviewed
   - Accounts payable aging reviewed
   - Inventory counts verified (if applicable)
   - Fixed assets updated (if applicable)
   - Accruals recorded (payroll, utilities, rent, etc.)
   - Prepaid expenses adjusted
   - Deferred revenue recognized

2. **Close Process**
   - Verify trial balance balances (debits = credits)
   - Review financial statements
   - Obtain manager approval
   - Close period using `fiscal_period.close`
   - Generate and distribute financial reports

3. **Post-Close**
   - Archive supporting documentation
   - Document any adjustments made
   - Communicate close completion to stakeholders

### Period Reopening Best Practices

1. **When to Reopen**
   - Late transactions dated in closed period
   - Errors discovered that affect closed period
   - Accrual adjustments needed

2. **Documentation Requirements**
   - Always provide detailed `reopen_reason`
   - Document what transactions will be posted
   - Get approval from accounting manager
   - Create audit trail ticket/email

3. **After Reopening**
   - Post corrections immediately
   - Re-close as soon as corrections complete
   - Update affected financial statements
   - Communicate restatement if material

### Period Locking Best Practices

1. **When to Lock**
   - After external audit complete
   - After tax returns filed
   - After board approval of financials
   - For SOX compliance (quarterly for public companies)

2. **Lock Reason Requirements**
   - Be specific and detailed
   - Include dates and references
   - Document who authorized lock
   - Reference audit reports, tax filings, or board minutes

3. **Lock Process**
   - Verify period is already closed
   - Verify all corrections complete
   - Document lock reason thoroughly
   - Communicate lock to accounting team

### Period Unlocking Best Practices

1. **Emergency Only**
   - Only for material errors or compliance requirements
   - Never for convenience or routine adjustments
   - Get the approval your organisation requires (e.g. the CFO) and document it

2. **Unlock Reason Requirements**
   - Detailed explanation of issue
   - Dollar impact (if applicable)
   - CFO approval reference (email, meeting, ticket)
   - Date and time of approval
   - Min 20 characters

3. **Unlock Process**
   - Document issue thoroughly
   - Get explicit CFO approval
   - Unlock period
   - Reopen period
   - Post corrections
   - Re-close period
   - Re-lock period
   - Update financial statements if needed
   - Communicate restatement to stakeholders

### Audit Trail Best Practices

1. **Always Provide Reasons**
   - Use `reopen_reason` when reopening
   - Use `lock_reason` when locking (required)
   - Use `unlock_reason` when unlocking (required)

2. **Include Context**
   - Who approved the action
   - Why the action is needed
   - What will be changed
   - When approval was given

3. **Reference Documentation**
   - Link to emails, tickets, meeting notes
   - Reference invoice numbers, transaction IDs
   - Include dollar amounts for material items

---

## Common Pitfalls

### Don't Close Prematurely

❌ **Don't** close period before all transactions are entered
✅ **Do** verify all transactions posted before closing

❌ **Don't** close before reconciliations complete
✅ **Do** complete all reconciliations first

### Don't Skip Trial Balance Validation

❌ **Don't** assume trial balance is correct
✅ **Do** verify debits = credits before closing

### Don't Reopen Without Documentation

❌ **Don't** reopen period without clear reason
✅ **Do** document reason and get approval

### Don't Unlock Without CFO Approval

❌ **Don't** unlock locked periods for convenience
✅ **Do** only unlock for material corrections with documented CFO approval

### Don't Create Overlapping Periods

❌ **Don't** create periods with overlapping date ranges
✅ **Do** verify date ranges don't overlap with existing periods

### Don't Use Inconsistent Naming

❌ **Don't** mix naming conventions (e.g., "Jan 2025", "2025-02", "March '25")
✅ **Do** use consistent naming pattern (e.g., "2025-01", "2025-02", "2025-03")

---

## Permission Requirements

| Operation | Permission Level | Typical Role |
|-----------|-----------------|--------------|
| Create Period | `write` | Accountant, Manager |
| Close Period | `write` | Senior Accountant, Manager |
| Reopen Period | `delete` | Senior Accountant, Manager |
| Lock Period | Configured per organisation (none by default) | Controller, CFO |
| Unlock Period | Configured per organisation (none by default) | CFO |

**Permission Hierarchy:**
- `read` - View periods
- `write` - Create and close periods
- `delete` - Reopen periods (requires elevated access)
- Lock/unlock - no permission is required by default; your organisation can set one on the `fiscal_period.lock` and `fiscal_period.unlock` workflow definitions

---

## Integration Points

### Transactions

All financial transactions (`transactions` table) link to fiscal periods via `fiscal_period_id`:

```javascript
// Example: Query all transactions in a period
query("transaction", filters={
  "legal_entity_id": 13,
  "fiscal_period_id": 42
})
```

**Rules:**
- Transactions can only be posted to open periods (`is_closed = false`)
- Transaction `transaction_date` must fall within period date range
- Closing a period blocks new transactions from being posted
- Locked periods block ALL transaction operations (post, edit, delete)

### Account Balances

There is no separate balances table -- balances per period are derived from
`transaction_lines` (debit/credit) grouped by account:

```javascript
// Example: Get account balances for a period
query("transaction_line", filters={
  "legal_entity_id": 13,
  "fiscal_period_id": 42
}, group_by=["account_number"], aggregates={"debit": "sum", "credit": "sum"})
```

**Rules:**
- Balances calculated per period
- Opening balance = prior period ending balance
- Ending balance = opening + period activity
- Balances frozen when period closes

### Financial Reporting

Financial statements use period date ranges:

```javascript
// Example: Generate P&L for a period
const period = get_entity("fiscal_period", id=42)

query("transaction", filters={
    legal_entity_id: 13
  },
  date_filters={transaction_date: {from: period.start_date, to: period.end_date}})
```

**Common Reports:**
- Monthly P&L (by month period)
- Quarterly financials (by quarter period)
- Annual statements (by year period)
- Trial balance (by period)
- Balance sheet (as of period end_date)

---

## Workflow Details

All fiscal period workflows are registered in the system and can be viewed in the admin dashboard. Use `get_submissions(action='schema', object_type="fiscal_period", operation="create")` to view field definitions for any workflow.

---

## Quick Reference

### Status Summary

| Field | Values | Meaning |
|-------|--------|---------|
| `is_closed` | `false` | Period is open, accepting transactions |
| `is_closed` | `true` | Period is closed, no new transactions |
| `is_locked` | `false` | Period can be reopened if closed |
| `is_locked` | `true` | Period is frozen, cannot be reopened without unlock |

### Workflow Summary

| Workflow | Required Fields | Permission |
|----------|----------------|------------|
| `fiscal_period.create` | `legal_entity_id`, `period_name`, `period_type`, `start_date`, `end_date`, `fiscal_year` | `write` |
| `fiscal_period.close` | `legal_entity_id`, `period_name` | `write` |
| `fiscal_period.reopen` | `legal_entity_id`, `period_name` | `delete` |
| `fiscal_period.lock` | `legal_entity_id`, `period_name`, `lock_reason` | `admin` |
| `fiscal_period.unlock` | `legal_entity_id`, `period_name`, `unlock_reason` | `admin` |

### Field Constraints

| Field | Type | Constraint |
|-------|------|------------|
| `period_name` | varchar(50) | Unique per entity, max 50 chars |
| `period_type` | varchar(20) | Must be "month", "quarter", or "year" |
| `start_date`, `end_date` | date | End must be after start, range unique per entity |
| `lock_reason` | text | Required when locking, min 10 chars |
| `unlock_reason` | text | Required when unlocking, min 20 chars |

---

## Key Takeaways

✅ **Organized Accounting** - Periods structure transactions into reporting cycles
✅ **Status Control** - Clear flow: open → closed → locked
✅ **Validation on Close** - Trial balance must balance before closing
✅ **Audit Compliance** - Lock periods to prevent changes after audit
✅ **Emergency Access** - Unlock workflow for material corrections with CFO approval
✅ **Complete Audit Trail** - All period status changes tracked with timestamps, users, and reasons
✅ **Permission Controls** - Segregation of duties (write for close, admin for lock/unlock)
✅ **Transaction Linkage** - All transactions link to fiscal periods
✅ **Flexible Calendars** - Support calendar year, fiscal year, and custom periods

**Financial period management ensures organized, compliant, and auditable accounting with proper controls and cutoff procedures.**

---

*Last Updated: 2026-01-14*
*Comprehensive Guide: GUIDE_FINANCIAL_PERIOD_MANAGEMENT.md*


### Provider balance and coverage controls

Statement finalisation is separate from line match rate. All source movements must tie opening to closing in account currency; missing balances, currency/scope inconsistencies or unresolved lines prevent finalisation. An excluded line still contributes its original movement to the balance check. No invoice write-off tolerance applies to the provider balance.

`bank_statement.import` accepts optional `coverage` containing `start`, `end` (YYYY-MM-DD), `scope: "complete_account"` and `source_reference` identifying the provider evidence. Supply the actual complete-account interval, not the first and last transaction dates. `complete_account` claims "between start and end, nothing on this account is missing" — not "all time", and not "every movement is a line here", so a partial extract is expressible: declare the interval you actually have. Original rows and balances remain unchanged; unknown coverage remains an explicit exception.

An empty `lines` list is valid for a genuine zero-activity statement with equal opening/closing balances and complete coverage. Month-end uses the union of explicit passing intervals; later activity does not prove earlier coverage. A split bank/card statement DOES declare complete coverage (this reverses earlier guidance): list the created card ids in `metadata.routed_card_source_ids` and the finalisation check counts them alongside the lines, so the balance tie proves the split was faithful. Declaring coverage without routing them produces a balance gap the size of the card spend.


### Amortization catch-up exception to the original service date

The amortization recognizer may post a due tranche into the earliest eligible
open, unlocked date on or after service-period end, bounded by as_of_date and
today. It preserves service-period metadata and never reopens the old period.
This is a specific executor policy, not general permission to move invoice or
journal dates silently. Inspect its returned posting evidence and current run status.


### Period Close pipeline (2026-09-23 migration)

Period Close now uses mandatory prepare/evaluate/resolve/finalize stages, including
stored hybrid definitions. Its saga, check registry and financial workflows remain
authoritative. An approval submission keeps the final phase open; ten-minute
durable continuations reuse the same command/workflow and verify the current closed
period before completing. Unknown effects retain their identity for investigation.
The bound final phase may close its own active saga only after other phases finish
and current checks have no blocking failures; it never supplies `force`.
Remediation still delegates to the specialist owner and rechecks after resolution.
Domain `dry_run` records a diagnostic saga; pipeline `preview` performs no writes
or model calls. Approval polling does not make another model memo call.

Reporting evidence failures remain blocking where they affect opening or current balances. Use the returned transaction IDs to involve the accounting administrator. Historical posting/closing decisions are audited and do not repair missing booked amounts. Do not bypass this check or approve all legacy rows merely to finish a close.


### Statement-based close evidence and voided history

Bank reconciliation uses `bank_statement_line.match`, `unmatch`, and `exclude` plus
statement coverage/balance controls. A verified full-period statement coverage
result can satisfy the reconciliation evidence requirement when no covering legacy
run exists. This does not waive live unmatched transactions, coverage gaps, balance
failures or other close checks. Existing covering reconciliation runs remain valid
for their supported scopes. A coverage result of not-applicable is not a substitute
for completed reconciliation evidence.

Voided statements remain audit history. Their lines do not count toward active
bank coverage discovery, unsettled-line checks, or confirmed-but-unposted checks.
Unsettled live lines, including a NULL reconciliation state, still block closing.
Do not exclude or match voided rows just to satisfy a close check.

`reconciliation.auto_match`, `unmatch` and `finalize` require an explicit supported
scope; bank is not an accepted scope. Use the statement-line operations for banks.


### Live close initiator

Live close binds to the recorded saga creator (the authenticated creator for `saga.create`, or the persisted manual-run starter). The worker service user is not the accountant. Current membership, entity access and financial write permission are rechecked; payloads cannot select a different actor. A live run with no recorded initiator is refused; use a manual live run or diagnostic dry-run.

For a legacy failed run with the service user pinned as its close actor, first verify no close workflow was submitted and the period remains open. Cancel the failed saga with the supported action and create a fresh live run. Do not edit checkpoints or use `force` to hide the identity failure. Preserve command IDs while submission outcome is pending or unknown; reconcile that outcome before restarting. See the period-close guide.

### Close-agent deployment recovery

After a close-agent implementation update, verify its active definition uses the intended release before starting a new live close. Retained v1.0.0 blocks preserve historical revision hashes; the initiating-accountant blocks are v1.0.1. A successful deployment does not itself activate a new agent revision. Have an authorized operator publish/activate the reviewed release. Preserve failed run evidence and use the supported cancellation/new-run flow; do not edit stored hashes or actor checkpoints.

> **Production QA finding (2026-10-08):** A yellow lane does not by itself guarantee human approval. QA organization8266000 had zero steps on its `fiscal_period.close` definition17930; its live close auto-approved and closed the period. Configure and verify an explicit eligible review step before relying on a human approval gate. After adding an explicit administrator review step, task 133 was approved by the independent reviewer and the close saga completed. This is organization configuration, not a default guarantee.


### Fiscal-period authorization floor

All `fiscal_period` mutations require `accounting:write` (including existing
Controller roles), or ordinary owner/admin wildcard authority. For `close`,
`reopen`, `lock`, and `unlock`, the dedicated `accounting:close` permission is
also sufficient. `create` requires `accounting:write`. AP/AR/payroll writes and
master-data writes alone do not authorize period changes.

This floor is enforced before validation-only requests, cached idempotency
responses, workflow selection, and execution under the effective actor. Entity
restrictions still apply, including to wildcard administrators. Workflow
permissions and approval steps may add requirements; an empty workflow cannot
remove the permission floor. No migration or workflow reseeding is required.

If a period was incorrectly reopened, preserve the audit history and reclose it
using an authorized accountant/owner and the configured review workflow after
checking current close evidence. Do not repair status directly in SQL. Retrying
the old reopen idempotency key as an AP-only actor must be denied.


Approved human fiscal-period workflows reload the submitter's current tenant
membership, permission roles, and entity scope at completion, including when a
background worker completes the workflow. The approver's permissions do not
replace the submitter's authority. Removed membership, revoked accounting
authority, or a narrowed entity scope can therefore stop execution after approval.

If approval is recorded but execution fails, inspect the workflow's
`execution_failed` history. Do not repeat the completed decision or change period
state directly. Correct the underlying cause and submit a fresh close request
with a new idempotency key for a new review; verify the period after approval.


### Stored close-check details

Close-check details and remediation payloads use strict JSON persistence: dates
and timestamps become ISO strings, UUIDs become strings, and Decimal amounts
remain exact decimal strings. Unknown objects, non-finite values and non-string
mapping keys are refused before the outcome row is written. A persistence error
is not a passing check or a completed close; inspect the failed run and correct
the producing check before retrying. Check severity and close approval rules are
unchanged.

### Fiscal-period execution evidence (QA branch)

Execution `pending_refs` and `evidence_refs` recognize `fiscal_period:<id>` and
`fiscal_period:<entity_id>:<period_name>` as distinct formats. Each must resolve
to a stored period in the execution entity. Numeric IDs use canonical positive
integer spelling; the name format preserves the entire exact suffix, including
colons. Missing/foreign records, invalid IDs and empty names withhold execution
results. This follows current entity-scoped period reads without adding an
accounting permission requirement. Readability does not prove current closure,
locking, or permission to close/reopen a period. `close_command:<uuid>` refers to
a saga checkpoint and remains part of pending cycle-safe saga verification.


## Closing a period (AR-461)

`fiscal_period.close` re-runs every close check at the moment of closing and records what it saw.
- If the month-end close saga ran for the month (not as a dry run), every check blocks as registered, and a close is refused while that saga is still running.
- Otherwise (you, closing directly) only the integrity checks (period open, trial balance, reversal pairs, AP/AR control ties) and earlier open months block; the other checks are recorded as advisory unless the company's `period_close.policy.check_severity` makes them blocking.
- Close earlier months first, or the close is refused. The company can allow out-of-order closing by saving `{"overrides": {"config_environment.earlier_periods_closed": "advisory"}}` (needs `accounting:close`).
- Net pay paid after the month end fails `payroll.payroll_run_paid` unless the company saved `period_close.policy` / `payroll_settlement` `{"carry_unsettled_net_pay": true, "carry_from_period": "YYYY-MM"}`. Then, from that month, a run passes as carried when its payroll accrual is posted in the month and the carried net pay equals the accrued payroll balance exactly (functional-currency runs only; tax or benefit lines in the batch must be paid by the month end; the later net-pay payment is not checked). If it still fails, report the two amounts; do not post anything to make them match.
- `force: true` with `force_reason` closes despite failing *policy* checks, never integrity ones, and only when a person holding `accounting:close` submits or approves it. As an agent, do not force; tell the user which checks fail and ask them to fix the records, change the policy, or force it themselves.
- A close refused by its checks comes back as `refused: true` with an `error` code (`close_integrity_failed`, `close_checks_failed`, `close_policy_invalid`, `close_drafts_exist`, `close_trial_balance_unbalanced`) and `detail.failing_checks`; nothing was written and the month is still open. Tell the user which checks failed. A forced close that fails still returns an outcome-unknown envelope; read its reason in `get_submissions(action="history", workflow_id=...)`. After fixing the cause, resubmit with a new `idempotency_key`: the same key replays the first answer.

## Close evidence update (b1, awaiting deployment)

Built-in saga orchestration is optional product workflow. External clients remain subject to supported operation authorization and integrity controls. Recompute-at-close, the recorded close basis and the scoped `force` shipped in AR-461 (section above). Inspect actual workflow configuration; a lane name alone does not prove a human approval step exists.


Anomaly-review evidence keeps numeric fabrication filtering separate from
unsupported duplicate claims and instruction-only observations. The optional
`fabricated_findings_stripped` count measures only the numeric filter, including
when no ordinary findings remain; use the separate arrays for other suppression.

### Billing hold decision evidence

Billing close details now show scoped overlapping/exact-period decision counts
for currently capability-held contracts, including those without a recorded
decision. The status calculation is unchanged: this evidence does not apply a
policy, authorize closure or prove a historical treatment was executed. Missing
hold-decision storage is explicit. The public hold report uses the same counts.
