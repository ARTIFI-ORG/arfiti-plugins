#!/usr/bin/env python3
"""Present a one-page financial summary from server reports (report_contract 1).

Usage:
    python3 format_financial_summary.py --input summary.json --output report.md [--entity-name NAME]

Input: a JSON object holding three generate_report results, each requested with
"report_contract": 1 and saved unchanged:

    {"income_statement": <result for start_date..end_date>,
     "balance_sheet": <result as_of end_date>,
     "cash_flow_statement": <result for start_date..end_date>}   # optional

All figures are the server's. Ratios and days outstanding are plugin analysis:
days use the income statement period's actual length, classification and bands
come from ratio_policy.json.
"""
from decimal import Decimal

from report_v1 import (UNAVAILABLE, ReportInputError, assess, dec, esc, evidence, footer, group_total, header,
                       load, load_policy, money, period_days, policy_note, ratio, require_unfiltered, run_cli,
                       same_basis, verdict)


def build_report(data, entity_name=None, **_):
    if not isinstance(data, dict) or "income_statement" not in data or "balance_sheet" not in data:
        raise ReportInputError("REPORT_SHAPE_INVALID: pass income_statement and balance_sheet results "
                               "(cash_flow_statement optional)")
    pnl = load(data["income_statement"], "income_statement", "income_statement")
    bs = load(data["balance_sheet"], "balance_sheet", "balance_sheet")
    reports = {"income_statement": pnl, "balance_sheet": bs}
    if data.get("cash_flow_statement") is not None:
        reports["cash_flow_statement"] = load(data["cash_flow_statement"], "cash_flow_statement", "cash_flow_statement")
    same_basis(reports)
    require_unfiltered(reports)
    cf = reports.get("cash_flow_statement")
    if cf:
        window = lambda e: (e["dates"].get("effective", {}).get("from"), e["dates"].get("effective", {}).get("to"))
        if window(cf) != window(pnl):
            raise ReportInputError(f"REPORT_PERIOD_MISMATCH: income statement {window(pnl)}, "
                                   f"cash flow {window(cf)}")

    out = header("Financial Summary", pnl, entity_name)
    period_end = pnl["dates"].get("effective", {}).get("to")
    as_of = bs["dates"].get("effective", {}).get("as_of")
    if period_end != as_of:
        out += [f"**The balance sheet date ({esc(as_of)}) is not the period end ({esc(period_end)}).** "
                "Balance figures and period figures do not describe the same date.", ""]
    for name, env in reports.items():
        out += evidence(env, name.replace("_", " ").capitalize())

    t, b = pnl["totals"], bs["totals"]
    out += ["## Performance (income statement)", "", "| Figure | Amount |", "|---|---:|"]
    for key, label in (("revenue", "Revenue"), ("cogs", "Cost of sales"), ("gross_profit", "Gross profit"),
                       ("operating_expenses", "Operating expenses"), ("operating_profit", "Operating profit"),
                       ("net_income", "Net income")):
        out.append(f"| {label} | {money(t.get(key), pnl)} |")
    out += ["", "## Position (balance sheet)", "", "| Figure | Amount |", "|---|---:|"]
    for key, label in (("assets", "Total assets"), ("liabilities", "Total liabilities"), ("equity", "Total equity")):
        out.append(f"| {label} | {money(b.get(key), bs)} |")
    out += [f"| Assets = liabilities + equity | {verdict(bs.get('details', {}).get('reconciliation'), bs)} |", ""]

    if cf:
        c = cf["totals"]
        out += ["## Cash (cash flow statement)", "",
                f"Method: {esc(cf.get('details', {}).get('method') or 'not stated')}.", "",
                "| Figure | Amount |", "|---|---:|"]
        for key, label in (("opening_cash", "Opening cash"), ("operating", "Operating"), ("investing", "Investing"),
                           ("financing", "Financing"), ("fx_effect_on_cash", "FX effect on cash"),
                           ("other_cash_balance_adjustments", "Other balance adjustments"), ("closing_cash", "Closing cash")):
            out.append(f"| {label} | {money(c.get(key), cf)} |")
        out += [f"| Opening + flows + FX + adjustments = closing | {verdict(cf.get('details', {}).get('reconciliation'), cf)} |", ""]

    policy = load_policy()
    bands = policy.get("bands", {})
    revenue, cogs = dec(t.get("revenue")), dec(t.get("cogs"))
    current_assets = group_total(bs, "asset", policy["current_asset_subtypes"])
    current_liabilities = group_total(bs, "liability", policy["current_liability_subtypes"])
    inventory = group_total(bs, "asset", policy["inventory_subtypes"])
    receivables = group_total(bs, "asset", policy["receivable_subtypes"])
    payables = group_total(bs, "liability", policy["payable_subtypes"])
    days = period_days(pnl)
    complete = pnl["quality"]["status"] == "complete" and bs["quality"]["status"] == "complete"

    def days_outstanding(balance, basis):
        # A zero balance is a real 0 days; a negative balance (a debit payables
        # balance) or a non-positive basis would give meaningless days.
        if not complete or balance is None or basis is None or not days or balance < 0 or basis <= 0:
            return None
        return (balance / basis * days).quantize(Decimal("1"))

    def pct(key):
        value = ratio(dec(t.get(key)), revenue, 4)
        return UNAVAILABLE if value is None else f"{value * 100:.1f}%"

    current_ratio = ratio(current_assets, current_liabilities)
    quick_ratio = ratio(None if current_assets is None or inventory is None else current_assets - inventory,
                        current_liabilities)
    leverage = ratio(dec(b.get("liabilities")), dec(b.get("equity"))) if bs["quality"]["status"] == "complete" else None
    show = lambda v, unit="": UNAVAILABLE if v is None else f"{v}{unit}"
    out += ["## Ratios", "", policy_note(policy),
            f"Days outstanding use the closing balance and the {days or '?'} days of the income statement period "
            "(an approximation, not an average balance).", "",
            "| Area | Ratio | Value | Example band |", "|---|---|---:|---|",
            f"| Profitability | Gross margin | {pct('gross_profit')} | |",
            f"| Profitability | Operating margin | {pct('operating_profit')} | |",
            f"| Profitability | Net margin | {pct('net_income')} | |",
            f"| Liquidity | Current ratio | {show(current_ratio)} | {assess(current_ratio, bands.get('current_ratio'))} |",
            f"| Liquidity | Quick ratio | {show(quick_ratio)} | {assess(quick_ratio, bands.get('quick_ratio'))} |",
            f"| Leverage | Liabilities to equity | {show(leverage)} | {assess(leverage, bands.get('debt_to_equity'))} |",
            f"| Efficiency | DSO | {show(days_outstanding(receivables, revenue), ' days')} | |",
            f"| Efficiency | DPO | {show(days_outstanding(payables, cogs), ' days')} | |",
            f"| Efficiency | Inventory days | {show(days_outstanding(inventory, cogs), ' days')} | |", ""]
    return "\n".join(out + footer())


def main():
    run_cli("Format a financial summary from report_contract 1 results", build_report)


if __name__ == "__main__":
    main()
