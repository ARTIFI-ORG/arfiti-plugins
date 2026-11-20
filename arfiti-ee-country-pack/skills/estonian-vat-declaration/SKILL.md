---
name: estonian-vat-declaration
description: Prepares the monthly Estonian VAT return (KMD) in the official KMD2 format — pre-close validation gate, KMD2 machine CSV + XSD-validated XML with KMD INF annex, GL reconciliation, and file→lock workflow for e-MTA
---

## Trigger

Activate when the user mentions: VAT declaration, KMD, kaibemaksudeklaratsioon, monthly VAT, EMTA filing, VAT return, kaibemaks, or VAT for an Estonian legal entity.

## Prerequisites

Before starting, ask the user for:
1. **Legal entity ID** — which Estonian entity to prepare the declaration for
2. **Period** — month and year (e.g., January 2026)
3. **VAT accounting method** — whether the entity applies the special arrangements for
   cash accounting for VAT (kassapõhine, VAT Act § 44). Use what the entity's recorded
   VAT setup says; if nothing records it, ask. Never assume. It decides which KMD INF
   columns are filled (Step 5) and is passed to the generator as `cash_accounting`.

Then resolve the **filing form code** the return is saved under (Step 8). Core validates
`return_type` against the forms registered in `tax_filing_forms` for the tax authority's
country; it is not a free-text label:

```
get_entity("legal_entity", id=ID)                          # → country_code (EE)
query("tax_filing_form", filters={"country_code": "EE", "form_code": "KMD", "is_active": true})
```

Use the row whose `form_code` is `KMD` (form name "Käibedeklaratsioon"), and take its
`tax_authority_id` as the authority. The list returns only the display fields
(`id`, `country_code`, `form_code`, `form_name`, `tax_authority_id`,
`filing_frequency`, `due_day_of_period_end`, `is_active`); `metadata` is read only with
`get_entity("tax_filing_form", id=<id>)` and is not needed to choose the form. If no VAT return form is registered for the
entity's country, STOP before Step 8: tell the user the country setup has not
registered the KMD form (the `setup_tax_filing_forms` onboarding task, or
`/arfiti-core-country-setup:set-up-country`), and that the return can be prepared and
the files generated but not saved as a tax return until it is registered. Never fall
back to a generic `return_type` such as `vat_return`, and never pick a form registered
for another country.

## Mandatory Checkpoints

Before generating the return you MUST run the **pre-close validation gate** — the seven
checks in **references/validation-checklist.md**, each rated BLOCK or WARN. If any BLOCK
is open, STOP and do not generate. The individual checkpoints below feed that gate:

- **CP1**: All transactions for the period are posted (no drafts) — gate check 2
- **CP2**: All transaction lines have tax codes assigned — gate check 4
- **CP3**: KMD calculations balance and tie to the GL — gate checks 1, 5, 7
- **CP4**: KMD INF covers every partner whose invoices **without VAT** total at least
  €1,000.00 in the period (inclusive), and reconciles to the KMD — gate check 6
- **CP5**: EC Sales List reconciles with the KMD: VD goods = line 3.1.1, VD services = line 3.1 − 3.1.1 — gate check 7

## Workflow Steps

### Step 1: Discover & Classify Tax Codes

This step is CRITICAL. Do NOT hardcode tax code names. Always discover and classify dynamically.

1. Fetch the entity's active Estonian tax codes:
   ```
   query("tax_code", filters={"legal_entity_id": ID, "is_active": true})
   ```

2. For each tax code, apply the classification rules from **references/tax-codes-ee.md**:
   - Check `reporting_code_override` first (entity-level override takes priority)
   - Then classify by properties: `default_rate`, `is_reverse_charge`, `is_recoverable`, `tax_type`, `tax_scope`, `metadata`
   - Map each code to a KMD line using the decision tree in **references/kmd-form-structure.md**

3. Present the classification table to the user:
   ```
   | Tax Code | Name | Rate | Reverse Charge | → KMD Line |
   |----------|------|------|----------------|------------|
   | [code]   | [name] | [rate] | [yes/no]   | [line]     |
   ```

4. Ask the user to confirm the classification before proceeding.

### Step 2: Fetch Period Figures and Documents

A document belongs to the period by its ledger effect and date, **not** by whether it
has been paid. Settlement moves a posted invoice or bill from `posted` to `partial` or
`paid` (and some flows use `partially_paid` or `completed`); all of them still carry
the VAT. A `status: "posted"` filter alone drops every paid document from
the return.

