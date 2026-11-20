---
name: budget-planning
description: Builds budgets from scratch, copies forward with adjustments, forecasts from actuals, plans employee costs with burden rates, and creates project budgets. Reads GL data, employees, projects, and existing budgets to calculate amounts and submits via the ERP workflow system.
---

## Trigger

Activate when the user mentions: create budget, build budget, budget planning, annual budget, forecast budget, budget from scratch, copy budget, roll forward budget, employee budget, project budget, headcount planning, what-if budget, budget scenario, operating budget, capital budget, department budget.

## Four Planning Modes

### Mode 1: Build from Scratch
Create a new budget by analyzing prior year GL actuals, applying growth assumptions and seasonal patterns.

### Mode 2: Copy Forward
Clone a prior year budget and apply adjustments (global growth %, per-account overrides, seasonal changes).

### Mode 3: Forecast
Create a mid-year forecast by blending YTD actuals with projected amounts for remaining months.

### Mode 4: Specialized
Employee cost budgeting (fully loaded costs with burden rates) or project budgeting (cost structures with profitability targets).

Ask the user which mode applies. If they mention "forecast" or "revision", use Mode 3. If they mention employees/headcount, use Mode 4 (Employee). If they mention a specific project, use Mode 4 (Project). Default to Mode 1 or 2 depending on whether a prior budget exists.

## Prerequisites

Before starting, confirm with the user:
1. **Legal entity ID** — which entity to budget for
2. **Fiscal year** — which year (e.g., 2026)
3. **Scenario** — budget (baseline), forecast (revised), or stretch (aspirational)
4. **Granularity** — monthly (12 periods), quarterly (4), or annual (1); required when the version is created
5. **Currency** — normally the entity's functional currency (`get_entity("legal_entity", <id>)`); required when the version is created
6. **Mode** — which of the four modes to use

Nothing is written until the user has seen the preview and said yes (CP6). In
preview-only use (the `/preview-budget` command) nothing is written at all.

## Mandatory Checkpoints

You MUST verify each checkpoint before proceeding. If a checkpoint fails, STOP and inform the user.

- **CP1**: Legal entity has an active chart of accounts (`query("account", filters={"legal_entity_id": <id>})` returns results)
- **CP2**: Prior year data is available (for copy-forward and forecast modes)
- **CP3**: All account numbers used in budget lines are active, non-header accounts of the entity (the write refuses others; a dry run with `validate_only=True` checks every line first)
- **CP4**: Budget amounts are reasonable: point out any single line that dominates the total and ask the user to confirm it
- **CP5**: Revenue vs expense sanity check: tell the user when expenses exceed revenue, and by how much (what counts as acceptable is the user's call)
- **CP6**: User has reviewed and confirmed the preview before submission
- **CP7**: Submission via `bulk_upsert` or `create` succeeds

---

## Reading every row

`query` returns at most **100 rows per page**, whatever `limit` you ask for (the
default is 50). Lists in this skill (accounts, budget lines, dimension values,
employees) are often longer, so read them page by page:

1. Ask for `limit=100`, starting at `offset=0`.
2. After each page, read `pagination`: stop when `has_next` is false, otherwise
   add the returned `pagination.page_size` to `offset` and read the next page.
   Never step by a larger number than the page actually held, and never stop
   just because a page came back short of what you asked for.
3. Check the result: the row count equals `pagination.total_count` and no record
   key appears twice (`id` for budget lines, `master_account_id` for accounts). If either check fails, read again rather than continue with a
   partial list.
4. Tell the user how many rows you read.

The same applies to every "page until complete" or "every page" below.

---

## Workflow Steps — Mode 1: Build from Scratch

### Step 1: Discover Chart of Accounts

Fetch the entity's active accounts to know what to budget:

```python
accounts, offset = [], 0
while True:
    page = query("account", filters={
        "legal_entity_id": <entity_id>,
        "is_active": true
    }, limit=100, offset=offset)
    accounts += page["results"]
    if not page["pagination"]["has_next"]:
        break
    offset += page["pagination"]["page_size"]   # a page holds at most 100 rows
```

Read every page (see **Reading every row** above; a chart often has more than
100 accounts) and tell the user how many accounts you read. Group accounts by `account_type` (revenue,
expense, asset, liability), never by account number prefix, and leave out header
accounts.

### Step 2: Fetch Prior Year Actuals

Get the prior fiscal year's actual movements as a baseline (use the entity's
fiscal year dates, not necessarily January to December):

