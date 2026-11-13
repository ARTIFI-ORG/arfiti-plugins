# Document Attachment Management

An invalid or expired upload link directs the user to request a new link from
the person or assistant who shared it. This recovery path works regardless of
which supported client issued the link; invalid links return 404 and expired
links return 410, without an upload form.

This resource explains how to capture and attach uploaded documents (bills, invoices, receipts) to ERP transactions.

For an existing Bill review task, continue its response flow. The task-bound Bill
agent can inspect its original attachment; extracted facts are evidence, not
automatic edits to the reviewed bill. Its attachment access is restricted to the
source bound to that task. The general upload and connector examples below do
not grant a task agent permission to inspect arbitrary files.

## CRITICAL: When User Uploads a File

**ALWAYS follow this workflow when a user uploads a document to the chat:**

1. **Analyze** the document (extract vendor, amounts, dates, line items)
2. **Identify the existing target first.** For a card purchase, inspect its linked bills and attach missing original evidence to the correct existing bill or provider card row through the supported attachment/receipt workflow. Do not create another AP invoice to satisfy a receipt obligation. Create a transaction via `submit("transaction", "post", {...})` only when the document represents a genuinely new, unrecorded transaction.
3. **Create attachment** with extracted metadata via `submit("attachment", "create", {...})`
4. **Generate upload link** via `submit("attachment", "generate_upload_url", {...})`
5. **Attach the original file.** Route on ONE question:

   > **Who is holding the bytes right now, and what can they run?**

   Not on file size — there is no "under X MB" rule — and never ask the user to
   re-upload a file they already gave you.

   | Who holds the bytes | Route |
   |---|---|
   | **You, on disk, and your environment has outbound network** (Claude Code) | `curl -sf -F "file=@<path>" "<upload_url>"` |
   | **You, but you cannot reach the endpoint** (Cowork), or the file only exists in the chat | Hand the user the upload link from step 4 |
   | **The user, in their inbox** | Ask them to forward it to the org's document intake address |
   | **The user, at a computer, on the record's own page** | Ask them to upload it there |
   | **Already in the org's connected Drive folder** | `read_attachment(storage_url="connector://<connector_id>/<file_id>", content_type=<MIME type>)` — no upload at all |

   **The upload link is the only route you can initiate when you have no shell
   and no egress.** In Cowork that is every time: its proxy denies CONNECT to
   `mcp.arfiti.com` and `app.arfiti.com` alike, allowlisting only package
   registries, so `curl` fails there every time (verified 2026-08-14 for the
   previous host). Generate
   the link, give it to the user, and say plainly what it is for.

   **You cannot put a file INTO Drive.** The Drive connector is a *pull* route
   only — it works when the document is already in the shared folder, because
   the user or a scanner put it there. The Drive MCP's `create_file` accepts
   only `base64Content`/`textContent`, `copy_file` needs the file already in
   Drive, and `update_file` is metadata; so "save it to Drive first, then pull
   it" is the inline-base64 route wearing a disguise, and it is forbidden for
   exactly the same reason:

   **Never try to carry the file yourself as inline base64.** A session on
   2026-08-14 spent several minutes shrinking an image four ways to make the
   payload "small enough", then corrupted an 18KB base64 string retyping it.
   Transcribing tens of thousands of random characters faithfully is not
   something you can do, and no amount of compression changes that. The
   constraint is the transcription, not the size.

**DO NOT wait for transaction approval** - generate the upload link immediately so the file can be uploaded while the transaction is pending approval.

## When to Use This

Use this when a user:
- Uploads a PDF, image, or document to the chat
- Wants to attach a bill/invoice to a transaction
- Needs to link supporting documentation to AP/AR invoices
- Asks to "attach this" or "save this document"

## Tools to Use

| Operation | Tool | Example |
|-----------|------|---------|
| Create attachment | `submit` | `submit("attachment", "create", {...})` |
| Generate upload link | `submit` | `submit("attachment", "generate_upload_url", {...})` |
| Confirm upload | `submit` | `submit("attachment", "confirm_upload", {...})` |
| Delete attachment | `submit` | `submit("attachment", "delete", {...})` |
| Read a stored document | `read_attachment` | `read_attachment(storage_url=..., content_type="application/pdf")` |
| Search attachments | `query` | `query("attachment", query="invoice", {...})` |
| Get attachment | `get` | `get("attachment", 123)` |
| List attachments | `list` | `list("attachment", {"transaction_id": 456})` |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

