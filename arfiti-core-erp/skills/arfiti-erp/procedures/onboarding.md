# Organization Onboarding Procedure

Step-by-step procedure for setting up a new organization in Arfiti. Follow this exactly.

---

## When This Applies

Use this procedure when ANY of these are true:
- User says "set up my organization", "onboard my company", "initialize", etc.
- `get_onboarding(action="check_status")` returns `needs_onboarding: true`
- Organization has no legal entities yet
- Onboarding checklist shows incomplete tasks

---


### Authority for organization setup

Organization-wide setup requires **current owner or admin membership** in the
connected organization and **access to all entities**. The backend reads live
membership; a Controller, Viewer, role named Admin, stale owner token, or
`admin:write`/`config:write` grant alone does not qualify. Agent credentials cannot
perform these user administration operations.

This applies to `manage_onboarding` actions `start`, `run_wave`, `update_task`,
`reset`, `add_entity`, `initialize_entity`, and `load_demo_data`, plus template
repair and `legal_entity.create` / `legal_entity.rerun_onboarding_task` workflows.
They can seed shared accounting configuration, workflow/agent definitions and
credentials, so entity-limited administrators must ask an unrestricted owner or
admin to perform them. Ordinary entity-scoped accounting workflows are unchanged.

Onboarding status/checklist/summary, support and skill-download actions retain
their existing access rules. New organization owners can still run first-time
onboarding before the organization has any entities. Explicit organization IDs
must match the connected organization; initialization/copy targets must belong
to it. Omitting `organization_id` in the MCP initialization/demo gateway uses
the connected organization. Switching the Admin browser login does not change
the identity of an existing MCP connection.

A permission refusal must be resolved with the correct owner/admin connection,
not by retrying through another setup tool or resetting the checklist. After a
legitimate setup failure, inspect the checklist and retry only the failed task.

## CRITICAL RULES

1. **ALWAYS use `manage_onboarding(action="start")` then `manage_onboarding(action="run_wave")`** for first-time setup
2. **Do not create the first entity manually.** The legal entity is created automatically by the first onboarding wave (`create_organization` task).
3. **NEVER call `manage_onboarding(action="initialize_entity")` before `start`** — `initialize_entity` requires an existing `legal_entity_id` and will fail with a fiscal_periods FK error if the entity doesn't exist yet.
4. **NEVER use `manage_onboarding(action="add_entity")`** for the first entity — that action is ONLY for adding a 2nd+ entity to an already-onboarded organization
5. **Run waves while runnable tasks remain.** Completion requires every task to be completed or explicitly skipped. Failed tasks remain open: inspect the error, resolve it, use `update_task` to reset that task to `pending`, then retry; never reset populated company data to recover a failed task.
6. The wave runner handles everything automatically: legal entity creation, chart of accounts, tax codes, posting profiles, agents, skills, plugins, payroll, dimensions, and more

---

## Step-by-Step

### Step 1: Check Current Status

```
get_onboarding(action="check_status")
```

- If `needs_onboarding` is `false` → org is already set up. Ask what the user needs help with.
- If `needs_onboarding` is `true` → continue to Step 2.

### Step 2: Collect Company Details

Ask the user for:

| Field | Required | Example | Used by `start` |
|-------|----------|---------|-----------------|
| Country | Yes | EE, US, GB, DE (2-letter ISO) | `country_code` |
| Accounting standard | Yes | IFRS or US GAAP | `accounting_standard` |
| Tax jurisdiction | Yes | EU, US, UK | `tax_jurisdiction` |
| Fiscal year start month | Optional (default: 1) | 1 = January, 4 = April | `fiscal_year_start_month` |
| Is VAT registered? | Optional | true/false | `is_vat_registered` |

**Note on entity name/code/currency:** Wave 1 auto-derives these from the organization record and country_code. Entity name = org name, entity_code = country_code, currency = country-derived (EE→EUR, US→USD, GB→GBP). Collect these from the user only for confirmation/context — they are NOT passed to `start`.

### Step 3: Initialize Onboarding Checklist (creates the legal entity)

Do NOT create the legal entity first. The `start` action initializes the checklist; the first wave's `create_legal_entity` task auto-creates the legal entity from the organization record.

```
manage_onboarding(action="start",
    country_code="EE",
    accounting_standard="ifrs_standard",
    tax_jurisdiction="eu_vat",
    fiscal_year_start_month=1,
    is_vat_registered=true   # optional
)
```

