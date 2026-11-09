# Permission model

**Status:** Implemented; reflects the current application authorization model.  
**Last reviewed:** 9 Nov 2026.

## Roles (system-wide)

| Role | Can do |
|---|---|
| user | Upload files, manage their own files, access documents shared with them, and view their own activity history |
| admin | Manage users and roles, view system-wide activity and audit records, and view document metadata |
| auditor | View system-wide activity and audit records; cannot manage users or documents |

## Per-document access

| Who | Read | Edit | Share/revoke | Delete |
|---|---|---|---|---|
| Owner | Yes | Yes | Yes | Yes |
| Edit grant | Yes | Yes | No | No |
| Read grant | Yes | No | No | No |
| Everyone else | No | No | No | No |

## Rules

1. **Deny by default:** no valid grant means no document access.
2. Document permissions are checked through the centralized authorization logic used by document routes.
3. Permission checks happen on the server; frontend visibility is not an authorization mechanism.
4. Revoking a grant takes effect on the next request.
5. Inaccessible documents are handled without revealing whether the document exists.
6. Security-relevant operations are recorded in the audit log. Successful document mutations such as delete, share and revoke are recorded with operation-specific events. Denied authorization attempts are also audited.
7. Document search must not expose documents that the requesting user is not authorized to read.
8. The user's role is read from the database during request authorization rather than trusted from a role claim in the JWT.

## Decisions

- Admins can view document metadata but cannot read document contents unless the owner grants them access.
- Only the document owner can share or revoke access. Editors cannot.
- When a document is deleted, its permission grants are deleted as part of the database operation.
- Document mutation audit events are committed in the same database transaction as the corresponding mutation.
- Local file deletion is best-effort after the database deletion; database-stored file content is retained as the recovery source while the document record exists.