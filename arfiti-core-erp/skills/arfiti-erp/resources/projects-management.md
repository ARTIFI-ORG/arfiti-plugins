# Project Management

> **MSEO release contract:** Keep master project identity and the legal entity of its project relationship explicit. A project dimension value is a classification, not an interchangeable project record ID. See the dimensions-management resource for assignment, approval and compatibility rules.

Comprehensive guide to project tracking, team management, time tracking, and profitability analysis across legal entities.

## Available Workflows

| Workflow Type | Operation | Typical lane |
|--------------|-----------|------|
| `project.create` | Create master project | Green |
| `project.update` | Update master project | Yellow |
| `project.delete` | Soft-delete project | Red |
| `project.assign_to_entity` | Assign project to entity | Green |
| `project.close` | Close/complete project | Yellow |
| `project.team_member.manage` | Add/update/delete team members | Green |
| `project.milestone.manage` | Add/update/delete milestones | Green |
| `project.task.manage` | Add/update/delete tasks | Green |
| `project.time_entry.manage` | Add/update/delete/submit/approve time entries | Green/Yellow |
| `project.budget.manage` | Add/update/delete budget categories | Green |
| `project.dimension.manage` | Add/delete dimension assignments | Green |
| `project.expense.manage` | Add/update/delete expense allocations | Yellow |
| `project.revenue.manage` | Add/update/delete revenue allocations | Yellow |

Lanes are assigned by your organisation's workflow rules; the submit() result is authoritative.

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

## Custom Fields