**Parameters `start` actually accepts:** `country_code`, `accounting_standard`, `tax_jurisdiction`, `onboarding_path`, `fiscal_year_start_month`, `is_vat_registered`, `legal_entity_id` (optional — omit for first-time setup).

**Tax jurisdiction values:**
- Estonia/EU → `eu_vat`
- United States → `us_sales_tax`
- United Kingdom → `uk_vat`

**Accounting standard values:**
- IFRS → `ifrs_standard` (also accepts UI value `IFRS`)
- US GAAP → `us_gaap_standard` (also accepts UI value `GAAP`)

**What Wave 1 uses for the legal entity (no way to override today):**
- `entity_name` ← `organizations.name` (the name collected during org signup)
- `entity_code` ← `country_code` (e.g., `EE`)
- `functional_currency` ← derived from country (EE → EUR, US → USD, GB → GBP, etc.)

If the user wants a different entity_name or entity_code (e.g., "AHG-EE" instead of "EE"), they must update the org name first or edit the entity after onboarding completes — do NOT pass `entity_name`/`entity_code`/`base_currency` to `start`; those parameters are ignored.

This creates ~34 onboarding tasks organized in dependency waves.

### Step 4: Run ALL Waves Until Complete

```
manage_onboarding(action="run_wave")
```

After each wave, check progress:

```
manage_onboarding(action="get_summary")
```

**Keep calling `run_wave` until `progress_pct` = 100.** Typical setup needs 3-5 waves.

A wave advances one legal entity's checklist. When more than one entity has open onboarding tasks, `run_wave` needs the entity, `manage_onboarding(action="run_wave", legal_entity_id=12)`; without it the call runs nothing and lists each entity with its open task count. Follow the call each answer's message names: when this entity has nothing runnable left, it names the other entity's call.

If a task fails, inspect and resolve its error, reset only that task to `pending` with `update_task`, then run another wave. Do not assume the failure is transient or repeatedly run a blocked wave.

### Step 5: Verify Setup

```
get_onboarding(action="check_status")
```

Should return `needs_onboarding: false` with complete `setup_info` including:
- Legal entity details
- Agent email addresses
- Enabled agents

### Step 6: Inform User About Next Steps

Tell the user:
1. ✅ Organization is fully set up — list what got provisioned (COA count, fiscal periods, tax codes, agents seeded)
2. **Agent email addresses** — list ONLY the emails with autonomous agent processing:
   - `bills.{entity}.{org-slug}@mail.arfiti.com` → bill_processor (forward vendor bills here)
   - `receipts.{entity}.{org-slug}@mail.arfiti.com` → expense_processor (forward expense receipts here)

   Do NOT list `invoices.*` or `payments.*` in the wrap-up. They exist in the DB but are manual/outbound utility addresses (invoices.* is for sending customer invoices; payments.* is a manual inbox for remittance advices). Listing them as "agent emails" confuses users because there is no agent behind them.
