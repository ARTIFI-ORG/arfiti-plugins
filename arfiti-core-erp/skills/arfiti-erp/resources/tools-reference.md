

## Card purchase policy

Use the backend purchase workspace and shared matching decision; do not implement a competing card matcher in conversation. Preserve provider rows and show net purchase spend. Reference conflicts and competing candidates require review. A paid/settled item can still lack documentation; attach missing source evidence to the existing bill. Evidence review, waiver and grouping use `card_purchase.manage` with current version, evidence fingerprint and reason. Never infer write-off authority from matching tolerance.

Receipt follow-up belongs to the purchase obligation, with one owner and deduplicated reminder stages. Automation and delivery are report-only until the entity rollout settings are explicitly enabled. Statement coverage and opening/movement/closing balance controls must pass independently of agent match counts. August deletion/replay requires its own reviewed manifest and explicit authorization through transaction.delete; implementation permission does not authorize it.

Legacy payment-pass descriptions below apply to non-card AP/AR behavior. Card rows use the shared purchase policy and cannot use nearest-date refund pairing, fuzzy amount identity or adjusting-journal workarounds.

# Tools Reference

Quick reference for all query, analytics, and write tools in the AI-Native ERP system.

---

## Tool Selection

| I want to... | Use |
|--------------|-----|
| Find records by name or text | `query(entity_type, query, filters)` |
| Get one record with full details | `get_entity(entity_type, id=X)` |
| List/filter records with pagination | `query(entity_type, filters, date_filters)` |
| Count matching records | `query(entity_type, filters, limit=1)` — returns `total_count` |
| Fetch reference data before create/update | parallel `query()` calls |
| Get totals, counts, trends (ad-hoc) | `query(entity_type, group_by, aggregates)` |
| Generate financial statements | `generate_report(report_type, params)` |
| Discover available reports | `generate_report("list", {"category": ...})` |
| Create / Update / Delete records | `submit(object_type, operation, data)` |
| View my pending approval tasks | `get_submissions(action='my_tasks', status="pending")` |
| Approve or reject a task | `manage_submissions(action='decide', task_id, decision, notes)` |
| Inspect a workflow or task | `get_submissions(action='task_details', task_id)` / `get_submissions(action='history', workflow_id)` |
| Discover workflow payload fields | `get_submissions(action='schema', object_type, operation)` |
| Convert currency amount | `convert_currency(amount, from_currency, to_currency, effective_date)` |
| Get effective item price | `get_effective_item_price(item_id, legal_entity_id, customer_id?, quantity?)` |
| Check bulk import progress | `get_imports(action="status", import_id)` |

---

## query() — read any entity (search + list + aggregate)

One tool for every tabular read. The mode is inferred from the arguments.

```javascript
query("vendor", query="Acme")                                   // search
query("bill", filters={"status": "pending"}, limit=50)          // list
query("transaction", query="Acme",                              // both
      date_filters={"transaction_date": {"from": "2026-01-01",
                                         "to": "2026-12-31"}})
query("bill", group_by=["vendor_name"],                         // aggregate
      aggregates={"amount": "sum", "id": "count"})
```

Unknown filter keys are a hard error listing the valid keys — never a silent
drop. Max limit 100 rows (list/search) or 500 groups (aggregate).

**Range filters**: any whitelisted numeric or date field also accepts an
operator object instead of a plain value — `{"gte": ..., "lte": ..., "gt": ...,
"lt": ...}`, any combination in one object. Dates work the same way as
numbers (pass an ISO date string).

```javascript
// Minimum amount — no more client-side post-filtering needed
query("asset_acquisition_line", filters={"legal_entity_id": 13,
                                         "available_amount": {"gte": 500}})

// Between: amount in a range, combined with a plain equality filter
query("transaction_line", filters={"legal_entity_id": 12,
                                   "debit": {"gte": 100, "lte": 900}})
```

`date_filters` (the `{"from": ..., "to": ...}` form above) keeps working
unchanged — it's sugar for the common "both ends of a date range" case.
Range operators in `filters` are the general mechanism and also work on
dates (`filters={"invoice_date": {"gt": "2026-01-01"}}`). An unknown
operator key (anything other than gte/lte/gt/lt), or an empty operator
object, is a hard error — same "never silently drop a filter" rule as
unknown filter keys.

> `query()` replaced the former `search`, `list_entities`,
> `aggregate_entities` and `batch_lookup` tools, which no longer exist.

---

---

## get_entity()

Get single entity by ID with related data.

```javascript
get_entity(entity_type, id?, ids?, global_id?, include_related?)
```

| Param | Default | Notes |
|-------|---------|-------|
| `id` | — | Numeric ID or UUID string |
| `ids` | — | Several records of this type in one call (max 100); not combined with `id`, `global_id` or `include_related=True` |
| `global_id` | — | Alternative: e.g., "VEND-000123" |
| `include_related` | `true` | Fetches addresses, bank accounts, lines, dimensions |

**Examples:**
```javascript
get_entity("vendor", id=123)
get_entity("customer", global_id="CUST-000456")
get_entity("transaction", id=5001, include_related=false)
```

---

---

## Counting Records

Use `query()` with `limit=1` to get a count without fetching full records. The response includes `total_count`.

