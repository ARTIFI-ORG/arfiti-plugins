# KMD INF Annex (Transaction Partner Reporting)

The KMD INF is the annex to the KMD form that reports invoices issued (part A) and
received (part B) per transaction partner once the partner reaches the threshold.

**Sources** (read these before changing any rule here):
- EMTA, *Instructions for filling in the appendix (form KMD INF) to the value added tax
  return*, version 07.2025:
  <https://www.emta.ee/sites/default/files/documents/2025-07/vorm_kmd_inf_2025_07_eng.pdf>
  (cited below as "KMD INF instructions").
- EMTA, *Filing VAT returns and reports*:
  <https://www.emta.ee/en/business-client/taxes-and-payment/value-added-tax/filing-vat-returns-and-reports>

A taxable person with limited liability files the KMD but not the annex (EMTA filing page).

## Threshold

**At least EUR 1,000.00 without VAT, per transaction partner, per taxation period
(calendar month).** Inclusive: exactly 1,000.00 qualifies, 999.99 does not. The amount is
the invoices' total **excluding VAT** — never the gross invoice amount.
(KMD INF instructions, introduction and "Accounting the limit per transaction partner";
EMTA filing page: "the total amount of sales or purchase invoices without VAT per
transaction partner is at least 1,000 euros".)

How the limit is counted (KMD INF instructions, "Accounting the limit per transaction partner"):

- Separately for invoices issued (part A) and invoices received (part B).
- Separately for ordinary invoices and for credit invoices. If either total reaches
  EUR 1,000 for a partner, **all** invoices with that partner in the period, credit
  invoices included, are declared.
- Only invoices containing supply taxable at 24 %, 13 %, 9 % (exceptionally 22 %, 20 %,
  5 %) count. For such an invoice the **whole** total without VAT counts, including
  0 %, exempt and non-supply amounts on the same invoice. An invoice with no supply at
  those rates does not count and is not declared.
- An invoice counts into the limit only once, in the first period it must be declared.
  An invoice declared earlier whose supply (part A) or deduction (part B) also falls in
  this period is declared again now, whatever this period's totals (pass it with
  `counted_in_earlier_period: true`).
- In a VAT group the limit is counted separately for each member.

Invoices that are **not** declared (KMD INF instructions, "Invoice data shall not be presented"):

1. Issued to a natural person (other than a self-employed person), or to a non-resident
   without a register code assigned in Estonia (register of taxable persons, Taxation Act § 17).
2. No supply at 24/22/20/13/9/5 % on the invoice (for example only exempt or 0 % supply).
3. Issued solely under the travel-services special procedure (VAT Act § 40).
4. Subject to professional secrecy (the recipient may still declare it).
5. Part B only: the VAT on the invoice is not deducted as input VAT.

A partner below the threshold may still be declared voluntarily (VAT Act § 27(1³)).

### Selecting partners (deterministic)

Build an invoice list from the period's ledger-effective invoices — every status that
carries the VAT, paid ones included (SKILL.md Step 2 fetches them with
`include_lines=true`). Per invoice: the **net** total is the sum of the document
lines' line net (`line_amount − tax_amount` when the line `is_tax_inclusive`, else `line_amount`) — the rule the canonical tax view uses, so a tax-inclusive line
never pushes a partner over the limit on its gross amount — the VAT is the sum of
`tax_amount`, and `has_positive_rate_supply` is true when any line carries a tax code at
24/22/20/13/9/5 %. Amounts are in **EUR**: for a foreign-currency document multiply
the document amounts by the header's `exchange_rate` (document → functional rate) and
round to cents per invoice; the limit and the annex are in euros, and `vat_report` sums
the functional amounts (per line, so cents may differ). For a credit memo pass
`net_amount` = −Σ|line net| — the canonical view (migration 601) makes each stored
(positive) line negative — with its `document_type`; the selector counts any credit
memo as a credit and returns `signed_net_amount` (negative) for the annex columns,
which take credit invoices with a minus sign. An ordinary invoice with a negative total (a reduction under VAT Act
§ 29¹) carries a negative `net_amount` and also counts as a credit. Then run:

```
python3 scripts/generate_kmd.py --select-inf invoices_A.json --side A
python3 scripts/generate_kmd.py --select-inf invoices_B.json --side B
```

