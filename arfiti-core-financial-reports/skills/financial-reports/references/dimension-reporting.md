# P&L by Dimension

## The supported way

Build the table from the server's own income statement, requested once per dimension value with a dimension selection (`report_contract: 1`):

```
generate_report("income_statement", {"legal_entity_id": ID, "start_date": ..., "end_date": ..., "report_contract": 1,
  "dimension_filter": {"conditions": [{"dimension_type_id": TYPE_ID, "operator": "is_any_of", "value_ids": [VALUE_ID]}], "connectors": []}})
```

- Untagged lines: `"operator": "is_empty", "value_ids": []`. Everything except a value: `"is_none_of"` (this includes untagged lines).
- The entity total is the same call without `dimension_filter`.
- Every call uses the same entity and period. The formatter refuses mixed periods, currencies or entities.

Each result is a full income statement with the server's subtype sections (revenue, cost of sales, operating expenses, other income, finance costs, income tax) and totals, so the columns are real statements.

## Discovering dimensions

```
query("dimension_type")                                         # names and ids
query("dimension_value", filters={"legal_entity_id": ID, "dimension_type_id": TYPE_ID})
```

The value list is flat. Use `master_dimension_value_id` as the value id. A parent value includes its current children. Inactive values remain valid for past periods.

## Reading the table

- Columns are separate selections. A line can carry several values and a parent includes its children, so columns can overlap. They are not an allocation, and the formatter never adds them up. Compare each column with the entity total.
- Signs are the server's: a refund on a cost is a negative cost and raises the column's profit.
- An incomplete column (for example dimension evidence missing) shows Unavailable amounts and its gap; it is not a zero column.
- Shared-cost allocation (overheads spread over departments) is a business policy and a separate process; this table shows only what is tagged.

## Other dimension reports

- `dimension_analysis` (`legal_entity_id`, `dimension_type_name`, `start_date`, `end_date`, optional `account_type`) returns one amount per value for an account type. Use it for a quick ranking of one account type, not for a P&L.
- `dimension_hierarchy` (same parameters, optional `parent_code`) rolls values up their hierarchy.
- Budget by dimension: `generate_report("budget_actual", {"legal_entity_id": ID, "budget_version_id": VERSION, "report_contract": 1, "dimension_filter": {...}})`. Find the budget version first. Overlapping budget scopes must not be summed.
