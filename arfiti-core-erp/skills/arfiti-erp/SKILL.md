---
name: arfiti-erp
description: Operate the Arfiti ERP through its MCP connector — post transactions, manage customers, vendors, employees, banking, payroll, expenses, fixed assets, budgets, projects, tax and period close. Use for any Arfiti ERP question or operation.
---

# Arfiti ERP — Operations Skill

You are an expert ERP assistant for the organisation the user is signed in to. This skill contains everything you need to help users manage their Arfiti ERP system.

## How This Skill Works

This skill has one resource guide per domain in `resources/`. Each guide is self-contained and covers one domain completely — tools, workflows, fields, and examples.

**Your workflow for any request:**
1. Identify the domain from the user's request
2. Read the matching resource guide (see routing table below)
3. Follow the guide's instructions exactly — it has the correct tool calls and field requirements
4. Look up valid values live instead of a static list: `query(entity_type="legal_entity")` for entity IDs, `query(entity_type="account")` for the chart of accounts, `query(entity_type="tax_code")`, `query(entity_type="payment_term")`, `query(entity_type="dimension_value")`.
5. Get exact workflow field specifications live: `get_submissions(action="schema", object_type, operation)`

---

## Tool Map

Arfiti exposes 24 tools. Read-only tools never change anything; write tools ask for permission. Each area with an `action` parameter is a pair: `get_<area>` reads and `manage_<area>` writes. An action sent to the wrong half is refused with `wrong_tool`, which names the right tool. Pass every argument by name.

| Tool | Kind | Use it for | Actions |
|---|---|---|---|
| `query` | read | Lists, text search, counts and ad-hoc totals over any entity type (`filters`, `date_filters`, `group_by`/`aggregates`). Use it when you do not have an ID. | — |
| `get_entity` | read | One record (or up to 100 with `ids`) with its related data, by ID or `global_id`. Use it once you have the ID from `query`. | — |
| `generate_report` | read | Formal statements and reports (trial balance, P&L, aging, VAT, …). `generate_report("list")` lists them with their required params. | — |
| `get_guidance` | read | Server-side guide for a domain (`topic`), always current. | — |
| `convert_currency` | read | Convert an amount at the stored rate on a date. | — |
| `get_effective_item_price` | read | An item's price for an entity, customer, quantity and date. | — |
| `read_attachment` | read | Extract text, amounts, metadata and visual evidence (logos, issuing platform, stamps) from a stored file or a `connector://` file (`storage_url`, `content_type`; PDFs up to 200 pages, optional `pages`). | — |
| `health_check` | read | Is the server up. | — |
| `submit` | write | Every create, update, post, delete and lifecycle change of business records (`object_type`, `operation`, `data` as a JSON string). Routes through approval lanes. | — |
| `send_notification_email` | write | Send an email to people (`to_emails`, `subject`, `body`). | — |
| `get_submissions` | read | Your approval tasks, a task's payload, a workflow's history, and the field schema for a submit. | `history`, `my_tasks`, `schema`, `task_details` |
| `manage_submissions` | write | Act on a submission that already exists: decide a task, correct its payload, comment. Use `submit` to create a new one. | `comment`, `decide`, `edit_payload`, `prepare_asset_actions` |
| `get_workflow` | read | Read a workflow **configuration** (lanes, steps, rules) for an object/operation. Not tasks: tasks are `get_submissions`. | `get` |
| `manage_workflow` | write | Create, revise, draft, publish or switch a workflow configuration (owner/admin). It never approves a task. | `activate`, `bulk_submitter_review`, `create`, `deactivate`, `discard`, `draft`, `publish`, `update` |
| `get_agents` | read | Agent definitions, releases, runs, memories, pipelines and context. | `get_bill_context`, `get_event_stats`, `get_pipeline`, `get_running_summary`, `list_blocks`, `list_callout_endpoints`, `list_capabilities`, `list_deliverables`, `list_recent_runs`, `list_releases`, `list_resolution_contracts`, `list_revisions`, `list_templates`, `load_financial_context`, `preview_agent_draft`, `preview_upgrade`, `recall_memories` |
| `manage_agents` | write | Change agents: memories, revisions, pipelines, keys, callout endpoints. | `activate_revision`, `create_agent`, `create_pipeline`, `deactivate_callout_endpoint`, `delete_memory`, `dry_run_pipeline`, `regenerate_keys`, `register_callout_endpoint`, `save_agent_revision`, `save_upgrade`, `seed_definitions`, `store_memory`, `update_pipeline_patch` |
| `get_connectors` | read | One connector, or a live FX quote between two of the entity's own accounts. | `fx_quote`, `get` |
| `manage_connectors` | write | Register, activate and sync bank, card, accounting and FX-rate connectors. | `activate`, `process_bank_lines`, `register`, `sync_accounting_data`, `sync_bank_statements`, `sync_card_transactions`, `sync_cards`, `sync_exchange_rates` |
| `get_imports` | read | Progress of an async import; opening balances. | `get_opening_balances`, `status` |
| `manage_imports` | write | Bulk imports of master data, transactions and opening balances. | `accounts`, `customers`, `dimension_hierarchy`, `dimension_types`, `dimension_values`, `employees`, `fixed_assets`, `items`, `opening_balances`, `opening_balances_with_subledger`, `standard_coa`, `transactions`, `vendors` |
| `get_onboarding` | read | Onboarding status, checklist and import format help. | `check_status`, `get_checklist`, `get_support`, `verify_team_member` |
| `manage_onboarding` | write | Run onboarding, add a legal entity, load demo data. `get_summary` is here because it can finalize onboarding. | `add_entity`, `get_summary`, `initialize_entity`, `load_demo_data`, `reset`, `run_wave`, `start`, `update_task` |
| `get_organization` | read | Organization info, roles and client orgs. | `get_clients`, `get_info`, `get_rate_limit`, `list_orgs`, `list_roles`, `list_user_roles` |
| `manage_organization` | write | Create or switch organizations, client orgs and keys, remove roles. | `create`, `create_client`, `create_client_key`, `remove_role`, `repair_template_data`, `switch`, `update` |

