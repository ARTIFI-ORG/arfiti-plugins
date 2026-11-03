# Communication Management

Migration note: old/new inbound addresses are not interchangeable merely because
parsing accepts both domains. They require explicit alias ownership and shared
routing controls. Provider retries use the provider email ID and canonical routing
record for queue deduplication; do not ask an agent to deduplicate by subject or
sender Message-ID, and do not replay historical financial mail to test migration.
Alias activation and live acceptance remain operational gates in the I-7 plan.

## Overview

Inbox and email-detail errors use fixed processing/delivery guidance rather than raw internal event or notification diagnostics. Stored diagnostics are unchanged and remain subject to operational access. Created-document and attachment-result lists accept only object entries in arrays; malformed containers and primitive entries are omitted. Human summaries must be strings. This shape validation does not certify every nested document reference.

The inbox applies the same company/entity/definition and execution-domain checks as email detail before showing a run ID, agent label or processing outcome. Readable email rows and counts remain unchanged; workflow notifications keep their notification label. Stored outcome counters must be nonnegative integers within the database integer range (integer strings are accepted). Malformed counters produce an unknown outcome rather than an error or a misleading success label.

Email detail keeps mailbox access separate from execution access. Processing summaries, created-document/attachment results, run IDs and assigned-agent labels are returned only when the linked run matches the email’s company and entity, has a definition in that company, and passes the shared execution-read policy. An inaccessible run does not hide the readable email itself.

Pending request summaries reapply the shared request-thread read policy when fetched. Workflow summaries require the current company for both the workflow and its definition, plus the workflow reader’s domain and entity policy. A readable organization-level run does not make an entity-unscoped workflow visible to a restricted member.

The activity timeline reads only the original email ID, source and timestamp for its email marker. It does not fetch unused linked-event payloads. Pending-request summaries select a nonblank string action, then a nonblank string vendor name, then the request type; malformed JSON values are not returned as display text.

Communication timeline run details require the same operational and business-domain read permissions as agent sessions. The shared execution policy applies before choosing root runs or descending to another run, including payroll restrictions and linked request/workflow provenance. A readable email alone does not authorize its processing details; the email remains governed by its own mailbox access checks.

The Admin communication activity timeline follows request/event links only within the current company. Each root and descendant run must also reference an agent definition in that company. A cross-company intermediate link stops traversal; it does not grant access because the original email was readable.

For callers with restricted entity access, the recursive timeline also filters root runs, intermediate events and descendant runs to their allowed entities. Existing organization-level records with no entity remain visible under the same rule used for requests and agent sessions; reading an email does not grant another entity’s runs.

The communication system handles **inbound email processing**, **outbound notifications**, and **entity email address management**. It provides an autonomous pipeline where emails are received, classified, routed to agents for processing, and tracked for audit.

**Key Features:**
- Inbound email ingestion via Resend webhooks
- AI-powered spam classification (Claude Haiku)
- Attachment extraction from PDFs, images, and text files
- Entity-specific email addresses with agent routing
- Outbound notification emails for workflow events and agent alerts
- Notification templates with Handlebars-style variable substitution
- Full notification logging and delivery tracking

**Architecture**: Inbound emails arrive via Resend webhooks, get classified and stored, then routed to autonomous agents. Outbound emails use database-stored templates rendered with workflow context. All notifications are logged in `system.notification_log`.

## Available Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `send_notification_email(to_emails, subject, body)` | Send email notification (requires write permission) | Alerting humans about findings, anomalies, or requests |
| `get_entity("entity_email", id=X)` | Get email address details by ID (replaces `get_entity_email_address(address_id=X)`, MCP registration removed) | Looking up a specific email routing config |
| `query("entity_email", query=X)` | Get email address details by address (text search on `email_address`) (replaces `get_entity_email_address(email_address=X)`, MCP registration removed) | Finding routing for a known address |
| `query("entity_email", query)` | Get routing info for incoming email | Determining which entity/agent handles an address |
| `read_attachment(storage_url, content_type)` | Extract content from an attachment (R2-hosted, or a connected file source via `connector://`) | Reading PDF/image/text attachments from emails, or a file in a connected Google Drive |
| `query("entity_email", filters)` | List entity email addresses | Browsing all configured email addresses |
| `query("entity_email", query)` | Search entity email addresses | Finding addresses by keyword |
| `get_entity("entity_email", id=X)` | Get single entity email address | Retrieving full details of a configured address |
| `submit("entity_email", "create", {...})` | Create entity email address | Setting up a new email routing |
| `submit("entity_email", "update", {...})` | Update entity email address | Changing routing rules or agent type |
| `submit("entity_email", "delete", {...})` | Delete entity email address | Removing an email routing |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