```python
# start_date + end_date give each account's debit/credit movements for the year;
# as_of_date alone would give balances at that date, which for revenue and
# expense accounts is not the year's activity once the year has been closed.
actuals = generate_report("trial_balance", {
    "legal_entity_id": <entity_id>,
    "start_date": "2025-01-01",
    "end_date": "2025-12-31"
})
```

Check the dates the report says it used before relying on the figures.

Or for monthly detail:

```python
# Monthly actuals per account (no gl_balance entity -- aggregate
# transaction_line debits/credits for the month instead)
monthly = query("transaction_line", filters={
    "legal_entity_id": <entity_id>
}, date_filters={
    "transaction_date": {"from": "2025-01-01", "to": "2025-01-31"}
}, group_by=["account_number"], aggregates={"debit": "sum", "credit": "sum"})
```

**CP1 checkpoint**: Confirm accounts exist.
**CP2 checkpoint**: Confirm prior year actuals are available. If not, inform the user they need to enter amounts manually.

### Step 3: Determine Growth Assumptions

Ask the user how to adjust from prior year actuals:

- **Global growth rate**: "Apply 5% increase across all accounts"
- **Per-account rates**: "Revenue +10%, Salaries +3%, Rent flat"
- **Seasonal patterns**: "Revenue peaks in Q4 (40% of annual), flat in Q1-Q3"
- **Step changes**: "New hire starts in April — salary expense increases from April onward"

See `references/budget-building-methods.md` for all calculation methods.

### Step 4: Calculate Monthly Amounts

Apply the chosen method to calculate amounts for each account and period. Show the user a clear preview table:

| Account | Jan | Feb | Mar | ... | Dec | Annual Total |
|---------|-----|-----|-----|-----|-----|-------------|
| 4000 Revenue | 45,000 | 45,000 | 45,000 | ... | 60,000 | 555,000 |
| 6000 Salaries | 25,000 | 25,000 | 25,000 | ... | 25,000 | 300,000 |
| 6100 Rent | 5,000 | 5,000 | 5,000 | ... | 5,000 | 60,000 |
| **Total** | | | | | | |

**CP3 checkpoint**: Verify all account numbers exist.
**CP4 checkpoint**: Flag any single line > 50% of total budget.
**CP5 checkpoint**: Compare total revenue vs total expense.

### Step 5: User Confirmation

**CP6 checkpoint**: Show the complete preview and ask: "Shall I create this budget?"

Show summary:
- Total Revenue: $XXX
- Total Expenses: $XXX
- Net Income: $XXX
- Number of lines: XX

Wait for explicit user confirmation.

### Step 6: Create Budget Version

```python
result = submit(object_type="budget_version", operation="create", data=json.dumps({
    "legal_entity_id": <entity_id>,
    "version_name": "FY2026 Operating Budget",
    "fiscal_year": 2026,
    "scenario": "budget",
    "version_type": "monthly",
    "currency_code": "EUR",
    "notes": "Built from 2025 actuals with 5% growth"
}))
budget_version_id = result["budget_version_id"]
```

### Step 7: Submit Budget Lines

```python
result = submit(object_type="budget_line", operation="bulk_upsert", data=json.dumps({
    "budget_version_id": <budget_version_id>,
    "lines": [
        {"account_number": "4000", "period_sequence": 1, "amount": 45000.00, "description": "January Revenue"},
        {"account_number": "4000", "period_sequence": 2, "amount": 45000.00, "description": "February Revenue"},
        // ... all lines
    ]
}))
```

