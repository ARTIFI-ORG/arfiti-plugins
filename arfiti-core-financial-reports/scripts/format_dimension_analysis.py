#!/usr/bin/env python3
"""Present a P&L by dimension value from server reports (report_contract 1).

Usage:
    python3 format_dimension_analysis.py --input dimension.json --output report.md [--entity-name NAME]

Input: one income statement per dimension value, each requested from the server
with a dimension selection, plus optionally one untagged column and the
unfiltered entity total:

    {"dimension_type": "Department",
     "columns": [
       {"label": "Sales", "report": <generate_report("income_statement", {..., "report_contract": 1,
            "dimension_filter": {"conditions": [{"dimension_type_id": 1, "operator": "is_any_of",
            "value_ids": [10]}], "connectors": []}})>},
       {"label": "Untagged", "report": <same with {"operator": "is_empty", "value_ids": []}>}],
     "entity_total": <the same income statement without a dimension_filter>}   # optional

Every amount is the server's, signed as the server presents it (a refund on a
cost stays a negative cost). Columns are separate selections: they can overlap,
they are not an allocation, and they are never added up here.
"""
from report_v1 import (UNAVAILABLE, ReportInputError, dec, dimension_selection, esc, evidence, footer, header,
                       load, money, ratio, require_unfiltered, run_cli, same_basis)

LINES = (("revenue", "Revenue"), ("cogs", "Cost of sales"), ("gross_profit", "Gross profit"),
         ("operating_expenses", "Operating expenses"), ("operating_profit", "Operating profit"),
         ("other_income", "Other income"), ("finance_costs", "Finance costs"), ("income_tax", "Income tax"),
         ("net_income", "Net income"))


def build_report(data, entity_name=None, **_):
    if not isinstance(data, dict) or not isinstance(data.get("columns"), list) or not data["columns"]:
        raise ReportInputError("REPORT_SHAPE_INVALID: pass columns, one income_statement result per dimension value")
    columns = []
    for i, col in enumerate(data["columns"]):
        if not isinstance(col, dict) or not col.get("label"):
            raise ReportInputError(f"REPORT_SHAPE_INVALID: columns[{i}] needs a label and a report")
        env = load(col.get("report"), "income_statement", f"columns[{i}] ({col['label']})")
        if not dimension_selection(env):
            raise ReportInputError(f"REPORT_SHAPE_INVALID: columns[{i}] ({col['label']}) has no dimension_filter "
                                   "in its scope; request it with a dimension selection")
        columns.append((col["label"], env))
    total = load(data["entity_total"], "income_statement", "entity_total") if data.get("entity_total") else None
    if total:
        require_unfiltered({"entity_total": total})
    envs = {label: env for label, env in columns}
    if total:
        envs["entity_total"] = total
    same_basis(envs)
    windows = {label: (e["dates"].get("effective", {}).get("from"), e["dates"].get("effective", {}).get("to"))
               for label, e in envs.items()}
    if len(set(windows.values())) > 1:
        raise ReportInputError(f"REPORT_PERIOD_MISMATCH: {windows}")

    first = columns[0][1]
    out = header(f"P&L by {esc(data.get('dimension_type') or 'dimension')}", first, entity_name)
    out += ["Each column is a separate server income statement for lines tagged with that value. "
            "Selections can overlap (a parent value includes its children; a line can carry several values), "
            "so the columns are not an allocation and are not added up. Compare with the entity total, not with a sum.", ""]
    for label, env in columns:
        out += evidence(env, label)
    if total:
        out += evidence(total, "Entity total")

    names = [label for label, _ in columns] + (["Entity total"] if total else [])
    reports = [env for _, env in columns] + ([total] if total else [])
    out += ["| Line | " + " | ".join(esc(n) for n in names) + " |", "|---|" + "---:|" * len(names)]
    for key, label in LINES:
        if not any(key in env["totals"] for env in reports):
            continue
        out.append(f"| {label} | " + " | ".join(money(env["totals"].get(key), env) for env in reports) + " |")
    margins = []
    for env in reports:
        value = ratio(dec(env["totals"].get("operating_profit")), dec(env["totals"].get("revenue")), 4)
        margins.append(UNAVAILABLE if value is None else f"{value * 100:.1f}%")
    out.append("| Operating margin | " + " | ".join(margins) + " |")
    out += ["", "Costs are shown as positive amounts; a negative cost is a refund or contra amount and raises profit. "
            "Operating margin is plugin analysis (server operating profit ÷ server revenue).", ""]
    return "\n".join(out + footer())


def main():
    run_cli("Format a P&L by dimension value from report_contract 1 results", build_report)


if __name__ == "__main__":
    main()
