# Vendor Merge Workflow

**Workflow:** `vendor.merge`
**Validator:** `VendorMergeInput`

## Purpose

Consolidate a duplicate vendor master record into another. Use when agent-driven onboarding (or manual entry) created two records for the same payee — for example, "Google Cloud EMEA" as a duplicate of "Google Workspace".

The winning vendor is the record you keep; the losing vendor is the duplicate that is retired.

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `winning_vendor_id` | integer | Master vendor ID to keep (identity and global ID preserved) |
| `losing_vendor_id` | integer | Master vendor ID to retire (references moved off it, then soft-deactivated) |

## Optional Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `merge_reason` | string | null | Reason for the merge (e.g., "duplicate") — recorded in the audit trail |

## Example Payload

```json
{
  "winning_vendor_id": 42,
  "losing_vendor_id": 87,
  "merge_reason": "duplicate"
}
```

## What It Does

In a single transaction, every reference to the losing vendor is reassigned to the winning vendor:

- Transactions, transaction lines, and GL lines
- Bank and card statement lines
- MSEO entity links (`vendors` rows), dimensions, and contracts
- Agent learned-mappings (vendor_mapping memories)
- Any polymorphic party reference

Once all references are moved, the losing vendor is **soft-deactivated** (`is_active=false`). History is preserved — the losing record is never hard-deleted. The winning vendor's identity and `global_vendor_id` are kept.

## Approval

Runs in the **yellow lane**: requires a single approval by the `admin` role (configurable per client) before it executes.

> **Tip:** Call `get_submissions(action='schema', object_type="vendor", operation="merge")` to discover the exact required and optional fields before submitting.

---

## Field Details

### `winning_vendor_id`

- **Type:** `integer`
- **Required:** Yes
- **Default:** `PydanticUndefined`
- **Description:** Master vendor ID to keep. Its identity and `global_vendor_id` are preserved.
- **Constraints:** >0

### `losing_vendor_id`

- **Type:** `integer`
- **Required:** Yes
- **Default:** `PydanticUndefined`
- **Description:** Master vendor ID to retire. Every reference is reassigned to the winning vendor, then this record is soft-deactivated.
- **Constraints:** >0

### `merge_reason`

- **Type:** `string`
- **Required:** No
- **Default:** `null`
- **Description:** Reason for the merge, recorded in the audit trail.
- **Constraints:** max_length=500
