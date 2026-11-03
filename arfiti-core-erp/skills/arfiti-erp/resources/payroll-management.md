# Payroll Management Guide

> **MSEO release contract:** Master employee IDs identify people; payroll/compensation keep legal-entity employment scope even where their numeric IDs equal the master. A person ID is not a dimension value ID. See the dimensions-management resource for assignment, approval and compatibility rules.

This guide explains how to manage payroll in the AI-Native ERP system, including employee compensation, tax settings, deductions, and payroll processing.

---

## Overview

The payroll system supports multi-country payroll processing with a **plugin-based calculation architecture**:
- The ERP backend is **country-agnostic** — it stores data and receives pre-calculated results
- Country-specific tax calculation logic lives in **Cowork plugins** (e.g., `arfiti-ee-payroll-calculator`)
- Claude.ai reads employee data via MCP tools, calculates payroll using plugin formulas, and submits results via `submit_calculation`
- Employees are paid directly via `employee_bank_accounts` (not through vendor mappings)

**Supported Countries (via Plugins):**
- **Estonia**: `arfiti-ee-payroll-calculator` plugin — Income tax (22%), Social tax (33%), Unemployment, Funded pension
- Additional countries can be added by creating new plugins without any backend code changes

**What you can do:**
- Configure employee compensation (salary, hourly, commission)
- Set up tax withholding (W-4 settings, Estonian pension tier)
- Manage deductions (401k, health insurance, garnishments)
- Process payroll (submit calculation, approve, post GL and prepare a payment batch; transmit and confirm separately)
- Generate tax declarations (941, W-2, Estonian TSD)

**Available Workflows:**