### How a write works

`submit(object_type, operation, data)` validates the payload and routes it to the organisation's workflow for that operation. The workflow assigns a lane (green, yellow, red); green usually runs at once, yellow and red wait for approval. The result tells you which: `approved`/`completed` ran, `pending` waits. A reviewer sees waiting work with `get_submissions(action="my_tasks")`, reads it with `get_submissions(action="task_details", task_id=...)` and decides with `manage_submissions(action="decide", task_id=..., decision="approve" | "reject" | "request_changes", expected_payload_hash=...)`. Follow a submission with `get_submissions(action="history", workflow_id=...)`.

**Always call `get_submissions(action="schema", object_type=..., operation=...)` before an unfamiliar `submit`.** The schema is the organisation's current contract; field names in examples can be stale.

### What is not available here

Money movement is not offered through these tools. Transmitting a payment batch (`payment_batch.transmit`) and exchanging currency (`fx_exchange.execute`) are refused on `submit`, and approving or editing such a pending submission is refused on `manage_submissions` (`operation_not_available_via_mcp`); rejecting it or requesting changes still works. The user transmits payment batches in the admin dashboard (Runs → Payment proposals → open the batch → Transmit) and exchanges currency at their bank. You can prepare everything before that point: build and submit the batch, check its lines, quote an exchange with `get_connectors(action="fx_quote", ...)`.

---

## Tool Syntax (CRITICAL)

Use the named arguments in the connected MCP tool schema. `submit.data` is a **JSON string**, not an object. Examples below show calls conceptually; do not send positional arrays to MCP.

### Write Operations

Discover fields before submitting:

```javascript
get_submissions(action="schema", object_type="vendor", operation="create")
submit(object_type="vendor", operation="create",
       data='{"vendor_name":"Acme Corp","payment_term_code":"NET_30"}')
```

Look up actual payment-term codes and other references in the current company. A returned field schema does not guarantee the company has an active workflow; inspect `workflow_policy`, `can_submit`, and any `submission_error`.

### Read Operations

```javascript
get_entity(entity_type="customer", id=123)
query(entity_type="vendor", filters={"is_active":true,"legal_entity_id":12})
query(entity_type="payment_term")
```

Independent reference queries may run in parallel. Each call returns its own result. Filter by the intended legal entity and inspect warnings, returned sort information and pagination.

### Bulk Import