**Ledger-effective statuses** — the set the canonical tax view `v_tax_lines` counts
(migration `601_canonical_tax_history.sql`), with `posted_at` set:

```
LEDGER_STATUSES = ["posted", "partial", "paid", "partially_paid", "completed", "approved", "reversed"]
```

Keep only posted rows. `approved` is in the list because the view counts it once
posted, but an `approved` document can also be one awaiting posting (it can still be
cancelled); the view excludes it then, and so must you. `posted_at` is not among the
fields `query("transaction")` returns, so filter on it instead: the date filter
`"posted_at": {"from": "1900-01-01"}` keeps only rows with a posting time (a NULL
`posted_at` never matches), as in the queries below.

`draft`, `void` and `cancelled` are not counted. A `reversed` original **stays** in its
own period; its reversal is a separate document dated on the reversal date that carries
the original's lines with the opposite sign. Count both, each in its own period — never
drop the original because it was later reversed.

1. **Box figures (authoritative source)** — the canonical tax lines:
   ```
   generate_report("vat_report", {"legal_entity_id": ID, "start_date": "YYYY-MM-01",
       "end_date": "YYYY-MM-DD"})
   ```
   It sums `v_tax_lines`: signed bases and VAT per tax name and rate, by direction
   (`output_vat_details`, `input_vat_details`), credit notes negative, tax-inclusive
   lines net of tax, reversals signed, ledger-effective statuses only. A reverse-charge
   purchase appears on both sides (self-assessed output and recoverable input). Map each
   row to its KMD line with the Step 1 classification. Where two tax codes share a tax
   name but feed different KMD lines, split that row with the document lines below.
   `registration_exceptions` lists deductible documents dated outside the entity's VAT
   registration; they are kept out of the totals and go to the person for review.
   Do not pass `country_code`: it filters on each tax code's own country and would drop
   codes with no or another country (generic exempt or 0 % codes, some reverse-charge
   codes).

2. **Documents** (for the KMD INF annex, the review lists and the split above), with
   lines:
   ```
   query("transaction", filters={
       "legal_entity_id": ID,
       "transaction_type": ["AR_INVOICE", "AR_CREDIT_MEMO"],
       "status": LEDGER_STATUSES
   }, date_filters={"transaction_date": {"from": "YYYY-MM-01", "to": "YYYY-MM-DD"},
                 "posted_at": {"from": "1900-01-01"}},
   include_lines=true)

   query("transaction", filters={
       "legal_entity_id": ID,
       "transaction_type": ["AP_INVOICE", "AP_CREDIT_MEMO"],
       "status": LEDGER_STATUSES
   }, date_filters={"transaction_date": {"from": "YYYY-MM-01", "to": "YYYY-MM-DD"},
                 "posted_at": {"from": "1900-01-01"}},
   include_lines=true)
   ```
   Then the reversals dated in the period (each negates the lines of the document it
   reverses, `reversal_of_id`):
   ```
   query("transaction", filters={"legal_entity_id": ID, "reversal_of_id": {"gt": 0},
       "status": LEDGER_STATUSES},
       date_filters={"transaction_date": {"from": "YYYY-MM-01", "to": "YYYY-MM-DD"},
                 "posted_at": {"from": "1900-01-01"}})
   ```
   And any other posted document with VAT lines (journals with a tax code):
   ```
   query("transaction", filters={"legal_entity_id": ID, "status": LEDGER_STATUSES},
       date_filters={"transaction_date": {"from": "YYYY-MM-01", "to": "YYYY-MM-DD"},
                 "posted_at": {"from": "1900-01-01"}},
       include_lines=true)
   ```
   Read every page. `include_lines` returns at most 500 lines across one response; when
   the response carries the `warnings` entry "Line items truncated…", lines are missing
   and an invoice's net would come out too low. Re-read with a smaller `limit` until no
   such warning appears, or read the affected invoices one by one with
   `get_entity("transaction", id=…)`. `get_entity` also stops at 500 lines per
   document, so an invoice with more than 500 lines cannot be read in full either way:
   give it to a person. Transaction type codes are matched exactly and stored in upper case
   (`AR_INVOICE`, not `ar_invoice`); a lower-case value returns no rows. The lists
   overlap (an invoice is in the first list and in the catch-all), so de-duplicate by
   `id` before rebuilding any total.

   Per document line, the net (tax base) is `line_amount − tax_amount` when the line
   `is_tax_inclusive`, otherwise `line_amount` — the same rule `v_tax_lines` applies.
   These are document-currency amounts. For a foreign-currency document convert to the
   entity's functional currency with the header's `exchange_rate` (document → functional
   rate, kept equal to `document_to_functional_rate` at posting): EUR amount = document
   amount × `exchange_rate`, rounded to cents per invoice. `vat_report` sums the
   functional amounts, and the KMD and KMD INF are in euros. If the entity's
   functional currency is not EUR, stop and ask the person how to convert.
   `vat_report` converts each line at the document's functional/document amount ratio
   and rounds per line, so a few cents' difference from it is expected; a larger gap
   means the document's rate needs checking (documents imported through a connector
   carry the rate the source system gave).
   A credit memo's lines are stored positive; the view makes each line negative. Pass
   a credit memo's `net_amount` as −Σ|line net| (each line's absolute value, summed,
   negated) with its `document_type`; the selector treats any credit memo as a credit.