Organisations define their own project fields. Before putting a business fact
into `metadata`, check `get_submissions(action="schema", object_type="project", operation="create")`
→ `custom_fields` (key, type, limits, options, required). Set values with
`"custom_fields": {"key": value}`; on update keys you leave out are unchanged
and `"custom_fields_clear": ["key"]` empties one; never send `null`. Decimals
as numeric strings, dates `YYYY-MM-DD`, choice = one option `value`. Filter
with `query("project", filters={"custom_fields.<key>": value}).
All rules (register, types, required fields, transactions, filters, import, merge): the custom-fields resource; full contract `docs/GUIDES/GUIDE_CUSTOM_FIELDS.md`.

## Available Query Tools

| Tool | Purpose |
|------|---------|
| `get_entity("project", id=X)` | Get single project (includes `customer_name`, `project_manager_name` inline) |
| `query("project", filters)` | List projects with filters and pagination |
| `query("project", query, filters)` | Search projects by text |
| `query("project", filters, limit=1)` | Count matching projects (use `total_count` from response) |
| `get_entity("project_milestone", id=X)` | Get single milestone |
| `query("project_milestone", filters)` | List milestones |
| `query("project_milestone", query, filters)` | Search milestones |

**Virtual fields (resolved inline — no extra lookups needed):**
- `customer_name` — customer name resolved from `customer_id`
- `project_manager_name` — manager name resolved from `project_manager_employee_id`

**Key notes:**
- `get_entity` defaults to `include_related=True` — related data (team members, milestones, etc.) included automatically
- Search/list results now include `customer_name`, `project_manager_name`, `currency_code`, `start_date`, `end_date`

---

## Complete Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

### Master Projects Table (master_projects)

| Field Name | Data Type | Required | Description | Example |
|------------|-----------|----------|-------------|---------|
| `id` | integer | PK | System-generated ID | `45` |
| `organization_id` | integer | Yes | Organization ID | `63` |
| `global_project_id` | varchar(50) | Yes | Unique project identifier | `"PROJ-000001"` |
| `project_code` | varchar(50) | No | User-friendly code | `"WEB-2024-01"` |
| `project_name` | varchar(255) | Yes | Project name | `"Website Redesign"` |
| `description` | text | No | Detailed description | `"Complete redesign..."` |
| `customer_id` | integer | No | FK to master_customers | `123` |
| `budget_amount` | numeric(15,2) | No | Total project budget | `50000.00` |
| `currency_code` | varchar(3) | No | Budget currency | `"USD"` |
| `start_date` | date | No | Project start date | `2024-01-15` |
| `end_date` | date | No | Expected completion date | `2024-06-30` |
| `project_type` | varchar(50) | No | Project category | `"consulting"`, `"development"`, `"implementation"` |
| `status` | varchar(50) | Auto | Project status | `"planning"`, `"active"`, `"completed"` |
| `external_project_ref` | varchar(255) | No | External system reference | `"JIRA-123"` |
| `external_system` | varchar(50) | No | External system name | `"Jira"`, `"Salesforce"` |
| `metadata` | jsonb | No | Additional structured data | `{"client_contact": "john@acme.com"}` |
| `created_at` | timestamp | Auto | Creation timestamp | `2025-01-15 10:00:00-08` |
| `created_by` | integer | Auto | User ID who created | `30` |
| `updated_at` | timestamp | Auto | Last update timestamp | `2025-01-15 10:00:00-08` |
| `updated_by` | integer | Auto | User ID who updated | `30` |

### Entity Projects Table (projects)

| Field Name | Data Type | Required | Description | Example |
|------------|-----------|----------|-------------|---------|
| `id` | integer | PK | System-generated ID | `123` |
| `master_project_id` | integer | Yes | FK to master_projects | `45` |
| `legal_entity_id` | integer | Yes | Legal entity ID | `13` |
| `status` | varchar(50) | No | Entity-specific status | `"active"`, `"on_hold"` |
| `project_manager_employee_id` | integer | No | Project manager (entity employee) | `67` |
| `priority` | varchar(20) | No | Project priority | `"high"`, `"medium"`, `"low"` |
| `budget_amount` | numeric(15,2) | No | Entity budget allocation | `30000.00` |
| `currency_code` | varchar(3) | No | Entity currency | `"GBP"` |
| `billing_model` | varchar(50) | No | How to bill | `"time_and_materials"`, `"fixed_price"`, `"milestone"` |
| `planned_margin_pct` | numeric(5,2) | No | Target margin percentage | `25.00` |
| `effective_from` | date | Yes | Assignment start date | `2024-01-15` |
| `effective_to` | date | No | Assignment end date | `2024-12-31` |
| `created_at` | timestamp | Auto | Creation timestamp | `2025-01-15 10:00:00-08` |
| `created_by` | integer | Auto | User ID who created | `30` |
| `updated_at` | timestamp | Auto | Last update timestamp | `2025-01-15 10:00:00-08` |
| `updated_by` | integer | Auto | User ID who updated | `30` |

### Project Team Members Table (project_team_members)

| Field Name | Data Type | Required | Description | Example |
|------------|-----------|----------|-------------|---------|
| `id` | integer | PK | System-generated ID | `456` |
| `project_id` | integer | Yes | FK to projects (entity level) | `123` |
| `legal_entity_id` | integer | Yes | Legal entity ID | `13` |
| `employee_id` | integer | Yes | Entity employee ID | `67` |
| `role` | varchar(100) | No | Team member role | `"developer"`, `"designer"`, `"pm"`, `"qa"` |
| `billable_rate` | numeric(10,2) | No | Hourly billing rate | `150.00` |
| `allocation_pct` | numeric(5,2) | No | Time allocation percentage | `75.00` (75% of time) |
| `start_date` | date | Auto | Assignment start | `2024-01-15` |
| `end_date` | date | No | Assignment end | `2024-06-30` |
| `created_at` | timestamp | Auto | Creation timestamp | `2025-01-15 10:00:00-08` |
| `created_by` | integer | Auto | User ID who created | `30` |
| `updated_at` | timestamp | Auto | Last update timestamp | `2025-01-15 10:00:00-08` |
| `updated_by` | integer | Auto | User ID who updated | `30` |

### Project Milestones Table (project_milestones)

| Field Name | Data Type | Required | Description | Example |
|------------|-----------|----------|-------------|---------|
| `id` | integer | PK | System-generated ID | `567` |
| `project_id` | integer | Yes | FK to projects | `123` |
| `legal_entity_id` | integer | Yes | Legal entity ID | `13` |
| `milestone_name` | varchar(255) | Yes | Milestone/deliverable name | `"Phase 1: Design"` |
| `description` | text | No | Detailed description | `"Complete UI mockups..."` |
| `sequence_number` | integer | No | Order of milestone | `1`, `2`, `3` |
| `due_date` | date | No | Expected completion date | `2024-02-28` |
| `completion_date` | date | No | Actual completion date | `2024-02-25` |
| `amount` | numeric(15,2) | No | Billing amount | `10000.00` |
| `currency_code` | varchar(3) | No | Currency | `"USD"` |
| `linked_transaction_id` | bigint | No | FK to invoice transaction | `789` |
| `status` | varchar(50) | Auto | Milestone status | `"planned"`, `"in_progress"`, `"completed"`, `"invoiced"` |
| `metadata` | jsonb | No | Additional data | `{"client_approved": true}` |
| `created_at` | timestamp | Auto | Creation timestamp | `2025-01-15 10:00:00-08` |
| `created_by` | integer | Auto | User ID who created | `30` |
| `updated_at` | timestamp | Auto | Last update timestamp | `2025-01-15 10:00:00-08` |
| `updated_by` | integer | Auto | User ID who updated | `30` |

### Project Time Entries Table (project_time_entries)

| Field Name | Data Type | Required | Description | Example |
|------------|-----------|----------|-------------|---------|
| `id` | integer | PK | System-generated ID | `1234` |
| `project_id` | integer | Yes | FK to projects | `123` |
| `legal_entity_id` | integer | Yes | Legal entity ID | `13` |
| `employee_id` | integer | Yes | Entity employee ID | `67` |
| `task_id` | integer | No | FK to project_tasks | `890` |
| `entry_date` | date | Yes | Date of work | `2024-02-10` |
| `hours` | numeric(5,2) | Yes | Hours worked | `8.0` |
| `description` | text | No | What was done | `"Implemented login UI"` |
| `billable_flag` | boolean | Auto | Bill to client? | `true` |
| `billable_rate` | numeric(10,2) | No | Rate for this entry | `150.00` |
| `status` | varchar(50) | Auto | Approval status | `"draft"`, `"submitted"`, `"approved"`, `"rejected"`, `"billed"` |
| `submitted_at` | timestamp | Auto | Submission timestamp | `2024-02-11 09:00:00-08` |
| `approved_by` | integer | Auto | User ID who approved | `12` |
| `approved_at` | timestamp | Auto | Approval timestamp | `2024-02-11 14:00:00-08` |
| `rejection_reason` | text | No | Reason if rejected | `"Add more detail"` |
| `created_at` | timestamp | Auto | Creation timestamp | `2025-01-15 10:00:00-08` |
| `created_by` | integer | Auto | User ID who created | `30` |
| `updated_at` | timestamp | Auto | Last update timestamp | `2025-01-15 10:00:00-08` |
| `updated_by` | integer | Auto | User ID who updated | `30` |

---

## Workflow Documentation

### Project Core Workflows

#### Create Project

Create a new master project (organization-wide).

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="project", operation="create")

// Step 2: Submit with discovered fields
submit("project", "create", {
    project_name: "Website Redesign",
    description: "Complete redesign of corporate website with modern UI",
    customer_id: 123,
    project_code: "WEB-2024-01",
    project_type: "development",
    budget_amount: 50000.00,
    currency_code: "USD",
    start_date: "2024-01-15",
    end_date: "2024-06-30"
})
// Tip: Use validate_only=true to check payload before submitting
```