3. **Suggested next steps** — choose from:
   - Import vendors, customers, and employees (via CSV or manual entry)
   - If migrating from a prior accounting system: import opening balances — see [Bulk Import: Opening Balance](../resources/bulk-import.md#opening-balance-import)
   - Set up payroll employees and compensation
   - Configure projects, dimensions, or budgets

   Do NOT suggest:
   - ❌ "Download the skill from the admin dashboard" — the skill download link was already surfaced during onboarding (via the `generate_org_skill` task). Don't re-prompt for it.
   - ❌ "Add bank accounts (bank connectors available)" — don't push connectors unprompted during onboarding. Revolut Business is the bank connectivity, and it is set up from the admin dashboard's connector wizard (certificate + consent), not from chat. Only mention it if the user explicitly asks about bank integrations.

---

## Adding a Second Entity (DIFFERENT Procedure)

**Only after the org is fully onboarded** (`check_status` returns `needs_onboarding: false`).

### Step A: Collect ALL entity details BEFORE calling add_entity

`add_entity` does NOT have a post-hoc update path for VAT/tax_id — those fields are only set correctly when passed at creation time. Do not call `add_entity` until you have every answer below.

Ask the user for:

| Field | Required | Example |
|-------|----------|---------|
| Entity legal name | Yes | "Hala Digital OÜ" |
| Entity code (short, unique in org) | Yes | "HALA-EE" |
| Country | Yes | EE, US, GB (2-letter ISO) |
| Currency | Yes | EUR, USD, GBP (3-letter ISO) |
| VAT-registered? | Yes | true / false |
| Tax ID / VAT number | Conditional (required if VAT-registered) | "EE101980223" |

If the user doesn't know the VAT number yet but will be registered, pass `is_vat_registered=true` with `tax_id="PENDING"` — the record can be updated later via `submit(object_type="tax_registration", operation="update", data=JSON_STRING)` or the admin dashboard.

### Step B: Call add_entity

```
manage_onboarding(action="add_entity",
    entity_name="Hala Digital OÜ",
    entity_code="HALA-EE",
    country_code="EE",
    base_currency="EUR",
    is_vat_registered=true,
    tax_id="EE101980223"
)
```

This reuses the org's existing chart of accounts, tax codes, agents, and posting profiles via MSEO. Only creates entity-specific items (fiscal periods, number series, emails, exchange rates, and an `entity_tax_registrations` row if `is_vat_registered=true`).

### Step C: Updating a legal entity after creation

Safe fields updatable via `submit(object_type="legal_entity", operation="update", data=JSON_STRING)`: `entity_name`, `tax_id`, `country_code`, `address`, `is_active`, `metadata`.

```
submit(object_type="legal_entity", operation="update",
    data='{"entity_id":37,"entity_name":"Hala Digital OÜ (renamed)","tax_id":"EE101980223"}')
```

**NOT updatable via this executor** (intentionally blocked — would invalidate existing data):
- `entity_code` — referenced by agent emails, number series, reports. If the code is truly wrong, deactivate and create a replacement entity.
- `functional_currency` / `reporting_currency` — transaction amounts are already stored in this currency.
- `entity_type` / `accounting_standard` — structural; affects consolidation and COA.

**VAT registration** goes through `submit(object_type="tax_registration", operation="create", data=JSON_STRING)` / `tax_registration.update`, NOT `legal_entity.update`. The `legal_entities` table has no `is_vat_registered` column — VAT status lives in `entity_tax_registrations`.

---

## Troubleshooting

### "Organization has not completed initial onboarding"

If you get this error from `add_entity`, it means the org hasn't been set up yet. Use this procedure (Steps 1-5) instead.

### Waves stuck at less than 100%

Check which tasks are blocked:
```
get_onboarding(action="get_checklist", status="failed")
get_onboarding(action="get_checklist", status="pending")
```

Resolve the failed task’s cause, then use manage_onboarding(action="update_task", task_key=THE_FAILED_KEY, new_status="pending") before running another wave. Pending tasks may have unmet dependencies; inspect get_summary instead of repeatedly running a blocked wave. Do not reset populated company data.

### User already created entity via admin dashboard

If a legal entity exists but the checklist was never initialized, call `start` with `legal_entity_id=<existing_id>` and the wave runner will detect existing data and skip tasks that are already done.

### "No executor registered for 'legal_entity.create'"

The current code registers a legal_entity.create executor. This error can indicate an older deployment or a missing workflow/executor configuration; inspect the deployed schema and setup status before retrying. For first-time assistant-led setup, use start and run_wave as described above. The Admin wizard has its own entity-create/setup flow. Do not create a duplicate entity or bypass authority to recover this error.

### "fiscal_periods_legal_entity_id_fkey" FK error from initialize_entity

You called `initialize_entity` before the legal entity was created. Do NOT call `initialize_entity` before `start`. Use `start` to initialize the checklist, then `run_wave` to execute runnable tasks. Inspect the existing entity and task state before retrying.

---

**Version**: 1.3
**Last Updated**: 2026-04-24

### Recovery and verification

Admin signup and MCP provisioning use shared database initialization for workflow definitions and subledger history. After deploying migration 623, an owner/admin can call `manage_organization(action="repair_template_data")` in their current company to repair missing initialization. Switch company first for a client company; cross-company repair arguments are refused. Existing/customized or inactive workflows are preserved, so intentionally inactive definitions need explicit review.

Check both `completed` and `skipped` counts. An empty migration task is skipped, not imported. An explicit null VAT configuration in the US template is not applicable and does not call an AI generator. A software failure must remain failed. Reports for periods before a repaired company's historical evidence boundary may remain unavailable; repair does not fabricate application history.

### After the final wave

Use the completion response with the user’s preferred connected assistant. Apply skill/instruction files through that client’s supported setup, using the Admin onboarding guide for details. Verify the chosen client connects to the intended organization; completed company setup does not certify that connection. Review any `needs_attention` items before relying on them.

The Admin finish summary uses the label Assistant. Its external Claude link appears only when the recorded path is Claude; IDE or unknown paths finish at the dashboard. Do not treat the finish-screen link or label as proof of a working connection.

Connection-step copy/download indicators describe local browser actions only. Changed instructions, organization URLs or replaced keys/configurations need copying again. A failure clears the corresponding success indicator; it does not revoke or create a key, verify installation, or change onboarding status.

Overlapping copy requests show feedback for the latest attempt. A login/error page returned by a skill/plugin download is rejected rather than reported as a downloaded archive; restore the browser session if needed and retry.


If Admin reports **Entities not loaded**, ask the user to retry the list read; do not infer that the organization has no entities or start duplicate setup from that message. The form disables currency selection when its catalog is unavailable: use Retry currencies after a read failure, or ask an administrator to investigate an empty catalog. Existing draft values are preserved; these browser states do not change MCP onboarding contracts.


Onboarding's **Entity refresh failed** means the displayed entity state came from the last successful read. Use **Reload** to refresh it without rerunning ledger tasks. **Retry currencies** reloads only currency choices and preserves draft edits; a full browser reload is unnecessary for that read failure. Neither action certifies setup completion or changes MCP contracts.

Admin configuration and record-page help offers ChatGPT, Claude, and a copyable
question for another assistant. The client choice does not install a connector or
change the MCP organization. Ask the user to paste the question into their
connected client and verify the current organization before record operations.
Clipboard refusal has a manual-copy fallback; it does not mean company setup failed.

Configuration company references such as ORG-0000002 are display labels, not API IDs; the underlying organization_id remains 2. The Admin connection wizard exposes ChatGPT, Claude and IDE setup paths. ChatGPT instructions use the company-pinned connector URL and OAuth; the selected path persists across reloads. Ask the user to select the installed Arfiti plugin in ChatGPT and request Check onboarding status, then confirm the returned company. The company connection timestamp may come from another client or user and does not verify this ChatGPT session. Workspace availability and live OAuth must be verified separately. The ChatGPT path offers neither IDE keys nor Claude skill/plugin downloads. The separate page-help link only opens the assistant destination.


The final wizard screen is **Review your setup**, labeled **SETUP REVIEW**.
Reaching it records navigation progress; it does not certify ledger completion
or the current assistant connection. Read the loaded entity/ledger/connection
facts and any failure or retry messages. A missing entity, running/failed ledger,
or failed finish save must be resolved through its existing setup/retry action.
The review heading stays neutral even when setup has completed.


The onboarding shell now uses the same company display reference as configuration:
ORG-0000002 for internal ID 2, followed by the organization slug. References are
padded to at least seven digits and never truncated. This is display formatting,
not a new random identifier or a change to tenant IDs, schemas, API arguments,
connector URLs, or organization selection. The shell still hides the company
line on the initial organization step.


### Claude plugin setup

In Claude, open Customize → Plugins → Add → Add marketplace and enter
`ARTIFI-ORG/arfiti-plugins`, or upload a downloaded plugin ZIP in the Plugins tab.
Plugins are available on Claude web and Desktop with a paid plan, subject to
workspace policy. Hooks, sub-agents and local MCP servers require Cowork or
Claude Code. Downloading a ZIP does not install or verify the plugin.

Provider instructions checked on 2026-10-16 against
[Anthropic’s plugin guide](https://support.claude.com/en/articles/13837440-use-plugins-in-claude).
Actual Arfiti marketplace access, installation and execution still require
verification in the intended client and workspace.


### Onboarding rename HTTP failures

The onboarding rename endpoint requires a JSON object with a string name; invalid
JSON or a missing/non-string name returns 400 before organization lookup or
workflow submission. Valid names are trimmed and checked against the existing
2–255 character rule. Unexpected failures return a generic 500 response without
exception details; the handler logs a static failure marker. Owner/admin and
unfinished-onboarding checks, workflow approval, and idempotency remain unchanged.
