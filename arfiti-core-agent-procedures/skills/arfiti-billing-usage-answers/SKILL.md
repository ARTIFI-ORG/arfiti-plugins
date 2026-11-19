---
name: arfiti-billing-usage-answers
description: Turn a person's answer to a "provide usage data" task into recorded contract usage and a billing run for exactly those contracts, through the Arfiti MCP tools - read the task and the answer, map each figure to a metered contract line, record it with submit(object_type="contract_usage", operation="record"), then submit(object_type="billing_run", operation="execute") for those contracts. Never invents a quantity. Use when a usage-data task has been answered.
---

# Record usage from an answered task and bill it

The billing run stays a governed operation (`billing_run.execute`, which
catches up periods and posts the invoices). When usage cannot be read anywhere, a
person is asked for it (a `provide_usage_data` task). This skill reads the
answer and records it, through public operations.

Tools: `query`, `get_entity`, `get_guidance`, `get_organization` (read:
`get_info`), `read_attachment`, `generate_report`, `get_submissions`,
`submit`.

## Rules that never bend

1. **No invented figures.** A quantity is recorded only when the answer
   states it for an identifiable contract and period. An unclear answer is a
   question back, once.
2. **Only the contracts in the task.** Record and bill only those; never run
   billing for the whole entity from this skill.
3. **Idempotency and read-back.** Keys: `usage-<request id>-<contract line id>`
   and `billrun-<request id>`. A definite refusal (`refused: true`, `effect_outcome: "no_effect"`, `reason_code`,
   `message`) saved nothing: when the records let you remove the cause it names,
   remove it and submit once more under a new key (the key plus `-r2`); otherwise
   report it verbatim with its `reason_code` and `workflow_id`. A `posting_unknown`
   (`effect_outcome: "unknown"`, often with `failure_reason`) is not proof that
   nothing was saved: read the target back first. Changed: it took effect.
   Unchanged: act on `failure_reason` as for a definite refusal (new key), or
   report it with its workflow id. The same key only replays the first answer;
   never resubmit with an invented value. Configuration values are read with
   `query("config_setting", filters={"config_key": ..., "legal_entity_id": ...})`,
   not asked for.

## Step 0: confirm the organisation and entity

As in the other skills; otherwise `status: wrong_scope`.

Rules: `query("agent_definition", filters={"agent_type": "billing_run_agent"})`
and `get_entity("agent_definition", id)` for its `managed_agent_rules` text,
plus any `client_rules:` in the first message. Other `config` keys are
a product default, the same for every organisation and chosen by no client: not the client's policy, not read.

## Step 1: read the task and the answer

`get_entity("agent_request", <request id>)` (or
`query("agent_request", filters={"status": ...})` for answered
`provide_usage_data` tasks): `request_data` (billing date, run number, the
contracts with their periods and units) and `response_data` (the answer).

## Step 2: map the answer

For each contract in the task: `get_entity("recurring_contract", id)` and its
metered lines (related `usage` / lines). From the answer, take the quantity
per line, the unit and the period. Check the unit against the line's unit of
measure; a different unit is a question, not a conversion you choose.

## Step 3: record usage

`get_submissions(action="schema", object_type="contract_usage",
operation="record")` once, then per line:

```
submit(object_type="contract_usage", operation="record", data=JSON.stringify({"contract_line_id": L, "quantity": Q,
  "usage_date": "<last day of the period>", "usage_period_start": "...",
  "usage_period_end": "...", "legal_entity_id": X, "unit_of_measure": "...",
  "source": "usage_task", "external_reference_id": "<request id>"}),
  validate_only=true)
```

then for real. Read back the usage record.

## Step 4: bill those contracts

```
submit(object_type="billing_run", operation="execute", data=JSON.stringify({"legal_entity_id": X,
  "billing_date": "<from the task>", "contract_ids": [<the task's contracts>]}),
  validate_only=true)
```

then for real (`billing_run.preview` first if the organisation's rules ask
for it). Read back the run (`query("billing_run", ...)`) and the invoices it
created.

## Result

```
USAGE_RESULT
status: billed | recorded_not_billed | asked | wrong_scope | refused
organization_id: <id>   legal_entity_id: <id>   request: <id>
usage_recorded: <each: contract line, quantity, unit, period, id>
billing_run: <id, invoices created> | none (reason)
questions_asked: <n> - <each>
not_done: <the task's settlement: see below>
```

## Not part of this skill

- Settling the usage task itself: the public `agent_request.resolve` is
  accepted only from the run bound to that answer. Report the task as handled
  and leave its status to a person.
- Creating the usage tasks and tax-profile requests is part of the governed
  billing operation, not this skill.