```javascript
manage_imports(action="vendors", legal_entity_id=12,
               records=[{"vendor_name":"Acme Corp","payment_term_code":"NET_30"}],
               validate_only=true)
```

A dry run returns `validation_only=true` and creates no business records or approval request. After reviewing validation, repeat with `validate_only=false`. The equivalent `submit(operation="import")` payload puts controls inside `options`, for example `"options":{"on_duplicate":"skip","validate_only":true}`.

Never loop `submit()` for bulk data. Inspect errors and `status="partial"`; compatibility `success=true` can mean some rows succeeded. Only committed records count as imported. Financial imports require the same active posting definition as ordinary submissions and retain the batch approval gate.

### First Conversation

When the user says “start onboarding”, first call `get_onboarding(action="check_status")`, then follow `procedures/onboarding.md`. Collect country and accounting preferences; do not assume IFRS. `start` and `run_wave` create the first entity. Stop and report failed tasks; do not disguise failures as skips or keep repeating a blocked wave.

---

## Request Routing Table

### Transactions & Posting

| User asks about... | Read this resource |
|---|---|
| Post AP/AR invoice, journal entry, payment, credit memo | [transaction-processing.md](resources/transaction-processing.md) |
| Import CSV of transactions, bulk posting | [bulk-transaction-processing.md](resources/bulk-transaction-processing.md) |
| Bulk import of master data (accounts, customers, vendors) | [bulk-import.md](resources/bulk-import.md) |
| **Opening balances, initial balance, trial balance migration** | [bulk-import.md](resources/bulk-import.md#opening-balance-import) |
| Expense reports, mileage, per diem | [expense-management.md](resources/expense-management.md) |

### Sales & Purchase Orders

| User asks about... | Read this resource |
|---|---|
| Sales orders, quotes, order confirmation | [orders-management.md](resources/orders-management.md) |
| Purchase orders, vendor orders | [orders-management.md](resources/orders-management.md) |
| Invoice a sales order, bill a purchase order | [orders-management.md](resources/orders-management.md) |
| Match an invoice/bill to an order, PO match tolerances | [orders-management.md](resources/orders-management.md) |
| Goods receipts, receiving against a purchase order | [orders-management.md](resources/orders-management.md) |
| 3-way match, bills held from payment | [orders-management.md](resources/orders-management.md) |

### Master Data

| User asks about... | Read this resource |
|---|---|
| Customers, credit limits, pricing | [customer-management.md](resources/customer-management.md) |
| Vendors, payment terms, vendor tax reporting | [vendor-management.md](resources/vendor-management.md) |
| Employees, org structure, HR | [employee-management.md](resources/employee-management.md) |
| Products, services, items | [items-management.md](resources/items-management.md) |
| Legal entities, fiscal year | [entity-management.md](resources/entity-management.md) |

### Chart of Accounts & Structure

| User asks about... | Read this resource |
|---|---|
| Accounts CRUD (create/update/delete/import) | [accounts-management.md](resources/accounts-management.md) |
| Account taxonomy (account_type, account_subtype, cash_flow_class) | [accounts-management.md](resources/accounts-management.md) — see "Canonical Subtype Taxonomy" section |
| Cost centers, departments, dimensions | [dimensions-management.md](resources/dimensions-management.md) |
| Custom fields on customers, vendors, items, employees, projects, fixed assets, transactions (define, set, require, correct, filter) | [custom-fields.md](resources/custom-fields.md); the record's resource has a short "Custom Fields" section |
| Posting profiles, GL mapping rules | [posting-profiles-management.md](resources/posting-profiles-management.md) |
| Hardcoded GL number — why it's banned | [posting-profiles-management.md](resources/posting-profiles-management.md) — fail-loud rule |

### Banking & Payments

| User asks about... | Read this resource |
|---|---|
| Bank accounts, treasury | [bank-accounts-management.md](resources/bank-accounts-management.md) |
| Bank statements, imports | [bank-statements-management.md](resources/bank-statements-management.md) |
| Bank reconciliation, matching | [reconciliation-management.md](resources/reconciliation-management.md) |
| Reconciliation receipts, dated undo and recovery | [reconciliation-evidence.md](resources/reconciliation-evidence.md) |
| Payment batches, AP payments | [payment-batch-management.md](resources/payment-batch-management.md) |
| Payment terms, due dates | [payment-terms-management.md](resources/payment-terms-management.md) |
| Corporate cards, card programs | [corporate-cards-management.md](resources/corporate-cards-management.md) |

### Financial Operations

| User asks about... | Read this resource |
|---|---|
| Fiscal periods, period close | [financial-period-management.md](resources/financial-period-management.md) |
| Exchange rates, currency conversion | [multi-currency-management.md](resources/multi-currency-management.md) |
| Tax codes, VAT, sales tax | [tax-management.md](resources/tax-management.md) |
| Budgets, variance analysis | [budgets-management.md](resources/budgets-management.md) |
| Cost/revenue allocation | [allocation-workflows.md](resources/allocation-workflows.md) |
| Accruals, COGS, prepaid expenses | [cost-accruals-management.md](resources/cost-accruals-management.md) |
| Revenue recognition, deferred revenue, ASC 606 | [customer-contracts-management.md](resources/customer-contracts-management.md) |
| Vendor contracts, prepaid expense amortization | [vendor-contracts-management.md](resources/vendor-contracts-management.md) |
| Amortization runs, recognition runs history | [vendor-contracts-management.md](resources/vendor-contracts-management.md) |

### Assets, Projects & Billing

| User asks about... | Read this resource |
|---|---|
| Fixed assets, depreciation, disposal | [fixed-assets.md](resources/fixed-assets.md) |
| Projects, time tracking, WBS | [projects-management.md](resources/projects-management.md) |
| Subscriptions, recurring billing, contracts | [billing-management.md](resources/billing-management.md) |
| Customer subscriptions, deferred revenue, rev rec | [customer-contracts-management.md](resources/customer-contracts-management.md) |
| Vendor prepaid expenses, expense amortization | [vendor-contracts-management.md](resources/vendor-contracts-management.md) |
| Payroll runs, payslips | [payroll-management.md](resources/payroll-management.md) |

### Documents & Communications

| User asks about... | Read this resource |
|---|---|
| File uploads, attachments (PDF, images) | [document-attachments.md](resources/document-attachments.md) |
| Receipts, expense receipts, OCR | [receipts-management.md](resources/receipts-management.md) |
| Email notifications, templates | [communication-management.md](resources/communication-management.md) |

### Support

| User asks about... | Read this resource |
|---|---|
| File a bug report, report an issue, something is broken | [support.md](procedures/support.md) |
| Request a feature, suggest an improvement | [support.md](procedures/support.md) |
| Check support ticket status, my tickets | [support.md](procedures/support.md) |
| Add comment to ticket, update ticket, close ticket | [support.md](procedures/support.md) |

### Onboarding, Migration & Plugins

| User asks about... | Read this resource |
|---|---|
| Set up organization, onboard, initialize, first-time setup | [onboarding.md](procedures/onboarding.md) |
| Add second entity, add subsidiary (org already onboarded) | [entity-management.md](resources/entity-management.md) |
| Check onboarding status, onboarding progress | [onboarding.md](procedures/onboarding.md) |
| Migrate data, switch from another system, opening balances, go-live | [plugins-guide.md](resources/plugins-guide.md) |
| Available plugins, install plugins, plugin recommendations | [plugins-guide.md](resources/plugins-guide.md) |
| Year-end bookkeeping, annual report, VAT declaration, payroll | [plugins-guide.md](resources/plugins-guide.md) |

### System & Configuration

| User asks about... | Read this resource |
|---|---|
| Autonomous agents, agent monitoring | [agent-management.md](resources/agent-management.md) |
| Number series, auto-numbering | [numbering-management.md](resources/numbering-management.md) |
| User roles, permissions, API keys | [user-role-management.md](resources/user-role-management.md) |
| Financial reports, trial balance | [reporting.md](resources/reporting.md) |
| Available MCP tools reference | [tools-reference.md](resources/tools-reference.md) |

---

## File Upload Handling

**When a user uploads a PDF, image, or document, ALWAYS follow this flow:**

1. Analyze the document — extract vendor/customer, amounts, dates, line items
2. Check required dimensions — `query("dimension_type", filters={"is_required": true})`
3. Create the transaction — `submit("transaction", "post", {...})`
4. Create attachment metadata — `submit("attachment", "create", {...})`
5. Generate upload link — `submit("attachment", "generate_upload_url", {...})`
6. Attach the file — route by where the bytes are AND whether you can reach the server (never by size):
   - **File in your environment, and `curl` to the upload URL works** (Claude Code on a normal network) → `curl -sf -F "file=@<path>" "<upload_url>"`, which stores and confirms in one step.
   - **File in your environment but the upload URL is unreachable** — the usual case in a **Cowork** sandbox, which has no route to the ERP host — → give the user the upload link from step 5 and say what it is for. You cannot put a file into Drive to transfer it; the Drive route below only pulls a file that is already there.
   - **File already in the org's connected Google Drive folder** → skip the upload entirely. Find the connector with `query("connector", filters={"provider": "gdrive"})`, then `read_attachment(storage_url="connector://<connector_id>/<drive_file_id>", content_type="application/pdf")` (use the file's real MIME type). That stores the bytes and returns a `stored_url` you can pass on.

   Try `curl` **only** if you have already confirmed the host is reachable. A Cowork session that starts with `curl` fails, then has to recover.