---

## Entity Email Addresses

### Overview

Each legal entity can have multiple email addresses for different purposes. When an email arrives at one of these addresses, the system automatically routes it to the configured agent for processing.

**Email Address Format:**

```
{purpose}.{entity_code}.{org_slug}@mail.arfiti.com
```

**Examples:**

| Address | Purpose | Entity |
|---------|---------|--------|
| `bills.warehouse.acme@mail.arfiti.com` | AP bills | Warehouse Ops |
| `receipts.hq.acme@mail.arfiti.com` | Expense receipts | HQ |
| `payments.main.acme@mail.arfiti.com` | Payment confirmations, remittance advices | Main entity |

### Field Reference

> **Note**: The fields below are the default configuration. Your organization may have additional required fields or different validation rules. Always call `get_submissions(action='schema', ...)` to get the authoritative field list for your setup.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email_address` | string | Yes | Full email address (unique among active addresses) |
| `legal_entity_id` | integer | Yes | Which entity receives emails at this address |
| `email_type` | string | Yes | Purpose: `bills`, `receipts`, `statements`, etc. |
| `is_inbound` | boolean | No | Whether this address accepts incoming emails (default: true) |
| `is_outbound` | boolean | No | Whether this address can send emails (default: false) |
| `default_agent_type` | string | No | Agent that processes emails (e.g., `bill_processor`) |
| `routing_rules` | jsonb | No | Config: `{"auto_process": true, "require_approval": false}` |
| `description` | text | No | Human-readable description |
| `is_active` | boolean | No | Active status (default: true) |

**Display fields** (returned by `query`/`query`): `id`, `legal_entity_id`, `email_address`, `email_type`, `default_agent_type`, `is_active`, `is_inbound`, `created_at`

**Searchable fields**: `email_address`

**Filter fields**: `legal_entity_id`, `email_type`, `is_active`, `default_agent_type`, `is_inbound`

**Sort fields**: `email_address` (default), `created_at`, `email_type`

### Creating Entity Email Addresses

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="entity_email", operation="create")

// Step 2: Submit with discovered fields
submit("entity_email", "create", {
    legal_entity_id: 9,
    email_address: "bills.warehouse.acme@mail.arfiti.com",
    email_type: "bills",
    default_agent_type: "bill_processor",
    is_inbound: true,
    routing_rules: {"auto_process": true}
})
// Tip: Use validate_only=true to check payload before submitting
```

### Updating Entity Email Addresses

```javascript
submit("entity_email", "update", {
    id: 5,
    default_agent_type: "receipt_processor",
    routing_rules: {"auto_process": true, "require_approval": true}
})
```

### Querying Entity Email Addresses

```javascript
// List all active inbound email addresses
query("entity_email", filters={"is_active": true, "is_inbound": true})

// List email addresses for a specific entity
query("entity_email", filters={"legal_entity_id": 9})

// Search by address
query("entity_email", query="invoices")

// Get specific address details
get_entity("entity_email", id=5)

// Specialized lookup with entity details
query("entity_email", query="bills.warehouse.acme@mail.arfiti.com")

// Check routing for an incoming email
query("entity_email", query="bills.warehouse.acme@mail.arfiti.com")
```

---

## Sending Notification Emails

### send_notification_email Tool

Use this tool to send email notifications from agents or when a human needs to be informed about findings, alerts, or anomalies.

> **Requires write permission.** A read-only caller gets a permission error rather than sending the email — this only applies to interactive callers; agent-initiated sends run with the agent's own permissioned context.

**What you write and what the server adds.** You write the subject and the body only. The server puts them in the standard email layout:

- at the top, the organisation's name when it sends from its own verified domain, otherwise the Arfiti logo;
- above the headline, "From the [agent name] agent" (for an agent; taken from the agent's own key, you do not pass it). A person sending through Claude gets "From [organisation]";
- the subject as the headline;
- your body as paragraphs: separate them with a blank line;
- a footer saying which agent sent it for which organisation, that an Arfiti agent wrote it, a reference to the sent message (`REF OUT-…`, the start of the event id shown in `/communications`) and the organisation's line.

So do not add a header, a "sent by" line, a sign-off naming the platform or a footer yourself. There is no button and no table; write a link as plain text. HTML is accepted but converted to plain text before it goes into the layout (a link becomes `label: url` text); it is never sent as HTML.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `to_emails` | list | Yes | List of recipient email addresses |
| `subject` | string | Yes | Email subject line |
| `body` | string | Yes | Plain text; paragraphs separated by a blank line |
| `body_format` | string | No | `"text"` (default). `"html"` is converted to plain text before it is placed in the layout |
| `cc_emails` | list | No | CC recipient addresses |
| `from_email` | string | No | Leave unset: the organisation's default sender is used. An address is used only when its domain is one of the organisation's verified sending domains |

**Example: Plain Text Alert**

```javascript
send_notification_email(
    to_emails=["finance@company.com"],
    subject="Anomaly Detected: Unusual expense in Q1",
    body="We detected an unusual expense pattern in Q1. Please review the following transactions..."
)
```

**Example: Several Paragraphs**

```javascript
send_notification_email(
    to_emails=["cfo@company.com", "controller@company.com"],
    subject="Monthly reconciliation complete",
    body="All 45 bank transactions for September are matched.\n\nTwo card payments are still waiting for receipts: AP-000142 and AP-000151."
)
```

**Example: With CC**

```javascript
send_notification_email(
    to_emails=["ap-manager@company.com"],
    subject="Duplicate Invoice Detected",
    body="Invoice INV-2024-001 from Acme Corp appears to be a duplicate...",
    cc_emails=["finance-team@company.com"]
)
```

**Response:**

```javascript
{
  "success": true,
  "email_id": "resend-message-id-here"
}
```

---

## Workflow Notification System

The system automatically sends email notifications for workflow events. These are not triggered by Claude directly but happen automatically when workflows change state.

### Notification Types

| Event | Template Type | Recipient | When |
|-------|--------------|-----------|------|
| Task assigned | `approval_request` | Approver | Workflow enters yellow/red lane |
| Workflow approved | `decision` | Submitter | Approver approves task |
| Workflow auto-completed | `auto_completed` | Submitter | Green lane workflow completes |
| Workflow rejected | `decision` | Submitter | Approver rejects task |
| Reminder | `reminder` | Approver | Task pending beyond threshold |
| Agent request | (system email) | Assigned user or admins | Agent needs human input |
| Credit exhaustion | (system email) | Org admins | AI credits depleted |

### Notification Templates

Templates are stored in `system.notification_templates` and use Handlebars-style variable substitution.

**Template Types:**
- `approval_request` -- Task assigned to approver
- `reminder` -- Reminder for pending task
- `decision` -- Workflow approved or rejected
- `auto_completed` -- Workflow auto-completed (green lane)
- `submitted` -- Confirmation to submitter
- `comment` -- Comment added to workflow
- `escalation` -- Task escalated to next level

**Template Variables:**

| Variable | Description |
|----------|-------------|
| `{{approver_name}}` | Name of the approver |
| `{{submitter_name}}` | Name of the workflow submitter |
| `{{workflow_name}}` | Human-readable workflow name |
| `{{object_type}}` | Entity type (vendor, payment_batch, etc.) |
| `{{lane}}` | Risk lane (green, yellow, red) |
| `{{step_name}}` | Current workflow step name |
| `{{submitted_at}}` | Submission timestamp |
| `{{decision_date}}` | Approval/rejection timestamp |
| `{{summary}}` | Workflow summary text |
| `{{comment}}` | Approver comment |
| `{{rejection_reason}}` | Reason for rejection |
| `{{view_url}}` | Link to task in admin dashboard |
| `{{payload_details}}` | Formatted HTML table of workflow payload |
| `{{days_pending}}` | Days the task has been pending (reminders) |
| `{{reminder_count}}` | Number of reminders sent (reminders) |

**Conditional Blocks:**

```
{{#if comment}}
Approver Comment: {{comment}}
{{/if}}
```

### Workflow Notification Settings

Per-workflow notification configuration is stored in `system.workflow_notification_settings`:

| Field | Description |
|-------|-------------|
| `definition_id` | Which workflow definition |
| `event_type` | Which event triggers notification |
| `enabled` | Whether notification is active |
| `delivery_method` | `email`, `in_app`, or `both` |
| `include_action_buttons` | Show approve/reject buttons in email |
| `action_requires_login` | One-click action vs login required |

### Notification Log

All sent notifications are tracked in `system.notification_log`:

| Field | Description |
|-------|-------------|
| `task_id` | Related workflow task |
| `instance_id` | Workflow instance UUID |
| `template_id` | Template used |
| `event_type` | Notification event type |
| `recipient_email` | Who received it |
| `subject` | Rendered subject |
| `delivery_status` | `pending`, `sent`, `delivered`, `failed`, `bounced` |
| `resend_message_id` | Resend tracking ID |
| `error_message` | Error details if failed |

---

## Inbound Email Pipeline

### How Inbound Email Works

```
1. Email arrives at entity address (e.g., bills.hq.acme@mail.arfiti.com)
2. Resend sends webhook to admin dashboard
3. Webhook handler:
   a. Verifies Svix signature
   b. Parses email address to determine org, entity, purpose
   c. Classifies spam (Claude Haiku)
   d. Fetches and stores attachments in Cloudflare R2
   e. Creates agent_events record
4. Agent executor picks up the event
5. Agent processes email (e.g., bill_processor extracts invoice data)
```

### Spam Classification

Every inbound email is classified before agent processing:

| Classification | Confidence | Action |
|---------------|------------|--------|
| Legitimate | >= 0.70 | Accept, create agent event |
| Spam | >= 0.85 | Reject, store audit record |
| Uncertain | 0.70-0.85 | Accept but flag for review |
| Check failed | N/A | Accept, recorded as `check_failed` (see below) |

The spam filter is designed to **never reject emails due to system errors**. If the check does not complete (API error, truncated or unparseable reply, budget exceeded), the email is accepted and recorded as `check_failed`. That says nothing about the sender, so a bill from such an email is not posted automatically: it goes to review ("The automatic email check did not complete") unless that sender is already trusted for that vendor, and approving it never trusts the sender. Only an `uncertain` sender can be trusted, and the trust is stored once the reviewed bill has posted.

### Attachment Processing

Agents extract content from attachments on-demand using `read_attachment`:

| Content Type | Method | Cost |
|-------------|--------|------|
| PDF | Claude Document API | ~$0.02/page |
| JPEG, PNG, GIF, WebP | Claude Vision API | ~$0.01/image |
| Plain text, CSV, HTML | Direct read | $0.00 |

Attachments are stored in Cloudflare R2 with org-scoped folders and 24-hour presigned URLs.

> **`read_attachment` only fetches from allowed storage hosts** — R2 presigned URLs and direct R2 downloads (`*.r2.cloudflarestorage.com` plus the org's configured `R2_PUBLIC_URL`/endpoint host) work as normal. A raw external URL — including a link a customer pasted into an email — is rejected with a structured error, not fetched.
>
> **To read a file from a connected source** (e.g. Google Drive), pass a connector reference as `storage_url`: `connector://<connector_id>/<file_id>`. `read_attachment` fetches it through the connector's authenticated API, stores it into R2, and extracts as normal. This requires a registered `FILE_STORAGE` connector and `config:read` permission (and the connector's entity must be in your scope). If there's no connector for the source, ask the user to forward the file as an attachment instead.

---

## Admin Dashboard Communications Inbox

The admin dashboard provides an inbox view for managing communications:

| Route | Purpose |
|-------|---------|
| `/communications` | Inbox list with filters, search, and stats |
| `/communications/[id]` | Email detail with body, attachments, and actions |

**Inbox Features:**
- Stats bar: Unprocessed, Processed, Spam Blocked, Total (30 days)
- Filters: Direction, Status, Classification
- Search across subject, from address, to address
- PDF/image attachment preview

**Available Actions:**
- Mark as Real: Override spam classification to legitimate
- Retry Processing: Re-queue email for agent processing
- Archive: Hide email from inbox

---

## Common Scenarios

### Scenario 1: Set Up Email Ingestion for a New Entity

```javascript
// Step 1: Create the entity email address for bill processing
submit("entity_email", "create", {
    legal_entity_id: 9,
    email_address: "bills.warehouse.acme@mail.arfiti.com",
    email_type: "bills",
    default_agent_type: "bill_processor",
    is_inbound: true,
    routing_rules: {"auto_process": true}
})

// Step 2: Verify the address was created
query("entity_email", query="bills.warehouse.acme@mail.arfiti.com")

// Step 3: Tell the user to forward invoices to that address
```

### Scenario 2: Send Alert About Unusual Activity

```javascript
send_notification_email(
    to_emails=["cfo@company.com"],
    subject="Alert: Large Transaction Detected",
    body="A transaction of $250,000 was posted to AP today, which is 5x the typical daily average. Please review transaction AP-000142."
)
```

### Scenario 3: Check Email Routing for an Address

```javascript
// Look up how an email address is routed
query("entity_email", query="bills.hq.acme@mail.arfiti.com")

// Response:
// {
//   "results": [{
//     "is_active": true,
//     "legal_entity_id": 9,
//     "entity_code": "hq",
//     "entity_name": "Headquarters",
//     "email_type": "bills",
//     "default_agent_type": "bill_processor",
//     "routing_rules": {"auto_process": true}
//   }]
// }
```

### Scenario 4: List All Email Addresses for an Entity

```javascript
query("entity_email", filters={"legal_entity_id": 9, "is_active": true})
```

### Scenario 5: Change the Agent Processing Emails

```javascript
// Switch from bill_processor to a different agent
submit("entity_email", "update", {
    id: 5,
    default_agent_type: "receipt_processor"
})
```

### Scenario 6: Send a Short Report via Email

The layout has no table: write the figures as sentences or one line each.

```javascript
send_notification_email(
    to_emails=["finance-team@company.com"],
    subject="Weekly AP aging",
    body="Acme Corp: 5,000.00 EUR current, 2,000.00 EUR 30 days overdue.\n\nNothing is 60 days overdue."
)
```

---

## Key Takeaways

1. **Entity email addresses** route inbound emails to the correct legal entity and agent
2. **Spam classification** uses AI (Haiku) with fail-open behavior to never lose legitimate emails
3. **Notification templates** use Handlebars syntax and are stored per-organization in the database
4. **All notifications are logged** in `system.notification_log` for audit and delivery tracking
5. **Attachments** are stored in R2 and extracted on-demand by agents (cost-efficient)
6. **`send_notification_email`** is the tool for sending ad-hoc emails from agents. You write the subject and a plain-text body; the server adds the brand, "From the [agent] agent", the footer and the message reference. Leave `from_email` unset: the organisation's default sender is used. A `from_email` outside the organisation's verified sending domains is ignored, and the result says so in `from_email_ignored`
7. **Workflow notifications** (task assigned, approved, rejected) happen automatically
8. **Entity email CRUD** uses standard workflow pattern: `submit("entity_email", "create/update/delete", {...})`

---

**End of Communication Management Guide**


Processing details also inherit the shared execution policy for reserved
`created_documents` and `results` arrays. Their entries must be objects, and
nested transaction IDs (including legacy document IDs and existing-transaction
references) must resolve in the run's entity with the required domain access.
An inaccessible run leaves the readable email available without its processing
details. This bounded check does not certify arbitrary deeper JSON or free text.


Email processing result display fields (document types/numbers/references,
currency/status, attachment/vendor names, reasons and review/rejection prose)
accept nonblank strings only; malformed values become null. Outcome flags and
configuration-request flags require boolean `true`, so the text `"false"` cannot
show a successful outcome. Asset counts require an array. Attachment errors use
fixed failure guidance instead of raw internal diagnostic text; stored diagnostics
are unchanged. Numeric values and request/workflow link metadata remain under
separate review; this is not a claim of complete result-schema validation.


Processing-result amounts accept finite numbers or decimal text; decimal text is
returned unchanged to avoid introducing rounding. Confidence must be a finite
number between zero and one. Transaction links accept positive safe integer
numbers or canonical positive bigint strings; malformed or oversized values
become null. Review-request and workflow IDs must have UUID shape before they
are returned. These format checks do not establish authorization of the linked
request/workflow; that stored-reference audit remains open.


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

### Resumed request outcomes (QA branch)

A readable request does not automatically make its resumed execution readable.
Admin's request outcome reader checks the resumed run and its definition belong
to the event's organization, applies the shared execution-domain/reference policy,
and retains the existing run entity-access check. If the latest completion event
points to a missing or inaccessible run, the optional outcome is absent; the
reader does not expose its run ID, summary or per-document results, and does not
fall back to an older readable completion. The request's own access is unchanged.


### Request notification link case

In-app request notifications resolve valid UUIDs with uppercase or lowercase
hexadecimal letters to the same stored request status. A pending request remains
an open decision after its notification is read; a completed request does not
become an open decision merely because its notification is unread. The same
status drives open-decision ordering. Existing recipient, company and linked-record
authority filters still apply; malformed or missing linked records remain hidden.
This does not change request state, read markers or email delivery.
