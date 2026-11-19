# Estonian Tax Code Classification

This reference describes how to classify Estonian tax codes into KMD lines
using their **properties**. Do NOT rely on specific tax code names — clients
may have custom codes. Always classify by properties.

## Classification Properties

Each tax code in `v_tax_codes_effective` has these relevant properties. `query("tax_code")`
returns `default_rate`, `tax_scope`, `is_reverse_charge`, `is_recoverable` and `is_active`;
`get_entity` on one code adds `tax_type` and `description`. `country_code`, `metadata` and
`reporting_code_override` are not returned by either tool today, so do not rely on them
unless the user supplies them.

| Property | Type | Description |
|---|---|---|
| `default_rate` | Decimal | Tax rate as a percentage (24, 13, 9, 0 — not 0.24) |
| `is_reverse_charge` | Boolean | Whether reverse charge mechanism applies |
| `is_recoverable` | Boolean | Whether input VAT is recoverable |
| `tax_type` | String | Category (e.g., 'output', 'input', 'import', 'reverse_charge') |
| `tax_scope` | String | Jurisdictional scope, the PRIMARY line-6-vs-7 signal (vocabulary enforced by a DB CHECK, see migration 464): `domestic`, `intra_union_goods`, `intra_union_services`, `import`, `foreign_reverse_charge`, `export`, `exempt`. NULL on unclassified org-local/imported codes — ask the user how to report those. |
| `country_code` | String | Always 'EE' for Estonian codes |
| `metadata` | JSONB | Additional flags (e.g., `{"kmd_element": "importVat", "is_import": true}`) |
| `reporting_code_override` | String | Entity-level KMD element override (if set, use this directly) |

## Classification Decision Tree

Targets are **KMD2 element names** (see `references/kmd-form-structure.md`). Reverse-charge
purchase bases go INTO the rate line (`transactions24`) — that drives the self-assessed
line 4 — with the informative breakout on lines 6/7 and the deductible VAT accumulated
into `inputVatTotal` (line 5).

```
1. Does the tax code have `reporting_code_override`?
   YES → Use that KMD2 element directly
   NO  → Continue to step 2

2. Is `is_reverse_charge = true`?  (base line derived from `tax_scope`.
   `reporting_code_override` is the only explicit override — step 1;
   `metadata.kmd_line` is a FALLBACK for NULL-scope codes only: legacy seed
   packs carry stale kmd_line values that do not match the official form)
   YES → by tax_scope:
         - `intra_union_goods` or `intra_union_services` (IC acquisition, EU supplier)
                                    → euAcquisitionsGoodsAndServicesTotal (line 6)
             · `intra_union_goods` subset → euAcquisitionsGoods (line 6.1)
         - `foreign_reverse_charge` (services from a non-EU supplier)
                                    → acquisitionOtherGoodsAndServicesTotal (line 7)
         - `domestic` (§ 41¹ domestic reverse charge: immovables/scrap/precious metal)
                                    → acquisitionOtherGoodsAndServicesTotal (line 7),
                                      incl. acquisitionImmovablesAndScrapMetalAndGold (line 7.1)
         - NULL scope → do NOT guess between line 6 and 7: fall back to
           `metadata.kmd_line` if present, otherwise ask the user.
         (The acquisition BASE also goes into the rate line — transactions24 — per
          EMTA guidance; 6/7 are informative. If recoverable, add the self-assessed
          VAT to inputVatTotal, line 5.)
   NO  → Continue to step 3

3. Check `default_rate` on the SALES side (base):
   - 24 → transactions24 (line 1)          - 5  → transactions5 (line 2¹)
   - 22 → transactions22 (line 1²)         - 13 → transactions13 (line 2²)
   - 20 → transactions20 (line 1¹)         - 9  → transactions9 (line 2)
   (22% and 20% appear on a current return only through credit invoices for
    earlier supplies.)
   - 0    → by counterparty:
            - Non-EU customer          → exportZeroVat (line 3.2)
            - EU business + goods      → euSupplyGoodsZeroVat (3.1.1) within euSupplyInclGoodsAndServicesZeroVat (3.1)
            - EU business + services   → euSupplyInclGoodsAndServicesZeroVat (3.1)
            - other zero-rated         → transactionsZeroVat (line 3)

4. For PURCHASE-side tax codes (VAT amounts):
   - `is_recoverable = true` → add to inputVatTotal (line 5)
            · on a fixed-asset account → also fixedAssetsVat (line 5.2)
            · import VAT paid in customs (`tax_scope='import'`, e.g. `EU-EE-IMPORT`; older codes
              may use `tax_type='import'` / `metadata.is_import`) → also importVat (line 5.1)
```

