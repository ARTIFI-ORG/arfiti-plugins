# Country setup operations

Every write goes through `submit(object_type, operation, payload)`; every read
through `query("<entity>")`. Before a write, read the operation's current
fields with `get_submissions(action="schema", object_type=..., operation=...)`
— the lists below name the fields that matter for country setup and mark the
required ones with `*`; the schema is the authority if they ever differ.

**Scope.** *Organisation* records are shared by every legal entity in the
organisation. *Entity* records take `legal_entity_id` and belong to that
entity; an id-based update or delete is refused for a record of an entity the
caller cannot reach.

**Onboarding.** While onboarding is open, only the types marked *allowed
during onboarding* are accepted.

| Area | Operations | Scope | Read back |
|---|---|---|---|
| Tax codes | `tax_code.create/update/delete` | Organisation | `query("tax_code")` |
| Tax code rate components | `tax_code_rate.create/update/delete` | Organisation or entity | no `query` entity yet: the submit receipt, then the tax code's quick view in Records → Tax codes |
| Tax authorities | `tax_authority.create/update/delete` | Organisation | `query("tax_authority")` |
| Tax jurisdictions | `tax_jurisdiction.create/update/delete` | Organisation | `query("tax_jurisdiction")` |
| Tax registrations | `tax_registration.create/update/delete` | Entity | `query("tax_registration")` |
| Tax filing forms | `tax_filing_form.create/update/delete` | Organisation | `query("tax_filing_form")` |
| Payment classifications | `payment_classification.create/update/delete` | Organisation | `query("payment_classification")` |
| Tax reporting periods | `tax_reporting_period.create/update/delete` | Entity | `query("tax_period")` |
| Withholding tax rates | `withholding_tax_rate.create/update/deactivate` | Entity | `query("withholding_tax_rate")` |
| Payroll taxes | `payroll_tax_jurisdiction.create/update` | Organisation | `query("payroll_tax_jurisdiction")` |
| Payroll vendor lines | `payroll_vendor_config.create/update` | Entity | `query("payroll_vendor_config")` |
| Government payees | `vendor.create/update` | Organisation | `query("vendor")` |
| Accounts | `account.create/update` | Organisation, entity override | `query("account")` |
| Per-diem rates | `per_diem_rate.create/update/delete`, `per_diem_policy.*` | Entity | `query("per_diem_rate")`, `query("per_diem_policy")` |
| Mileage rates | `mileage_rate.create/update/delete` | Entity | `query("mileage_rate")` |

Of these, accepted while onboarding is open: `tax_code`, `tax_authority`,
`tax_jurisdiction`, `tax_registration`, `vendor`, `account` (the onboarding
allow-list also covers other master data).

## Units — the most common mistake

| Field | Unit | Example |
|---|---|---|
| `tax_code.default_rate`, `tax_code_rate.rate` | percentage points, 0–100 | `22` means 22 % |
| `withholding_tax_rate.withholding_rate` | percentage points, 0–100 | `20` means 20 %. A value between 0 and 1 is refused as a likely fraction. |
| `payroll_tax_jurisdiction.rate`, `employee_rate`, `employer_rate` | fraction, 0–1 | `0.33` means 33 % |
| `payroll_tax_jurisdiction.tax_brackets[].rate` | fraction, 0–1 | `{"min": 0, "max": 9000, "rate": 0.0}` |
| per-diem and mileage amounts | money in the record's `currency` | always send `currency` |

## Areas

### Tax codes — `tax_code`

`tax_code*`, `tax_name*`, `tax_type*`, `default_rate`, `tax_scope`,
`is_reverse_charge`, `is_recoverable`, `is_tax_inclusive`, `country_code`,
`state_province`, `jurisdiction_level`, `sales_account_number`,
`purchase_account_number`, `default_tax_account_number`, `metadata`.

- One code per rate the company actually uses, including zero-rated, exempt
  and reverse-charge treatments where they apply. There is no minimum number.
- `tax_scope` says how the code is used (domestic, intra-EU, export, import,
  reverse charge…); `get_submissions(action="schema")` lists the accepted
  values. A VAT declaration plugin reads it, so set it deliberately.
- A regional rate (US state, Canadian province, Swiss canton) is its own code
  with `jurisdiction_level` and `state_province`, never a national code with
  the most common rate.
- A tax code itself has no effective dates. For a code taxed at its own rate
  (`calculation_method = 'rate'`, the default), a rate change is a new code,
  with the old one deactivated when it stops being used. For a code taxed by
  its components, a rate change is a dated component (next section). Posted
  documents keep the code and the tax they were posted with.