**Returns:**
```javascript
{
  success: true,
  project_id: 45,
  global_project_id: "PROJ-000001",
  status: "planning",
  workflow_id: "wf-uuid-here",
  lane: "green"
}
```

**Project Types:**
- `consulting` - Professional services, advisory
- `development` - Software development, custom apps
- `implementation` - System implementation, ERP rollout
- `maintenance` - Ongoing support, retainers
- `internal` - Internal projects (IT infrastructure, R&D)

#### Update Project

Update master project fields.

```javascript
submit("project", "update", {
    global_project_id: "PROJ-000001",
    project_name: "Website Redesign & Mobile App",
    description: "Expanded scope to include mobile app",
    end_date: "2024-08-31",
    budget_amount: 75000.00
})
```

#### Delete Project

Soft-delete project (sets status to archived/deleted).

```javascript
submit("project", "delete", {
    global_project_id: "PROJ-000001",
    deletion_reason: "Project cancelled by client"
})
```

**Validation:**
- Cannot delete project with active time entries
- Cannot delete project with unreconciled expenses
- Cannot delete project with open invoices

#### Assign Project to Entity

Assign project to a legal entity for execution.

```javascript
submit("project", "assign_to_entity", {
    global_project_id: "PROJ-000001",
    legal_entity_id: 13,
    project_manager_employee_id: 67,
    status: "active",
    priority: "high",
    budget_amount: 30000.00,
    currency_code: "USD",
    billing_model: "time_and_materials",
    planned_margin_pct: 25.00
})
```

**Returns:**
```javascript
{
  success: true,
  entity_project_id: 123,
  master_project_id: 45,
  legal_entity_id: 13,
  status: "active"
}
```

**Billing Models:**
- `time_and_materials` - Bill by hours worked (consulting, support)
- `fixed_price` - Single total price (well-defined scope)
- `milestone` - Bill on deliverables (phased projects)
- `retainer` - Monthly recurring (ongoing services)

**Multi-Entity Example:**

```javascript
// Same project assigned to US (billing) and UK (delivery)

// US entity - client-facing
submit("project", "assign_to_entity", {
    global_project_id: "PROJ-000010",
    legal_entity_id: 10,  // US Corp
    project_manager_employee_id: 12,
    billing_model: "milestone",
    budget_amount: 200000.00,
    currency_code: "USD"
})

// UK entity - delivery team
submit("project", "assign_to_entity", {
    global_project_id: "PROJ-000010",
    legal_entity_id: 11,  // UK Ltd
    project_manager_employee_id: 34,
    billing_model: "time_and_materials",
    budget_amount: 150000.00,
    currency_code: "GBP"
})
```

#### Close Project

Close/complete project with final status.

```javascript
submit("project", "close", {
    global_project_id: "PROJ-000001",
    completion_notes: "Project delivered successfully, client very satisfied",
    final_status: "completed"
})
```

**Final Status Options:**
- `completed` - Successfully finished
- `cancelled` - Project terminated
- `archived` - Historical record

**Pre-Close Checklist:**
- All time entries submitted and approved
- All expenses allocated and reconciled
- All milestones completed or closed
- All invoices created and linked
- All open tasks completed or closed

---

### Team Member Management

#### Add Team Member

Add team member to project.

```javascript
submit("project.team_member", "manage", {
    action: "add",
    global_project_id: "PROJ-000001",
    legal_entity_id: 13,
    employee_id: 67,
    role: "developer",
    billable_rate: 150.00,
    allocation_pct: 75.00,
    start_date: "2024-01-15"
})
```

**Returns:**
```javascript
{
  success: true,
  team_member_id: 456,
  action: "add"
}
```

**Common Roles:**
- `developer` - Software developer
- `designer` - UI/UX designer
- `pm` - Project manager
- `qa` - QA engineer/tester
- `architect` - Solutions architect
- `consultant` - Business consultant
- `analyst` - Business/data analyst

#### Update Team Member

Update team member allocation or rate.

```javascript
submit("project.team_member", "manage", {
    action: "update",
    team_member_id: 456,
    global_project_id: "PROJ-000001",
    allocation_pct: 100.00,
    billable_rate: 175.00
})
```

#### Remove Team Member

Remove team member from project.

```javascript
submit("project.team_member", "manage", {
    action: "delete",
    team_member_id: 456,
    global_project_id: "PROJ-000001",
    end_date: "2024-03-31"
})
```

**Building a Complete Team:**

```javascript
const project_id = "PROJ-000001";
const entity_id = 13;

// Senior Developer
submit("project.team_member", "manage", {
    action: "add",
    global_project_id: project_id,
    legal_entity_id: entity_id,
    employee_id: 67,
    role: "developer",
    billable_rate: 150.00,
    allocation_pct: 75.00
})

// Junior Developer
submit("project.team_member", "manage", {
    action: "add",
    global_project_id: project_id,
    legal_entity_id: entity_id,
    employee_id: 68,
    role: "developer",
    billable_rate: 80.00,
    allocation_pct: 100.00
})

// Designer
submit("project.team_member", "manage", {
    action: "add",
    global_project_id: project_id,
    legal_entity_id: entity_id,
    employee_id: 69,
    role: "designer",
    billable_rate: 120.00,
    allocation_pct: 50.00
})

// QA Engineer
submit("project.team_member", "manage", {
    action: "add",
    global_project_id: project_id,
    legal_entity_id: entity_id,
    employee_id: 70,
    role: "qa",
    billable_rate: 100.00,
    allocation_pct: 50.00
})
```

---

### Milestone Management

#### Add Milestone

Create project milestone/deliverable.

```javascript
submit("project.milestone", "manage", {
    action: "add",
    global_project_id: "PROJ-000001",
    legal_entity_id: 13,
    milestone_name: "Phase 1: Design",
    description: "Complete all design mockups and get client approval",
    due_date: "2024-02-28",
    amount: 10000.00,
    currency_code: "USD",
    sequence_number: 1
})
```