See `references/submission-format.md` for the complete payload format.

**CP7 checkpoint**: Verify submission succeeded.

### Step 8: Add Dimensions (Optional)

If the user wants to tag lines by department, project, etc.:

```python
submit(object_type="budget_line_dimension", operation="bulk_set", data=json.dumps({
    "budget_line_id": <line_id>,
    "dimensions": [
        {"dimension_type_code": "DEPARTMENT", "dimension_value_code": "SALES"}
    ]
}))
```

### Step 9: Next Steps

Read the version back (`get_entity("budget_version", <id>)`) and its lines
(`query("budget_line", filters={"budget_version_id": <id>})`, every page), then
inform the user:
1. The version's own `status` (a new version is **draft**; the `status: "approved"`
   in the submit receipt describes the workflow request, not the budget) and the
   number of lines and totals actually saved
2. They can submit for approval: `submit(object_type="budget_workflow", operation="submit", data=JSON.stringify({"budget_version_id": <id>}))`
3. After approval, it can be locked to prevent edits

---

## Workflow Steps — Mode 2: Copy Forward

### Step 1: Find Source Budget

```python
versions = query("budget_version", filters={
    "legal_entity_id": <entity_id>,
    "fiscal_year": 2025,
    "scenario": "budget",
    "status": ["approved", "locked"]   # a locked version is an approved one frozen against edits
})
```

If several versions qualify, show the user the options with their status and ask
which to copy. A draft or submitted version is a source only if the user names it.

### Step 2: Read Every Source Line

There is no copy operation: `budget_version.create` refuses
`copy_from_version_id` / `copy_lines`. Read all source lines, page by page,
keeping each line's scope:

```python
lines, offset = [], 0
while True:
    page = query("budget_line", filters={"budget_version_id": <source_version_id>},
                 limit=100, offset=offset)
    lines += page["results"]
    if not page["pagination"]["has_next"]:
        break
    offset += page["pagination"]["page_size"]
```

Before proposing the copy, check the read is complete (see **Reading every
row**): the line count equals `pagination.total_count`, no line `id` appears
twice, and the total of the amounts is the source version's total.

Each row carries account, period, amount, currency, description, memo,
`project_id` / `customer_id` / `vendor_id` and `dimension_combo_json`. Tell the
user how many lines were read and their total.

### Step 3: Determine Adjustments

Ask the user what changes to apply:
- **Global growth %**: "Increase all lines by 5%"
- **Per-account overrides**: "Revenue +10%, keep expenses flat"
- **Remove/add accounts**: "Drop account 6500, add account 6600"
- **Seasonal rebalancing**: "Shift more revenue to Q4"

### Step 4: Calculate Adjusted Amounts

Apply the adjustments to the source lines and show a comparison:

| Account | 2025 Budget | Adjustment | 2026 Budget | Change |
|---------|-------------|------------|-------------|--------|
| 4000 Revenue | 500,000 | +10% | 550,000 | +50,000 |
| 6000 Salaries | 300,000 | +3% | 309,000 | +9,000 |
| 6100 Rent | 60,000 | Flat | 60,000 | 0 |

**CP3-CP5 checkpoints**: Same as Mode 1.

### Step 5: User Confirmation

**CP6 checkpoint**: Show comparison and ask for confirmation. Nothing has been
written yet.

### Step 6: Create the Version and Save the Lines

```python
result = submit(object_type="budget_version", operation="create", data=json.dumps({
    "legal_entity_id": <entity_id>,
    "version_name": "FY2026 Operating Budget",
    "fiscal_year": 2026,
    "scenario": "budget",
    "version_type": "monthly",         # required: the source version's granularity unless the user chose another
    "currency_code": "EUR",            # required: the source version's currency
    "notes": "Copied from FY2025 approved budget (version <source_version_id>), +5% on all lines"
}))

submit(object_type="budget_line", operation="bulk_upsert", data=json.dumps({
    "budget_version_id": result["budget_version_id"],
    "lines": [
        # every adjusted source line, with its account, period, amount and the same
        # project_id / customer_id / vendor_id and dimensions
    ]
}))
```

