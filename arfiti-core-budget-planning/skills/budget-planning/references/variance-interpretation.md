# Variance Interpretation Reference

## Favorable vs Unfavorable Logic

Whether a variance is "good" or "bad" depends on the account's **type**
(`account_type` from the chart of accounts, never the account number's first
digit, which differs between charts):

| `account_type` | Favorable when | Unfavorable when |
|----------------|----------------|------------------|
| revenue / income | Actual > Budget | Actual < Budget |
| expense / cogs | Actual < Budget | Actual > Budget |
| asset | Actual > Budget | Actual < Budget |
| liability | Actual < Budget | Actual > Budget |

A contra account (for example sales returns under revenue, or accumulated
depreciation under assets) follows its `account_subtype`: it reduces its parent,
so its favorable direction is the parent's reversed.

**Formula**: `variance_amount = actual - budget`
- Positive variance on revenue/asset = favorable
- Negative variance on expense/liability = favorable

**Sign convention**: budget amounts are entered as positive numbers for revenue
and for expenses alike, and the budget vs actual report shows actuals the same
way (revenue 200 and expenses 120 give a net of 80). Do not enter revenue or other
credit-normal amounts as negative numbers. The report's own `verdict` per row
already applies this logic; use it rather than recomputing.

---

## Materiality Thresholds

Not every variance deserves investigation. Focus on material items:

### Suggested Thresholds

These are examples to agree with the user, not rules: materiality is the client's or
the accountant's choice, in the entity's own currency and scale. Ask which
thresholds to use and say which you applied.

| Criteria | Threshold | Action |
|----------|-----------|--------|
| Variance > 10% AND > $1,000 | Material | Investigate |
| Variance > 20% (any amount) | Significant | Investigate |
| Variance > $10,000 (any %) | Large absolute | Investigate |
| Variance < 5% AND < $1,000 | Immaterial | Monitor only |

### Priority Order

Investigate variances in this order:
1. **Large unfavorable** — biggest risk items first
2. **Large favorable** — may indicate budget was too conservative or timing issues
3. **Trending** — small variances that are growing month-over-month
4. **One-time** — explain and move on

---

## Common Variance Explanations

### Timing Variances
The expense or revenue was incurred in a different month than budgeted, but the annual total will be on track.

**Signs**: Monthly variance is large, but YTD is close to budget.
**Action**: No correction needed. Note "timing" in variance commentary.

**Example**:
```
Q2 Insurance premium: Budgeted evenly (5K/month), actually paid in lump sum (15K in April)
April variance: -10K unfavorable
YTD through June: on budget (30K budget, 30K actual)
```

### Volume Variances
More or fewer units/transactions than planned.

**Signs**: Revenue and related costs move in same direction.
**Action**: Determine if volume change is permanent (update forecast) or temporary (monitor).

**Example**:
```
Revenue: +15% (more customers)
COGS: +12% (more goods sold)
Net impact: favorable (revenue grew faster than costs)
```

### Price/Rate Variances
Per-unit costs or prices changed from budget assumptions.

**Signs**: Volume is on track, but dollar amounts differ.
**Action**: Update forecast if rate change is permanent. Renegotiate if possible.

**Example**:
```
Cloud hosting: Budgeted 2,000/month, Actual 2,400/month
Volume (servers): Same as budget
Root cause: AWS price increase not in budget
Annual impact: +4,800 unfavorable
```

### Mix Variances
The product/service/customer composition changed from plan.

**Signs**: Total revenue on track, but gross margin differs.
**Action**: Analyze by product line or customer segment.

**Example**:
```
Total revenue: On budget (500K)
High-margin product: -20% below budget
Low-margin product: +30% above budget
Gross margin: 2% below budget (unfavorable mix shift)
```

### One-Time Items
Non-recurring events that won't repeat.

**Signs**: Large variance in single month, not in other months.
**Action**: Note as one-time, exclude from forecasting trends.

**Example**:
```
Legal fees: Budget 5K/month, Actual 25K in March (lawsuit settlement)
One-time: Yes — exclude from run-rate forecast
Remaining months: Expect normal 5K/month
```

---

## Drill-Down Strategy

When a material variance is found, investigate in layers:

### Level 1: Account Summary
"Which accounts have the largest variances?"
```python
# Use query() or generate_report
generate_report("variance_summary", {
    "budget_version_id": <id>   # the version fixes the entity; legal_entity_id is not a parameter here
})
```

### Level 2: Period Trend
"Is this variance growing, shrinking, or one-time?"
```python
generate_report("variance_by_period", {"budget_version_id": <id>})
```
Look at whether the variance is consistent across periods or concentrated.

### Level 3: Dimension, Project or Party Breakdown
"Which department/project/region is driving this?"
```python
# The exact budget vs actual report: every row carries its stored scope
# (project_id, customer_id, vendor_id, dimension_combo_json).
generate_report("budget_actual", {
    "legal_entity_id": <entity_id>,
    "budget_version_id": <id>,
    "report_contract": 1,
    # optional: only lines in one dimension selection, by master type/value IDs
    "dimension_filter": {"conditions": [{"dimension_type_id": <type_id>,
                                         "operator": "is_any_of", "value_ids": [<value_id>]}],
                         "connectors": []}
})
```
Group the rows by their scope fields. Respect the report's verdicts: lines that
cover more than the selection are "unallocated" and overlapping scopes are not
additive, so do not add them up into a dimension total the report did not give.
Budget lines cannot be filtered by dimension with `query("budget_line")`.

### Level 4: Transaction Detail
"What specific transactions caused this?"
```python
# Every posting to the account in the period, with opening and closing balance
generate_report("account_activity", {
    "legal_entity_id": <entity_id>,
    "account_number": "6500",
    "start_date": "2026-03-01",
    "end_date": "2026-03-31"
})
```
Or the lines themselves: `query("transaction_line", filters={"legal_entity_id": <entity_id>, "account_number": "6500"}, date_filters={"transaction_date": {"from": "2026-03-01", "to": "2026-03-31"}})`, paging until complete.

---

## Review Cadence

| Frequency | Scope | Audience | Focus |
|-----------|-------|----------|-------|
| **Monthly** | Detailed by account | Budget owners | Line-by-line variance, action items |
| **Quarterly** | Summary by department | Executive team | Trends, forecast revisions |
| **Annual** | Full-year reconciliation | Board / CFO | Lessons learned, next year planning |

### Monthly Review Template

1. **Top 5 unfavorable variances** — Account, amount, %, explanation, action
2. **Top 5 favorable variances** — Account, amount, %, explanation (is budget too conservative?)
3. **YTD summary** — Total revenue vs budget, total expense vs budget, net income variance
4. **Forecast impact** — Should we revise the full-year forecast based on YTD?
5. **Action items** — Who needs to do what by when

---

## Corrective Actions

| Situation | Recommended Action |
|-----------|-------------------|
| Revenue consistently below budget | Create forecast revision (Mode 3). Investigate root cause (volume? pricing? mix?) |
| Expenses consistently above budget | Identify specific cost categories. Propose cuts or justify as investment. |
| One-time variance explained | Document explanation. No forecast change needed. |
| Trend worsening month-over-month | Escalate to management. Create pessimistic scenario. |
| Budget was wrong (bad assumptions) | Create forecast revision. Update assumptions for next year. |
| Favorable variance (under-spending) | Check if delayed spending will catch up. If genuine savings, reallocate to priorities. |
