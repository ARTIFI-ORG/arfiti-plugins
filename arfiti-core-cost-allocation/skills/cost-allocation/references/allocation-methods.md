# Allocation Methods Reference

## 1. Fixed Percentage

User specifies exact percentages for each target.

**When to use**: Simple overhead splits where percentages are known and stable.

**Example**: "Split IT costs 60% Sales, 25% Marketing, 15% Finance"

```
Source: 6900 IT Overhead, CR 10,000
Target: 6900 IT Overhead (Sales),     DR 6,000  (60%)
Target: 6900 IT Overhead (Marketing), DR 2,500  (25%)
Target: 6900 IT Overhead (Finance),   DR 1,500  (15%)
```

**Validation**: Percentages must sum to 100%. Rounding follows the section below: the remainder goes to the line the user's rule names.

## 2. Proportional by Account Balance

Allocate proportional to each target's existing balance (e.g., by department expenses or revenue).

**When to use**: Fair distribution based on actual financial data.

**Example**: "Allocate rent based on each department's total expenses"

**Steps**:
1. Find the dimension's real name first (`query("dimension_type", filters={"is_active": True})`; "Department" below is an example), then fetch target balances by it: `generate_report("dimension_analysis", {"legal_entity_id": <id>, "dimension_type_name": "<name>", "start_date": <period_start>, "end_date": <period_end>, "account_type": "expense"})`. Account types are lowercase: `asset`, `liability`, `equity`, `revenue`, `cogs`, `expense`. A refusal (an unknown dimension or `REPORT_INVALID_ACCOUNT_TYPE`) means the drivers could not be read, not that they are zero: say so and stop. A successful report with no values means nothing was posted with that dimension in the period; say that too before choosing another driver.
2. Calculate each department's share: `dept_balance / total_balance`
3. Apply percentages to source amount

## 3. By Employee Headcount

Allocate based on number of active employees per department/cost center.

**When to use**: Shared services, HR costs, office expenses.

**Example**: "Allocate office rent by number of employees in each department"

**Steps**:
1. Fetch employees: `query("employee", filters={"legal_entity_id": <id>, "status": "active"})`
2. Group by department dimension
3. Calculate percentages: `dept_count / total_count`

## 4. By Revenue

Allocate proportional to each segment's revenue.

**When to use**: Common for shared corporate costs, management fees.

**Example**: "Allocate corporate overhead based on each business unit's revenue"

**Steps**:
1. Fetch revenue balances by dimension
2. Calculate each segment's revenue share
3. Apply percentages

## 5. Step-Down Allocation

Sequential allocation where service departments allocate to each other and to operating departments.

**When to use**: Complex cost center hierarchies where IT serves HR, HR serves everyone, etc.

**Steps**:
1. Determine allocation order (most shared → least shared)
2. First department allocates, excluding itself from future allocations
3. Next department allocates (including costs received from step 1)
4. Continue until all service departments are allocated

**Note**: This requires multiple allocation runs in sequence.

## 6. Custom Formula

Any combination of the above, or user-defined rules.

**Examples**:
- "First $5,000 equally, remainder by revenue"
- "50% by headcount, 50% by square footage"
- "Allocate to departments that used the service (based on tickets)"

## Rounding

When a method doesn't produce exact amounts:
1. Calculate each target's amount in decimal arithmetic (never binary floating point)
2. Round each line to the decimals of the run's currency (2 for most currencies, 0 for some, such as JPY; allocation amounts never carry more than 2, even in a 3-decimal currency). Amounts with more decimals than that are refused, not rounded
3. Sum the rounded amounts; the difference from the source amount is the rounding remainder
4. Put the remainder on the one target line that the user's rule (or their firm's documented practice) names. If they have none, propose one in the preview (for example the largest target) and let them confirm it before submitting. The largest target is only a suggestion, not a fixed rule
5. Total debits then equal total credits exactly; there is no tolerance

Example, JPY (0 decimals), source CR 10,000 split three ways equally, with the user's rule "remainder to Finance": Sales DR 3,333, Marketing DR 3,333, Finance DR 3,334.

## Multi-Dimension Allocations

Lines can carry up to 3 dimension pairs:
- `dimension_1_code` / `dimension_1_value` (e.g., DEPT / SALES)
- `dimension_2_code` / `dimension_2_value` (e.g., PROJECT / PROJ-001)
- `dimension_3_code` / `dimension_3_value` (e.g., REGION / NORTH)

This enables allocations like "split by department AND project".