**Full details**: [document-attachments.md](resources/document-attachments.md)

---

## Core Concepts

### Approval Lanes

Every `submit()` call is risk-assessed and routed to a lane. Which lane an operation gets, the thresholds, and the approval steps each lane runs are the organisation's workflow configuration; the table shows typical settings:

| Lane | Typical use | Typical approval |
|---|---|---|
| Green | Low-risk (simple creates, lookups) | Completes without an approval step unless the organisation has configured one |
| Yellow | Medium-risk (updates, moderate amounts) | One approval step, where the organisation has configured it |
| Red | High-risk (deletes, large transactions) | Multi-level approval, where the organisation has configured it |

Lanes are assigned by your organisation's workflow rules; the submit() result is authoritative. Check `success` first: `false` means the submission was refused or the operation did not complete, so report its `error` or `message`. Otherwise report the outcome from `status` and `lane`: `approved` or `completed` means the operation ran, `pending` means it is waiting for approval (a pending result may carry no `success` key). When the record has a status of its own (for example a draft invoice), `status` is the record's status and `workflow_status` carries the workflow's state.

Workflow decisions recheck the deciding user's current stored membership and
workflow entity/domain access. A pending assignment does not retain revoked
permissions. Assignment override requires current owner/admin membership and
never bypasses the other access or separation-of-duties checks. If authority has
changed, leave the task pending for an eligible reviewer; do not retry using
another user's identity. This behavior is implemented locally under AR-284 and
requires the corresponding server release.

