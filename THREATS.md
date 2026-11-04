# Threat notes

Status: not started. I will fill this in on Day 5 after attacking my own system.

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
3. A grant row with an invalid level could give access (found in a Codex review). Fixed: only "read" and "edit" count. Test added. Commit: [your commit message].
4. Document routes are not built yet, so enforcement is not proven. To do: every document route must call can(), with tests for each role.
5. No login rate limiting. Known weakness, not fixed.
6. Magic-byte checks only verify file headers (found in Codex review). A file can start with a valid header (like `%PDF-`) and still hold arbitrary payloads afterward. Mitigated: Uploaded files are renamed to random `.bin` files, stored outside static web roots, and must always be served as downloads with safe content types rather than executed or rendered inline.
7. No storage quota or retention/cleanup policy (found in Codex review). Repeated valid uploads will persistently consume disk space. Known limitation for Render's free tier.
8. Orphaned files on database commit failure (found in Codex review). If writing to disk succeeds but `db.commit()` fails, the `.bin` file remains on disk without a corresponding database row. Recorded as an operational limitation.
9. Potential path disclosure in server errors (found in Codex review). Mitigated: Keep FastAPI/Uvicorn debug mode disabled in production environments so unhandled exceptions return generic responses.