**CP7 checkpoint**: Read the new version's lines back and confirm the line
count and totals match the confirmed preview.

---

## Workflow Steps — Mode 3: Forecast

### Step 1: Load the Budget to Revise

```python
budget = query("budget_version", filters={
    "legal_entity_id": <entity_id>,
    "fiscal_year": 2026,
    "scenario": "budget",
    "status": ["approved", "locked"]   # the same sources as /forecast-budget
})
```

If several versions qualify, show them with their status and ask which to revise.
Then read every line of the chosen version, page by page (see **Reading every
row**), and check the count, ids and total.

### Step 2: Choose the Actuals Cutoff, Then Load YTD Actuals

Which months count as actuals is the user's (or their firm's) choice, not a
fixed rule. Ask before reading any figures:

- **Cutoff date**: the last day whose posted activity counts as actual
  (for example the end of last month).
- **Basis**:
  - **Closed periods only**: months whose fiscal period is closed
    (`query("fiscal_period", filters={"legal_entity_id": <entity_id>})`, read the
    `status`). If no period is closed yet, say so; there are then no actuals on
    this basis.
  - **Posted to date**: every month up to the cutoff, closed or not. Months
    still open are **provisional**: label them so in the preview and in
    `notes`, because later postings can change them.

Neither basis needs a period close or a month-end process to have run; both read
posted transactions. Record the cutoff and basis in the forecast's `notes`.

For the months inside the cutoff, fetch actual movements:

```python
# start_date + end_date give the period's debit/credit movements; as_of_date alone
# gives balances at that date. Check the returned dates match what you asked for.
actuals = generate_report("trial_balance", {
    "legal_entity_id": <entity_id>,
    "start_date": "2026-01-01",
    "end_date": "2026-06-30"  # the cutoff the user chose
})
```

Keep each month's movement with its sign. A month with a reversal can be
negative for an expense or revenue account; carry it as it is rather than as an
absolute value, and point it out to the user.

### Step 3: Show YTD Comparison

| Account | Budget YTD | Actual YTD | Variance | Variance % |
|---------|-----------|------------|----------|------------|
| 4000 Revenue | 270,000 | 285,000 | +15,000 | +5.6% |
| 6000 Salaries | 150,000 | 148,000 | -2,000 | -1.3% |

### Step 4: Choose Forecast Method

Ask the user which method to apply for remaining months. See `references/forecasting-methods.md`:

1. **Run Rate** — (YTD Actual / months elapsed) x remaining months
2. **Budget + Trend** — Adjust remaining budget months by YTD variance trend
3. **Seasonal Adjusted** — Apply prior year seasonal pattern to current run rate
4. **Manual Override** — User specifies amounts for remaining months

### Step 5: Calculate Full-Year Forecast

Replace past months with actuals, project remaining months:

| Account | Jan (A) | Feb (A) | ... | Jun (A) | Jul (F) | ... | Dec (F) | Full Year |
|---------|---------|---------|-----|---------|---------|-----|---------|-----------|
| 4000 | 47,500 | 48,000 | ... | 47,000 | 47,500 | ... | 52,000 | 580,000 |

(A) = Actual, (F) = Forecast; on the posted-to-date basis mark open months (P) = provisional actual

### Step 6: User Confirmation

**CP6 checkpoint**: Show full forecast with comparison to original budget.

### Step 7: Create Forecast Version and Submit

