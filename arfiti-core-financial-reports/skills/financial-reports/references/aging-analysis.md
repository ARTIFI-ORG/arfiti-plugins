# Aging Analysis

## What the server returns

`generate_report("ar_aging" | "ap_aging", {"legal_entity_id": ID, "as_of_date": ..., "report_contract": 1})`:

- `rows`: one row per party with `current`, `days_1_30`, `days_31_60`, `days_61_90`, `days_over_90` and `total`. The party with no id on its documents has `party_id: null`.
- `totals`: the same buckets plus `overdue`, all four past-due buckets summed by the server.
- `details.certified` and `details.control_tie_out`: whether the open documents agree with the control account. `details.documents`: the open documents with due dates and balances.

Amounts are amounts owed, on both agings: positive is owed by the customer (AR) or to the vendor (AP); the server turns the credit-normal AP control balance the same way. A party whose own total is negative is a credit or unapplied amount and stays visible in its bucket. This does not depend on the overall total: a portfolio can net negative or to zero and the owed parties are still owed. A party whose total is unavailable is neither owed nor credit until it is reviewed. Values are in functional currency; the document currency is separate.

## Overdue

Overdue means more than 0 days past due: every amount in 1–30, 31–60, 61–90 and 90+. Current means not yet due. An amount 1–30 days past due is overdue, not "current".

## Days outstanding

DSO = closing AR ÷ revenue × days in the revenue period. DPO = closing AP ÷ cost of sales × days in the period. Use an income statement whose period ends on the aging date, and its actual length. This is an approximation on the closing balance, not an average. It, and the overdue share, are unavailable when the total is not a net amount owed (zero or a net credit) or the revenue or cost of sales is not positive.

## Follow-up and payments: firm policy

Which step follows which bucket (reminder, call, escalation), when to pay a supplier, and which thresholds matter are the firm's or client's policy, not product rules. The plugin's example wording lives in `scripts/ratio_policy.json` (`receivable_follow_up`) and is labelled as an example. Present suggestions; this plugin sends no reminders and schedules no payments.

If the aging is not certified, say so before any follow-up list: its figures may not agree with the ledger.
