# Custom Fields

Organisations define their own fields for facts the product has no column
for: a contract number, a review date, a preferred contact method, a PO
reference on a bill. Nothing about a particular field is built in; each
organisation's register decides which fields exist, their types, and which
are required.

Available on: customers, vendors, items, employees, projects, fixed assets
and transaction headers (`applies_to`: `customer`, `vendor`, `item`,
`employee`, `project`, `fixed_asset`, `transaction`).

**Before putting a business fact into `metadata`, `description` or
`reference_number`, check whether a custom field exists for it.** A list of
choices used to classify records for reporting (segment, region, channel) is
a dimension, not a custom field (dimensions-management resource).

## Find the organisation's fields

- `query("custom_field")` lists the register (key, label, type, limits,
  options, `applies_to`, `transaction_types`, archived or active).
- `get_submissions(action="schema", object_type="<kind>", operation="create")` (for
  transactions `operation="post"`) lists the active fields for that kind with
  their type, limits, active choice options and whether they are required.
  A transaction field required only for some types shows
  `required_for_transaction_types`.

## Define a field (admin)

```javascript
submit("custom_field", "create", {
  "key": "po_reference",            // lowercase letters, digits, _; starts with a letter
  "label": "PO reference",
  "field_type": "text",             // text | decimal | boolean | date | choice
  "applies_to": ["transaction"],
  "transaction_types": ["AP_INVOICE", "AP_CREDIT_MEMO"],   // optional, transactions only
  "constraints": {"max_length": 40}
})
```

- Types and limits: `text` (`max_length`), `decimal` (`scale`, `min`, `max`;
  send large values as numeric strings), `boolean`, `date` (`YYYY-MM-DD`,
  `min`, `max`), `choice` (`options: [{"value", "label"}]`, one value).
- The key and type never change, and keys are never reused. A new meaning
  needs a new field.
- `custom_field.update` changes label, description, limits, options,
  `applies_to` or `transaction_types`. A change that would make stored values
  invalid, or leave values on a kind or transaction type the field no longer
  covers, is refused and names the records; retire a choice option with
  `"active": false` instead of removing it. Dropping a record kind or a
  transaction type a workflow (live or draft) requires the field for is
  refused too, naming the workflow: remove that requirement first.
- `custom_field.archive` stops new values; stored values stay readable and
  can still be cleared. It is refused while a workflow definition (live or
  an open draft) requires the field.
- All three need `admin:write`.

## Set values

```javascript
submit("customer", "create", {..., "custom_fields": {"contract_number": "C-2026-017"}})
submit("customer", "update", {"customer_id": 42,
                              "custom_fields": {"credit_score": "720.50"},
                              "custom_fields_clear": ["review_date"]})
```

- A write is a **patch**: keys left out are unchanged. `custom_fields_clear`
  empties named fields. Never send `null`; a key cannot be set and cleared at
  once.
- Values are checked against the register on submit and again inside the
  write's transaction; an unknown key, an archived field, a wrong type, too
  many decimals or an inactive choice is refused with the reason and nothing
  is written.
- **Required fields** come from the organisation's `create` workflow
  definition (`"custom_fields.<key>"` in `required_payload_fields`; for
  transactions the `transaction.post` definition, shared or per transaction
  type). A create or posting without them is refused; an update cannot clear
  them. Agents' own submissions are held to the same rule, so ask for the
  value rather than guessing it.
- Same contract on every kind: `customer`, `vendor`, `item`, `employee`,
  `project`, `fixed_asset` create and update. Fixed-asset updates name the
  asset's legal entity. A project update may change only custom fields.

## Transactions

- Fields apply to customer invoices and credit notes, vendor bills and credit
  notes, and journal entries (`AR_INVOICE`, `AR_CREDIT_MEMO`, `AP_INVOICE`,
  `AP_CREDIT_MEMO`, `JOURNAL_ENTRY`), or only to the types a field names.
  Payments, bank entries and system postings take none.
- Set them at posting: `"custom_fields": {...}` on `transaction.post`.
- Correct one later with an update that sends only the fields (and optionally
  `edit_reason`):

  ```javascript
  submit("transaction", "update", {"transaction_id": 123, "legal_entity_id": 10,
                                   "custom_fields": {"po_reference": "PO-4471"},
                                   "edit_reason": "PO number corrected"})
  ```

  Allowed in an open, closed or VAT-locked period; it changes nothing else and
  the ledger activity records the old and new values, who and why. Combined
  with other fields it follows the normal update restrictions.
- **Exception:** a journal held by a bank or card match keeps its header fixed
  after posting; its custom fields cannot be corrected. Set them when posting.
- A reversal copies the original's values. Values never change amounts, tax
  or the GL, and are not printed on invoices.

## Find records by value

```javascript
query("customer", filters={"custom_fields.contract_number": "C-2026-017"})
query("vendor", filters={"custom_fields.contact_method": ["email", "phone"]})
query("item", filters={"custom_fields.weight_kg": {"gte": 10}})
query("transaction", filters={"custom_fields.po_reference": "PO-4471", "legal_entity_id": 10})
query("employee", filters={"custom_fields.badge": None})              // no value
query("project", filters={"custom_fields.sponsor": {"exists": True}})
```

- Equality is exact (`10.5` matches `10.50`); ranges work on decimal and date
  fields only. "No value" differs from `false` or `0`. An unregistered key is
  an error that lists the registered ones.
- `get_entity` and lists return `custom_fields` (archived fields included);
  `bill` is an alias of `transaction` here.

## Import, merge, history

- CSV import (customers, vendors, items, employees, fixed assets,
  transactions): map a column to `custom_fields.<key>`. An empty cell sets or
  changes nothing. Required fields apply to rows that create a record; every
  transaction row creates one. A transaction row's value must suit its type,
  or the row is refused.
- Customer or vendor merge: values only the losing record holds fill the
  winner; conflicting values need `"custom_fields_resolution": {"<key>":
  "winner" | "loser"}`.
- History: master records' changes are in `query("master_activity")` (employee
  personal data masked); transaction corrections are in the transaction's
  activity. Erasure requests use `submit("master_activity", "redact", …)`.

## In the dashboard

Configuration › Custom fields shows the register and each field's history;
owners and admins set Required per workflow there (for transactions, per
transaction type on `transaction.post`). Record pages show values read-only. Defining a field and setting
values stay with `submit`.

## Not available

Per-entity values, multi-choice fields, formulas, fields that drive posting or
tax, values on transaction lines, printing values on issued documents.

Full contract: `docs/GUIDES/GUIDE_CUSTOM_FIELDS.md`.