```javascript
// Returns {"total_count": 47, "results": [...1 record...]}
query("vendor", filters={"is_active": true}, limit=1)
query("bill", filters={"status": "pending", "legal_entity_id": 10}, limit=1)
```

> **Note:** The standalone `count_entities()` tool has been removed. Use `query(limit=1)` instead.

---

---

---

## generate_report()

Formal financial and operational reports.

```javascript
generate_report(report_type, params?)
```

**Common params:** `legal_entity_id`, `as_of_date`, `start_date`, `end_date`, `entity_ids`

**Report categories:** financial, consolidated, tax, operational, banking, saas, budget, dimension, allocation

Use `generate_report("list")` to discover available reports and their required parameters.

**Examples:**
```javascript
generate_report("trial_balance", {"legal_entity_id": 9, "as_of_date": "2025-12-31"})
generate_report("income_statement", {"legal_entity_id": 9, "start_date": "2025-01-01", "end_date": "2025-12-31"})
generate_report("ap_aging", {"legal_entity_id": 9, "as_of_date": "2025-01-31"})
```

---

## generate_report("list")

Discover available reports.

```javascript
generate_report("list", {"category": ...})
```

**Categories:** financial, consolidated, tax, operational, banking, saas, budget, dimension, allocation

```javascript
generate_report("list")                    // All reports
generate_report("list", {"category": "financial"}) // Financial only
```

---

## submit() — Schema Discovery Required

Local R0 update (not yet deployed): a sole registered typed payload-validation
refusal can return `success: false`, `refused: true`, `reason_code`, and the human
`message`, with validation errors and field hints preserved. Mixed, unknown-code
and ordinary validation failures keep their legacy response. Do not infer that
an execution failed without effects from an error code alone.

If saving a durable task's refusal receipt cannot be confirmed, the response is
`posting_unknown` / `workflow_result_unavailable`, without `refused`. Keep the
same task identity and reconcile its receipt; do not invent a new identity to
retry posting. This transport rule adds no country or accountant policy and does
not require a Saga.


Local AR-273 recovery update (not deployed): ordinary submissions also retain
request identity before dispatch, fail closed if replay protection is unavailable,
and never release an uncertain outcome merely because an exception or timeout
occurred. Keep the same key for transport retries. Generic execution failures
remain `posting_unknown`; a failure sentence alone is not rollback proof.
A `Validation Failed` with `error_stage: pre_submission` is different: the
executor refused before dispatch and nothing ran. Fix the listed `errors` and
submit again. The refusal is kept without expiry, so an identical payload under
the same key replays it even after the cause is fixed elsewhere (a vendor
created, a period reopened): pass a new `idempotency_key` to be checked again.
A refusal with `reason_code: invalid_payload` and `effect_outcome: no_effect` is
the same kind: the workflow's own validation (a missing required field, an
unknown reference, a name another record already uses) refused before any
workflow existed. `message` is the sentence, `validation_errors` the list and
`guidance` the expected format and reference lists. Fix them and submit again;
the same key replays the refusal.
A replayed refusal carries `replay_hint` saying this. A task-bound submission's
identity comes from its task, so neither a new key nor a changed payload starts a
new request; its replay carries no hint.
Pending/unknown workflows recover only from actual saved execution results;
missing evidence requires reconciliation. Known result IDs remain available.

For a deliberate identical new intent, use an explicit MCP idempotency key or the
dashboard's existing attempt ID after resolving any previous uncertainty. Ordinary
Base agent submission has no fresh-intent parameter; use the supported MCP path.
Retained keys do not expire. Reusing a key for another object/operation or payload
is refused. This applies without Saga and adds no country/accountant policy.

Universal write gateway — routes to workflow system.

> **MANDATORY**: Always call `get_submissions(action='schema', object_type, operation)` BEFORE calling `submit()`. Each organization configures different required/optional fields per workflow. The schema tells you exactly what fields are needed. Submitting without checking the schema will likely fail with validation errors.

### Required 2-Step Pattern

```javascript
// Step 1: ALWAYS discover the schema first
schema = get_submissions(action='schema', object_type="vendor", operation="create")
// → Returns: required fields, optional fields, field types, validation rules, examples

// Step 2: Build payload using schema, then submit
submit("vendor", "create", '{"vendor_name": "Acme", "payment_term_code": "NET30", ...}')
```

### Tool Signature

```javascript
submit(object_type, operation, data, validate_only?, idempotency_key?)
```

| Param | Type | Description |
|-------|------|-------------|
| `object_type` | string | "vendor", "customer", "transaction", etc. |
| `operation` | string | "create", "update", "delete", "post", "reverse", etc. |
| `data` | JSON string | Operation payload — fields from `get_submissions(action='schema', ...)` |
| `validate_only` | bool (default: false) | If true, validates payload without creating workflow or executing. Returns validation result only. |
| `idempotency_key` | string (optional) | Replays the first result for the same key; use a new key to submit the same intent again on purpose |

### validate_only Mode

Use `validate_only=true` to check a payload before submitting. Runs the full validation pipeline (Pydantic, entity checks, reference data, business rules) but stops before creating any workflow instance or executing. No side effects.

