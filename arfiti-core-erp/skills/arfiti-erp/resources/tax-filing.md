# Tax Filing — Universal Resource

This resource explains how to file periodic tax returns (VAT, payroll, withholding, etc.) using the universal `tax_return` workflow. Country-specific forms (Estonia TSD, UK RTI, US 1099, etc.) are produced by country plugins; this guide covers the **shared** pieces that work the same regardless of country.

## When to use

A user asks to file a tax return, generate a TSD/KMD/RTI/1099/etc., view recently filed returns, mark a return as filed, or check filing deadlines.

## Discover what forms this country files

```python
# What forms does this org's country file with their tax authority?
query("tax_filing_form", filters={"country_code": "<EE|US|GB|...>"})

# What payment classifications are available (slug ↔ external code)?
query("payment_classification", filters={"country_code": "<...>", "is_active": true})
```

If a country has **zero** rows, the catalog hasn't been seeded for this org. This is common for orgs onboarded before the `setup_tax_filing_forms` task existed. **You can fix it yourself — it is NOT a backend-only / separate-engagement task.** See "Register a missing form" below. Only escalate if the country has no template at all (no `tax_filing_forms` entries in `mcp-server/src/data/onboarding/{cc}.json`), which means the country plugin genuinely doesn't exist yet.

## Register a missing form (self-service)

The `tax_filing_forms` catalog is writable through the standard `submit()` gateway — no deploy, no admin action. Register each form the country files:

```python
submit("tax_filing_form", "create", json.dumps({
    "country_code": "EE",                 # ISO 3166-1 alpha-2 (required)
    "form_code": "TSD",                   # the return_type code (required)
    "tax_authority_id": 91,               # from query("tax_authority")
    "form_name": "Tulu- ja sotsiaalmaksudeklaratsioon",
    "filing_frequency": "monthly",        # monthly|quarterly|semi_annual|annual|adhoc
    "due_day_of_period_end": 10,
    "metadata": { "filing_portal": "https://maasikas.emta.ee" }
}))
```

The canonical seed values for each country live in `mcp-server/src/data/onboarding/{cc}.json` under `tax_filing_forms` — copy `form_code`, `form_name`, `frequency`, `due_day`, and `metadata` from there, and resolve `tax_authority_code` → `tax_authority_id` via `query("tax_authority")`. Forms are unique per `(country_code, form_code)`; re-registering an existing form errors. Also `update` / `delete` (soft-delete if referenced by a `tax_return`).

After registering, the `tax_return` create will accept that `return_type`. New orgs get this automatically — `setup_tax_filing_forms` is a tier-2 onboarding task that seeds the catalog from the country JSON.

## Read filing-relevant data

Per-employee filing attributes live in `master_employees.metadata.tax_filing.{...}`:

```python
emp = get_entity("employee", id=N)
tax_filing = (emp.get("metadata") or {}).get("tax_filing") or {}
# residency, country_of_residence, is_pensioner, basic_exemption_code,
# pension_fund_id, tax_treaty_country, treaty_rate_override
```

Per-vendor (for legal-person withholding):

```python
vendor = get_entity("vendor", id=N)
tax_filing = (vendor.get("metadata") or {}).get("tax_filing") or {}
# is_withholding_subject, withholding_classification_slug, tax_residency, country_of_residence
```

Per-payment classification (the type of payment — drives form codes):

```python
# Read directly off the comp record (real column, indexed)
comp = query("employee_compensation", filters={"employee_id": N, "is_active": true})
slug = comp["results"][0]["payment_classification_slug"]   # e.g. "salary_wage", "board_fee"

# Resolve slug → country external code at filing time
classifications = query("payment_classification", filters={"country_code": "EE", "slug": slug})
external_code = classifications["results"][0]["external_code"]   # e.g. "10" for EE c1020
```

## Submit a return (universal — same call regardless of country)

```python
submit("tax_return", "create", json.dumps({
    "legal_entity_id": <id>,
    "return_type": "<form_code>",        # must match a row in tax_filing_forms (TSD, INF1, KMD, 1099-NEC, P11D, RTI, ...)
    "tax_authority_id": <id>,            # from master_tax_authorities
    "return_data": { ... }               # form-specific payload — country plugin defines the shape
}))
```

The validator checks `return_type` against `tax_filing_forms` for the country. If unknown, you get: *"return_type 'X' is not a registered tax filing form for country 'EE'. Registered forms: TSD, INF1, KMD."*

