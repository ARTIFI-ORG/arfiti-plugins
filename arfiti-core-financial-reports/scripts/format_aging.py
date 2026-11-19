#!/usr/bin/env python3
"""Present AR or AP aging from the server report (report_contract 1).

Usage:
    python3 format_aging.py --input ar_aging.json --output report.md [--entity-name NAME]
                            [--income-statement income_statement.json]

Input: the result of
    generate_report("ar_aging" | "ap_aging", {"legal_entity_id": ID, "as_of_date": "YYYY-MM-DD",
                                              "report_contract": 1})
saved unchanged. Buckets, totals, overdue, certification and the control-account
tie-out are the server's; amounts keep their sign, so credits and unapplied
amounts stay visible. Overdue means more than 0 days past due, as the server
counts it. With --income-statement (a report_contract 1 income statement whose
period ends on the aging date) the plugin adds days outstanding over that
period's actual length. Follow-up wording is example policy from
ratio_policy.json; nothing here contacts anyone or pays anything.
"""
from datetime import date, timedelta
from decimal import Decimal

from report_v1 import (UNAVAILABLE, ReportInputError, dec, esc, evidence, footer, header, load, load_policy,
                       money, period_days, policy_note, require_unfiltered, run_cli, same_basis)

BUCKETS = (("current", "Current"), ("days_1_30", "1–30"), ("days_31_60", "31–60"),
           ("days_61_90", "61–90"), ("days_over_90", "90+"))
PAST_DUE = ("days_1_30", "days_31_60", "days_61_90", "days_over_90")


def overdue(row):
    """Sum of the past-due buckets, or None when any of them is unavailable."""
    amounts = [dec(row.get(key)) for key in PAST_DUE]
    return None if any(a is None for a in amounts) else sum(amounts, Decimal(0))


