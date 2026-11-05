# User & Role Management Guide

This guide explains how to manage users, roles, permissions, and API keys in the AI-Native ERP system.

---

## Overview

The system uses a **two-layer access model**:

1. **Membership level** -- Controls access to the admin dashboard (owner, admin, member, viewer)
2. **Permission roles (RBAC)** -- Controls accounting operations via MCP tools (e.g., controller, ap_accountant)

These layers are independent. A user can be a "Viewer" membership (read-only dashboard) but have the "Controller" permission role (full accounting access via MCP).

**Permission refusals:** The internal dashboard workflow submit route returns
HTTP 403 for domain or target-entity permission denial, retaining a string
`detail` reason. Treat this as missing authority, not a transient server failure.
A null workflow `required_permission` does not bypass the shared domain floor.
The dashboard checks the shared domain and payroll record scope before enrichment,
claim creation and cached replay. Current access loss denies a repeated request
without exposing its earlier result. A preflight denial creates no execution or
claim; an execution-time failure remains uncertain until verified recovery. Keep
its request identity. This does not change MCP tool response contracts.

**What you can do:**
- List all roles (system and custom) for the organization
- List role assignments for specific users or all users
- Create custom roles with specific permission groups
- Assign roles to users with optional entity scoping and expiration
- Remove role assignments from users
- Create and revoke API keys for programmatic access
- Query API keys and audit logs

**Available Workflows (write operations via `submit`):**

| Workflow | Purpose | When to Use |
|----------|---------|-------------|
| `role.create` | Create a custom role with permissions | Organization needs a role beyond the 7 built-in system roles |
| `user_role.assign` | Assign a role to a user | Granting a user access to specific accounting operations |
| `api_key.create` | Generate a new API key | Setting up programmatic access (Claude Desktop, CI/CD) |
| `api_key.revoke` | Permanently revoke an API key | Rotating credentials or removing access |

**Available Read Tools:**

| Tool | Purpose |
|------|---------|
| `get_organization(action="list_roles")` | List all system and custom roles for the organization |
| `get_organization(action="list_user_roles", user_id=X)` | List roles assigned to a specific user |
| `get_organization(action="list_user_roles")` | List role assignments for all users |
| `get_organization(action="get_info")` | Get current organization details including membership |
| `get_organization(action="list_orgs")` | List all organizations the current user belongs to |
| `get_organization(action="get_rate_limit")` | Check current rate limit status |
| `get_entity("api_key", id=X)` | Get details of a specific API key |
| `query("api_key")` | List all API keys for the organization |
| `query("api_key", query="...")` | Search API keys by name or prefix |
| `query("audit_log", filters={...})` | View audit trail entries |

> **IMPORTANT — Schema Discovery Required**: Before calling `submit()` for any workflow below, you MUST first call `get_submissions(action='schema', object_type, operation)` to discover the exact required and optional fields. Each organization configures different field requirements. Never assume the fields listed below are complete — always check the schema first.

---

## Key Concepts

### Membership Levels

Membership is set on each user's organization association and controls admin dashboard access.

| Level | Value | Description |
|-------|-------|-------------|
| **Owner** | `owner` | Full organization control. Cannot be removed. Auto-assigned to org creator. |
| **Admin** | `admin` | Can manage team members, settings, and API keys. |
| **Member** | `user` | Standard dashboard access. Can view data and use assigned features. |
| **Viewer** | `viewer` | Read-only access to the dashboard. |

Owner is not selectable when inviting -- it is only for the organization creator.

### Built-in System Roles

Seven system roles are seeded by migration and cannot be modified or deactivated:

| Role | Slug | Permissions |
|------|------|-------------|
| **Administrator** | `admin` | `admin:*` (full system access) |
| **Controller** | `controller` | `accounting:write`, `accounting:read`, `ar:write`, `ar:read`, `ap:write`, `ap:read`, `master_data:read`, `reports:read` |
| **AP Accountant** | `ap_accountant` | `ap:write`, `ap:read`, `master_data:write`, `master_data:read`, `accounting:read` |
| **AR Accountant** | `ar_accountant` | `ar:write`, `ar:read`, `master_data:write`, `master_data:read`, `accounting:read` |
| **Auditor** | `auditor` | `accounting:read`, `ar:read`, `ap:read`, `master_data:read`, `reports:read`, `audit:read`, `payroll:read` |
| **Investor** | `investor` | `reports:read` |
| **Payroll Specialist** | `payroll_specialist` | `payroll:read`, `payroll:write`, `payroll:approve`, `payroll:post`, `master_data:read`, `accounting:read`, `reports:read` |

### Permission Groups

Permissions follow the format `category:action`. Wildcard (`category:*`) grants all actions within a category.

| Category | Available Actions |
|----------|-------------------|
| `admin` | `read`, `write`, `delete`, `*` |
| `accounting` | `read`, `write`, `post`, `close`, `*` |
| `ar` | `read`, `write`, `post`, `void`, `*` |
| `ap` | `read`, `write`, `approve`, `post`, `void`, `*` |
| `payments` | `read`, `write`, `approve`, `void`, `*` |
| `master_data` | `read`, `write`, `delete`, `*` |
| `dimensions` | `read`, `write`, `delete`, `*` |
| `reports` | `read`, `*` |
| `config` | `read`, `write`, `*` |
| `global_ids` | `read`, `write`, `*` |
| `audit` | `read` |

### Entity Scoping

Roles can be scoped to specific legal entities:

- **All entities** -- `entity_ids` is empty or omitted. The role applies across all entities.
- **Specific entities** -- `entity_ids` lists the entity IDs. The role only applies to those entities.

A user can have the same role assigned multiple times with different entity scopes. For example:
- Controller role scoped to Entity 1 (US operations)
- AR Accountant role scoped to Entity 2 (UK operations)

**Membership is the ceiling.** Owner/admin wildcards grant operations but do
not bypass restricted membership or API-key entity scope. Role assignments
union their scopes within that ceiling. An unrestricted role cannot enlarge
restricted membership access.

Legal-entity list/search results and pagination counts include only allowed
entities. Single and batch `get_entity("legal_entity", ...)` reads report
excluded IDs as not found, just like nonexistent IDs; do not infer that an
entity exists from that response. Explicit out-of-scope query filters can
return a permission error. Legal-entity aggregation is unsupported. Explain
the access restriction and refer the user to an administrator; do not retry
through another tool to bypass it. Unrestricted callers see the full catalog
within their current organization.

### Authentication Methods

The system supports two auth methods transparently:

| Method | Header | Format | Use Case |
|--------|--------|--------|----------|
| **OAuth 2.1** | `Authorization: Bearer <token>` | JWT from the sign-in provider (Auth0, or WorkOS AuthKit once switched) | Claude.ai, admin dashboard |
| **API Keys** | `X-API-Key: <key>` | `sk_<org_id>_<random_64_chars>` | Claude Desktop, programmatic access |

Both methods produce the same `AuthContext`, so tools work identically regardless of auth method.

---

## Creating a Custom Role

Use the `role.create` workflow when the 7 built-in system roles do not cover the organization's needs.

**Only owners and admins can create roles.** The check reads the caller's organization membership at execution, not their role permissions. Anyone else gets `permission_denied` with the sentence "Only owners and admins can change roles in this organization. Ask one of them to make the change." Relay that sentence and point the user to an owner or admin; don't retry or rework the payload.

```javascript
// Step 1: Discover required fields
schema = get_submissions(action='schema', object_type="role", operation="create")

// Step 2: Submit with discovered fields
// Tip: Use validate_only=true to check payload before submitting
```
```
submit("role", "create", {
    "role_name": "payment_manager",
    "description": "Manages all payment operations",
    "permissions": ["payments:*", "ap:read", "ar:read", "master_data:read"]
})
```

**Required Fields:**
- `role_name` (string) -- Lowercase alphanumeric + underscores. Must be unique within the organization. Reserved names are refused in any letter case: `owner`, `admin`, `admin_membership`, `system` and every system role name (`controller`, `ap_accountant`, `ar_accountant`, `auditor`, `investor`, `payroll_specialist`). The refusal is `reserved_role_name` with "That role name is reserved. Choose another name."
- `permissions` (array of strings) -- Each in `category:action` format. At least one permission required.

**Optional Fields:**
- `description` (string) -- Human-readable description of the role's purpose.

**Response:**
```json
{
  "success": true,
  "role_id": 15,
  "role_name": "payment_manager",
  "description": "Manages all payment operations",
  "permissions": ["payments:*", "ap:read", "ar:read", "master_data:read"],
  "message": "Custom role 'payment_manager' created"
}
```

**Validation rules:**
- `role_name` must match pattern: lowercase letters, digits, underscores only
- Cannot use a reserved name (see above)
- A role's name never grants access by itself; only its permissions do
- Each permission must be in `category:action` format with a valid category
- Role name must be unique within the organization (different organizations can have same custom role names)

---

## Assigning a Role to a User

Use the `user_role.assign` workflow to grant a user a specific permission role.

**Only owners and admins can assign roles**, including to themselves. The check reads the caller's organization membership at execution. Anyone else gets `permission_denied` with "Only owners and admins can change roles in this organization. Ask one of them to make the change." Relay it and point the user to an owner or admin.

**If you are an agent, a role or access change waits for a person.** `role.create`, `user_role.assign`, `organization_user.invite`, `organization_user.update`, `organization_user.remove` and `organization_user.revoke_invite` submitted from an agent return `status: "pending"`; an owner or admin approves on the dashboard. You cannot approve it with `manage_submissions(action="decide")`. Tell the user it is waiting for their approval. If the organisation's workflow has no approval step, the submission is refused; ask an owner or admin to add one.

```
submit("user_role", "assign", {
    "user_id": 42,
    "role_name": "controller",
    "entity_ids": [1, 2],
    "expires_at": "2026-12-31T00:00:00Z"
})
```

**Required Fields:**
- `user_id` (integer) -- The ID of the user to assign the role to.
- `role_name` (string) -- The slug of the role to assign (system or custom).

**Optional Fields:**
- `entity_ids` (array of integers) -- Scope the role to specific legal entity IDs. Omit or pass empty array for all-entity access.
- `expires_at` (string, ISO 8601 datetime) -- When the role assignment should automatically expire. Omit for permanent assignment.

**Response:**
```json
{
  "success": true,
  "user_id": 42,
  "role_name": "controller",
  "entity_ids": [1, 2],
  "expires_at": "2026-12-31T00:00:00Z",
  "message": "Role 'controller' assigned to user 42"
}
```

---

## Removing a Role from a User

Use the `manage_organization` tool to remove a role assignment.

```
manage_organization(action="remove_role", user_id=42, role_name="controller")
```

**Parameters:**
- `user_id` (integer) -- The user to remove the role from.
- `role_name` (string) -- The role slug to remove.

**Protection:** The system prevents removing the last admin role from an organization -- at least one user must always have admin access.

`remove_role`, `list_roles` and `list_user_roles` need owner or admin membership of the current organization; RBAC permissions such as `admin:*` don't count.

---

## Listing Roles

### List All Available Roles

```
get_organization(action="list_roles")
```

Returns all system roles (7 built-in) and any custom roles created by the organization.

### List Role Assignments for a User

