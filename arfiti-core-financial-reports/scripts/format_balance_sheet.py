#!/usr/bin/env python3
"""Present a balance sheet from the server report (report_contract 1).

Usage:
    python3 format_balance_sheet.py --input balance_sheet.json --output report.md [--entity-name NAME]

Input: the result of
    generate_report("balance_sheet", {"legal_entity_id": ID, "as_of_date": "YYYY-MM-DD",
                                      "report_contract": 1[, "comparison_mode": "prior_year"]})
saved unchanged. Rows, totals, the earnings bridge and the reconciliation verdict
are the server's; the ratios at the end are labelled plugin analysis.
"""
from report_v1 import (UNAVAILABLE, assess, dec, esc, evidence, footer, group_total, header, load,
                       load_policy, missing_row, money, policy_note, ratio, run_cli, verdict)

SECTIONS = (("asset", "Assets", "assets"), ("liability", "Liabilities", "liabilities"), ("equity", "Equity", "equity"))


def build_report(data, entity_name=None, **_):
    env = load(data, "balance_sheet")
    comparison = env.get("details", {}).get("comparison")
    prior = load(comparison, "balance_sheet", "details.comparison") if comparison else None
    prior_rows = {r.get("row_id"): r for r in prior["rows"]} if prior else {}

    out = header("Balance Sheet", env, entity_name)
    out += evidence(env)
    if prior:
        out += evidence(prior, f"Comparison ({prior['dates'].get('effective', {}).get('as_of') or '?'})")

    cols = "| Line | Amount | Prior |" if prior else "| Line | Amount |"
    sep = "|---|---:|---:|" if prior else "|---|---:|"
    for section, title, total_key in SECTIONS:
        out += [f"## {title}", "", cols, sep]
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
                if row.get("section") == section and row.get("row_id") not in {r.get("row_id") for r in env["rows"]}:
                    out.append(f"| {esc(row.get('account_name') or row.get('row_id'))} | {missing_row(env)} | {money(row.get('display_amount'), prior)} |")
        total = f"| **Total {title.lower()}** | **{money(env['totals'].get(total_key), env)}** |"
        if prior:
            total += f" **{money(prior['totals'].get(total_key), prior)}** |"
        out += [total, ""]

    liabilities, equity = dec(env["totals"].get("liabilities")), dec(env["totals"].get("equity"))
    both = None if liabilities is None or equity is None else str(liabilities + equity)
    out += ["## Check", "", "| Check | Result |", "|---|---|",
            f"| Total assets | {money(env['totals'].get('assets'), env)} |",
            f"| Total liabilities and equity (plugin sum of the two server totals) | {money(both, env)} |",
            f"| Assets = liabilities + equity | {verdict(env.get('details', {}).get('reconciliation'), env)} |", ""]

    bridge = env.get("details", {}).get("earnings_bridge")
    if isinstance(bridge, dict):
        out += ["## Earnings in equity (server bridge)", "",
                f"Fiscal year {esc(bridge.get('fiscal_year', '?'))}, starting {esc(bridge.get('fiscal_year_start', '?'))}. "
                "The current-year result covers the fiscal year to the as-of date, not an arbitrary P&L period.", "",
                "| Component | Amount |", "|---|---:|"]
        for key, label in (("current_performance", "Current-year performance"), ("current_closing_transfers", "Current-year closing transfers"),
                           ("current_unclosed", "Current-year result (not closed)"), ("prior_performance", "Prior-years performance"),
                           ("prior_closing_transfers", "Prior-years closing transfers"), ("prior_unclosed", "Prior-years result (not closed)")):
            if key in bridge:
                out.append(f"| {label} | {money(bridge.get(key), env)} |")
        out.append("")

    policy = load_policy()
    assets_current = group_total(env, "asset", policy["current_asset_subtypes"])
    liabilities_current = group_total(env, "liability", policy["current_liability_subtypes"])
    inventory = group_total(env, "asset", policy["inventory_subtypes"])
    quick_assets = None if assets_current is None or inventory is None else assets_current - inventory
    current_ratio = ratio(assets_current, liabilities_current)
    quick_ratio = ratio(quick_assets, liabilities_current)
    debt_to_equity = ratio(liabilities, equity) if env["quality"]["status"] == "complete" else None
    bands = policy.get("bands", {})
    out += ["## Ratios", "", policy_note(policy), "", "| Ratio | Value | Example band |", "|---|---:|---|",
            f"| Current ratio | {current_ratio if current_ratio is not None else UNAVAILABLE} | {assess(current_ratio, bands.get('current_ratio'))} |",
            f"| Quick ratio | {quick_ratio if quick_ratio is not None else UNAVAILABLE} | {assess(quick_ratio, bands.get('quick_ratio'))} |",
            f"| Liabilities to equity | {debt_to_equity if debt_to_equity is not None else UNAVAILABLE} | {assess(debt_to_equity, bands.get('debt_to_equity'))} |",
            ""]
    return "\n".join(out + footer())


def main():
    run_cli("Format a balance sheet from report_contract 1", build_report)


if __name__ == "__main__":
    main()
