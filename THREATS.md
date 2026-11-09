# Threat notes

Status: in progress. Verified attacks and security reviews logged from Day 3 to Day 5.

## Format for each entry
- Attack: what I tried
- Result: what happened
- Fix: what I changed, and the commit that did it

## Things I plan to test
- Opening another user's document by changing the ID in the URL
- Calling an endpoint without a token, and with an expired or edited token
- A normal user calling admin endpoints
- Uploading a file with a wrong type, an oversized file, or a dangerous filename
- Access after a permission is revoked
- Search results leaking documents I shouldn't see
- Editing or deleting audit log entries

## Findings
1. JWT secret changed on every restart (found in a Codex review). Fixed: production now needs a fixed SECRET_KEY and refuses to start without it. Commit: Require SECRET_KEY in production.
2. Registration reveals whether an email exists (found in a Codex review). Accepted: the clear message is friendlier, and hiding it properly needs email verification, which is out of scope. Login itself uses one generic error.
3. A grant row with an invalid level could give access (found in a Codex review). Fixed: only "read" and "edit" count. Test added. Commit: Add permission validation tests.
4. Document route permission bypass (found in a Codex review). Mitigated: every document route (list, get, download, delete, share, revoke) delegates authorization directly to `can()`. Verified via automated tests in `test_sharing.py`.
5. No login rate limiting. Known weakness, not fixed.
6. Magic-byte checks only verify file headers (found in Codex review). A file can start with a valid header (like `%PDF-`) and still hold arbitrary payloads afterward. Mitigated: Uploaded files are renamed to random `.bin` files, stored outside static web roots, and must always be served as downloads with safe content types rather than executed or rendered inline.
7. No storage quota or retention/cleanup policy (found in Codex review). Repeated valid uploads will persistently consume disk space. Known limitation for Render's free tier.
8. Orphaned files on database commit failure (found in Codex review). If writing to disk succeeds but `db.commit()` fails, the `.bin` file remains on disk without a corresponding database row. Recorded as an operational limitation.
9. Potential path disclosure in server errors (found in Codex review). Mitigated: Keep FastAPI/Uvicorn debug mode disabled in production environments so unhandled exceptions return generic responses.
10. Unlink failure during deletion can orphan storage files (found in Codex review). If `file_path.unlink()` fails after `db.commit()`, the database record is removed while the physical `.bin` file persists. Operational limitation recorded for future garbage collection/retention jobs.
11. Path traversal defense in depth on downloads/deletes (found in Codex review). Mitigated: Resolved filesystem paths are explicitly validated to ensure they remain inside `UPLOAD_DIR.resolve()` before reading or deleting.
12. Resource existence disclosure via 403 vs 404 (found in Codex review). Requesting an existing document without access yields 403, whereas a missing document yields 404, allowing an attacker to enumerate valid document IDs. Accepted for hackathon UX clarity; returning uniform 404s can be enabled if ID enumeration becomes a priority concern.
13. Process-local audit-write lock (identified during deployment review). The existing threading lock coordinates audit writes only within one Python process. It does not coordinate multiple workers or service instances. Known limitation: database-level coordination is required before scaling to multiple workers or instances.

14. Audit-chain tail deletion (identified during security review). The hash chain can detect modifications to retained records, but deletion of the latest records or the entire chain may not be independently detectable. Known limitation: an independent, protected checkpoint mechanism has not yet been implemented.

15. File persistence and recovery (hardened). Document bytes are stored in the database alongside local file storage. If the local file is missing, the download path can restore it from database-stored content. Recovery behavior has been tested, but this does not protect against loss or compromise of the database itself.

16. Document mutation and audit transaction consistency (hardened). Successful delete, share and revoke operations now record their operation-specific audit events in the same database transaction as the corresponding database mutation. Tests cover successful operations and transaction failures. Physical file cleanup after a database deletion remains a separate filesystem operation.