---

## Primary Flow: File Uploaded to Chat

When a user uploads a file directly to Claude.ai:

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Analyze Document                                    │
│  - Extract vendor name, invoice number, amounts, dates       │
│  - Extract full text content                                 │
│  - Identify line items                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: Create Transaction                                  │
│  submit("transaction", "post", {                            │
│    transaction_type_code: "AP_INVOICE",                     │
│    vendor_id: ..., invoice_number: ..., lines: [...]        │
│  })                                                          │
│  → Returns: transaction_id                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: Create Attachment (Metadata Only)                   │
│  submit("attachment", "create", {                           │
│    entity_type: "AP_INVOICE",                               │
│    entity_id: <transaction_id>,                             │
│    file_name: "invoice.pdf",                                │
│    extracted_text: "...",                                   │
│    extracted_amounts: {...},                                │
│    extracted_metadata: {...}                                │
│  })                                                          │
│  → Returns: attachment_id                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 4: Generate Upload Link                                │
│  submit("attachment", "generate_upload_url", {              │
│    attachment_id: <attachment_id>,                          │
│    legal_entity_id: ...,                                    │
│    file_name: "invoice.pdf",                                │
│    content_type: "application/pdf"                          │
│  })                                                          │
│  → Returns: upload_url (expires in 15 min)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 5: Attach the Original File                            │
│                                                              │
│  File on disk + shell access (Cowork / Claude Code)?         │
│    curl -sf -F "file=@invoice.pdf" "<upload_url>"            │
│    → stored in R2 + linked automatically. Then tell user:    │
│    "I've created AP invoice #1234 for $5,432.10 from Acme.   │
│     Original PDF attached. Status: {result.status}."         │
│                                                              │
│  No file access / no shell (claude.ai web chat)?             │
│    → "To attach the original PDF, click here:                │
│       https://mcp.arfiti.com/api/upload/abc123...           │
│       The link expires in 15 minutes. No login required."    │
└─────────────────────────────────────────────────────────────┘
```

---

## Alternative Flow: File from Google Drive MCP

When the user provides a file from Google Drive (via Google Drive MCP):

```
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Read file from Google Drive                         │
│  - Use Google Drive MCP to read the file                     │
│  - Extract content and analyze                               │
│  - Get the Google Drive URL                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: Create Transaction                                  │
│  (same as above)                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: Create Attachment WITH Google Drive URL             │
│  submit("attachment", "create", {                           │
│    entity_type: "AP_INVOICE",                               │
│    entity_id: <transaction_id>,                             │
│    file_name: "invoice.pdf",                                │
│    storage_url: "https://drive.google.com/file/d/...",      │
│    storage_provider: "google_drive",                        │
│    extracted_text: "...",                                   │
│    extracted_amounts: {...}                                 │
│  })                                                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  NO UPLOAD LINK NEEDED - File already in Google Drive        │
│                                                              │
│  Response: "I've created AP invoice #1234 for $5,432.10.    │
│   The original file is linked from your Google Drive."       │
└─────────────────────────────────────────────────────────────┘
```

**Key difference**: When file comes from Google Drive, pass `storage_url` and `storage_provider` to `attachment.create`. No need to generate upload link.

---

## Workflow Operations

### 1. Create Attachment (Metadata)

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="attachment", operation="create")

// Step 2: Submit with discovered fields
submit("attachment", "create", {
    // Required
    "entity_type": "AP_INVOICE",  // AP_INVOICE, AR_INVOICE, FIXED_ASSET, etc.
    "entity_id": 1234,
    "legal_entity_id": 9,
    "file_name": "acme_invoice_jan2025.pdf",

    // Extracted content (ALWAYS provide)
    "extracted_text": "Invoice from Acme Corp dated January 15, 2025...",
    "extracted_amounts": {
        "total": 5432.10,
        "subtotal": 4938.27,
        "tax": 493.83,
        "line_items": [
            {"description": "Consulting services", "amount": 4938.27}
        ]
    },
    "extracted_metadata": {
        "vendor_name": "Acme Corporation",
        "invoice_number": "INV-2025-001",
        "invoice_date": "2025-01-15",
        "due_date": "2025-02-14",
        "payment_terms": "NET30",
        "po_number": "PO-2025-007"
    },

    // Optional
    "attachment_type": "INVOICE",
    "content_type": "application/pdf",
    "description": "January consulting invoice",
    "tags": ["consulting", "monthly"],

    // Only if from external source (Google Drive, etc.)
    "storage_url": "https://drive.google.com/file/d/...",
    "storage_provider": "google_drive"
})
// Tip: Use validate_only=true to check payload before submitting

// Returns:
// {
//   "success": true,
//   "attachment_id": 456,
//   "entity_type": "AP_INVOICE",
//   "entity_id": 1234,
//   "file_stored": false,
//   "storage_provider": "metadata_only"
// }
```