**Returns:**
```javascript
{
  success: true,
  milestone_id: 567,
  action: "add"
}
```

#### Update Milestone

Update milestone details or status.

```javascript
submit("project.milestone", "manage", {
    action: "update",
    milestone_id: 567,
    global_project_id: "PROJ-000001",
    status: "completed",
    completion_date: "2024-02-25",
    metadata: {
      client_approved: true,
      approval_date: "2024-02-25",
      notes: "Client very satisfied with mockups"
    }
})
```

**Milestone Status Flow:**
```
planned → in_progress → completed → invoiced
```

#### Delete Milestone

Remove milestone from project.

```javascript
submit("project.milestone", "manage", {
    action: "delete",
    milestone_id: 567,
    global_project_id: "PROJ-000001"
})
```

**Fixed-Price Milestone Project Example:**

```javascript
// $50K project with 5 milestones

const milestones = [
  { name: "Phase 1: Design", due: "2024-02-28", amount: 10000.00 },
  { name: "Phase 2: Development", due: "2024-04-30", amount: 25000.00 },
  { name: "Phase 3: Testing", due: "2024-05-31", amount: 5000.00 },
  { name: "Phase 4: Deployment", due: "2024-06-15", amount: 5000.00 },
  { name: "Phase 5: Training", due: "2024-06-30", amount: 5000.00 }
];

for (let i = 0; i < milestones.length; i++) {
  submit("project.milestone", "manage", {
      action: "add",
      global_project_id: "PROJ-000001",
      legal_entity_id: 13,
      milestone_name: milestones[i].name,
      due_date: milestones[i].due,
      amount: milestones[i].amount,
      sequence_number: i + 1
    }
  })
}
```

---

### Time Entry Management

#### Add Time Entry

Record billable or non-billable time.

```javascript
submit("project.time_entry", "manage", {
    action: "add",
    global_project_id: "PROJ-000001",
    legal_entity_id: 13,
    employee_id: 67,
    entry_date: "2024-02-10",
    hours: 8.0,
    description: "Implemented login UI and authentication flow",
    task_id: 890,  // Optional: link to task
    billable_flag: true,
    billable_rate: 150.00
})
```

**Returns:**
```javascript
{
  success: true,
  time_entry_id: 1234,
  action: "add",
  billable_amount: 1200.00  // 8 hours × $150
}
```

#### Update Time Entry

Update time entry details (only if status = draft).

```javascript
submit("project.time_entry", "manage", {
    action: "update",
    time_entry_id: 1234,
    global_project_id: "PROJ-000001",
    hours: 7.5,
    description: "Implemented login UI and authentication flow - updated hours"
})
```

#### Submit Time Entry

Submit time entry for approval.

```javascript
submit("project.time_entry", "manage", {
    action: "submit",
    time_entry_id: 1234,
    global_project_id: "PROJ-000001",
    submission_notes: "Week of Feb 10-16"
})
```

**Status:** `draft` → `submitted`

#### Approve Time Entry

Approve submitted time entry (requires manager permission).

```javascript
submit("project.time_entry", "manage", {
    action: "approve",
    time_entry_id: 1234,
    global_project_id: "PROJ-000001",
    approval_notes: "Approved for billing"
})
```

**Status:** `submitted` → `approved`

#### Reject Time Entry

Reject submitted time entry with reason.

```javascript
submit("project.time_entry", "manage", {
    action: "reject",
    time_entry_id: 1234,
    global_project_id: "PROJ-000001",
    rejection_reason: "Please add more detail to description"
})
```

**Status:** `submitted` → `rejected` (employee can edit and resubmit)

**Time Entry Workflow:**
```
draft → submitted → approved → billed
          ↓
       rejected → draft (resubmit)
```

#### Delete Time Entry

Delete time entry (only if status = draft or rejected).

```javascript
submit("project.time_entry", "manage", {
    action: "delete",
    time_entry_id: 1234,
    global_project_id: "PROJ-000001"
})
```

---

### Expense & Revenue Allocation

#### Allocate Expense

Link expense transaction to project.

```javascript
submit("project.expense", "manage", {
    action: "add",
    global_project_id: "PROJ-000001",
    legal_entity_id: 13,
    transaction_id: 456,
    allocation_amount: 5000.00,
    expense_category: "cloud_hosting",
    notes: "AWS costs for Feb 2024"
})
```

**Returns:**
```javascript
{
  success: true,
  allocation_id: 789,
  action: "add"
}
```

**Expense Categories:**
- `cloud_hosting` - AWS, Azure, GCP
- `contractors` - External contractors
- `travel` - Travel and expenses
- `software_licenses` - Tools and software
- `equipment` - Hardware and equipment
- `other` - Miscellaneous

**Splitting Expenses Across Projects:**

```javascript
// $10K contractor invoice split between 2 projects

// 60% to Website project
submit("project.expense", "manage", {
    action: "add",
    global_project_id: "PROJ-000001",
    legal_entity_id: 13,
    transaction_id: 456,
    allocation_amount: 6000.00,
    expense_category: "contractors"
})

// 40% to Mobile App project
submit("project.expense", "manage", {
    action: "add",
    global_project_id: "PROJ-000002",
    legal_entity_id: 13,
    transaction_id: 456,
    allocation_amount: 4000.00,
    expense_category: "contractors"
})

// Total allocations: $10K (matches transaction)
```

#### Update Expense Allocation

Update expense allocation amount or category.

```javascript
submit("project.expense", "manage", {
    action: "update",
    allocation_id: 789,
    global_project_id: "PROJ-000001",
    allocation_amount: 5500.00,
    notes: "Adjusted allocation after invoice correction"
})
```

#### Delete Expense Allocation

Remove expense allocation from project.