```javascript
// Validate first — catches all errors in one call
result = submit("vendor", "create", '{"vendor_name": "Acme", ...}', validate_only=true)
// If valid:   {"success": true, "validate_only": true, "valid": true, "message": "Payload validation passed..."}
// If invalid: {"success": false, "errors": [...]}

// Then submit for real
submit("vendor", "create", '{"vendor_name": "Acme", ...}')
```

### Examples (always preceded by schema discovery)

```javascript
// Vendor creation
schema = get_submissions(action='schema', object_type="vendor", operation="create")     // Check required fields first
submit("vendor", "create", '{"vendor_name": "Acme", "payment_term_code": "NET30", "email": "ap@acme.com"}')

// Merge a duplicate vendor (consolidate two records into one)
schema = get_submissions(action='schema', object_type="vendor", operation="merge")      // Check required fields first
submit("vendor", "merge", '{"winning_vendor_id": 42, "losing_vendor_id": 87, "merge_reason": "duplicate"}')

// Transaction posting
schema = get_submissions(action='schema', object_type="transaction", operation="post")  // Check required fields first
submit("transaction", "post", '{"transaction_type_code": "AP_INVOICE", "legal_entity_id": 10, ...}')

// Legal entity creation — goes through onboarding, NOT submit()
// First entity in a new org:
manage_onboarding(action="start", country_code="US", accounting_standard="us_gaap_standard", tax_jurisdiction="us_sales_tax")
// Second+ entity in an onboarded org:
manage_onboarding(action="add_entity", entity_name="Acme US", entity_code="ACME-US", country_code="US", base_currency="USD")

// Legal entity update (safe fields only — entity_name, tax_id, country_code, address, is_active, metadata)
submit("legal_entity", "update", '{"entity_id": 13, "entity_name": "Acme US LLC"}')

// Configuration
schema = get_submissions(action='schema', object_type="number_series", operation="create")
submit("number_series", "create", '{"legal_entity_id": 9, "series_type": "invoice", "prefix": "INV-"}')
```

---

## Workflow Management Tools

Tools for workflow instances, approval tasks and import tracking. Tasks use a read/write pair: `get_submissions` reads and `manage_submissions` changes, both dispatched by `action`. An action sent to the other half is refused with `wrong_tool`, naming the right tool.

Read actions (`get_submissions`): `history`, `my_tasks`, `schema`, `task_details`

Write actions (`manage_submissions`): `comment`, `decide`, `edit_payload`, `prepare_asset_actions`

| Tool | Signature | Purpose |
|------|-----------|---------|
| `get_submissions(action='my_tasks', status?, object_type?)` | `status`: `"pending"` (default), `"in_progress"` or `"completed"` | List tasks assigned to current user |
| `get_submissions(action='task_details', task_id)` | `task_id`: int | Get full details of a task (payload, history, comments) |
| `manage_submissions(action='decide', task_id, decision, notes?, field_verifications?, expected_payload_hash?)` | `decision`: `"approve"`, `"reject"` or `"request_changes"` | Decide a workflow task. Approving a `payment_batch.transmit` or `fx_exchange.execute` is refused (`operation_not_available_via_mcp`) |
| `manage_submissions(action='edit_payload', workflow_id, field_changes, notes?, expected_payload_hash?)` | `field_changes`: JSON string of `{"field": new_value}` pairs | Modify payload fields before approval (see guardrails below). Refused on a pending `payment_batch.transmit` or `fx_exchange.execute` |
| `manage_submissions(action='comment', workflow_id, comment)` | Add a comment to a workflow | Attach notes for reviewers |
| `get_submissions(action='history', workflow_id)` | Get full audit trail | All events, decisions, comments |
| `get_submissions(action='schema', object_type, operation, payload?)` | Discover payload fields | Get required/optional fields for a workflow; `payload` is optional JSON routing context (`legal_entity_id`, `transaction_type_code`) |
| `get_imports(action="status", import_id)` | Check import progress (replaces `get_import_status(import_id)`, MCP registration removed) | Track bulk import operations |

> **Org-scoped:** `get_submissions(action='my_tasks')`, `get_submissions(action='task_details')`, and `manage_submissions(action='decide')` only see/act on tasks belonging to the session's **current** organization. A task from another org of a multi-org user is invisible (`my_tasks`) or returns "Task {id} not found" (`task_details`, `decide`) — select that org with `manage_organization(action="switch", organization_id=X)`, then verify `get_info` reports it before working its tasks. A pinned connection may need reconnection to the intended company.

> **`manage_submissions(action='edit_payload')` guardrails:**
> - Entity-scoped users cannot set `legal_entity_id` (or any entry of `legal_entity_ids`) outside their entity scope — fails with `entity_access_denied`.
> - Once a workflow has **any** recorded approval, edits to protected fields are rejected: `legal_entity_id`, `vendor_id`, `customer_id`, `employee_id`, `iban`, `account_number`, `bank_account_id`, `vendor_bank_account_id`, `payee`, `payee_name`, `lines`, plus lane-relevant amount fields. Reject the workflow and resubmit instead of trying to edit around this.
> - Object types with no registered payload validator return a clean "payload editing is not supported for this type" error — reject and resubmit.
> - Edited payloads are serialized the same way `submit()` serializes them: `model_dump_json(exclude_none=True)` — Decimal values persist as JSON strings, and explicit `null`s are stripped rather than written.