Each invoice object: `partner_key` (the ERP `customer_id` / `vendor_id`),
`document_type` (required: `AR_INVOICE` / `AR_CREDIT_MEMO` for part A, `AP_INVOICE` /
`AP_CREDIT_MEMO` for part B), `currency` (required, must be `"EUR"`), `partner_name`,
`registry_code`,
`registry_code_verified`, `non_resident`, `partner_kind`, `invoice_number`,
`invoice_date`, `net_amount` (required), `vat_amount`, `has_positive_rate_supply`
(required, true/false), optional
`travel_special_procedure_only`, `professional_secrecy`, `counted_in_earlier_period`,
and for part B `vat_deducted_in_period` (required: the input VAT this invoice puts into
KMD line 5 this period, `0` when none). Amounts are numbers with a dot decimal; a
missing, null or non-numeric amount is refused, never read as zero. The limit is per
transaction partner, not per ERP record: records that carry the same register code
(two customer cards for one company) are combined into one partner, listed in
`partner_keys` and `partner_names`. The group is declared only when every invoice in it
carries the same verified code; a group that reaches the limit with an unverified or
conflicting code goes to `needs_registry_code`. Records are never merged by name. The output lists `declare`, `needs_registry_code`, `below_threshold` and
`excluded` (with the reason). Do **not** aggregate the header `amount` with
`query("transaction", group_by=..., aggregates={"amount": "sum"})`: that is the gross
amount, and it mixes in invoices the instructions exclude.

## Partner register code (column 2)

Column 2 is "the register code assigned to the transaction partner, including a
self-employed person, in Estonia"; for non-residents, the register code assigned in the
register of taxable persons (Taxation Act § 17); for notaries and bailiffs, their
personal ID code (KMD INF instructions, part A and part B, column 2). **A VAT number
is not a register code** (an Estonian VAT number `EE10…` is a different number from the
8-digit registry code), and `generate_kmd.py` refuses a reg-code value with a country
prefix.

Where ARTIFI stores it:

- **Customers**: `master_customers.tax_id` holds the registry / company code; the VAT
  number lives on the entity-level customer tax profile (`customer_tax_profiles.vat_number`).
  This is the convention the invoice PDF uses (`resolve_customer_tax_identifiers`:
  `tax_id` prints as "Reg.", `vat_number` as "VAT").
- **Vendors**: there is **no dedicated registry-code field**. `master_vendors.tax_id`
  accepts an EIN, an EU VAT number or a generic code, so it is often a VAT number.
- Either record may carry an organisation-defined custom field for the registry code
  (check `query("custom_field")` for one on customer / vendor).

Treat a value as the partner's register code only when **all** hold:

1. It comes from that partner's own record (`tax_id` for a customer, or a registry-code
   custom field) — never from another company with a similar name.
2. It has no country prefix and has the Estonian form (8-digit registry code, or an
   11-digit personal ID code for a notary / bailiff / self-employed person). A
   vendor's `tax_id` qualifies only if it is in this form; an `EE…` value is a VAT number.
3. It is confirmed by the partner's own document (the code printed on the invoice) or
   the e-Business Register (ariregister.rik.ee) — say which in the review list.

A partner that reaches the threshold without a verified register code goes on a **review
list for a person to resolve** (`needs_registry_code` in the selection output). Never
fill it from the VAT number, by stripping a prefix, or from another company's record. If
the person confirms the partner is a non-resident with no register code assigned in
Estonia, its invoices are not declared (instructions, column 2). Omitting a code is not a
failure to file if EMTA can identify the partner from the data given (KMD INF
instructions, introduction), but filing a wrong code is a wrong declaration.

## Structure

The form is filled **invoice by invoice** (KMD INF instructions, parts A and B).

### Part A — Invoices issued (`salesAnnex`)

| Col | KMD2 element | Content | Source |
|---|---|---|---|
| 2 | `buyerRegCode` | Register code / personal ID code (see above) | verified register code |
| 3 | `buyerName` | Partner name | `customer.customer_name` |
| 4 | `invoiceNumber` | Invoice number | `transaction_number` / invoice number on the document |
| 5 | `invoiceDate` | Invoice date | `transaction_date` |
| 6 | `invoiceSum` | Invoice total **without VAT**, incl. 0 %/exempt parts | Σ line net |
| 7 | `taxRate` | Rate classifier (`24`, `13`, `9`, `5`, special-procedure variants) | tax code |
| 8 | `invoiceSumForRate` | Taxable value stated on the invoice — **cash-accounting taxpayers only** | only if `cash_accounting: true` |
| 9 | `sumForRateInPeriod` | Part declared in KMD lines 1, 1¹, 1², 2, 2¹, 2² this period | Σ line net at that rate |
| 10 | `comments` | Special code: 01 (§ 41/§ 42 special procedure), 02 (§ 41¹, buyer accounts the VAT), 03 (invoice also has 0 %/exempt/non-supply, or two or more rates) | tax codes |

Part A is declared for the period in which the invoice's supply is incurred (VAT Act
§ 11); if supply on the same invoice is also incurred in a later period, the invoice is
declared again in that period. Selecting invoices by `transaction_date` assumes the
supply date and the invoice date fall in the same period; flag invoices where they do
not (gate check 3).

Up to 4 lines per invoice (one per rate group). Credit invoices are entered with a minus
sign. A § 41¹ seller leaves column 9 empty.

### Part B — Invoices received (`purchasesAnnex`)

