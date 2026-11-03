# Annotated Example: Estonia (ee.json)

This is the complete Estonian template with annotations explaining each field's purpose. Use this as the gold standard when generating templates for other countries.

Source file: `mcp-server/src/data/onboarding/ee.json`

---

## Top-Level

```json
{
  "country_code": "EE",        // ISO 3166-1 alpha-2. Used for filtering throughout the system.
  "country_name": "Estonia",   // English name. Not used programmatically, just for readability.
```

## vat_tax_codes

Estonia uses EU VAT. Note: we include historical rates (active, clearly labelled) because companies may need to import or correct older transactions, and posting only accepts active codes.

```json
  "vat_tax_codes": [
    {
      "tax_code": "EU-EE-STD",           // Convention: EU-{CC}-{tier}
      "tax_name": "Estonian VAT Standard 24%",
      "tax_type": "vat",                  // Could be: vat, gst, sales_tax, hst
      "default_rate": 24.00,              // PERCENTAGE, not decimal
      "country_code": "EE",
      "tax_scope": "domestic",            // domestic | intra_union_goods | intra_union_services | import | foreign_reverse_charge | export | exempt
      "description": "Estonian standard VAT rate 24%, from 1 July 2025. Sales base: KMD line 1."
    },
    // Historical rates (kept active so older transactions and credit invoices can be posted)
    {"tax_code": "EU-EE-STD-22", "default_rate": 22.00, "description": "Historical (Jan 2024 - June 2025), KMD line 1²"},
    {"tax_code": "EU-EE-OLD-20", "default_rate": 20.00, "description": "Historical (until Dec 2023), KMD line 1¹"},

    // Reduced, zero, exempt — every VAT country has these
    {"tax_code": "EU-EE-RED", "default_rate": 9.00, "description": "Reduced: books, medicines, press publications (KMD line 2)"},
    {"tax_code": "EU-EE-RED13", "default_rate": 13.00, "description": "Reduced: accommodation, from Jan 2025 (KMD line 2²)"},
    {"tax_code": "EU-EE-RED5-PRESS", "default_rate": 5.00, "description": "Transitional: press publications under the cash-accounting transition only (KMD line 2¹)"},
    {"tax_code": "EU-EE-ZERO", "default_rate": 0.00, "description": "Zero-rated other than intra-EU supply, e.g. exports (KMD line 3)"},
    {"tax_code": "EU-EE-EXEMPT", "default_rate": 0.00, "tax_scope": "exempt", "description": "Exempt: financial services, healthcare (KMD line 8)"},

    // Reverse charge: the buyer self-assesses, so the code carries the rate AND the flag.
    // Domestic reverse charge (VAT Act § 41¹) is not seeded yet: the bill agent's
    // reverse-charge pick does not filter by scope, so a domestic RC code could land on
    // a foreign bill. Seed it once that selection respects scope.
    {"tax_code": "EU-EE-RC-FOREIGN", "default_rate": 24.00, "tax_scope": "foreign_reverse_charge", "is_reverse_charge": true,
     "description": "Services from non-EU suppliers (KMD lines 1 and 7)"},

    // EU-specific: intra-community transactions
    {"tax_code": "EU-EE-IC-ACQ", "default_rate": 24.00, "tax_scope": "intra_union_services", "is_reverse_charge": true,
     "description": "Intra-EU acquisitions (KMD lines 1 and 6)"},
    {"tax_code": "EU-EE-IC-SUPPLY", "default_rate": 0.00, "tax_scope": "intra_union_goods", "description": "Intra-EU supplies (KMD lines 3 and 3.1)"},
    {"tax_code": "EU-EE-IMPORT", "default_rate": 24.00, "tax_scope": "import", "is_reverse_charge": false,
     "description": "Import VAT paid at customs, deducted (KMD lines 5 and 5.1)"}
  ],
```

**Key patterns:**
- Include historical rates if a recent rate change occurred
- EU countries need IC-ACQ and IC-SUPPLY codes
- Exempt and zero-rated are different: exempt = no VAT at all, zero = VAT at 0% (still reported)
- A reverse-charge code needs the rate the buyer self-assesses and `is_reverse_charge: true`; at 0% without the flag no VAT is booked
- Name a second reduced rate `EU-{CC}-RED{rate}` (here `EU-EE-RED13`)

## tax_authorities

```json
  "tax_authorities": [
    {
      "code": "EMTA",                           // Short uppercase, used as FK
      "name": "Maksu- ja Tolliamet",             // LOCAL LANGUAGE name
      "jurisdiction_type": "vat_authority",
      "country_code": "EE",
      "authority_type": "vat",
      "filing_frequency": "monthly",
      "website_url": "https://www.emta.ee",
      "metadata": {
        "name_en": "Estonian Tax and Customs Board",  // English name in metadata
        "tax_types": ["vat", "income", "social"]      // What this authority handles
      }
    },
    {
      "code": "EMTA-PAYROLL",                    // Same org, different code for payroll
      "name": "Maksu- ja Tolliamet (Payroll)",
      "jurisdiction_type": "payroll_authority",
      "authority_type": "payroll",
      "filing_frequency": "monthly",
      "metadata": {
        "filing_form": "TSD",                    // Official form name
        "filing_deadline_day": 10,               // Due on 10th of following month
        "payment_deadline_day": 10
      }
    }
  ],
```

