#!/usr/bin/env python3
"""Present an income statement (P&L) from the server report (report_contract 1).

Usage:
    python3 format_income_statement.py --input income_statement.json --output report.md [--entity-name NAME]

Input: the result of
    generate_report("income_statement", {"legal_entity_id": ID, "start_date": "YYYY-MM-DD",
                                         "end_date": "YYYY-MM-DD", "report_contract": 1
                                         [, "comparison_mode": "prior_period" | "prior_year"]})
saved unchanged. Sections follow the server's subtype classification and sign
convention (a contra cost keeps its sign); totals are the server's. Margins are
labelled plugin analysis.
"""
from report_v1 import (UNAVAILABLE, dec, esc, evidence, footer, header, load, missing_row, money, money_totals,
                       ratio, run_cli)

# Labels for the server's section and total keys. A section the server adds later
# is still shown, under its own key.
LABELS = {"revenue": "Revenue", "cogs": "Cost of sales", "gross_profit": "Gross profit",
          "operating_expenses": "Operating expenses", "operating_profit": "Operating profit",
          "other_income": "Other income", "finance_costs": "Finance costs", "income_tax": "Income tax",
          "net_income": "Net income"}
TOTAL_ORDER = ("revenue", "cogs", "gross_profit", "operating_expenses", "operating_profit",
               "other_income", "finance_costs", "income_tax", "net_income")


def label(key):
    if key is None:
        return "Unclassified"
    return LABELS.get(key) or str(key).replace("_", " ").capitalize()


def build_report(data, entity_name=None, **_):
    env = load(data, "income_statement")
    comparison = env.get("details", {}).get("comparison")
    prior = load(comparison, "income_statement", "details.comparison") if comparison else None
    prior_rows = {r.get("row_id"): r for r in prior["rows"]} if prior else {}

    out = header("Income Statement", env, entity_name)
    out += evidence(env)
    if prior:
        eff = prior["dates"].get("effective", {})
        out += evidence(prior, f"Comparison ({eff.get('from') or '?'} to {eff.get('to') or '?'})")

    cols = "| Line | Amount | Prior |" if prior else "| Line | Amount |"
    sep = "|---|---:|---:|" if prior else "|---|---:|"
    sections = []
    for row in env["rows"] + (prior["rows"] if prior else []):
        if row.get("section") not in sections:
            sections.append(row.get("section"))
    current_ids = {r.get("row_id") for r in env["rows"]}
    for section in sections:
        out += [f"## {esc(label(section))}", "", cols, sep]
        for row in env["rows"]:
            if row.get("section") != section:
                continue
            name = row.get("account_name") or row.get("row_id")
            if row.get("account_number"):
                name = f"{row['account_number']} {name}"
            line = f"| {esc(name)} | {money(row.get('display_amount'), env)} |"
            if prior:
                match = prior_rows.get(row.get("row_id"))
                line += f" {money(match.get('display_amount'), prior) if match else missing_row(prior)} |"
            out.append(line)
        if prior:
            for row in prior["rows"]:
                if row.get("section") == section and row.get("row_id") not in current_ids:
                    out.append(f"| {esc(row.get('account_name') or row.get('row_id'))} | {missing_row(env)} | {money(row.get('display_amount'), prior)} |")
        if section is not None and section in money_totals(env["totals"]):
            total = f"| **Total {esc(label(section).lower())}** | **{money(env['totals'][section], env)}** |"
            if prior:
                total += f" **{money(prior['totals'].get(section), prior)}** |"
            out.append(total)
        out.append("")

    out += ["## Summary (server totals)", "", cols, sep]
    money_keys = money_totals(env["totals"])
    keys = [k for k in TOTAL_ORDER if k in money_keys] + [k for k in money_keys if k not in TOTAL_ORDER]
    for key in keys:
        line = f"| {esc(label(key))} | {money(env['totals'].get(key), env)} |"
        if prior:
            line += f" {money(prior['totals'].get(key), prior)} |"
        out.append(line)
    out += ["", "Expenses are shown as positive costs; a negative cost is a refund or contra amount and increases profit.", ""]

    revenue = dec(env["totals"].get("revenue"))
    margins = [(name, ratio(dec(env["totals"].get(key)), revenue, 4)) for name, key in
               (("Gross margin", "gross_profit"), ("Operating margin", "operating_profit"), ("Net margin", "net_income"))]
    out += ["## Margins", "", "*Plugin analysis: server totals divided by server revenue.*", "", "| Margin | Value |", "|---|---:|"]
    for name, value in margins:
        out.append(f"| {name} | {UNAVAILABLE if value is None else f'{value * 100:.1f}%'} |")
    out.append("")
    return "\n".join(out + footer())


def main():
    run_cli("Format an income statement from report_contract 1", build_report)


if __name__ == "__main__":
    main()