### 2. Generate Upload Link

**Call this immediately after creating attachment** (don't wait for transaction approval):

```javascript
submit("attachment", "generate_upload_url", {
    "attachment_id": 456,                        // Required
    "legal_entity_id": 9,                        // Required
    "file_name": "acme_invoice_jan2025.pdf",     // Optional: defaults to the attachment's file name
    "content_type": "application/pdf",           // Optional: defaults from the attachment / file extension
    "expires_in_minutes": 15  // Optional, default 15, max 60
})
// A "Validation Failed" answer lists the bad fields: fix them and resend.
// Nothing was executed, so a corrected request is safe.

// Returns:
// {
//   "success": true,
//   "upload_url": "https://mcp.arfiti.com/api/upload/abc123def456...",
//   "upload_token": "abc123def456...",
//   "attachment_id": 456,
//   "expires_at": "2025-01-21T12:30:00Z",
//   "expires_in_minutes": 15,
//   "instructions": "Upload your file to this link. The link expires in 15 minutes. No login required."
// }
```

### Uploading the File Yourself (preferred whenever possible)

If the user's file exists as a real file in your working environment — Cowork and Claude Code place chat attachments in your working directory — and you can run shell commands, **upload it yourself instead of handing the user the link**:

```bash
curl -sf -F "file=@/path/to/acme_invoice_jan2025.pdf" "https://mcp.arfiti.com/api/upload/abc123def456..."
```

- Success returns `{"success": true, "attachment_id": ..., "file_size": ..., "content_hash": ...}`. The file is stored in R2 and linked to the attachment automatically — **no `confirm_upload` call needed**.
- Tell the user the original file is attached; don't show them the link.
- HTTP 404/410 means the token expired, was already used, or its attachment was deleted — check the attachment first; if it still has no file, generate a new upload URL and retry once.
- HTTP 409 means another upload with the same link is in progress — do not send the file again; check the attachment a moment later.
- If your environment cannot reach the endpoint, fall back to giving the user the link.
- Only default to the link when you have no copy of the file on disk or no shell access (claude.ai web chat).
- Keep uploads at or below **25 MB** (the document pipeline's working ceiling). Larger files: attach metadata only and tell the user the file is too large to store.

### Files Already in Google Drive (connector pull — no upload at all)

If the organization has a Google Drive connector and the document sits in its shared folder, skip every upload path:

```javascript
read_attachment(
    storage_url="connector://<connector_id>/<drive_file_id>",
    content_type="application/pdf",
    filename="invoice.pdf"
)
```

- The server fetches the file through the connector, stores it, and runs extraction; the response includes `stored_url` — use it as the attachment's `storage_url` in `attachment.create`.
- The Drive file ID is the long token in the file's URL (`/d/<id>/` or `?id=<id>`).
- Only files inside the connector's shared folder are readable (25 MB cap); anything else is refused.
- Find the connector at runtime: `query("connector", filters={"provider": "gdrive"})` — use the active one for the entity.
- **This is a PULL route only — it is not a way to transfer a file you hold.** It works when the document is already in the shared folder because a human or a scanner put it there. You cannot put one there yourself: the Drive MCP's `create_file` takes only `base64Content`/`textContent`, so "save it to Drive, then pull it" just moves the bytes through your context, which is the one thing that never works. When you hold a file and cannot reach the upload endpoint, hand the user the upload link instead.
- **Never route by file size** — there is no "under X MB" rule. Route on who holds the bytes: yours on disk with egress → curl; already in the Drive folder → pull; anything else → the upload link.

### Reading a Stored Document (`read_attachment`)

Read the whole document first; the server handles length:

```javascript
read_attachment(storage_url="<storage_url from the attachment>", content_type="application/pdf")
```

- PDFs up to **200 pages** are read whole. Long ones come back with `extraction_method: "claude_document_chunked"`, `page_count`, and `reconciliation` showing which printed figure the line items add up to.
- **`success: false` with an `incomplete` block means the bill was NOT read completely.** There are no amounts or line items in that answer; do not build a transaction from anything you saw elsewhere. Follow `incomplete.next_step`: read the `missing_pages` with `pages`, or tell the user which pages could not be read and why (`problems`).
- `pages="3-7"` (at most 5 pages) returns the full text of those pages. Its figures are what those pages print, **not the document total** — never post a page-range total as the bill total.
- Over 200 pages: read it in ranges with `pages` and say plainly that no whole-document check was made.
- A long read takes minutes and costs about $2 per 100 pages; read a document once and reuse the result.
- `visual_evidence` lists what the page shows beyond its text: logos, the platform or app that issued the document when it differs from the seller, stamps and watermarks (such as PAID), handwriting, alterations; each item has `kind`, `description`, `location`, `confidence`. `{"none_seen": true}` means nothing was seen. Use a logo or platform as a lead (for example, the seller may be a driver or merchant selling through that platform, and the platform may already be a vendor), **never as the seller**: the vendor is the legal seller in `metadata.vendor_name` and `vendor_details` (tax number, bank details). Ask the user when the two point to different vendors.

### 3. Confirm Upload

Links a file already stored under the pending upload's storage key to the attachment. A file uploaded through the public upload page is linked by the page itself, so no confirmation is needed there.

The server reads the stored object: it must exist and match `content_hash` and `file_size`, or the call is refused ("Validation Failed"), nothing changes and the token stays usable. Confirm only after the file is stored. After a refusal, send the corrected call with a new `idempotency_key`: an identical retry replays the saved refusal.

```javascript
submit("attachment", "confirm_upload", {
    "upload_token": "abc123def456...",
    "content_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",  // SHA-256 of the uploaded bytes, 64 hex characters
    "file_size": 12345
})

// Returns:
// {
//   "attachment_id": 456,
//   "file_name": "invoice.pdf",
//   "file_size": 12345,
//   "storage_provider": "r2",
//   "confirmed": true
// }
```

### 4. Delete Attachment

```javascript
submit("attachment", "delete", {
    "attachment_id": 456,
    "legal_entity_id": 9,
    "delete_file": true  // Also delete from R2 storage
})
```

---

## Entity Type Mapping

| User Says | entity_type |
|-----------|-------------|
| "bill", "vendor invoice", "AP invoice" | AP_INVOICE |
| "customer invoice", "AR invoice", "sales invoice" | AR_INVOICE |
| "journal entry", "JE", "adjustment" | JOURNAL_ENTRY |
| "asset", "fixed asset", "equipment" | FIXED_ASSET |
| "expense", "expense report" | EXPENSE |
| "contract", "agreement" | CONTRACT |
| "vendor document" | VENDOR |
| "customer document" | CUSTOMER |
| "card receipt", "receipt for this charge" | CARD_TRANSACTION |

**Card charges**: `entity_id` is the `bank_card_transactions.id` — the feed row
you see in `query("card_transaction", ...)` — **not** its posted GL transaction
id. They are different id spaces and both are plain integers, so a mix-up files
the receipt somewhere silently wrong.

Uploading against a card charge files a real **card receipt**, not merely a
stored attachment, so it appears on the Card expenses page immediately. The
charge moves to `receipt_status = 'uploaded'` — a draft. It is **not** submitted:
call `submit("card_transaction", "submit_receipt", {...})` to hand it to the bill
pipeline. See `receipts-management.md`.

Before 2026-08-17 this row did not exist, and aiming a link at a proxy entity
(EMPLOYEE was the usual workaround) stored the bytes where nothing ever linked
them to the charge — the upload succeeded and the page still showed "no receipt".
If you are reading an older transcript that does this, it was working around a
gap that is now closed.

---

## Transaction Required Fields

**IMPORTANT**: Before creating any transaction, ensure you include ALL required fields. Missing fields will cause validation errors.

### AP_INVOICE Required Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `transaction_type_code` | string | **YES** | Must be `"AP_INVOICE"` |
| `legal_entity_id` | integer | **YES** | Legal entity ID |
| `vendor_id` | integer | **YES** | Vendor ID (lookup by name if needed) |
| `transaction_date` | string | **YES** | Transaction date in `YYYY-MM-DD` format |
| `invoice_date` | string | **YES** | Invoice date in `YYYY-MM-DD` format |
| `due_date` | string | **YES** | Due date in `YYYY-MM-DD` format |
| `dimensions` | object | **CONDITIONAL** | Header dimensions - required if organization has required dimension types |
| `lines` | array | **YES** | At least one line item |

### Line Item Required Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string | **YES** | Line description |
| `quantity` | number | **YES** | Quantity (must be > 0) |
| `unit_price` | number | **YES** | Unit price |
| `account_number` OR `item_id` | string/int | **YES** | Either account number OR item ID (not both) |
| `dimensions` | object | **CONDITIONAL** | Line dimensions (inherits from header if not provided) |

### Dimension Format

Dimensions can be provided in **two formats**:

**Format 1: Simple Object (PREFERRED)**
```json
{
  "dimensions": {
    "cost_center": "CC-1000",
    "location": "NYC"
  }
}
```

**Format 2: Array of Objects**
```json
{
  "transaction_dimensions": [
    {"dimension_type": "cost_center", "dimension_value": "CC-1000"},
    {"dimension_type": "location", "dimension_value": "NYC"}
  ]
}
```

**Use the simple object format** - it's more concise and less error-prone.

**Check required dimensions**: Required dimensions are configured per workflow definition under `workflow_definitions.related_entity_rules.<transaction_type>.transaction_dimensions.required_dimension_types`. Query the org's `transaction.post` workflow definition to discover which dimensions are required for the transaction type you're about to post. Do NOT use `list_dimension_types(... is_required=true)` — that field is deprecated and no longer enforced.

---

## Complete Example: User Uploads Invoice

**User uploads: acme_invoice.pdf**

**Step 1: Analyze**
```
I can see this is an invoice from Acme Corporation:
- Invoice #: INV-2025-001
- Date: January 15, 2025
- Total: $5,432.10 (subtotal $4,938.27 + tax $493.83)
- Due: February 14, 2025 (NET30)
- For: Consulting services - December 2025
- PO Reference: PO-2025-007

Would you like me to create this as an AP invoice?
```

**User**: "Yes, create it for Innovate Tech Solutions (entity 10)"

**Step 1.5: Check Required Dimensions**
```python
# Required dimensions live in the workflow definition, keyed by transaction_type.
# Read related_entity_rules from THIS org's transaction.post workflow definition:
#   workflow_definitions WHERE organization_id=$ORG AND object_type='transaction'
#                          AND operation='post' AND is_active=true
# Then look at:
#   related_entity_rules["AP_INVOICE"].transaction_dimensions.required_dimension_types
#   → e.g., ["cost_center", "location"]
#
# (The deprecated list_dimension_types(is_required=true) filter is NO LONGER
#  enforced by the validator and should not be relied on.)
```

**Step 2: Create Transaction**
```python
submit("transaction", "post", {
    # Required fields
    "transaction_type_code": "AP_INVOICE",
    "legal_entity_id": 10,
    "vendor_id": 16,  # Acme Corporation
    "transaction_date": "2025-01-15",  # REQUIRED - use invoice date or today
    "invoice_date": "2025-01-15",      # REQUIRED for invoices
    "due_date": "2025-02-14",          # REQUIRED for invoices

    # Optional but recommended
    "reference_number": "INV-2025-001",  # Vendor invoice number
    "description": "Consulting services - December 2025",

    # Required dimensions (at header level - all lines inherit)
    "dimensions": {
        "cost_center": "CC-1000",  # Required dimension
        "location": "NYC"          # Required dimension
    },

    # Lines
    "lines": [
        {
            "line_number": 1,
            "description": "Consulting services - December 2025",
            "quantity": 1,
            "unit_price": 4938.27,
            "account_number": "6500"
            # Note: dimensions inherited from header
        }
    ]
})
# → Returns transaction_id: 1234
```

**Step 3: Create Attachment**
```python
submit("attachment", "create", {
    "entity_type": "AP_INVOICE",
    "entity_id": 1234,
    "legal_entity_id": 10,
    "file_name": "acme_invoice.pdf",
    "content_type": "application/pdf",
    "attachment_type": "INVOICE",
    "extracted_text": "Invoice from Acme Corporation...",
    "extracted_amounts": {
        "total": 5432.10,
        "subtotal": 4938.27,
        "tax": 493.83
    },
    "extracted_metadata": {
        "vendor_name": "Acme Corporation",
        "invoice_number": "INV-2025-001",
        "invoice_date": "2025-01-15",
        "due_date": "2025-02-14"
    }
})
# → Returns attachment_id: 456
```

**Step 4: Generate Upload Link**
```python
submit("attachment", "generate_upload_url", {
    "attachment_id": 456,
    "legal_entity_id": 10,
    "file_name": "acme_invoice.pdf",
    "content_type": "application/pdf"
})
# → Returns upload_url: "https://mcp.arfiti.com/api/upload/abc123..."
```

**Step 5: Attach the file, then respond**

In Cowork / Claude Code (the uploaded file is in your working directory):
```bash
curl -sf -F "file=@acme_invoice.pdf" "https://mcp.arfiti.com/api/upload/abc123..."
```
```
I've created AP invoice #1234 for Acme Corporation:

| Field | Value |
|-------|-------|
| Invoice # | INV-2025-001 |
| Amount | $5,432.10 |
| Due Date | February 14, 2025 |
| Status | {result.status} |

Original PDF attached. All invoice details are captured and searchable.
```

Fill **Status** from the `status` in the submit() result; whether the invoice waits for approval is the organisation's workflow configuration.

In claude.ai web chat (no file access — give the link instead):
```
I've created AP invoice #1234 for Acme Corporation ($5,432.10, due Feb 14).

All invoice details have been captured and are searchable.

**To attach the original PDF, click here:**
https://mcp.arfiti.com/api/upload/abc123...

The link expires in 15 minutes. No login required.
```

---

## Searching Attachments

```python
# Search by text
query("attachment", query="Acme invoice", {
    "legal_entity_id": 9,
    "attachment_type": "INVOICE"
})

# List attachments for a transaction
list("attachment", {
    "transaction_id": 1234,
    "transaction_type": "AP_INVOICE"
})
```

---

## Attachment Types

| Type | Use For |
|------|---------|
| `INVOICE` | Vendor invoices, customer invoices |
| `RECEIPT` | Purchase receipts, expense receipts |
| `CONTRACT` | Agreements, contracts, SOWs |
| `PO` | Purchase orders |
| `STATEMENT` | Bank statements, account statements |
| `SUPPORTING_DOC` | General supporting documentation |
| `PHOTO` | Asset photos, damage documentation |

---

## Important Notes

1. **Upload it yourself only where you actually can** - In Claude Code the chat attachment is on disk and egress works, so `curl -sf -F "file=@<path>" "<upload_url>"` attaches it with zero user effort. **In Cowork it does not**: egress to `mcp.arfiti.com` is blocked, so the link is not a fallback there, it is the only route you can initiate. Check which you are before promising the user anything.

2. **Generate upload link immediately** - Don't wait for transaction approval. The file upload is independent.

3. **Upload link expires in 15 minutes** - If expired, generate a new one.

4. **No login required** - The upload link uses a secure token for authentication.

5. **Google Drive files don't need an upload link** - If the file is *already* in the org's connected Drive folder, `read_attachment(storage_url="connector://<connector_id>/<file_id>", content_type=<MIME type>)` pulls it into storage; use the returned `stored_url` as the attachment's `storage_url`. This is a pull route only — you cannot put a file into Drive to transfer it (see above).

6. **All content is searchable** - Even without the original file, extracted text and metadata are fully searchable.

---

## Common Errors and How to Avoid Them

### Error: "transaction_date is required"
**Cause**: Missing `transaction_date` field.
**Fix**: Always include `transaction_date` in YYYY-MM-DD format. Use the invoice date or document date.

### Error: "Missing required dimension 'cost_center'"
**Cause**: Organization has required dimensions configured but you didn't provide them.
**Fix**:
1. First, query `list_dimension_types` to find required dimensions
2. Include them in the `dimensions` object at header level

### Error: "dimensions must be an object/dict"
**Cause**: Passing dimensions as an array or string instead of object.
**Fix**: Use the simple object format:
```json
"dimensions": {"cost_center": "CC-1000", "location": "NYC"}
```
**NOT** this:
```json
"transaction_dimensions": [{"dimension_type": "cost_center", "dimension_value": "CC-1000"}]
```

### Error: "Line X: quantity must be greater than 0"
**Cause**: Line item has quantity of 0 or null.
**Fix**: Ensure every line has `quantity` > 0.

### Error: "Line X: Either item_id or account_number is required"
**Cause**: Line item missing both `item_id` and `account_number`.
**Fix**: Provide either `account_number` (GL account code) OR `item_id` (from items list).

---

## AR_INVOICE Required Fields

For customer invoices, use similar fields but with `customer_id` instead of `vendor_id`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `transaction_type_code` | string | **YES** | Must be `"AR_INVOICE"` |
| `legal_entity_id` | integer | **YES** | Legal entity ID |
| `customer_id` | integer | **YES** | Customer ID (lookup by name if needed) |
| `transaction_date` | string | **YES** | Transaction date in `YYYY-MM-DD` format |
| `invoice_date` | string | **YES** | Invoice date in `YYYY-MM-DD` format |
| `due_date` | string | **YES** | Due date in `YYYY-MM-DD` format |
| `dimensions` | object | **CONDITIONAL** | Header dimensions if required |
| `lines` | array | **YES** | At least one line item |

---

## Pre-Flight Checklist

Before calling `submit("transaction", "post", {...})`, verify:

- [ ] `transaction_type_code` is set (AP_INVOICE, AR_INVOICE, etc.)
- [ ] `legal_entity_id` is set
- [ ] `vendor_id` (for AP) or `customer_id` (for AR) is set
- [ ] `transaction_date` is set in YYYY-MM-DD format
- [ ] `invoice_date` is set in YYYY-MM-DD format (for invoices)
- [ ] `due_date` is set in YYYY-MM-DD format (for invoices)
- [ ] `dimensions` object includes all required dimensions (check `list_dimension_types` first)
- [ ] `lines` array has at least one line
- [ ] Each line has `description`, `quantity` > 0, `unit_price`, and either `account_number` or `item_id`


## Purchase evidence coverage

A paid bill, generated preview PDF, attachment metadata row or uploaded-but-unsubmitted receipt does not by itself prove that original source evidence is present and accepted. Card Expenses derives one documentation obligation from the purchase, its source receipts and all linked bills. Finance review records the current purchase version and evidence fingerprint; new source/evidence changes invalidate stale decisions. Use `card_purchase.manage` to link an existing bill or submit a reasoned evidence decision. This changes documentation relationships, not ledger settlement.

## Recover an existing document link

For a corrected/replacement document, use `submit("attachment", "update", data)`
with `attachment_id`, `legal_entity_id`, `expected_transaction_id` (current owner),
`transaction_id` (new owner), and a factual `reason`. Set `restore_deleted: true`
only for a deliberately restored soft-deleted attachment. Read both records first;
recovery is same-entity and same-document-type, keeps the file identity, and records
an audit history. Never re-upload evidence just to change its owner. A physically
deleted storage object needs its original file supplied again.

### Recovery permissions and authority-statement attachments

`attachment.update` recovery supports AP_INVOICE/AP_CREDIT_MEMO/AP_PAYMENT,
AR_INVOICE/AR_CREDIT_MEMO/AR_PAYMENT and JOURNAL_ENTRY, preserving the document type.
The approved workflow rechecks the submitter's current tenant membership, entity
scope and document-domain write permission; a generic workflow approval does not
grant accounting/AP/AR access. It preserves the storage key/hash and writes link history.

`TAX_RETURN` is a supported attachment owner for retained tax-authority evidence.
It is not an additional `attachment.update` recovery type. Verify uploaded file
bytes/hash before citing evidence; metadata-only records are not stored documents.

Emailed Bill sources can be read before posting with AP read permission and
access to the owning Bill draft/email-event entity. A task-bound read additionally
requires its exact reviewed source URL and MIME type. Knowing an email storage
key does not grant access to arbitrary organization email files.


### Payment-batch attachment salary boundary (Q2-ATT-01)

Admin attachment downloads and MCP stored-attachment reads require the owning
batch's entity and a batch-read grant (`payments:read`, `ap:read` or
`accounting:read`). A batch with stored payroll-run linkage, PAY-RUN reference,
or PAYROLL/SALARY_PAYMENT source provenance additionally requires `payroll:read`.
A mixed salary/reimbursement batch is protected as a whole. Ordinary employee
expense reimbursements alone do not classify a batch as salary. Payroll read
alone does not substitute for the baseline batch grant. Missing owners refuse.
This reuses the existing batch classification; legacy manual salary batches
without identifiable provenance still require a policy decision. This change
does not grant approval, payment execution or attachment-write authority.


### Generic attachment metadata queries (Q2-ATT-02)

MCP attachment query/search, single/batch get, counts and grouped totals apply
owning-record authorization before returning results or paginating. A filename,
storage key, extracted text or amount is protected by the same owner domain and
entity rules as the stored document. Unsupported owner types, missing or
cross-entity owners and deleted attachments are excluded. Payroll reversals
follow their source transaction; salary-batch attachments require the additive
payroll grant described above. Expense/card self-service ownership remains in
place, including own receipts for authenticated ordinary/unknown membership
roles. Read permission does not grant write or approval authority. These tested
query rules do not classify sensitive data embedded in arbitrary free text or
legacy manual salary records without identifiable provenance.


### Storage task visibility (QA branch; not deployed)

The bill-upload list requires AP read and the caller's entity scope. Its review
task link and status additionally require the shared task/thread read policy,
including supported nested draft, workflow and saga references and purchase
ownership. If a task is unreadable, Storage withholds its ID/status and shows a
generic processing state instead of an actionable review link. This does not
change the stored task or grant access to its payload.

Display redaction does not make the upload safe to retry. Reprocess eligibility
uses the actual case, task and live-event state before display fields are hidden;
posted or active work remains refused. Do not re-upload or edit task references
to bypass an access refusal. Arbitrary case narratives and unmapped metadata
remain outside this bounded task-authority verification.


### Storage bill transaction references (QA branch; not deployed)

A posted invoice link and number are displayed only when the current transaction
exists, is an AP invoice in the upload's entity, and the caller has AP read
permission. Storage displays the current transaction number, not the cached upload
number. Number search uses that same authorized record before the 100-row cap;
stale or orphan cached numbers cannot reveal a match. Filename search and uploads
without a posted invoice remain available within the existing upload scope.

Payroll access or wildcard grants do not turn a non-AP transaction into the bill
producer's AP invoice reference. Hiding a missing or unreadable invoice link does
not reset the upload or enable Reprocess. Case narratives, raw error text and
unmapped metadata remain separate acceptance work.


### Storage case outcomes (QA branch; not deployed)

A case's draft revision and supported outcome references must be readable before
Storage shows its case state, outcome detail or associated error text. This check
uses the shared request/execution graph independently of an active task: a readable
case with no current task still shows its result. Missing, foreign or forbidden
transaction/workflow/saga descendants withhold the case detail. Payroll grants
apply to supported nested references but do not waive draft AP-invoice identity.

The actual case/event state still determines retry eligibility first. A hidden
case cannot make active or posted work reprocessable. Storage shows a generic
processing/failure state when case details are withheld. Untyped free-text
references, duplicate-number narratives and errors without a bound case remain
separate acceptance work; this is not semantic classification of arbitrary prose.
