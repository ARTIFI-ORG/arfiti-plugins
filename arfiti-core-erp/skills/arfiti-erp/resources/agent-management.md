

## Runtime contracts and responses

Check execution status separately from verified task outcome. Saved configuration
or a successful diagnosis does not establish financial recovery. Executable human
replies require an installed owner/action adapter; unsupported tasks retain comments
and history but require contract repair before execution. Master Data party-review
replies bind the response attempt and human actor, use ordinary update workflows,
and close only after current effects verify. Use memory type `decision` with
`merchant_identity:*` keys for human merchant corrections.

Permissions are checked across native/model hosts, approval continuations and
replay against current and pinned workflow grants and entity scope. System-agent
transaction grants cover AP, AR, accounting and payroll domains unless narrowed by
`financial_permissions`; this never gives a human reply more authority than its
actor. Never request wildcard/admin grants to resolve a source permission failure.
These October changes require release activation; inspect the active revision.


## Card purchase policy

Use the backend purchase workspace and shared matching decision; do not implement a competing card matcher in conversation. Preserve provider rows and show net purchase spend. Reference conflicts and competing candidates require review. A paid/settled item can still lack documentation; attach missing source evidence to the existing bill. Evidence review, waiver and grouping use `card_purchase.manage` with current version, evidence fingerprint and reason. Never infer write-off authority from matching tolerance.

Receipt follow-up belongs to the purchase obligation, with one owner and deduplicated reminder stages. Automation and delivery are report-only until the entity rollout settings are explicitly enabled. Statement coverage and opening/movement/closing balance controls must pass independently of agent match counts. August deletion/replay requires its own reviewed manifest and explicit authorization through transaction.delete; implementation permission does not authorize it.

Legacy payment-pass descriptions below apply to non-card AP/AR behavior. Card rows use the shared purchase policy and cannot use nearest-date refund pairing, fuzzy amount identity or adjusting-journal workarounds.

# Agent Management Guide

This guide covers the autonomous agent system in AI-Native ERP.

---

## Overview

Agents are autonomous processors that handle specific tasks like bill processing, transaction reconciliation, and master data management. They run independently, communicate with each other via requests, and are triggered by events or schedules.

**What you can do:**
- View and configure agent definitions
- Monitor running agent instances
- Manage the event queue (trigger, retry, ignore)
- Handle inter-agent requests
- Manage agent API keys and scheduled jobs
- Orchestrate multi-step processes with sagas
- Configure downstream event routing rules
- Use agent memory for persistent lookups

**Agent definitions** are stored as files in `agent-definitions/` and loaded at startup. Configuration changes (enable/disable, thresholds) are managed via tools.

**Gateway Tools**: Most agent management operations use three gateway tools:
- `submit(object_type, operation, data)` - for all write operations
- `get_entity(entity_type, id=X)` - for getting single entities
- `query(entity_type, filters={...})` - for listing/searching entities

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

---

## Execution modes and cost interpretation

Pipeline availability and effective organization settings are different. Bill
requires its single pipeline host. Bills Collector and Reconciliation use their sole effective pipeline, including org patches;
older stored modes are normalized by template sync and cannot restore the retired host.
Confirm the deployed version before describing a production agent as migrated; do not
change mode as a troubleshooting shortcut. A resolution task contract can also be adopted by
an LLM agent without converting it into a pipeline.

Session details distinguish observed model-call receipts from historical legacy
estimates. SDK-reported costs and rate-based estimates are labeled separately.
Interrupted or unpriced attempts make the subtotal incomplete; missing usage is
not zero. Verified remote extraction is recorded against the originating run.
Task details have an expandable Model usage panel that combines attributed calls
across replies, delegated child requests and resumed task sagas. Earlier intake,
unlinked work and uninstrumented calls can remain outside it. Related creator-batch
and verified pre-worker email intake are displayed separately and remain unallocated;
never add a shared batch to each resulting task. Pre-call input estimates and
reported input/output counts are separate; unavailable counts are not zero. Missing historical
usage and truncated results are explicit. Neither subtotal is a certified full
business-task cost or a customer credit charge.
Do not infer a new spending allowance from usage receipts: existing budget and
workflow authority remain separate controls.

## Built-in Agents

| Agent Type | Description | Mode | Key Workflows |
|------------|-------------|------|---------------|
| `bill_processor` | Processes vendor bills and owned review replies through the sole saga runtime. | pipeline | `transaction.post`, `vendor.create`, `fixed_asset.acquire_from_bill` |
| `reconciliation_agent` | Matches AP/AR and card purchases; unresolved purchases can enter optional, opt-in durable evidence investigation. | pipeline | Existing reconciliation/settlement workflows and validators |
| `master_data_agent` | Centralized vendor/customer creation. Handles requests from other agents, searches for duplicates. | llm | `vendor.create`, `customer.create`, `vendor.update`, `customer.update` |
| `bank_transaction_processor` | Processes bank and corporate-card feeds | pipeline | Posting, source match/exclusion and review workflows |
| `stripe_transaction_processor` | Processes Stripe payment transactions | code | varies |
| `bills_collector_agent` | Collects missing vendor bills | pipeline | varies |
| `payment_proposal_agent` | Proposes payment batches for approval | pipeline | varies |
| `asset_creator` | Creates fixed asset records from transactions | llm | `fixed_asset.create` |
| `agent_architect` | Manages and optimizes agent configurations | llm | varies |
| `configuration_agent` | Handles system configuration tasks | llm | varies |

---

## Agent Definitions

Configuring the agent platform is for an owner or admin of the organization,
or an agent whose own definition's `allowed_workflows` names the operation
(`agent_architect` names `agent_definition.create`, `update` and `enable`).
That covers agent definitions, downstream rules, scheduled jobs, agent API
keys, `agent_event` create and retry, `agent_instance` start, and the
`manage_agents` actions that change an agent (`seed_definitions`,
`regenerate_keys`, `create_agent`, `preview_agent_draft`,
`save_agent_revision`, `activate_revision`, `preview_upgrade`, `save_upgrade`,
`update_pipeline_patch`, `create_pipeline`, `register_callout_endpoint`,
`deactivate_callout_endpoint`). A member is refused with `permission_denied`
("Only an owner or admin can change scheduled jobs."); ask an owner or admin
of the organization to make the change. Reads, answering agent requests and
cancelling a run stay open to members. Rows marked "(owner or admin)" below
follow this rule.

Manage agent configurations using these tools:

| Tool | Purpose |
|------|---------|
| `query("agent_definition")` | List all agent definitions with status |
| `get_entity("agent_definition", ...)` | Get full config for a specific agent |
| `submit("agent_definition", "create", {...})` | Create a new agent definition (owner or admin) |
| `submit("agent_definition", "update", {...})` | Update agent configuration (owner or admin) |
| `submit("agent_definition", "enable", {...})` | Enable or disable an agent (owner or admin) |
| `manage_agents(action="regenerate_keys")` | Regenerate MCP API keys (owner or admin) for agents missing one, or (`force: true`, optionally `agent_type`) replace them. The new key keeps the previous runtime key's owner, whose roles are the agent's authority, and the earlier runtime key is revoked (a run still using it fails and is retried). An agent whose owner has left goes to the calling person (an agent caller cannot take it over); owner changes are listed under `owner_changed`, agents that got no key under `skipped`, and agents whose missing key another caller filled meanwhile under `already_filled` |
| `get_agents(action="list_templates")` | List available agent templates |
| `manage_agents(action="seed_definitions")` | Seed agents from templates (owner or admin) |

### Agent Config Structure

Each agent definition includes:

```
agent_type          # Unique identifier (e.g., "bill_processor")
name                # Display name
description         # What the agent does
is_enabled          # Whether the agent is active
execution_mode      # "llm", "code", "hybrid", or "pipeline"; distinct from model_tier
model_tier          # LLM tier: "fast" (Haiku)
config              # Behavior settings (thresholds, flags)
max_concurrent_runs # Concurrency limit
timeout_minutes     # Max runtime per run
allowed_workflows   # Workflows this agent can execute
allowed_tools       # MCP tools this agent can use
trigger_events      # Events that start this agent
```

### Examples

```javascript
// Step 1: Discover required fields before any submit call
schema = get_submissions(action='schema', object_type="agent_definition", operation="update")

// Step 2: Use discovered fields in submit calls
// Tip: Use validate_only=true to check payload before submitting
```
```
# List all agents
query("agent_definition")

# Get bill processor config
get_entity("agent_definition", global_id="bill_processor")

# Disable an agent
submit("agent_definition", "enable", {definition_id: 1, is_enabled: false})

# Read the definition first; config updates replace the full object.
# Preserve every existing key, including resolution and rollout flags.
# Update bill processor confidence threshold
submit("agent_definition", "update", {
    definition_id: 1,
    config: {...current_definition.config, "confidence_threshold": 0.90}
})
```

---

## Pipeline Agents & Blocks

Agents run in one of four execution modes — knowing the mode tells you which
update surface actually changes behavior:

| Mode | Runtime | How to change its behavior |
|------|---------|---------------------------|
| `llm` | System prompt drives a Claude session | `submit("agent_definition", "update", {definition_id, system_prompt/config/...})` |
| `pipeline` | Deterministic staged blocks (no LLM unless a block uses one) | `manage_agents(action="update_pipeline_patch", ...)` |
| `code` | Python handler deployed with the server | Code deploy only — the definition's `system_prompt` row is **documentation, not runtime**; editing it changes nothing |
| `hybrid` | Code + LLM steps | Code deploy for the code part; definition `config` for tunables |

The stored mode may be `pipeline`, but `agent_definition.update` accepts only
`llm`, `code` and `hybrid`. Use dedicated pipeline management to activate a
pipeline. Bill requires `pipeline` and has no hybrid compatibility host. The
eleven migrated operational types use their effective pipeline even when old
stored modes differ. Existing custom agents keep their selected execution mode.

### Discovering blocks (ALWAYS do this before creating or patching a pipeline)

```python
# The block catalog: every block's params schema, what it reads/writes,
# and whether it is effectful (posts documents / sends email / mutates state)
get_agents(action="list_blocks")

# The canonical pipeline for an agent type + this org's patch + the effective stages
get_agents(action="get_pipeline", agent_type="bill_processor")
```

Blocks are the unit of pipeline behavior. `list_blocks` is the source of truth
for what exists and what each block's `params` accept — never guess block names
or params; the patch validator rejects unknown ones, but reading the catalog
first is how you design a correct change.

### Creating and revising agents

Admin and Cowork use the shared authoring service. Start with LLM or Pipeline.
Discover `list_capabilities`, `list_blocks`, `list_resolution_contracts`; custom
pipelines can use only catalog blocks marked standalone-compatible. Provide full
`pipeline_definition` JSON and deliberate tool/workflow/skill/entity grants. Empty
custom grants mean none. Python handlers/blocks still require deployment.

Preview `create_agent(confirmed=False)` before saving the reviewed configuration.
Creation atomically provisions credentials and an immutable revision, disabled.
`preview_agent_draft` with full fields and `sample_payload` is isolated: no DB/model
or effect adapters, unsupported stages refused. It is distinct from legacy
`dry_run_pipeline`; domain/model execution needs a sandbox and authorized spend.

Use `list_revisions`, `save_agent_revision` with `expected_revision_id`, and
`activate_revision` with `expected_active_revision_id`. A saved draft is not live.
Rollback means activating a valid earlier revision, never a raw mode-field update.
Use full drafts after version capture; `update_pipeline_patch` cannot mutate a
revision-owned definition. `create_pipeline` remains a validated compatibility adapter.