```javascript
submit("project.expense", "manage", {
    action: "delete",
    allocation_id: 789,
    global_project_id: "PROJ-000001"
})
```

#### Allocate Revenue

Link revenue transaction (invoice) to project.

```javascript
submit("project.revenue", "manage", {
    action: "add",
    global_project_id: "PROJ-000001",
    legal_entity_id: 13,
    transaction_id: 789,
    allocation_amount: 10000.00,
    revenue_category: "milestone_billing",
    milestone_id: 567,
    notes: "Phase 1 completion invoice"
})
```

**Revenue Categories:**
- `milestone_billing` - Milestone/deliverable invoices
- `time_and_materials` - Hourly billing
- `fixed_price` - Fixed price payment
- `retainer` - Monthly retainer
- `change_order` - Scope change billing

#### Update Revenue Allocation

Update revenue allocation details.

```javascript
submit("project.revenue", "manage", {
    action: "update",
    allocation_id: 890,
    global_project_id: "PROJ-000001",
    allocation_amount: 12000.00,
    notes: "Updated to reflect scope expansion"
})
```

#### Delete Revenue Allocation

Remove revenue allocation from project.

```javascript
submit("project.revenue", "manage", {
    action: "delete",
    allocation_id: 890,
    global_project_id: "PROJ-000001"
})
```

---

### Dimension Management

#### Assign Dimension

Tag project with department, cost center, or other dimensions.

```javascript
submit("project.dimension", "manage", {
    action: "add",
    global_project_id: "PROJ-000001",
    legal_entity_id: 13,
    dimension_type_code: "DEPT",
    dimension_value_code: "Engineering"
})
```

**Multiple Dimensions Example:**

```javascript
const project_id = "PROJ-000001";
const entity_id = 13;

// Department
submit("project.dimension", "manage", {
    action: "add",
    global_project_id: project_id,
    legal_entity_id: entity_id,
    dimension_type_code: "DEPT",
    dimension_value_code: "Engineering"
})

// Cost Center
submit("project.dimension", "manage", {
    action: "add",
    global_project_id: project_id,
    legal_entity_id: entity_id,
    dimension_type_code: "COST_CENTER",
    dimension_value_code: "ENG-001"
})

// Location
submit("project.dimension", "manage", {
    action: "add",
    global_project_id: project_id,
    legal_entity_id: entity_id,
    dimension_type_code: "LOCATION",
    dimension_value_code: "NYC"
})
```

#### Remove Dimension

Remove dimension assignment from project.

```javascript
submit("project.dimension", "manage", {
    action: "delete",
    project_dimension_id: 999,
    global_project_id: "PROJ-000001"
})
```

---

## Common Project Scenarios

### Scenario 1: Time & Materials Consulting Project

**Setup:**

```javascript
// 1. Create master project
const project = submit("project", "create", {
    project_name: "Management Consulting Services",
    description: "Strategic advisory for digital transformation",
    customer_id: 123,
    project_type: "consulting",
    budget_amount: 100000.00,
    currency_code: "USD"
})
// Returns: { global_project_id: "PROJ-000001" }

// 2. Assign to entity
submit("project", "assign_to_entity", {
    global_project_id: "PROJ-000001",
    legal_entity_id: 13,
    project_manager_employee_id: 12,
    status: "active",
    billing_model: "time_and_materials",
    planned_margin_pct: 30.00
})

// 3. Add team
submit("project.team_member", "manage", {
    action: "add",
    global_project_id: "PROJ-000001",
    legal_entity_id: 13,
    employee_id: 67,
    role: "consultant",
    billable_rate: 200.00,
    allocation_pct: 100.00
})
```

**Weekly Time Tracking:**

```javascript
// Employee records time daily
submit("project.time_entry", "manage", {
    action: "add",
    global_project_id: "PROJ-000001",
    legal_entity_id: 13,
    employee_id: 67,
    entry_date: "2024-02-10",
    hours: 8.0,
    description: "Client workshop - digital strategy session",
    billable_flag: true,
    billable_rate: 200.00
})

// End of week: Submit for approval
submit("project.time_entry", "manage", {
    action: "submit",
    time_entry_id: 1234,
    global_project_id: "PROJ-000001",
    submission_notes: "Week of Feb 10-16, 40 hours total"
})

// Manager approves
submit("project.time_entry", "manage", {
    action: "approve",
    time_entry_id: 1234,
    global_project_id: "PROJ-000001",
    approval_notes: "Approved"
})
```

**Monthly Invoicing:**

```javascript
// Create invoice for approved time
// Then link revenue to project
submit("project.revenue", "manage", {
    action: "add",
    global_project_id: "PROJ-000001",
    legal_entity_id: 13,
    transaction_id: 789,  // Invoice transaction ID
    allocation_amount: 16000.00,  // 40 hrs × 4 weeks × $200
    revenue_category: "time_and_materials"
})
```

---

### Scenario 2: Fixed-Price Development Project with Milestones

**Setup:**

```javascript
// 1. Create project
const project = submit("project", "create", {
    project_name: "Mobile App Development",
    customer_id: 456,
    project_type: "development",
    budget_amount: 75000.00,
    start_date: "2024-03-01",
    end_date: "2024-08-31"
})

// 2. Assign to entity
submit("project", "assign_to_entity", {
    global_project_id: project.global_project_id,
    legal_entity_id: 13,
    project_manager_employee_id: 12,
    billing_model: "milestone",
    status: "active"
})

// 3. Create milestones
const milestones = [
  { name: "Design & Wireframes", due: "2024-03-31", amount: 15000.00 },
  { name: "Backend API", due: "2024-05-31", amount: 30000.00 },
  { name: "Mobile UI", due: "2024-07-31", amount: 20000.00 },
  { name: "Testing & Launch", due: "2024-08-31", amount: 10000.00 }
];

for (let i = 0; i < milestones.length; i++) {
  submit("project.milestone", "manage", {
      action: "add",
      global_project_id: project.global_project_id,
      legal_entity_id: 13,
      milestone_name: milestones[i].name,
      due_date: milestones[i].due,
      amount: milestones[i].amount,
      sequence_number: i + 1
    }
  })
}
```