- A code needs its tax account: `default_tax_account_number`, or both
  `sales_account_number` and `purchase_account_number` (an `exempt` code needs
  none). The accounts are the customer's choice by type and subtype.

### Tax code rate components — `tax_code_rate`

`master_tax_code_id*`, `rate*` (percentage points), `effective_from*`,
`effective_to`, `legal_entity_id`, `component_name`, `calculation_order`,
`taxable_basis`, `applies_on_component`, `is_compound`, `tax_account_number`.

Posting uses components **only for a code that opts in**. A tax code is taxed
either at its own `default_rate` (`calculation_method = 'rate'`, the default)
or by its rate components (`'components'`, set with `tax_code.update`).
Components on a `rate` code are stored but do not change what posts; `fixed`
and `tiered` also post as `rate`. Opt in only for a tax the customer confirmed
is made of separate parts (a state plus a county rate, a compound levy), and
say which codes you switched.

For a `components` code, posting:

- takes the components **active and effective on the document date**; an
  entity's own components (`legal_entity_id` set) replace the organisation's
  as a set for that entity;
- applies them in `calculation_order`; a compound component (`is_compound:
  true`, `applies_on_component` = the `component_name` of an earlier
  component) is charged on the line plus that component; any other component
  needs `taxable_basis` `subtotal` or `net_amount` (`gross` and `custom` are
  refused at posting);
- rounds each component half-up and books it as its own tax GL line, recorded
  in `transaction_line_taxes`. `tax_account_number` is an output (sales-side)
  account; without it the code's sales account is used. Purchase documents
  book input tax to the code's purchase account. A component account the
  entity does not have refuses the posting;
- back-solves the combined rate for tax-inclusive prices;
- **refuses** a line when no component is effective on the document date. It
  never posts it untaxed, so the components must cover every date the code
  will be used on.

Units and dates: `rate` is percentage points (`7.25` means 7.25 %); dates are
`YYYY-MM-DD`; `effective_to` is the last day the component applies, or empty.
Keep the code's `default_rate` equal to the combined rate: posting ignores it
for a `components` code, but tax reports label the code with it and the bill
agent matches supplier invoices against it.

Booked history does not move:

- A rate change is a new component from its `effective_from`, with the old
  one ended by `effective_to` the day before. Do not edit the rate of a
  component that documents were posted with.
- Once a component is booked, `tax_code_rate.update` refuses a change to its
  name or compound setting.
- `tax_code_rate.delete` deactivates the component; it is not removed, and
  documents already posted keep what they booked.
- A credit memo reverses what the invoice it credits booked, whatever the
  code's method or components are today.
- Switching a code between `rate` and `components` changes new postings only.

**Verify** (there is no `query` entity for components yet):

1. `query("tax_code")` and check `calculation_method` and `default_rate` on
   the code.
2. Check each component's submit receipt (`tax_code_rate_id`), then open the
   code's quick view in Records → Tax codes and compare each component's
   name, rate, order, basis, compound setting, account and dates with what
   the customer confirmed.
3. Check coverage: for every date the code will be used on, at least one
   active component is effective, and the components add up to the
   confirmed total.
4. If the customer wants proof of the arithmetic, post one test document
   only with their yes and in a period they choose, read its tax lines back,
   and reverse it. Never post a test document without that yes.

### Tax authorities, jurisdictions, registrations

- `tax_authority`: `code*`, `name*`, `jurisdiction_type*`, `country_code*`,
  `authority_type*`, `region_code`, `filing_frequency`, `website_url`,
  `metadata` (`filing_deadline_day` is read by onboarding's calendar
  generator; keep it only when the deadline really is a fixed day of the
  following month).
- `tax_jurisdiction`: `code*`, `name*`, `jurisdiction_type*`,
  `country_code*`, `tax_authority_id` (from `query("tax_authority")`),
  `parent_jurisdiction_id`, `state_code`, `metadata`.
- `tax_registration`: `legal_entity_id*`, `registration_number*`,
  `registration_type*`, `effective_from*`, `tax_authority_id`,
  `jurisdiction_id`, `filing_frequency`, `next_filing_date`. The
  registration number comes from the customer's documents, never from
  research.

### Filing forms and payment classifications

- `tax_filing_form`: `country_code*`, `form_code*`, `tax_authority_id`,
  `form_name`, `filing_frequency`, `due_day_of_period_end`, `metadata`.