Custom `human_deliverable.v1` supports human input followed by a schema-validated
non-financial artifact, in both modes. Read tools only, no workflow grants. Discover
its contract, bind it in config, use Provide input or Decline; never complete its task
via generic update/resolve. Author-assigned confirmation requests appear in My Tasks.
`list_deliverables` reads the actual persisted evidence. A single enclosing JSON
code fence is accepted, but schema validation still governs completion. Temporary
concurrency deferral retains the submitted response for automatic retry; do not
submit another answer solely because execution is waiting for capacity.
No prompt or owner alias can adopt Bill/Bank financial resolution semantics.

`list_releases`, `preview_upgrade` and `save_upgrade` expose the same reviewed
three-way upgrade as Admin. Preserve customer edits, resolve conflicts explicitly,
then activate separately. Only operators publish immutable Arfiti releases. Template
sync preserves version-owned configuration; old task/run revisions remain pinned and
current revocations still apply. Model budgets use `config.model_call_policy`.


### Updating agents

```python
# LLM agents — prompt, config, tools, triggers, model tier, concurrency:
get_submissions(action="schema", object_type="agent_definition", operation="update")  # field contract
submit("agent_definition", "update", {"definition_id": N, "system_prompt": "..."})
submit("agent_definition", "enable", {"definition_id": N, "is_enabled": false})

# Pipeline agents — patch this org's stages (canonical pipeline stays shared):
manage_agents(action="update_pipeline_patch", agent_type="...",
              patch='{"ops": [...]}', confirmed=False)   # ALWAYS preview first
# ... confirmed=True to save

# Then PROVE the pipeline still works, with a realistic trigger payload —
# the bare dry-run sentinel yields zero documents for intake-style agents:
manage_agents(action="dry_run_pipeline", agent_type="...",
              sample_payload='{"event_type": "...", ...}')   # effects stubbed
```

### Schedules

```python
submit("scheduled_job", "create", {...})                       # cron for an agent
submit("scheduled_job", "update", {"job_id": N, "cron_expression": "0 9 * * *"})
submit("scheduled_job", "enable", {"job_id": N, "is_enabled": false})
submit("scheduled_job", "delete", {"job_id": N})
```

### Monitoring

```python
get_agents(action="get_running_summary")
get_agents(action="list_recent_runs", agent_type="...")
```

Terminally failed runs email the org's owner/admins automatically (out-of-band
— the alert does not depend on the agent itself running; at most one email per
agent per 6 hours). Credit exhaustion sends the critical billing alert.

## Agent Instances

Monitor and manage running agent sessions:

| Tool | Purpose |
|------|---------|
| `query("agent_instance", filters={...})` | List running/completed sessions |
| `get_entity("agent_instance", id="X")` | Get instance details with logs |
| `submit("agent_instance", "cancel", {...})` | Cancel a running instance (owner, admin or the person who started it) |
| `get_agents(action="get_running_summary")` | Summary of all active agents |
| `submit("agent_instance", "start", {...})` | Manually trigger an agent run (owner or admin) |

### Examples

```
# View all running agents
get_agents(action="get_running_summary")

# List recent bill processor runs
query("agent_instance", filters={agent_type: "bill_processor", status: "completed"})

# Get details of a specific run
get_entity("agent_instance", id="42")

# Manually trigger reconciliation
submit("agent_instance", "start", {agent_type: "reconciliation_agent"})

# Cancel a stuck instance
submit("agent_instance", "cancel", {instance_id: "42"})
```

---

## Agent Events

Events are triggers that start agent runs. They flow through a queue.

| Tool | Purpose |
|------|---------|
| `query("agent_event", filters={...})` | List events in queue |
| `get_entity("agent_event", id="X")` | Get event details |
| `submit("agent_event", "create", {...})` | Create a new event manually (owner or admin) |
| `submit("agent_event", "retry", {...})` | Retry a failed event (owner or admin) |
| `submit("agent_event", "ignore", {...})` | Mark event as ignored |
| `get_agents(action="get_event_stats")` | Queue statistics |

### Event Types

Common event types that trigger agents:

| Event Type | Triggers |
|------------|----------|
| `email.received` | Bill processor |
| `email.received.ap` | Bill processor |
| `schedule.triggered` | Reconciliation agent, scheduled jobs |
| `manual.trigger` | Any agent (manual start) |
| `agent_request.created.master_data` | Master data agent |
| `agent_request.completed.master_data` | Bill processor (callback) |
| `saga.phase_started` | Master data agent |

### Examples

```
# Check event queue
query("agent_event", filters={status: "pending"})

# Queue statistics
get_agents(action="get_event_stats")

# Create manual event
submit("agent_event", "create", {
    event_type: "manual.trigger",
    agent_type: "reconciliation_agent",
    payload: {"scope": "vendor"}
})

# Retry a failed event
submit("agent_event", "retry", {event_id: "15"})

# Ignore a problematic event
submit("agent_event", "ignore", {event_id: "16", reason: "Duplicate email"})
```

A person cannot create every event. The gateway refuses an event type outside
the allowed prefixes (`email.`, `connector.`, `import.`, `manual.`, …; for
example `bank_statement.manual_import` belongs to the import workflow), a
request callback (`agent_request.completed.*`), and a payload with keys only
the system sets (`from`, `storage_url`, `original_request_data`, …). The
refusal is a definite `Validation Failed` with `error_stage: pre_submission`:
nothing was created, and `validate_only` returns the same refusal. To re-run
a forwarded email, forward it again; to re-run bank or card lines, raise
`connector.data_received` (with `sync_type` and `bank_account_id`) or
`import.completed.card_transaction` (with `card_transaction_ids`).

---

## Agent Requests

Inter-agent communication. One agent creates a request, another processes it.

| Tool | Purpose |
|------|---------|
| `query("agent_request", filters={...})` | List requests with filters |
| `get_entity("agent_request", id="X")` | Get request details |
| `submit("agent_request", "create", {...})` | Create a new request |
| `submit("agent_request", "update", {...})` | Agent-side request updates; not a substitute for a human answer |
| `submit("agent_request", "respond", {...})` | Authenticated human answer with current version and retry key; follow the task contract |
| `submit("agent_request", "add_reminder", {...})` | Add follow-up reminder |
| `query("agent_request", filters={assigned_to_employee_id: X, status: "pending"})` | Get requests pending for a specific employee |

### Request Flow

A Bill review answer belongs to the existing task. Read the current request and
bill before responding; use its offered action and response contract. Human
answers use `agent_request.respond` with `expected_version`, an idempotency key
and, for Bill commands, `TaskActionV1` bound to the reviewed draft revision.
Comments and read-only questions do not authorize changes. Do not mark a review
completed through `agent_request.update` or manually post a second invoice to
bypass its owner.

Questions from Master Data (and other model-driven agents) take a plain-words
answer. The agent that asked carries it out with its own permissions, not the
person's, and records what it did on the task: applied, partly applied, failed
with the reason (including a permission it lacks), or a follow-up question. A
change that needs approval brings the task back to the agent after the decision.
Telling an agent to "take all permissions" does nothing: permissions change only
in the agent's configuration.

If the response is refused with "A response is already being processed", an
earlier answer is still with its agent: wait for its outcome on the task. For
Master Data and other model-driven agents, Bill reviews and billing usage tasks,
an answer the agent did not act on is released: the task shows "could not be
carried out" and accepts a new answer. Other tasks keep the answer until their
agent records an outcome; ask an administrator if one stays stuck. A `review_auto_created_*` request must name an existing vendor or
customer (`entity_type`, `entity_id`); creating one without is refused.

The Bill resolution agent reads evidence, updates the candidate,
validates and submits through existing workflows. Missing vendor/account/tax
configuration can be delegated through existing requests. It waits for verified
records and resumes the accepted instruction. A child's “completed” message
alone does not prove that the requested record exists or fits the bill.

**Apply changes** saves authorized bill changes for review; it does not
permit posting or master-data creation. **Apply and submit** permits the agent
to work toward posting within the accepted instruction. Hold and Reject are
explicit decisions; the bill task's response rail no longer offers a Hold
button (2026-09-25), though the intent still exists. Report the persisted outcome: a submitted workflow may
still await approval, a posted bill may have pending follow-ups, and a bill whose
reviewer made posting depend on a vendor rule stays unposted until that rule is
stored (it waits while the rule awaits approval). Never
repost a confirmed bill to repair a rule, attachment or purchase-order link.

Bill uses one pipeline/saga runtime in every entity. There is no legacy reply
engine or per-entity rollout flag. Other agents retain their own response contracts.

When an accepted `agent_request.resolve` leaves the request open (`held`,
`partially_applied`, `clarification_requested` or `amended`), its current
`completed_at` is cleared. Prior attempt outcomes and resolution times remain
history; an identical resolution retry does not rewrite them. Read current status
and the attempt evidence together. This does not bypass owner, revision or
supersession checks, nor establish a terminal-reason contract for every writer.

### Reference

Use the current `agent_request.create`, `agent_request.respond`,
`agent_request.update` and `agent_request.resolve` workflow definitions for
payloads. Requests use UUIDs, `request_data` for request content and
`response_data` for agent result content. The runtime's candidate amendment and
resolve operations require the authenticated owning agent; they are not general
chat shortcuts for editing or completing Bill review tasks.

---

## Agent API Keys

Each agent gets its own MCP API key for authentication.

| Tool | Purpose |
|------|---------|
| `submit("agent_api_key", "create", {...})` | Create MCP API key for an agent (owner or admin); the key is shown once to the caller and acts with the caller's roles |
| `query("agent_api_key")` | List agent API keys |
| `submit("agent_api_key", "revoke", {...})` | Revoke a key (owner or admin) |
| `submit("agent_api_key", "rotate", {...})` | Rotate a key, revoking the old one (owner or admin); the new key acts with the caller's roles. The agent's own runtime key is refused: use `regenerate_keys` |

A revoked or rotated-out key is refused with HTTP 401 on its next authentication,
even if its expiry date has not passed. Use the replacement key after rotation;
revocation does not stop a request already in progress.

A new key is shown once, in the response to the submission that made it.
Submitting the same request identity again returns the retained first result
with `api_key: "[redacted — shown once]"` and a `secret_notice`; the key is not
stored. If it was lost, use a deliberate new rotation intent after confirming
the previous rotation completed; do not repeat an uncertain rotation with a new key.

### Examples

```
# List API keys for all agents
query("agent_api_key")

# Create key for bill processor
submit("agent_api_key", "create", {agent_definition_id: 1, name: "bill-processor-prod"})

# Rotate a compromised key you created (an agent's own runtime key is refused:
# manage_agents(action="regenerate_keys", agent_type=..., force=True) replaces and revokes it)
submit("agent_api_key", "rotate", {key_id: 3})

# Revoke a key
submit("agent_api_key", "revoke", {key_id: 5})
```

---

## Scheduled Jobs

Configure recurring agent runs.