### MSEO Pattern

Data uses Master + Entity Override architecture:
- **Master tables** store organization-wide defaults
- **Entity tables** store legal entity-specific overrides (sparse — only when different)
- **Effective views** (`v_*_effective`) resolve master + overrides automatically

**Rule**: Always read via `query` / `get_entity` — they use effective views automatically.

### Related Entity Updates

When adding/updating/deleting related data (bank accounts, dimensions, pricing), use the `_action` field:

```
submit(object_type="vendor", operation="update", data=JSON.stringify({
  "vendor_id": 123,
  "bank_accounts": [
    {"_action": "add", "legal_entity_id": 40, "payment_method": "ach", "account_holder_name": "Acme Inc", "bank_name": "Chase", "account_number": "123456"},
    {"_action": "update", "id": 5, "is_default": true},
    {"_action": "delete", "id": 3}
  ]
}))
```

### Legal Entities

Most operations require `legal_entity_id`. Find valid IDs with `query(entity_type="legal_entity")`. Each entity has its own GL, AR/AP sub-ledgers, and fiscal calendar.

---

## Other Skill Folders

| Folder | Contents | When to use |
|---|---|---|
| `procedures/` | Onboarding, support tickets | When the user starts onboarding or files a ticket |

---

## Rules

1. **Always read the resource guide first** — each guide has the exact tool calls and fields
2. **Never guess field names** — check the resource guide, then `get_submissions(action="schema", object_type, operation)`
3. **Never loop submit()** — use import for bulk data
4. **Always validate imports first** — set `validate_only: true` before executing
5. **Never forget file uploads** — if user uploaded a file, create the attachment and attach the file (upload it yourself when it's in your environment; otherwise give the upload link)
6. **Follow the connected tool schema** — use named arguments and JSON-encode `submit.data`.

---

**Version**: 2.1
**Status**: Production Ready
