# VAT / Tax Return Management

Tax returns capture the output of periodic tax compliance filings (VAT declarations, sales tax returns, GST returns, etc.). Uses the same **plugin-based architecture** as allocation and payroll — jurisdiction-specific plugins calculate the return data, then submit results to the backend for persistent storage.

---

## Overview

| Aspect | Detail |
|--------|--------|
| **Entity type** | `tax_return` |
| **Return types** | `vat_return`, `sales_tax`, `sales_tax_quarterly`, `gst`, `1099`, `w2`, `corporation_tax` |
| **Storage** | Structured JSONB in `return_data` field (jurisdiction-specific form data) |
| **Status flow** | `draft` → `filed` → `accepted` / `rejected` → `amended` |
| **XML generation** | On demand from stored JSONB (no file storage needed) |
| **GL impact** | VAT closing journal entry posted separately (not by the tax return itself) |

### Architecture

```
Plugin/Agent                          Backend (MCP Server)
---------------------                 --------------------
1. Fetch period transactions
   (query)
2. Calculate return lines
   (KMD lines, VAT boxes, etc.)
3. Validate and reconcile
4. submit(tax_return, create)      -> Store draft return with
                                      return_data JSONB
5. submit(transaction, post)       -> Post VAT closing journal
                                      entry (separate step)
6. Generate XML for portal upload
   (on demand from return_data)
7. User files with tax authority
8. submit(tax_return, file)        -> Mark as filed with
                                      confirmation number
```

> **IMPORTANT — Schema Discovery**: Before calling `submit()`, call `get_submissions(action='schema', object_type="tax_return", operation)` to discover the exact required and optional fields for your organization.

---

## Workflow Operations

| Operation | Typical lane | Description |
|-----------|------|-------------|
| `tax_return` + `create` | Green | Create draft return from plugin calculation results |
| `tax_return` + `file` | Yellow | Mark return as filed with confirmation number from authority |

Lanes are assigned by your organisation's workflow rules; the submit() result is authoritative.

---

## Creating Tax Returns

### From Plugin Calculation

After calculating the return data (KMD lines, VAT boxes, sales tax summary, etc.):

```
submit("tax_return", "create", {
    "legal_entity_id": 1,
    "return_type": "vat_return",
    "reporting_period_id": 45,
    "tax_authority_id": 3,
    "return_data": {
        // The form, its lines, the filing portal and the due date come from the
        // country plugin that calculated the return and from the reporting period:
        // never type a form code, portal URL or deadline from memory.
        "form_code": "<form code from the plugin>",
        "year": 2026,
        "month": 3,
        // ...the plugin's own line fields (see "Jurisdiction-Specific Plugins" below for each one's keys)
        "vat_calculation": { "total_output_vat": 2400.00, "total_input_vat": 1800.00, "net_vat_due": 600.00 },
        "filing_instructions": { ... }
    },
    "notes": "March 2026 VAT return - calculated by the country plugin"
})
```

Returns: `{ "success": true, "tax_return_id": 5, "status": "draft" }`

### Viewing Tax Returns

```python
# Search tax returns
query("tax_return", query="vat_return")

# List all draft returns for an entity
query("tax_return", filters={"legal_entity_id": 12, "status": "draft"})

# Get full return with JSONB data
get_entity("tax_return", id=5)
```

---

## VAT Closing Journal Entry

**Key accounting principle:** VAT Output/Input accounts are already posted throughout the month with each invoice. The tax return is just a report — it doesn't create the obligation. But at period end, you need a **closing journal entry** to reclassify VAT accounts.

### When Net VAT is Payable (Output > Input)

```
submit("transaction", "post", {
    "transaction_type_code": "JOURNAL_ENTRY",
    "legal_entity_id": 12,
    "description": "VAT closing - 2026/03",
    "transaction_date": "2026-03-31",
    "lines": [
        { "account_number": "2210", "debit": 2400.00, "credit": 0 },
        { "account_number": "1410", "debit": 0, "credit": 1800.00 },
        { "account_number": "2215", "debit": 0, "credit": 600.00 }
    ]
})
```