def build_report(data, entity_name=None, income_statement=None, **_):
    env = load(data, ("ar_aging", "ap_aging"))
    is_ar = env["report_type"] == "ar_aging"
    party = "Customer" if is_ar else "Vendor"
    details = env.get("details", {})
    totals = env["totals"]

    out = header("Accounts Receivable Aging" if is_ar else "Accounts Payable Aging", env, entity_name)
    out += evidence(env)

    tie = details.get("control_tie_out") or {}
    certified = details.get("certified") is True
    out += ["## Certification", "",
            f"- Certified against the control account: {'yes' if certified else '**no**'}",
            f"- Control tie-out: {esc(tie.get('status') or UNAVAILABLE)}; control balance "
            f"{money(tie.get('control_balance'), env)}, difference {money(tie.get('difference'), env)}",
            "- Amounts are the server's signed figures in functional currency; "
            "a party whose total has the opposite sign to a non-zero overall total is a credit or unapplied amount.", ""]

    out += ["## Aging by party", "",
            f"| {party} | " + " | ".join(t for _, t in BUCKETS) + " | Total |",
            "|---|" + "---:|" * (len(BUCKETS) + 1)]
    for row in env["rows"]:
        name = row.get("party_name") or f"No {party.lower()} on the document"
        out.append(f"| {esc(name)} | " + " | ".join(money(row.get(k), env) for k, _ in BUCKETS)
                   + f" | {money(row.get('total'), env)} |")
    out.append("| **Total** | " + " | ".join(f"**{money(totals.get(k), env)}**" for k, _ in BUCKETS)
               + f" | **{money(totals.get('total'), env)}** |")
    out.append("")

    total_overdue = dec(totals["overdue"]) if "overdue" in totals else overdue(totals)
    total = dec(totals.get("total"))
    share = None if total_overdue is None or not total else (total_overdue / total * 100).quantize(Decimal("0.1"))
    out += ["## Key figures", "", "| Figure | Value |", "|---|---:|",
            f"| Total outstanding | {money(totals.get('total'), env)} |",
            f"| Overdue (1+ days past due) | {money(None if total_overdue is None else str(total_overdue), env)} |",
            f"| Overdue share of total | {UNAVAILABLE if share is None else f'{share}%'} |",
            f"| 90+ days | {money(totals.get('days_over_90'), env)} |"]

    if income_statement is not None:
        pnl = load(income_statement, "income_statement", "income statement")
        same_basis({"aging": env, "income statement": pnl})
        require_unfiltered({"aging": env, "income statement": pnl})
        aging_date = env["dates"].get("effective", {}).get("as_of")
        if pnl["dates"].get("effective", {}).get("to") != aging_date:
            raise ReportInputError(f"REPORT_PERIOD_MISMATCH: the income statement must end on the aging date "
                                   f"{aging_date}, not {pnl['dates'].get('effective', {}).get('to')}")
        days = period_days(pnl)
        basis = dec(pnl["totals"].get("revenue" if is_ar else "cogs"))
        value = None
        if days and basis and total is not None and env["quality"]["status"] == "complete" \
                and pnl["quality"]["status"] == "complete":
            # The balance's size, whichever sign the control account carries.
            value = (abs(total) / basis * days).quantize(Decimal("1"))
        eff = pnl["dates"].get("effective", {})
        out.append(f"| {'Days sales outstanding' if is_ar else 'Days payables outstanding'} | "
                   f"{UNAVAILABLE if value is None else f'{value} days'} |")
        out += ["", f"*Plugin analysis: closing balance ÷ {'revenue' if is_ar else 'cost of sales'} for "
                f"{eff.get('from') or '?'} to {eff.get('to') or '?'} × {days or '?'} days in that period. "
                "An approximation on the closing balance, not an average.*", ""]
        out += evidence(pnl, "Income statement used for days outstanding")
    out.append("")

    as_of = env["dates"].get("effective", {}).get("as_of")
    documents = details.get("documents") or []
    if not is_ar and as_of and documents:
        today = date.fromisoformat(as_of)
        cov = env["coverage"]
        partial = cov.get("truncated") or cov.get("has_more") or env["quality"]["status"] != "complete"
        out += ["## Coming due (open documents, cumulative from the aging date)", ""]
        if partial:
            out += ["Not shown: the aging is incomplete or only partly delivered, so the open documents "
                    "may not all be present.", ""]
        out += ["| Window | Balance due |", "|---|---:|"]
        for window in (7, 14, 30):
            amounts, missing = Decimal(0), False
            for doc in documents:
                due = doc.get("due_date")
                if due and today < date.fromisoformat(due) <= today + timedelta(days=window):
                    amount = dec(doc.get("balance_due"))
                    missing = missing or amount is None
                    amounts += amount or 0
            out.append(f"| Within {window} days | {UNAVAILABLE if missing or partial else money(str(amounts), env)} |")
        out.append("")

    policy = load_policy()
    out += ["## Follow-up" if is_ar else "## Overdue vendors", "", policy_note(policy), ""]
    if not certified:
        out += ["The aging is not certified, so follow-up lists are indicative only.", ""]
    # A credit is a party balance with the opposite sign to the report total, so
    # this holds whichever sign the control account's booked balance carries.
    # When the total nets to zero or is unavailable no sign can be trusted, so the
    # negative and positive balances are listed as two groups instead.
    credits = [r for r in env["rows"]
               if total and dec(r.get("total")) is not None and dec(r.get("total")) * total < 0]
    mixed = []
    if not total:
        negative = [r for r in env["rows"] if (dec(r.get("total")) or 0) < 0]
        positive = [r for r in env["rows"] if (dec(r.get("total")) or 0) > 0]
        if negative and positive:
            mixed = [("negative", negative), ("positive", positive)]
    if is_ar:
        steps = policy.get("receivable_follow_up", {})
        out += [f"| {party} | Oldest past-due bucket | Amount | Example follow-up |", "|---|---|---:|---|"]
        for row in env["rows"]:
            if any(dec(row.get(key)) is None for key in PAST_DUE):
                out.append(f"| {esc(row.get('party_name') or 'No customer on the document')} | "
                           f"{UNAVAILABLE} | {UNAVAILABLE} | Review: a past-due amount is unavailable |")
                continue
            for key in reversed(PAST_DUE):
                amount = dec(row.get(key))
                if amount > 0:
                    out.append(f"| {esc(row.get('party_name') or 'No customer on the document')} | "
                               f"{dict(BUCKETS)[key]} | {money(row.get(key), env)} | {esc(steps.get(key, ''))} |")
                    break
    else:
        out += [f"| {party} | Overdue (1+ days) | Total |", "|---|---:|---:|"]
        for row in env["rows"]:
            amount = overdue(row)
            if amount is None or amount != 0:
                out.append(f"| {esc(row.get('party_name') or 'No vendor on the document')} | "
                           f"{money(None if amount is None else str(amount), env)} | {money(row.get('total'), env)} |")
        out += ["", "Whether and when to pay is the business's decision (terms, disputes, cash); "
                "this list does not schedule payments."]
    if credits:
        out += ["", f"Credit balances to review ({len(credits)}): "
                + ", ".join(f"{esc(r.get('party_name') or 'unnamed')} {money(r.get('total'), env)}" for r in credits)]
    if mixed:
        out += ["", "The total nets to zero or is unavailable, so credits cannot be told from amounts due by sign. "
                "Review both groups:"]
        for label, rows in mixed:
            out.append(f"- Parties with {label} balances ({len(rows)}): "
                       + ", ".join(f"{esc(r.get('party_name') or 'unnamed')} {money(r.get('total'), env)}" for r in rows))
    out.append("")
    return "\n".join(out + footer())


def main():
    run_cli("Format AR or AP aging from report_contract 1", build_report)


if __name__ == "__main__":
    main()
