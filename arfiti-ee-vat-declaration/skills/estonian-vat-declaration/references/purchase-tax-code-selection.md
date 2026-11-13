# Estonian purchase bills: tax code selection

How to choose the tax code on an Estonian purchase bill, and the rates it depends on. Where the text says "this role", it means whoever owns VAT for the entity.

This file is maintained here. (Until AR-1207 it was generated from a tax manager role template in the ERP repository; that template and the generation step were removed.)

## VAT Rates (Current — Effective from July 1, 2025)

| Rate | Application |
|------|-------------|
| **24%** | Standard rate — most goods and services (increased from 22% on July 1, 2025) |
| **13%** | Reduced rate — accommodation services, with or without breakfast (increased from 9% on January 1, 2025) |
| **9%** | Reduced rate — books, medicines, medical equipment, press publications in physical or electronic form (press increased from 5% on January 1, 2025; publications mainly made up of advertising or erotic content are at the standard rate) |
| **0%** | Exports outside EU, intra-community supplies (B2B) |

EMTA lists no VAT rate changes for 2026 ([Maksumuudatused 2026](https://www.emta.ee/uudised/maksumuudatused-2026),
checked 2026-10-31). EMTA does not say whether the rates change after 2026; check
the rates page before relying on them for later periods.

A business on cash accounting may, until 31 December 2026, keep the old rate for
some supplies invoiced and made before 1 January 2025: 9% for accommodation
(VAT Act § 46(26), KMD line 2) and 5% for press publications (§ 46(27), line 2¹).
It is a right, not an obligation ([EMTA rates handbook](https://www.emta.ee/node/336/main_chapter/10335/pdf)).

**Source**: [EMTA VAT Rates](https://www.emta.ee/en/business-client/taxes-and-payment/value-added-tax/vat-rates-and-supply-exempt-tax)

**Historical rates:** onboarding creates `EU-EE-STD-22` (22%) and `EU-EE-OLD-20`
(20%) so transactions and credit invoices dated before 1 July 2025 can be imported
and corrected; they are not for current supplies. The 5% code `EU-EE-RED5-PRESS` is
transitional and only for press publications under § 46(27) (cash accounting, invoiced
and made before 1 January 2025); every other press publication is 9% (`EU-EE-RED`).

## Purchase Bills: Tax Code Selection (for AP Clerks)

Estonian guidance for choosing the tax code on a purchase bill. Rates are in "VAT Rates" above;
confirm them against the entity's configured codes (`query(entity_type="tax_code")`) before relying on a table here.

| Vendor Type | Transaction | Tax Code |
|-------------|-------------|----------|
| Domestic Estonian vendor | Standard purchase | `EU-EE-STD` |
| Domestic Estonian vendor | Accommodation (with or without breakfast) | `EU-EE-RED13` |
| Domestic Estonian vendor | Books, press publications, medicines | `EU-EE-RED` |
| EU vendor (B2B) | Goods or services acquisition | `EU-EE-IC-ACQ` |
| Non-EU vendor | Services acquisition | `EU-EE-RC-FOREIGN` |
| Non-EU vendor | Goods imported from outside the EU | Supplier invoice: no Estonian VAT. Import VAT on the customs decision: `EU-EE-IMPORT` (see Tax Code Setup) |
| Domestic reverse charge (VAT Act § 41¹) | Immovables, scrap metal, precious metal, metal products | Not seeded yet (see Tax Code Setup) |

When processing a bill for an Estonian entity:

1. **Identify vendor origin** - Domestic, EU, or non-EU
2. **Determine transaction type** - Goods, services, or special category
3. **Select tax code** - Based on vendor type and transaction (table above)
4. **Verify input VAT deductibility** - Most business purchases qualify for VAT recovery

Example (an Estonian entity):

```javascript
submit(
  object_type: "transaction",
  operation: "post",
  data: JSON.stringify({
    transaction_type_code: "AP_INVOICE",
    legal_entity_id: <entity_id>,   // the Estonian entity
    vendor_id: <vendor_id>,         // an Estonian vendor
    invoice_date: "2026-01-27",
    due_date: "2026-02-26",
    lines: [
      {
        description: "Office supplies",
        quantity: 1,
        unit_price: 85.00,
        account_number: "<expense_account_number>",  // query("account", filters={"account_subtype": "operating_expense"})
        tax_code: "EU-EE-STD"        // Standard 24% Estonian VAT
      }
    ]
  })
)
```

AP Clerks escalate to this role for uncertain tax code selection, reverse charge, cross-border
services, VAT exemptions and KMD/INF reporting queries.
