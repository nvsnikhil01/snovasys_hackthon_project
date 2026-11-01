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
(none yet)