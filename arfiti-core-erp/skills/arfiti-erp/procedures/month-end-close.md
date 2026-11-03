

## Card purchase policy

Use the backend purchase workspace and shared matching decision; do not implement a competing card matcher in conversation. Preserve provider rows and show net purchase spend. Reference conflicts and competing candidates require review. A paid/settled item can still lack documentation; attach missing source evidence to the existing bill. Evidence review, waiver and grouping use `card_purchase.manage` with current version, evidence fingerprint and reason. Never infer write-off authority from matching tolerance.

Receipt follow-up belongs to the purchase obligation, with one owner and deduplicated reminder stages. Automation and delivery are report-only until the entity rollout settings are explicitly enabled. Statement coverage and opening/movement/closing balance controls must pass independently of agent match counts. August deletion/replay requires its own reviewed manifest and explicit authorization through transaction.delete; implementation permission does not authorize it.

Legacy payment-pass descriptions below apply to non-card AP/AR behavior. Card rows use the shared purchase policy and cannot use nearest-date refund pairing, fuzzy amount identity or adjusting-journal workarounds.

# Month-End Close Procedure

## Overview

The month-end close process ensures all financial transactions are recorded, reconciled, and reported accurately for the period.

## Timeline

| Day | Activity | Owner |
|-----|----------|-------|
| Day 1 | Transaction cutoff | All |
| Day 2 | Subledger close | AP/AR |
| Day 3 | Reconciliations | Staff Accountant |
| Day 4 | Adjusting entries | Senior Accountant |
| Day 5 | Financial statements | Controller |

## Pre-Close Checklist

### Before Period End

- [ ] Notify all departments of cutoff dates
- [ ] Review pending transactions
- [ ] Confirm all invoices received
- [ ] Process recurring entries
- [ ] Complete intercompany billing

## Close Procedures

### Step 1: Transaction Cutoff (Day 1)

1. **AP Cutoff**
   - Process all vendor invoices dated in period
   - Review invoice queue for completeness
   - Create accruals for unbilled items
   - Verify 3-way match completion

2. **AR Cutoff**
   - Process all revenue for period
   - Apply all received payments
   - Review deferred revenue schedule
   - Calculate bad debt provision

3. **Payroll Cutoff**
   - Ensure all payroll posted
   - Calculate accrued wages
   - Review benefit accruals

### Step 2: Subledger Close (Day 2)

1. **Close Accounts Payable**
   ```
   Workflow: Run AP aging report
   Workflow: Review open invoices
   Workflow: Post final AP entries
   Action: Close AP subledger
   ```

2. **Close Accounts Receivable**
   ```
   Workflow: Run AR aging report
   Workflow: Review open invoices
   Workflow: Post final AR entries
   Action: Close AR subledger
   ```

3. **Close Fixed Assets**
   ```
   Workflow: Run depreciation for period
   Workflow: Review asset additions
   Workflow: Post depreciation entries
   Action: Close FA subledger
   ```

### Step 3: Reconciliations (Day 3)

1. **Bank Reconciliation**
   - Download bank statements
   - Match cleared transactions
   - Research outstanding items
   - Post reconciling entries

2. **Intercompany Reconciliation**
   - Verify IC balances match
   - Research differences
   - Post correcting entries

3. **Balance Sheet Reconciliation**
   - Reconcile all balance sheet accounts
   - Document support for balances
   - Clear reconciling items

### Step 4: Adjusting Entries (Day 4)

1. **Standard Adjustments**
   - Prepaid expense amortization
   - Accrued expenses
   - Deferred revenue recognition
   - Inventory adjustments

2. **Non-Standard Adjustments**
   - Error corrections
   - Reclassifications
   - Estimates updates

3. **Review Process**
   ```
   Workflow: Submit adjusting entries
   Workflow: Senior Accountant reviews
   Workflow: Controller approves
   Action: Post approved entries
   ```

### Step 5: Financial Statements (Day 5)

1. **Generate Reports**
   - Trial balance
   - Income statement
   - Balance sheet
   - Cash flow statement

2. **Review Process**
   - Controller reviews statements
   - Variance analysis
   - Management discussion

