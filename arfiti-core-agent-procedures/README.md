# arfiti-core-agent-procedures

The procedures Arfiti's own agents follow (bills, bank and card lines,
reconciliation, parties, configuration, expenses, period close, billing usage),
published so your own Claude, Cowork or agent can do the same work the same way
through the Arfiti MCP server. Your sign-in decides the organisation and what you
may do; every write goes through `submit`, under your organisation's workflows
and approvals.

The procedures are written for an agent: where one says "the first message",
"a brief" or "raise a task", a person working in Cowork gives that information
in the conversation and answers the question there. Where one hands work to the
master-data or configuration agent, follow that skill in this plugin yourself.

Generated from the agents' own procedures; do not edit by hand. To keep rules
of your own, write a skill of your own beside this plugin: an update replaces
edits made to an installed plugin.

## What it runs and sends

Skills only: no scripts, no hooks, no local servers. Accounts, tax codes, parties,
rules and documents are read live through the connector's read tools; nothing of
any organisation's data ships with the plugin. All data goes to the Arfiti MCP server
over the authenticated connector. The one exception is `arfiti-master-data`, which
may read a public company register named in its `REGISTERS.md` to confirm a party.

## Skills

| Skill | What it does |
|---|---|
| `arfiti-account-choice` | Choose the ledger account for one purchase in Arfiti - a card charge the bank agent posts or a line of a supplier bill - from the records, in a fixed order of authority (client rule, vendor default, vendor history, vendor notes, the chart of accounts), and say which evidence decided it. Use whenever a posting needs an expense, cost or asset account that the caller's skill does not already fix. |
| `arfiti-bank-statement-lines` | Settle one bank account's (or card programme's) unreconciled statement lines in Arfiti through the MCP tools - confirm a payment-batch line, post a bank entry or payment through submit anchored to the statement line and match it, or exclude a duplicate - in a fixed order of checks, never breaking a tie with a date or an amount, and reading the line back after every write. Use for every bank session. |
| `arfiti-bill-processing` | Process one incoming vendor bill in Arfiti end to end through the MCP tools only - read the document, find or delegate the vendor, choose accounts and tax codes from vendor defaults, history and the organisation's rules, check for a duplicate, validate, post through submit, attach the source document, and report. Use for every bill session. |
| `arfiti-billing-usage-answers` | Turn a person's answer to a "provide usage data" task into recorded contract usage and a billing run for exactly those contracts, through the Arfiti MCP tools - read the task and the answer, map each figure to a metered contract line, record it with submit("contract_usage", "record"), then submit("billing_run", "execute") for those contracts. Never invents a quantity. Use when a usage-data task has been answered. |
| `arfiti-configuration` | Resolve one accounting-configuration problem in Arfiti through the MCP tools - accounts, posting profiles, transaction-type posting links, fiscal periods, payment terms, tax codes, a confirmed entity time zone - by finding what exists, choosing the smallest change that only affects future postings, validating, submitting, and reading back. Refuses on its own to change anything that would reclassify or re-report posted history. Use for every configuration task, whether a session's own or a brief from another agent. |
| `arfiti-expense-check` | Check a submitted expense claim in Arfiti against the company's own written rules - gather the evidence for every line (rate tables, meal deductions, the employee's other claims and per diems for the same days, card charges, duplicates, missing receipts, the employee's own history), weigh it against each rule the company wrote, and either report nothing or raise one plain-language task for the employee that names the line, the rule and what to do. Holds no company or country policy, no amounts and no thresholds of its own. Never approves, rejects, holds, modifies or pays a claim. |
| `arfiti-expense-claim` | Build an employee's expense claim in Arfiti through the MCP tools - sort each receipt (company card, supplier invoice, paid by the employee, not usable), add reimbursement, mileage and per-diem lines with amounts from the server's rate tables, check for duplicates and per-diem overlaps, write a draft report and read it back, and submit it only when the person it belongs to says so. Used by an employee's own Claude in Cowork and by the expense agent. Never approves, posts or pays. |
| `arfiti-expense-processing` | The expense agent's own procedure in Arfiti. Mode receipt - a receipt arrives with no claim around it (expenses or receipts mailbox, app upload) - file it on its company card charge, list a supplier invoice for the bill agent, or start a draft claim for the employee who paid and ask them by task to check and submit it. Mode check - check each submitted claim against the company's own written rules and raise one plain-language task for the employee when something is against them. Builds claims with arfiti-expense-claim and checks them with arfiti-expense-check. Never submits a claim for an employee unless a company rule says so; never approves, rejects, posts or pays. Use for every expense agent session. |
| `arfiti-master-data` | Find or create one vendor (or customer) in Arfiti through the MCP tools - multi-pass duplicate search, employee cross-check, registration and VAT number, a public-register lookup when the organisation's rules ask for it, tax code and terms from the organisation's own codes, bank details through the vendor workflow - and return a result block to the agent that asked. Use when briefed to resolve a party. |
| `arfiti-period-close` | Run the month-end close for one legal entity and fiscal period in Arfiti through the MCP tools only - collect the evidence for each standard check, report every finding with its evidence, decide which findings block from the client's own close rules (never from this skill), fix what ordinary operations or the helpers can fix, raise plain-language tasks for the rest, and close the period through submit("fiscal_period", "close") when asked and nothing the client calls blocking is open. Also resolves a paused built-in close saga. Never forces, never reopens, never locks. |
| `arfiti-reconciliation` | Reconcile one legal entity's open payments (bank payments, card expenses, refunds) against its open bills and invoices in Arfiti through the MCP tools. Reads every document and its card purchase, uses history, dates, references and original-currency amounts as evidence, matches one-to-one, many-to-one and one-to-many, applies each match through submit with a row-level read-back, and turns every item it cannot settle into a person task. Use for every reconciliation session. |
| `arfiti-vendor-deduplication` | Sweep one organisation's vendors for duplicates through the Arfiti MCP tools, decide which pairs are certainly the same party from hard evidence (tax or registration number, bank account, history), and propose each merge through submit("vendor", "merge"), which the organisation's workflow holds for approval; never merge on a name alone. Use for a scheduled or requested duplicate sweep. |
| `arfiti-working-with-people` | How an Arfiti agent treats a person's answer to a task it raised, and how it keeps what the person told it - act on the answer, never ask the same thing again or look for a second opinion, and turn a standing instruction into a record update or a proposed rule so the same question is not asked next time. Use whenever a task you raised is answered, and before raising a task. |

## Support

support@arfiti.com · Documentation: https://arfiti.com/plugins/arfiti-core-agent-procedures
