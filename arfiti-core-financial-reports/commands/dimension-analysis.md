---
name: dimension-analysis
description: Present a P&L by department, project or other dimension: one server income statement per dimension value, an untagged column and the entity total, without adding the columns up. Uses format_dimension_analysis.py.
---

# P&L by Dimension

Builds a P&L table by dimension value from the server's own income statement, requested once per value with a dimension selection. The server classifies every line by subtype, so revenue, cost of sales and expenses are real statement sections.

## Usage

```
/arfiti-core-financial-reports:dimension-analysis
```

Requires Python 3.9+ (`python3 --version`) when a formatter runs.

## Rules

- Add `"report_contract": 1` to every `generate_report` call and save the result **unchanged** as JSON. Never retype amounts, re-classify accounts, sum rows into totals or round them.
- A `null` amount is **Unavailable**, never zero. Show every evidence gap, warnings included.
- If the result is `success: false`, show its message (for example `REPORT_SCOPE_FORBIDDEN`: the user has no access to that entity) and stop.
- If the formatter exits with code 2, show its reason and fix the request; do not work around it.

## Step 1: Choose the dimension

```
query("dimension_type")
query("dimension_value", filters={"legal_entity_id": ID, "dimension_type_id": TYPE_ID})
```

`dimension_value` returns a flat list. Use each value's `master_dimension_value_id`. Inactive values are valid for past periods. A parent value includes its children.

## Step 2: Fetch one income statement per value

For each chosen value:

```
generate_report("income_statement", {"legal_entity_id": ID, "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "report_contract": 1,
  "dimension_filter": {"conditions": [{"dimension_type_id": TYPE_ID, "operator": "is_any_of", "value_ids": [VALUE_ID]}], "connectors": []}})
```

Also fetch the untagged lines (`"operator": "is_empty", "value_ids": []`) and the entity total (the same call without `dimension_filter`). Use the same period for every call.

## Step 3: Build the input and format

```json
{"dimension_type": "Department",
 "columns": [{"label": "Sales", "report": <result>}, {"label": "Untagged", "report": <result>}],
 "entity_total": <result>}
```

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/format_dimension_analysis.py" --input /tmp/dimension_{ENTITY_ID}_{TYPE}.json --output /tmp/dimension_report.md --entity-name "ENTITY NAME"
```

Example input: `scripts/examples/dimension_analysis.json`.

## Present

Show the generated markdown. Each column is a separate selection: a line can carry several values and a parent includes its children, so the columns can overlap. They are not an allocation and are not summed. Compare each column with the entity total, not with a sum of columns.

For a budget comparison by dimension, use `generate_report("budget_actual", {"legal_entity_id": ID, "budget_version_id": VERSION, "report_contract": 1, "dimension_filter": {...}})`. Find the version first: `variance_summary` and `budget_actual` both need `budget_version_id`.