| Tool | Purpose |
|------|---------|
| `query("scheduled_job")` | List all scheduled jobs |
| `get_entity("scheduled_job", id=X)` | Get job details |
| `submit("scheduled_job", "create", {...})` | Create a new scheduled job (owner or admin) |
| `submit("scheduled_job", "update", {...})` | Update job schedule/config (owner or admin) |
| `submit("scheduled_job", "enable", {...})` | Enable or disable a job (owner or admin) |
| `submit("scheduled_job", "delete", {...})` | Delete a scheduled job (owner or admin) |
| `submit("scheduled_job", "trigger", {...})` | Manually trigger a scheduled job now (owner, admin or the job's creator) |

### Examples

```
# List all scheduled jobs
query("scheduled_job")

# Create daily reconciliation run at 6 AM
submit("scheduled_job", "create", {
    agent_type: "reconciliation_agent",
    cron_expression: "0 6 * * *",
    job_name: "Daily AP/AR Reconciliation",
    job_payload: {"scope": "vendor"}
})

# Disable a job temporarily
submit("scheduled_job", "enable", {job_id: 3, is_enabled: false})

# Trigger a job immediately
submit("scheduled_job", "trigger", {job_id: 3})
```

---

## Sagas

Multi-step orchestration across agents.

| Tool | Purpose |
|------|---------|
| `query("saga", filters={...})` | List sagas with filters |
| `get_entity("saga", id="X", include_related=true)` | Get saga with all phases |
| `submit("saga", "create", {...})` | Create a new saga |
| `submit("saga", "advance", {...})` | Advance saga to next phase |
| `submit("saga", "cancel", {...})` | Cancel a running saga |

### Saga Pattern

Sagas coordinate multi-agent workflows. Each saga has phases that execute in sequence:

```
Saga: "Process incoming bill"
  Phase 1: bill_processor extracts data
  Phase 2: master_data_agent creates vendor (if new)
  Phase 3: configuration_agent creates posting profile (if needed)
  Phase 4: bill_processor posts transaction
```

### Examples

```
# List active sagas
query("saga", filters={status: "in_progress"})

# Get saga details with all phases
get_entity("saga", id="7", include_related=true)

# Cancel a stuck saga
submit("saga", "cancel", {saga_id: 7, reason: "Vendor creation failed"})
```

---

## Downstream Rules

Configure event routing rules that automatically create events when triggers fire.

| Tool | Purpose |
|------|---------|
| `query("downstream_rule", filters={...})` | List all routing rules |
| `get_entity("downstream_rule", id=X)` | Get rule details |
| `submit("downstream_rule", "create", {...})` | Create a new rule (owner or admin) |
| `submit("downstream_rule", "update", {...})` | Update a rule (owner or admin) |
| `submit("downstream_rule", "toggle", {...})` | Enable/disable a rule (owner or admin) |
| `submit("downstream_rule", "delete", {...})` | Delete a rule (owner or admin) |

### Examples

```
# List all active rules
query("downstream_rule", filters={is_enabled: true})

# Create rule: when bill is posted, trigger reconciliation
submit("downstream_rule", "create", {
    name: "Post-bill reconciliation",
    trigger_event: "transaction.posted",
    target_agent_type: "reconciliation_agent",
    conditions: {"transaction_type": "AP_INVOICE"}
})

# Disable a rule
submit("downstream_rule", "toggle", {rule_id: 4, is_active: false})
```

---

## Agent Memory

Agents can store and recall persistent key-value mappings for future lookups.

| Tool | Purpose |
|------|---------|
| `manage_agents(action="store_memory")` | Store a memory entry (requires write permission) |
| `get_agents(action="recall_memories")` | Search for memories |
| `manage_agents(action="delete_memory")` | Delete a memory entry (requires write permission) |

> `store_memory` and `delete_memory` require write permission — a read-only caller gets `{"error": "write permission required to modify agent memory"}`. `recall_memories` has no such gate. This only applies to interactive (human/session) callers; agents writing their own learned memories run with their own permissioned context and are unaffected.

### Use Cases

- **Vendor name mappings**: "Amazon Web Services" -> vendor_id 42
- **Account classification rules**: "SaaS subscription" -> account 6200
- **Customer reference numbers**: "PO-12345" -> customer_id 15

### Examples

Memory is scoped per entity: one row per `(agent_type, legal_entity_id, memory_key)`, and `legal_entity_id` NULL is the org-wide scope. Recall without `legal_entity_id` sees only org-wide rows; with it, the entity's rows plus org-wide rows. A store or delete from an entity-scoped context (every agent, and any user limited to certain entities) must name an accessible entity — an org-wide write is refused with `{"error": "An accessible entity is required for this memory write"}`. There is no `memory_id`: a delete is addressed by key and scope, and omitting `legal_entity_id` deletes only an org-wide row.

```
# Store a vendor mapping for entity 9
manage_agents(action="store_memory", agent_type="bank_transaction_processor",
    memory_type="learned_mapping",
    memory_key="vendor_mapping:Amazon Web Services",
    memory_value='{"vendor_id": 42, "default_account": "6200"}',
    legal_entity_id=9
)

# Recall vendor mappings (entity 9's rows plus org-wide rows)
get_agents(action="recall_memories", agent_type="bank_transaction_processor",
    memory_type="learned_mapping", memory_key_pattern="vendor_mapping:%", legal_entity_id=9)

# Delete stale memory (this entity's row only)
manage_agents(action="delete_memory", agent_type="bank_transaction_processor",
    memory_key="vendor_mapping:Amazon Web Services", legal_entity_id=9)
```

---

## Entity Email Addresses

Manage email addresses associated with legal entities for agent email routing.

| Tool | Purpose |
|------|---------|
| `query("entity_email", filters={...})` | List email addresses for an entity |
| `get_entity("entity_email", id=X)` | Get email address details (replaces `get_entity_email_address`, MCP registration removed) |
| `submit("entity_email", "create", {...})` | Create a new email address |
| `submit("entity_email", "update", {...})` | Update email address config |
| `submit("entity_email", "delete", {...})` | Delete an email address |
| `submit("entity_email", "verify", {...})` | Verify an email address |
| `query("entity_email", query=...)` | Look up which entity an email routes to |

### Examples

```
# List email addresses for entity
query("entity_email", filters={legal_entity_id: 9})

# Create AP inbox for an entity
submit("entity_email", "create", {
    legal_entity_id: 9,
    email_address: "ap@company.com",
    email_type: "ap_inbox"
})

# Look up routing for incoming email
query("entity_email", query="bills@company.com")
```

---

## Context Helpers

Pre-built tools that load everything an agent needs in a single call.

| Tool | Purpose |
|------|---------|
| `get_agents(action="get_bill_context")` | Loads legal entity, workflow schema, vendors, accounts, tax codes, payment terms, dimensions, posting profiles |
| `get_agents(action="load_financial_context")` | Loads trial balance, income statement, balance sheet, AR/AP aging, recent transactions, bank balances, budget vs actual |
| `send_notification_email` | Send notification emails (requires write permission for interactive callers). You write the subject and a plain-text body; the server adds the brand, "From the [agent] agent", the footer and the message reference |

### Examples

```
# Load everything needed for bill posting
get_agents(action="get_bill_context", legal_entity_id=9)

# Load financial snapshot for analysis
get_agents(action="load_financial_context", legal_entity_id=9)

# Send notification
send_notification_email(
    to_emails=["admin@company.com"],
    subject="Bill processing complete",
    body="Processed 15 bills. 2 need review."
)
```

---

## Common Scenarios

### 1. Deploy a New Agent from Template

```
# List available templates
get_agents(action="list_templates")

# Seed from template
manage_agents(action="seed_definitions", agent_types=["bill_processor"], confirmed=True)

# Configure the agent
submit("agent_definition", "update", {
    definition_id: 1,
    config: {"confidence_threshold": 0.85}
})

# Enable it
submit("agent_definition", "enable", {definition_id: 1, is_enabled: true})

# Create API key
submit("agent_api_key", "create", {agent_definition_id: 1, name: "bill-processor-prod"})
```

### 2. Monitor Agent Health

```
# Quick summary of all running agents
get_agents(action="get_running_summary")

# Check event queue for backlogs
get_agents(action="get_event_stats")

# List failed events
query("agent_event", filters={status: "failed"})

# List recent instances with errors
query("agent_instance", filters={status: "failed"}, limit=10)
```

### 3. Debug a Failed Agent Run

```
# Get the failed instance
get_entity("agent_instance", id="42")

# Check the triggering event
get_entity("agent_event", id="15")

# Check any pending requests (agent_request has no instance filter;
# read the instance's linked requests from get_entity above)
query("agent_request", filters={status: "pending"})

# Retry the event after fixing the issue
submit("agent_event", "retry", {event_id: "15"})
```

### 4. Set Up Scheduled Agent Runs

```
# Create daily reconciliation at 6 AM UTC
submit("scheduled_job", "create", {
    agent_type: "reconciliation_agent",
    cron_expression: "0 6 * * *",
    job_name: "Daily Reconciliation"
})

# Create weekly payment proposals on Fridays at 10 AM
submit("scheduled_job", "create", {
    agent_type: "payment_proposal_agent",
    cron_expression: "0 10 * * 5",
    job_name: "Weekly Payment Proposals"
})

# Verify scheduled jobs
query("scheduled_job")
```

### 5. Configure Inter-Agent Communication

```
# Create downstream rule: bill posted -> reconciliation
submit("downstream_rule", "create", {
    name: "Auto-reconcile after bill posting",
    trigger_event: "transaction.posted",
    target_agent_type: "reconciliation_agent",
    conditions: {"transaction_type": "AP_INVOICE"}
})

# Verify rules
query("downstream_rule")
```

---

## Key Concepts

### Execution Modes

- **pipeline**: Runs validated stages and domain services. Bill requires this mode.
- **code / hybrid**: Uses a code host; either may call a model for a bounded step.
- **llm**: Uses the SDK host for model-led work. Model tiers such as `fast` are
  separate from the stored execution mode.

### Agent Concurrency

Each agent has `max_concurrent_runs` to prevent resource conflicts. The reconciliation agent is limited to 1 concurrent run to prevent double-matching.

### Event-Driven Architecture

Agents are triggered by events. Events flow through a queue and are processed in order. Failed events can be retried or ignored.

### Inter-Agent Communication

Agents communicate via requests, not direct calls. This enables loose coupling and audit trails. Common pattern: bill_processor creates a request to master_data_agent for vendor creation, then receives a callback when complete.

### Memory Persistence

Agent memory persists across runs. This allows agents to learn from previous processing (e.g., mapping vendor names to IDs without repeated searches).

## Architect diagnosis and event liveness

`agent_architect` memories with keys beginning `diagnosis:` or `health_review:`
are diagnostic hypotheses, not permanent suppression rules. Stores require a JSON
object, set `requires_live_revalidation: true` and `authority: diagnostic_hypothesis`,
and cap TTL at seven days (default seven). Re-read live source documents, GL identity,
schedule capacity and journal state before accepting an old diagnosis. Different
expense accounts do not prove two schedules consume different source prepayments.

Check enabled definitions for a real trigger/scheduled job and zero lifetime runs.
Normal seeding repairs a missing amortization job while preserving custom/disabled
jobs. Expired pending events are terminalized; in-flight events are not expired by
this sweep. Card upload events keep their dedicated cleanup callback. Recognition
emits a downstream event only when an enabled subscriber exists.

### Bills Collector delivery recovery (pipeline 1.1)

Collector distinguishes confirmed provider acceptance from unknown delivery. A held
payment must not be re-reminded by changing recipient, grouping, or run date.
The next run repairs confirmed delivery stamps automatically. Unknown dispatches
require operator verification; never delete an effect key or payment claim to
force a retry. `collector_delivery_recovery.py` is an operator maintenance command,
not an agent tool. Recording a verified provider outcome does not send an email.
Migration 610 is required before deploying this pipeline version.

Amortization Recognizer also uses its canonical deterministic pipeline on the
2026-09-23 platform release. Do not switch its mode to recover the old host. Task retry
authority comes from the stored human response, scoped schedules and current
permissions. Waiting workflows retain their existing identity; final status uses
live recognition evidence. Preview does not post or resolve a task.


Bank/card processing uses mandatory prepare/load/per-source/finalize stages. Task
responses bind current worklist fingerprints and the stored human actor; changed
sources, revoked access, or superseded replies do not authorize posting. Legacy
worklists refresh and require a new response. Approval waits and receipt recovery
retain the same response attempt. A historical checkpoint is not evidence that a
currently unmatched source is resolved. Legacy verification-completed events are
observational; use the owning task response path for financial instructions.


Billing Run now uses mandatory prepare/record-usage/bill/finalize stages. Its V2
usage answers use the same owning response-attempt lifecycle, with a Billing domain
adapter: stored contract periods and quantities, current human authority, durable
workflow replay, and invoice evidence before completion. A child workflow approval
must not auto-complete a response-owned task. Legacy usage completion callbacks
require a new owning reply. This was deployed and verified in the 2026-09-23
platform release (PR #134).


### Invoice Delivery pipeline and uncertain sends (2026-09-23)

Invoice Delivery has one mandatory prepare/deliver/finalize pipeline, including
stored code definitions. Automatic delivery remains opt-in; a manual resend is
a new persisted event, while replaying that event does not send again. Invoice
claims and durable provider receipts prevent concurrent or uncertain sends from
being repeated. A provider message ID is required for completion; delivery log,
sent event and receipt completion commit together. Unknown dispatches await
operator provider verification using `scripts/invoice_delivery_recovery.py`;
never clear a claim to force a retry. Preview performs no rendering or writes.
The agent sends invoices and does not collect payment.


### Period Close pipeline (2026-09-23 migration)

Period Close now uses mandatory prepare/evaluate/resolve/finalize stages, including
stored hybrid definitions. Its saga, check registry and financial workflows remain
authoritative. An approval submission keeps the final phase open; ten-minute
durable continuations reuse the same command/workflow and verify the current closed
period before completing. Unknown effects retain their identity for investigation.
The bound final phase may close its own active saga only after other phases finish
and current checks have no blocking failures; it never supplies `force`.
Remediation still delegates to the specialist owner and rechecks after resolution.
Domain `dry_run` records a diagnostic saga; pipeline `preview` performs no writes
or model calls. Approval polling does not make another model memo call.


### Payment Collection pipeline (2026-09-23 migration)

Payment Collection uses mandatory prepare/charge/post/finalize stages, including
stored code-mode definitions. An invoice reservation and provider idempotency key
separate charging from ledger settlement. Unknown charges stay held; known
provider payments and approval waits resume without another charge. Only live
posted AR payment evidence is `collected`. Confirmed declines alone schedule
new dunning intentions. Private receipt bindings preserve current actor/entity
and workflow authority through posting. Invoice creation still does not dispatch
collection. See GUIDE_AGENT_PAYMENT_COLLECTION.md for configuration, recovery,
provider limits and tests; production deployment remains a separate operation.


### Payment Proposal pipeline (2026-09-23 migration)

Payment Proposal uses mandatory prepare/select/groups/create/finalize stages and
reserves current source payables before approval. The executor rechecks source
versions, actor/entity and bank fingerprints. Creation and receipt completion are
atomic; pending workflows resume, unknown effects stay held. `proposed` reports
live batch status and never means transmitted or paid. Missing bank setup produces
an entity-specific recheck task; current configuration evidence completes it.
Historical nonempty proposal drafts retain the normal approval recovery sweep.
See GUIDE_AGENT_PAYMENT_PROPOSAL.md for exact behavior and cutover limitations.

### Expense pipeline outcomes

Expense Processor has one pipeline host. A created draft, attached receipt,
accepted approval request, forwarded bill and posted reimbursement are distinct
outcomes. Current report/ledger evidence determines completion; replay uses the
original source key. Never restore the removed hybrid/LLM fallback to bypass a
held operation. Employee and configured workflow approval remain required.


### Optional model dispatch limits

`config.model_call_policy` accepts positive `max_input_tokens`,
`max_call_cost_usd`, and `max_run_cost_usd`. Shared call preflight reserves run
exposure atomically before dispatch and refuses unavailable bounds when a limit
requires them. SDK input estimates cover initial context only; an input-token
limit refuses SDK sessions because future tool/context turns cannot be bounded.
SDK calls enforce their session cost budget; native calls estimate input
and maximum output. Unknown/interrupted calls retain reservations. These estimates
are separate from provider invoices and customer credits; they do not grant spend
authority or imply an organization monthly ceiling. Existing effect recovery can
finish without new model work. See the technical model usage guide for coverage.


### LLM domain task completion

Bill's existing vendor dependency format (`entity_type=vendor` with `entity_name`
or `vendor_name`, and no `action`) is supported by the same current-record verifier
as `create_vendor`. It does not bypass entity scope, active-record checks or
ambiguity handling. Explicit actions retain their original meaning.

Master Data and Configuration requests complete only after their owning activation
verifies current entity-scoped deliverables. A successful model run, saved edit or
approval alone is insufficient; direct completion without response data is also
checked. Existing V2 response owners retain their own executors.

For Configuration questions use `verification` action `resolve_configuration`; the
server stamps the original request and resumes it from the stored human response.
Older unbound activations need evidence review and a fresh owning run. Triage
creates correlated dependencies with server-enforced hop limits and does not claim
that routing solved the producer's problem. Architect definition changes and custom
Vendor Deduplication updates are saved work, not verified recovery or a merge. Do
not broaden permissions to make an outcome green. Unknown effects need deterministic
recovery before another model activation. The technical domain-outcomes guide
documents the supported actions and read-only recovery command.


### Agent mode and origin display (deployed 2026-09-25)

The definitions list, quick view and detail/edit views distinguish LLM, Code,
Hybrid and Pipeline. Pipeline is not an alias for Hybrid. Missing or unsupported
modes display Unknown instead of LLM; the list includes Pipeline/Unknown filters.
Origin (Arfiti or Custom) is separate from execution mode. Customized reflects
the existing customization flag; a historical false flag is shown as Not verified
until its base and effective configuration have been reconciled. These display
changes do not convert agents or change dispatch.


### Authoring release status

The authoring implementation was deployed on 2026-09-25. See
`RELEASE_AGENT_AUTHORING_PARITY_2026-09-25.md` for deployment evidence and known
follow-ups, the closed `SPEC_AGENT_AUTHORING_PARITY_2026-09-24.md` for the specification, and pipeline
guide section 9 for tool contracts. Supplied-JSON preview has no production DB or
provider adapters. Do not describe it as live model or financial execution.
Architect release 107 is published for reviewed upgrades; publication alone did not
activate its changed prompt for existing customers.


### Native Bill posting authority

Autonomous native Bill posting derives only `ap:write` from an enabled Bill
processor's current `transaction.post` capability and a bound system-created Bill
revision. The current run must match the organization and entity and be running
or awaiting approval. Human-reviewed candidates retain the current human's roles
and entity access; authored agents retain creator/revision-bound authority.

Workflow creation stores the verified native run ID in
`system.workflow_instances.native_bill_instance_id` before automatic completion.
Caller-supplied payload/provenance fields cannot select this execution identity.
At execution, including after approval, the worker rechecks the Bill revision,
agent capability and entity. A successfully completed originating run can finish
its approved workflow; disabled agents, revoked capabilities and failed runs
cannot. This authority covers AP invoices only, not AR, payroll or journals.
Migration 626 is required before deploying this code. These changes have local
regression evidence; production deployment remains a separate release gate.


Collection posting carries the receipt owner's freshly verified human permissions
into WorkflowEngine, rather than retaining generic service-account permissions.
Current role/entity revocation can refuse posting even after the provider confirms
payment. Such a receipt requires reconciliation/recovery; it must not trigger a
second charge. This changes no provider permissions and does not grant the agent
AR authority independently of the reserved human actor.


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

### Dashboard operations visibility

Dashboard Events is an owner/admin operations view, scoped to accessible entities; restricted admins cannot open unscoped events. Use Communications for ordinary mail access. Memory, job, entity-email, and run-count reads are entity-scoped. A restricted reader sees a scheduled job only when all its targets are accessible; organization-wide jobs require organization-wide access.

### Activation validation for direct operations (2026-10-06, release pending)

An explicit capability can name a registered platform executor (for example
`agent_request.resolve`) or `attachment.create`, even when no tenant workflow row
exists. Activation checks the existing routing policy and executor registration.
Human grants for this path require organization administrator authority; agents
can only delegate capabilities they already hold. Runtime grant/entity checks
remain enforced. Existing tenant workflow permissions still apply, and missing
financial workflows and unknown executors remain refused. This validation change
does not add capabilities to existing definitions or enable agents automatically.


## Bounded worker admission (unreleased correction)

A pending event remains queued when its lane has no capacity. The claim query now
materializes the selected event IDs once so PostgreSQL cannot exceed the requested
batch through a repeated locking scan. Organisation/fleet/worker caps and reserved
interactive/finalization capacity are unchanged. This requires updated workers;
confirm deployment before claiming the correction is live. Existing processing
claims remain subject to ordinary heartbeat and liveness recovery.
### Agent task access after role changes

Agent request details and supporting task data require a current operational
read grant: `accounting:read`, `ap:read`, `ar:read`, `payroll:read`,
`master_data:read`, `payments:read`, or `audit:read` (including matching
wildcards and owner/admin authority). `reports:read` alone does not grant this
access. An old assignment is not an access grant after a role change.

Admin applies this baseline to request lists/details, outcomes, review lines,
workspace/history, candidate/reference reads, model usage and conversations.
Report-only users receive empty task inboxes/counts and no agent-request
notification previews. MCP agent-request reads use the same operational gate;
legacy agent API keys retain their existing bare `read` scope.

Comments and response submission additionally require a live mutation grant,
in addition to the membership write gate. Read-only questions retain the
operational read gate. Existing entity restrictions and downstream business
permissions still apply. This is a baseline report-only boundary, not a new
per-agent/domain isolation model: having one operational read grant does not
prove every task's embedded data has been independently domain-filtered.
Financial report drill-down semantics and other agent run surfaces are separate
from this change.


### Saga phase output persistence

Completed and deferred phase outputs use the strict agent JSON encoder. Dates and
timestamps persist in ISO format, UUIDs as strings, and Decimal amounts as exact
strings without float conversion. Nested evidence retains its structure. Unknown
objects, non-string mapping keys and non-finite amounts are refused rather than
stored as arbitrary representations. A persistence failure is not phase completion;
inspect the durable phase status before recovery or retry. No new migration or
accounting entry is involved.

### Deferred-phase timeout arbitration

The worker locks and rechecks active-saga and stale-waiting-phase state before
applying timeout failure. A callback that already resumed the phase wins over an
older scan result; competing workers skip locked candidates. A real blocking
timeout still pauses the saga and requires reviewed retry. Do not interpret a
timeout scan or late callback as permission to repeat a financial effect.

## Grantable SDK tool validation

Agent authoring and activation recognize the execution host's explicit SDK builtin
allow-list (`WebSearch`) as well as registered MCP tools. WebSearch still requires
normal administrator/delegation authority. Other SDK builtins, including shell,
filesystem and WebFetch tools, remain unavailable through this exception. This
does not waive workflow availability or current/pinned permission checks.


### Saga checkpoint workflow references (QA branch)

A saga is readable only when every `close_workflow_id` in its root checkpoint,
phase checkpoint or phase output resolves to a workflow and definition in that
saga’s organization. The check applies even without a linked agent instance.
Missing or cross-company definitions hide the saga before rows, counts and pages
are returned, alongside existing domain/entity checks. Valid same-company links
remain readable with the required permissions. This is read protection; it does
not repair stored links, grant write authority or certify hosted deployment.

The same read policy rejects a present `pending_request_ids` container that is
text, a number or an object in any of those three locations. It must be an array
(or absent/null for no list). A malformed container is not interpreted as an
empty list. Every listed request still has to resolve and satisfy current read
authority; empty arrays and null retain their existing no-reference behavior.


### Execution progress-log containers (QA branch)

Admin and MCP execution reads require stored `progress_log` to be an array or
null. A malformed object, string or number hides the execution before rows,
counts and pages are returned; linked sagas inherit that exclusion. Empty arrays
and null retain their no-log behavior. This protects against treating malformed
stored metadata as an empty log; it does not repair historical data or classify
sensitive information embedded in arbitrary free text.

Each progress entry's optional `data` must likewise be an object or null/absent.
An array, string, number or boolean in that field excludes the execution and its
linked sagas rather than silently dropping the metadata from the read check.
Empty objects and null remain supported; valid structured metadata still receives
the existing domain/entity checks.


### Request line source authority (QA branch)

For readers whose transaction types are restricted, Admin and MCP resolve each
`lines[].source_transaction_id` in request and response metadata against the
request's entity and the stored transaction's reversal-source type. A claimed AP
line type cannot downgrade a payroll source. Missing, foreign-entity or forbidden
references hide the request and its thread before rows, counts and pagination.
Valid reimbursement sources remain readable with AP authority. Payments-only
access does not acquire transaction read grants. Execution/saga policies reuse
these request checks. Arbitrary free text and unsupported nested shapes remain
outside this bounded source classification; no write or approval grant changes.

The structured `lines` field in request/response metadata must be an array of
objects, or null/absent. Object/scalar containers and scalar, null or nested-array
entries fail closed before domain checks. Empty arrays and object entries remain
supported. Admin's explicit metadata guard and both SQL predicates apply this
shape rule; it does not classify arbitrary text nested inside valid objects.

Stored transaction reference lookups preserve canonical decimal ID matching while
using the transaction ID index. Leading zeros, plus signs, decimal/exponent forms,
negative zero and out-of-range bigint values remain unresolvable. Invalid text
cannot produce a numeric-cast error. This changes query cost, not read grants.


### Nested execution result authority (QA branch)

Admin and MCP execution reads validate the reserved `created_documents` and
`results` arrays in payloads and progress-entry data. Containers must be arrays
of objects or absent/null. Each entry receives the existing domain checks;
legacy created-document `id`/`type`, `transaction_id`, `existing_transaction_id`
and line source references cannot downgrade stored transaction authority.
Every nested transaction reference must resolve in the execution's entity,
including for wildcard readers. Missing, noncanonical, oversized and conflicting
references hide the execution before rows, counts and pages; valid AP and
payroll results remain available to appropriately authorized readers.
These checks cover one reserved result-array level. Arbitrary deeper JSON,
free-text disclosures and individual display-field validation remain under
review. They do not repair stored data or grant write/approval access.


Reserved execution result entries carrying `request_id` must resolve to a
request in the current company and the execution's entity. Admin and MCP apply
the shared request-thread policy, including restricted sibling requests, before
returning the execution. Missing, foreign-company/entity or forbidden-thread
references hide the execution; null references and readable AP/payroll requests
retain their existing behavior. This covers `created_documents` and `results`
entries, not arbitrary request-like fields elsewhere or recursive reference
chains. Workflow references and broader provenance remain under audit.


Reserved result entries with `workflow_id` must resolve to a workflow and
definition in the current company. The referenced workflow must have an object
payload, a nonempty definition type, and satisfy execution entity/domain checks
for its payload and stored object links. Transaction object links must resolve
in the execution entity even with wildcard domain grants; this also applies to
workflows already linked through execution actions. Missing or forbidden
references hide the execution. Valid AP/payroll and null-reference cases remain
supported. Arbitrary deeper result arrays and recursive workflow/request chains
are not certified by this bounded check.


Execution request/workflow reference checks also cover the root input/output
objects and progress-entry envelopes/data, in addition to reserved result-array
entries. The same company, entity and shared request-thread/workflow rules apply;
putting a restricted reference outside a result array does not make it readable.
Valid AP/payroll references remain supported. This is not recursive traversal of
arbitrary JSON or of every referenced record's own references.

Execution payloads also require direct `transaction_id` and each
`lines[].source_transaction_id` to resolve to a stored transaction in the execution
entity, even for wildcard readers. This applies to input/output, progress
envelopes/data and workflow payload metadata. Missing, cross-entity, noncanonical
and overflowing IDs withhold the execution; valid same-entity references retain
their existing business-domain checks.

Request readers enforce the same transaction existence/entity boundary for
transaction sources and request/response transaction or line references, including
wildcard readers. A thread containing an unauthorized transaction reference is
withheld as a whole before summaries, counts and pagination; a readable sibling
does not grant access. Business-domain access to valid same-entity records remains
unchanged.

Payment-batch source references and both `batch_id`/`payment_batch_id` fields
in request/response data must resolve to a batch in the request entity, including
for payroll-authorized and wildcard readers. Each supplied reference is checked;
a valid batch ID does not override a conflicting, missing or cross-entity one.
Thread siblings and execution metadata using the shared request policy inherit
this boundary. Payroll authorization changes domain visibility, not entity scope.

### Deferred references in execution payloads (QA branch)

Execution inputs, outputs, progress-log envelopes/data and supported `results` /
`created_documents` records now enforce `pending_request_ids` and
`close_workflow_id` references as well as the existing singular request/workflow
fields. Each pending request must exist in the current organization/entity and
pass the shared request/thread read policy. A close workflow must resolve with a
same-organization definition and pass entity/domain and stored-link checks.
Wildcard domain grants do not bypass existence or tenant/entity boundaries.

A pending list must be an array or absent/null; null elements, unresolved IDs and
malformed containers are refused. Empty lists and absent/null close references
remain allowed. Denial applies before execution rows, counts and pages are
returned. This does not alter deferred-phase processing, repair historical
references or grant write authority. Arbitrary deeper JSON and recursive chains
are not certified by this bounded reference check.

### UUID reference lookups (QA branch)

Execution and saga request/workflow references must use the lowercase hyphenated
UUID spelling returned by the API. Guarded input-side UUID casts preserve the
existing refusal of malformed, uppercase or noncanonical reference strings while
allowing stored UUID primary-key lookups. Tenant/entity/domain and thread-sibling
checks still apply after lookup. No schema migration, index creation or stored
payload normalization is performed by this optimization.

### Structured execution outcome references (QA branch)

The shared read policy checks request/workflow metadata inside `task_outcome`,
`investigation`, and `investigation.outcome`, in addition to supported root and
result records. `pending_refs` and `evidence_refs` must be arrays of strings (or
absent/null). Recognized `workflow:<uuid>`, `agent_request:<uuid>` and
`transaction:<id>` entries resolve through current stored read authority; missing,
foreign or forbidden targets withhold the execution. Transaction IDs must retain
canonical integer spelling; UUID spelling requirements are unchanged. Malformed
wrapper containers are refused. Empty lists and null wrappers remain supported.

This is a bounded check of producer-defined structured references. Other evidence
prefixes require their own authority mapping. Attempt/draft and fiscal-period
checks are described below; saga continuations remain open. Free text and arbitrary recursive JSON are not certified.
The change does not execute task actions, rewrite payloads or grant permissions.

### Attempt and draft evidence references (QA branch)

Execution outcome references of the form `agent_request_response_attempt:<uuid>`
now resolve to an existing attempt in the current organization. Its parent request
must pass current entity/domain and thread-sibling authority. The attempt's stored
execution workflow and root metadata in its compiled directive, domain command
and interpretation also pass the existing reference and payload checks. Malformed
metadata containers and missing/foreign references withhold the execution.
The same checks apply to the domain command's `execution` binding and each
compiled directive `bank_row_outcomes` value. The row map and its entries must
be objects; a missing/null map is allowed. Any unreadable row withholds the
execution, including when another row is readable. Nested typed outcomes use the bounded recursive traversal described below.

`bill_draft:<id>:<revision>` requires AP/accounting read access, a draft in the
execution entity, and that exact stored revision. Canonical ID/revision spelling
is required. The draft's stored transaction, workflow and active request links
must remain readable. `bill_draft:<id>:followup:<nonempty-label>` checks the same
draft authority; the label is descriptive and does not prove follow-up completion.
These checks do not execute recovery actions or rewrite saved evidence. Arbitrary
attempt metadata and remaining master/attachment reference
types still require separate verification.

### Fiscal-period execution evidence (QA branch)

Execution `pending_refs` and `evidence_refs` recognize `fiscal_period:<id>` and
`fiscal_period:<entity_id>:<period_name>` as distinct formats. Each must resolve
to a stored period in the execution entity. Numeric IDs use canonical positive
integer spelling; the name format preserves the entire exact suffix, including
colons. Missing/foreign records, invalid IDs and empty names withhold execution
results. This follows current entity-scoped period reads without adding an
accounting permission requirement. Readability does not prove current closure,
locking, or permission to close/reopen a period. `close_command:<uuid>` refers to
retained saga/phase bindings, as described below.

### Recursive attempt outcome authority (QA branch)

Supported attempt evidence is traversed through `task_outcome`, `investigation`
and `investigation.outcome`, and `task_execution` and `task_execution.outcome`.
A recursive SQL query deduplicates metadata nodes: readable self-references and
mutual attempt cycles terminate without an arbitrary depth cutoff. Every reached
supported request/workflow/transaction, attempt, draft or period reference still
passes its stored authority checks. One unreadable or malformed reached record
withholds the execution. Ordinary scalar `outcome` labels are not treated as
nested wrappers. These checks do not follow arbitrary JSON fields or free text;
other unmapped evidence families remain open. No effects,
recovery actions, merges or deployment are performed by this read policy.

### Saga and close-command outcome authority (QA branch, deployment pending)

Execution `pending_refs` and `evidence_refs` resolve `agent_saga:<uuid>`,
`saga:<uuid>:phase:<positive-number>:iteration:<nonnegative-number>` and
`close_command:<uuid>` against retained records. Missing, malformed, foreign or
unreadable references withhold the execution. All saga phases and current linked
instances retain domain/entity, progress/result, request-thread and workflow
checks. Known result arrays on reached metadata are normalized and checked too.
Readable saga/instance/attempt cycles terminate through deduplicated traversal.

A phase/iteration reference requires a matching retained `saga.phase_started`
event from `saga_orchestrator`, with the same company, entity, phase and assigned
agent type. Its historical assigned instance, when present, must retain its event
binding and pass the execution checks. An advanced or reset current checkpoint
does not invalidate a readable retained historical event. An invented iteration
is not readable merely because the phase exists.

Close commands resolve a unique saga/phase through its current checkpoint,
a retained fiscal-period **close** workflow's `_period_close` binding, or an exact
period-close submission receipt. Conflicting owners are denied. Retained workflow
and receipt metadata remain subject to authority checks. A root-field lookalike
is not the producer's binding. This establishes read eligibility only: it does
not prove close completion, authorize a close/retry, or bypass current actor and
phase mutation guards. Missing retained history fails closed; this change does
not recreate history. Other unmapped typed records and investigation references,
arbitrary JSON and general request/workflow graph expansion remain open.

### Typed master and configuration evidence (QA branch, deployment pending)

Supported execution evidence `<kind>:<positive-id>` now resolves a stored record
in the execution entity for: account, amortization_schedule, bank_account,
customer, dimension_value, exchange_rate, fixed_asset_category, item, payment_term,
posting_profile, recurring_contract, tax_code, tax_registration and vendor.
Effective-view types use their master IDs and the entity-specific view, matching
the existing registry reader; a shared master ID in another entity is insufficient.
Missing records, noncanonical/overflow IDs and extra suffixes withhold the execution.

The installed read contract requires `ap:read` or `master_data:read` for vendors,
`ar:read` or `master_data:read` for customers, and `accounting:read` for amortization
schedules. Existing wildcard semantics apply. The other mapped types retain their
current entity-scoped registry read contract without a new permission requirement.
The mapping is checked against the installed registry in tests. These are read
checks, not `current_record`'s active/effect-completion checks; readability does not
prove completion or grant write access. Organization-only tax/dimension records,
unregistered types, investigation arguments and arbitrary reference fields remain
outside this bounded mapping. Fiscal-period evidence retains its separate formats.

### Investigation bill and attachment read authority (QA branch, deployment pending)

Non-null persisted `investigation` metadata requires current AP read authority,
including narrative reasons without record IDs. Its `outcome.bill_id` and known
trace tools `bill`, `attachment` and `prepare_review` also validate stored targets.
Bills must be same-entity `AP_INVOICE` transactions. Attachments must be explicitly
undeleted, in that entity and stored in the `AP_INVOICE` owner space; the stored
transaction must exist with the same entity/type. A `prepare_review` attachment
must also belong to that trace entry's bill. Missing, malformed, foreign, deleted
or mismatched references withhold the execution, including when reached through
saga phases, linked instances or attempts.

Trace containers must be arrays/null/absent; entries require known tool names and
object arguments. Internal outcome rows carry a separate trusted origin flag; a
trace tool named `outcome` cannot impersonate them. Bill/attachment tools require their reference fields, and
`prepare_review` requires a nonempty attachment array. `open_bills.after_id` remains
a pagination cursor, not an ownership reference. These checks cover reference
shape and authority; they do not revalidate every historical tool argument or
prove a completed settlement.

The producer also returns flattened output. Its `bill_id` is interpreted only
when paired input identifies `reconciliation_evidence_v1`, directly or through
`job_payload.engine_version`. Unrelated root `bill_id` fields retain their prior
semantics. This source binding is retained when traversing saga phases and linked
instances. Producer-bound purchase IDs now require current stored purchase
ownership: AP read plus entity scope, and for human callers the stored membership
or entity employee link. Missing purchase records, malformed IDs, missing actors
or memberships, foreign entities and mixed-owner self-service rows are withheld.
The binding is `engine_version=reconciliation_evidence_v1` directly or in
`job_payload`, or the stored saga type for its checkpoint. Both direct and nested
bindings must pass if present. Unrelated purchase_id fields retain their prior
meaning. Arbitrary source text and unmapped references remain outside this scope.
No write, retry or financial effect is authorized by this read.


### Reconciliation request evidence reads (QA branch, not deployed)

Stored `reconciliation_agent` requests with action `investigate_purchase` or
`review_purchase_settlement` require AP read permission and current purchase
ownership in the request entity. Ordinary/unknown human roles need their entity
employee link; broad stored finance/viewer roles retain entity-scoped reads.
Missing actors, memberships, purchases and malformed IDs fail closed. Trusted MCP
agent reads retain their existing domain/entity/task boundaries. Every member of
a request thread must pass before rows, counts or pagination are returned.

Settlement-review requests additionally resolve the saved AP bill, attachment
IDs and attachment owner snapshots, and saved card sources/journals against
current read authority. Deleted, missing, foreign-entity or unreadable evidence
hides the request. Attachment ownership uses its canonical owner type; card
sources use master employee IDs, while purchases use entity employee IDs.
Legacy requests without `source_evidence` remain supported. Readability does not
approve settlement, refresh a historical snapshot, or bypass version/effect
checks. Additional unmapped request references and arbitrary metadata/free text
and hosted acceptance remain open.


### Bill and billing-usage request reads (QA branch, not deployed)

Admin and MCP request readers require `ap:read` for the installed `review_bill`
action and `ar:read` for `provide_usage_data`. These requirements apply even to
legacy rows without owner, object-type or source-table hints, and also to known
actions in response metadata. They add to existing domain/entity checks. Every
member of a thread must be readable before rows, counts and pages are returned;
a thread containing both actions requires both domains. Wildcard grants retain
both domains. Other actions are not classified by this change. Read access does
not authorize approval, posting, changing a draft or supplying usage. Broader
structured-reference and hosted-role acceptance remains open.


### Stored review and usage references (QA branch, not deployed)

For `review_bill`, a supplied draft ID and revision must resolve together to a
stored revision of a draft in the request entity. A linked transaction must be
a same-entity AP invoice. Missing/foreign drafts, absent revisions, malformed
IDs and wrong bill bindings hide the request and its thread. Legacy reviews
without either draft field remain readable under the existing AP/entity policy.
Historical revisions may remain readable; this does not approve a stale draft.

For `provide_usage_data`, a supplied billing run must match the organization and
entity, and each supplied `contracts[].contract_id` must resolve in that entity.
Malformed contract collections and missing/foreign contract IDs deny the thread.
The producer allows an absent billing-run ID; it remains supported. Checks apply
to request and response metadata before rows, counts and pagination. Responses
inherit the originating request action even when they omit their own action. Approval,
posting and usage submission still perform their existing live validations.
The bounded draft workflow graph is described below. Source attachments and
arbitrary embedded metadata remain outstanding read-authority coverage.


### Storage outcome binding correction (QA branch, not deployed)

Upload outcomes use the newest matching bill draft in the upload's entity. A
matching storage key in another entity cannot supply failure details, a posted
state, or a review status. Linked tasks and original/retry events must match both
the organization and upload entity before their status contributes to the page.
Original and retry events must also be `bill.upload` events whose payload
`bill_upload_id` matches the upload. Missing, null or mismatched payload IDs and
unrelated event types cannot mark this upload processing or suppress Reprocess.
Valid live upload events continue to block duplicate processing.
A linked task contributes its ID/status only when its action is `review_bill`
and its `bill_draft_id` names the matched draft. Same-entity tasks for another
draft or action are ignored. This does not certify all task payload references.
The same joins run under the existing upload-row lock for Reprocess, so a newer
foreign draft cannot override the local posted case and permit another attempt.

Owner/admin reprocess authorization, entity checks, live-run/posting refusals and
source-file checks are unchanged. Historical mismatched references are ignored
for these derived outcomes; this change does not repair stored data or authorize
a retry. Broader task payload reference authority and arbitrary posting-result
content remain separate acceptance work.


### Bank worklist read bindings (QA branch, not deployed)

For `review_statement_lines` and `review_card_transactions`, request reads now
check stored `lines[].id` and `_bank_worklist.rows` keys against the corresponding
business rows in the request entity. Statement-ID lists must resolve in that
entity too. Missing, foreign or malformed references withhold the request and
its thread before returned rows, counts and pagination. Present worklist/snapshot
containers must have the expected object/array shape; absent legacy metadata
remains supported. Responses inherit the originating request action.

Linked GL/posting transaction IDs use the existing transaction-read policy,
including stored transaction type and reversal ancestry. A fingerprint is not
authority and these read checks do not certify freshness, approval or completion.
The checks do not introduce a new Bank permission or repair historical records.
Free-text classification remains separate acceptance work; hosted identity and performance acceptance
remain open.


### Bank snapshot parent bindings (QA branch, not deployed)

Creating or revalidating a Bank review snapshot requires the statement line and
its statement to name the same bank account. Card rows must reference a program
in their entity; explicitly configured funding and card bank accounts must also
resolve in that entity. Optional account references may remain absent. A broken
explicit reference is not treated as an unconfigured optional account.

An inconsistent row is refused before a new fingerprint is returned. Investigate
the source and configuration through authorized workflows; do not retag records,
change old fingerprints or bypass the refusal to force a retry. This correction
does not repair historical data or certify the read authority of previously
stored request narratives. Existing status/dispute and response gates remain.


### Historical Bank review parent authority (QA branch, not deployed)

Historical Bank review reads now also validate each row's stored parents. A
statement line must resolve to a statement in the request entity and use that
statement's bank account; the account must resolve in the same entity. Card
rows must resolve to a program in the request entity, and every explicit funding
or card-bank account must resolve there. Standalone statement-ID lists apply
the same account check. Absent optional program accounts remain supported.

These checks apply before request/thread rows, totals and pages, including
response metadata. They validate identity and entity authority, not current
operational eligibility: archived, voided or disputed history is not hidden
merely because it cannot be executed again. Arbitrary narratives, hosted identity acceptance and representative performance
remain open. No historical data is repaired by reading it.


### Linked re-ask request authority (QA branch, not deployed)

Admin/MCP stored request reads follow explicit `reask_of_request_id` values in
request and response metadata. Every reachable request and its thread siblings
must pass the existing source/domain/ownership checks in the same organization
and entity. Missing, malformed or forbidden links withhold the request/thread
before rows, totals and pagination. Readable self-links and mutual cycles are
supported: traversal deduplicates visited stored rows rather than expanding the
SQL builder recursively. Virtual execution metadata uses the same policy even
when it has no request ID or thread columns.

This validates stored read authority, not whether a re-ask completed successfully
or whether free-text narratives are safe. It does not repair references. Use
authorized source/configuration recovery rather than editing history to force a
read. Hosted identity, representative performance and arbitrary narrative
acceptance remain open.


### Bill draft active-request authority (QA branch, not deployed)

When `review_bill` metadata names a draft/revision, Admin/MCP request reads also
follow the draft's stored `active_request_id`, when present. The linked request
and every reachable thread/re-ask/draft request must remain readable in the same
organization and entity under existing domain and ownership checks. Missing,
foreign or forbidden links withhold the review/thread before rows, totals and
pages. Response metadata inherits the originating review action.

Readable self/mutual cycles and absent optional active-request links remain
supported. Unrelated actions do not acquire bill-review semantics merely by
carrying a `bill_draft_id` field. These are read checks, not current-revision
approval or posting authorization. Do not change historical pointers to bypass
a refusal; use authorized case recovery. Source-attachment graphs, arbitrary narratives and hosted/performance acceptance
remain open; the bounded draft workflow graph is described below.


### Bill draft workflow authority (QA branch, not deployed)

Bill-review request reads follow a stored draft's optional `workflow_id`. The
workflow and its definition must belong to the request organization, and its
resolved entity must match the request. Existing workflow domain, payroll and
stored-transaction checks apply; a payload hint cannot replace the stored
transaction's authority. Missing, foreign, malformed or forbidden workflows
withhold the review and its reachable thread before totals or pagination.

The shared graph also checks workflow payload request references and stored
object-link metadata. Transaction links must resolve in the same entity under
the reader's existing transaction permissions; payment-batch links retain the
existing batch policy. A producer `metadata.bill_candidate` stamp follows its
`draft_id` and `revision` through the same draft checks. Readable self/mutual
request/draft/workflow cycles terminate without being denied merely for cycling.
Response review metadata and virtual execution metadata use the same rules.

These are historical read-authority checks, not approval, current-revision or
posting authorization. They neither change stored pointers nor repair workflows.
Other object-link families retain their existing domain checks; this does not
certify every nested reference, source attachment or free-text narrative. Hosted
identity and representative performance acceptance remain open.


### Investigation request saga authority (QA branch; not deployed)

A stored `reconciliation_agent` request with action `investigate_purchase` must
reference a saga in the same organization and entity, with type
`reconciliation_evidence_v1` and the same checkpoint purchase ID. Current AP and
purchase-owner read rules still apply. Missing, malformed, foreign or differently
bound saga references withhold the request/thread before rows, totals and pages.

The shared graph checks supported saga checkpoints, phase metadata, linked
instances and retained references. A readable request cannot make a forbidden
descendant readable. Readable completed history and self/mutual/mixed cycles
remain supported; the active-status check used when retrying an investigation
is not a condition for reading its history. Settlement-review requests retain
their separate producer contract and do not acquire a required saga ID.

These checks neither resume a saga nor approve settlement. Do not change stored
references to bypass a read refusal. Additional unmapped metadata, arbitrary
narratives, representative performance and hosted identity acceptance remain
open. Isolated SQL validation covers this implementation; merge and deployment remain pending.


### Delegation parent read authority (QA branch, not deployed)

Admin/MCP request reads follow stored `parent_request_id` and the reserved
`original_triage_request_id` in request/response metadata. For the installed
`resolve_configuration` action, `original_config_request_id` must resolve to a
configuration request. An action payload without that binding is withheld;
response references inherit the originating action. Other actions do not acquire
a meaning for similarly named configuration fields.

Each reached parent must belong to the current organization and request entity,
and pass its existing domain, stored-reference and thread-sibling checks.
Missing, malformed, foreign or forbidden parents withhold the child before
rows, totals and pages. The same rules apply to supported virtual execution
metadata. Stored and triage parent fields remain optional when absent; empty
responses remain valid. Deduplicated traversal terminates readable mixed cycles
without granting access through a forbidden member.

Completed parents remain readable when their current authority permits it. These
read checks do not certify fingerprint freshness, outcome completion, routing
correctness or permission to resume a parent. Existing mutation/recovery checks
still apply. Other producer reference fields, arbitrary copied text and hosted
identity acceptance remain open.


### Bill recovery payload read authority (QA branch, not deployed)

The Bill-only `fix_default_expense_account` action requires `ap:read`, including
when its original payload is absent. Its optional existing/returned profile
references use the same entity checks as other posting-profile requests.

For `review_bill`, `create_posting_profile` and `fix_default_expense_account`, a
non-null `original_email_payload` requires AP read access and must be an object.
Its explicit legal-entity hint must match the request. The copied payload is
also traversed through the shared, deduplicated execution-reference graph:
recognized nested transaction, workflow, request and outcome references retain
their existing stored authority. A nested payroll reference therefore needs the
applicable payroll read grant as well as AP access to the enclosing Bill task.
Responses inherit the originating action. These checks precede task rows,
counts, pages, sibling visibility and supported virtual execution metadata.

Absent/null optional originals remain supported. Generic posting-profile tasks
without a copied Bill payload keep their existing policy; unrelated actions do
not acquire these field meanings. Readability is not permission to retry or
proof that configuration is repaired. Raw prose, attachments, source email/upload
identity and other source fields not covered by the existing graph remain outside
this bounded verification. Other copied-payload producers and the no-action
missing-GL escalation still need explicit producer binding and hosted acceptance.


### Copied Bill card-source ownership

For the known Bill recovery actions above, an optional
`original_email_payload.card_transaction_id` must resolve to a stored card
transaction in the request entity and satisfy the caller's current card ownership.
The check applies to request and response originals; responses inherit the
originating action. Ordinary memberships cannot expose another employee's or
unowned sources. Broad stored roles retain same-entity access; trusted MCP system
callers retain entity/task scope. Missing, malformed, overflowing and cross-entity
IDs fail closed. This read check does not authorize receipt submission or posting.
Email/upload identity, attachments and untyped prose remain separate open scopes.


### Copied Bill upload-source authority

Known Bill recovery originals carrying `bill_upload_id` must resolve to a stored
upload in the request entity. If the upload links a transaction, that record must
exist in the same entity with type `AP_INVOICE`; a payroll or other transaction
type cannot impersonate the upload's posted bill. AP read access remains required
for the enclosing copied Bill payload. Unposted uploads remain readable, without
requiring a retryable status or an active workflow. Request and response originals
use the same checks. Missing, malformed or foreign references withhold the task.
These checks do not authorize upload retries, posting or cleanup. Provider email
and attachment references use the separate source-binding rules below.


### Bill vendor-delegation originals

The installed Bill vendor delegation uses `action=create_vendor`,
`request_data.source_table=bills` and `metadata.original_email_payload`. When that
original is present, Admin/MCP request reads traverse it through the same Bill
recovery authority checks: AP read permission, object/entity validation, stored
card/upload identity and recognized nested execution references. Response metadata
inherits the originating Bill producer binding. The shared graph deduplicates
visited nodes; a forbidden nested reference withholds the request and its thread.

Absent/null originals remain compatible. Other vendor producers do not acquire
Bill semantics solely because they contain similarly named metadata. This does
not approve vendor creation, callbacks, posting or raw copied narrative. Named
provider email and attachment references use the source-binding rules below.


### Manual-upload attachment binding in copied Bill payloads

When a known Bill recovery original names `bill_upload_id`, any copied attachments
must be an array of objects carrying a nonempty storage key or URL. Each supplied
key/URL must match an attachment on the upload's retained `bill.upload` event in
the same organization and entity. The event's upload ID and stored attachment key
must also match the upload record. A key and URL cannot point to different files.
Key-only and URL-only references remain valid when the stored binding proves them.

Absent/null/empty attachment lists retain prior behavior. These checks do not
require the upload or event to remain active and do not approve reprocessing.
They apply through response copies and the nested Bill vendor-delegation mapping.
Provider email and card-receipt attachment producers have separate bindings and
are not certified by this manual-upload check. Raw attachment descriptions and
other copied narrative remain outside this identity validation.


### Copied card-receipt source binding

Known Bill recovery originals marked `source=card_receipt_submission` require a
readable card transaction and a nonempty attachment array. Each attachment's
supplied key or URL must match both a current receipt row for that card/entity
and a retained `card_submit_receipt` / `bill.upload` event in the same organization
and entity, with the matching payload source and card ID. The receipt key must
belong to that card's organization/entity storage namespace, without dot traversal.

The stored R2 reference may retain its historical bucket; current configuration
does not invalidate a proven historical event. Explicit key/URL disagreement,
missing records, substituted files and wrong event bindings fail closed. The
checks apply through nested Bill vendor originals and response copies. They do
not require an active processing status or authorize submission, settlement or
retry. Provider-email sources use their separate binding rules below; arbitrary
copied narrative remains open work.


### Generic event reads and employee mail

MCP `agent_event` list, count, pagination, single-get and batch-get reads enforce
the caller's organization, allowed entities and any task entity. Null-entity
events remain readable only with organization-wide entity scope and no task
entity restriction. Human callers need stored organization membership. Stored
owner/admin/accountant/viewer roles retain broad mailbox access within that scope.
Other human roles see pinned Expenses/Receipts mail only through their stored
login or linked employee work email, including sender, recipient and thread
checks used by Communications. Caller-supplied role/email labels do not widen
access. Trusted agent callers retain system behavior within entity/task scope.
This does not certify arbitrary non-mail event payloads or copied narrative.
Named provider-email sources inside recovery requests use the rules below.


### Copied provider-email recovery sources

Known Bill recovery originals that name a provider `email_id` must resolve to a
retained `email.received` event from Resend in the same organization. The source
must belong to the request entity, or be an organization-wide null-entity email
readable by the caller. MCP applies its effective entity/task scope; Admin checks
stored membership and active, unexpired role scopes for organization-wide access.
Owners/admins bypass role scope only, not the membership entity ceiling.

Pinned Expenses/Receipts sender, recipient and thread ownership still applies.
An AP grant or caller-supplied email does not authorize another employee's mail.
Each copied attachment key or URL must match the same stored event attachment;
key/URL disagreement, malformed entries and missing sources fail closed. Stored
`resend://` fallback references remain valid without fetching remote content.
Missing/empty attachment lists remain supported. This validates named source and
file references, not arbitrary copied narrative. Other source producers retain
their own contracts; hosted acceptance and representative performance stay open.


### Retained provider-mail content

For named provider-email originals, supplied message identifiers, sender/recipient
headers, subject, received timestamp, text/HTML bodies and reply headers must
match their retained source values. Supplied attachment filename, content type
and size must match the same attachment that proves its key/URL. Omitting a field
remains supported; changing a supplied field is not treated as source proof.
The Bill intake and recovery path preserves these original fields unchanged.

This comparison does not apply to mutable routing, classification or review
metadata, and does not certify arbitrary added narrative. Review overrides remain
separate from the preserved original email. No retry, posting or cleanup action
is authorized by these read checks.


### Generic event payload domain checks

MCP `agent_event` list/count/page, single-get and batch-get now apply the shared
request/execution domain policy to event payloads as well as the existing
organization, entity, task and mailbox policy. Named transactions must exist in
the event entity and be readable under their stored type; supplied type labels
do not override that authority. Recognized nested results and linked request or
workflow references use the existing cycle-safe graph. Missing or mismatched
references fail closed, including for wildcard callers where existence and
entity binding still apply.

Admin event operations retain their existing admin-role gate. Provider-email
source binding continues to use the mailbox-only predicate to avoid recursively
constructing the domain graph. This does not certify arbitrary narrative or
unmapped producer fields and retained import-run bindings; those
remain open QA coverage. Read permission does not authorize retries or mutations.


### Transaction import event references

Generic MCP reads of retained `import.completed.transaction` and
`import.completed.opening_balance` events from `import_executor` validate every
ID in `created_ids` and `updated_ids` against stored transaction type and the
event entity. Opening-balance import IDs refer to `OPENING_ENTRY` transactions.
The event type must agree with its payload object type; both arrays must be
present and contain positive integer IDs. Malformed, missing, foreign-entity or
unauthorized references hide the event on all generic read surfaces.

This changes event reads only. Transaction update-on-duplicate remains unsupported
and skipped by the importer; validating hostile updated arrays does not add update
support. Binding the event to its retained import record remains open coverage. Import execution and recovery permissions are unchanged.


### Master-data and card import event references

Import completion events for customers, vendors, employees, accounts, items,
dimension types/values, fixed assets and card transactions validate both ID
arrays using the installed registry's read permissions and record keys. Effective
views use master IDs, not entity-assignment IDs. Entity records must match the
event entity; dimension types belong to the caller's organization. Every supplied
ID must resolve, even for wildcard callers.

Card IDs additionally use stored employee ownership: ordinary members can read
their own employee's records, while the existing broad membership roles retain
their wider access. Caller-supplied role labels do not grant that access. The
existing event payload domain, organization, entity, task and mailbox checks also
apply. Unknown importer types, mismatched event types and malformed arrays fail
closed. This checks referenced record access; it does not yet prove the event's
binding to a retained import run or certify arbitrary copied narrative.


### Agent visibility — deployed 2026-10-20

The approved replacement separates agent-output visibility from business-action
permissions. Role and direct-user grants are additive; owners/admins retain
organization/entity-scoped defaults. Non-admin users start with no grants.
Access includes historical and future outputs, including sensitive payroll data,
but does not authorize payroll records or business actions.

The deployed implementation provides Roles → Agent access and Agent → Access over one
grant store with audited changes. Reader integration shipped with PR403; production rollout was verified on 2026-10-20. The canonical workflow
and permissions plan tracks producer scope, reader parity, tests and rollout.


General agent
runtimes have organization-wide data authority, so their output scope includes
all tenant entities even when a run has a single display entity. A reader must
cover that entire scope. Entity labels do not narrow runtime authority. A verified
task host can record its bound entity scope; once a run has broader retained
content, retries cannot narrow it. These checks do not change business-action
permissions.

New runs record scope at publication. Runs retained from before the migration
remain unclassified on resume and are not automatically granted visibility.
Saga owners are explicit at creation; publishing a classified child's output adds
its entity scope to the saga. An unclassified child invalidates the parent's
classification until retained content is explicitly reviewed. The reviewed run-history repair on 2026-10-20 restored 2,203 runs; other retained
artifact types still require their own ownership review.

In production, Dashboard run list/detail predicates and
MCP run get/list/count predicates now use the shared grant and certified-scope
check. Dashboard definition statistics, recent runs, run metrics, pipeline history
and usage summaries also filter runs before returning activity or totals. An
authorized run output does not require an additional payroll domain grant.
Existing business-action checks remain separate.


### Assignment and auxiliary readers — deployed 2026-10-20

The deployed implementation applies the shared grant/scope check to saga pages,
phase counts and child runs. A visible parent does not reveal a child owned by an
ungranted agent. Phase numbers remain stable action identifiers; hidden dependency
links are omitted. Event and memory reads use the same grant store. New event and
memory publications record a stable installed agent and conservatively cover all
organization entities. Unassigned events, unknown owners and retained unclassified
rows stay hidden; ordinary retries do not classify legacy content.

Task/request content follows the current assigned user or stored role, plus scoped
owners/admins. This includes copied payroll content; assignment does not authorize
underlying payroll records or actions. The latest clarification-round assignment
controls access through earlier task URLs. Reassignment removes former-assignee
access. Dashboard inbox/count/detail and MCP task/request queries apply this rule
before pagination. Live business-record enrichment still needs business access.
Storage task/draft previews require a readable linked request; the business record
and attachment permissions remain separate. Generic saga creation by a human
requires stored owner/admin membership and an explicit `owner_agent_type`; a worker
uses its authenticated installed agent identity.

These changes are deployed through PR403. Real Auth0 browser verification and the
approved 20-reader capacity profile passed locally with JIT on and off. The
60-reader overload failed; full production workload capacity is not certified.
Legacy artifacts beyond the reviewed runs remain open. See the canonical
workflow/permissions plan for deployment and recovery evidence.

In production, refreshed run/saga/definition pages hide cached
content after an access refusal. Temporary server errors may retain the loaded
view. Revocation applies on the next read and cannot retract copied/downloaded
outputs. Real Auth0 login was verified against synthetic local authorization fixtures;
production identities were unchanged. Deployed acceptance remains separate.


### Restored historical run visibility — 2026-10-20

The initial rollout hid older runs because their visibility metadata was absent.
An audited repair restored 2,203 runs after checking stored agent ownership, tenant
legal entities and event provenance. The signed-in production activity page showed
1,471 runs for Arfiti Technologies OU and an existing run detail opened successfully.
Thirty-nine runs with missing event provenance remain hidden for separate review.
No agent grants, business permissions or financial records changed. The simple
indexed read policy remains in place. This repair does not classify legacy sagas,
events, memory, tasks or requests.


### Extended historical visibility recovery — 2026-10-20

An explicitly authorized, audited metadata repair restored 73 sagas and 383 phases,
2,360 events, 379 requests and 118 workflow tasks in production. Stored agent and
tenant ownership, child-run ownership, task workflow/assignee membership, and
request creator/owner/parent bindings were checked. Bill sagas additionally matched
their saved response-attempt/request links; reconciliation sagas matched their
purchase/run records and phase bindings. Month-end sagas matched the reviewed
producer contract, installed owner and executed child phases. Scope conservatively
covers verified tenant entities. Read policies, grants, assignments and business
permissions were unchanged; no financial work was executed.

The remaining 39 Master Data runs reference neither a retained trigger event nor
a retained request at their saved request ID. They remain hidden. Also excluded:
3,231 events without a stored installed-agent owner and 41 requests without a
verifiable creator or owner. Do not guess ownership from names or narrative.
Historical memory/conversation classification was not part of this repair.

Signed-in production verification for Arfiti Technologies OU showed 51 sagas,
1,318 events, 321 requests and 26 pending inbox tasks. A restored request detail
opened successfully; no response or business action was submitted.


### Memory and further provenance recovery — 2026-10-20

Explicitly authorized production repair restored 472 memory entries, another
169 events and 2 requests. Memory ownership used the stored installed agent
namespace and verified every recorded creator/updater run against that agent,
tenant and existing classified visibility. The events had no stored agent type
but had reciprocal event-to-run and run-to-event links, matching tenant/entity,
and a classified run with an installed owner. The two manual requests had valid
member assignees and typed source records in the tenant schema with matching
entity IDs. No owner was inferred from a narrative, key name or display label.

Remaining hidden: 39 runs with missing event/request provenance, 3,062 events
without reciprocal classified owners, 39 requests without sufficient source or
assignment evidence, and 103 memory entries. Memory exceptions comprise 29
namespaces that are not installed agents, 32 missing creator runs and 42 entries
whose creator agent differs from the namespace. Those need additional provenance
or an explicit ownership decision; no ownership/assignment relabeling was done.

Conversation audit found no separate conversation table and zero stored
`agent_task_messages`. All 60 response attempts reference same-tenant requests
and classified thread roots. Their timeline access remains governed by existing
request/current-assignment policy; no conversation grants or synthetic ownership
records were added. This does not claim that deleted conversation history exists.

Ten isolated ownership/source tests and the rollback-only rehearsal passed.
Application required the reviewed manifest digest; repeat audit found zero more
eligible records. Existing scoped access-denial checks passed. The signed-in
production Memory page showed 305 entries for Arfiti Technologies OU. No reader
query, permission, grant, assignment or financial record changed.


### Recent-memory verification and historical exclusions — 2026-10-21

The user accepts keeping old closed history hidden. Do not delete it or infer
ownership to restore it. A focused audit of hidden memories created or updated
since October 13 found three records: two created October 19, and one older
record updated October 20. All three were restored after confirming the existing
`validate_namespace` permission for Bill Processor `vendor_mapping:` writes to
Bank Transaction Processor, the installed namespace owner, every recorded writer
run and entity scope. Writer identity need not equal the namespace owner when an
explicit existing cross-agent rule permits that write. No new permission was added.

Rollback rehearsal and actual administrator/denied-scope checks passed. The final
query found no hidden memories created or updated in that window. One hundred
older memory entries remain hidden; this does not mean they have expired.


### Pipeline submit receipts (1.1.0, local/unreleased)

`submit_workflow` 1.1.0 uses the shared gateway's durable submission receipt after
standalone validation. Repeated identical intent returns recorded outcomes;
unknown or in-progress attempts require reconciliation and cannot be retried as
new effects. A pending workflow or a claim is not proof of financial completion.
A new business operation needs a distinct legitimate reference, not a changed
field intended to bypass an uncertain earlier attempt. Do not delete claims.

The retained 1.0.0 block remains available under its original hash; it still has
its historical outer-guard limitations. Review and activate pipeline revisions
through supported release controls to adopt 1.1.0. Do not edit saved version/hash
pins or assume installing code has upgraded an existing pinned pipeline. No
production activation is included in this implementation.


### Connection-owned response resolution

An internal resolution already running on an owned connection checks persisted
Bank enrollment through that same connection before request locks. It does not
require a separate global pool or treat an unavailable pool as legacy authority.
An enrolled Bank request still requires its dedicated lifecycle transaction; a
non-Bank bill clarification can proceed when its undispatched draft has no
posting receipt. Dispatched bills and malformed receipt evidence still refuse.


### Locked tax period and uncertain posting outcomes

The existing pre-executor tax-period check returns the stable refusal code
`tax_period_locked`. Its lock applicability and dates are unchanged. For a
reviewed bill, a definitive refusal is recovered from the exact saved workflow
and unposted candidate evidence; retrying the same request retains that refusal.
Correct the underlying condition and use the supported candidate revision flow.

A raw execution exception or unavailable submission receipt is not proof of
no financial effect. Such cases remain `posting_unknown` until saved evidence
resolves them. A saved dependency child can be recovered without dispatching a
second child. Sender trust is recorded only after a verified posted bill.

### Receiving-address creation contract

`entity_email.create` accepts the currently provisioned mailbox types `bills`,
`invoices`, `payments` and `receipts`, as well as legacy `ap_inbox`, `ar_inbox`
and `general`. Discover the live schema through `get_submissions(action="schema",
object_type="entity_email", operation="create")` before submitting. Creating a
record configures routing; it does not configure provider DNS, verify delivery,
or create a linked alias. Use the same entity, agent and routing rules when
provisioning a replacement destination. Existing addresses are not overwritten.

The current table has no verification-token columns. Creation does not return an
`is_verified` assertion or require a token; verify actual provider-to-inbox
delivery separately. The legacy `entity_email.verify` operation still references
absent token columns and is not a supported delivery proof for this schema.

With provider forwarding, deliver to one destination rather than making a second
copy. A new SMTP delivery may receive a new provider message ID; retry protection
does not deduplicate independently sent copies across separate inbox records.

### Displayed primary receiving address

Entity details and Communications select one existing active inbound address per
mailbox type using the order of `INBOUND_MAIL_DOMAINS` (first domain preferred).
Row order no longer chooses the label. If a type has no address on the preferred
domain, its existing stored address remains visible; no address is invented.
Unlisted custom-domain addresses remain available as a fallback. Equal-priority
addresses are ordered lexically for stable display. This affects labels and copy
controls only: it neither changes routes nor disables legacy forwarding. To roll
back display preference, reorder the configured domains and redeploy. Provision
and verify a receiving route before making its domain preferred.

### Migration provisioning and membership safety (2026-10-28; release pending)

New company inbox setup uses configured mail-domain aliases, with the first configured domain preferred for display. Do not assume an address is available until its stored row and provider delivery have been verified. Conflicting entity/purpose ownership must be resolved explicitly, never reassigned during setup. Ordinary team-member update/removal and invitation acceptance preserve system-role memberships. Existing approval filters remain in force; no stored service identities are renamed by this migration cleanup.

### Closure reasons from failure and legacy completion writers (AR-476)

These writers now set or clear `closed_reason` / `closed_transition_id`
themselves; callers never supply them.

| Writer | Effect |
|---|---|
| Orphan sweep when the creating run fails (`_cancel_orphaned_requests`) | `cancelled`, `creator_instance_failed`, new transition id |
| Failure cascade to the run's originating request | `failed`, `originating_instance_failed`, new transition id |
| Legacy auto-complete after a successful run (`_auto_complete_agent_request`) | `completed`; closure pair cleared (run success is not verified domain evidence) |
| Linked-workflow bridge (`_complete_agent_requests_on_workflow_complete`) | approved/rejected status; closure pair cleared, same reason |
| Payment bank setup recheck | `payment_bank_eligibility_rechecked` or `declined_by_respondent`; hold/unresolved stays `in_progress` with the pair cleared |

Both completion bridges write only when the request is still `pending`,
`in_progress` or `failed`, in the organization and at the `version` they read.
A cancellation, expiry, competing completion or question revision that lands
after the read is left untouched and no completion callback is emitted. Each
bridge commits its status change and its `agent_request.completed.*` callback
event in one transaction, so a failed callback insert rolls the completion back
and a retry publishes once. The workflow bridge handles linked requests in
agent-instance order, each in its own savepoint: a failing link is logged at
warning level with the workflow and agent instance ids, rolls back only its own
completion and callback, and the remaining links are still attempted. Bridge
errors never fail the workflow itself. A completion skipped because the request moved on is logged
at info level with the request id and the version read.

These reasons describe orchestration outcomes. `creator_instance_failed` is not
a human rejection and does not mean financial effects were reversed;
`payment_bank_eligibility_rechecked` is not a payment approval. A linked
workflow alone is not proof that the current question is answered, and the
bridges do not bind a workflow to the request revision at its original
submission. Existing rows are not backfilled: a NULL pair still means unknown.
