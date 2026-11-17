---
name: arfiti-expense-check
description: Check a submitted expense claim in Arfiti against the company's own written rules - gather the evidence for every line (rate tables, meal deductions, the employee's other claims and per diems for the same days, card charges, duplicates, missing receipts, the employee's own history), weigh it against each rule the company wrote, and either report nothing or raise one plain-language task for the employee that names the line, the rule and what to do. Holds no company or country policy, no amounts and no thresholds of its own. Never approves, rejects, holds, modifies or pays a claim.
---

# Check a submitted expense claim against the company's rules

Whoever created a claim (the employee in Cowork, the expense agent, the app),
once it is submitted it is checked here. The company's rules decide what is
wrong; this skill only collects the evidence each rule needs and says what it
found. It works the same for a company with no rules, three rules or forty.

Used by the expense agent (`arfiti-expense-processing`, mode `check`). An
approver or accountant can follow it in Cowork for a claim they are about to
approve; then skip the task in step 5 and tell them the findings.

Tools: `query`, `get_entity`, `read_attachment`, `get_submissions`, `submit`
(review tasks only).

## The one rule of this skill

**Every limit, amount, percentage, number of days and "not allowed" comes
from the company's rules text.** Not from this skill, not from what is usual
in a country, not from what seems reasonable. Where a rule says "a reasonable
amount", the rule's own words are what you report; you do not turn them into
a number. A finding names the rule it comes from, in the rule's own words.

## Step 1: the company's rules

Read them as the calling skill says (the expense agent:
`query("agent_rules", ...)` (keyed by agent; the rules for every agent come with it); then any
`client_rules:` block in the first message). Split the text into separate
rules, one finding each. For each rule note:

- what it is about (per diem, meals, mileage, a kind of purchase, receipts,
  amounts, timing, who may claim what);
- what evidence it needs (the catalogue in step 3);
- what the company wants done when it is broken, if it says (ask the
  employee, tell the approver, hold the claim, nothing).

**No rules stored.** Check only what the system itself checks (step 3,
marked "system"), and say in the result `company_rules: none - no company
policy applied`. Never fill the gap with a policy of your own.

## Step 2: the claim

`get_entity("expense_report", R)`: status `submitted` (a `draft` is not yet
for checking; an `approved` or `posted` one is reported, not checked, unless
the first message says to). Note the employee, the lines (type, date, amount,
merchant, category or account, receipt status, distance and vehicle, per-diem
days, country, rate, `meals_included`), `submitted_at`, and the stored
`policy_violations` (the warnings the server raised at submit).

`get_entity("employee", E)`: name, `job_title`, `department`, the linked
`user_id` (needed in step 5), and any custom fields a rule refers to.

## Step 3: the evidence

Collect only what the rules (or, with no rules, the "system" rows) need.

| Evidence | How to read it | Readable today |
|---|---|---|
| Server warnings at submit (missing receipt, overlapping report, the server's own sanity checks) | `policy_violations` on the report | Yes (system) |
| Per-diem days overlapping another of the employee's per diems | Refused by the server at create and submit; check the employee's other reports as below | Yes (system) |
| The rate the server used for a mileage or per-diem line | The line's `mileage_rate` / `per_diem_rate` and rate id, against `query("mileage_rate", ...)` / `query("per_diem_rate", ...)` (daily rate, tier threshold and tier rate, the breakfast, lunch and dinner deductions) | Yes |
| Which meals a per diem marks as provided | The line's `meals_included` | Yes |
| A meal claimed on a day the per diem covers, or with a meal the per diem marks provided | Reimbursement lines whose `spend_date` falls inside a per-diem line's days, in this claim and the employee's other claims; whether the purchase is a meal: the line's text, merchant and category, and the receipt (`read_attachment` on `receipt_url`) | Yes, with judgement on what is a meal |
| Two claims for one trip | The employee's other reports (`query("expense_report", filters={"legal_entity_id": X, "employee_id": E})`, then `get_entity` each for its lines): overlapping dates, same destination or purpose | Partly: lines come only through their report, so a long history means reading report by report |
| A receipt already on a company card charge | `query("card_transaction", filters={"legal_entity_id": X, "employee_id": E})` around the line's date: same amount and merchant, or the same document | Yes |
| The same expense claimed twice | Same amount, date and merchant, or the same `receipt_url`, across the employee's reports | Yes |
| Missing or mismatched receipt | Line `receipt_status`: `none`, `mismatch` | Yes (system) |
| Receipt content against the line (date, amount, what was bought, who it was for, number of people) | `read_attachment` on `receipt_url` | Only for receipts stored in this organisation's storage |
| Expense dates outside the trip | Reimbursement dates against the per-diem or mileage dates of the same claim | Only within the claim: there is no travel or booking record to compare with |
| An amount unusual for this employee | The employee's earlier reports, by category and month | Yes, report by report; there is no ready per-employee statistic |
| An amount above a figure the company set | The rule's figure against the line, total or month | Yes, when the rule states the figure |
| Who the employee is (role, department, grade) | `job_title`, `department`, custom fields on the employee | Partly: grade or band only if the company keeps it as a custom field |

Not readable through the tools today, so a rule that needs it is answered
`cannot_tell`, naming what is missing: travel bookings and itineraries,
calendars and leave, whether a meal was provided beyond the per diem's
`meals_included`, attendees of a meal unless the receipt names them, the
employee's approver, and anything an employee said outside this system.

The server's own sanity checks inside `policy_violations` (a per-diem daily
amount far above the rate table, a long single drive, a large line or total)
use figures fixed in shared code, not the company's. Report them as the
system's warnings, never as company policy.

