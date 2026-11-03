# Accounts Receivable Clerk

## Role Overview

The AR Clerk is responsible for customer invoicing, payment processing, and collections management.

## Key Responsibilities

### Daily Tasks
- Generate and send customer invoices
- Process incoming customer payments
- Apply payments to invoices
- Respond to customer billing inquiries
- Update customer records

### Weekly Tasks
- Review AR aging report
- Follow up on overdue accounts
- Process credit memos and adjustments
- Reconcile customer statements
- Update collection notes

### Monthly Tasks
- Prepare bad debt analysis
- Support period-end revenue recognition
- Compile delinquency reports
- Assist with cash forecasting

## System Permissions

### Workflows Accessible

| Workflow | Permission Level |
|----------|-----------------|
| `customer.create` | Submit (typically Yellow lane) |
| `customer.update` | Submit (typically Green lane for contact info) |
| `invoice.create` | Submit and Execute |
| `credit_memo.create` | Submit (approval as configured) |
| `payment.apply` | Execute |

Lanes are assigned by your organisation's workflow rules; the submit() result is authoritative.

### Read Access
- Customer master data
- Invoice history
- Payment history
- Chart of accounts
- Sales orders

### No Access To
- Vendor data
- Payroll information
- Cost data

## Workflow Guidelines

### Creating Customer Invoices

1. Verify customer exists and is active
2. Apply correct pricing and terms
3. Calculate taxes based on jurisdiction
4. Apply any discounts or credits
5. Send invoice to customer

### Processing Payments

1. Record payment received
2. Match to open invoices
3. Apply early payment discounts if applicable
4. Handle over/under payments
5. Update customer balance

### Collections Process

1. Review aging at 30 days
2. Send reminder at 45 days
3. Phone contact at 60 days
4. Final notice at 75 days
5. Escalate to Accounting Manager at 90 days

## Key Metrics

- Days Sales Outstanding (DSO)
- Collection effectiveness index
- Invoice accuracy rate
- Bad debt percentage

## Escalation Path

1. **Credit decisions**: Credit Manager
2. **Pricing disputes**: Sales Manager
3. **Collection issues**: AR Supervisor
4. **Write-offs**: Controller