**Approval workflow pattern:**
```
1. get_submissions(action='my_tasks')                           -> list pending tasks (current org only)
2. get_submissions(action='task_details', task_id)                -> inspect payload and context
3. manage_submissions(action='edit_payload', workflow_id=..., field_changes='{"email": "new@x.com"}', notes="fixing typo") -> (optional) fix payload issues (subject to guardrails above)
4. manage_submissions(action='decide', task_id=..., decision="approve", notes="Looks good", expected_payload_hash=<payload_hash from task_details>) -> approve, reject or request changes
```

**Discover workflow fields before submit:**
```javascript
get_submissions(action='schema', object_type="vendor", operation="create")   // What fields does vendor.create need?
get_submissions(action='schema', object_type="vendor", operation="merge")    // What fields does vendor.merge need?
get_submissions(action='schema', object_type="transaction", operation="post") // What fields does transaction.post need?
```

---

## convert_currency()

Convert an amount from one currency to another using stored exchange rates.

```javascript
convert_currency(amount, from_currency, to_currency, effective_date)
```

| Param | Notes |
|-------|-------|
| `amount` | Amount to convert (>= 0) |
| `from_currency` | Source currency (3-letter ISO 4217, e.g., `"USD"`) |
| `to_currency` | Target currency (3-letter ISO 4217, e.g., `"EUR"`) |
| `effective_date` | Date for rate lookup (`"YYYY-MM-DD"`) |

**Example:**
```javascript
convert_currency(1000.00, "USD", "EUR", "2026-03-01")
// Returns: { original_amount: 1000.00, converted_amount: 920.50, rate: 0.9205, ... }
```

---

## get_effective_item_price()

Calculate the effective price for an item considering all pricing rules.

```javascript
get_effective_item_price(item_id, legal_entity_id, customer_id?, quantity?, pricing_date?, promo_code?, price_type?, billing_interval?)
```

**Priority**: Customer-specific > Promotion > Volume tier > Entity price > Master price.

| Param | Notes |
|-------|-------|
| `item_id` | Item to price |
| `legal_entity_id` | Legal entity context |
| `customer_id` | Optional: apply customer-specific pricing |
| `quantity` | Optional: for volume tier resolution (default: 1) |
| `pricing_date` | Optional: effective date (default: today) |
| `promo_code` | Optional: promotional discount code |

**Example:**
```javascript
get_effective_item_price(101, 13, customer_id=456, quantity=100)
// Returns: { unit_price: 85.00, applied_rule: "volume_tier", tier_name: "100+", ... }
```

---

## Domain Gateway Tools

Each area has a read tool `get_<area>` (read-only) and a write tool
`manage_<area>`. Both take `action` and the same other parameters; an action
sent to the other half is refused with `wrong_tool`, naming the right tool.
The action lists below are the tools' own action sets.

| I want to... | Use |
|--------------|-----|
| Bulk import data (accounts, vendors, etc.) | `manage_imports(action="accounts", ...)` |
| Onboard entity, run checklist, load demo | `manage_onboarding(action="start", ...)` |
| Org admin, roles, plugins | `get_organization(action="get_info")` |
| Register/sync banking connectors | `manage_connectors(action="register", ...)` |
| Agent memory, financial context | `get_agents(action="recall_memories", ...)` |
| Read or change a workflow configuration | `get_workflow(action="get", ...)` / `manage_workflow(action="draft", ...)` |

### get_workflow() / manage_workflow()

Workflow configuration (approval lanes, steps, related rules). Approving a task is `manage_submissions`, not this pair.

Read actions (`get_workflow`): `get`

Write actions (`manage_workflow`): `activate`, `bulk_submitter_review`, `create`, `deactivate`, `discard`, `draft`, `publish`, `update`

### get_imports() / manage_imports()

```javascript
manage_imports(action, records?, legal_entity_id?, on_duplicate?, validate_only?,
               dimension_type_name?, hierarchy_data?, confirmed?, template?)
```

Read actions (`get_imports`): `get_opening_balances`, `status`

Write actions (`manage_imports`): `accounts`, `customers`, `dimension_hierarchy`, `dimension_types`, `dimension_values`, `employees`, `fixed_assets`, `items`, `opening_balances`, `opening_balances_with_subledger`, `standard_coa`, `transactions`, `vendors`

> Bulk actions (`accounts`, `customers`, `vendors`, `employees`, `items`, `dimension_values`, `dimension_types`, `fixed_assets`, `transactions`) run through the same executor as `submit(operation='import')`: any org-configured `import_batch.review` approval workflow applies, batches over 50 records route async and return a pollable UUID `import_id` (poll with `get_imports(action="status", import_id)`), and entity scope is enforced before the import runs. A zero-error run is always `success: true` — including an idempotent re-run where every record is a duplicate skip (counts still come back as imported 0 / updated 0 / skipped N). With errors, partial success only happens when `stop_on_error=false` and at least one record imported.