**Milestone Completion Flow:**

```javascript
// 1. Complete milestone
submit("project.milestone", "manage", {
    action: "update",
    milestone_id: 567,
    global_project_id: "PROJ-000002",
    status: "completed",
    completion_date: "2024-03-28",
    metadata: {
      client_approved: true,
      approval_date: "2024-03-28"
    }
})

// 2. Create invoice for milestone
// (Create invoice transaction via unified transactions)

// 3. Link revenue to project
submit("project.revenue", "manage", {
    action: "add",
    global_project_id: "PROJ-000002",
    legal_entity_id: 13,
    transaction_id: 890,
    allocation_amount: 15000.00,
    revenue_category: "milestone_billing",
    milestone_id: 567
})

// 4. Update milestone status
submit("project.milestone", "manage", {
    action: "update",
    milestone_id: 567,
    global_project_id: "PROJ-000002",
    status: "invoiced",
    linked_transaction_id: 890
})
```

---

### Scenario 3: Internal Project (Cost Tracking Only)

**Setup:**

```javascript
// 1. Create internal project (no customer)
const project = submit("project", "create", {
    project_name: "ERP System Upgrade",
    project_type: "internal",
    budget_amount: 50000.00,
    start_date: "2024-02-01",
    end_date: "2024-06-30"
})

// 2. Assign to entity
submit("project", "assign_to_entity", {
    global_project_id: project.global_project_id,
    legal_entity_id: 13,
    project_manager_employee_id: 12,
    status: "active"
})

// 3. Tag with IT department
submit("project.dimension", "manage", {
    action: "add",
    global_project_id: project.global_project_id,
    legal_entity_id: 13,
    dimension_type_code: "DEPT",
    dimension_value_code: "IT"
})
```

**Track Internal Costs:**

```javascript
// Track employee time (non-billable)
submit("project.time_entry", "manage", {
    action: "add",
    global_project_id: "PROJ-000003",
    legal_entity_id: 13,
    employee_id: 67,
    entry_date: "2024-02-10",
    hours: 8.0,
    description: "Data migration and testing",
    billable_flag: false  // Internal time
})

// Allocate vendor costs
submit("project.expense", "manage", {
    action: "add",
    global_project_id: "PROJ-000003",
    legal_entity_id: 13,
    transaction_id: 456,
    allocation_amount: 25000.00,
    expense_category: "software_licenses",
    notes: "ERP software licenses"
})
```

**Result:**
- Track total project cost
- No revenue tracking
- Budget monitoring only

---

### Scenario 4: Multi-Entity Global Project

**Setup:**

```javascript
// 1. Create master project
const project = submit("project", "create", {
    project_name: "Global Customer Portal",
    customer_id: 789,
    budget_amount: 150000.00,
    currency_code: "USD",
    start_date: "2024-03-01",
    end_date: "2024-12-31"
})

// 2. Assign to US entity (client-facing, billing)
submit("project", "assign_to_entity", {
    global_project_id: project.global_project_id,
    legal_entity_id: 10,  // US Corp
    project_manager_employee_id: 12,
    billing_model: "milestone",
    budget_amount: 150000.00,  // Revenue budget
    currency_code: "USD",
    status: "active"
})

// 3. Assign to India entity (delivery team)
submit("project", "assign_to_entity", {
    global_project_id: project.global_project_id,
    legal_entity_id: 15,  // India Pvt Ltd
    project_manager_employee_id: 45,
    billing_model: "time_and_materials",
    budget_amount: 75000.00,  // Cost budget
    currency_code: "INR",
    status: "active"
})
```

**US Team: Create milestones and bill client**

```javascript
submit("project.milestone", "manage", {
    action: "add",
    global_project_id: project.global_project_id,
    legal_entity_id: 10,  // US
    milestone_name: "Phase 1: Requirements & Design",
    amount: 50000.00,
    due_date: "2024-05-31",
    sequence_number: 1
})
```

**India Team: Track delivery costs**

```javascript
submit("project.time_entry", "manage", {
    action: "add",
    global_project_id: project.global_project_id,
    legal_entity_id: 15,  // India
    employee_id: 67,
    entry_date: "2024-03-10",
    hours: 8.0,
    billable_rate: 25.00,  // USD equivalent
    billable_flag: false  // Internal cost
})
```

**Consolidated View:**
- Entity 10 (US): Revenue tracking ($150K)
- Entity 15 (India): Cost tracking ($75K in USD equivalent)
- Global margin: $150K - $75K = $75K (50% margin)

---

## Query Examples

### Get Project

Retrieve single project by ID or global ID.

```javascript
get_entity("project", id=45)
// or: get_entity("project", global_id="PROJ-000001")

// Returns (with virtual fields resolved inline):
// {
//   master_project_id: 45,
//   global_project_id: "PROJ-000001",
//   project_name: "Website Redesign",
//   customer_id: 123,
//   customer_name: "ACME Corp",              ← resolved inline
//   project_manager_name: "John Smith",       ← resolved inline
//   budget_amount: 50000.00,
//   currency_code: "USD",
//   status: "active",
//   start_date: "2024-01-15",
//   end_date: "2024-12-31",
//   ...
// }
// include_related=True by default — includes team members, milestones, etc.
```

### List Projects

List projects with filters and pagination.