3. **Close Period**
   ```
   Action: Lock period from changes
   Action: Document close completion
   Action: Archive support
   ```

## Post-Close Activities

### Documentation
- [ ] Save final trial balance
- [ ] Archive reconciliations
- [ ] Document any issues
- [ ] Update close checklist

### Analysis
- [ ] Prepare variance analysis
- [ ] Review KPIs
- [ ] Identify trends
- [ ] Prepare management commentary

## Key Accounts Checklist

### Assets
- [ ] Cash reconciled
- [ ] AR agrees to subledger
- [ ] Inventory valued
- [ ] Prepaids amortized
- [ ] Fixed assets depreciated

### Liabilities
- [ ] AP agrees to subledger
- [ ] Accruals reasonable
- [ ] Deferred revenue current
- [ ] Debt balances confirmed

### Income Statement
- [ ] Revenue complete
- [ ] COGS accurate
- [ ] Expenses coded correctly
- [ ] Intercompany eliminated

## Common Issues

| Issue | Resolution |
|-------|------------|
| Late invoices | Accrue if material |
| Missing receipts | Use estimate with documentation |
| Reconciling items | Research before close |
| System errors | Log ticket, post manual entry |

## Sign-Off

| Role | Responsibility | Sign-Off |
|------|----------------|----------|
| Staff Accountant | Reconciliations complete | _____ |
| Senior Accountant | Adjustments reviewed | _____ |
| Controller | Statements approved | _____ |

## Evidence required before closing

- Run reconciliation for the explicit period; an all-open scan is a different scope.
  Historical run items and manual action counts are audit records, not unresolved work.
- Read AP/AR aging at the close date in functional currency. Require usable dated
  application history and independent control tie-outs; do not certify a failed or
  uncertified report just because the trial balance balances.
- Require bank statements for accounts with movement/nonzero balances, honoring
  explicit internal-account configuration. Compare GL with provider closing balances.
- Review due amortization lines and live recognition journals, not just a successful
  earlier run. Empty asset registers do not justify skipping nonzero asset costs.
- Review control-account signs and aged prepaid/clearing balances using account roles.
- Compare VAT controls with a retained authority account statement at period end.
  A filed return or claim amount alone is not the authority account balance. The
  `external_vat_account_statement` contract requires as_of, currency, payable_balance,
  account_numbers, source_reference, attachment_id and content_hash on the tax return;
  the stored attachment belongs to that same TAX_RETURN and entity.
- Equal payout amounts do not establish duplicate reimbursement. Resolve exact
  source links/references across earlier expense-report periods and inspect cumulative
  payments. Keep this deterministic source check separate from LLM commentary.
- The built-in saga is optional orchestration; external clients use supported operations and shared controls. Inspect actual approval configuration. `closed_without_close_saga` means
  a direct close bypassed the checklist; it is not evidence that checks passed.


## Evidence interpretation

The close check does not infer payroll absence from a scan. Seeded periods without runs continue to fail with “payroll absence not established; payroll applicability policy not configured”. Diagnostic evidence lists the adjacent-month window, salary/benefit account nets, accrued-payroll movement, compensation and employee count in functional currency, plus the most recent earlier net-debit month. No periods with non-run evidence warns “Not determined: payroll source policy not configured”; no periods and no signal retains the existing not-applicable result with an explicit absence caveat. Void/canceled payment documents do not settle a run. Carried payroll policy remains future work.

The close check reports each contract’s recorded attempts separately from service-period coverage. A completed run header alone no longer proves coverage. Recorded billed intervals and eligible same-entity invoices dated by period end establish coverage; the current engine schedule classifies gaps. A future billing pointer, no-usage skip, or manual invoice description never proves coverage. A convention invoice date falling after period end is labelled “accrual not tested”. No new billing policy block is introduced: incomplete coverage retains the old no-completed-run failure or reports a warning when that old check passed.

Filing evidence matches a return’s own period or a reporting period for the same entity and authority. Candidate forms are selected by country or overlapping authority registration. An unfiled selected form without an applicability rule is advisory not_determined, not “missing” or “not expected”. Quarterly selection still assumes calendar quarters and says so; this is a disclosed existing selection limitation, not a universal tax rule.
