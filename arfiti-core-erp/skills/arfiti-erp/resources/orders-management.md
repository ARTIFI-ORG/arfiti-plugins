# Sales & Purchase Orders Management

Sales orders (what a customer agreed to buy) and purchase orders (what you
agreed to buy from a vendor), plus purchase receipts (goods arriving against a
purchase order) and the 2-way / 3-way match controls that connect orders to
real invoices, bills, and payments.

---

## The one rule

**Orders and receipts are documents, not transactions. They never post to the
GL and never appear in financial reports.** Money enters the books only when
an order generates a real AR invoice (`sales_order` → `create_invoice`) or a
real AP bill (`purchase_order` → `create_bill`), or when an independently
posted invoice/bill is *matched* to the order. The order tracks progress
against those postings — it is never itself a posting.

Progress is **derived at read time** from invoice/bill line linkage — never
stored as counters. Voiding an invoice automatically releases the order
quantity it covered; nothing needs to be "un-counted".

Two different progress bases (this is deliberate, not an inconsistency):

- **Sales orders track progress by QUANTITY** — invoicing_status compares
  invoiced quantity per line against ordered quantity.
- **Purchase orders track progress by AMOUNT** — vendor bills often carry no
  real quantities (a bill line is "account, description, amount"), so billing
  progress compares billed amount per line against the ordered line amount.

---

## Sales Orders

### Lifecycle

```
draft ──confirm──→ confirmed ──(fully invoiced)──→ closed
  │                    │
  │                    └──cancel──→ cancelled
  └──delete (draft only, gone entirely)
```

- **draft** — editable; this is also how you represent a *quote* (there is no
  separate quote object).
- **confirmed** — committed; header/lines locked except safe fields; can
  generate invoices.
- **closed** — auto-closes on full invoicing by default
  (`orders.auto_close_on_full_invoice`, absent = true), or close manually.
- **cancelled** — refused while any live invoice linkage exists; unmatch or
  void the invoices first.

### Create

```
submit("sales_order", "create", {
  "legal_entity_id": 12,
  "customer_id": 387,
  "order_date": "2026-09-01",
  "currency": "EUR",
  "customer_reference": "CUST-PO-4711",
  "lines": [
    {"item_id": 5, "quantity": 10},
    {"description": "Onboarding services", "quantity": 1, "unit_price": "1500.00"}
  ]
})
```

- `customer_id` is the **master** customer id (the same id space
  `query("customer")` returns as `master_customer_id`).
- A line needs `item_id` **or** a non-empty `description`; `unit_price` is
  required on lines without `item_id` (with an item it resolves via effective
  pricing and is frozen onto the line).
- Line fields: `item_id`, `description`, `quantity`, `unit_price`,
  `discount_amount`, `tax_code_id`, `is_tax_inclusive`, `unit_of_measure`,
  `dimensions`, `metadata`.
- Pass `"confirm": true` to create directly in confirmed status.
- Optional header fields: `expected_invoice_date`, `payment_term_code`,
  `description`, `dimensions`, `metadata`.

### The other operations

