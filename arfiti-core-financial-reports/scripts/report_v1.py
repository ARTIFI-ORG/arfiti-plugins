"""Read and present the server's exact report contract (report_v1).

The formatters in this plugin are presentation only. The server report
(generate_report(..., {"report_contract": 1})) already returns every amount,
total, classification, reconciliation verdict, completeness status, coverage
and currency precision. This module reads that envelope and renders it as
returned:

- money is the server's exact decimal string; null is "Unavailable", never 0;
- totals come from the server's full-selection totals, never from summing rows;
- quality, every evidence gap (warnings included), coverage and dates are shown;
- a reconciliation verdict is the server's, never this plugin's arithmetic.

Anything the plugin adds on top (ratios, days outstanding, collection steps,
thresholds) is labelled as plugin analysis and reads its policy from
ratio_policy.json, which a firm edits for its own practice.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

POLICY_FILE = Path(__file__).with_name("ratio_policy.json")
UNAVAILABLE = "Unavailable"


class ReportInputError(ValueError):
    """The input is not a report_v1 envelope this formatter can present."""


def unwrap(obj, field: str = "report") -> dict:
    """Return the report_v1 envelope from a generate_report result or a bare envelope."""
    if not isinstance(obj, dict):
        raise ReportInputError(f"REPORT_CONTRACT_REQUIRED: {field} must be a JSON object")
    if obj.get("success") is False:
        raise ReportInputError(f"REPORT_REFUSED: {field}: {obj.get('code') or obj.get('error')}")
    if isinstance(obj.get("report_v1"), dict):
        obj = obj["report_v1"]
    if obj.get("contract_version") != 1:
        raise ReportInputError(
            f"REPORT_CONTRACT_REQUIRED: {field} is not a report_v1 envelope. "
            'Call generate_report with "report_contract": 1 and pass its result unchanged.')
    return obj


def load(obj, report_types, field: str = "report") -> dict:
    """Validate the envelope fields every formatter relies on."""
    env = unwrap(obj, field)
    if isinstance(report_types, str):
        report_types = (report_types,)
    if env.get("report_type") not in report_types:
        raise ReportInputError(
            f"REPORT_TYPE_MISMATCH: {field} is {env.get('report_type')!r}, expected {' or '.join(report_types)}")
    currency = env.get("currency")
    if not isinstance(currency, dict) or not currency.get("code"):
        raise ReportInputError(f"REPORT_CURRENCY_MISSING: {field} has no functional currency")
    places = currency.get("decimal_places")
    if type(places) is not int or places < 0:
        raise ReportInputError(f"REPORT_CURRENCY_PRECISION_MISSING: {field} has no decimal_places")
    quality = env.get("quality")
    if not isinstance(quality, dict) or quality.get("status") not in ("complete", "incomplete"):
        raise ReportInputError(f"REPORT_QUALITY_MISSING: {field} has no quality status")
    for key, kind in (("rows", list), ("totals", dict), ("coverage", dict), ("dates", dict)):
        if not isinstance(env.get(key), kind):
            raise ReportInputError(f"REPORT_SHAPE_INVALID: {field}.{key} is missing or malformed")
    return env


def same_basis(envs: dict) -> None:
    """Refuse to combine reports in different currencies or for different entities."""
    codes = {name: e["currency"]["code"] for name, e in envs.items()}
    if len(set(codes.values())) > 1:
        raise ReportInputError(f"REPORT_CURRENCY_MISMATCH: {codes}")
    scopes = {name: tuple(e.get("scope", {}).get("entity_ids") or ()) for name, e in envs.items()}
    if len(set(scopes.values())) > 1:
        raise ReportInputError(f"REPORT_SCOPE_MISMATCH: {scopes}")


def dimension_selection(env: dict):
    """The dimension selection the server applied (scope.filters.dimension_filter), or None."""
    selection = (env.get("scope", {}).get("filters") or {}).get("dimension_filter") or {}
    return selection if selection.get("conditions") else None


def require_unfiltered(envs: dict) -> None:
    """Refuse a dimension-selected report where entity-wide figures are combined or labelled."""
    filtered = [name for name, env in envs.items() if dimension_selection(env)]
    if filtered:
        raise ReportInputError(f"REPORT_SELECTION_MISMATCH: {', '.join(filtered)} carries a dimension_filter; "
                               "request it without a dimension selection")


def dec(value):
    """Exact Decimal for a server money string, or None when unavailable."""
    if value is None:
        return None
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ReportInputError(f"REPORT_MONEY_INVALID: {value!r}") from exc
    if not amount.is_finite():
        raise ReportInputError(f"REPORT_MONEY_INVALID: {value!r}")
    return amount


def money(value, env: dict) -> str:
    """The server amount with thousands separators, at least the currency's precision.

    Never rounds: a value with more decimals than the currency keeps them.
    """
    amount = dec(value)
    if amount is None:
        return UNAVAILABLE
    places = env["currency"]["decimal_places"]
    exponent = -amount.as_tuple().exponent if amount.as_tuple().exponent < 0 else 0
    text = f"{abs(amount):,.{max(places, exponent)}f}"
    return f"-{text}" if amount < 0 else text


def ratio(numerator, denominator, places: int = 2):
    """numerator / denominator, or None when either is unavailable or the denominator is 0."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return (numerator / denominator).quantize(Decimal(1).scaleb(-places))


