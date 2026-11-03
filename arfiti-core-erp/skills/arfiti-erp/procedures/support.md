# Support Ticket Procedure

Step-by-step procedure for filing support tickets, adding comments, and checking ticket status.

---

## When This Applies

Use this procedure when ANY of these are true:
- User reports a bug, error, or unexpected behavior
- User wants to request a new feature or improvement
- User asks to "file a ticket", "report a bug", "submit a support request", "contact support"
- User asks to check status of their support tickets
- User wants to add information to an existing ticket
- User wants to close a support ticket

---

## CRITICAL RULES

1. **ALWAYS confirm with the user before submitting** — show them the draft ticket (subject, description, context) and ask for approval
2. **ALWAYS include conversation_context** when filing from an active issue — summarize the relevant conversation details that led to the ticket
3. **Category must be `bug_report` or `feature_request`** — no other values are accepted
4. **Customers can only close tickets** — they cannot change status to in_progress or resolved (that's for the support team)
5. **Cannot comment on closed tickets** — if user needs to reopen, they must file a new ticket
6. **Never use `validate_only` to "preview" a ticket or comment** — a dry run only checks the payload and never files a ticket or posts a comment, so nothing is created. Show the user the draft in chat instead (Step 3), then submit without `validate_only`

---

## Filing a Support Ticket

### Step 1: Identify the Category

| Category | When to Use |
|----------|------------|
| `bug_report` | Something is broken, returning wrong results, or behaving unexpectedly |
| `feature_request` | User wants new functionality, improvements, or changes to existing behavior |

### Step 2: Draft the Ticket

Prepare the ticket details before submitting. Include:

| Field | Required | Description |
|-------|----------|-------------|
| `category` | Yes | `bug_report` or `feature_request` |
| `subject` | Yes | Clear, concise title (max 255 chars) |
| `description` | Yes | Detailed explanation of the issue or request (max 10,000 chars) |
| `conversation_context` | Recommended | Summary of the conversation that led to this ticket — tool calls made, errors seen, data observed |

**Good subject examples:**
- "AP aging report shows incorrect 30-day bucket totals"
- "Request: Add bulk vendor import from CSV"
- "Bank statement sync fails for Revolut connector after authorization"

**Bad subject examples:**
- "Bug" (too vague)
- "Something is wrong" (not actionable)
- "Help" (no context)

### Step 3: Confirm with User

Show the user the prepared ticket and ask for confirmation:

```
I've prepared a support ticket:

  Category: Bug Report
  Subject: AP aging report shows incorrect 30-day bucket totals
  Description: When generating AP aging for entity 9 as of 2026-03-20,
    the 0-30 day bucket includes 3 invoices with due dates from January.
  Context: User ran generate_report('ap_aging', {legal_entity_id: 9,
    as_of_date: '2026-03-20'}). Report returned 15 invoices in 0-30
    bucket, but 3 have due dates older than 60 days.

Shall I submit this?
```

### Step 4: Submit

```
submit("support_ticket", "create", {
    "category": "bug_report",
    "subject": "AP aging report shows incorrect 30-day bucket totals",
    "description": "When generating AP aging for entity 9 as of 2026-03-20, the 0-30 day bucket includes 3 invoices with due dates from January 2026. Expected: only invoices due within last 30 days.",
    "conversation_context": "User ran generate_report('ap_aging', {legal_entity_id: 9, as_of_date: '2026-03-20'}). Report returned 15 invoices in 0-30 bucket. Manual verification showed 3 invoices (INV-001, INV-002, INV-003) have due dates from January."
})
```

**Expected result:**
```json
{
    "success": true,
    "ticket_id": 42,
    "ticket_number": "TKT-000042",
    "status": "open",
    "message": "Support ticket TKT-000042 created successfully."
}
```

Tell the user: "Ticket TKT-000042 has been created. You'll receive a confirmation email. Our team will review it shortly."

---

## Checking Ticket Status

### List All Open Tickets

```
query("support_ticket", filters={"status": "open"})
```

### List All Tickets (Any Status)

```
query("support_ticket")
```

### Get Full Ticket Details (with Comments)

```
get_entity("support_ticket", 42)
```

This returns the ticket plus all comments in the thread. A comment with `author_type` `support` is a reply from the support team; `customer` comments are the user's own. Tell the user what support wrote and what the ticket's status is.

When the support team resolves or closes a ticket, the person who filed it receives an email. A support reply on its own does not send one, so check the ticket when the user asks whether support has answered.

### Search Tickets by Keyword

```
query("support_ticket", query="aging report")
```

Searches across ticket number, subject, and description.

---

## Adding a Comment to a Ticket

Use this when the user wants to provide additional information about an existing ticket.

### Step 1: Verify the Ticket

```
get_entity("support_ticket", 42)
```

Check that:
- The ticket exists and belongs to the user's organization
- The ticket is NOT closed (comments on closed tickets are blocked)

### Step 2: Submit the Comment

```
submit("support_ticket_comment", "create", {
    "ticket_id": 42,
    "body": "I also noticed this happens when filtering by vendor 'Acme Corp' specifically. Other vendors seem to show correct aging buckets."
})
```

**Expected result:**
```json
{
    "success": true,
    "comment_id": 7,
    "ticket_id": 42,
    "ticket_number": "TKT-000042",
    "message": "Comment added to ticket TKT-000042."
}
```

**Note:** If the ticket status was `resolved`, adding a comment automatically reopens it to `open` (the support team will be notified).

---

## Closing a Ticket

When the user's issue has been resolved and they want to close the ticket:

```
submit("support_ticket", "update", {
    "ticket_id": 42,
    "status": "closed"
})
```

**Expected result:**
```json
{
    "success": true,
    "ticket_id": 42,
    "ticket_number": "TKT-000042",
    "status": "closed",
    "message": "Ticket TKT-000042 has been closed."
}
```

**Note:** Customers can only set status to `closed`. To change other statuses (in_progress, resolved), the support team handles this through the admin dashboard.

---

## Troubleshooting

### "Ticket not found" or "Access denied"
- Tickets are scoped to the user's organization — they can only see their own org's tickets
- Verify the ticket_id is correct: `query("support_ticket", query="TKT-000042")`

### "Cannot comment on closed ticket"
- Closed tickets do not accept new comments
- If the issue recurs, file a new ticket and reference the old one in the description

### "Invalid category"
- Only `bug_report` and `feature_request` are valid
- If the user's request doesn't fit either category, use `feature_request` for general requests

---

**Version**: 1.1
**Last Updated**: 2026-10-21