```
get_organization(action="list_user_roles", user_id=42)
```

Returns all role assignments for the specified user, including entity scoping and expiration.

### List All Role Assignments

```
get_organization(action="list_user_roles")
```

Returns role assignments for all users in the organization.

---

## API Key Management

API keys provide programmatic access to MCP tools. They are organization-scoped and support the same permission model as OAuth tokens.

### Creating an API Key

```
submit("api_key", "create", {
    "name": "CI/CD Pipeline Key",
    "scope": {"permissions": ["read", "write"]}
})
```

**Required Fields:**
- `name` (string) -- Descriptive name for the key.

**Optional Fields:**
- `scope` (object) -- `permissions`: any of `read`, `write`, `delete`; `entities`: legal entity IDs, clamped to the creator's own entity access. Omit `scope` for a read key over the creator's entities.

**A key carries only `read`, `write` and `delete`.** Anything else (`*`, `admin:*`, `ap:write`, ...) is refused with `permission_denied`: "An API key can carry only read, write and delete. Remove the other permissions, then submit again." A caller without write access can't create a `write` or `delete` key, and `rate_limit` is set by the platform, not the scope. The key also acts with its creator's own role permissions and membership, re-read on every request, so it never holds more than its creator.

**Response includes the key value only once** -- it cannot be retrieved after creation. Store it securely.

### Revoking an API Key

```
submit("api_key", "revoke", {
    "api_key_id": 5
})
```

Permanently revokes the key. This action cannot be undone. The key immediately stops working.

### Querying API Keys

```
query("api_key")
```

Returns all API keys for the organization with fields: `id`, `key_prefix`, `name`, `scope`, `last_used_at`, `expires_at`, `created_at`.

```
get_entity("api_key", id=5)
```

Returns detailed information for a specific API key.

```
query("api_key", query="CI/CD")
```

Searches API keys by name or key prefix.

---

## Entity-Level Access Control

Access control has two layers that work together:

### Membership Entity Access

Set on the user's organization membership. Controls which legal entities a user can see in the dashboard.

- **All entities** -- `entity_access` is NULL or empty. User sees all entities.
- **Specific entities** -- `entity_access` lists allowed entity IDs.

### Role Entity Scoping

Set on individual role assignments. Controls which entities a role's permissions apply to.

- **All entities** -- `entity_ids` is empty. The role's permissions apply everywhere.
- **Specific entities** -- `entity_ids` lists the entities where this role is active.

Both layers are checked. A user needs both membership access to an entity AND a role scoped to that entity to perform operations on it.

---

## Multi-Organization Support

Users can belong to multiple organizations. The auth system handles org selection automatically.

### View All Organizations

```
get_organization(action="list_orgs")
```

Returns all organizations the current user belongs to.

### Switch Active Organization