```python
# Create forecast version
result = submit(object_type="budget_version", operation="create", data=json.dumps({
    "legal_entity_id": <entity_id>,
    "version_name": "FY2026 Q2 Forecast",
    "fiscal_year": 2026,
    "scenario": "forecast",
    "version_type": "monthly",
    "currency_code": "EUR",            # required: the entity's functional currency
    "notes": "Q2 forecast: actuals posted to 2026-06-30 (May-Jun provisional, periods open) + Jul-Dec projected (run rate)"
}))

# Submit all lines (actuals + projections)
submit(object_type="budget_line", operation="bulk_upsert", data=json.dumps({
    "budget_version_id": <forecast_version_id>,
    "lines": [...]
}))
```

---

## Workflow Steps — Mode 4a: Employee Cost Budget

### Step 1: Fetch Active Employees

```python
employees = query("employee", filters={
    "legal_entity_id": <entity_id>,
    "status": "active"
})
```

Also fetch compensation records if available, and use only the ones in effect for each budget month (check effective dates and status; a future or ended record is not current pay):
```python
compensation = query("employee_compensation", filters={
    "legal_entity_id": <entity_id>
})
```

Discover the organisation's dimension codes before tagging lines (`query("dimension_value", filters={"legal_entity_id": <entity_id>})`). An employee record ID is not a dimension value; use an "employee" dimension value only if one exists for the person, otherwise name the person in `memo`. The burden rates below are illustrations: confirm the country, year and the client's rates with the user and record them in `notes`.

### Step 2: Calculate Fully Loaded Cost

For each employee, calculate the full burden. See `references/employee-cost-planning.md` for formulas:

| Employee | Base Salary | Social Tax (33%) | Unemployment (0.8%) | Benefits | Fully Loaded |
|----------|------------|-------------------|---------------------|----------|-------------|
| John Smith | 3,500/mo | 1,155 | 28 | 200 | 4,883/mo |
| Jane Doe | 4,000/mo | 1,320 | 32 | 200 | 5,552/mo |
| TBH (Q3 hire) | 3,800/mo | 1,254 | 30 | 200 | 5,284/mo |

### Step 3: Add Headcount Plans

Ask the user about planned hires/terminations:
- "Any planned hires? When do they start?"
- "Any expected terminations?"

Use TBH (To Be Hired) placeholders for planned positions. Pro-rate partial months.

### Step 4: Preview Employee Budget

Show a summary per department or per employee, with monthly breakdown.

**CP3-CP6 checkpoints**: Validate accounts, check reasonableness, get confirmation.

### Step 5: Submit with Employee Dimensions

```python
submit(object_type="budget_line", operation="bulk_upsert", data=json.dumps({
    "budget_version_id": <id>,
    "lines": [
        {
            "account_number": "6000",
            "period_sequence": 1,
            "amount": 3500.00,
            "dimensions": {"employee": "EMP-JSMITH", "department": "ENG"},
            "memo": "John Smith - Base salary"
        },
        {
            "account_number": "6010",
            "period_sequence": 1,
            "amount": 1155.00,
            "dimensions": {"employee": "EMP-JSMITH", "department": "ENG"},
            "memo": "John Smith - Social tax (33%)"
        },
        // ... more lines per employee per period
    ]
}))
```

---

## Workflow Steps — Mode 4b: Project Budget

### Step 1: Fetch Active Projects

```python
projects = query("project", filters={
    "legal_entity_id": <entity_id>,
    "status": "active"
})
```

### Step 2: Determine Cost Structure

For each project, determine the budget categories. See `references/project-budgeting.md`:

- Revenue accounts (if billable): 4100, 4200, 4300
- Expense accounts: 6000 (Labor), 6100 (Infrastructure), 6300 (Contractors), etc.

### Step 3: Calculate Project Budget Lines

For each project and period, calculate revenue and expense amounts:

| Project | Account | Monthly Budget | Annual Total |
|---------|---------|---------------|-------------|
| Website Redesign | 4100 Consulting Revenue | 12,000 | 144,000 |
| Website Redesign | 6000 Employee Time | 8,000 | 96,000 |
| Website Redesign | 6300 Contractors | 3,000 | 36,000 |
| **Gross Profit** | | **1,000** | **12,000** |

