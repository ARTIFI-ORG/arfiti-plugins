# Aging Analysis

## What the server returns

`generate_report("ar_aging" | "ap_aging", {"legal_entity_id": ID, "as_of_date": ..., "report_contract": 1})`:

- `rows`: one row per party with `current`, `days_1_30`, `days_31_60`, `days_61_90`, `days_over_90` and `total`. The party with no id on its documents has `party_id: null`.
- `totals`: the same buckets plus `overdue`, all four past-due buckets summed by the server.
- `details.certified` and `details.control_tie_out`: whether the open documents agree with the control account. `details.documents`: the open documents with due dates and balances.

Amounts are signed as booked against the control account. A party whose balance has the opposite sign to a non-zero total is a credit or unapplied amount; it stays visible in its bucket. When the total nets to zero or is unavailable, no sign tells credits apart: review the negative and positive balances as two groups. Values are in functional currency; the document currency is separate.

## Overdue

Overdue means more than 0 days past due: every amount in 1–30, 31–60, 61–90 and 90+. Current means not yet due. An amount 1–30 days past due is overdue, not "current".

## Days outstanding

DSO = closing AR ÷ revenue × days in the revenue period. DPO = closing AP ÷ cost of sales × days in the period. Use an income statement whose period ends on the aging date, and its actual length. This is an approximation on the closing balance, not an average.

## Follow-up and payments: firm policy

Which step follows which bucket (reminder, call, escalation), when to pay a supplier, and which thresholds matter are the firm's or client's policy, not product rules. The plugin's example wording lives in `scripts/ratio_policy.json` (`receivable_follow_up`) and is labelled as an example. Present suggestions; this plugin sends no reminders and schedules no payments.

If the aging is not certified, say so before any follow-up list: its figures may not agree with the ledger.