```
manage_organization(action="switch", organization_id=5)
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

### Partner Organizations

Current owners/admins of partner organizations can create client organizations and mint client keys. Both actions check live membership; a write permission alone is insufficient:

```
manage_organization(action="create_client", client_name="Acme Corp", client_slug="acme")
```

When a client org is created, partner owners and admins receive admin membership in it. Ordinary partner members are not propagated.

---

## Invitation Flow

Use `submit("organization_user", "invite", {...})` or Admin Users & team. Payload:

```json
{"email":"invitee@example.com","membership_role":"user","entity_ids":null,"role_assignments":[{"role_name":"ap_accountant","entity_ids":null}]}
```

Owner/admin membership is required at execution, in addition to the definition's
`admin:write` permission. Only owners can grant owner membership. Approvals defer
the grant and email. Optional `client_org_access` entries use `organization_id`
and `role`; the actor must manage every linked client.

`revoke_invite` and `resend_invite` take `{"invitation_id":123}`. Revocation is soft
and covers linked child invitations; resend retries unsent delivery. Inspect
`emailSent`/`delivery_status`, not just workflow success. Do not request or expose
invite tokens. Acceptance is through verified Auth0 login in Admin, never an agent
asserting another person's identity. It checks the invited email, original inviter's
current authority, and every grant; replay/expiry/revocation fail atomically.
Existing memberships and their scopes/roles are preserved unchanged.

If Admin cannot confirm acceptance because the response was lost or malformed,
check organization access or ask the administrator before trying again. Acceptance
may already have committed; the callback does not automatically retry. Do not infer
that no grant occurred or resend a capability from this message. Structured errors
show a generic refusal, and success navigation requires a positive integer company
ID. Verified identity and atomic backend validation remain required.
If the initial invitation lookup fails, Admin shows administrator guidance and
logs only a fixed failure message. Do not request database diagnostics or invitation
tokens from the user to retry this flow.

The success page no longer displays the legacy different-email acceptance notice:
acceptance requires the verified invited email. Its company value is only a
connection hint, not proof of membership. Missing or invalid company hints use the
generic MCP connection URL; valid positive integer hints retain the company URL.
Opening or editing this informational page does not grant access.

---

## Linked Employees

Team members can be linked to employee records. When a `system.users` record matches a `master_employees.user_id`, the team list displays the linked employee's ID and name. This enables role-to-employee coordination -- for example, ensuring an employee who handles AP is assigned the `ap_accountant` role.

---

## Audit Trail

Governed team operations have workflow instances. Invitation acceptance and initial
organization provisioning have atomic completed receipts; these do not claim a
complete team Timeline or coverage of every legacy administration operation.

```
query("audit_log", filters={"action": "role_assign"})
```

Query the audit log to review who made access control changes and when.

---

## Common Scenarios

### Set Up a New Accountant

1. Admin sends invitation via dashboard with membership level and roles
2. After user accepts, verify role assignment:
   ```
   get_organization(action="list_user_roles", user_id=42)
   ```
3. If additional roles needed:
   ```
   submit("user_role", "assign", {
       "user_id": 42,
       "role_name": "ap_accountant",
       "entity_ids": [1, 2]
   })
   ```

### Create a Read-Only Auditor Role

The built-in `auditor` role covers most cases. If a more restricted role is needed:

```
submit("role", "create", {
    "role_name": "limited_auditor",
    "description": "Read-only access to GL and reports only",
    "permissions": ["accounting:read", "reports:read"]
})
```

Then assign it:

```
submit("user_role", "assign", {
    "user_id": 55,
    "role_name": "limited_auditor"
})
```

### Grant Temporary Access

Assign a role with expiration for contractors or temporary staff:

```
submit("user_role", "assign", {
    "user_id": 60,
    "role_name": "ap_accountant",
    "entity_ids": [3],
    "expires_at": "2026-06-30T00:00:00Z"
})
```

### Restrict a User to Specific Entities

Assign the same role multiple times with different entity scopes:

```
submit("user_role", "assign", {
    "user_id": 42,
    "role_name": "controller",
    "entity_ids": [1]
})
```

```
submit("user_role", "assign", {
    "user_id": 42,
    "role_name": "ar_accountant",
    "entity_ids": [2, 3]
})
```

This gives the user Controller access to Entity 1 and AR Accountant access to Entities 2 and 3.

### Set Up Programmatic Access

1. Create an API key:
   ```
   submit("api_key", "create", {
       "name": "Claude Desktop - Finance Team"
   })
   ```
2. Store the returned key securely (shown only once)
3. Use the key in the `X-API-Key` header for API calls

### Revoke Compromised Credentials

1. Find the API key:
   ```
   query("api_key", query="Finance Team")
   ```
2. Revoke it:
   ```
   submit("api_key", "revoke", {
       "api_key_id": 5
   })
   ```
3. Create a replacement:
   ```
   submit("api_key", "create", {
       "name": "Claude Desktop - Finance Team (rotated)"
   })
   ```

### Review Who Has Access

1. List all role assignments:
   ```
   get_organization(action="list_user_roles")
   ```
2. List all API keys:
   ```
   query("api_key")
   ```
3. Check audit trail for recent changes:
   ```
   query("audit_log", filters={"action": "role_assign"})
   ```

---

## Database Schema Reference

### Tables

| Table | Purpose |
|-------|---------|
| `system.roles` | Role definitions (system + custom) |
| `system.role_permissions` | Permission groups assigned to each role |
| `system.user_roles` | Role assignments linking users to roles with entity scoping |
| `system.organization_users` | Organization membership (level + entity access) |
| `system.api_keys` | API key records (hashed, never stored in plain text) |
| `system.user_invitations` | Pending and accepted team invitations |
| `system.user_external_identities` | Sign-in identities by issuer and subject; how a token finds its user (never email) |
| `system.user_linked_identities` | Legacy: multiple Auth0 identities per user, kept until Auth0 is retired |
| `system.audit_logs` | Audit trail for all operations |

### Key Relationships

- `system.roles.organization_id` is NULL for system roles, set for custom roles
- `system.user_roles.entity_ids` is an INTEGER array -- empty means all entities
- `system.user_roles.expires_at` enables time-limited role assignments
- `system.organization_users.entity_access` is an INTEGER array -- NULL means all entities

---

## Tips & Best Practices

### 1. Role Selection
- Start with built-in system roles before creating custom ones
- Use entity scoping to restrict roles rather than creating overly narrow custom roles
- The `admin` role includes `admin:*` which grants full access -- assign sparingly

### 2. Entity Scoping
- Scope roles to specific entities when users should only operate within certain business units
- A user with no entity scoping on any role has access to all entities
- Combine multiple scoped role assignments for fine-grained control

### 3. API Key Security
- Use descriptive names so keys can be identified for rotation
- Set expiration dates for temporary access
- Revoke and rotate keys regularly
- Never share API keys in chat -- use the admin dashboard for credential entry

### 4. Permission Checking
- OAuth membership, roles and entity scope are reloaded during request authentication.
- Streamable HTTP tools use the current request context, not the session-opening snapshot.
- Verify `get_info` after a saved role change; a reconnect is not the role-change mechanism.

### 5. Custom Role Naming
- Use lowercase alphanumeric with underscores: `payment_manager`, `inventory_clerk`
- Be descriptive: `senior_accountant` is better than `role1`
- Cannot reuse system role slugs

### 6. Audit Compliance
- All role assignments and removals are logged automatically
- API key creation and revocation are logged
- Use the audit log to demonstrate access control compliance

---

## End of Guide

This guide covers complete user and role management including membership levels, RBAC permissions, entity scoping, API key management, custom roles, and access control best practices for Claude.ai automation.


## Team update and removal workflows

With migration 620 applied, `organization_user.update` and
`organization_user.remove` are registered workflow operations. Their definitions
require `admin:write`; execution additionally requires current **owner or admin
organization membership**, so an accounting RBAC admin role alone is insufficient.
The Admin member drawer submits these operations with the authenticated actor.
Since migrations 833/834 the shipped `organization_user.update`, `.invite`, `.remove` and `.revoke_invite` definitions
carry one "Owner or admin approves" step that is skipped on the green lane: a
person's own change runs directly, an agent's change waits for an owner or admin
(AR-460). Other configured approval steps defer the change. The drawer reports a
pending submission instead of claiming it was applied.

- Update requires `user_id` and `membership_role` (`owner`, `admin`, `accountant`,
  `user`, `viewer`). `entity_ids: null` means all; a supplied list must contain
  positive IDs from this organization. `role_assignments` replaces accounting
  assignments when supplied; omission preserves them and an explicit empty list
  removes them. Each assignment
  has `role_name` and optional `entity_ids` with the same scope convention.
- Optional `full_name` changes the shared user name across organizations; omit it
  to preserve the name. Supplied role assignments replace the complete set.
- Remove requires `user_id`; membership deletion and role deactivation are atomic.
  Owners cannot be removed. Only an owner can grant/change owner membership, and
  the last owner cannot be demoted. Changes serialize per organization.
- Actor membership and target organization are checked again at execution, after
  any approval wait. Only active roles belonging to the organization or system
  roles can be assigned. Existing assignment expiry dates are preserved.

Workflow instances retain the submitting user and an object link using the target
user ID within the workflow's organization. Migrations 621–622 add invitation
operations and `organization.update` (name, optional status). Organization creation
and invitation acceptance have separate capability/bootstrap receipts rather than
requiring a nonexistent prior membership. Deploy migrations and MCP before Admin;
full visual Timeline and real OAuth acceptance remain separate verification gates.

Admin browser signup uses the same verified-identity checks as the signup API.
A matching email is not authority to replace or link an Auth0 identity. Conflicting
or inactive accounts require administrator resolution. Users awaiting invitations
must redeem their invitation; opening onboarding grants no organization access.


### OAuth role-change freshness

OAuth authorization reloads current membership, role grants and entity scope on
every validation, ignoring old cached owner contexts. A roleless viewer is a
valid restricted identity; token consent scopes cannot restore removed write
permissions. After a role change, verify the connected user and company and test
both allowed reads and denied writes. Keep a separate owner available for recovery;
a restricted user must not restore their own administrative access.

The submit gateway (including validate-only and idempotent retries) and workflow
start boundary refuse callers with no mutation grants before writing an idempotency
claim or creating a workflow. This baseline applies even to legacy definitions
with no required_permission. Scoped writers must still satisfy configured domain
permissions and entity scope; the baseline does not supply missing domain policy.


### Saving membership and permission roles in Admin

The full member editor (`/team/{userId}/edit`) submits membership level, entity
access, and permission-role assignments together. Use an owner/admin session in
the intended organization. Selecting Member and AP Accountant does not itself
apply the change: wait for “Team member updated”. A review-pending response means
the change has not yet been applied. Validation or permission errors leave saved
authority unchanged; confirm effective MCP permissions with `get_info`.

The membership field uses a native select. Existing Accountant memberships are
preserved on unchanged saves; selecting Member does not automatically assign
AP Accountant. Owner membership remains non-editable in this full-page form.


Streamable HTTP role propagation: the context resolver prefers the current
middleware-validated Request carried by the MCP SDK over inherited session
ContextVars. Explicit agent/task bindings retain their narrower authority. Missing
HTTP authentication context fails closed. Regression coverage includes promotion
and demotion on the same MCP session. Check deployment evidence in the active
permissions plan before treating this fix as live in an environment.


### Financial domain authorization and Admin access (2026-09-30)

A non-configurable permission floor now applies before submit validation,
idempotent replay, workflow creation and execution: transaction.post requires
ap:write for AP/expense types, ar:write for AR/recurring invoices, payroll:post
for payroll postings, and accounting:write for other types. Payroll workflow
objects require payroll:write, with separate payroll:approve and payroll:post
for those stages (process_payment also requires payroll:post). Configured
workflow permissions are additional restrictions; a missing setting cannot
remove this floor. The transaction.create compatibility alias has the same posting
floor. Existing transaction update, reverse, cancel and delete operations resolve
the required domain from the stored transaction type in the authenticated company
and requested legal entity, ignoring submitted type hints. Checks run before
validation/idempotent replay, workflow creation, and executor dispatch (after
resolving delegated task authority). Missing or deleted documents fail closed;
a repeated hard-delete cannot replay successfully once its source row is gone.
AP edits/reversals require ap:write, AR requires ar:write, payroll requires
payroll:post, and unclassified/other ledger types require accounting:write.
Configured permissions, entity restrictions and accounting-state checks still
apply. Other workflow domains remain in the role-matrix audit.

Admin team editing requires owner/admin membership before rendering; server
mutation checks remain in place. Subscription billing pages and procedures
require owner membership, including Checkout and payment-method portal creation.
The user menu displays authenticated email, active company and membership;
Member is the display label for user membership. Vendor details normalize the
master ID to a number so bill-note queries can start, and note-loading errors
are shown explicitly. Billing load failures no longer imply an expired trial.

Financial workflow completion (transactions and payroll) reloads the submitter's
current tenant membership, role grants and entity scope before executor dispatch.
Approval does not grant synthetic full write permissions. Removed membership or
revoked domain authority blocks execution, including worker-driven completion.


### Reversal read permissions (E2E-037, 2026-09-30)

A REVERSAL keeps its displayed document type but inherits read authority from its
original transaction. Nested reversals follow the source chain in the same company
and legal entity. Missing sources, cross-entity links, cycles and chains exceeding
32 hops deny restricted readers; owner/admin wildcard access remains unchanged.
AP reversals require ap:read, AR reversals ar:read and payroll reversals payroll:read.
General accounting read access does not grant access to a payroll reversal.

MCP single/batch reads, lists, counts, aggregates, journal lines and transaction
attachments use this source classification. A transaction_type=REVERSAL filter
still means reversal records; it cannot override the independent permission filter.
Admin transaction lists, totals, filter metadata, details, timelines, related reads
and attachment download authorization use the same transaction permission map.
Permission classification is internal; returned document types remain unchanged.
Existing entity scope and configured write permissions still apply. This read fix
does not alter the lifecycle write-policy review or certify all financial reports.

Transaction attachment reads also require the attachment and linked transaction
to belong to the same legal entity; a mismatched or missing parent fails closed.


### Admin effective entity access (E2E-043)

Admin entity filters and direct entity checks combine the union of active,
unexpired permission-role entity assignments with the membership entity ceiling.
For example, Member + membership All entities + Payroll Specialist scoped to
entity 2 can access only entity 2. Null/empty role scope means all entities;
multiple restricted roles contribute their union. Owner/Admin membership bypasses
the role restriction, while the membership ceiling remains in effect in Admin.
No active role assignments leave the membership scope in effect; this does not
grant domain permissions. An empty intersection denies every entity.

Admin reloads this scope for each authorization check. A role change made from
another owner session therefore applies to the next request without a server
restart. Refresh an already-open page to replace previously rendered data.
The entity selector, employee reads, and payroll routes use the shared helper.
Staging verification for this fix is tracked in the active E2E results document.

Direct employee detail/history lookups require an employee assignment in an
allowed entity for scoped callers. Related addresses, bank accounts, dimensions,
and history are filtered by entity; unscoped history is withheld from scoped
callers. Compensation, tax settings, and deduction queries always constrain
stored entity IDs, even when a request supplies only a global employee ID.


### Unreleased wizard integration (2026-10-01)

Production-release reconciliation is in progress. The new Admin setup wizard
retains subject-only membership lookup and verified-email signup; matching an
email never authorizes changing an existing account's Auth0 identity. A pending
invitation must be accepted before separate-company signup. Existing-company
setup and onboarding key creation/reveal require owner/admin membership.
Do not describe this integration as deployed or the role-testing program as
complete: full migration/release verification and production acceptance are still pending.
The old signup endpoints are removed; use the current Admin wizard, whose setup
transaction includes the schema and audit receipt. Local real-database tests cover
creation, retry, identity/invitation denial and rollback.


### Quick member editor: membership and accounting permissions

The quick member drawer labels its selector **Membership level**. Membership
controls workspace access; accounting operations additionally depend on assigned
permission roles. Member and Accountant labels do not promise posting, period
closing or other domain permissions by themselves.

For an existing accepted member, **Manage accounting permissions** opens the
existing `/team/{userId}/edit` form, including permission roles and their entity
scopes. Save drawer changes before following that link. Quick saves continue to
omit role assignments and therefore preserve the existing assignments.
For a new invitation, **Invite with accounting permissions** opens `/team/invite`;
unsaved drawer entries are not carried over. Pending invitations show guidance to
manage roles after acceptance instead of linking to a nonexistent member record.
This change does not alter role grants or server-side authorization.


### Owner/admin entity limits

Owner/admin operation permissions do not override the membership entity list.
Reads, reports, connector access and workflow writes/edits stay within the
caller’s effective entities, including an API key’s narrower scope. NULL or
empty membership access remains unrestricted; no-access intersections never
become unrestricted.


### Master-data workflow authorization

Vendor, customer, employee and project mutation workflows require `master_data:write`
at submission (including validation-only and cached replay) and execution, even
when an older workflow definition has no configured permission. AP/AR write
permissions alone do not grant master-data editing. The default Controller role
has master-data read access only; assign an appropriate additional permission role
if editing is intended. Existing entity restrictions and extra workflow permissions
still apply. Employee payloads containing compensation or tax settings also require
`payroll:write`; standalone payroll detail workflows retain their payroll permission.

After human approval, these workflows reload the submitter's current membership,
permissions and entity scope. Approval does not lend the reviewer's authority to the
submitter. If access was removed while awaiting review, execution must fail; restore
only intended access and make a new submission after reviewing the failed workflow.
Do not bypass the denial or reuse a recorded human decision.

Installed native agents derive this permission only after their current/pinned workflow capability is verified. Authored agents retain their creator/revision-bound RBAC; a workflow capability alone does not elevate them. No agent run acts with a person's permissions.

### Report-only access to workflow approvals

Workflow instances use UUIDs. Pass the UUID returned by `query("workflow_instance", ...)`
to `get_entity("workflow_instance", id="<uuid>")`, or fetch several with
`get_entity("workflow_instance", ids=["<uuid>", ...])`. Batch lookup does not
support related records. Read authorization runs before UUID validation; the
organization filter is enforced for lookup and query, including batches.
An explicit different organization is rejected. This correction does not add per-domain
or per-entity payload isolation beyond the existing workflow read policy.

Generic `workflow_task` reads use integer task IDs and inherit organization
scope from the parent workflow instance. Single/batch lookup, query results,
pagination counts exclude tasks outside the current organization,
including tasks whose parent cannot be found. Workflow-task aggregation is not
exposed by the MCP query tool; the shared SQL builder is scoped if used internally.
Supplying a different organization
is refused. This does not grant write access or resolve the separate per-domain
and per-entity workflow payload policy.


Workflow execution payloads and decisions are operational data, not financial
reports. Admin task/instance detail, timelines, related-record context, activity
and attachment links require a current operational read grant. MCP generic
`workflow_task` / `workflow_instance` reads and `get_submissions` actions `my_tasks`,
`task_details` and `history` enforce the same baseline, including their legacy
entry points. A previous assignment, submission or completed approval does not
preserve access after the user becomes report-only.

The operational grants are `accounting:read`, `ap:read`, `ar:read`, `payroll:read`,
`master_data:read`, `payments:read` or `audit:read`, including matching wildcards
and owner/admin authority. Legacy agent API-key `read` scope is preserved.
Existing object, organization and entity checks continue to apply; this baseline
does not replace a complete per-domain payload isolation policy.

Report-only users do not receive historical workflow-task or workflow-instance
notification previews, including rows identified by a task ID. These records
remain stored; restoring an authorized operational role restores normal reads.
Financial reports and workflow schema discovery remain available under their
existing permissions. No migration or role reconfiguration is required.


### Notification visibility after role changes

The Admin notification feed and unread counts require a current operational read
permission (the same baseline as agent tasks). Report-only users, including
Investor, receive an empty feed and zero unread counts. This covers processed
transaction descriptions and agent outcomes as well as approval notifications,
regardless of the event type or link. Previously delivered rows remain stored.
Restoring operational access restores the normal feed.

Admin-only alerts additionally require current owner/admin membership; historical
recipient assignment does not preserve access after a downgrade. These checks
apply when the feed or count is requested. Linked workflow task/instance notifications
now also require current entity access and the workflow AP/AR object-domain and payroll-payload read policy.
Agent-request links require entity access and the request thread's domain/provenance
policy. These predicates apply before pagination and unread counts; missing or
malformed supported links are withheld. Unlinked/free-text notifications, other
routes and other workflow object-domain classification remain open. No migration or
role reconfiguration is required; hosted acceptance is not yet verified.


### Read-only workflow mutation boundary

Read-only roles such as Auditor and Investor cannot add workflow comments, edit
workflow payloads, or approve/reject/request changes through MCP. These actions
check mutation authority before database access, including legacy entry points.
Admin payload edits and decisions also check current operational write authority
before forwarding to the backend. Existing assignment, domain, organization and
payload-integrity rules still apply; a write grant alone does not bypass them.

Authorized comments resolve the actor using the user's full name and store the
audit comment in a transaction. A failed actor lookup must not leave a comment
behind. For failures observed on older versions, inspect workflow history before
retrying: the old path could save a comment and then report an internal error.
No migration is required.


### Optional employee identity during workflow execution

Workflow execution reloads the caller's current membership and permissions.
Its read-only employee lookup runs inside a savepoint: if employee data is
unavailable, the lookup returns no employee without leaving the surrounding
workflow transaction aborted. This fallback creates no employee, grants no
permission and does not bypass an operation's employee-identity requirement.

### Task action visibility

The Admin task page uses current server-derived action permissions. Pending
tasks are readable by authorized operational readers, but read-only users see
a viewing-only message instead of payload-edit and decision controls. A writer
can decide a task only when unassigned, assigned to them, or permitted by the
existing owner/admin or platform-support policy. Otherwise the page explains
that another user is assigned. Payload editing retains its separate write
permission policy; assignment alone does not forbid editing. Payment-batch
approval controls follow the same decision gate. Missing capabilities hide
actions, and server checks remain authoritative on every mutation. These
capabilities do not guarantee that downstream business validation will pass.


### Payroll workflow payload reads in Admin

Payroll workflow details, supporting task context, timelines and attachment links
require `payroll:read` (or a matching wildcard). An AP, AR, accounting or
master-data read grant alone does not authorize these payroll payloads. The
same filter applies before pagination/counting to Admin workflow instances,
activity, My Tasks and dashboard waiting tasks. Existing organization checks
and decision-assignment rules remain in force.

The payroll classification includes payroll objects, employee compensation/tax/
deduction objects, nested employee payroll commands, and transaction payloads
explicitly identified as PAYROLL or SALARY_PAYMENT. This patch is not a complete
per-domain/entity visibility policy: generic MCP workflow reads, agent payloads
and transaction workflows without a payroll type in the payload need separate
coverage. Do not interpret assignment or a general operational grant as proof
that those remaining boundaries have been verified.


### Workflow read hardening (implementation branch; release verification pending)

Salary payment batches require `payroll:read` in addition to the existing
batch-read grant. Employee expense reimbursement lines alone do not make a
batch payroll-sensitive. Salary classification checks explicit PAYROLL or
SALARY_PAYMENT source types, PAY-RUN references, stored source transaction
types, and payroll-run links. A mixed batch containing salary payments is
protected as a whole. Admin workflow collection filters use the same salary
provenance rule as workflow details, including payloads containing only a batch
ID. Missing referenced batches fail closed for readers without payroll access.

MCP history and task reads check the underlying object permission and caller's
entity membership before returning or enriching payloads/actions. A wildcard
does not bypass entity restrictions. A restricted reader cannot read workflows
with missing entity metadata; retain an owner for reviewing legacy metadata.
Stored transaction types override payload hints. Generic MCP workflow get,
batched get, list/search and count apply the payroll/entity filter in SQL before
pagination; generic payment-batch reads also exclude salary batches without
payroll access. This does not grant approval authority or execute a workflow.

Remaining scope: agent request/response business-domain isolation; full Admin
entity/domain parity beyond the payroll workflow check; legacy manual salary
batches without identifiable salary provenance. Do not treat this scope as
complete certification of all read surfaces. No schema migration is required.


### Agent request domain reads (implementation branch; release verification pending)

Agent request detail, outcome, review lines, linked request summaries, task-thread
readers, My Tasks and waiting counts
apply additive source and request/response domain checks. MCP generic request
get/list/count uses the same rules. Organization, assignment and entity checks
still apply; a read grant never authorizes an approval or business mutation.

Known payroll source/object/owner markers, compensation metadata and inline
salary payment markers require `payroll:read`. Bill, expense, card and purchase
order markers require `ap:read`; customer invoice and sales order markers
require `ar:read`. Conflicting markers require every indicated domain: a bill
hint does not downgrade a payroll source. Employee payee type alone does not
classify an expense reimbursement as salary.

Transaction references are checked against the tenant's stored transaction,
including reversal ancestry, in the request's entity. Payment-batch references
are checked against stored salary provenance. Missing references fail closed.
A forbidden sibling or different entity within a request thread prevents
reading that thread. Lists/counts filter before pagination. An authorized owner
should correct source metadata through normal supported administration; do not
remove provenance or grant broader access simply to make a task visible.

This is not complete classification of arbitrary legacy request bodies.
Unclassified free text, unknown source types and arbitrary nested payloads
remain outside verified domain coverage. The new guard does not certify all
agent execution logs or every Admin surface. Production rollout and the exact
verification evidence are tracked in the canonical permissions QA plan.

Agent request batch references are additive: when both `batch_id` and `payment_batch_id` are supplied in request or response metadata, each is checked. An expense batch reference cannot override a salary batch reference.

#### Execution-domain read checks (PR284 deployed 2026-10-12)

Agent session and saga detail/list/count readers are being guarded before
pagination by the same explicit business-domain provenance as requests.
Payroll agent families, input/output metadata, log envelopes and their data,
linked request threads, workflow actions, saga phases and checkpoint request /
close-workflow references are additive checks. Missing linked records deny
access; a permission lookup failure does not return execution payloads.
AP expense/bill access and authorized payroll access remain separate.
This does not classify arbitrary free text or unknown legacy metadata, and does
not certify every agent memory/metrics surface. Database and release evidence
must be checked in the canonical permissions QA plan before claiming rollout.

Execution read checks also include stored workflow object links: a transaction or payment-batch link adds its stored domain requirement even when the workflow payload omits the reference. These checks are additive to payload and entity checks; arbitrary free-text classification remains outside this scope. PR284 deployment was verified on all three Railway services on 2026-10-12; restricted-account synthetic bank reads and excluded-entity lists passed live smoke checks. Sensitive payroll denials are covered by isolated SQL fixtures, not live salary inspection. Production-scale query performance remains unverified.


### Workflow configuration authority (implementation pending release)

Definition payload requirements, related-entity and lane rules, submitter-review settings, step creation/editing/deletion/reordering, lane skips, entity overrides and activation changes require owner or admin membership. Organization access checks still apply; task-review and decision permissions are unchanged. Deleting a step referenced by an instance refuses rather than deleting pending tasks or history.

`get_workflow(action="get", definition_id=...)` returns the current organization's configuration and content revision under live owner/admin authority. Snapshots cover definitions, steps, conditions, overrides, automations, escalations, required fields, dimensions and notifications, including lane and velocity rules. `manage_workflow(action="update")` requires `expected_revision` from `get` and a `changes` object. It atomically replaces an active definition, returns the new definition ID/revision, and leaves existing instances linked to their original definition. Inactive or stale sources refuse. Full editor integration and validation remain under development.

The internal draft editor creates an inactive version, preserves the source and existing instance links, and writes an attributed audit record in the same transaction. An audit failure rolls back the entire draft. Omitted settings remain unchanged. A complete desired step list can reuse source steps, add/reorder steps or omit them from the new version; conditions can be replaced per step. Content revisions detect stale edits. Transaction locks serialize version allocation and prevent child edits while a draft is copied. Legacy UI editing outside the clone transaction still needs migration to versioned edits.

Direct and rule-based user targets must be active organization members. Roles must be active system/current-organization roles. Employee targets must be active in the organization and linked to an active member; supplied employee identifiers must agree. The engine accepts Admin `roleName` and legacy `role`, rejecting conflicting aliases. Dimension approvers now resolve the workflow header dimension (including a server-frozen derived header) through the entity-scoped dimension repository. The selected master value metadata must contain an integer approver_employee_id, manager_employee_id or owner_employee_id pointing to an active employee with current employment in that entity and active human organization membership. Missing, inactive or ambiguous values refuse instead of selecting a fallback admin. Full rule/runtime parity remains under review.

Supplied velocity lists persist validated defaults (`total_amount`,24 hours,red escalation), so omitted fields cannot silently fall back to a different engine amount field. Explicit null lane settings are rejected; omitted lanes stay unchanged. Atomic replacement refuses payment definitions without a usable human review step and review steps without an approver. Runtime payment safeguards still apply to actual routing. Grouped lane conditions preserve their AND semantics; existing legacy lane lists are normalized when patched. Remaining work includes embedded reference migration, broader activation/routing validation, full UI write integration and release verification. These internal capabilities do not authorize payment decisions or transmission.

Unreleased condition parity: lane text rules support contains and starts_with, and SQL equality aliases (=, <>) remain accepted. New authoring input rejects malformed membership values, nonboolean exists values, nonfinite numeric thresholds and invalid regular expressions before a version is inserted. Dimension rules are accepted in the local tool contract with dimensionTypeId and metadataField; lookup and actual task assignment are covered by isolated fixtures. Line-only dimensions require a configured, unambiguous header derivation; the resolver does not pick an arbitrary line. This remains unreleased.

Local editor integration now has a shared internal configuration endpoint and session-attributed Admin getConfiguration/reviseConfiguration procedures. The backend rechecks live admin membership and returns an explicit conflict for stale/inactive sources. Editor controls still need migration from legacy mutation procedures; the presence of this endpoint does not certify UI history preservation or production availability.

The local step editor now uses the shared revision service for add/edit/delete/reorder. It loads a fixed configuration snapshot before enabling edits, reports conflicts without retrying against a newer revision, blocks duplicate saves and opens the returned new definition. Other legacy controls still need migration. The existing escalation-role selector was not persisted by the legacy router and remains an open integration gap; full authoring is not released.

Local routing editor changes: lane rules and step-lane skips now save through the revision service. The routing overview shows saved velocity rules; admins can add/remove/edit grouping, rolling hours, amount/payee fields, threshold and escalation level. An inherited threshold is ineffective without a matching red-lane amount threshold. Existing omitted amount fields retain the engine legacy amount default when saved, while new rules explicitly use total_amount. Grouped conditions retain AND semantics within a rule and OR across rules; red is checked before yellow, with green as fallback. Other configuration controls still require parity review before release.


Unreleased payload-field editing: `changes.payload_fields` accepts required/optional lists of field specifications (field, type, description). The shared service creates a new version, preserves system-owned fields, existing extra field metadata, identifier alternatives and specialized transaction contracts. System-field edits and duplicate fields refuse. The general Admin Fields tab uses the viewed revision and reports conflicts; it does not retry against unseen configuration. The specialized transaction editor is covered by the versioned transaction-field contract below. Remaining legacy endpoints still need review, so full authoring/history parity is not yet certified.


Unreleased conditional-assignment hardening: assign_to requires exactly one positive user_id, employee_id or role, without extra keys. The shared validator checks active organization roles and active human membership; employee targets must be active and linked. It validates copied conditions as well as edited conditions. A matched but empty/ambiguous target, unavailable employee/user/role or unresolved role refuses instead of silently assigning the default approver. Tests use isolated fixtures and create no live tasks. Advanced change_lane/additional-approval actions and automatic condition decisions remain open runtime gaps, not accepted capabilities.


Unreleased automatic rejection: a matching auto_reject condition on a lane-eligible step now terminates the new workflow as rejected, records an auto_reject policy action with the matching step IDs, and skips other instantiated steps. final_decision_by is empty because no human made the decision. No approval tasks or operation executor run. The submission gateway reports workflow_rejected rather than pending approval. Rejection notifications are exercised only with mocked delivery in local tests. auto_approve, change_lane and require_additional_approval remain incomplete and must not be advertised as working.


Unreleased condition lane routing: change_lane accepts exactly a green/yellow/red target. It can raise the lane but cannot lower risk imposed by base rules, bank-detail controls or velocity rules. Lane-eligible condition steps are evaluated to a stable final lane before steps/tasks are selected; newly eligible steps can raise it again. Submission audit records the base lane, final lane and lane-condition step IDs. Payload edits and payment-line corrections use the same calculation and refuse a change to the reviewed lane. The required human payment-review check remains in place: a routing change that skips all review steps rolls back rather than executing. Automatic approval behavior remains unchanged and incomplete; additional-approval action support remains open.


Unreleased additional-review routing: require_additional_approval uses action_config.step_id for another existing approval/review/change_request step in the same definition. The target must remain in the desired version; self, foreign/missing, removed and non-human targets refuse. Version cloning remaps both copied and edited condition references to the new step IDs. New steps must first obtain a persisted ID before a later edit references them. A matching condition adds a required human review despite the target's lane/conditional skips; it never records an approval. Additive review requirements and lane escalation resolve together before task creation. Payload/line corrections that change the instantiated review set, conditional assignee or match a rejection rule refuse and require rejection/resubmission. Dynamic dimension-assignee changes still require broader parity review. Automatic-approval support remains incomplete and is not enabled by this change.


Unreleased Admin condition editor: the step dialog now displays existing conditions and supports adding/removing grouped conditions, typed values, inclusion/skipping, named role/linked-person assignment, upward risk-lane changes, another configured human review and policy rejection. Additional-review choices exclude the current/non-human steps. Saving submits the viewed revision and a validated desired condition list; conflicts are shown inside the dialog. Condition order must be unique, and rows in one group must agree on All/Any matching. Existing automatic-approval rules are labelled unsupported and cannot be added from this editor. Their runtime gap and other legacy editing surfaces remain open.

Local unreleased dimension-edit guard: workflow payload corrections and payment-line payload synchronization now resolve dimension approver dependencies against both the stored and proposed payload before saving. A changed or unresolved reviewer refuses the edit; reject and resubmit to establish a new route. Included steps use the saved approver rules; conditional assignee overrides and submitter-assigned steps take precedence. Dimension fallback dependencies are checked conservatively even when another rule may currently win. This does not reassign existing tasks or record decisions, and does not certify handling of later changes to employee/dimension master data.

Unreleased escalation authoring foundation: per-step escalations is a complete replacement list; omission preserves saved rules and [] removes them only from the new version. Each rule requires a unique positive escalation_order, positive trigger_after_hours and exactly one current-organization active role or human user target (escalate_to_role / escalate_to_user_id). include_previous_assignee defaults true, reassign_task false, increase_priority true; explicit values persist. Targets are revalidated when copying existing rules. Historic definitions and instances remain unchanged. This persistence work does not yet connect rule targets/reassignment to the reminder scanner or editor; do not claim those behaviors work until runtime acceptance is complete.

Unreleased configured escalation runtime: due rules are applied once per task in escalation order while the task, step and workflow remain pending. The task and workflow are locked in the same order as human decisions. The named role/user must currently be an active human member with access to the workflow's entity and business domain; there is no fallback to an unrelated administrator. Reassignment also requires mutation authority and refuses self-review for human review steps except explicit submitter assignment. A rule may raise priority and reassign the pending task, but does not approve, reject or execute a workflow. Original assignment time is preserved so later rule deadlines do not restart. A system escalation action records the rule and previous/target assignee; each rule is applied once. Notifications are attempted after the transaction commits. A delivery failure does not repeat reassignment; inspect notification/worker logs for recovery rather than deleting audit history. Prior assignees receive a copy only if configured and still authorized. Steps with configured rules do not also use the legacy escalation_hours reminder. Custom notification-template selection, editor integration, concurrency stress and final release review remain open.

Unreleased escalation editor: each step now exposes multiple escalation stages with a deadline, named role/person, previous-assignee notification, pending-task reassignment and priority controls. Add/remove stages through the versioned save; clearing the list removes only the new version's rules. The separate simple overdue reminder applies only when no configured escalation rules exist. Existing custom notification-template rules are displayed but remain read-only in this editor, and are preserved during unrelated step edits; custom template delivery/editing is still open. The ignored legacy escalation_role field is no longer sent.

Workflow notification configuration requires owner/admin authority. The local draft closes a legacy member-write gap; this correction is not yet deployed. Legacy notification JSON switches and actual per-event delivery settings still require migration and verification; do not claim tool/UI parity for notifications yet.

Unreleased notification event controls: workflow definitions now expose Notifications using the versioned service. manage_workflow changes.notifications accepts unique event_type/enabled patches for task_assigned, reminder, escalation, approved, rejected, submitted and comment. These update workflow_notification_settings, the table read by delivery. Omitted events and existing delivery/template metadata are preserved; missing event rows use the delivery default of enabled. Settings apply to the new definition version, leaving existing instances on their original version. Organization and recipient preferences remain additional delivery gates. The new editor removes the ineffective legacy JSON channel/CC/reply-to controls; channel and custom-template management are not newly implemented. Legacy JSON endpoint retirement and full mocked delivery/release acceptance remain open.

Unreleased notification endpoint migration: updateNotificationSettings now refuses legacy JSON writes and directs admins to reviseConfiguration with the viewed revision and notifications event patches. Non-admin and foreign-definition calls remain denied. Existing historical JSON is retained as evidence rather than rewritten. Mocked sender tests verify all seven event gates (including reminder/comment/rejected) stop email/log creation when disabled, with enabled sender controls retained. No real email was sent by these tests.

### Transaction-type field configuration authority (local, unreleased)

Editing per-transaction-type workflow header and line requirements requires owner/admin membership in the definition’s organization. Ordinary members, accountants and viewers cannot change these requirements; foreign-organization definitions are refused even for admins. The editor now uses the viewed revision to create a successor; direct updateTransactionTypeFields writes refuse. Existing workflow instances retain their definition. These changes are local and unreleased.

### Versioned activation lifecycle (local, unreleased)

`manage_workflow(action="activate" | "deactivate", definition_id=..., expected_revision=...)`
requires a fresh `get` revision, current owner/admin membership, and no `changes`
payload. The internal Admin configuration gateway uses the same service.
Deactivation locks the configuration and records an audit event; existing
instances and tasks remain unchanged. Activation creates a new active version
from the inactive source, revalidates assignment targets and required human
review, and returns its new ID/revision. A source with a successor cannot be
reactivated: read the successor instead. If another definition is already active for the same object/operation, activation
refuses with a conflict; read and revise that active definition instead. It is
never silently replaced.
Stale revisions, foreign definitions and revoked membership refuse without writes;
an audit failure rolls back the entire transition. Activation does not approve,
execute, or submit a payment. The Admin definition-page toggle uses this same contract, stays disabled until
an authorized snapshot loads, and displays conflicts without automatically
retrying with a fresh revision. Activation opens the new definition; deactivation
updates the saved snapshot. Two-connection local tests verify that competing activations, deactivations,
and revision-versus-deactivation requests serialize: one succeeds and the stale
request conflicts. Draft editing/creation remains open.

### Prepare an inactive revision (local, unreleased)

Use `manage_workflow(action="draft", definition_id=..., expected_revision=...,
changes=...)` to prepare an inactive successor from an active or inactive
configuration. `changes={}` copies the configuration unchanged. Use the returned
ID and revision for the next draft edit; a source that already has a successor
refuses instead of creating competing branches. Existing instances and the
active policy are untouched. The versioned Admin editors automatically save
inactive definitions as inactive successors; active editing retains its existing
atomic update behavior. The Admin definition page offers **Copy to draft**, which opens the returned
inactive version.

Drafts can be incomplete (for example, payment review steps can be added later).
Activation still validates mandatory human review and assignment targets. To
activate a prepared draft while another definition for that operation is active,
explicitly deactivate that active definition using its viewed revision, then
activate the finished draft. These are separate audited operations, not an atomic
policy switch; until activation succeeds, new submissions may lack an active
workflow. Existing submissions keep their original definitions. Prefer the
existing atomic `update` action for an immediate change to an active policy.
Creating a definition from scratch remains open; this draft action copies an
existing supported contract. Use publish below for atomic prepared-draft replacement.

### Publish a prepared draft (local, unreleased)

Prefer `manage_workflow(action="publish", definition_id=<draft>,
expected_revision=<viewed draft revision>, active_definition_id=<active>,
active_expected_revision=<viewed active revision>)` to replace an active policy
without the availability gap of separate deactivate/activate calls. Read both
configurations first; do not pass a changes payload or automatically retry with
unseen revisions. The service validates the draft and changes activation with
its audit receipt in one transaction. A stale revision, foreign organization,
wrong operation, revoked admin, missing payment review or audit failure leaves
the active policy unchanged. The result provides a new definition ID/revision;
existing workflow instances retain their original definitions. This publishes
configuration only and never makes a task decision.

The Admin `publishConfiguration` gateway uses the same contract and server actor.
Local two-connection tests verify that simultaneous publication, publication
versus draft editing, and competing draft saves serialize without duplicate
versions; the stale request conflicts. The Admin definition page offers **Publish draft** when a same-operation active
version is available. It displays the active name/version being replaced and
sends both viewed revisions. A conflict stays visible without an automatic retry.
Without an active version, use the activation switch. Controls require an
authorized configuration snapshot and disable while a save is pending.
Creating a workflow from scratch also remains open.

### Discard a draft (local, unreleased)

`discard` sets an open draft aside; it stays in the version history and nothing live changes.
Call `manage_workflow(action="discard", definition_id=<draft>,
expected_revision=<viewed draft revision>)` without a changes payload (the Admin
configuration gateway takes the same action through the admin-only `discardDraft`
procedure). The draft and its earlier saves are
marked discarded, not deleted, and the audit log records
`workflow_draft_discarded`. A live or earlier version refuses, a draft with a newer
save refuses (discard that save instead), and a stale revision conflicts. The result
returns `definition_id` of the version the draft was copied from, or null for a new
workflow's draft; unlike the other actions it names no new version. A discarded draft cannot be saved, published or activated; its
source can be copied to a new draft, and a new workflow's operation can be created
again.

### Retired direct step and lane writes (local, unreleased)

The legacy Admin mutations `updateLaneRules`, `createWorkflowStep`,
`updateWorkflowStep`, `deleteWorkflowStep`, `reorderWorkflowSteps`, and
`updateStepLaneSkip` now refuse direct writes after checking administrator and
organization access. Use the current versioned editors or `reviseConfiguration`
with a viewed revision (Cowork: `manage_workflow` update/draft). Step changes use
the complete desired steps list; lanes use the supported lane-rule patch.
Removing a step omits it only from the successor, preserving historical tasks.
This prevents old clients from bypassing conflict checks and history preservation.
Related-entity and transaction-type field writes now use versioned saves. Entity
override and other remaining legacy writes still need migration; do not claim
every authoring surface is versioned yet.

### Versioned related collection rules (local, unreleased)

`manage_workflow` update/draft accepts `changes.related_rules` with a `rules`
map of collection names. Each collection patch supports nonnegative integer
`min_required`, nullable `max_allowed`, typed `required_fields`, supported
primary/preferred/billing validation flags and distinct required dimension types.
Omitted collections/settings and specialized metadata are preserved; effective
minimum/maximum limits are checked after merging. `dimension_policy` cannot be a collection name; use the separate policy field
described below to edit it. Omission preserves the current policy. Transaction workflows must
supply an active registered `transaction_type_code`; a missing scope is created
in the new version, and unrelated type
scopes are retained. The standard related-entity tab uses fixed-revision collection patches and
preserves omitted metadata; switching a dimension collection to optional clears
its required dimension types. The specialized transaction/dimension-policy editor also saves through this
versioned path. The workflow settings matrix also uses viewed revisions. Transaction rows link
to their per-type editor rather than writing a global dimension requirement.
The old updateRelatedEntityRules endpoint now refuses direct writes. Runtime dimension validation and full editor parity remain to
verify before release.

### Versioned dimension policy authoring (local, unreleased)

`changes.related_rules.dimension_policy` explicitly replaces the selected
scope’s dimension policy; omit it to preserve the policy. Use `rules={}` when
changing only the policy. The format is version 1 with a dimensions array,
validated by the same `policy_from_rules` parser used at runtime. Types must
exist and be active in the current organization. Supported ordered default
sources, requirement scopes, inheritance flags, derivation strategies and
business-line roles retain runtime semantics. Unsupported versions, duplicate
sources, invalid flags and unavailable types refuse before a revision is saved.
An empty dimensions array explicitly clears policy entries. Collection rules
and other transaction scopes remain unchanged. The admin dashboard does not edit the policy (it keeps the stored one on
every save); set it through `manage_workflow` with this versioned contract, or an entity override. Interaction with
dimension-write concurrency still needs acceptance testing.

Related collection deletion is explicit: pass `remove_collections` alongside
`rules`. Omitted collections stay unchanged; removal affects only the new
version. Duplicate removal names, simultaneously patched/removed collections,
and the reserved dimension_policy name are refused. The admin dashboard does not
remove collections; compute removals from the snapshot you read with `get`. Clear policy entries using an empty
dimensions array, not by deleting the reserved collection name.

In the settings matrix, adding a required dimension also makes the related
collection required, so the displayed requirement is enforced. Removing the last
required type preserves the collection minimum; change that separately in the
related-entity editor when the collection itself should be optional. Saving
opens the new workflow version and preserves historical configurations.

### Versioned transaction field requirements (local, unreleased)

`manage_workflow` update/draft accepts `changes.transaction_fields` with an
existing configured `transaction_type_code` and `header_fields`, `line_fields`,
or both. Each supplied scope replaces its editable required/optional lists of
`{field, type, description?}` specifications. Omit the other scope to preserve it.
Use direct field names; the one exception is `custom_fields.<key>` in
`header_fields`, for a field in the organisation's register that applies to
transactions (a required one must be active and apply to that type; AR-1040).
Other dotted names, null scopes, duplicate fields and system-owned fields
are refused. Unrelated transaction types, extra metadata on retained fields,
identifier alternatives and system-owned requirements remain unchanged. Generic
requirements remain additive: a per-type optional setting cannot weaken them.

The Admin editor reads the same revision snapshot, saves only the edited scope,
shows conflicts without retrying and opens the successor. Changing transaction
type discards the unsaved field editor. Initial creation of a missing type scope
is not supported by this contract. Required-field presence is verified against
the existing runtime checker; this does not certify all importer or field-type
validation paths. No existing transaction or task is changed by a field edit.


### Entity override gap and read isolation (local review, unreleased fix)

The entity override tab stores lane, step, field, related-entity and approver
configuration, but legacy unmarked definitions do not load these records.
Do not rely on them for routing or validation. A disposable definition-selection
characterization confirms that a stored entity payload requirement is ignored;
this is evidence of a missing feature, not acceptance of the behavior.

The Admin override reader now checks access to the parent definition before
fetching override contents. Ordinary users and organization admins cannot read
another organization's overrides; existing platform-admin policy is unchanged.
Own-organization configuration read access remains available. Versioned override
authoring, entity ownership validation and runtime application are still open;
they must be implemented and tested together before claiming working parity.


Entity policy integration status (local, unreleased): a shared typed composition
module now covers all five stored categories, with organization-bound entity
loading and successor step-reference remapping. Payload requirements are
additive to definition-wide requirements. Payment approval composition refuses
policies without an assigned human review step in every lane. The helpers now support draft authoring and explicitly versioned definition
selection as described below. The publication acceptance checkpoint below supersedes
the earlier integration block. Live approver eligibility and actor entity access must still
be checked by integrated callers; helper tests alone do not establish parity.


Versioned entity override drafts (local, unreleased): `manage_workflow` draft
accepts `changes.entity_overrides`, the complete desired list of
`{legal_entity_id, override_type, override_config}` records. Omit the list to
preserve it; `[]` explicitly removes overrides from the successor only. Entity
and type pairs must be unique. Target entities must be active in the organization
and within the administrator's entity access. Explicit user/employee approvers
must be active human members with access to that entity; referenced roles and
dimension types must exist. Runtime role/dimension resolution still needs its
own live eligibility checks.

Configurations use the typed lane and payload contracts; step_skip takes
`{step_ids:[...]}`; approvers takes `{steps:[{step_id,approver_rules:[...]}]}`;
related_entity_rules takes the related collection patch contract. Step IDs must
refer to retained source steps and are remapped into the successor. Create a
new step in a draft first, then reference its returned ID in a subsequent draft.
Payment composition preserves assigned human review in every lane. Publication
and activation now revalidate each composed entity policy after cloning, including
remapped step references and live authoring checks. Saving a draft does not activate it.
The Admin override form now uses this draft contract. It reads the authorized
revision snapshot, supports adding/editing/removing a selected entity/type pair,
preserves other pairs, and opens the successor after saving. Conflicts remain
visible in the dialog with unsaved input retained; no automatic retry occurs.
Direct upsertEntityOverride/deleteEntityOverride writes now refuse after
organization and administrator checks. Read-only users can still view authorized
configuration but cannot change it. These editor changes do not enable runtime
overrides or remove the publication guard.


Versioned runtime selection checkpoint (local, unreleased): validated successor
versions with overrides receive the internal `entity_override_policy_version=1`
marker. The engine applies their entity-specific requirements, lane rules and
step/approver settings when selecting the definition, and passes composed steps
to instance-step creation. The marker is not a caller payload option. Legacy
unmarked records remain inert rather than silently changing historical policy;
unknown marker versions refuse. Versioned policies require a positive entity ID,
an active entity in the definition organization and caller entity access.

Local tests verify definition selection, required-field validation, lane
resolution, composed approvers and legacy compatibility without making workflow
decisions. Full creation/assignment acceptance, corrections, line edits, import
and guidance parity still require verification. The activation/publication guard
remains in force until those paths consistently use the same effective policy.


Entity-policy correction checkpoint (local, unreleased): payload corrections and
pending payment-line synchronization resolve the exact instance definition,
including when that definition is now inactive. Versioned workflows cannot
change legal_entity_id through a correction; reject and resubmit to establish a
new entity policy. Required fields, related/dimension settings, lane checks and
review-step checks use the composed policy. Entity requirements that fail during
batch synchronization refuse before rewriting the approval payload/hash.

Disposable tests cover both refusal without a rewrite and a valid synchronization
that leaves the batch/workflow pending with no review decision. This is not a
payment execution test. Import/schema guidance, complete creation/assignment
acceptance was extended in the publication checkpoint below; broader live checks remain open.


Submission requirements checkpoint (local, unreleased): submit now selects its
required fields through the same workflow routing and versioned entity-policy
composition used by creation, with the caller context. It no longer takes the
newest active definition regardless of matching conditions. A failed policy
lookup/composition refuses submission with error_stage=workflow_requirements;
static validation does not replace configured requirements. Retry after the
configuration or availability problem is resolved. No workflow is started by
that failed check, and internal database details are not returned to the caller.

Payload-less import requirement loaders still use their legacy selection/cache;
transaction imports and schema guidance require separate alignment. This change
does not certify those paths or lift the entity-policy publication guard.


Vendor import policy checkpoint (local, unreleased): the base required-field
checker used by VendorImporter now selects workflow requirements separately for
each record, including its entity and routing fields. It enforces header fields
and identifier alternatives; it does not reuse the first row's requirements.
Numeric text entity IDs are normalized for policy lookup in line with vendor
transformation. A missing entity on a versioned policy or an inaccessible entity
refuses the record. Failed lookup/composition returns a workflow_requirements row
error before transformation or persistence; fixing the policy allows a later
retry. There is no fallback to an unconstrained policy after a lookup failure.

This is not certification of every importer: transaction imports retain a
separate requirement/line-validation path, and other subclasses must explicitly
opt in to the base checker. Per-record lookup adds database work; import latency
has not been certified. Later transaction/assignment and publication acceptance
checkpoints supersede the earlier publication block.


Transaction import requirement checkpoint (local, unreleased): validation now
selects transaction.post for each record's routing payload and entity, with the
caller context. The cached first definition no longer determines required fields
or the type enum. Generic and per-type header/line requirements are combined;
missing line fields include their line index in the row error. Numeric zero is a
present value in structured lines. Identifier aliases and cached account/item/tax
resolution remain available without creating parties during this policy check.
Fiscal period remains executor-resolved; configured metadata is no longer
silently exempted. A failed policy check or no matching definition refuses the
record instead of validating it as unconstrained.

The initial workflow cache remains for compatibility with reference loading,
but it does not authorize the record. Remaining acceptance includes full
normalization/executor parity (defaults, dynamically resolved identifiers and
custom fields), mixed-entity reference caches, schema guidance and performance.
These local tests do not establish full import/approval certification or permit
publication of entity overrides yet.


Transaction normalization checkpoint (local, unreleased): required-field checks
now preview the same transformation used by posting, with party creation
explicitly disabled. This includes currency/date defaults, resolved existing
identifiers, flat/structured lines and dimensions. The preview copies the source
record, so validation does not mutate its dimensions or other fields. A required
custom field that transformation drops now refuses before any auto-created party
or transaction. Defaults that satisfy requirements are accepted consistently.

This does not certify new-party routing: the existing vendor/customer creation
helpers use a separate committed connection. New IDs may affect conditions after
the preview, and those side effects need explicit atomicity/routing acceptance.
This remains open together with mixed-entity reference caches and schema guidance;
the later atomic import and publication checkpoints supersede this earlier block.


Import party atomicity checkpoint (local, unreleased): missing vendors/customers
are now created using the import record's connection, which is also passed to
the transaction executor. Party creation and entity linkage roll back with a
failed record or group. Creation validates active organization/entity ownership
and caller entity scope, serializes same-name creation within that scope, and
refuses ambiguous names. Newly inserted IDs are not put in long-lived importer
caches; later records re-query, avoiding references to rolled-back IDs.

After transformation, transaction imports reselect workflow requirements using
actual resolved IDs before duplicate lookup, GL backfill or posting. A new ID
that changes routing must satisfy the newly selected requirements and type enum,
or the record rolls back. Tests cover refusal, rollback and retry without posting
financial transactions. This supersedes the separate-connection finding above;
full posting/concurrency acceptance, mixed-entity reference-cache isolation,
schema guidance and publication gates remain open.


Mixed-entity import checkpoint (local, unreleased): transaction import validates
an active in-organization entity and caller scope before loading reference data.
Each entity has a separate importer cache for parties, transaction settings,
dimensions and reusable executors. Alternating records cannot reuse the first
entity's settings or identifiers. Connector hooks and the record connection are
preserved across these entity-specific importers. Invalid IDs (including boolean
IDs), excluded entities and unavailable entities refuse; numeric text IDs are
normalized. Omitted row entity uses the configured import entity.

Synthetic tests verify alternating-entity resolution and denial before loading;
existing disposable rollback/requirement tests continue to pass. Broader live
isolation, full posting and performance remain to be accepted before release.


Workflow schema context (local, unreleased): call
`get_submissions(action="schema", object_type="transaction", operation="post", payload='{"legal_entity_id":12,"transaction_type_code":"AP_INVOICE"}')`
with the intended entity, transaction type and other routing fields. The schema
uses engine selection and the caller's entity scope, then combines the validator
contract with effective workflow requirements. `workflow_requirements` retains
line and conditional configuration; the validator path also exposes
`resolved_line_required_fields`. `selection_resolved=true` means selection used
the supplied payload, not that submission or approval has occurred.

Without payload, the response is generic guidance marked
`selection_resolved=false`. Explicitly versioned entity policies require payload
context instead of returning misleading base-only requirements. An excluded
entity refuses. Validator-only fallback remains discoverable and explicitly says
no matching workflow was resolved. Recheck with complete payload before submit;
this guidance does not approve, execute or bypass publication restrictions.


Pending-task assignment checkpoint (local, unreleased): task creation now
resolves approver rules from the instance's saved effective entity policy, rather
than re-reading only the base step's approver columns. Conditional explicit
targets keep their existing precedence. The same resolution is used when the
engine assigns later pending steps. Definition/entity ownership remains scoped
to the workflow organization.

Every selected task assignee is rechecked as a current active human member,
with live workflow read access for the entity/domain. Review/approval/edit-review
steps additionally require mutation authority. Missing access refuses task
creation and rolls back workflow creation; it does not silently pick another
user. Existing owner/admin selection and explicit submitter rules remain subject
to these checks. Disposable end-to-end tests create a pending review only, with
email and completion calls prevented. Later pending-step tests verify saved
policy and access revoked before assignment. Assignment-time access locking is
covered below. No approval or execution is implied.


Saved-step ownership safeguard (local, unreleased): assignment refuses a pending
step linked to any definition other than the instance’s saved definition, even
within the same organization. It does not substitute the foreign approver, skip
the malformed step or complete the workflow. Investigate and repair the stored
link through an authorized recovery process; retrying cannot repair it.


Assignment authority locking (local, unreleased): task creation holds the current
user, membership, role grants, role definitions and permission rows stable until
its transaction ends. A competing restriction or revocation waits; a committed
revocation is seen by the next check. This does not grant continuing access after
commit or replace the access checks when a task is read or decided. No task is
approved by assignment. Deferred notification access and all other authorization
writers still need separate review; this is not full concurrency certification.


Deferred task-recipient checks (local, unreleased): before sending an assignment
email, delivery rechecks that the task and workflow are pending, the saved step
belongs to the definition, and the named assignee is still assigned. Recipients
must be active human members with current entity/domain read access and mutation
authority for review steps. Role copies use the current stored task role, active
unexpired grants in the same organization, and a separate access check for every
recipient. Revoked or excluded recipients are skipped. Checks precede delivery;
they cannot retract email already accepted by the provider. Other notification
types and provider-side access checks remain separate review work.


PR289 missing transaction sections (unreleased): transaction_fields and
transaction-scoped related_rules can create a missing section for an active
registered system transaction type. The type is checked under a shared lock.
Unknown/inactive types refuse before a successor is created. Generic requirements,
unselected sections and existing workflow instances retain their previous values.
Creating a section neither enables transaction posting nor expands the workflow's
accepted transaction-type enum. Draft/publication and reviewer safeguards still apply.


New-definition service checkpoint (local, unreleased): an internal creation
service can build an inactive root workflow for a supported executor operation,
using the unique active system-template operation contract for permission and
required-field metadata. Administrators provide review configuration; they cannot
provide authority fields. Existing tenant operations return a conflict directing
the editor to the draft lifecycle. Creation is audited and rolls back on invalid
configuration. The `manage_workflow(action="create", creation=...)` tool action
and Admin `createConfiguration` gateway now expose this service. Supply name,
object_type, operation and configuration (including assigned human-review steps),
without definition IDs, revisions or changes. The returned ID/revision identifies
an inactive draft; creation never activates or executes it. The Admin workflow list now includes New workflow for administrators. Choose an
available action and name; the form creates an inactive draft with an administrator
approval step. Existing operation families must use Copy to draft. Review the
returned draft before activating it. Isolated creation/isolation/concurrency tests pass; this feature remains unreleased
until the final PR checks, review and deployment are complete.


PR289 settings migration (unreleased): notification matrix toggles now save an
event patch against the displayed revision and open the returned workflow version.
Conflicts remain visible without optimistic success or automatic retry. Legacy
updateNotificationGate, updatePayloadFields and updateRequiredDimensions refuse
direct changes; use reviseConfiguration with notifications, payload_fields or
related_rules dimension policies. Existing versioned field/dimension editors remain
the supported UI. Single submitter-review settings now use versioned edits; bulk settings now use the atomic displayed-revision contract described below.


PR289 submitter review (unreleased): reviseConfiguration/manage_workflow changes
accept submitter_review as a boolean. It adds a submitter change-request step if
absent, or removes existing submitter change-request steps, in a successor version.
Other steps and children remain intact; references to removed steps refuse. Do not
combine this convenience field with steps. The single workflow settings checkbox
uses its displayed revision; conflicts remain visible. Legacy toggleSubmitterReview
refuses direct writes. Bulk settings use the atomic displayed-revision contract described below.


Bulk submitter-review service (unreleased): the shared
service accepts 1–100 unique definition IDs with their displayed revisions and a
boolean. Only one version per operation family is allowed. It takes family locks
in canonical order and validates all snapshots before making successor versions.
A stale selection or later validation failure rolls back all versions and audits.
The unreleased manage_workflow action bulk_submitter_review and Admin
reviseSubmitterReviewBatch now expose this contract. Supply changes containing
revisions (definition_id and expected_revision pairs) and enabled; do not supply
singular definition/revision or creation arguments. The settings bulk controls load and display fixed snapshots before saving, as
described below.


PR289 bulk settings UI (unreleased): Bulk submitter review lets an administrator
select up to 100 active workflows, inspect loaded version/review state and enable
or disable submitter review in one atomic save. Each displayed revision is fixed
while editing; conflicts stay visible without retry. Successful saves link to the
new versions and disable duplicate submission. Historical/inactive versions are
edited individually, not included in bulk changes. The legacy
bulkUpdateSubmitterReview route now refuses direct writes. This supersedes earlier
bulk-UI-pending checkpoints; final release acceptance remains open.


Entity publication acceptance (unreleased PR289): 256 combined isolated tests pass
for configuration, all five entity policy categories, actual policy selection,
saved-definition edits, imports, task assignment/revocation, notification recipients
and escalation. Publication now clones/revalidates overrides and checks every
composed entity policy, including payment human review per lane. An integration
test publishes and resolves the resulting policy while existing instances retain
their original definition. Unsupported policy versions refuse. This is not
production or performance certification; final review/CI/deployment remains open.

PR289 draft navigation (unreleased): after copying or publishing, the returned
workflow version can be edited without reloading the page. The duplicate-save
guard applies to the submitted version and resets on navigation to a different
definition; stale-version conflicts still require explicit review, not automatic retry.


### Unreleased QA clarification: team membership and login history

The team table labels organization access as **Membership** to distinguish it
from assigned accounting permission roles. An accounting Administrator role alone
does not grant organization team-management authority. A null last-login timestamp
is shown as **Not recorded**, not **Never**; it is not proof that the user has never
signed in. This is a display correction, not new login telemetry or an access change.


### Admin invalid-session recovery (QA branch; deployment unverified)

The Admin middleware's existing JWE-error recovery now expires both current
`__session` and legacy `appSession` cookies, including numeric chunks, at the
configured cookie path/domain before redirecting to login. It leaves unrelated
cookies alone and logs no SDK error text or cookie values. This does not change
MCP authentication, grants or identity-provider logout. The historical hosted
logout failure remains open; do not claim it resolved from isolated tests.


### Single-notification read scope (QA branch; deployment unverified)

Marking a notification read checks both its recipient and the currently selected
company, matching the feed and mark-all-read scope. A row for another company or
recipient is left unchanged; company-neutral legacy rows remain eligible for
their own recipient. Already-read timestamps are preserved. The response remains
idempotent and does not disclose whether an excluded row exists. This changes
only the personal in-app read marker, not email delivery, workflow decisions,
grants or notification payload visibility within a company.


### Onboarding connection indicator

The connector step polls every five seconds while visible and waiting, pauses in
a hidden tab, and stops after a valid first-connection timestamp. Malformed or
noncanonical timestamps do not mark the company connected; the next scheduled
poll can recover. Summary steps read once without polling. The timestamp is a
company-level first human MCP connection signal, not proof that the current
browser user has connected or that a particular connector is working now.

### Onboarding country skill guidance

The onboarding skill picker currently offers country variants for Estonia and the
United Kingdom. For other selected entity countries, including the US, both the
Claude and IDE paths explain that no dedicated variant is offered in this wizard
and direct the user to General. This changes only skill guidance: the entity's
country and accounting setup stay unchanged. It does not claim US-specific tax
or compliance coverage; country setup and skill availability are separate.

### Empty entity list navigation

Configuration → Entities offers **Open entity setup guide** when the list is empty. This opens `/entities/create`, which describes assistant-led first-entity onboarding and additional-entity setup. It is guidance only and does not grant onboarding authority or create records.


### Workflow AP/AR read parity (QA branch; deployment unverified)

Workflow details and collections using the shared payload-read policy now require
`ap:read` for bill, expense_report, card_transaction and purchase_order, and
`ar:read` for customer_invoice and sales_order. The mapping is shared with agent
request readers. A payroll read grant does not bypass AP/AR checks; domain
wildcards and administrative wildcards retain their existing semantics. Existing
payroll-payload and entity checks remain additional requirements.

This applies to shared-policy workflow detail reads, activity/run collections and
linked notifications. Filtered runs are reported as hidden; the explanation refers to current domain or entity permissions because either can restrict a row. Configurable workflow
write/approval grants do not substitute for these read grants. Other object families,
unknown provenance and hosted acceptance remain open; no new read policy is inferred
from arbitrary free text or custom workflow write permissions.


For linked workflow notifications, a restricted caller needs a matching entity in
the workflow payload or its stored payment batch. Missing/malformed entity values
are not evidence of organization-wide scope. A stored batch with a contradictory
payload entity hint is withheld for restricted readers. Agent-request null-entity
semantics remain separate. This is read authorization, not a repair of old payloads.


### Workflow entity ceilings (QA branch; deployment unverified)

Shared workflow payload/detail and collection readers now enforce the current
membership/role entity ceiling independently of domain grants, including wildcard
grants. Restricted readers need a valid matching payload entity or a stored payment
batch whose entity is allowed and does not contradict a supplied hint. Missing,
malformed or foreign entity values are denied for restricted readers; no numeric
cast of arbitrary payload text is used in collection SQL. A newly restricted scope
is re-read on the next call in the same session.

Unrestricted membership is determined by `hasOrganizationEntityAccess`, not by
whether `getUserEntityIds` returns a list (it enumerates current entities for
unrestricted members too). Unrestricted access retains the existing organization
rules. A restricted caller's cross-company payload read is denied rather than
reusing entity IDs across tenants. Domain and payroll checks still apply separately.

Family activity/run summaries now check for hidden rows in any object family;
entity restrictions can hide master-data workflows too. The explanation says
**Some runs are hidden by your current domain or entity permissions**, avoiding
an incorrect claim about which grant is missing. No role assignments, workflow
approvals, old payloads or accounting data are changed.


### Definition summary visibility (QA branch; deployment unverified)

Definition lists, definition details and family lists calculate run counts and the
latest submission from runs the caller may read. Domain and entity filters apply
before aggregation, with each run pinned to its definition's organization. Family
counts include readable runs across earlier versions. Definition metadata and step
counts remain visible under their existing access rules, even when no runs are
readable; zero run counts describe the caller's visible subset, not the absence of
all runs. Authorized cross-organization reads use the target tenant for stored
payroll provenance; a restricted caller's entity IDs are never reused in another
tenant. These are read-only changes; approvals and accounting records are unchanged.


### Analytics run visibility (QA branch; deployment unverified)

Workflow dashboard metrics, analytics summaries, leaderboards and bottleneck
statistics use the same run-read restrictions as workflow details. The filters
apply before aggregation, including previous-period comparisons, nested escalation
counts, top-definition selection, heatmaps, sparklines and approver statistics.
Only runs belonging to the selected definition's organization are included.
Definition configuration totals retain their existing metadata access rules.

Selecting an entity or lane narrows the readable set; it never expands the user's
membership scope. Entity filters compare canonical entity text instead of casting
stored payload text to an integer, so malformed legacy values are excluded rather
than crashing the entire report. Analytics describe visible runs, not necessarily
all company activity. These changes do not edit old payloads or approval records.


### Run lists, activity and audit export (QA branch; deployment unverified)

Workflow instance rows, their total count and recent activity require the run and
its definition to belong to the same organization. The shared domain/entity policy
uses the authorized target tenant for stored payroll provenance; entity-restricted
callers cannot reuse their own entity IDs in another tenant. These checks apply
before pagination or activity limits, so excluded rows do not consume page slots.

The analytics audit CSV exports only the current returned page and its selected
summary fields, not all rows indicated by the total and not raw workflow payloads.
An empty returned page produces no download. Other workflow CSVs use their existing
returned summary/list data; this observation does not certify hosted revocation,
browser caching or all export surfaces. No approval or data-repair writes occur.


### Stored transaction workflow reads (QA branch; deployment unverified)

Admin workflow readers resolve an existing transaction by its stored ID **and**
entity. A payload's transaction-type hint cannot replace the stored authority.
Reversals use the existing ledger source-chain policy, including cycle/depth bounds;
restricted readers need the source transaction's domain. Proposed transactions
without a stored ID use the existing transaction-type permission registry. Payroll
read alone does not grant AP, AR or general-ledger transaction access.

The same policy filters workflow lists, counts, analytics and linked notifications
before pagination/aggregation. Missing stored references fail closed even for
unrestricted owners; wildcard owners retain domain access to existing records.
No transaction types, grants, payroll data or accounting records are changed.
This bounded transaction-source contract also applies to MCP workflow detail
and collection reads: stored types use the same registry and bounded reversal
source chain. Other business-object families, malformed/legacy provenance and
hosted identity acceptance remain open; this is not blanket workflow parity.

For MCP readers restricted by membership or a host task entity, stored payment-batch
references may omit the entity hint, but a supplied hint must match the stored
batch entity before list/count visibility. Conflicting hints are rejected, matching
the existing direct-read check. Unrestricted and malformed legacy-shape acceptance
remains separate; this check does not certify those cases.

Admin and MCP workflow collection reads require an object-shaped payload and a nonempty
object type before counting or pagination, including for wildcard owners. This
matches direct-read validation. Payment batches with non-null, non-array `lines`
require payroll-read authority because their content cannot be classified safely;
false, zero and empty-string containers are not treated as absent. Missing/null
lines and arrays retain existing provenance checks. No stored payload is repaired
or deleted. Other malformed references and wider object-domain parity remain open.

Admin and MCP workflow readers validate supplied payment-batch and payroll-run
references before applying broad permission grants. A batch must exist in the
authorized tenant, and a supplied entity hint must match it. An existing payroll
run requires both its ID and matching entity. Missing/conflicting references are
withheld even for wildcard owners, including lists, counts and linked Admin
notifications. Proposed workflows without stored references retain their existing
domain/entity checks. MCP batch-domain requirements remain unchanged; payroll
read alone is not a substitute for them. No history or accounting data is repaired.

Assignment and configured escalation eligibility now check the specific workflow
through the shared detail-read policy. They first require matching instance and
definition organizations, then enforce current domain, membership-entity and host
task scope. Only that object’s stored references are resolved; organization-level
invitations do not depend on unrelated accounting tables. Existing mutation and
self-review checks remain in place. Collection reads still filter in SQL before
pagination/counting; this change does not bypass their policy.

On the QA branch, payment-batch workflow/request reads require at least one of
`payments:read`, `ap:read`, or `accounting:read` (or matching broad authority).
Salary batches additionally require `payroll:read`; payroll, AR, audit or ordinary
master-data read alone does not grant batch access. Request source tables,
request/response object types and explicit batch-ID metadata all retain this
requirement, including thread summaries and linked notifications. Entity limits
remain independent. This matches the existing MCP batch registry and Admin
attachment policy; it does not add grants or authorize a payment. Direct Admin
payment-screen reads and broader legacy/provenance acceptance remain under audit.


On the QA branch, notification links to `/agents/sessions/<uuid>` must resolve
to a readable agent instance in the notification organization. The feed and
both unread counts apply the existing execution domain/provenance policy and
the caller's entity scope before pagination or counting. Missing, malformed,
foreign-organization and excluded-entity session references are withheld; a
readable session link cannot override a forbidden task/instance reference on
the same notification. Existing recipient and admin-alert gates remain in place.
Unlinked alerts, unknown routes and free-text provenance are not newly certified;
this change does not retract previously delivered email.


QA branch execution-read hardening: an agent's linked workflow definition must
belong to the same organization as its workflow instance. A missing or mismatched
definition makes the execution unreadable in both Admin and MCP; saga phases and
linked session notifications inherit that check. Existing domain, entity and
workflow payload checks still apply. This is verified with synthetic SQL parity
for lists, counts and pages, not hosted-session acceptance.


### Pinned OAuth organization refusal

An OAuth connection with an explicit organization selection must resolve current
membership in that organization. Missing membership returns HTTP 403 with
`organization_access_denied` before employee linkage, rate-limit accounting or
new-user provisioning. Access to a different organization does not change the
selected company. Check the connected account or ask an administrator to restore
access; do not remove the organization selection merely to retry a company task.
Unpinned first-login provisioning remains available. This local signed-token
regression does not certify hosted OAuth reconnect or provider revocation.


### MCP company creation and initial credentials

The current manage_organization(action="create") confirmation preview discloses
that confirmed creation always issues an initial API key, including when the
caller signs in with OAuth. It expires after 365 days and carries read, write
and delete without a narrower key entity filter. Effective access remains bounded
by the creator's current membership, roles and entity access. The unconfirmed
preview generates no key and provisions no company. The confirmed response shows
the plaintext key once; handle it as a credential.

There is currently no key-free option on this action. Whether key issuance should
become optional or separate remains an owner decision (ONB-023); this disclosure
does not change key lifetime, scope or issuance policy. Admin onboarding/signup
uses separate routes and is not described by this MCP creation contract.


Dashboard workflow CSVs use the currently returned summary/list data; they are
not a grant to retrieve hidden rows. Analytics exports object-type aggregates
and the current top-eight workflow summaries, while the audit CSV exports the
returned page. Generic CSV text is guarded against spreadsheet formulas and
quoted for embedded line breaks. MCP read/write contracts are unchanged.


### Agent visibility replacement — implementation in progress

The approved replacement separates agent-output visibility from business-action
permissions. Role and direct-user grants are additive; owners/admins retain
organization/entity-scoped defaults. Non-admin users start with no grants.
Access includes historical and future outputs, including sensitive payroll data,
but does not authorize payroll records or business actions.

The implementation branch adds Roles → Agent access and Agent → Access over one
grant store with audited changes. It is not yet released or fully integrated with
readers. Continue to follow the deployed access policy until rollout is verified;
do not promise access based solely on the new controls. The canonical workflow
and permissions plan tracks producer scope, reader parity, tests and rollout.


### Assignment and auxiliary readers — unmerged implementation, 2026-10-20

The implementation branch now applies the shared grant/scope check to saga pages,
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

These changes are local and unreleased. Classification repair/backfill, deployment,
production-capacity acceptance and live authenticated browser verification have not
been performed. See the canonical workflow/permissions plan for measured evidence
and outstanding acceptance; do not treat this section as rollout confirmation.
