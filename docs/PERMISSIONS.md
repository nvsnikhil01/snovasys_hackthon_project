# Permission model

Status: draft, 1 Nov 2026. I will update it as the code is written.

## Roles (system-wide)
| Role | Can do |
|---|---|
| user | Upload files, manage their own files, open files shared with them |
| admin | Manage users and roles, see the audit log |
| auditor | Read the audit log only |

## Per-document access
| Who | Read | Edit | Share/revoke | Delete |
|---|---|---|---|---|
| Owner | Yes | Yes | Yes | Yes |
| Edit grant | Yes | Yes | No | No |
| Read grant | Yes | No | No | No |
| Everyone else | No | No | No | No |

## Rules
1. Deny by default: no grant means no access.
2. One permission function decides everything, and every route calls it.
3. Checks happen on the server, not in the browser.
4. Revoking access takes effect on the next request.
5. A denied request looks the same as "not found", so outsiders can't tell whether a file exists.
6. Every attempt, allowed or denied, is written to the audit log.
7. Search only returns documents the user may read.
8. The user's role is read from the database on each request, not trusted from the token.

## Decisions
- Admins can see document metadata but not file contents, unless the owner grants them access.
- Only the owner can share a document. Editors cannot.
- When a document is deleted, its grants are deleted too.