## Standard Estonian Tax Codes (Onboarding Pack)

These are the codes onboarding creates for an Estonian entity
(`mcp-server/src/data/onboarding/ee.json`). Clients may rename them or hold imported
codes; classify by properties, not by name.

| Code | Rate | Reverse Charge | KMD2 element (line) |
|---|---|---|---|
| `EU-EE-STD` | 24% | No | `transactions24` (1) |
| `EU-EE-STD-22` | 22% | No | `transactions22` (1²) — historical |
| `EU-EE-OLD-20` | 20% | No | `transactions20` (1¹) — historical |
| `EU-EE-RED` | 9% | No | `transactions9` (2) |
| `EU-EE-RED13` | 13% | No | `transactions13` (2²) |
| `EU-EE-RED5-PRESS` | 5% | No | `transactions5` (2¹) — transitional, press under § 46(27) only |
| `EU-EE-ZERO` | 0% | No | `transactionsZeroVat` (3); exports also `exportZeroVat` (3.2) |
| `EU-EE-IC-SUPPLY` | 0% | No | `transactionsZeroVat` (3) + `euSupplyInclGoodsAndServicesZeroVat` (3.1); goods also `euSupplyGoodsZeroVat` (3.1.1) |
| `EU-EE-IC-ACQ` | 24% | Yes | base in `transactions24` (1) + `euAcquisitionsGoodsAndServicesTotal` (6), goods also `euAcquisitionsGoods` (6.1); VAT in `inputVatTotal` (5) |
| `EU-EE-RC-FOREIGN` | 24% | Yes | base in `transactions24` (1) + `acquisitionOtherGoodsAndServicesTotal` (7); VAT in line 5 |
| `EU-EE-EXEMPT` | 0% | No | `supplyExemptFromTax` (8) |
| `EU-EE-IMPORT` | 24% | No | VAT in `inputVatTotal` (5) and `importVat` (5.1); base in no line |

`EU-EE-IMPORT` is import VAT paid at customs (`tax_scope: "import"`, not reverse charge):
only the deduction is declared. Import VAT declared in the return under VAT Act
§ 38(2¹)-(2³) (line 4¹, with EMTA's authorisation) is not seeded. Domestic reverse charge under VAT Act § 41¹ (immovables, scrap metal,
precious metal) is not seeded yet; an organisation that needs it adds the code itself with
`tax_scope: "domestic"`, once the bill agent's reverse-charge code selection respects scope.
Such a code goes to lines 7 and 7.1 (`acquisitionImmovablesAndScrapMetalAndGold`), base also
in line 1. Organisations onboarded before AR-1025 may lack `EU-EE-RED13` and
`EU-EE-RC-FOREIGN`, and may hold an `EU-EE-RC` code whose meaning varies (often 0% without
the reverse-charge flag, which carries no self-assessed VAT): ask the user how those lines
were meant to be reported.

## Discovery Query

Always start by fetching the entity's actual tax codes:

```
query("tax_code", filters={"legal_entity_id": <id>, "is_active": true})
```

Then classify each code using the decision tree above. Present the classification
to the user for confirmation before calculating KMD amounts.