def esc(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def period_days(env: dict):
    """Days in the report's effective period, both boundaries included, or None."""
    eff = env.get("dates", {}).get("effective", {}) or {}
    try:
        start, end = date.fromisoformat(eff["from"]), date.fromisoformat(eff["to"])
    except (KeyError, TypeError, ValueError):
        return None
    return (end - start).days + 1


def describe_dates(env: dict) -> str:
    dates = env.get("dates", {})
    eff = dates.get("effective") or {}
    req = dates.get("requested") or {}
    if eff.get("as_of"):
        text = f"As of {eff['as_of']}"
        if req.get("as_of") and req.get("as_of") != eff.get("as_of"):
            text += f" (requested {req['as_of']})"
    else:
        text = f"{eff.get('from') or '?'} to {eff.get('to') or '?'}"
        if (req.get("from"), req.get("to")) != (eff.get("from"), eff.get("to")) and req:
            text += f" (requested {req.get('from') or '?'} to {req.get('to') or '?'})"
    if dates.get("adjustment_reason"):
        text += f"; adjusted: {dates['adjustment_reason']}"
    return text


def header(title: str, env: dict, entity_name: str | None) -> list:
    dates = env.get("dates", {})
    cur = env["currency"]
    entity = entity_name or "Entity " + ", ".join(str(e) for e in env.get("scope", {}).get("entity_ids") or ["?"])
    return [f"# {title}", "",
            f"**{esc(entity)}** | {esc(describe_dates(env))} | Currency: {esc(cur['code'])} ({esc(cur.get('basis', 'functional'))})",
            f"Business date {esc(dates.get('business_date') or '?')}, timezone {esc(dates.get('timezone') or '?')}"
            f" ({esc(dates.get('timezone_source') or 'source not stated')})", ""]


def evidence(env: dict, label: str | None = None) -> list:
    """Quality, every evidence gap and delivery coverage, as the server reported them."""
    out = []
    prefix = f"{label}: " if label else ""
    quality = env["quality"]
    if quality["status"] == "complete":
        out.append(f"{prefix}Report quality: complete.")
    else:
        out.append(f"{prefix}**Report quality: incomplete.** Unavailable amounts are shown as {UNAVAILABLE}; "
                   "no total, verdict or ratio is inferred from them.")
    for gap in quality.get("evidence_gaps") or []:
        severity = "Blocking" if gap.get("severity") == "blocking" else "Warning"
        refs = gap.get("sample_refs") or []
        ref_text = f" Examples: {', '.join(esc(r.get('kind', '') + ' ' + str(r.get('id', ''))) for r in refs[:5])}." if refs else ""
        out.append(f"- **{severity}** ({esc(gap.get('code') or 'gap')}): {esc(gap.get('message') or '')}{ref_text}")
    cov = env["coverage"]
    if cov.get("truncated") or cov.get("has_more"):
        out.append(f"- **Partial delivery:** {cov.get('returned_count', '?')} of {cov.get('line_count', '?')} "
                   f"{esc(cov.get('row_unit') or 'rows')} rows are shown. Totals cover the full selection "
                   f"({esc(cov.get('totals_scope') or 'scope not stated')}); request the next page with cursor "
                   f"`{esc(cov.get('next_cursor') or '?')}` before presenting row detail as complete.")
    elif cov.get("totals_scope") not in (None, "full_selection"):
        out.append(f"- Totals scope: {esc(cov.get('totals_scope'))} (not the full selection).")
    out.append("")
    return out


def missing_row(env: dict) -> str:
    """What to show for a row absent from a comparison: absent, or possibly on an undelivered page."""
    cov = env.get("coverage") or {}
    return "Not in delivered page" if cov.get("truncated") or cov.get("has_more") else "—"


def money_totals(totals: dict) -> list:
    """Keys of totals that hold a money value (string or null); other scalars and lists are skipped."""
    keys = []
    for key, value in totals.items():
        if value is None:
            keys.append(key)
        elif isinstance(value, str):
            try:
                dec(value)
            except ReportInputError:
                continue
            keys.append(key)
    return keys


def verdict(recon, env: dict) -> str:
    """The server's reconciliation verdict; never a pass this plugin computed itself."""
    if not isinstance(recon, dict):
        return f"{UNAVAILABLE} (the server returned no reconciliation)"
    status = recon.get("status")
    if status == "tied" and env["quality"]["status"] == "complete":
        return f"Tied (server reconciliation, tolerance {money(recon.get('tolerance'), env)})"
    if status == "tied":
        return "Tied on the amounts available, but the report is incomplete: not certified"
    if status == "difference":
        return f"**Difference {money(recon.get('difference'), env)}** (server reconciliation)"
    return f"{UNAVAILABLE}: insufficient evidence to prove agreement"


def load_policy() -> dict:
    with open(POLICY_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def policy_note(policy: dict) -> str:
    return (f"*Plugin analysis, not part of the server report. Classification and bands are example policy "
            f"from {POLICY_FILE.name}; edit it for the firm's practice.*")


def assess(value, band: dict | None) -> str:
    """Compare a ratio with the example band from the policy file, labelled as such."""
    if value is None:
        return UNAVAILABLE
    if not band:
        return ""
    low, high = dec(band.get("low")), dec(band.get("high"))
    if low is not None and high is not None:
        text = f"{low}–{high}"
    elif low is not None:
        text = f"at least {low}"
    elif high is not None:
        text = f"at most {high}"
    else:
        return ""
    if low is not None and value < low:
        return f"Below example band ({text})"
    if high is not None and value > high:
        return f"Above example band ({text})"
    return f"Within example band ({text})"


def group_total(env: dict, section: str, subtypes) -> object:
    """Sum of the server's per-subtype balance sheet totals for the listed subtypes.

    Returns None when the report carries no subtype groups, any matching group
    is unavailable or the report is incomplete, so a ratio is never built on a
    missing amount. Groups present but none matching is a real zero.
    """
    groups = env["totals"].get("groups")
    if not isinstance(groups, list):
        return None
    total = Decimal(0)
    for group in groups:
        if group.get("section") == section and group.get("subtype") in subtypes:
            amount = dec(group.get("total"))
            if amount is None:
                return None
            total += amount
    if env["quality"]["status"] != "complete":
        return None
    return total


def footer() -> list:
    return ["---", "*Generated by arfiti-core-financial-reports from the server report (report_contract 1).*"]


def run_cli(description: str, build, inputs=("input",)):
    """Shared CLI: read JSON input(s), build markdown, write it; refusals exit 2."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--input", required=True, help="JSON file: the generate_report result (report_contract 1)")
    parser.add_argument("--output", required=True, help="Output markdown file")
    parser.add_argument("--entity-name", help="Entity name for the heading")
    parser.add_argument("--income-statement", help="Optional income_statement result for days outstanding (aging only)")
    args = parser.parse_args()
    try:
        with open(args.input, encoding="utf-8") as fh:
            data = json.load(fh)
        extra = None
        if args.income_statement:
            with open(args.income_statement, encoding="utf-8") as fh:
                extra = json.load(fh)
        report = build(data, entity_name=args.entity_name, income_statement=extra)
    except ReportInputError as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        sys.exit(2)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(report + "\n", encoding="utf-8")
    print(f"Written to {args.output}")