| Col | KMD2 element | Content | Source |
|---|---|---|---|
| 2 | `sellerRegCode` | Register code / personal ID code (see above) | verified register code |
| 3 | `sellerName` | Partner name | `vendor.vendor_name` |
| 4 | `invoiceNumber` | Supplier's invoice number | `reference_number` |
| 5 | `invoiceDate` | Invoice date | invoice date on the bill |
| 6 | `invoiceSumVat` | Invoice total **with VAT** | Σ (line net + `tax_amount`) |
| 7 | `vatSum` | VAT stated on the invoice — **cash-accounting taxpayers only**; exceptionally the line-5 amount for a partial deduction (VAT Act § 32 / § 29(4)). The generator requires special code 11 on such a line: that is our derivation (code 11 is the instructions' code for exactly that deduction), not a sentence in the source | only if `cash_accounting: true` or code 11 |
| 8 | `vatInPeriod` | Input VAT declared in KMD line 5 this period | deductible `tax_amount` |
| 9 | `comments` | Special code: 11 (partial deduction, VAT Act § 32 / § 29(4)), 12 (§ 41¹ acquisition, buyer accounts the VAT) | tax codes |

Part B is reported in the period the VAT is deducted in KMD line 5, not by invoice date
alone; a partly deductible or partly paid invoice appears again in later periods when
more is deducted.

### Cash accounting (kassapõhine)

Whether the company applies the special arrangements for cash accounting (VAT Act § 44)
is a fact about the entity that the preparer must establish, not assume — ask the user
or read it from the entity's recorded VAT setup. Record it as `cash_accounting` in the
generator input. For cash-accounting taxpayers, part A uses the period in which the
supply is generated under § 44(3)–(4), and part B lists invoices fully or partly paid in
the period. `generate_kmd.py` refuses `invoiceSumForRate` and `vatSum` unless
`cash_accounting` is `true` (part B special code 11 excepted).

## Reconciliation

- Part A column 9 per rate ≤ the KMD rate lines (1, 1¹, 1², 2, 2¹, 2²); the difference is
  partners below the threshold, natural persons and other excluded invoices.
- Part B column 8 ≤ KMD line 5 (`inputVatTotal`); the difference is the same population.
- List the difference by cause rather than calling it rounding.

## Corrections

Submitted electronically: complete or correct the data and submit the form again. A
line declared by mistake is deleted by resubmitting it with zero amounts (KMD INF
instructions, "Correcting the KMD INF form").

## Format (KMD2)

KMD INF A/B are the `salesAnnex` and `purchasesAnnex` parts of the **single**
`vatDeclaration` document (see `references/kmd-form-structure.md`). There is no
separate `<KMDINF>` file and no `http://emta.ee/schemas/vat` namespace. When no
partner reaches the threshold, set `noSales` / `noPurchases` to `true` in
`declarationBody` and omit the annex entirely.

Feed the generator via the `sales_annex` / `purchases_annex` blocks in the input JSON.
EMTA's instructions say the form is filled invoice by invoice, so prefer per-invoice
mode (`sum_per_partner: false`, below). The XSD also accepts a summed-per-partner mode
(`sum_per_partner: true`), where each line is one partner:

```json
"sales_annex": {
  "sum_per_partner": true,
  "lines": [
    {"buyerRegCode": "87654321", "buyerName": "Customer OÜ",
     "invoiceSum": 13000.00, "taxRate": "24", "sumForRateInPeriod": 13000.00}
  ]
},
"purchases_annex": {
  "sum_per_partner": true,
  "lines": [
    {"sellerRegCode": "11223344", "sellerName": "Vendor AS",
     "invoiceSumVat": 3660.00, "vatInPeriod": 660.00}
  ]
}
```

`generate_kmd.py` renders these into schema-valid `<salesAnnex>` / `<purchasesAnnex>`
elements:

```xml
<salesAnnex>
  <saleLine>
    <buyerRegCode>87654321</buyerRegCode>
    <buyerName>Customer OÜ</buyerName>
    <invoiceSum>13000.00</invoiceSum>
    <taxRate>24</taxRate>
    <sumForRateInPeriod>13000.00</sumForRateInPeriod>
  </saleLine>
</salesAnnex>
<purchasesAnnex>
  <purchaseLine>
    <sellerRegCode>11223344</sellerRegCode>
    <sellerName>Vendor AS</sellerName>
    <invoiceSumVat>3660.00</invoiceSumVat>
    <vatInPeriod>660.00</vatInPeriod>
  </purchaseLine>
</purchasesAnnex>
```

Per-invoice mode, the one EMTA's instructions describe: set `sum_per_partner: false`
and add `invoiceNumber` + `invoiceDate` to each line (up to 4 lines per invoice, one per
rate group). Mandatory fields
per the XSD: A → `invoiceSum`, `taxRate`; B → `invoiceSumVat`, `vatInPeriod`.