3. **Reversed and voided documents of the period — review list.** A reversal carries
   no document lines and no customer or vendor of its own, and `vat_report` nets it
   against the reversed invoice. A voided document was never posted (only an unposted
   document can be voided), so it was never in the ledger figures; it is listed only so
   the person sees what was withdrawn.
   How a reversed or voided invoice is shown in the KMD INF is not settled here. List
   them separately for a person to decide, and do not add or remove annex lines for
   them on your own:
   ```
   query("transaction", filters={"legal_entity_id": ID,
       "transaction_type": ["AR_INVOICE", "AR_CREDIT_MEMO", "AP_INVOICE", "AP_CREDIT_MEMO"],
       "status": ["reversed", "void", "voided"]},
       date_filters={"transaction_date": {"from": "YYYY-MM-01", "to": "YYYY-MM-DD"}})
   ```
   plus the reversals dated in the period (the `reversal_of_id` query above), each with
   the document it reverses.

**Which source wins.** The `vat_report` totals are authoritative for the KMD box
figures: they are the ledger's canonical tax computation, shared with the dashboard
Sales-tax report and the reconciliation panel. Totals rebuilt from the document lists
must agree with them per KMD line. If they differ, do not file either figure: find the
cause (a document missing from the lists — usually a status or type filter — a line
without a tax code, a registration exception, a document dated outside the period) and
present it to the person. File only once the two agree or the person has decided how
the difference is treated.

**CP1 checkpoint**: Check for any draft transactions in the period. If drafts exist, list them and ask the user to post or exclude them.

### Step 2.5: Supplier invoices already in a filed period (review list)

Before preparing the return, list supplier invoice numbers in this period that also
appear, for the same supplier, in a period whose return has already been filed. The
case this catches: a bill included in a filed return is later voided and reposted with
a new date, so its input VAT would be claimed a second time. This is a **review list
for a person**, not an automatic exclusion: a supplier can legitimately reuse a number,
and a correction may belong in this period.

Use existing reads only:

1. Filed periods for the entity:
   ```
   query("tax_period", filters={"legal_entity_id": ID, "status": "filed"})
   ```
   Also include periods with status `locked`, and periods that have a tax return in
   status `filed`, `amended`, `accepted` or `paid`:
   ```
   query("tax_return", filters={"legal_entity_id": ID})   # read every page
   ```
2. This period's AP invoices from Step 2 (all ledger-effective statuses): keep
   `vendor_id`, `reference_number` (the supplier's invoice number),
   `transaction_number`, `transaction_date`, `status`.
3. For each vendor in that list, its AP invoices dated inside the filed periods, **in
   any status** (posted, partial, paid, void, reversed):
   ```
   query("transaction", filters={"legal_entity_id": ID, "transaction_type": "AP_INVOICE",
       "vendor_id": VENDOR_ID},
       date_filters={"transaction_date": {"from": "<filed period start>", "to": "<filed period end>"}})
   ```
   Read every page.
4. Compare `reference_number` per vendor after trimming spaces and ignoring case.
   Skip empty references (a bill generated from a purchase order carries an empty
   reference on purpose).

Present each match: supplier, invoice number, this period's transaction (number, date,
status, VAT) and the earlier one (number, date, status, filed period). Ask the person
to confirm, for each, whether this period's VAT on it is claimed or left out. Record the
decision in `return_data.validation_results` (Step 8). Do not void, edit or exclude a
transaction on your own.