Where (example account numbers; use the entity's own VAT accounts):
- `2210` = VAT Output (what you collected from customers) — zeroed out
- `1410` = VAT Input (what you paid to suppliers) — zeroed out
- `2215` = VAT Payable to tax authority — net liability

### When Net VAT is Overpaid (Input > Output)

```
submit("transaction", "post", {
    "transaction_type_code": "JOURNAL_ENTRY",
    "legal_entity_id": 12,
    "description": "VAT closing - 2026/03 (overpaid)",
    "transaction_date": "2026-03-31",
    "lines": [
        { "account_number": "2210", "debit": 1200.00, "credit": 0 },
        { "account_number": "1415", "debit": 400.00, "credit": 0 },
        { "account_number": "1410", "debit": 0, "credit": 1600.00 }
    ]
})
```

Where `1415` = VAT Receivable from tax authority.

---

## Filing with Tax Authority

After uploading XML/forms to the tax authority portal and receiving confirmation:

```
submit("tax_return", "file", {
    "return_id": 5,
    "confirmation_number": "<the authority's receipt reference>",
    "filing_date": "2026-04-18",
    "notes": "Filed via the tax authority portal"
})
```

This updates:
- `tax_returns.status` → `filed`
- `tax_returns.confirmation_number` → stored
- `tax_reporting_periods.status` → `filed`

**Three preconditions, checked before the status flips.** Filing is the moment a
working draft becomes a compliance record, so this is where the facts have to
line up — drafts stay deliberately free-form:

1. **The return must be linked to a reporting period.** A filed return has to
   record which period it declares; without that the deadline on the record is a
   guess. Link one with `tax_return.update(reporting_period_id=...)`, or create
   it first with `tax_reporting_period.create` — note the object type differs
   from `tax_period.lock`.
2. **That period must belong to the same tax authority as the return.** Filing
   calendars differ per authority — an Estonian KMD is due to the VAT authority
   on the 20th while the TSD is due to the payroll authority on the 10th — so a
   mismatched link stamps the wrong deadline on the record.
3. **`filing_date` must not precede the period's `period_end`.** A period cannot
   be declared before it closes.

Filing **late is allowed** and never blocked — it happens, and refusing it would
leave the ERP unable to record what actually occurred. It comes back flagged as
`late_filing` / `days_late`.

> **Always pass `filing_date` explicitly.** It defaults to *today*, which
> silently records the wrong date whenever you are entering a filing after the
> fact.

---

## Payment

Tax payments are NOT AP bills. The payment flows through normal banking:

1. User logs into tax authority portal (e.g., e-MTA) to see actual amount due (may be reduced by prepayment account balance from payroll taxes, etc.)
2. User makes bank transfer to tax authority
3. Bank statement line is reconciled against the VAT Payable GL account
4. VAT Payable balance is cleared

> **Note:** some tax authorities keep one prepayment account across taxes (e.g. Estonia; the country tax role covers it), so a positive balance from other taxes can lower the VAT payment. Check the authority's account balance before paying.

---

## Jurisdiction-Specific Plugins

The `tax_return.create` operation is generic. Each jurisdiction's plugin fills in the `return_data` JSONB with form-specific data:

| Jurisdiction | Plugin | Form | return_data Contains |
|---|---|---|---|
| Estonia | `arfiti-ee-vat-declaration` | KMD (13 lines) | kmd_lines, kmd_inf, vd_entries, validation_results |
| UK | `vat_uk` agent | VAT100 (9 boxes) | vat_boxes, adjustments, fuel_scale_charges |
| US | Core tools | State-specific | gross_sales, exempt_sales, taxable_sales, tax_collected |
| EU (generic) | `eu_vat_returns.py` | Country-specific | output_vat_categories, input_vat, reverse_charge |

---

## Admin Dashboard

Tax returns are viewable at `/tax/returns`:
- **List page**: the selected entity's returns; search, status chips and + Filter (return type, status) narrow the list
- **Detail page**: tabs Return data, Form checks, Export and Metadata. Return data draws the stored `return_data` by shape: a list of same-shaped rows is a table, other keys are rows, nested objects fold
- **Form checks and Export (KMD only)**: Form checks lists the KMD check's errors and warnings; Export's **Generate XML** creates the KMD files (CSV and XML) from the stored data for download and sends nothing to the tax authority. It is off while the checks list errors. Other return types have neither tab


## Close evidence update (b1, awaiting deployment)

A retained authority account statement is distinct from a return liability. For close evidence, current return statuses are filed, amended, accepted and paid. Draft/superseded/rejected rows are listed but not compared when a current statement exists. Unknown statuses remain not_determined; a differing retained statement still produces a named conflict. If no current return carries a statement, the previous non-cancelled-return fallback remains, labelled “not a current filed return”. Equal statements do not conflict; compare GL only on eligible ledger lines.
