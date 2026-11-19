# Authoring a country plugin

Country setup stores a country's data in the customer's company. What a
country *calculates* or *files* — payroll gross-to-net, the VAT return — lives
in a country plugin the customer owns: a Claude Code / Cowork plugin with
skills, commands and, where a file must be produced exactly, deterministic
scripts. Arfiti's `arfiti-ee-country-pack` (Estonia) is the worked example:
read it before designing another country's pack.

A country plugin uses the same Arfiti tools as any other client: `query` and
`get_entity` to read, `submit` to write, `get_submissions(action="schema")` for
each operation's live contract. It has no access an external agent lacks, and
every amount it writes is validated, scoped, approved and audited by the
gateway.

## Layout

```
<org>-<cc>-country-pack/
  .claude-plugin/plugin.json      name, description, version
  .mcp.json                       the Arfiti connector
  README.md                       what it does, requirements, what it sends
  commands/<command>.md           one per user action
  skills/<skill>/SKILL.md         the procedure, loaded when the task matches
  skills/<skill>/references/*.md  country rules with sources and dates
  scripts/*.py                    deterministic file generation, if any
```

Country rules (rates, thresholds, form lines, deadlines) belong in the
references with their source and effective date, so the next year's change is
an edit to one file, not a rewrite of the procedure.

## Payroll calculator

What core provides:

- employees, compensation, tax settings and deductions to read
  (`query("employee")`, `query("employee_compensation")`,
  `query("employee_tax_settings")`, `query("employee_deduction")`);
- the payroll taxes and their brackets configured by country setup
  (`query("payroll_tax_jurisdiction")`) — reference data the plugin may read;
- the payroll run lifecycle: `payroll_run.create`, `submit_calculation`,
  `approve`, `process_payment`, `void`;
- posting of the submitted amounts to the payroll vendor lines' accounts
  (`payroll_vendor_config`).

What the plugin does:

1. Read the period's employees and their settings.
2. Calculate gross-to-net with the country's rules from its references:
   brackets, allowances, ceilings, rounding.
3. Submit per employee: `gross_pay`, `net_pay`, totals, and `tax_lines`,
   each with a `line_type` that matches a `payroll_vendor_config.line_type`,
   a `category` (`employee_deduction` or `employer_tax`), the `amount`, a
   `side` (`CR` for an employee deduction, `BOTH` for an employer tax) and a
   `description`.
   The gateway checks that the lines add up to the totals and that net pay is
   gross less employee taxes and deductions; it does not check the country's
   arithmetic. Read `get_submissions(action="schema", object_type="payroll_run",
   operation="submit_calculation")` for the current contract.
4. Show the customer a summary to review before `approve`.

The Estonian `estonian-payroll` skill and its `references/submission-format.md`
show a complete payload; `/generate-tsd` adds the monthly declaration file.

## VAT declaration

What core provides: tax codes with `default_rate`, `tax_scope`,
`is_reverse_charge`, `is_recoverable`, `metadata`; posted transactions and
their tax lines (`query("transaction")`); tax reporting periods
(`query("tax_period")`) and tax returns (`tax_return.create`, `update`, `file`;
filing marks the period filed, and a filed period can no longer be changed).

What the plugin does:

1. Discover the entity's tax codes and classify each one to a line of the
   form by its properties — never by its name or code. Keep the classification
   rules and the form's line structure in the references, with the form
   version and source.
2. Ask the customer to confirm the classification.
3. Aggregate the period's posted transactions per line, run its validation
   checks, and generate the authority's file with a script when the format is
   strict (schema-validated XML, fixed CSV).
4. Record the return (`tax_return`) and leave the upload to the customer.

The Estonian `estonian-vat-declaration` skill classifies codes to KMD lines
from their properties and an entity-level override, then generates the KMD
files with `scripts/generate_kmd.py` against the official XSD.

## Checklist before handing a plugin to the customer

- Every country rule has a source, a read date and an effective date in the
  references.
- No account numbers, tax codes or rates are hard-wired in the procedure;
  they are read from the company or from the references.
- Every write goes through `submit`; the plugin never asks for database access
  or a special endpoint.
- The plugin says what it sends where (connector only, or public web for
  research).
- A test run on a test entity, compared by hand with a known result (an
  official calculator or a prior period filed by the customer's accountant).
