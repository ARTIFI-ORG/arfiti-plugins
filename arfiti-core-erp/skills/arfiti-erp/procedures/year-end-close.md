

## Card purchase policy

Use the backend purchase workspace and shared matching decision; do not implement a competing card matcher in conversation. Preserve provider rows and show net purchase spend. Reference conflicts and competing candidates require review. A paid/settled item can still lack documentation; attach missing source evidence to the existing bill. Evidence review, waiver and grouping use `card_purchase.manage` with current version, evidence fingerprint and reason. Never infer write-off authority from matching tolerance.

Receipt follow-up belongs to the purchase obligation, with one owner and deduplicated reminder stages. Automation and delivery are report-only until the entity rollout settings are explicitly enabled. Statement coverage and opening/movement/closing balance controls must pass independently of agent match counts. August deletion/replay requires its own reviewed manifest and explicit authorization through transaction.delete; implementation permission does not authorize it.

Legacy payment-pass descriptions below apply to non-card AP/AR behavior. Card rows use the shared purchase policy and cannot use nearest-date refund pairing, fuzzy amount identity or adjusting-journal workarounds.

# Year-End Close Procedure

## Scope and system capability

This is an adaptable accountant checklist, not a claim that the app automatically
performs these steps. Country-specific examples, reserve percentages and the
calendar below require the entity’s approved policy. No automatic year-end
closing-entry workflow is implemented by month-end b1. The journal below is a
conceptual example, not an executable payload; discover the current operation
schema and review each entry before submission. A close result does not prove
that every manual reconciliation in this checklist was performed.

## Overview

Year-end close completes the fiscal year, prepares for external audit, and ensures proper transition to the new year.

## Timeline

| Phase | Timing | Activities |
|-------|--------|------------|
| Pre-Close | 2 weeks before YE | Planning, cutoffs |
| Initial Close | Week 1 of new year | Standard close |
| Year-End Adjustments | Week 2-3 | Estimates, accruals |
| Audit Preparation | Week 3-4 | PBC schedules |
| Final Close | Week 4+ | Audit adjustments |

## Pre-Close Activities

### 4 Weeks Before Year-End

- [ ] Schedule year-end close meeting
- [ ] Distribute cutoff dates to departments
- [ ] Request fixed asset inventory
- [ ] Schedule physical inventory count
- [ ] Collect the vendor tax details the entity's jurisdiction needs for year-end vendor tax reporting (ask the tax role)

### 2 Weeks Before Year-End

- [ ] Review open purchase orders
- [ ] Clear old outstanding items
- [ ] Review capitalization thresholds
- [ ] Confirm intercompany balances
- [ ] Update depreciation schedules

## Year-End Close Steps

### Phase 1: Transaction Cutoff

#### Revenue Recognition
- [ ] Review all revenue contracts
- [ ] Verify delivery/performance
- [ ] Calculate percentage of completion
- [ ] Defer unearned revenue
- [ ] Accrue unbilled revenue

#### Expense Cutoff
- [ ] Accrue all known liabilities
- [ ] Review prepaid expense amortization
- [ ] Process all vendor invoices
- [ ] Estimate unbilled items
- [ ] Record inventory obsolescence

### Phase 2: Inventory & Fixed Assets

#### Physical Inventory
1. Count all inventory
2. Compare to system
3. Research variances
4. Post adjustments
5. Calculate LIFO/FIFO reserves

#### Fixed Asset Review
1. Verify all additions capitalized
2. Run full-year depreciation
3. Review impairment indicators
4. Write off abandoned assets
5. Reconcile to subledger

### Phase 3: Estimates & Reserves

#### Bad Debt Reserve
```
Review AR aging
Calculate reserve %:
- Current: 0.5%
- 30 days: 2%
- 60 days: 10%
- 90 days: 25%
- 120+ days: 50%

Post adjustment to bring reserve to calculated amount
```

#### Warranty Reserve
- Review warranty claims history
- Calculate reserve as % of sales
- Adjust reserve balance