### Step 3: Verify Tax Code Coverage

Check that all transaction lines have valid tax codes:

1. Scan all fetched transaction lines
2. Flag any lines without a tax code assigned
3. Flag any lines using inactive or unclassified tax codes

**CP2 checkpoint**: If lines are missing tax codes, list them with transaction number, date, and amount. Ask the user to assign tax codes before continuing.

For a purchase bill (AP invoice), the code to choose by vendor origin and kind of purchase is in **references/purchase-tax-code-selection.md**; use it when proposing a code for a bill that has none or the wrong one.

### Step 3.5: Run the pre-close validation gate

Run **every** check in **references/validation-checklist.md** and emit the single
pass/fail report (one row per check, PASS / WARN / BLOCK, with the offending records and
the fix). This catches — before generation — payments without a document (check 2),
cut-off errors (check 3), tax-code/jurisdiction problems (check 4), GL mismatches
(check 5), and INF-threshold inconsistencies (check 6).

- **If any BLOCK is open: STOP. Present the report and do not proceed to Step 4.**
- WARN items are listed for the user to confirm but do not stop the workflow.
- Check 1 (output format) and the arithmetic in check 7 are enforced again by
  `generate_kmd.py` at Step 9, which refuses to write files on any format defect.

### Step 4: Calculate the KMD main form (declarationBody)

Using the tax code classification from Step 1 and the `vat_report` figures from Step 2
(the authoritative source; document lines only to split a shared tax name), compute the
KMD2 `declaration_body` values following **references/kmd-form-structure.md**. These are
taxable **bases** by rate (except the input-VAT lines, which are VAT amounts). Use the
**real KMD2 element names** — NOT Line1_1…Line13.

**Output side — bases by rate:**
- `transactions24` (line 1): base of sales at 24% (standard rate from 07.2025)
- `transactions22` (line 1²) / `transactions20` (line 1¹): legacy standard-rate bases (22% for 01.2024–06.2025, 20% until 12.2023); on a current return only credit invoices for those supplies
- `transactions9` (line 2): base at 9%; `transactions5` (2¹) at 5%; `transactions13` (2²) at 13%
- `transactionsZeroVat` (line 3): zero-rated total
- `euSupplyInclGoodsAndServicesZeroVat` (3.1) + `euSupplyGoodsZeroVat` (3.1.1): intra-Community supplies
- `exportZeroVat` (3.2): exports to non-EU

**Input side — VAT amounts:**
- `inputVatTotal` (line 5): total recoverable input VAT from purchases
- `importVat` (5.1, VAT on codes with `tax_scope` `import` such as `EU-EE-IMPORT`), `fixedAssetsVat` (5.2), `carsVat`/`carsPartialVat` (5.3/5.4): subsets of line 5

**Reverse charge / acquisitions:**
- The acquisition bases go **inside the rate lines** (add them to `transactions24` etc.) — per EMTA guidance the rate lines include IC acquisitions and reverse-charge services; that is what drives e-MTA's self-assessed line 4. Their deductible VAT goes into `inputVatTotal` (line 5).
- `euAcquisitionsGoodsAndServicesTotal` (line 6): informative breakout — goods + services acquired from **EU** suppliers; `euAcquisitionsGoods` (6.1) is the goods subset
- `acquisitionOtherGoodsAndServicesTotal` (line 7): informative breakout — services received from **non-EU** suppliers + domestic reverse charge
- Lines 6/6.1/7/7.1 are informative only; the generator rejects inputs whose 6+7 exceed the rate-line bases

**Exempt / adjustments:**
- `supplyExemptFromTax` (line 8)
- `adjustmentsPlus` (line 10) / `adjustmentsMinus` (line 11): non-negative corrections

**Do NOT compute total VAT (line 4), VAT due (line 12) or overpaid (line 13)** — e-MTA
derives them from the bases + `inputVatTotal`, and there are no XSD elements for them.
`generate_kmd.py` computes them for the CSV / summary automatically.

**CP3 checkpoint**: Present the completed main form. Sanity-check that
`Σ(base × rate) − inputVatTotal` gives the expected net VAT (payable if positive,
refundable if negative).

### Step 5: Prepare KMD INF Annex