```javascript
query("project", filters={"status": "active", "customer_id": 123})

// Returns paginated array with customer_name and project_manager_name inline:
// [
//   { global_project_id: "PROJ-000001", project_name: "Website Redesign", customer_name: "ACME Corp", ... },
//   { global_project_id: "PROJ-000005", project_name: "Mobile App", customer_name: "ACME Corp", ... }
// ]
```

### Search Projects

Search projects by text query.

```javascript
query("project", query="website", filters={"status": "active"})
```

### Get Project Team

The team comes back with the project record (`related.team_members`).

```javascript
get_entity("project", id=<project id>)
// related.team_members: [{ employee_id: 67, role: "developer", billable_rate: 150.00, allocation_pct: 75.00 }, ...]
```

### Get Project Profitability

Sum the project's posted GL lines by account; revenue and cost come from each account's type.

```javascript
query("transaction_line",
      filters={legal_entity_id: 13, project_id: <project id>},
      group_by=["account_number"],
      aggregates={debit: "sum", credit: "sum"})
```

---

## Best Practices

### Project Setup

**1. Always Create Master First:**

```javascript
// GOOD: Create master, then assign to entities
const project = submit("project", "create", { project_name: "Website Redesign", ... }
})

submit("project", "assign_to_entity", { global_project_id: project.global_project_id, ... }
})

// BAD: Can't assign without master
```

**2. Set Up Team Before Tracking Time:**

```javascript
// GOOD: Add team member with rate first
submit("project.team_member", "manage", {
    action: "add",
    employee_id: 67,
    billable_rate: 150.00
})

// Then record time
submit("project.time_entry", "manage", {
    action: "add",
    employee_id: 67,
    billable_rate: 150.00  // Uses team member rate
})
```

**3. Create Milestones at Project Start:**

```javascript
// GOOD: Define all milestones upfront
const milestones = [...];
for (let m of milestones) {
  submit("project.milestone", "manage", { action: "add", ... })
}

// Gives clear roadmap and billing schedule
```

### Time Tracking

**1. Submit Time Weekly:**

```javascript
// GOOD: Weekly time submission
// Monday-Friday: Record time daily (status: draft)
// Friday EOD: Submit all entries for the week
submit("project.time_entry", "manage", {
    action: "submit",
    time_entry_ids: [1234, 1235, 1236, 1237, 1238]
})

// BAD: Submitting once per month (too late for corrections)
```

**2. Consistent Descriptions:**

```javascript
// GOOD: Clear, specific descriptions
{
  description: "Implemented user authentication with OAuth 2.0 integration"
}

// BAD: Vague descriptions
{
  description: "Worked on login"
}
```

**3. Approve Time Promptly:**

```javascript
// GOOD: Approve within 2 business days
// Manager reviews and approves by Tuesday

// BAD: Waiting until month-end (delays billing)
```

### Expense Allocation

**1. Allocate Expenses When Incurred:**

```javascript
// GOOD: Allocate immediately after expense recorded
submit("project.expense", "manage", {
    action: "add",
    transaction_id: 456,  // Just created
    allocation_amount: 5000.00
})

// BAD: Allocating expenses at month-end (hard to track)
```

**2. Split Shared Costs Proportionally:**

```javascript
// GOOD: $10K contractor split 60/40 based on actual work
submit("project.expense", "manage", {
    global_project_id: "PROJ-000001",
    allocation_amount: 6000.00  // 60%
})

submit("project.expense", "manage", {
    global_project_id: "PROJ-000002",
    allocation_amount: 4000.00  // 40%
})

// Total = $10K (matches transaction)
```

### Milestone Billing

**1. Complete → Invoice → Link Revenue:**

```javascript
// GOOD: Follow the sequence
// Step 1: Complete milestone
submit("project.milestone", "manage", {
    action: "update",
    status: "completed",
    completion_date: "2024-02-28"
})

// Step 2: Create invoice transaction

// Step 3: Link revenue to project
submit("project.revenue", "manage", {
    action: "add",
    milestone_id: 567,
    transaction_id: 789
})

// Step 4: Update milestone
submit("project.milestone", "manage", {
    action: "update",
    status: "invoiced",
    linked_transaction_id: 789
})
```

### Project Closure

**1. Pre-Close Checklist:**

```javascript
// Before closing project, verify:
// ✓ All time entries submitted and approved
// ✓ All expenses allocated
// ✓ All milestones completed or cancelled
// ✓ All invoices created
// ✓ No open tasks
// ✓ Fixed assets reassigned or unassigned

// Then close:
submit("project", "close", {
    global_project_id: "PROJ-000001",
    completion_notes: "...",
    final_status: "completed"
})
```

---

## Common Pitfalls

### ❌ Pitfall 1: Not Assigning Project to Entity

**Wrong:**
```javascript
// Create master project
const project = submit("project", "create", { project_name: "Website Redesign" }
})

// Try to add team member (will fail!)
submit("project.team_member", "manage", {
    global_project_id: project.global_project_id,
    legal_entity_id: 13,
    employee_id: 67
})
// ERROR: Project not assigned to entity 13
```

**Correct:**
```javascript
// Create master
const project = submit("project", "create", { project_name: "Website Redesign" }
})

// Assign to entity first
submit("project", "assign_to_entity", {
    global_project_id: project.global_project_id,
    legal_entity_id: 13
})

// Now add team member
submit("project.team_member", "manage", {
    action: "add",
    global_project_id: project.global_project_id,
    legal_entity_id: 13,
    employee_id: 67
})
```

---

### ❌ Pitfall 2: Approving Time Before Submission

**Wrong:**
```javascript
// Record time (status: draft)
submit("project.time_entry", "manage", { action: "add", ... }
})

// Try to approve immediately (will fail!)
submit("project.time_entry", "manage", { action: "approve", time_entry_id: 1234 }
})
// ERROR: Cannot approve time entry in 'draft' status
```