#### Other Reserves
- Legal contingencies
- Environmental liabilities
- Restructuring reserves

### Phase 4: Tax Provisions

#### Income Tax Provision
1. Calculate book income
2. Identify permanent differences
3. Identify temporary differences
4. Calculate current tax
5. Calculate deferred tax
6. Record provision entry

#### Other Taxes
- [ ] Property tax accrual
- [ ] Sales/use tax reconciliation
- [ ] Payroll tax reconciliation

### Phase 5: Reconciliations

Complete reconciliations for:
- [ ] All bank accounts
- [ ] All intercompany accounts
- [ ] All balance sheet accounts
- [ ] Payroll clearing accounts
- [ ] Fixed asset subledger

### Phase 6: Final Adjustments

#### Standard Year-End Entries
- Bonus accruals
- Vacation accruals
- Insurance true-ups
- Rent straight-lining

#### Post-Close Adjustments
- Audit adjustments (space reserved)
- Tax return adjustments
- Error corrections

## Audit Preparation

### Prepared by Client (PBC) List

Common PBC items:
- [ ] Trial balance
- [ ] GL detail for all accounts
- [ ] Bank reconciliations
- [ ] AR aging
- [ ] AP aging
- [ ] Fixed asset roll-forward
- [ ] Inventory listing
- [ ] Debt schedule
- [ ] Equity roll-forward
- [ ] Revenue breakdown
- [ ] Expense breakdown
- [ ] Related party transactions
- [ ] Legal letters

### Supporting Schedules

Create schedules for:
1. **Cash**
   - Bank reconciliations
   - Restriction analysis

2. **Receivables**
   - Aging summary
   - Bad debt reserve analysis
   - Large balance confirmations

3. **Inventory**
   - Physical count documentation
   - Obsolescence analysis
   - Cost layer analysis

4. **Fixed Assets**
   - Additions/disposals
   - Depreciation calculation
   - Impairment analysis

5. **Payables**
   - Vendor confirmations
   - Accrual support
   - Large balance analysis

6. **Revenue**
   - Contract analysis
   - Revenue recognition memos
   - Deferred revenue support

## Close Journal Entries

### Year-End Close Entry
```json
{
  "transaction_type": "JE",
  "description": "Close revenue/expense to retained earnings",
  "lines": [
    {"account": "Revenue accounts", "debit": "Total revenue"},
    {"account": "Expense accounts", "credit": "Total expenses"},
    {"account": "Retained Earnings", "credit/debit": "Net income"}
  ]
}
```

### Dividend Declaration (if applicable)
```json
{
  "transaction_type": "JE",
  "description": "Dividend declaration",
  "lines": [
    {"account": "Retained Earnings", "debit": "Dividend amount"},
    {"account": "Dividends Payable", "credit": "Dividend amount"}
  ]
}
```

## System Activities

### Before Close
- [ ] Run all recurring entries
- [ ] Process depreciation
- [ ] Generate required reports
- [ ] Create audit data exports

### Closing the Year
- [ ] Close all 12 periods
- [ ] Review any required closing journals under the entity’s policy; no automatic year-end entry is implied
- [ ] Verify retained earnings roll-forward
- [ ] Lock prior year

### New Year Setup
- [ ] Open new fiscal year
- [ ] Copy recurring entries
- [ ] Update budget
- [ ] Set up new period structure

## Sign-Off Checklist

| Item | Preparer | Reviewer | Date |
|------|----------|----------|------|
| Revenue cutoff | _____ | _____ | _____ |
| Expense cutoff | _____ | _____ | _____ |
| Inventory count | _____ | _____ | _____ |
| Fixed assets | _____ | _____ | _____ |
| Reserves | _____ | _____ | _____ |
| Tax provision | _____ | _____ | _____ |
| Reconciliations | _____ | _____ | _____ |
| Financial statements | _____ | _____ | _____ |

## Final Close Certification

I certify that the year-end close procedures have been completed:

Controller: _________________ Date: _________

CFO: _________________ Date: _________