**Key patterns:**
- In Estonia, the same authority (EMTA) handles both VAT and payroll — we create two entries with different codes
- Some countries have completely separate authorities for VAT vs payroll vs social security

## tax_jurisdictions

```json
  "tax_jurisdictions": [
    {
      "code": "EE-VAT",
      "name": "Estonian VAT",
      "jurisdiction_type": "country",            // Estonia is small = one national jurisdiction
      "country_code": "EE",
      "authority_code": "EMTA",                  // FK → tax_authorities.code
      "metadata": {
        "filing_frequency": "monthly",
        "form_code": "KMD"                       // The official VAT return form
      }
    }
  ],
```

**Key patterns:**
- `authority_code` MUST match a `code` in `tax_authorities`
- Larger countries may have multiple jurisdictions (e.g., state-level)

## tax_reporting_periods

```json
  "tax_reporting_periods": {
    "frequency": "monthly",         // "monthly" → 12 periods, "quarterly" → 4 periods
    "filing_due_day": 20,           // VAT return due on 20th of following month
    "generate_for_year": true       // Auto-generate periods for current year
  },
```

**Key patterns:**
- Set to `null` for countries without VAT/GST
- The executor generates actual period records from this config

## payroll_tax_jurisdictions

```json
  "payroll_tax_jurisdictions": [
    {
      "tax_type": "income",                   // Short identifier
      "tax_name": "Estonian Income Tax",
      "employee_rate": 0.22,                  // DECIMAL (0.22 = 22%), NOT percentage
      "effective_from": "2025-01-01",
      "metadata": {
        "basic_exemption": 700                // Country-specific details in metadata
      }
    },
    {
      "tax_type": "social",
      "tax_name": "Estonian Social Tax",
      "employer_rate": 0.33,                  // Employer-only tax
      "minimum_wage_base": 886,
      "effective_from": "2025-01-01"
    },
    {
      "tax_type": "unemployment",
      "tax_name": "Unemployment Insurance",
      "employee_rate": 0.016,                 // Split between employee and employer
      "employer_rate": 0.008,
      "effective_from": "2025-01-01"
    },
    {
      "tax_type": "pension_ii_pillar",
      "tax_name": "Pension II Pillar",
      "employee_rate": 0.02,                  // Employee-only
      "effective_from": "2025-01-01",
      "metadata": {"voluntary": true}         // Important context
    }
  ],
```

**Key patterns:**
- Rates are DECIMALS (0.22), not percentages (22)
- Use `null` for rates that don't apply (e.g., employer has no income tax rate)
- Include metadata for country-specific nuances (basic exemptions, brackets, voluntary flags)

## payroll_vendors

```json
  "payroll_vendors": [
    {
      "vendor_key": "emta",                     // Reference key for payroll_vendor_config
      "vendor_name": "Maksu- ja Tolliamet (EMTA)",
      "vendor_type": "government",
      "tax_id": "70000349",                     // Real registration number
      "email": "emta@emta.ee",
      "website": "https://www.emta.ee",
      "currency": "EUR",
      "payment_method": "wire",
      "notes": "Receives all payroll tax payments via single prepayment account.",
      "metadata": {
        "name_en": "Estonian Tax and Customs Board",
        "payment_accounts": [                   // Real bank account details
          {"bank": "SEB Pank", "iban": "EE351010052031000004", "swift": "EEUHEE2X"}
        ],
        "tax_types_handled": ["income_tax", "social_tax", "unemployment", "pension_ii_pillar"],
        "filing_forms": {
          "TSD": "Monthly payroll declaration — due 10th of following month"
        }
      }
    }
    // ... more vendors (Tootukassa, Pensionikeskus)
  ],
```