**Correct:**
```javascript
// Record time
submit("project.time_entry", "manage", { action: "add", ... }
})

// Submit first
submit("project.time_entry", "manage", { action: "submit", time_entry_id: 1234 }
})

// Now approve
submit("project.time_entry", "manage", { action: "approve", time_entry_id: 1234 }
})
```

---

### ❌ Pitfall 3: Closing Project with Open Items

**Wrong:**
```javascript
// Try to close project with open time entries
submit("project", "close", {
    global_project_id: "PROJ-000001",
    final_status: "completed"
})
// ERROR: Project has 15 draft time entries
```

**Correct:**
```javascript
// Submit and approve all time entries first
// Complete or cancel all milestones
// Close all open tasks
// Then close project

submit("project", "close", {
    global_project_id: "PROJ-000001",
    final_status: "completed"
})
```

---

### ❌ Pitfall 4: Mismatched Expense Allocation

**Wrong:**
```javascript
// $10K transaction, but allocations don't match
submit("project.expense", "manage", {
    transaction_id: 456,  // $10,000 transaction
    allocation_amount: 7000.00  // Only allocated $7K!
})
// Unallocated: $3,000
```

**Correct:**
```javascript
// Fully allocate the transaction
submit("project.expense", "manage", {
    global_project_id: "PROJ-000001",
    transaction_id: 456,
    allocation_amount: 6000.00  // 60%
})

submit("project.expense", "manage", {
    global_project_id: "PROJ-000002",
    transaction_id: 456,
    allocation_amount: 4000.00  // 40%
})

// Total: $10K (matches transaction)
```

---

## Getting Reference Data

### Get Organization Projects

**CORRECT - Use dynamic query:**
```javascript
query("project", filters={"status": "active"})
// Returns customer_name and project_manager_name inline
```

**DO NOT - Use static references:**
```javascript
// ❌ WRONG: Don't hardcode project IDs
const project_id = 123;  // Will break if data changes
```

---

### Get Project Team Members

**CORRECT - Use get_entity with related data:**
```javascript
get_entity("project", id=45)
// include_related=True by default — returns team members, milestones, etc.
```

---

### Get Customer Projects

**CORRECT - Use list with filter:**
```javascript
query("project", filters={"customer_id": 123, "status": "active"})
// customer_name is returned inline — no need for a separate customer lookup
```

---

## Quick Reference

### Project Status

| Status | Description | Can Track Time? | Can Invoice? |
|--------|-------------|-----------------|--------------|
| `planning` | Pre-kickoff planning | No | No |
| `active` | Actively executing | Yes | Yes |
| `on_hold` | Temporarily paused | Yes | Maybe |
| `completed` | Successfully finished | No | Yes |
| `cancelled` | Project terminated | No | No |
| `archived` | Historical record | No | No |

### Billing Models

| Model | Description | When to Use | Invoice Frequency |
|-------|-------------|-------------|-------------------|
| `time_and_materials` | Bill by hours worked | Consulting, support | Weekly/Monthly |
| `fixed_price` | Single total price | Well-defined scope | Upon completion |
| `milestone` | Bill on deliverables | Phased projects | Per milestone |
| `retainer` | Monthly recurring | Ongoing services | Monthly |

### Time Entry Status

| Status | Description | Can Edit? | Can Delete? |
|--------|-------------|-----------|-------------|
| `draft` | Not yet submitted | Yes | Yes |
| `submitted` | Awaiting approval | No | No |
| `approved` | Approved for billing | No | No |
| `rejected` | Rejected, needs revision | Yes | Yes |
| `billed` | Invoiced to client | No | No |

### Project Types

| Type | Description | Common Use Cases |
|------|-------------|------------------|
| `consulting` | Professional services | Advisory, strategy, analysis |
| `development` | Software development | Custom apps, integrations, APIs |
| `implementation` | System implementation | ERP rollout, migrations, setup |
| `maintenance` | Ongoing support | Retainers, managed services, updates |
| `internal` | Internal projects | IT infrastructure, R&D, tools |

---

## Key Takeaways

1. **Master + Entity Pattern**: Projects use MSEO pattern (master project + entity assignments)

2. **Explicit Entity Assignment**: Projects must be explicitly assigned to entities before use

3. **Multi-Entity Support**: Same project can be assigned to multiple entities with different PMs/budgets

4. **Time Entry Workflow**: draft → submitted → approved → billed (with rejection path)

5. **Milestone Billing**: Complete milestone → create invoice → link revenue → update status

6. **Expense Allocation**: Link expenses to projects for accurate profitability tracking

7. **Team Management**: Track roles, rates, and allocation percentages for all team members

8. **Dimension Integration**: Tag projects with departments, cost centers, campaigns for analytics

9. **Project Closure**: Verify all items closed before completing project

10. **Profitability Tracking**: Revenue - Costs = Margin (tracked at project level)

---

**Version**: 1.0
**Last Updated**: 2025-01-15
**Related Resources**: [Employees](employee-management.md), [Customers](customer-management.md), Unified Transactions, [Dimensions](dimensions-management.md)

## Entity update and ISO dates

For `project.update`, include `legal_entity_id` to change the entity's status,
manager (entity employee ID), budget/currency or effective dates. Without it,
status/budget/currency change master defaults only. Team/milestone/task/time-entry
dates use `YYYY-MM-DD` on add/update. Use milestone status `pending` initially.


### Admin project progress and invoice linkage (PR #224, October 2026)

When the loaded project has one entity assignment, its effective entity status
is displayed ahead of the master status. With multiple assignments, the header
retains the master status. Completed milestone value describes completed milestones
with amounts; it is not billed-to-date or proof of an invoice. The remaining-value
label explicitly states that it is budget less milestone value.

AR invoice project references persist on header, business lines and GL, with
line override and entity/date validation. Revenue allocation and time billing
remain separate workflows; invoice linkage does not automatically mark them billed.
