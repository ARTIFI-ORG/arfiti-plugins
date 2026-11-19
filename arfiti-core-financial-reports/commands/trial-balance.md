---
name: trial-balance
description: Present the server's trial balance with its full-selection totals and reconciliation verdict, and point out balances that are unusual for their account type.
---

# Trial Balance

Presents the server's trial balance as of a date.

## Usage

```
/arfiti-core-financial-reports:trial-balance
```

Requires Python 3.9+ (`python3 --version`) when a formatter runs.

## Rules

- Add `"report_contract": 1` to every `generate_report` call and save the result **unchanged** as JSON. Never retype amounts, re-classify accounts, sum rows into totals or round them.
- A `null` amount is **Unavailable**, never zero. Show every evidence gap, warnings included.
- If the result is `success: false`, show its message (for example `REPORT_SCOPE_FORBIDDEN`: the user has no access to that entity) and stop.
- If the formatter exits with code 2, show its reason and fix the request; do not work around it.

## Step 1: Fetch

```
generate_report("trial_balance", {"legal_entity_id": ID, "as_of_date": "YYYY-MM-DD", "report_contract": 1})
```

For a prior date, make a second call.

## Step 2: Build the table from the result

- Header: entity, `dates.effective`, `currency.code`; quality, every gap, and partial delivery from `coverage`.
- Rows: account number, name, `account_type`, and the server's `opening_signed`, `movement_debit`, `movement_credit`, `closing_debit`, `closing_credit`. Keep a `null` as Unavailable.
- Totals: the server's `totals` (full selection), never a sum of the displayed rows.
- Verdict: `details.reconciliation.status`, as returned.

## Present

Show the table and the server's verdict. A `difference` or `unavailable` verdict is reported as such with the gaps. Don't present a balanced result built from missing amounts.

Point out balances unusual for their type (a debit closing balance on a revenue account, a credit on an expense account) as items to review, not as errors: refunds and contra accounts are legitimate.