**Key patterns:**
- Use REAL data: actual tax IDs, actual bank accounts, actual websites
- `vendor_key` is the FK used by `payroll_vendor_config`
- Some countries route all payments through one agency (like Estonia's EMTA)
- Other countries have separate agencies for each tax type

## payroll_vendor_config

```json
  "payroll_vendor_config": [
    {"line_type": "income_tax", "vendor_key": "emta", "expense_account_number": null, "payable_account_number": "2410"},
    {"line_type": "social_tax", "vendor_key": "emta", "expense_account_number": "6100", "payable_account_number": "2420"},
    {"line_type": "unemployment_employee", "vendor_key": "tootukassa", "expense_account_number": null, "payable_account_number": "2440"},
    {"line_type": "unemployment_employer", "vendor_key": "tootukassa", "expense_account_number": "6100", "payable_account_number": "2440"},
    {"line_type": "pension", "vendor_key": "pension_fund", "expense_account_number": null, "payable_account_number": "2430"}
  ],
```

**Key patterns:**
- `expense_account_number` is null for employee-only deductions (income tax, employee unemployment)
- `expense_account_number` is set for employer-side costs (social tax, employer unemployment)
- Split employee/employer for taxes that have both components
- `vendor_key` MUST match a key in `payroll_vendors`

## payroll_gl_accounts

```json
  "payroll_gl_accounts": [
    {"account_number": "2420", "account_name": "Social Tax Payable", "account_type": "liability", "account_subtype": "payroll_withholding", "normal_balance": "credit"},
    {"account_number": "2430", "account_name": "Pension Contributions Payable", "account_type": "liability", "account_subtype": "payroll_withholding", "normal_balance": "credit"},
    {"account_number": "2440", "account_name": "Unemployment Insurance Payable", "account_type": "liability", "account_subtype": "payroll_withholding", "normal_balance": "credit"},
    {"account_number": "6100", "account_name": "Social Security Costs", "account_type": "expense", "account_subtype": "salaries_expense", "normal_balance": "debit"}
  ],
```

**Key patterns:**
- Only accounts that the standard COA might NOT have
- Liabilities in 2400-2499 range, expenses in 6000-6199 range
- These get inserted into `master_accounts` during onboarding

## withholding_tax_rates

```json
  "withholding_tax_rates": [
    {"payment_type": "services", "withholding_rate": 20.0, "description": "Non-resident services WHT"},
    {"payment_type": "interest", "withholding_rate": 20.0, "description": "Interest payments to non-residents"},
    {"payment_type": "royalties", "withholding_rate": 10.0, "description": "Royalty payments to non-residents"},
    {"payment_type": "dividends", "withholding_rate": 0.0, "description": "No WHT on dividends (CIT at distribution level)"}
  ],
```

**Key patterns:**
- Rates are PERCENTAGES (20.0 = 20%), not decimals
- Note: this is different from payroll rates which are decimals — be careful!
- Include 0.0 rates to explicitly document that the country doesn't withhold on that type

## vat_declaration

Boxes follow the KMD form valid from 1 July 2025
(https://www.emta.ee/sites/default/files/documents/2025-07/vorm_kmd_2025_07_eng.pdf). The
real file lists every line of the form (31 rows); an excerpt:

```json
  "vat_declaration": {
    "form_code": "KMD",
    "form_name": "Estonian VAT Return (käibedeklaratsioon)",
    "form_version": "Form KMD valid from 1 July 2025",
    "source_url": "https://www.emta.ee/sites/default/files/documents/2025-07/vorm_kmd_2025_07_eng.pdf",
    "boxes": [
      {"box_number": "1", "box_label": "Acts and transactions taxable at 24%", "tax_code_pattern": "EU-EE-STD", "transaction_type_filter": "sales", "sign_multiplier": 1},
      {"box_number": "1", "box_label": "Acts and transactions taxable at 24%", "tax_code_pattern": "EU-EE-IC-ACQ", "transaction_type_filter": "purchases", "sign_multiplier": 1},
      {"box_number": "2", "box_label": "Acts and transactions taxable at 9%", "tax_code_pattern": "EU-EE-RED", "transaction_type_filter": "sales", "sign_multiplier": 1},
      {"box_number": "2¹", "box_label": "Acts and transactions taxable at 5%", "tax_code_pattern": "EU-EE-RED5-PRESS", "transaction_type_filter": "sales", "sign_multiplier": 1},
      {"box_number": "2²", "box_label": "Acts and transactions taxable at 13%", "tax_code_pattern": "EU-EE-RED13", "transaction_type_filter": "sales", "sign_multiplier": 1},
      {"box_number": "4", "box_label": "Total VAT (...)", "tax_code_pattern": null, "transaction_type_filter": "all", "sign_multiplier": 1, "description": "Computed from the rate lines"},
      {"box_number": "5", "box_label": "Total input VAT deductible", "tax_code_pattern": "%", "transaction_type_filter": "purchases", "sign_multiplier": -1},
      {"box_number": "6", "box_label": "Intra-Community acquisitions of goods and services ..., total", "tax_code_pattern": "EU-EE-IC-ACQ", "transaction_type_filter": "purchases", "sign_multiplier": 1},
      {"box_number": "7", "box_label": "Acquisition of other goods and services subject to VAT", "tax_code_pattern": "EU-EE-RC-FOREIGN", "transaction_type_filter": "purchases", "sign_multiplier": 1}
    ]
  }
```

**Key patterns:**
- `tax_code_pattern` uses SQL LIKE: `%` matches anything, `EU-EE-STD` matches exactly
- `sign_multiplier`: 1 for output/sales, -1 for input/purchases (credits reduce the return)
- Box numbers match the official government form, superscripts included (`1¹`, `2²`)
- A box may have several rows, one per pattern (unique on box number + pattern)
- A box no tax code determines (computed totals, subsets split by goods/services, adjustments) gets `tax_code_pattern: null` and a description
- Every non-null pattern must match a seeded code; Estonia's old `EU-IC` pattern matched none
- Set entire `vat_declaration` to `null` for non-VAT countries