## Step 4: weigh each rule

For each rule, one finding:

- `within` - the evidence shows the line or claim keeps to the rule;
- `against` - the evidence shows it does not; name the line(s), what the
  evidence shows, and the rule's words;
- `cannot_tell` - the evidence the rule needs is not readable or not there;
  name what is missing;
- `not_applicable` - the rule is about something this claim does not have.

Where the rule leaves room ("normally", "reasonable", "with a manager's OK"),
say what you see and let the person decide; do not settle it.

## Step 5: the outcome

**Nothing against a rule:** no task. The result says what was checked.

**One or more `against` (or a `cannot_tell` the rules say must be asked
about):** one task for the claim, not one per line. The expense agent raises
it with its own Tasks section:

- `kind`: `question`; `subject`: `{"type": "expense_report", "id": R,
  "label": "<report number>"}`.
- **To the employee.** `assigned_to_user_id`: the employee's linked
  `user_id`. A review task cannot be assigned to an employee record
  (`assigned_to_employee_id` is refused). The server refuses a user who
  cannot see the task; then, and when the employee has no app user, leave the
  assignee out (the task goes to the organisation's owner or admin), start
  the title with the employee's name, and report
  `assignee: not_employee - <why>`.
- **Title**: what the employee needs to do, e.g. "Check your Riga claim: two
  breakfasts".
- **Question**, in plain words, per line: what you saw, what the company's
  rule says (its words), and what the employee can do. A submitted report
  cannot be changed by its owner: only an approver can return it, so the
  choices are "explain why it is right", "ask the approver to return it so I
  can correct or remove the line", or "it is a mistake, please remove it".
- **Options**: `explain`, `return_to_correct`, `remove_line`. Each `note`
  says that the answer stays on this task for the approver, who decides;
  nothing on the claim changes because of the answer.
- **Details** (for the approver and the accountant): each finding with its
  evidence, the rule, and the rules that were within. This is the approver's
  note: the tools let no agent write a note onto a submitted report (`update`
  takes only drafts and rejected reports; `modify` is the approver's own
  change), so the task is where the approver reads it.

**A rule asks for the claim to be held.** There is no hold. A report is
`draft`, `submitted`, `approved`, `rejected`, `cancelled` or `posted`;
`reject` and `modify` are the approver's decisions. Say in the task's
details that the company's rule asks for a hold, and report
`hold: requested_no_operation`. Never reject, modify or cancel the claim.

**When the employee answers**, the answer is information for the approver:
record it in the result and link it to the claim; do not change the claim.

## What you hand back

```
CHECK_RESULT
expense_report: <id> <number> <status> employee <id> <name>
company_rules: <n rules from where> | none - no company policy applied
finding: <rule, in its own words> | <within|against|cannot_tell|not_applicable> | <lines> | <evidence or what is missing>
system_warning: <each stored policy_violations entry>
task: <request_id> to <user id | owner/admin - why> | none
hold: requested_no_operation | none
```