```javascript
manage_imports("accounts", records=[...], legal_entity_id=9, validate_only=true)
manage_imports("standard_coa", legal_entity_id=9, template="us_gaap", confirmed=true)
manage_imports("opening_balances", balances=[{"account_number": "1000", "debit": 50000}, ...],
    legal_entity_id=9, fiscal_period_name="2025-01")
manage_imports("opening_balances_with_subledger", balances=[...], legal_entity_id=9,
    fiscal_period_name="2025-01", balancing_account_number="3300",
    open_ar_items=[{"customer_name": "Acme", "reference_number": "INV-001", "amount": 5000, "invoice_date": "2024-11-15", "due_date": "2024-12-15"}],
    open_ap_items=[{"vendor_name": "Supplier", "reference_number": "BILL-042", "amount": 3200, "invoice_date": "2024-12-01", "due_date": "2025-01-15"}],
    fixed_assets_detail=[{"name": "Server", "acquisition_date": "2023-06-15", "original_cost": 15000, "accumulated_depreciation": 5000, "useful_life_months": 60}])
get_imports("get_opening_balances", legal_entity_id=9, fiscal_period_name="2025-01")
```

### get_onboarding() / manage_onboarding()

Write actions require live owner/admin membership and unrestricted entity access in the current organization. Agent credentials cannot perform setup. Status/support/download actions keep their existing rules. See [onboarding procedure](../procedures/onboarding.md#authority-for-organization-setup).

```javascript
manage_onboarding(action, legal_entity_id?, task_key?, new_status?, support_type?, ...)
```

Read actions (`get_onboarding`): `check_status`, `get_checklist`, `get_support`, `verify_team_member`

Write actions (`manage_onboarding`): `add_entity`, `download_skill`, `get_summary`, `initialize_entity`, `load_demo_data`, `reset`, `run_wave`, `start`, `update_task`

`get_summary` and `download_skill` are write actions: when every task is done, `get_summary` finalizes onboarding, and the first `download_skill` generates the skill package. Their authority rules are unchanged.

```javascript
manage_onboarding(action="start", country_code="US", accounting_standard="us_gaap_standard",
    tax_jurisdiction="us_sales_tax")   // first entity: omit legal_entity_id
manage_onboarding(action="run_wave")   // repeat while next_tasks lists runnable work
get_onboarding(action="get_support", support_type="import_accounts")
```

A wave advances one legal entity's checklist. When more than one entity has open onboarding tasks, pass the entity: `manage_onboarding(action="run_wave", legal_entity_id=12)`; without it the call is refused and lists each entity with its open task count. Each answer's `next_tasks` carries `legal_entity_id`, and its message names the exact call to make next. `update_task` takes `legal_entity_id` the same way when two entities share the task.

### get_organization() / manage_organization()

```javascript
manage_organization(action, organization_id?, user_id?, role_name?, plugin_slug?, ...)
```

### Verify company scope after selection

`manage_organization(action="switch", organization_id=X)` records a selection
preference after checking target membership and active status. It does not retarget
the current request or guarantee that a pinned MCP connection changes company.
The response's `organization_id` names the selected company;
`request_organization_id` names the unchanged request company, and
`verify_context_before_operations=true` requires a follow-up
`get_organization(action="get_info")`. If that reports a different company,
connect to the intended company and verify again before reading or writing records.
Selection does not expand access or override an API key's organization scope.

Read actions (`get_organization`): `download_plugin`, `get_clients`, `get_info`, `get_plugin`, `get_rate_limit`, `list_orgs`, `list_plugins`, `list_roles`, `list_user_roles`

Write actions (`manage_organization`): `create`, `create_client`, `create_client_key`, `push_plugin`, `remove_role`, `repair_template_data`, `switch`, `update`

> **`action="update"` (rename) is current-org-only for non-wildcard callers**: it renames the session's **current** organization and requires `admin:write` — it cannot target another org by passing a different `organization_id`. To rename a different org, select it with `switch` and verify `get_info` reports it first; pinned connections can retain their scope. Wildcard (owner/admin) callers still must be members of the target org. An unknown/foreign org ID returns "Organization {id} not found".

> **`action="create"` requires `confirmed=true`**: the first call without it writes nothing and returns `{"requires_confirmation": true, "preview": {...}}` — show the preview to the user, then re-call with `confirmed=true` to actually create the org.

```javascript
get_organization("get_info")
manage_organization("switch", organization_id=5)
manage_organization("update", name="New Org Name")  // renames the CURRENT org
manage_organization("create", name="New Org", confirmed=true)  // confirmed=true required, or it just previews
get_organization("list_user_roles", user_id=42)
```

### get_connectors() / manage_connectors()

```javascript
manage_connectors(action, connector_id?, legal_entity_id?, bank_account_id?, ...)
```

Read actions (`get_connectors`): `fx_quote`, `get`

Write actions (`manage_connectors`): `activate`, `process_bank_lines`, `register`, `sync_accounting_data`, `sync_bank_statements`, `sync_card_transactions`, `sync_cards`, `sync_exchange_rates`

> **`action="register"` requires write permission** AND a `legal_entity_id` within the caller's entity scope. Read-only callers or callers scoped to a different entity are rejected before any credential is stored.

```javascript
manage_connectors("register", legal_entity_id=9, connector_code="revolut_main",
    provider="revolut", connector_type="banking", auth_type="oauth2",
    credentials={"client_id": "...", "private_key_pem": "...", "certificate_pem": "...", "issuer_domain": "..."})
// Revolut is normally registered via the Admin Dashboard wizard (certificate + OAuth consent)
manage_connectors("sync_bank_statements", connector_id="uuid",
    bank_account_id=10, entity_id=9, from_date="2026-01-01", to_date="2026-01-31")
manage_connectors("sync_exchange_rates", mode="latest")
```

### get_agents() / manage_agents()

```javascript
manage_agents(action, agent_type?, memory_key?, memory_value?, memory_type?,
              legal_entity_id?, sections?, confirmed?, ...)
```

Read actions (`get_agents`): `get_bill_context`, `get_event_stats`, `get_pipeline`, `get_running_summary`, `list_blocks`, `list_callout_endpoints`, `list_capabilities`, `list_deliverables`, `list_recent_runs`, `list_releases`, `list_resolution_contracts`, `list_revisions`, `list_templates`, `load_financial_context`, `preview_agent_draft`, `preview_upgrade`, `recall_memories`

Write actions (`manage_agents`): `activate_revision`, `create_agent`, `create_pipeline`, `deactivate_callout_endpoint`, `delete_memory`, `dry_run_pipeline`, `regenerate_keys`, `register_callout_endpoint`, `save_agent_revision`, `save_upgrade`, `seed_definitions`, `store_memory`, `update_pipeline_patch`

> **`store_memory` / `delete_memory` require write permission.** Read-only callers get `{"error": "write permission required to modify agent memory"}` — `recall_memories` and the other read actions are unaffected. Agent-initiated calls are unaffected (agents run with their own permissioned context).

> **Memory is per entity** (`agent_type` + `legal_entity_id` + `memory_key`; NULL entity = org-wide). `recall_memories` without `legal_entity_id` returns only org-wide rows; with it, the entity's rows plus org-wide rows. `store_memory` / `delete_memory` from an entity-scoped context (every agent, any entity-limited user) must pass an accessible `legal_entity_id` — an org-wide write is refused with `"An accessible entity is required for this memory write"`. There is no `memory_id`: a delete is addressed by `agent_type` + `memory_key` + `legal_entity_id`, and omitting the entity deletes only an org-wide row.

```javascript
get_agents("recall_memories", agent_type="bank_transaction_processor",
    memory_type="learned_mapping", memory_key_pattern="vendor_mapping:%", legal_entity_id=9)
manage_agents("delete_memory", agent_type="bank_transaction_processor",
    memory_key="vendor_mapping:AMZN*MKTPL", legal_entity_id=9)
get_agents("load_financial_context", legal_entity_id=9, sections="trial_balance,ar_aging")
get_agents("get_bill_context", legal_entity_id=9)
```

---

## Common Patterns

### Preflight -> Schema Discovery -> Gather References -> Create

```
1. get_submissions(action='schema', object_type, operation) -> discover required/optional fields
2. query() calls in parallel -> gather reference data needed by schema (payment terms, tax codes, accounts, etc.)
   — or use get_entity() for specific record lookups
3. (optional) submit(validate_only=true) -> validate payload without creating workflow
4. submit() -> create with valid reference IDs and correct fields
```

**Example: Creating a vendor**
```javascript
// 1. Discover what fields are needed
schema = get_submissions(action='schema', object_type="vendor", operation="create")
// → tells you: payment_term_code required, tax_code optional, dimensions optional...

// 2. Gather reference data for the required fields (issue these query() calls in parallel)
payment_terms = query("payment_term")
tax_codes     = query("tax_code", filters={"legal_entity_id": 10})
dim_types     = query("dimension_type")  // NOTE: "is_required" filter is deprecated; read required dims from workflow_definitions.related_entity_rules instead

// 3. (Optional) Validate payload first — catches all errors without side effects
submit("vendor", "create", '{"vendor_name": "Acme", "payment_term_code": "NET30", ...}', validate_only=true)

// 4. Submit for real
submit("vendor", "create", '{"vendor_name": "Acme", "payment_term_code": "NET30", ...}')
```

### Analytics -> Drill Down -> Details

```
1. query() -> summary (totals by vendor)
2. query() -> filter records for one vendor
3. get_entity() -> view single record with GL lines
```

### Search -> Inspect -> Schema -> Update

```
1. query() -> find by name/text
2. get_entity() -> full details + related data
3. get_submissions(action='schema', object_type, operation="update") -> discover update fields
4. query() -> gather any new reference data if needed (parallel calls for multiple entity types)
5. submit() -> update with changes
```

---

## Key Rules

1. **ALWAYS call `get_submissions(action='schema', ...)` before `submit()`** — each organization has different required/optional fields. Never guess the payload structure.
2. **Filter by `legal_entity_id`** for MSEO entities (vendors, customers, accounts, tax codes, items)
3. **Use `date_filters`** for date queries — `query()` does text matching, not date comparison
4. **`include_lines` is a top-level param** — not inside `filters`
5. **Check `warnings` in responses** — they explain ignored filters or suggest better approaches
6. **Gather reference data with parallel `query()` calls before writes** — issue the lookups together, not sequentially
7. **Use `query()` for quick analytics**, `generate_report()` for formal statements


## Workflow schema and read discovery

`get_submissions(action="schema", object_type=..., operation=...)` preserves Literal
enums and nested field constraints in validator-backed definitions, with the full
`input_schema`. Follow enum values such as card purchase actions rather than
assuming an arbitrary string is valid. The running server's schema remains the
source of truth for organization-specific requirements.

`get_entity` is a public MCP tool and should remain present after reconnecting.
Use transaction/attachment ID filters for exact evidence lookup. Amortization
schedules, schedule lines and live runs are registered entity types; read them
before creating or retrying recognition rather than assuming no existing schedule.

## Human task routing and admin review

Role routing uses active human membership and active, unexpired role grants from the current organization. A matching requested role wins, then an organization admin/owner; a system principal, inactive user, or arbitrary first member is never the fallback. If no eligible approver exists, configure one and resubmit. Explicit user/employee/submitter assignments must also resolve to an active human member. Unresolved routing does not silently assign an approval to its submitter; explicit submitter confirmation steps remain supported.

MCP get_submissions(action='my_tasks') and Admin My Tasks show personally assigned workflow tasks; active organization owners/admins can also see and decide other tasks in that organization under the existing Admin review policy. Membership is checked again for MCP decisions. Object/entity permission filters and cross-organization guards remain applicable; this does not add a second-person approval policy. The actual deciding actor is recorded in workflow history.

Previously misassigned pending tasks are not silently reassigned. An authorized owner/admin can inspect and decide the original task through the normal audited workflow. Existing duplicate-submission protection remains in place. Admin labels generic chat-origin submissions **Chat / MCP** because that source field does not identify a specific AI client. The recorded ui channel displays **Admin**; missing/unknown human channels display **User**.
\n
Business refusal after approval (executor success=false) is treated as execution failure, like an exception. The human decision remains recorded; the workflow is persisted as rejected with execution_failed audit evidence because the current status schema has no failed state. MCP returns workflow_status=execution_failed and execution_error; success=true means the decision was recorded, not that the underlying business operation succeeded. Inspect workflow_status before reporting completion.


### Financial context response limits (report correctness release)

`load_financial_context` returns section summaries under one repeatable-read snapshot.
Statements include `accounts` (at most 200), full `totals`, `account_count`,
`truncated`, `currency`, `dates`, `coverage` and `quality`; familiar total aliases
remain. Recent activity is at most 500 transactions, with `line_count` and
`truncated`. Budget context contains at most 10 separate version summaries, never
additive across versions. Invalid section names return an `error` response.
Unavailable monetary evidence is `null`, never zero. Read the section's gaps before
using a total, and request a paged report for all underlying rows. These are source
template changes; stored tenant skills require the normal approved regeneration.

### Workflow requests for changes

A `manage_submissions(action="decide", decision="request_changes")` decision never approves execution. Once the parallel review step finishes, the workflow is rejected/returned; expense reports become resubmittable. The decision and notes stay in the audit trail. Correct the returned record and submit again; a later approval cannot override a request for changes.

Reviewers cannot edit pending access-management grants (`role`, `user_role`, `api_key`, `organization_user`, `agent_api_key`); ask the submitter to correct them. Self-approval is available only when there is no other eligible approver.

An agent's `role.create`, `user_role.assign`, `organization_user.invite`, `organization_user.update`, `organization_user.remove`, `organization_user.revoke_invite` or `policy.save` waits for a person and cannot be approved by an agent, nor can an agent approve a forced `fiscal_period.close`: `manage_submissions(action="decide", decision="approve")` from an agent returns `permission_denied`. A person's own submission of these runs directly when they may decide it.

### Governed policy (`policy.save`)

`submit("policy", "save", {"namespace": "period_close.policy", "section": "check_severity", "legal_entity_id": 12, "content": {"overrides": {"group.code": "advisory"}}, "reason": "..."})` saves a new version for an entity (omit `legal_entity_id` for the organisation). `"action": "retire"` without `content` ends that level's version. Every version is kept. In force: entity, then organisation, then the product default. An owner, admin or holder of `accounting:close` saves directly; `accounting:write` holders and agents propose and someone with `accounting:close` approves. `fiscal_period.close` reads `period_close.policy.check_severity`, and `payroll.payroll_run_paid` reads `period_close.policy.payroll_settlement` (carry net pay paid after the month end, from a month); integrity checks cannot be overridden (see financial-period-management.md, "Closing a period"). `fiscal_period.close` with `force: true` needs `force_reason` and a person holding `accounting:close`. Human workflow downstream payloads are sanitized recursively; setting provenance fields does not grant agent authority.

Stored attachment reads authorize the actual owning type and entity. Employee personnel files require HR/payroll read, and a colliding ledger ID grants no access. Unknown/retired CONTRACT spaces are refused. Unscoped raw email/import/skill storage is an organization-wide admin operation. Existing expense/card ownership scope still applies to receipts.

Approval routing and self-approval alternatives apply live membership and trusted
role entity scopes. An administrator outside the workflow's entity is not an
eligible alternative; organization-wide work requires unrestricted scope.

### Workflow review and onboarding authority

`request_changes` never executes a workflow; its completion notice says Changes
requested. Correct and resubmit the record. Explicit submitter confirmation steps
remain confirmable by the submitter. Agent submissions with authenticated submit
provenance may be approved by their human creator. Human self-approval on an
approval step requires there to be no other eligible approver.

`submit("legal_entity", "rerun_onboarding_task", ...)` requires live owner/admin
membership and access to the entity, including when invoked through MCP.


#### Client-organization creation readiness (hardening branch, unreleased)

For `manage_organization(action="create_client")`, success confirms organization
creation, not full accounting setup. Check `schema_created`, `config_copied`,
`t1_created`, `posting_profiles_copied` and `posting_profile_copy_issue`. Invalid profile
account mappings refuse copying; unexpected copy/setup failures expose a generic
issue, not raw SQL. Profile failure rolls back T1 setup but leaves earlier organization
stages intact. Do not automatically repeat creation or change account flags to recover.
A general resume operation for a partially created MCP client remains unfinished.


### Bank-line rollback refusals (local AR-273 update)

For direct/immediate `bank_statement_line.match`, `unmatch` and `exclude`, a
confirmed refusal proves only the exact attempted bank mutation rolled back.
Its original reason and same-intent receipt are retained; earlier postings and
workflow/audit records may remain. Missing acknowledgements or unconfirmed receipt
storage stay `posting_unknown`. Do not retry under a new identity while uncertain.
Delayed approvals also retain verified bank proof with the rejected workflow.
Same-intent Base/MCP/dashboard recovery checks that exact workflow, organization,
operation and saved payload without executing again. Failed receipt commits,
nested approval transactions and missing/contradictory evidence remain uncertain;
ordinary failure text does not prove rollback. This changes no matching/exclusion
policy and requires no Saga.

Intermediate-review integrity: a non-final review assigns the next pending task;
it does not automatically execute the bank operation. If pending steps exist but
cannot be resolved through the saved workflow definition and organization, task
advancement is refused before execution. The current review decision rolls back;
resolve the workflow configuration through an authorized process before retrying.
This error is not a bank rollback receipt. Initial workflows with no pending steps
can still execute automatically; final-review bank failures use the saved proof
and recovery described above.


### Card-line rollback receipts (AR-273, local; not deployed)

`card_statement_line.match`, `unmatch` and `exclude` can return a confirmed refusal
only after the operation's owned database transaction has acknowledged rollback.
The proof binds organization, entity, card source, operation and validated payload,
and includes attempted routed-parent statement updates. Earlier postings and
pre-existing links remain outside that proof; it is not permission to reverse them.

Direct/immediate submissions retain the original request identity and refusal.
Final approvals store the verified receipt with their failure outcome; same-intent
retries recover it without executing again. Missing or contradictory evidence,
failed commit/rollback acknowledgements, nested transaction uncertainty and
unconfirmed receipt storage remain unknown. Keep the original identity and known
source IDs for reconciliation. Bank-line and card-line proof cannot substitute
for each other. An arbitrary error or `refused` flag is not proof.

This covers link/match/unmatch/exclude operations, not card expense posting or
`post_as_bill`. It changes no matching, exclusion, close or accountant policy,
and requires no built-in Saga.


### Unavailable card-to-bill operation

`card_transaction.post_as_bill` is unavailable. Its retained executor refuses
with `operation_unavailable` before opening a database connection or attempting
a bill, journal, numbering or card-status write. Existing discovery and saved
workflow identities remain readable; they do not make this capability available.
This restriction does not change supported card matching, classification or
ordinary bill operations.

Direct/internal/agent submission returns the definite reason only after the
exact request's refusal receipt is saved. A delayed approval records the same
scoped refusal on its failed workflow. If receipt storage or acknowledgement is
uncertain, the result stays `posting_unknown`; retain the original request
identity and recover its saved result. Do not submit a new identity to retry the
unavailable operation. This proves no posting by this attempted capability, not
that the card has no previous posting or that another operation is safe.


### Pending review request versus pending submission (local, not deployed)

`agent_request.create` returns the request's `status: pending` while its successful
creation receipt carries `operation_status: completed`,
`resource_type: agent_request`, and `request_id`. Reuse that request; do not create
a duplicate just because it awaits an answer. This is not evidence that review
or financial work is complete. These are server result fields, not caller inputs.
A pending status/identifier without the complete successful receipt does not
resolve a `posting_unknown` outcome.


### Pre-dispatch refusal and retry identity

Local correction (2026-10-24, not deployed): MCP wrong-tool/deprecated-type,
empty-payload, entity-scope and missing-definition gates can retain their exact
refusal when the server proves the check preceded operation execution and no
onboarding reconciliation effect was attempted. The dashboard missing-definition
gate has the same pre-execution boundary. Retry the same request identity to read
the saved refusal; do not interpret a later executor exception as rollback proof.
If storing the result cannot be confirmed, retain the identity and reconcile the
unknown outcome. The private validation receipt is not a caller-supplied field.


### Explicit dates for inbound payment applications

Normalized connector payment records may supply `application_effective_date`
for new applications and `undo_effective_date` for removed applications. The
sync adapter forwards these values unchanged to the existing reconciliation
operations, which validate the date and current period controls. It does not
derive either date from the payment booking date, provider timestamps, or today.
Missing or malformed dates refuse the affected application; an already imported
payment remains imported. Inspect application failure counts and connector event
details rather than treating payment import as successful application.

Provider mapping must explicitly supply the appropriate date under the client's
configured policy. The existing Odoo payment mapper does not yet supply these
fields; this forwarding contract does not certify automatic Odoo application
or removal as ready without that mapping. Existing unresolved counterpart
mappings continue to report unresolved/conflict outcomes.