- `payment_classification`: `country_code*`, `slug*`, `external_code*`
  (the authority's code for the payment type), `description`,
  `applicable_forms`, `metadata`.

### Tax reporting periods — `tax_reporting_period`

- `create`: `legal_entity_id*`, `period_type*`, `period_start*`,
  `period_end*`, `filing_due_date*`, `tax_authority_id`, `notes`.
- `update`: `period_id*`, `period_start`, `period_end`, `filing_due_date`,
  `notes`, `reason`. Open periods only; a period a tax return refers to keeps
  its dates. New dates must stay ordered and must not overlap another period
  of the same entity and authority.
- `delete`: `period_id*`, `reason*`. Open periods with no tax return only.

`period_type` is `monthly`, `quarterly` or `annual`. Each period carries its
real filing due date from an official source, after `period_end`; periods of
the same entity and authority must not overlap. Calendars onboarding does not
generate — due 60 days after the quarter, due on the last day of the next
month, annual — are created period by period with their actual dates. A
bimonthly or other cycle has no `period_type`: report it to the customer as
unsupported rather than storing it as monthly or quarterly.

### Withholding tax rates — `withholding_tax_rate`

- `create`: `legal_entity_id*`, `country_code*`, `payment_type*`,
  `withholding_rate*` (percentage points), `effective_from*`, `effective_to`,
  `minimum_threshold`, `gl_account_number` (an active account of the entity),
  `description`, `metadata`.
- `update`: `withholding_tax_rate_id*` plus the fields to change. It cannot
  clear `effective_to` or `minimum_threshold`; deactivate and create a new rule
  instead. `metadata` replaces the stored object: read, merge, send.
- `deactivate`: `withholding_tax_rate_id*`, `reason`. The row is kept.

One rule per entity, country, payment type and `effective_from`. A changed
rate from a new date is a new rule; end the old one so two rules are not
active for the same payment type. Domestic statutory rates and treaty rates
are different rules: record which one, and the treaty, in `metadata`.

### Payroll taxes — `payroll_tax_jurisdiction`

`country_code*`, `tax_type*`, `tax_name*`, `effective_from*`, `rate`,
`employee_rate`, `employer_rate` (fractions), `wage_base_limit`,
`minimum_wage_base`, `tax_brackets`, `state_code`, `locality_code`,
`effective_to`, `metadata`.

- Progressive taxes put their brackets in the **`tax_brackets`** field — a
  list of `{"min": <amount>, "max": <amount or null>, "rate": <fraction>}`,
  optionally with a `name` — not in `metadata`. Brackets are reference data: no core code calculates
  with them; the country payroll plugin does.
- A tax with no confirmed rate is not created with a null rate to fill a
  list; leave it open.
- Regional payroll taxes take `state_code` / `locality_code`.

### Payroll vendor lines and government payees

- `vendor.create` for each authority the employer pays: `vendor_name*`,
  `vendor_type`, `tax_id`, `country`, `website`, `notes`. Payment details come
  from the authority's official page; confirm them with the customer.
- `payroll_vendor_config.create`: `legal_entity_id*`, `line_type*`,
  `master_vendor_id` (from `query("vendor")`), `expense_account_number`
  (employer-side cost), `payable_account_number` (the liability). Accounts
  are chosen by the customer by type and subtype.

### Accounts — `account`

`account.create` for an account the customer decides is missing (type,
subtype and number theirs). `account.update` with `metadata` **replaces the
whole metadata object**: read the account first, merge, send the merged object.
Filing categories are `metadata.filing_categories`.

### Per-diem and mileage — `per_diem_rate`, `per_diem_policy`, `mileage_rate`

- `per_diem_rate.create`: `legal_entity_id*`, `country_code*`,
  `daily_rate*`, `effective_from*`, `currency`, `region`, `city`,
  `first_last_day_rate`, `breakfast_deduction`, `lunch_deduction`,
  `dinner_deduction` (send all three, `0` where none applies),
  `tier_threshold_days` and `tier_daily_rate` (together or not at all).
- `mileage_rate.create`: `legal_entity_id*`, `vehicle_type*`,
  `rate_per_unit*`, `effective_from*`, `currency`, `distance_unit`,
  `tier_threshold`, `tier_rate`, `tiers`, `max_amount_per_month`.
- Every rate carries its own `effective_from` and `currency`. A new year's
  rate is a new record from its date.
- Statutory tax-free limits and the company's own reimbursement policy are
  different things; ask which one the customer wants recorded.

## Not stored by core

| Topic | Where it lives |
|---|---|
| VAT return box mapping | The country VAT declaration plugin |
| Payroll gross-to-net arithmetic | The country payroll calculator plugin |
| Deduction templates (pension schemes, garnishments, benefits) | Reference for the payroll plugin; employee deductions are set per employee |