| Operation | Payload essentials | Notes |
|---|---|---|
| `update` | `sales_order_id`, `legal_entity_id`, changed fields; `lines` = full replacement, `edit_reason` | Line replacement refused once any line has live invoice linkage (unmatch first). `customer_id`/`currency` changes are draft-only. |
| `confirm` | `sales_order_id`, `legal_entity_id` | draft → confirmed |
| `cancel` | `sales_order_id`, `legal_entity_id`, `reason` | Refused while live invoice linkage exists |
| `close` | `sales_order_id`, `legal_entity_id` | Manual close (partial deliveries you won't finish) |
| `delete` | `sales_order_id`, `legal_entity_id`, `deletion_reason` | Draft only; removes order + lines entirely |

### Generating the invoice — create_invoice

```
submit("sales_order", "create_invoice", {
  "sales_order_id": 18,
  "legal_entity_id": 12
})
```

Posts a **real AR_INVOICE** through the normal transaction executor (GL, tax,
numbering — everything a directly posted invoice gets) with its lines linked
back to the order lines. Omitting `lines` invoices **all remaining
quantities**; pass `lines` (each `sales_order_line_id` + `quantity`) for a
partial invoice. Over-invoicing beyond remaining quantity is refused under a
lock, so concurrent invoicing cannot double-bill.

### Matching an independently posted invoice — match_invoice / unmatch_invoice

When the invoice already exists (posted directly, or came in through a
connector), link it instead of generating a new one:

```
submit("sales_order", "match_invoice", {
  "sales_order_id": 18,
  "legal_entity_id": 12,
  "transaction_id": 4402
})
```

Omitting `line_pairs` auto-pairs lines by item then by position and **refuses
when ambiguous** — pass explicit `line_pairs`
(`transaction_line_id` + `sales_order_line_id`) to resolve. `unmatch_invoice`
(same payload minus pairs) severs the linkage; progress recomputes
automatically.

---

## Purchase Orders

The mirror of sales orders with the same nine operations — differences only
where the AP world differs:

- `vendor_id` (master vendor id) instead of `customer_id`;
  `vendor_reference`, `expected_receipt_date` instead of the customer fields.
- Vendor-side item pricing falls back to the item's **cost price**, never its
  sell price.
- Progress is **amount-based** (`billing_status`), and auto-close is governed
  by `orders.auto_close_on_full_bill` (absent = true).

### create_bill — generate the AP bill

```
submit("purchase_order", "create_bill", {
  "purchase_order_id": 7,
  "legal_entity_id": 12
})
```

Posts a real AP_INVOICE linked to the order. Omitting `lines` bills **all
remaining amounts**; pass `lines` (each `purchase_order_line_id` + `amount`)
for a partial bill. The remaining-amount cap is enforced under a lock.

### match_bill / unmatch_bill — link an existing bill

Same shape as the sales side (`transaction_id`, optional `line_pairs`).
Matching tolerances are per-org config, and both default to **exact** when
unconfigured:

| Key | Meaning | Absent = |
|---|---|---|
| `orders.po_match_price_tolerance_pct` | Per-line unit-price tolerance (%) | 0 (exact) |
| `orders.po_match_amount_tolerance` | Over-billing allowance, entity currency — bounds the OVER side only, at line and header level | 0 (exact) |

Under-billing is always allowed (that's just a partial bill). A bill linked to
lines of **several** orders is normal (consolidated vendor bills); the order
header's FK then goes NULL by design — line linkage is the truth.

### The bill_processor pass (agent)

When enabled, the bill-processing agent proposes a purchase-order match for
each incoming vendor bill (candidates ranked by closeness; it matches only
when the best candidate clearly beats the runner-up, otherwise flags for
review). Controlled by `orders.po_match_enabled` (absent = OFF) and
`orders.po_match_required` (absent = advisory only). The agent only ever
*matches* — the sole way a purchase order is created is
`submit("purchase_order", "create", ...)`.

---

## Purchase Receipts (goods receipt)

A receipt records **what physically arrived** against a confirmed purchase
order. Quantities only — **a receipt has no prices, no amounts, no GL, no
dimensions**. Its value, when needed, derives from the order's own line
prices. Numbering: `GR-` series.

```
draft ──confirm──→ confirmed
  │                    │
  │                    └──cancel (with reason; keeps the audit trail)
  └──delete (draft only, gone entirely)
```

### Create

```
submit("purchase_receipt", "create", {
  "legal_entity_id": 12,
  "purchase_order_id": 7,
  "receipt_date": "2026-09-03",
  "lines": [
    {"purchase_order_line_id": 21, "received_quantity": "6"},
    {"purchase_order_line_id": 22, "received_quantity": "2.5"}
  ]
})
```

- The order must be **confirmed** (or closed). There is **no `vendor_id`** in
  the payload — the receipt inherits the order's vendor.
- Receipts are always created as **draft**; there is no confirm-on-create
  shortcut.
- `received_quantity` must be > 0, up to 4 decimal places.

### Rules that will bite you if you don't know them

- **Ordered quantity is a hard cap, checked at confirm.** Confirming a receipt
  that would take a line's total confirmed-received quantity over its ordered
  quantity is refused — over-receipt is not accepted, with no tolerance. If
  goods genuinely over-shipped, the remedy is to update the order's quantity
  first (possible only before receipts pin the lines — see next point) or
  receive only up to the cap and handle the surplus outside the order.
- **Only confirmed receipts count** toward received progress. Draft receipts
  reserve nothing.
- `update` is **draft-only** (full line replacement). A confirmed receipt
  records physical reality: it can only be **cancelled** (reason required),
  never edited.
- **`delete` is draft-only** and is the only operation that removes a
  receipt's line references. A receipt that was ever confirmed — even if
  since cancelled — permanently blocks `purchase_order.update` (line
  replacement) and `purchase_order.delete` for that order. If a draft receipt
  is blocking order maintenance, use `purchase_receipt.delete`, not `cancel`.

---

## 3-Way Match (order ↔ receipt ↔ bill payment gate)

When `orders.three_way_match_required` is on (absent = **OFF**), the payment
proposal agent checks every AP bill whose lines link to purchase-order lines:
**billed amount must not exceed received value** (received quantity × the
order line's effective price), per order. Bills that fail are **held out of
payment batches** — the run summary lists each held bill with the reason.

- The gate lives at the **payment stage only**. Creating or matching a bill is
  never blocked by receiving status — refusing the link would only hide the
  discrepancy the gate exists to surface.
- A bill with **no** order-linked lines passes vacuously (nothing to check).
- `orders.po_match_amount_tolerance` is reused as the over-billing allowance.
- To release a held bill: receive the goods (create + confirm the receipt),
  or fix the bill, or (deliberately) turn the key off for that org/entity.

**Never enable `orders.three_way_match_required` on a database that does not
have the purchase-receipt tables (migration 526)** — the check would error and
fail the whole payment run.

---

## Reading orders, receipts, and progress

```
query("sales_order", filters={"legal_entity_id": 12, "status": "confirmed"})
query("purchase_order", query="PO-000007")
query("purchase_receipt", filters={"purchase_order_id": 7})

get_entity("sales_order", id=18)      # header + lines + derived progress + related invoices
get_entity("purchase_order", id=7)    # header + lines + billing progress + related bills + receipts
get_entity("purchase_receipt", id=3)
```

Derived fields you'll see (never stored, always current):

- Sales: `qty_invoiced` per line, `invoicing_status`
  (not_invoiced / partial / fully_invoiced) — quantity-based.
- Purchase: billed amount per line, `billing_status` — amount-based.
- Receipts: received quantity per order line — **confirmed receipts only**.

The admin dashboard shows the same data read-only under Records → Sales
Orders / Purchase Orders (plus an Orders tab and open-order-backlog KPI on
each customer and vendor page). **There is deliberately no order entry in the
admin UI** — orders are created only through this gateway (Claude, agents,
connectors).

---

## Config keys (all per-org/entity via config_settings; all have safe defaults)

| Key | Absent means |
|---|---|
| `orders.auto_close_on_full_invoice` | true — SO auto-closes when fully invoiced |
| `orders.auto_close_on_full_bill` | true — PO auto-closes when fully billed |
| `orders.po_match_price_tolerance_pct` | 0 — exact price match |
| `orders.po_match_amount_tolerance` | 0 — no over-billing allowance |
| `orders.po_match_enabled` | false — bill_processor PO pass OFF |
| `orders.po_match_required` | false — advisory only |
| `orders.three_way_match_required` | false — payment gate OFF |

## Approvals

Every order and receipt operation runs through the workflow engine on the
**green lane by default** (no approval stop). An org can tighten any single
operation to yellow/red approval on the workflow definitions page — orders are
not special-cased in the approval system.

## Common pitfalls

- **Don't put order lines on an invoice by editing the invoice.** Linkage is
  managed only by `create_invoice`/`create_bill`/`match_*`/`unmatch_*`.
- **Amounts vs quantities:** a vendor bill's "quantity" is usually fictional
  (defaults to 1) — that is exactly why PO progress is amount-based. Never
  judge a purchase order "partially billed" from quantities.
- **Currency:** an order's backlog and progress figures are in the order's own
  currency; nothing converts silently.
- **Cancelling an order** requires releasing invoice/bill linkage first; the
  refusal message names the exact operation to run.
- **Order lines with receipts are pinned** (see the receipt rules above) —
  plan order edits before receiving begins.


### Explicit purchase bill account

purchase_order.create_bill accepts optional account_number for all generated bill lines, overriding item/vendor defaults. Use a verified account for description-only orders lacking a vendor default. Without an explicit choice, item account then vendor default is used; missing mappings refuse posting.

### Billing before final goods receipt

Full billing may close a purchase order before all goods arrive. Both receipt
creation and confirmation accept confirmed or closed orders; draft and cancelled
orders remain ineligible. Confirmation still enforces cumulative confirmed receipts
at or below each ordered quantity. Closing a PO does not grant permission to exceed
that cap or to bill it again. Receipts remain documents with no independent GL posting.

If a previously generated bill used the wrong account, the fix affects future bill
creation only. Preserve the posted evidence and correct through the supported
reversal/reposting workflow; do not edit posted GL rows. Verify the replacement's
item/account choice and resulting PO linkage before resuming volume tests.
