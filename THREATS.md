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