Following **references/kmd-inf-annex.md** (rules from EMTA's KMD INF instructions, 07.2025):

1. **Build the invoice lists** from Step 2's invoices (`include_lines=true`): per invoice
   the `document_type`, the total **without VAT in EUR** (Σ line net × `exchange_rate`,
   see Step 2) with `currency: "EUR"`, the VAT (Σ `tax_amount`, converted the same way),
   whether any line is at 24/22/20/13/9/5 %, the partner (`partner_key` = the
   `customer_id` or `vendor_id`) and its register code. Part A uses invoices issued; part B uses invoices received whose VAT
   is deducted in KMD line 5 this period (with the amount deducted).
2. **Select partners** with the generator's selection mode, which applies the
   threshold (at least EUR 1,000.00 without VAT per partner, inclusive; ordinary and
   credit invoices totalled separately; excluded invoice types left out). The limit is
   per transaction partner: records that carry the same register code are combined
   (`partner_keys`, `partner_names` list them), and such a group is declared only when
   every invoice in it carries the same verified code — otherwise it goes to
   `needs_registry_code`. It refuses non-EUR amounts and a missing document type:
   ```
   python3 scripts/generate_kmd.py --select-inf invoices_A.json --side A
   python3 scripts/generate_kmd.py --select-inf invoices_B.json --side B
   ```
   Do not total the header `amount`: it is the gross amount.
3. **Register codes**: use only a verified register code from the partner's own record
   (see the reference: a customer's `tax_id`, a registry-code custom field, never a VAT
   number). Partners in `needs_registry_code` go on a review list for a person to
   resolve. Never fill the code from the VAT number or from another company's record.
4. **Build the annex lines**, invoice by invoice (`sum_per_partner: false`). Credit
   invoices are entered with a **minus sign** in every amount column (`invoiceSum`,
   `sumForRateInPeriod`, `invoiceSumVat`, `vatInPeriod`, and the cash-accounting
   columns). Use the signed values each returned invoice carries: `invoiceSum` (the
   whole invoice without VAT) from `signed_net_amount`; `sumForRateInPeriod` = Σ line net
   at that line's rate group declared this period, negative for a credit invoice (one
   annex line per rate group, up to 4 per invoice); `vatInPeriod` from
   `signed_vat_deducted_in_period`; `invoiceSumVat` = `signed_net_amount` +
   `signed_vat_amount`. Never the unsigned `net_amount` for a credit invoice.
   - Part A: `buyerRegCode`, `buyerName`, `invoiceNumber`, `invoiceDate`, `invoiceSum`
     (total without VAT), `taxRate`, `sumForRateInPeriod`, special code in `comments`.
   - Part B: `sellerRegCode`, `sellerName`, `invoiceNumber` (supplier's number),
     `invoiceDate`, `invoiceSumVat` (total with VAT), `vatInPeriod` (line 5 amount),
     special code in `comments`.
   - **Only if the entity is on cash accounting** (`cash_accounting: true`): part A
     `invoiceSumForRate` (column 8) and part B `vatSum` (column 7). For an accrual-basis
     entity leave both out; the generator refuses them otherwise (part B special code 11,
     partial deduction, is the one exception for `vatSum`).

When no partner reaches the threshold, omit the annex — the generator sets
`noSales` / `noPurchases` to `true`.

**CP4 checkpoint**: Part A column 9 per rate ≤ the KMD rate lines, part B column 8 ≤
`inputVatTotal`; explain the difference by cause (partners below the threshold, natural
persons, excluded invoices). Present the `needs_registry_code` list and stop for the
person's answer before filing.

### Step 6: Prepare EC Sales List (Form VD)

Following **references/ec-sales-list.md**:

1. Identify intra-community supply transactions (zero-rated sales to EU B2B customers)
2. Group by customer VAT number
3. Classify supply type: **G** (goods), **S** (services), or **T** (triangular)
4. Calculate total supply amount per customer per type

**CP5 checkpoint**: Verify Form VD col 3 (goods) total = `euSupplyGoodsZeroVat` (KMD line 3.1.1) and col 5 (services) total = `euSupplyInclGoodsAndServicesZeroVat` − `euSupplyGoodsZeroVat` (line 3.1 − 3.1.1). Triangular resale (col 4) is NOT declared in the KMD. If no IC transactions exist, note that Form VD is not required.

### Step 7: Reconcile VAT GL Accounts

Compare calculated KMD amounts with GL account balances:

```
generate_report("trial_balance", {"legal_entity_id": ID, "as_of_date": "YYYY-MM-DD"})
```

1. VAT Output account balance should match the computed total output VAT (line 4)
2. VAT Input account balance should match `inputVatTotal` (line 5)
3. Net VAT payable/receivable should match line 12 or line 13

If there are differences, identify the cause (timing, manual entries, rounding) and present to the user.

### Step 8: Submit Tax Return to ERP

Store the KMD calculation results in the ERP so they are viewable in Admin Dashboard → Tax → Returns and XML can be regenerated on demand.
`return_type` is the **registered form code** resolved in Prerequisites from
`query("tax_filing_form", …)` (for Estonia `KMD`), and `tax_authority_id` is that form's
authority. If no VAT form is registered for the entity's country, do not submit: report
it as described in Prerequisites.

```
submit(object_type="tax_return", operation="create", data=JSON.stringify({
    "legal_entity_id": <entity_id>,
    "reporting_period_id": <period_id>,
    "tax_authority_id": <EMTA authority id>,
    "return_type": "<form_code resolved in Prerequisites, e.g. KMD>",
    "return_data": {
        "form_code": "<same form_code>",
        "cash_accounting": <true|false, from Prerequisites>,
        "year": <YYYY>,
        "month": <MM>,
        "regcode": "<business registry code>",
        "declaration_body": {
            "transactions24": <base>, "transactions22": <base>, "transactions20": <base>,
            "transactions9": <base>, "transactions5": <base>, "transactions13": <base>,
            "transactionsZeroVat": <base>,
            "euSupplyInclGoodsAndServicesZeroVat": <base>, "euSupplyGoodsZeroVat": <base>,
            "exportZeroVat": <base>,
            "inputVatTotal": <vat>, "importVat": <vat>, "fixedAssetsVat": <vat>,
            "euAcquisitionsGoodsAndServicesTotal": <base>, "euAcquisitionsGoods": <base>,
            "acquisitionOtherGoodsAndServicesTotal": <base>,
            "supplyExemptFromTax": <base>,
            "adjustmentsPlus": <amount>, "adjustmentsMinus": <amount>
        },
        "sales_annex": {"sum_per_partner": true, "lines": [{"buyerRegCode": "...", "buyerName": "...", "invoiceSum": <amount>, "taxRate": "24"}, ...]},
        "purchases_annex": {"sum_per_partner": true, "lines": [{"sellerRegCode": "...", "sellerName": "...", "invoiceSumVat": <amount>, "vatInPeriod": <amount>}, ...]},
        "sales_summary": {
            "standard_rate": {"rate": 24, "net_sales": <amount>, "vat_amount": <amount>},
            "reduced_rate": {"rate": 13, "net_sales": <amount>, "vat_amount": <amount>},
            "zero_rated": {"rate": 0, "net_sales": <amount>, "vat_amount": 0},
            "exempt": {"net_sales": <amount>, "vat_amount": 0}
        },
        "purchases_summary": {"total_purchases": <amount>, "input_vat_recoverable": <amount>},
        "vat_calculation": {
            "total_output_vat": <computed total VAT, line 4>,
            "total_input_vat": <inputVatTotal, line 5>,
            "net_vat_due": <line 12 payable, or negative of line 13 overpaid>
        },
        "reverse_charge_transactions": {"count": <n>, "total_value": <amount>, "vat_self_assessed": <amount>},
        "validation_results": {"cp1": true, "cp2": true, "cp3": true, "cp4": true, "cp5": true},
        "filing_instructions": {
            "form": "KMD + KMD INF + Form VD",
            "filing_method": "e-MTA XML upload",
            "portal_url": "https://maasikas.emta.ee",
            "due_date": "<YYYY-MM-20 of following month>",
            "payment_due": "<YYYY-MM-20 of following month>"
        }
    },
    "notes": "<Month Year> KMD - auto-calculated"
}))
```

Tell the user: "Tax return saved (ID: {tax_return_id}). You can view it at Admin Dashboard → Tax → Returns."

### Step 9: Post VAT Closing Journal Entry

Post a journal entry to reclassify VAT accounts for the period. VAT Output/Input are already posted per-transaction — this entry moves the net balance to a VAT Payable (or Receivable) account.

**If Line 12 > 0 (net VAT payable):**
```
submit(object_type="transaction", operation="post", data=JSON.stringify({
    "transaction_type_code": "GL_JOURNAL",
    "legal_entity_id": <entity_id>,
    "description": "VAT closing - KMD <YYYY>/<MM>",
    "transaction_date": "<last day of reporting period>",
    "lines": [
        { "account_number": "<VAT Output account>", "debit": <total output VAT, line 4>, "credit": 0 },
        { "account_number": "<VAT Input account>", "debit": 0, "credit": <inputVatTotal, line 5> },
        { "account_number": "<VAT Payable account>", "debit": 0, "credit": <net VAT payable, line 12> }
    ]
}))
```

**If Line 13 > 0 (VAT overpaid/refundable):**
```
submit(object_type="transaction", operation="post", data=JSON.stringify({
    "transaction_type_code": "GL_JOURNAL",
    "legal_entity_id": <entity_id>,
    "description": "VAT closing - KMD <YYYY>/<MM> (overpaid)",
    "transaction_date": "<last day of reporting period>",
    "lines": [
        { "account_number": "<VAT Output account>", "debit": <total output VAT, line 4>, "credit": 0 },
        { "account_number": "<VAT Receivable account>", "debit": <net VAT overpaid, line 13>, "credit": 0 },
        { "account_number": "<VAT Input account>", "debit": 0, "credit": <inputVatTotal, line 5> }
    ]
}))
```

Tell the user: "VAT closing journal entry posted. Net VAT {payable/overpaid}: EUR {amount}."

> **Note:** Determine the correct VAT Output, Input, Payable, and Receivable account numbers by querying the entity's chart of accounts. Look for accounts with `account_subtype` matching `vat_output`, `vat_input`, or similar naming conventions.

### Step 9b: Post the EMTA Settlement Bill (Line 12 > 0 only)

The closing entry records the liability on the ledger, but nothing
vendor-shaped exists yet — so when the user pays EMTA from the bank, the
bank agent finds no bill to apply the payment to and books a dangling AP
payment against nothing (live incident, Hala Digital 2026: four EMTA
payments accumulated a fake EUR 298.94 "EMTA owes us" receivable on the AP
control while VAT Payable sat unrelieved, reconciliation flagged the
payments forever, and the bills-collector emailed phantom reminders).

Post an AP bill to the tax authority for the declared amount. This moves
the net VAT from VAT Payable onto Accounts Payable as an open, dated,
vendor-visible obligation — exactly the model payroll taxes already use
(TSD settlement bills):

1. Resolve the tax-authority vendor: `query("vendor", query="Maksu- ja
   Tolliamet")` (also try "EMTA"). If none exists, create one via
   `submit(object_type="vendor", operation="create", …)` — name "Maksu- ja Tolliamet (EMTA)",
   no VAT number, no payment terms.

2. Post the bill:
```
submit(object_type="transaction", operation="post", data=JSON.stringify({
    "transaction_type_code": "AP_INVOICE",
    "legal_entity_id": <entity_id>,
    "vendor_id": <EMTA vendor id>,
    "transaction_date": "<last day of reporting period>",
    "due_date": "<20th of the following month>",
    "currency": "EUR",
    "description": "Net VAT payable — KMD <YYYY>/<MM>",
    "reference_number": "KMD-<YYYY>-<MM>",
    "lines": [
        { "account_number": "<VAT Payable account>",
          "amount": <net VAT payable, line 12>,
          "description": "KMD <YYYY>/<MM> line 12" }
    ]
}))
```
The line debits the VAT Payable account (the executor skips auto-VAT on
tax-subtype accounts — the line IS the tax), crediting AP. VAT Payable
returns to zero for the period; AP shows what is owed and by when.

3. Tell the user: "EMTA settlement bill {number} posted: EUR {amount},
   due {date}. Pay it from the bank as usual — the payment will apply to
   this bill automatically."

**Do NOT post a bill for the Line 13 (refund) case** — a receivable from
EMTA is not a payable; the closing entry's VAT Receivable line already
records it.

**Why the payment then self-applies:** the reconciliation agent's vendor
sweep exact-matches open bills to payments by vendor + amount, and
payment-batch confirmations FIFO-apply for vendors listed in the entity's
`payroll.tax_bill_vendor_ids` config. If the org also runs payroll through
tax-bill settlement, add the EMTA vendor id to that config key so both
paths cover it.

### Step 9c: Track Refunds (Line 13 > 0)

Complete Step 9 also in a refund month. Verify that the closing journal moves
net overpaid VAT to the entity's VAT Recoverable account (2310 where configured),
not a debit left on VAT Payable. Resolve accounts from the chart; do not assume
these account numbers apply to every entity. Do not create an AP settlement bill.
Before posting, check for the period's existing closing journal to avoid duplicates.

Read the saved tax return and preserve its complete `return_data`. Add or update
`return_data.open_item` using `submit(object_type="tax_return", operation="update", ...)` (the field is
inside the JSON return payload, not a separate ERP object):

```json
{
  "kind": "vat_refund",
  "currency": "EUR",
  "amount": "<line 13>",
  "remaining_amount": "<unclaimed balance>",
  "status": "unclaimed",
  "description": "Refund EUR X claimable from ettemaksukonto, not yet requested",
  "closing_transaction_id": "<verified closing journal id>",
  "settlements": []
}
```

Report the cumulative `remaining_amount` across this entity's non-superseded
refund returns, including earlier periods. Read all pages; do not total just the
current month. Reconcile this amount to the e-MTA prepayment statement and the GL,
listing differences explicitly. Never infer an e-MTA balance from the GL alone.
A filed refund return does not prove that a refund was requested or received.
Prompt the user to request a refund or confirm the intended offset.

Record a request as `requested`, preserving the receivable. Reduce the remaining
amount only after a verified bank receipt or tax-authority offset, recording its
reference, date and amount in `settlements`. Partial settlements leave the item
open; zero remaining changes its status to `settled`. Each settlement reference
must be recorded once. Carry the item into subsequent close reviews until settled.

### Step 10: Generate Output

Compile the final declaration package:

1. **KMD Form Summary** — All main-form values in a clear table
2. **KMD INF** — Part A (sales partners) and Part B (purchase partners)
3. **EC Sales List** — Form VD data (if applicable)
4. **Reconciliation** — GL vs KMD comparison
5. **Validation Results** — All checkpoint results from **references/validation-checklist.md**

Provide filing guidance from **references/emta-filing-guide.md**:
- Deadline: 20th of the following month
- Portal: e-MTA (maasikas.emta.ee)
- XML format available for upload (downloadable from Admin Dashboard → Tax → Returns → [this return])
- Digital signature required

After the user files with EMTA and receives confirmation, mark the return as filed
(this also transitions the tax reporting period to `filed`):
```
submit(object_type="tax_return", operation="file", data=JSON.stringify({
    "return_id": <tax_return_id from Step 8>,
    "confirmation_number": "<confirmation from e-MTA>"
}))
```

Then offer to **lock the period** so the filed return keeps matching the ledger:
```
submit(object_type="tax_period", operation="lock", data=JSON.stringify({
    "period_id": <reporting_period_id>,
    "reason": "KMD filed — confirmation <number>"
}))
```
To amend later: `submit(object_type="tax_period", operation="unlock", …)` → correct → re-file → re-lock.
The Reports → Sales tax reconciliation panel flags any ledger-vs-return drift.

> **Payment note:** Check your e-MTA prepayment account (ettemaksukonto) balance before paying. If payroll taxes or other obligations already created a positive balance, the actual payment may be lower than KMD Line 12. Make a bank transfer to EMTA — it applies against the settlement bill from Step 9b (a lower actual payment applies partially; the remainder stays visibly open on the bill, which is correct).

## Output Format

Present the final output as a structured document with clear sections:
- KMD main-form table (KMD2 element values)
- KMD INF partner tables (Part A and Part B)
- EC Sales List table (if applicable)
- Reconciliation summary
- Validation checklist (pass/fail for each check)
- Tax return ID and link to Admin Dashboard
- Filing instructions and deadline reminder


## Period-close statement evidence (b1, awaiting deployment)

A retained authority account statement is distinct from a return liability. For close evidence, current return statuses are filed, amended, accepted and paid. Draft/superseded/rejected rows are listed but not compared when a current statement exists. Unknown statuses remain not_determined; a differing retained statement still produces a named conflict. If no current return carries a statement, the previous non-cancelled-return fallback remains, labelled “not a current filed return”. Equal statements do not conflict; compare GL only on eligible ledger lines.

Filing evidence matches a return’s own period or a reporting period for the same entity and authority. Candidate forms are selected by country or overlapping authority registration. An unfiled selected form without an applicability rule is advisory not_determined, not “missing” or “not expected”. Quarterly selection still assumes calendar quarters and says so; this is a disclosed existing selection limitation, not a universal tax rule.