| Workflow | Purpose | Typical lane |
|----------|---------|-----------|
| [`employee_compensation.create`](#create-compensation) | Set up salary/hourly rate | Yellow |
| [`employee_compensation.update`](#update-compensation) | Modify compensation | Yellow |
| [`employee_tax_settings.create`](#create-tax-settings) | Configure tax withholding | Yellow |
| [`employee_tax_settings.update`](#update-tax-settings) | Modify tax settings | Yellow |
| [`employee_deduction.create`](#create-deduction) | Add benefit deduction | Yellow |
| [`employee_deduction.update`](#update-deduction) | Modify deduction | Yellow |
| [`payroll_period.create`](#create-period) | Define pay period | Green |
| [`payroll_period.close`](#close-period) | Close completed period | Green |
| [`payroll_run.create`](#create-run) | Start payroll batch | Green |
| [`payroll_run.submit_calculation`](#submit-calculation) | Submit pre-calculated payroll results | Green |
| [`payroll_run.approve`](#approve-payroll) | Approve for payment | Red |
| [`payroll_run.process_payment`](#process-payment) | Post payroll GL and prepare a payment batch; transmission is separate | Red |
| [`payroll_run.void`](#void-run) | Void incorrect run | Red |
| [`payroll_run.update`](#update-run) | Relink run to a different payroll period (labels only) | Yellow |
| [`payroll_vendor_config.create`](#create-vendor-config) | Map tax type to vendor | Green |
| [`payroll_vendor_config.update`](#update-vendor-config) | Update vendor mapping | Green |

Lanes are assigned by your organisation's workflow rules; the submit() result is authoritative.

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

---

## Database Tables

### 3-Table Payroll Data Architecture

The **Cowork plugin** reads three tables via MCP tools to calculate payroll — all tax rates are stored in the database (no hardcoded rates in code or plugins):

| # | Table | What It Stores | How Plugin Uses It |
|---|-------|----------------|-------------------|
| 1 | `payroll_tax_jurisdictions` | Statutory base rates per country/state | Plugin reads rates for the employee's country_code |
| 2 | `employee_tax_settings` | Per-employee modifiers | Plugin reads pension tier, exemption, filing status |
| 3 | `employee_deductions` | Voluntary + court-ordered deductions | Plugin reads active deductions to calculate amounts |

**Rate changes require NO code changes** — update `payroll_tax_jurisdictions` in the DB. Plugins read rates dynamically at calculation time.

### Core Tables

| Table | Purpose |
|-------|---------|
| `employee_compensation` | Salary, hourly rates, commission settings |
| `employee_tax_settings` | Tax withholding configuration (W-4, pension tier) — **CRITICAL: sets country_code for calculator** |
| `employee_deductions` | Benefits (401k, health insurance, garnishments, multi-country) |
| `payroll_tax_jurisdictions` | Tax rates by country/state/locality (loaded dynamically by calculator) |
| `payroll_periods` | Pay period definitions |
| `payroll_runs` | Payroll batch execution |
| `payroll_run_details` | Per-employee calculations |
| `payroll_run_detail_lines` | Vendor-linked sub-lines per employee |
| `payroll_vendor_config` | Maps tax/deduction types to vendors per entity |

---

## Employee Compensation

### Complete Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

**Required Fields:**
- `employee_id` (integer) - Employee to configure
- `legal_entity_id` (integer) - Legal entity
- `compensation_type` (enum) - Type of compensation
  - Options: `salary`, `hourly`, `commission`, `contract`, `stipend`
- `pay_frequency` (enum) - Payment schedule
  - Options: `monthly`, `bi_weekly`, `weekly`, `semi_monthly`, `annual`
- `base_amount` (decimal) - Base salary or hourly rate
- `currency` (string, 3 chars) - Currency code (USD, EUR, etc.)
- `effective_from` (date) - Start date (YYYY-MM-DD)

**Optional Fields:**
- `standard_hours_per_week` (decimal) - For hourly employees (default: 40)
- `overtime_multiplier` (decimal) - Overtime rate (default: 1.5)
- `effective_to` (date) - End date (null = current)
- `metadata` (jsonb) - Country-specific settings

### Create Compensation

Use the `employee_compensation.create` workflow.

**Salaried Employee:**
```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="employee_compensation", operation="create")

// Step 2: Submit with discovered fields
// Tip: Use validate_only=true to check payload before submitting
```
```json
{
  "employee_id": 42,
  "legal_entity_id": 13,
  "compensation_type": "salary",
  "pay_frequency": "monthly",
  "base_amount": 75000.00,
  "currency": "USD",
  "effective_from": "2025-01-01",
  "metadata": {"flsa_exempt": true}
}
```

**Hourly Employee:**
```json
{
  "employee_id": 43,
  "legal_entity_id": 13,
  "compensation_type": "hourly",
  "pay_frequency": "bi_weekly",
  "base_amount": 25.00,
  "currency": "USD",
  "standard_hours_per_week": 40.00,
  "overtime_multiplier": 1.50,
  "effective_from": "2025-01-01"
}
```

**Getting Reference Data:**
- Employees: Use `query("employee")` to find employee IDs
- Legal Entities: Use `query("legal_entity")` to find entity IDs

### Update Compensation

Use the `employee_compensation.update` workflow.

**Salary Increase:**
```json
{
  "compensation_id": 15,
  "base_amount": 82500.00,
  "effective_from": "2025-07-01"
}
```

---

## Employee Tax Settings

### Complete Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

**Required Fields:**
- `employee_id` (integer) - Employee to configure
- `legal_entity_id` (integer) - Legal entity
- `country_code` (string, 2 chars) - Country code (US, EE, DE, etc.)
- `tax_id_type` (enum) - Type of tax ID
  - Options: `ssn`, `personal_id`, `nin`, `sin`, `steuer_id`, `nif`
- `effective_from` (date) - Start date

**US-Specific Fields:**
- `state_code` (string, 2 chars) - State code (CA, NY, TX, etc.)
- `filing_status` (enum) - W-4 filing status
  - Options: `single`, `married_filing_jointly`, `married_filing_separately`, `head_of_household`
- `allowances` (integer) - W-4 allowances (pre-2020 form)
- `additional_withholding` (decimal) - Extra withholding per period
- `tax_id_number` (string) - Social Security Number (encrypted)

**Estonia-Specific Fields:**
- `pension_tier` (enum) - II pillar contribution rate
  - Options: `2%`, `4%`, `6%`
- `basic_exemption_applied` (boolean) - Apply monthly exemption
- `basic_exemption_employer_id` (integer) - Which employer applies exemption
- `tax_id_number` (string) - Personal ID code (isikukood)

### Create Tax Settings

Use the `employee_tax_settings.create` workflow.

**US Employee:**
```json
{
  "employee_id": 42,
  "legal_entity_id": 13,
  "country_code": "US",
  "state_code": "CA",
  "tax_id_type": "ssn",
  "tax_id_number": "123-45-6789",
  "filing_status": "married_filing_jointly",
  "allowances": 2,
  "effective_from": "2025-01-01",
  "metadata": {"w4_version": "2020", "step3": 4000}
}
```

**Estonian Employee:**
```json
{
  "employee_id": 50,
  "legal_entity_id": 14,
  "country_code": "EE",
  "tax_id_type": "personal_id",
  "tax_id_number": "38501010001",
  "pension_tier": "2%",
  "basic_exemption_applied": true,
  "effective_from": "2025-01-01",
  "metadata": {"employment_register_id": "12345678"}
}
```

### Update Tax Settings

Use the `employee_tax_settings.update` workflow.

**Change Filing Status:**
```json
{
  "tax_settings_id": 25,
  "filing_status": "single",
  "allowances": 1
}
```

**Change Pension Tier (Estonia):**
```json
{
  "tax_settings_id": 30,
  "pension_tier": "6%"
}
```

---

## Employee Deductions

### Complete Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

**Required Fields:**
- `employee_id` (integer) - Employee
- `legal_entity_id` (integer) - Legal entity
- `deduction_type` (string) - Type of deduction (free-form, any value allowed)
- `deduction_name` (string) - Display name
- `calculation_method` (string) - How to calculate
  - Options: `fixed`, `percentage`, `per_hour`
- `effective_from` (date) - Start date

**Common Deduction Types (US):**
- Benefits: `health_insurance`, `dental`, `vision`, `life_insurance`
- Retirement: `401k`, `roth_401k`, `403b`, `hsa`, `fsa`
- Legal: `garnishment`, `child_support`
- Other: `union_dues`, `other`

**Common Deduction Types (Estonia):**
- Voluntary: `pension_iii`, `health_insurance`, `union_fees`, `loan_repayment`
- Court orders: `court_enforcement`, `child_support`
- Employer costs: `fringe_benefit_income_tax`, `fringe_benefit_social_tax`
- Benefits: `gym_benefit`, `parking`, `lunch_benefit`, `phone_plan`

**Amount Fields (based on calculation_method):**
- `amount` (decimal) - Fixed amount per period (for `fixed`)
- `percentage` (decimal) - Percentage of gross 0.0-1.0 (for `percentage`)
- `per_hour_rate` (decimal) - Rate per hour worked (for `per_hour`)

**Limits:**
- `annual_limit` (decimal) - Maximum annual deduction

**Employer Match (retirement plans):**
- `employer_match_percentage` (decimal) - Match rate (e.g., 0.50 = 50%)
- `employer_match_limit` (decimal) - Maximum employer match

**Classification & Vendor Linkage:**
- `is_mandatory` (boolean) - Mandatory deduction (court orders, statutory requirements)
- `deduction_category` (string) - Category for grouping: `voluntary_benefit`, `court_order`, `employer_cost`, `other`
- `master_vendor_id` (integer) - Vendor who receives this deduction payment (per-employee override)
- `payable_account_number` (string) - GL liability account for this deduction
- `expense_account_number` (string) - GL expense account (for employer-side costs)

**Tax Treatment:**
- `is_pre_tax` (boolean) - Pre-tax deduction (reduces taxable income)
- `reduces_federal_tax` (boolean) - Reduces federal taxable income
- `reduces_state_tax` (boolean) - Reduces state taxable income
- `reduces_social_security` (boolean) - Reduces Social Security wages
- `reduces_medicare` (boolean) - Reduces Medicare wages

**Garnishment Fields:**
- `garnishment_case_number` (string) - Court case number
- `garnishment_agency` (string) - Collecting agency (IRS, state, etc.)
- `garnishment_priority` (integer) - Processing order

**One-Time Deductions:**
- Set `effective_from = effective_to` (same date or same month) for deductions that should only apply once
- Example: A court enforcement for a single month uses `effective_from: "2026-02-01"`, `effective_to: "2026-02-28"`

### Create Deduction

Use the `employee_deduction.create` workflow.

**401(k) with Employer Match (US):**
```json
{
  "employee_id": 42,
  "legal_entity_id": 13,
  "deduction_type": "401k",
  "deduction_name": "401(k) Contribution",
  "calculation_method": "percentage",
  "percentage": 0.06,
  "annual_limit": 23000.00,
  "employer_match_percentage": 0.50,
  "employer_match_limit": 6000.00,
  "is_pre_tax": true,
  "deduction_category": "voluntary_benefit",
  "effective_from": "2025-01-01"
}
```

**III Pillar Pension (Estonia):**
```json
{
  "employee_id": 50,
  "legal_entity_id": 12,
  "deduction_type": "pension_iii",
  "deduction_name": "III Pillar Pension (LHV)",
  "calculation_method": "fixed",
  "amount": 200.00,
  "is_pre_tax": true,
  "is_mandatory": false,
  "deduction_category": "voluntary_benefit",
  "master_vendor_id": 47,
  "payable_account_number": "2250",
  "effective_from": "2026-01-01"
}
```

**Health Insurance:**
```json
{
  "employee_id": 42,
  "legal_entity_id": 13,
  "deduction_type": "health_insurance",
  "deduction_name": "Medical - Family Plan",
  "calculation_method": "fixed",
  "amount": 450.00,
  "is_pre_tax": true,
  "deduction_category": "voluntary_benefit",
  "effective_from": "2025-01-01"
}
```

**Court Enforcement (one-time, Estonia):**
```json
{
  "employee_id": 50,
  "legal_entity_id": 12,
  "deduction_type": "court_enforcement",
  "deduction_name": "Court order #2026-1234",
  "calculation_method": "fixed",
  "amount": 500.00,
  "is_pre_tax": false,
  "is_mandatory": true,
  "deduction_category": "court_order",
  "payable_account_number": "2710",
  "effective_from": "2026-02-01",
  "effective_to": "2026-02-28"
}
```

**Garnishment (US):**
```json
{
  "employee_id": 45,
  "legal_entity_id": 13,
  "deduction_type": "garnishment",
  "deduction_name": "IRS Tax Levy",
  "calculation_method": "fixed",
  "amount": 500.00,
  "is_pre_tax": false,
  "is_mandatory": true,
  "deduction_category": "court_order",
  "garnishment_case_number": "2024-12345",
  "garnishment_agency": "Internal Revenue Service",
  "garnishment_priority": 1,
  "effective_from": "2025-01-01"
}
```

### Update Deduction

Use the `employee_deduction.update` workflow.

**Increase 401(k) Contribution:**
```json
{
  "deduction_id": 78,
  "percentage": 0.10
}
```

**End Deduction:**
```json
{
  "deduction_id": 78,
  "effective_to": "2025-06-30",
  "is_active": false
}
```

---

## Payroll Periods

### Create Period

Use the `payroll_period.create` workflow (no approval step by default; the organisation's workflow configuration sets the lane and any approval).

```json
{
  "legal_entity_id": 13,
  "period_name": "January 2025",
  "period_type": "monthly",
  "period_number": 1,
  "fiscal_year": 2025,
  "period_start": "2025-01-01",
  "period_end": "2025-01-31",
  "pay_date": "2025-02-05"
}
```

**Period Types:**
- `monthly` - Once per month
- `bi_weekly` - Every two weeks (26 periods/year)
- `weekly` - Every week (52 periods/year)
- `semi_monthly` - Twice per month (24 periods/year)

### Close Period

Use the `payroll_period.close` workflow (green lane — auto-approved and executes immediately unless the organization has configured approval steps for it).

```json
{
  "payroll_period_id": 1
}
```

Requires the legacy stored `paid` or `voided` marker before closing; this checks posting completion, not bank settlement.

---

## Payroll Runs

### Create Run

Use the `payroll_run.create` workflow (no approval step by default — completes immediately and records who opened the run; approval happens at `payroll_run.approve`).

```json
{
  "legal_entity_id": 13,
  "payroll_period_id": 1,
  "run_type": "regular"
}
```

**Run Types:**
- `regular` - Normal payroll
- `correction` - Fix errors from previous run
- `bonus` - Bonus-only run
- `final` - Final paycheck (termination)

### Submit Calculation (Plugin-Based)

Use the `payroll_run.submit_calculation` workflow (Green lane by default: completes without an approval step unless the organisation has configured one).

> **Tip**: call `get_submissions(action='schema', object_type='payroll_run', operation='submit_calculation')` to fetch the live contract — required fields, the `tax_lines` shape, the `category` enum, and a verbatim example.
>
> **Critical**: `category` selects the tax total and must agree with posting `side`: `employee_deduction` uses `CR`; `employer_tax` uses `BOTH`. Positive `total_deductions` requires itemized `deduction_details`; itemized amounts must match the total at current detail precision. The validator and direct calculation executor enforce this before replacing prior calculations. Country formulas and business rules remain external/configurable.

The **Cowork plugin** (not the backend) performs all country-specific calculations. The plugin:
1. Reads employee data via MCP tools (compensation, tax settings, deductions)
2. Reads tax rates from `payroll_tax_jurisdictions`
3. Calculates gross pay, taxes, deductions, and net pay
4. Submits pre-calculated results to the backend via `submit_calculation`

The backend **validates** the submission (net_pay formula, tax_lines sums) and stores the results.

**Payload format:**

Each `tax_lines[i]` requires: `line_type`, `category` (`'employee_deduction'` | `'employer_tax'`), `amount`, `side` (`'CR'` | `'BOTH'`), `description`.

```json
{
  "payroll_run_id": 1,
  "employees": [
    {
      "employee_id": 13,
      "gross_pay": "5500.00",
      "regular_pay": "5500.00",
      "total_employee_taxes": "1214.16",
      "total_employer_taxes": "1859.00",
      "total_deductions": "200.00",
      "net_pay": "4085.84",
      "tax_lines": [
        {"line_type": "income_tax", "category": "employee_deduction", "amount": "1018.16", "side": "CR", "description": "Income tax 22%"},
        {"line_type": "unemployment_employee", "category": "employee_deduction", "amount": "88.00", "side": "CR", "description": "Unemployment (employee) 1.6%"},
        {"line_type": "pension", "category": "employee_deduction", "amount": "108.00", "side": "CR", "description": "Funded pension II pillar 2%"},
        {"line_type": "social_tax", "category": "employer_tax", "amount": "1815.00", "side": "BOTH", "description": "Social tax 33%"},
        {"line_type": "unemployment_employer", "category": "employer_tax", "amount": "44.00", "side": "BOTH", "description": "Unemployment (employer) 0.8%"}
      ],
      "deduction_details": [
        {"deduction_type": "pension_iii", "deduction_name": "Voluntary pension contribution", "amount": "200.00", "is_pre_tax": true}
      ]
    }
  ]
}
```

**What the backend does on submit:**
1. Validates each employee's results:
   - `net_pay = gross_pay - total_employee_taxes - total_deductions` at the current detail builder’s two-decimal precision
   - Sum of employee_deduction tax_lines = `total_employee_taxes`
   - Sum of employer_tax tax_lines = `total_employer_taxes`
2. Stores results in `payroll_run_details` (per-employee totals)
3. **Generates vendor-linked detail lines** in `payroll_run_detail_lines`:
   - Uses `payroll_vendor_config` to map each tax to a vendor + GL account
   - Uses `employee_deductions` vendor/GL info for voluntary deductions
   - Creates DR/CR lines for: gross_pay, taxes, deductions, net_pay
4. Updates run totals and sets status to `calculated`

**Recalculation**: Submit again to the same run — existing details are replaced.

**Vendor resolution for detail lines:**
- `employee_deductions.master_vendor_id` → checked first (per-employee override for voluntary deductions)
- `payroll_vendor_config.master_vendor_id` → fallback (entity-level defaults for mandatory taxes)
- If neither has a vendor, the line is still created but without vendor assignment

---

## Payroll Vendor Config

Before calculating payroll, you must set up **vendor configuration** for each legal entity. This maps each payroll `line_type` to the GL accounts (and, where applicable, the vendor) used when generating detail lines and posting GL.

### Required canonical line_types (every entity, every country)

Two `line_type` rows are **always required**, regardless of country:

| line_type | DR/CR | What it represents | vendor | Account columns |
|-----------|-------|--------------------|--------|-----------------|
| `gross_pay` | DR | Salary/wages expense | NULL (no third party) | `expense_account_number` |
| `net_pay` | CR | Wages payable to employee | NULL (paid directly) | `payable_account_number` |

If either row is missing or has the wrong account column populated, `submit_calculation` raises a `ValueError` listing the missing key — **before** any detail lines are written. The run stays in `draft`.

Country-specific tax line_types are whatever the country plugin emits in `tax_lines[i].line_type` (see [Submit Calculation](#submit-calculation-plugin-based)). Each one needs a row.

### Prerequisites (one-time per entity)

Before creating vendor config, ensure:

1. **Country-specific GL accounts exist** — The IFRS template only includes generic accounts (e.g., 6010 Salaries & Wages, 2210 Wages Payable, 2410 Income Tax Payable). You must create country-specific accounts (e.g., EE: 2230 Social Tax Payable, 2240 Unemployment Payable, 6012 Social Tax Expense; US: 2120 Federal Income Tax Payable, 2121 FICA Payable) using `account.create`.

2. **Government/institutional vendors exist** — Create vendors for tax authorities and pension funds (e.g., EMTA, HMRC, IRS, Töötukassa) using `vendor.create`, then set up their bank accounts. **Not needed** for `gross_pay` and `net_pay` (no vendor).

3. **Employee bank accounts exist** — Each employee needs a bank account in `employee_bank_accounts` for net pay batch lines.

See country-specific role docs (Estonian, UK) for exact accounts, vendors, and config per country.

### Create Vendor Config

Use the `payroll_vendor_config.create` workflow (no approval step by default; configurable per organisation).

```json
{
  "legal_entity_id": 12,
  "line_type": "income_tax",
  "master_vendor_id": 45,
  "expense_account_number": null,
  "payable_account_number": "2410"
}
```

**Required Fields:**
- `legal_entity_id` (integer) - Legal entity
- `line_type` (string) - Payroll line_type (see table below). MUST include `gross_pay` and `net_pay` rows.

**Optional Fields:**
- `master_vendor_id` (integer) - Vendor who receives payment. **Omit (or NULL) for `gross_pay` and `net_pay`** — neither has a third-party payee.
- `expense_account_number` (string) - DR account. Required for `gross_pay` and any employer-tax line_types.
- `payable_account_number` (string) - CR account (liability). Required for `net_pay` and any payable-side tax line_types.
- `metadata` (jsonb) - Additional config

**Common line_type values:**

| line_type | Category | Typical Vendor | Needs expense_account? | Needs payable_account? |
|-----------|----------|---------------|----------------------|----------------------|
| `gross_pay` | (universal) | NONE | **Yes** | No |
| `net_pay` | (universal) | NONE | No | **Yes** |
| `income_tax` | employee_deduction | EMTA / IRS | No | Yes |
| `social_tax` | employer_tax | EMTA | Yes | Yes |
| `unemployment_employee` | employee_deduction | Töötukassa | No | Yes |
| `unemployment_employer` | employer_tax | Töötukassa | Yes | Yes |
| `pension` | employee_deduction | Pension Fund | No | Yes |
| `federal_income_tax` | employee_deduction | IRS | No | Yes |
| `social_security_employee` | employee_deduction | IRS/SSA | No | Yes |
| `social_security_employer` | employer_tax | IRS/SSA | Yes | Yes |
| `medicare_employee` | employee_deduction | IRS | No | Yes |
| `medicare_employer` | employer_tax | IRS | Yes | Yes |

**Estonian Setup Example:**
```json
// 1. Gross pay (salary expense) — required, no vendor
{"legal_entity_id": 12, "line_type": "gross_pay", "expense_account_number": "6010"}

// 2. Net pay (wages payable to employee) — required, no vendor
{"legal_entity_id": 12, "line_type": "net_pay", "payable_account_number": "2210"}

// 3. Income Tax → EMTA
{"legal_entity_id": 12, "line_type": "income_tax", "master_vendor_id": 45, "payable_account_number": "2410"}

// 4. Social Tax → EMTA
{"legal_entity_id": 12, "line_type": "social_tax", "master_vendor_id": 45, "expense_account_number": "6012", "payable_account_number": "2230"}

// 5. Unemployment (Employee) → Töötukassa
{"legal_entity_id": 12, "line_type": "unemployment_employee", "master_vendor_id": 46, "payable_account_number": "2240"}

// 6. Unemployment (Employer) → Töötukassa
{"legal_entity_id": 12, "line_type": "unemployment_employer", "master_vendor_id": 46, "expense_account_number": "6014", "payable_account_number": "2240"}

// 7. Pension → LHV Pension Fund
{"legal_entity_id": 12, "line_type": "pension", "master_vendor_id": 47, "payable_account_number": "2250"}
```

### Update Vendor Config

Use the `payroll_vendor_config.update` workflow (no approval step by default; configurable per organisation).

```json
{
  "config_id": 5,
  "payable_account_number": "2235"
}
```

---

## Payroll Run Detail Lines

After `payroll_run.submit_calculation`, each employee gets **vendor-linked detail lines** in `payroll_run_detail_lines`. These lines:

- Link each tax/deduction amount to a **vendor** (via `payroll_vendor_config`)
- Specify the **GL account** and **DR/CR** direction
- Enable proper GL posting and payment batch creation
- Net pay lines have **no vendor** — employees are paid directly via `employee_bank_accounts`

**Example detail lines for Estonian employee (€3,500 gross):**

| Line Type | Category | Vendor | Account | DR/CR | Amount |
|-----------|----------|--------|---------|-------|--------|
| gross_pay | gross_pay | — | 6000 | DR | €3,500.00 |
| income_tax | employee_deduction | EMTA | 2410 | CR | €588.28 |
| unemployment_employee | employee_deduction | Töötukassa | 2240 | CR | €56.00 |
| pension | employee_deduction | LHV Pension | 2250 | CR | €70.00 |
| net_pay | net_pay | — | 2260 | CR | €2,785.72 |
| social_tax | employer_tax | EMTA | 6012 | DR | €1,155.00 |
| social_tax | employer_tax | EMTA | 2230 | CR | €1,155.00 |
| unemployment_employer | employer_tax | Töötukassa | 6014 | DR | €28.00 |
| unemployment_employer | employer_tax | Töötukassa | 2240 | CR | €28.00 |

**Key points:**
- Employer taxes generate **two lines** each (DR expense + CR payable)
- Employee deductions generate **one CR line** (payable to vendor)
- Gross pay is always **DR** (salary expense)
- Net pay is always **CR** (no vendor — paid directly to employee via `employee_bank_accounts`)
- Lines without vendor config still get created but without vendor/account info

---

### Approve Payroll

Approval changes `calculated` to `approved`; it does **not** post GL. `payroll_run.process_payment` posts the payroll journal and prepares the payment batch. `execute_payment=false` leaves that batch in draft; neither setting transmits money. The legacy internal `paid` marker is not bank-confirmed settlement: this operation returns `status=posted`, `accounting_status=posted` and `payment_status=not_sent`. Use the linked payment batch and its confirmations to establish settlement. Transmission and confirmation are separate payment-batch operations. Approval lanes and steps are organization-configurable.

Use the `payroll_run.approve` workflow (high-risk; any executive approval step is the organisation's workflow configuration, and the `status` in the submit() result says whether the run is approved or waiting).

```json
{
  "payroll_run_id": 1
}
```

**Approval Chain:**
1. Payroll Administrator reviews calculations
2. Controller or CFO approves for payment

### Process Payment

Use the `payroll_run.process_payment` workflow (high-risk; approval steps as the organisation has configured them).

```json
{
  "payroll_run_id": 1,
  "payment_batch_name": "January 2025 Payroll",
  "payment_method": "SEPA",
  "bank_account_id": 9,
  "execute_payment": true
}
```

`payment_method` is required: `ACH`, `WIRE`, `SEPA`, or `CHECK`. Refresh `get_submissions(action="schema", object_type="payroll_run", operation="process_payment")` before preparing the request. The executor normalizes accepted aliases, never guesses a method from currency, requires EUR for SEPA and USD for ACH, and stores the canonical value. Method selection does not certify bank/provider or recipient eligibility; payment approval and readiness checks still apply.

`bank_account_id` (optional) — Source bank account. Auto-selected if not provided. A supplied account must be active and belong to the run's entity and currency. Invalid method/account selections roll back preparation; existing draft batches are not rewritten by this code change.

`execute_payment` (optional, default `true`) — whether to submit the payment
batch for approval. **Neither value moves money**: transmission is a separate,
approval-gated step. `false` leaves the batch in `draft` for someone to submit
by hand later, which is only useful when you want the GL posted but the payment
deliberately held back.

**What happens:**
1. Reads vendor-linked detail lines from `payroll_run_detail_lines`
2. Posts a **PAYROLL GL transaction** with all DR/CR lines (balanced). Each GL line carries:
   - `vendor_id` for tax/deduction lines (e.g., MTA, Pensionikeskus)
   - `employee_id` for gross-pay (DR) and net-pay (CR) lines
   - `metadata.source = 'payroll_run'` and `metadata.payroll_run_id` on the header — surfaces a back-link in the transaction-detail "Links" tab in the admin UI
3. Creates a **bank payment batch** (batch_type='payroll') with dual payee lines:
   - **Vendor lines**: Tax payments to government vendors (EMTA, Töötukassa, pension fund) — looks up `vendor_bank_accounts`.
     Entities with `payroll.tax_bill_vendor_ids` configured: listed authority vendors are **skipped** here
     (reported in the result as `skipped_tax_bill_vendors`) — they are paid by settling the tax filing's
     settlement bill (e.g. TSD Step 7b) through the normal AP chain instead, so the authority is never paid twice.
   - **Employee lines**: Net pay directly to employees — looks up `employee_bank_accounts`
4. Updates `payroll_runs` with `transaction_id` and `payment_batch_id`
5. Records the legacy internal `paid` marker; the public status is `posted` until all linked payment lines are confirmed
6. Submits the batch for approval, unless `execute_payment: false`

Steps 1–5 are one transaction; step 6 runs **after** it commits, because the
batch must be visible to the submit executor's own connection and because a
failure to route the batch for approval must not roll back a correct GL posting.
If step 6 fails the run is still publicly `posted` and the books are still right — the
result reports `payment_batch_status` and `payment_batch_submit_error` rather
than raising, so nobody is tempted to re-run an already-posted payroll.

**Why this matters for reporting:** because each GL line carries its own `vendor_id` / `employee_id`, AP-aging-by-vendor reports include payroll-derived liabilities (e.g. what's owed to MTA across AP invoices + payroll income tax + payroll social tax). Without per-line partner refs, payroll would appear as an opaque journal entry and AP aging would miss those liabilities.

**Automatic Behaviors:**
- **Fiscal period auto-lookup**: If not provided, looks up the open fiscal period matching the pay_date
- **Bank account auto-lookup**: If `bank_account_id` not provided, selects the first active bank account matching the entity + currency
- **GL idempotency**: If a previous attempt posted a GL transaction but failed before marking the run as 'paid', the system detects and reuses the existing GL transaction (matched by reference_number `PAY-RUN-{id}`)
- **Batch line_count correction**: After inserting batch lines, the header's `line_count` is updated to reflect actual inserted lines (may differ from anticipated if vendor bank accounts are missing)

**Prerequisites:** `payroll_vendor_config` must be set up. Employees must have bank accounts in `employee_bank_accounts`.

### Void Run

Use the `payroll_run.void` workflow (high-risk; approval steps as the organisation has configured them).

```json
{
  "payroll_run_id": 1,
  "void_reason": "Incorrect tax calculations - need to recalculate",
  "reverse_gl": true
}
```

Use when errors are discovered after processing. Creates reversing GL entries if `reverse_gl` is true.

### Update Run

Use the `payroll_run.update` workflow (Yellow lane by default, with one admin approval step) to relink a run to a different payroll period. Labels only — the posted GL journal, its dates and its lines are never touched. Use it when a run was created on the wrong period but the GL (and any filed declaration) is correct: voiding would reverse a correct journal. The executor also syncs the GL transaction's `metadata.payroll_period_id` back-link and records the edit on the transaction's Activity tab.

```json
{
  "payroll_run_id": 5,
  "payroll_period_id": 1472,
  "edit_reason": "Run created on August period; GL and TSD are July"
}
```

The target period must belong to the run's legal entity; voided runs are refused. A closed target period produces a warning, not a refusal — there is no `payroll_period.reopen` operation and the GL is unaffected.

---

## Tax Calculations

### United States

**Federal Taxes:**

| Tax | Employee Rate | Employer Rate | Wage Base (2025) |
|-----|--------------|---------------|------------------|
| Federal Income | Progressive (10%-37%) | - | Based on W-4 |
| Social Security | 6.2% | 6.2% | $176,100 |
| Medicare | 1.45% | 1.45% | No limit |
| Additional Medicare | 0.9% | - | Wages > $200,000 |

**Employer-Only Taxes:**
- FUTA: 0.6% on first $7,000
- SUTA: Varies by state (0.5%-5.4%)

**State Taxes:**
- Income tax rates vary by state (0% to 13.3%)
- Some localities have additional taxes (NYC, SF)

### Estonia

**Employee Deductions:**

| Tax | Rate | Notes |
|-----|------|-------|
| Income Tax | 22% | After exemptions |
| Unemployment Insurance | 1.6% | Employee portion |
| Funded Pension (II Pillar) | 2%, 4%, or 6% | Employee choice |
| Basic Exemption | up to 700/month | Can only be applied at one employer |

**Employer Taxes:**

| Tax | Rate | Notes |
|-----|------|-------|
| Social Tax | 33% | 20% pension + 13% health |
| Unemployment Insurance | 0.8% | Employer portion |
| Minimum Social Tax Base | 886/month | Minimum tax: 292.38 |

**Calculation Example (3,500 gross):**
```
Gross Pay:                     3,500.00
- Unemployment (1.6%):           -56.00
- Pension II Pillar (2%):        -70.00
- Basic Exemption:              -700.00
= Taxable Income:              2,674.00
- Income Tax (22%):             -588.28
= Net Pay:                     2,785.72

Employer Cost:
+ Social Tax (33%):           1,155.00
+ Unemployment (0.8%):           28.00
= Total Employer Cost:        4,683.00
```

---

## Standard Payroll Processing Workflow

### Monthly Payroll

```
0. Payroll Onboarding (one-time per entity)
    a. Create country-specific payroll GL accounts (liability + expense)
       - The IFRS template does NOT include country-specific payroll accounts
       - Examples: Social Tax Payable (2230), Unemployment Payable (2240), etc.
       - Use account.create workflow for each account
    b. Create government/institutional vendors
       - Examples: EMTA (Estonia), IRS (US), HMRC (UK), Töötukassa, etc.
       - Use vendor.create workflow, then set up vendor bank accounts
    c. Create payroll vendor config
       - payroll_vendor_config.create for each tax type
       - Maps income_tax → EMTA, social_tax → EMTA, etc.
    See country-specific role docs for exact accounts, vendors, and config

1. Create Payroll Period (if not exists)
    payroll_period.create

2. Create Payroll Run
    payroll_run.create (status: draft)

3. Calculate Payroll (Plugin-Based)
    Plugin reads employee data via MCP tools
    Plugin calculates taxes using country-specific formulas
    Plugin submits results via payroll_run.submit_calculation (status: calculated)
    → Creates payroll_run_details (per-employee totals)
    → Creates payroll_run_detail_lines (vendor-linked sub-lines)

4. Review Results
    Check payroll_run_details and payroll_run_detail_lines
    Verify vendor assignments and GL accounts

5. Approve Payroll (executive approval where the organisation has configured it)
    payroll_run.approve (status: approved)

6. Process Payment
    payroll_run.process_payment (public status: posted)
    → Posts PAYROLL GL transaction (sets transaction_id)
    → Creates bank_payment_batch with dual payee lines:
       - Vendor lines for tax authority payments
       - Employee lines for net pay (via employee_bank_accounts)

7. Close Period
    payroll_period.close (status: closed)
```

### Error Correction

If errors are discovered after payment:

```
1. Void the incorrect run
    payroll_run.void (creates reversing entries)

2. Create correction run
    payroll_run.create (run_type: correction)

3. Process normally
    calculate -> approve -> process_payment
```

---

## Tax Declaration Forms

### United States

| Form | Purpose | Due Date |
|------|---------|----------|
| 941 | Quarterly federal tax return | End of month after quarter |
| 940 | Annual FUTA return | January 31 |
| W-2 | Annual wage statement | January 31 |
| State equivalents | Vary by state | Varies |

### Estonia

| Form | Purpose | Due Date |
|------|---------|----------|
| TSD | Monthly income and social tax declaration | 10th of following month |
| TSD Annex 1 | Residents | With TSD |
| TSD Annex 2 | Non-residents | With TSD |
| Employment Register | Real-time employee registration | Before work starts |

---

## Common Scenarios

### New Employee Setup

1. Create employee (see [Employee Management](./employee-management.md))
2. Create compensation record (`employee_compensation.create`)
3. **Create tax settings** (`employee_tax_settings.create`) — **CRITICAL for payroll**
   - Sets `country_code` which determines which tax formula the calculator uses
   - Without tax settings, employee defaults to US formula (wrong for non-US employees)
   - For Estonia: set `pension_tier` (`'2%'`, `'4%'`, `'6%'`, or `NULL` = not enrolled) and `basic_exemption_applied`
   - For US: set `state_code`, `filing_status` (selects bracket set)
4. Add deductions (benefits enrollment) — optional

```json
// Step 2: Compensation
{
  "employee_id": 100,
  "legal_entity_id": 13,
  "compensation_type": "salary",
  "pay_frequency": "monthly",
  "base_amount": 85000.00,
  "currency": "USD",
  "effective_from": "2025-02-01"
}

// Step 3: Tax Settings
{
  "employee_id": 100,
  "legal_entity_id": 13,
  "country_code": "US",
  "state_code": "NY",
  "tax_id_type": "ssn",
  "tax_id_number": "987-65-4321",
  "filing_status": "single",
  "effective_from": "2025-02-01"
}

// Step 4: 401(k) Deduction
{
  "employee_id": 100,
  "legal_entity_id": 13,
  "deduction_type": "401k",
  "deduction_name": "401(k) Contribution",
  "calculation_method": "percentage",
  "percentage": 0.05,
  "employer_match_percentage": 0.50,
  "employer_match_limit": 3000.00,
  "is_pre_tax": true,
  "effective_from": "2025-02-01"
}
```

### Salary Increase

Create new compensation record with future effective date:

```json
{
  "employee_id": 42,
  "legal_entity_id": 13,
  "compensation_type": "salary",
  "pay_frequency": "monthly",
  "base_amount": 90000.00,
  "currency": "USD",
  "effective_from": "2025-07-01"
}
```

The system automatically ends the previous compensation record.

### Employee Relocation (State Change)

Update tax settings for new state:

```json
{
  "employee_id": 42,
  "legal_entity_id": 13,
  "country_code": "US",
  "state_code": "TX",
  "tax_id_type": "ssn",
  "filing_status": "married_filing_jointly",
  "effective_from": "2025-03-01"
}
```

### Off-Cycle Bonus

1. Create bonus payroll run:
```json
{
  "legal_entity_id": 13,
  "payroll_period_id": 3,
  "run_type": "bonus"
}
```

2. Calculate with bonus amounts (handled by payroll_run_details)
3. Approve and process normally

### Employee Termination

1. Create final payroll run:
```json
{
  "legal_entity_id": 13,
  "payroll_period_id": 3,
  "run_type": "final"
}
```

2. Include:
   - Prorated salary through termination date
   - Accrued PTO payout
   - Any outstanding expense reimbursements

3. End all active deductions with termination date

---

## Risk Lane Summary

| Typical lane | Workflows | Typical approval |
|------|-----------|-------------------|
| Green | `payroll_run.submit_calculation`, `payroll_period.create/close`, `payroll_tax_jurisdiction.create/update`, `payroll_vendor_config.create/update` | None, unless the organisation has configured a step |
| Yellow | All create/update for compensation, tax settings, deductions | Single approval, where configured |
| Red | `payroll_run.approve`, `payroll_run.process_payment`, `payroll_run.void` | Executive approval, where configured |

Lanes are assigned by your organisation's workflow rules; the submit() result is authoritative.

---

## Getting Reference Data

Before constructing payloads, use search tools to get valid reference data:

| Data Type | How to Get | Example Values |
|-----------|-----------|----------------|
| Employees | `query("employee")` | Employee IDs |
| Legal entities | `query("legal_entity")` | Entity IDs |
| Payroll periods | `query("payroll_period")` | Period IDs |
| Payroll runs | `query("payroll_run")` | Run IDs |
| Tax jurisdictions | `query("payroll_tax_jurisdiction")` | Tax rates by country/state |

---

## Querying Employee Payroll Data

**IMPORTANT:** Employee payroll data is stored in dedicated database tables, NOT in employee metadata. Use the following tools to retrieve compensation, tax settings, and deductions.

### Get Employee Compensation

Use `query("employee_compensation")` to retrieve salary/hourly rate information:

```python
# Get all compensation records for an employee
query("employee_compensation", query="", filters={"employee_id": 42})

# Get current compensation (active record)
query("employee_compensation", query="", filters={"employee_id": 42, "is_active": true})

# Get compensation for all employees in an entity
query("employee_compensation", query="", filters={"legal_entity_id": 12})
```

**Returns fields:**
- `id` - Compensation record ID
- `employee_id` - Employee ID
- `legal_entity_id` - Legal entity ID
- `compensation_type` - "salary", "hourly", "commission", etc.
- `pay_frequency` - "monthly", "bi_weekly", "weekly", etc.
- `base_amount` - Salary or hourly rate
- `currency` - Currency code (EUR, USD, etc.)
- `standard_hours_per_week` - For hourly employees
- `overtime_multiplier` - Overtime rate multiplier
- `effective_from` - Start date
- `effective_to` - End date (null = current)

### Get Employee Tax Settings

Use `query("employee_tax_settings")` to retrieve tax withholding configuration:

```python
# Get tax settings for an employee
query("employee_tax_settings", query="", filters={"employee_id": 42})

# Get current tax settings
query("employee_tax_settings", query="", filters={"employee_id": 42, "is_active": true})

# Get Estonian employees' tax settings for an entity
query("employee_tax_settings", query="", filters={"legal_entity_id": 12, "country_code": "EE"})
```

**Returns fields:**
- `id` - Tax settings record ID
- `employee_id` - Employee ID
- `legal_entity_id` - Legal entity ID
- `country_code` - "US", "EE", "GB", etc.
- `tax_id_type` - "ssn", "personal_id", etc.
- `tax_id_number` - Tax ID (encrypted)
- **For US:** `state_code`, `filing_status`, `allowances`, `additional_withholding`
- **For Estonia:** `pension_tier` ("2%", "4%", "6%"), `basic_exemption_applied`
- `effective_from` - Start date
- `effective_to` - End date (null = current)

### Get Employee Deductions

Use `query("employee_deduction")` to retrieve benefit and deduction information:

```python
# Get all deductions for an employee
query("employee_deduction", query="", filters={"employee_id": 42})

# Get active deductions only
query("employee_deduction", query="", filters={"employee_id": 42, "is_active": true})

# Get specific deduction types
query("employee_deduction", query="", filters={"employee_id": 42, "deduction_type": "401k"})

# Get all deductions for an entity
query("employee_deduction", query="", filters={"legal_entity_id": 12})
```

**Returns fields:**
- `id` - Deduction record ID
- `employee_id` - Employee ID
- `legal_entity_id` - Legal entity ID
- `deduction_type` - "401k", "health_insurance", "pension_iii", "court_enforcement", etc.
- `deduction_name` - Display name
- `calculation_method` - "fixed", "percentage", "per_hour"
- `amount` - Fixed amount (if calculation_method = "fixed")
- `percentage` - Percentage (if calculation_method = "percentage")
- `annual_limit` - Maximum annual deduction
- `employer_match_percentage` - Employer match rate
- `employer_match_limit` - Maximum employer match
- `is_pre_tax` - Pre-tax deduction flag
- `is_mandatory` - Whether this deduction is mandatory (court orders, statutory)
- `deduction_category` - Category: "voluntary_benefit", "court_order", "employer_cost", "other"
- `master_vendor_id` - Vendor receiving this deduction payment
- `payable_account_number` - GL liability account
- `expense_account_number` - GL expense account (employer-side costs)
- `is_active` - Active status
- `effective_from` - Start date
- `effective_to` - End date (same as effective_from for one-time deductions)

### Complete Payroll Data Retrieval Example

To get full payroll data for an employee:

```python
# Step 1: Get employee basic info
employee = get_entity("employee", id=42)

# Step 2: Get current compensation
compensation = query("employee_compensation", query="", filters={"employee_id": 42, "is_active": true})
# Returns: base_amount, currency, pay_frequency, compensation_type

# Step 3: Get current tax settings
tax_settings = query("employee_tax_settings", query="", filters={"employee_id": 42, "is_active": true})
# Returns: pension_tier, basic_exemption_applied, country_code

# Step 4: Get active deductions
deductions = query("employee_deduction", query="", filters={"employee_id": 42, "is_active": true})
# Returns: All active deductions with amounts/percentages
```

### Get All Payroll Data for an Entity

To prepare payroll for all employees in an entity:

```python
# Get all employees for the entity
employees = query("employee", query="", filters={"legal_entity_id": 12, "status": "active"})

# Get all current compensation records
compensation_records = query("employee_compensation", query="", filters={"legal_entity_id": 12, "is_active": true})

# Get all current tax settings
tax_settings_records = query("employee_tax_settings", query="", filters={"legal_entity_id": 12, "is_active": true})

# Get all active deductions
deduction_records = query("employee_deduction", query="", filters={"legal_entity_id": 12, "is_active": true})
```

### Estonian Payroll Data Summary

For Estonian payroll processing (entity 12 - Arfiti Technologies OÜ):

```python
# Get employees with their compensation and tax settings for Estonia
employees = query("employee", filters={"legal_entity_id": 12, "status": "active"})

for emp in employees:
    # Get salary
    comp = query("employee_compensation", query="", filters={"employee_id": emp["id"], "is_active": true})
    gross_salary = comp[0]["base_amount"]  # e.g., 5500.00 EUR

    # Get pension tier and exemption settings
    tax = query("employee_tax_settings", query="", filters={"employee_id": emp["id"], "is_active": true})
    pension_tier = tax[0]["pension_tier"]  # "2%", "4%", or "6%"
    basic_exemption = tax[0]["basic_exemption_applied"]  # true/false

    # Get deductions (III pillar pension, health insurance, etc.)
    deductions = query("employee_deduction", query="", filters={"employee_id": emp["id"], "is_active": true})
```

---

## Tips & Best Practices

### 1. Compensation Management
- Create new records for salary changes (don't update existing)
- Use effective dates to schedule future changes
- Keep historical records for audit trail

### 2. Tax Settings
- Verify tax ID numbers carefully
- Update settings promptly for life events (marriage, relocation)
- Estonian employees: only apply basic exemption at one employer

### 3. Deductions
- Set annual limits to comply with IRS regulations (401k: $23,000 for 2025)
- Process garnishments in priority order
- Track employer match limits separately

### 4. Payroll Processing
- Always calculate before approving
- Review payroll_run_details before approval
- Use correction runs for errors (don't void unless necessary)

### 5. Period Management
- Create periods in advance
- Don't close periods until all runs are complete
- Keep periods aligned with fiscal calendar

### 6. Compliance
- Generate tax forms on schedule
- Maintain audit trail for all changes
- Archive payroll reports monthly

---

## Related Resources

- [Employee Management](./employee-management.md) - Employee master data (create employees, manage status)
- [Bank Accounts Management](./bank-accounts-management.md) - Direct deposit setup and employee bank accounts
- [Tax Management](./tax-management.md) - Tax codes, tax jurisdictions, and tax calculation
- [Accounts Management](./accounts-management.md) - GL accounts for payroll posting (salary expense, tax payable)
- [Dimensions Management](./dimensions-management.md) - Department/cost center tagging on payroll transactions
- [Vendor Management](./vendor-management.md) - Government vendor setup (tax authorities, pension funds)
- [Billing Management](./billing-management.md) - Related if payroll feeds into customer billing (contractor invoicing)

## Extended Documentation

- GUIDE_PAYROLL_MANAGEMENT.md - Full technical documentation
- PLAN_PAYROLL_INFRASTRUCTURE.md - Database schema and implementation

---

## Tax-filing fields on payroll records (universal, country-pluggable)

Two universal fields support tax-filing without per-country branching in core code:

### `employee_compensation.payment_classification_slug`

Real indexed column. Country tax-filing plugins translate the slug to a country-specific external code at filing time (EE TSD: `salary_wage` → `c1020 = "10"`; US W2: → `W2-BOX-1`; UK RTI: → `PAYE-A1`).

**Auto-defaulted from `compensation_type` on create:**
- `salary` / `hourly` → `salary_wage`
- `contract` → `contractor_payment`
- `commission` → `commission_payment`
- `stipend` → `stipend_payment`

**Override** by passing `payment_classification_slug` explicitly:

```python
submit("employee_compensation", "create", {
    "employee_id": 50, "compensation_type": "salary",
    "payment_classification_slug": "board_fee",   # explicit — for board members
    ...
})
```

### `master_employees.metadata.tax_filing.*`

Per-employee filing attributes:
- `country` (ISO 3166-1 alpha-2)
- `residency` (`resident` | `non_resident`)
- `country_of_residence`
- `is_pensioner` (drives unemployment-insurance exclusion)
- `basic_exemption_code` (EE: `610`)
- `pension_fund_id` (FK to master_vendors)
- `tax_treaty_country`, `treaty_rate_override`

Set via `submit("employee", "update", { metadata: { tax_filing: { ... } } })`. Country plugins fall back to sensible defaults when fields are missing; explicit values are recommended for production filings.

### `DIVIDEND_PAYMENT` transaction type

For corporate dividend distributions. Posts `DR Dividends/Retained Earnings / CR Bank`. Country plugins read these to populate dividend-specific tax-form annexes (EE TSD Annex 7 + INF1, US 1099-DIV, etc.).

For the architectural pattern, see GUIDE_TAX_FILING_PLUGINS.md.

## End of Guide

This guide covers complete payroll management including compensation, tax settings, deductions, and payroll processing for US and Estonian jurisdictions.


### US payroll readiness

US setup now seeds gross_pay expense 6010 and net_pay payable 2110 (both vendor-free). For existing companies, review the chart and create missing payroll_vendor_config mappings; do not assume completed onboarding retroactively added them. Use the configured country tax line_type names. Arithmetic is validated during validate_only, while database configuration and downstream approval/payment readiness still need verification.


### Payroll mutation entity scope
ID-based payroll writes resolve the stored record's legal entity in the current
tenant before validation/replay and again at workflow start and execution. A
caller-supplied entity ID cannot override that stored entity. This covers employee
compensation, tax settings, deductions, payroll runs, periods and vendor config;
create references (employee/period) and nested employee payroll updates are also
checked. Restricted callers receive entity:access for missing/inaccessible targets.
Existing wildcard and all-entity semantics remain; read permission alone never
implies write permission. Global payroll tax-jurisdiction configuration is not an
entity-owned record and is not covered by this entity lookup.

## Posted is not paid

Public payroll status is `posted` after GL posting until every linked batch line
is completed from payment confirmation evidence. Draft/transmitted batches do not
prove cash payment. `execute_payment=false` leaves a draft batch and returns
`posted`; never tell the user it was paid. Employee dimensions are inherited per
GL line in the posting entity; explicit line/header tags take precedence. Verify
dimension reports after posting; old journals are not retroactively retagged.

### Month-end settlement evidence

The close checklist checks all non-voided runs in overlapping payroll periods.
The internal paid marker alone does not pass it: payment lines must be completed
and linked to posted, unreversed cash transactions dated through period end.
Draft/incomplete batches, processing-only provider responses, payments posted in
a later month and reversed payments remain unresolved. Never describe prepared
payroll as paid or invent bank confirmations to clear the checklist.


### Bank-confirmed payroll settlement

Payroll payment batch lines keep `PAY-RUN-{run_id}`. Confirmation clears that exact run's net-pay or direct authority liability, retaining source master employee/vendor IDs and dimensions on both liability and bank lines. Employee settlement uses SALARY_PAYMENT; direct authority settlement uses BANK_WITHDRAWAL. Configured tax-bill vendors still settle AP bills. Full amounts in functional currency are supported; partial payments, fees, foreign currency, ambiguous sources and inactive dimensions require review. See [payment batch confirmation](payment-batch-management.md#payroll-batch-confirmation-source-liabilities-and-dimensions). Do not treat the payroll run's `paid` status alone as proof of cash settlement.


## Close evidence update (b1, awaiting deployment)

The close check does not infer payroll absence from a scan. Seeded periods without runs continue to fail with “payroll absence not established; payroll applicability policy not configured”. Diagnostic evidence lists the adjacent-month window, salary/benefit account nets, accrued-payroll movement, compensation and employee count in functional currency, plus the most recent earlier net-debit month. No periods with non-run evidence warns “Not determined: payroll source policy not configured”; no periods and no signal retains the existing not-applicable result with an explicit absence caveat. Void/canceled payment documents do not settle a run. Carried payroll policy remains future work.

The local calculation integrity follow-up also refuses totals that would round
differently in the current Decimal detail builder and PostgreSQL `numeric(15,2)`
columns (for example, a `200.005` total versus `200.00` detail). Submit explicitly
rounded, consistent amounts; this does not choose a country tax-rounding method.
Compatible fractional inputs remain accepted. With zero total deductions, omitted
or null itemization is allowed; positive totals require matching details.


### Payroll schema guidance rollout

The field contract comes from the current validator, while nested payroll guidance
also comes from stored workflow definitions. Draft migration
`775_payroll_calculation_contract_guidance.sql` aligns active standard definitions
with tax-side pairing, deduction itemization and current stored-precision checks.
It changes guidance only: required organization policy, approval steps and custom
definitions are preserved. Customized guidance may therefore need a separate owner
review; it cannot relax validator integrity checks. Empty field lists stay empty.
The migration number must be reconciled with merge order before publication.
This candidate has not been deployed or applied to production.

### Employee assignment and nested payroll command scope

A shared employee may have assignments in several legal entities. Payroll scope
checks use the requested assignment; without an explicit target they require an
assignment within the caller's existing entity scope. An entity hint never
authorizes a foreign stored compensation or tax record. Nested update/delete
commands use the collection writer's ID alias order, including
`employee_compensation_id` and `employee_tax_settings_id`, and still require
positive integer IDs. Malformed command blocks produce validation errors.

Public employee update schemas continue to require list blocks. Normalizing
internal object/JSON forms before the scope check does not advertise those forms
as accepted public payloads or bypass downstream validation.

### Stored payroll runs in configured reviews (AR-427 candidate)

The local reader correction derives review access scope from the stored payroll run in the current organization when an operation accepts only `payroll_run_id`. Do not add a `legal_entity_id` field to an operation schema that forbids it. A supplied entity hint, where supported, must agree with the stored run; missing or ambiguous runs are refused. Reviewers still require current payroll read authority and entity access. Approval lanes and approver rules remain organization-configurable.

Delivery status: local database and review-path acceptance passes; review/CI delivery is pending. Without certified rollback proof, reviewer assignment failure returns conservative HTTP409 uncertainty and same-key replay does not execute again. The bounded initial-assignment proof candidate is tracked in AR-948 below. See the active user-workflows and permissions plan. This correction is not deployed.


### Initial reviewer denial recovery (AR-948 local candidate)

For the audited initial payroll review-assignment path, an acknowledged owned rollback can return `reviewer_access_denied` with `effect_outcome=no_effect`. The saved refusal replays under the same request identity even after reviewer access is restored; it does not execute the original request. A failure to persist that receipt remains uncertain and retains retry protection. Nested transactions, unsupported failures and old uncertain claims do not acquire proof merely because no workflow row can be found. Do not submit an uncertain operation under a new identity to bypass reconciliation. This candidate is not delivered or deployed; remaining acceptance is tracked in the active plan.

For older uncertain requests, preserve the original identity and inspect the stored request, workflow/action receipts and operation-specific effects through authorized reads. Missing workflow rows are insufficient proof. If a trusted outcome cannot be established, leave the request unresolved; do not clear its claim or create another identity. Any production repair needs a separately reviewed, explicitly approved procedure. The AR-948 candidate does not perform such repairs.


Delivery status (2026-10-26): the bounded initial reviewer-refusal recovery from
PR443 is merged into main (fed599071), without deployment. The payroll scope fix
from PR440 is integrated locally with that main and awaits final hosted CI and
merge. Repository delivery does not activate a policy or change running services.