### Step 4: Preview with Profitability Summary

Show total revenue, total expense, and gross profit per project.

**CP3-CP6 checkpoints**: Validate, check, confirm.

### Step 5: Submit with Project IDs

```python
submit(object_type="budget_line", operation="bulk_upsert", data=json.dumps({
    "budget_version_id": <id>,
    "lines": [
        {
            "account_number": "4100",
            "period_sequence": 1,
            "amount": 12000.00,
            "project_id": 45,
            "memo": "Website Redesign - Consulting revenue"
        },
        // ... more project lines
    ]
}))
```

---

## Approval and Locking

After successful line submission (any mode):

```python
# Submit for approval
submit(object_type="budget_workflow", operation="submit", data=json.dumps({
    "budget_version_id": <id>,
    "comments": "FY2026 budget ready for CFO review"
}))

# Approve (by authorized user)
submit(object_type="budget_workflow", operation="approve", data=json.dumps({
    "budget_version_id": <id>,
    "comments": "Approved by CFO"
}))

# Lock (prevent further edits)
submit(object_type="budget_workflow", operation="lock", data=json.dumps({
    "budget_version_id": <id>
}))
```

Tell the user:
- Budget is now locked and visible in variance analysis
- They can view it in the Admin Dashboard under Master Data > Budgets
- Variance reports are available at Reports > Budget vs Actual

---

## Error Handling

Every write is checked before anything is saved; a refusal lists every reason
(`Line N: ...` for `bulk_upsert`) and nothing is written, so fix and resend:

- **"account ... is not an active posting account"**: check the chart of accounts (`query("account", query="XXXX")`); header and inactive accounts cannot carry budget amounts.
- **"Cannot modify budget in locked/archived/approved status"**: create a new forecast version instead.
- **"repeats the account, period and scope of line N"** or **"budget line N already has this account, period and scope"**: one line per account, period and scope; use `bulk_upsert` (it updates an existing line) or `budget_line.update`.
- **"period_sequence N is not a period of this ... version"**: 1 for annual, 1-4 quarterly, 1-12 monthly, or the version's custom period numbers.
- **"currency ... differs from the version currency"**: every line uses the version's currency.
- **"Dimension ... is unknown, inactive, ineligible"**: use dimension codes discovered with `query("dimension_value", ...)`.
- **"customer_id / vendor_id / project_id ... is not a ... of legal entity"**: the party or project must exist for the version's entity.
- **"Extra inputs are not permitted"**: the field is not part of the operation (for example `copy_from_version_id`); see `references/submission-format.md`.
- **"No prior year data"**: build from scratch with manual amounts instead of growth-based.
- **One version per entity, year and scenario**: every version that is not archived (draft, submitted, approved or locked) holds the place for its entity, fiscal year and scenario, so a second `budget_version.create` for the same three is refused by the database, and the receipt may say only that the outcome is unknown. Before creating, `query("budget_version", filters={"legal_entity_id": ..., "fiscal_year": ..., "scenario": ...})` and tell the user which version holds the place. To replace it, archive that version first (a locked one can be archived; deleting it is a separate choice), or use another scenario.
- **A submission is pending approval or its outcome is uncertain** (pending, `posting_unknown`, `workflow_result_unavailable`): do not resend it under a new idempotency key. Check what happened, in this order:
  1. `get_submissions` for the submission: its status and history say whether it was applied, rolled back or is still waiting.
  2. Read the record itself (`query("budget_version", ...)` or the version's lines) on the scope you meant to write.
  3. If it is still waiting or unclear, wait and retry with the **same** idempotency key; a replay returns the first result instead of writing twice.
  4. Use a new key only once history shows the first attempt rolled back **and** the read-back shows nothing was saved; fix the cause first (for example the version-per-scenario rule above).