## Mark as filed after upload

```python
submit("tax_return", "file", json.dumps({
    "return_id": <id>,
    "confirmation_number": "<from portal>",
    "filing_date": "YYYY-MM-DD"
}))
```

**The return must already be linked to a reporting period of the same tax
authority**, and `filing_date` must not precede that period's `period_end`.
Filing turns a working draft into a compliance record, so that is where the
facts are checked; drafts themselves stay free-form. If the return has no
period, link one with `tax_return.update(reporting_period_id=...)` — or create
it with `tax_reporting_period.create` (note: the object type differs from
`tax_period.lock`).

Periods exist **per tax authority**, because filing calendars differ: in Estonia
the KMD goes to the VAT authority by the 20th and the TSD to the payroll
authority by the 10th. Linking a payroll return to a VAT period would put the
wrong deadline on the record, so it is refused.

Late filing is permitted and simply flagged (`late_filing`, `days_late`) — the
ERP has to be able to record a filing that really happened.

> **Always pass `filing_date` explicitly.** It defaults to *today*, so entering
> a filing after the fact silently records the wrong date.

## CoA-driven Annex routing (Estonia TSD Annex 5, UK P11D, etc.)

Some forms (like EE TSD Annex 5 for gifts/donations/entertainment) are driven by the **chart of accounts** — every transaction line that touches a tagged account counts. To find tagged accounts:

```python
accounts = query("account", filters={"legal_entity_id": <id>})
for a in accounts["results"]:
    cats = (a.get("metadata") or {}).get("filing_categories") or []
    # cats is a list like [{"form": "TSD", "annex": "5", "code": "4040"}, ...]
```

Then aggregate transaction lines on those accounts:

```python
query(
    "transaction_line", group_by=["account_number", "vendor_id"],
    aggregates={"debit": "sum", "credit": "sum"},
    filters={
        "legal_entity_id": <id>,
        "account_number": [<tagged accounts>]   # a list means "any of"
    },
    date_filters={"transaction_date": {"from": period_start, "to": period_end}}
)
```

## When the calc lives outside core

Tax-filing **calculation and XML generation** live in country plugins (e.g. `arfiti-ee-payroll-calculator`). If the user asks "generate the TSD" and you're not running the country plugin's command, route them: *"Run /generate-tsd from the arfiti-ee-payroll-calculator plugin — it owns the e-MTA XML format."*

For the architecture itself, see `docs/GUIDES/GUIDE_TAX_FILING_PLUGINS.md`.

## Dated tax evidence and VAT control reconciliation

VAT reports and filing readers use the canonical tax-line view. Effective VAT
registration intervals govern deductible input; an active registration today is
not evidence of registration on the historical transaction date. Review
`registration_exceptions` rather than silently claiming pre-registration input tax.
Zero-rated sales remain taxable-turnover evidence even when their tax amount is zero.

AP credits reduce input tax and reversals contribute on their own posting dates;
originals remain in earlier periods. Use booked functional currency and preserve
source line rounding. Missing conversion evidence must be investigated rather than
replaced by today's FX rate. A filed return alone does not prove the VAT control
balance: the close gate compares it with a retained period-end authority account
statement covering the configured VAT control accounts.

### Legacy currency evidence and reverse-charge totals

A legacy document with a missing header functional amount can use rate 1 only
when its document currency equals its recorded functional currency (or the entity's
functional currency when that field is absent). Foreign-currency evidence without
a recorded conversion basis remains uncertified; never substitute today's FX.

Reverse-charge tax contributes input and output rows. Keep both directions for
VAT/worksheet presentation, but count its base once in an undirected taxable total.
Sales-tax collected totals count output tax rather than adding input and output.


### Assistant help in Admin (QA branch)

The connectors list, connector details and tax returns page use the shared
assistant chooser. Choose ChatGPT or Claude, or copy the page-specific question
to another connected assistant. Opening help does not connect an assistant,
change the active company, run a sync or file a return. Connector details retain
the selected connector’s provider and name in the question. This change is in
the draft QA branch; deployment has not been verified.


## Close evidence update (b1, awaiting deployment)

Filing evidence matches a return’s own period or a reporting period for the same entity and authority. Candidate forms are selected by country or overlapping authority registration. An unfiled selected form without an applicability rule is advisory not_determined, not “missing” or “not expected”. Quarterly selection still assumes calendar quarters and says so; this is a disclosed existing selection limitation, not a universal tax rule.
