# Finance & Accounting Roles

This section defines the key roles in a finance and accounting department, their responsibilities, and typical workflow permissions.

## Available Roles

| Role | Primary Function | Typical Approval Authority |
|------|------------------|-------------------|
| [AP Clerk](ap-clerk.md) | Vendor invoice processing | Green lane only |
| [AR Clerk](ar-clerk.md) | Customer invoice and collections | Green lane only |
| [Assets Manager](assets-manager.md) | Fixed asset lifecycle management | Yellow lane |
| Staff Accountant | Journal entries and reconciliation | Green lane only |
| Senior Accountant | Month-end close and review | Yellow lane |
| Accounting Manager | Department oversight | Yellow lane |
| Controller | Financial reporting and controls | Red lane |
| CFO | Financial strategy and compliance | Red lane |
| Tax Manager (the organisation's tax role) | VAT declarations and tax compliance | Yellow lane |
| Payroll Manager (the organisation's payroll role) | Payroll processing and TSD filings | Yellow lane |
| [Data Migration Specialist](data-migration-specialist.md) | Bulk imports and system migrations | Yellow lane |

Lanes are assigned by your organisation's workflow rules; the submit() result is authoritative.

## Role Hierarchy

```
CFO
└── Controller
    ├── Assets Manager
    ├── Data Migration Specialist
    └── Accounting Manager
        ├── Senior Accountant
        │   └── Staff Accountant
        ├── AP Supervisor
        │   └── AP Clerk
        └── AR Supervisor
            └── AR Clerk
```

## Workflow Permissions

Typical defaults. Each organisation configures which operations fall in which lane and which approval steps each lane runs; report outcomes from the `status` and `lane` in the submit() result.

### Green Lane (typically no approval step)
- Small transactions under threshold
- Standard vendor/customer maintenance
- Routine journal entries

### Yellow Lane (typically manager approval, where configured)
- Medium-risk transactions
- New vendor/customer creation
- Period adjustments

### Red Lane (typically executive approval, where configured)
- Large transactions
- Intercompany transfers
- Period close operations
- Vendor/customer deletions

## Country-Specific Roles

Country-specific roles define compliance obligations, tax calculations, filing procedures, and deadlines for each jurisdiction.

### Estonia (EE)

| Role | Primary Function | Key Filings |
|------|------------------|-------------|
| Payroll Manager (EE) | Payroll processing and TSD filings | TSD (Annex 1, 4, 5), employment register |
| Tax Manager (EE) | VAT declarations and tax compliance | KMD + KMD INF, EC Sales List (VD) |
| Annual Report Manager (EE) | Annual report preparation and filing | Majandusaasta aruanne |
| Corporate Tax Manager (EE) | CIT on distributions, WHT, transfer pricing | TSD Annex 7, INF forms |
| Trade Reporter (EE) | Intrastat and customs compliance | Intrastat dispatches, customs declarations |

### United Kingdom (UK)

| Role | Primary Function | Key Filings |
|------|------------------|-------------|
| Payroll Manager (UK) | PAYE, NI, RTI submissions, pensions | FPS, EPS, P11D, P60 |
| VAT Manager (UK) | MTD VAT returns, PVA | Quarterly VAT return via MTD |
| Corporation Tax Manager (UK) | CT600, capital allowances, R&D claims | CT600, iXBRL accounts |
| Annual Accounts Manager (UK) | Companies House filings | Annual accounts, CS01 |
| Customs & Trade Manager (UK) | Post-Brexit import/export declarations | CDS customs declarations, PVA |

---

## Segregation of Duties

The system enforces segregation of duties:

1. **AP Segregation**: Different users must:
   - Create vendor records
   - Enter invoices
   - Approve payments

2. **AR Segregation**: Different users must:
   - Create customer records
   - Generate invoices
   - Apply payments

3. **GL Segregation**: Different users must:
   - Enter journal entries
   - Approve journal entries
   - Post to ledger
