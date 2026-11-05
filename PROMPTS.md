# AI usage log

I use AI tools and record every use here, including where they were wrong.

## 1 Nov 2026
- Tool: Claude (chat)
- Used it for: planning the 7-day timeline, choosing the stack, the folder structure, and the laptop setup checks.
- What I did myself: created the private repo, installed Node, tested that Python and the libraries install.
- Note: Node was installed but missing from PATH, so I added it manually.

## 1 Nov 2026 (second entry)
- Tool: Antigravity
- Used it for: reading the assessment brief and generating an early prototype in a separate folder (`sample_V1`) to see how the requirements fit together.
- What it suggested: a full document-sharing prototype with login, roles, and an audit log.
- What I kept: nothing from the generated code (`sample_V1` was never added to my Git repo). I only used it to understand the brief.
- What I changed or rejected: rejected the generated prototype because I needed to write and understand every line myself for the live interview. I started fresh in a clean repo with FastAPI + React.
- What I understood from it: the project needs per-document permissions checked on the server, and an audit log that records denied attempts too.

## 2 Nov 2026
- Tool: Claude (chat)
- Used it for: step-by-step setup of the FastAPI backend with a /health route, the React (Vite) scaffold, and the Render deployment settings (build command, start command, Python version, free plan)
- What I did myself: ran every command, created and saved the files, read the error messages, and made each commit
- What I kept: all the commands and the 6-line /health route; I can explain what each line does
- What I changed or rejected: I did not use the paid Claude Code extension.

## 3 Nov 2026
- Tool: Claude (chat)
- Used it for: code and explanations for the database models, bcrypt password hashing, register, login with JWT, /auth/me, roles, the seed script and permissions.py with tests
- What I did myself: typed or pasted each piece, ran it, tested it in /docs and with pytest, and fixed my own mistakes (a misnamed file, wrong folder, a stale server)
- What I kept: all of it, and I can explain what each part does
- What I changed or rejected: kept SQLite for local dev and tests before setting up production env variables on Render.

## 3 Nov 2026 (review)
- Tool: Codex (ChatGPT) in VS Code, used as a read-only reviewer
- Asked it to: review my auth code (round 1) and my permission code (round 2)
- What it found: (1) the JWT secret changed on every restart, (2) registration reveals whether an email exists, (3) an invalid grant level in the database could give access, (4) no document routes yet to check, plus missing tests
- What I tested: reproduced the missing SECRET_KEY startup crash in production mode, verified duplicate email registration returns 409[cite: 1, 2], and ran pytest (9 passed) for invalid grant levels.
- What I changed: production now refuses to start without SECRET_KEY, only "read" and "edit" count as grants, and I added three tests
- What I rejected and why: the email-exists message stays, because hiding it needs email verification, which is out of scope. It is recorded in THREATS.md.

## 4 Nov 2026
- Tool: Claude (chat) & Gemini (used when Claude hit the free message limit)
- Used it for: setting SECRET_KEY and APP_ENV on Render, verifying live /auth endpoints, and building Piece 7 (`POST /documents` file upload with extension whitelist, 5 MB limit, magic-byte checks, and random UUID `.bin` storage).
- What I did myself: configured Render environment variables, tested register/login/me on the live Render URL[cite: 1, 2, 3, 4], created the 4 test files (`ok.txt`, `fake.pdf`, `virus.exe`, `big.txt`), and tested all 5 upload scenarios in `/docs`.
- What I kept: the upload validation logic in `routes/documents.py` and `DocumentOut` schema in `schemas.py` (which omits `stored_path`).
- What I changed or rejected: postponed attaching Render PostgreSQL until the core document routes are complete.

## 4 Nov 2026 (Codex Review - Round 3)
- Tool: Codex (ChatGPT) in VS Code, used as a read-only reviewer
- Asked it to: review `backend/app/routes/documents.py` and `DocumentOut` in `schemas.py` for dangerous uploads, path traversal, memory/disk exhaustion, and path leakage.
- What it found: 
  1. Signature/magic-byte checks only verify file headers, so files can contain misleading payloads after a valid header (Medium).
  2. No global multipart request body size limit or storage quota/retention cleanup policy for accepted uploads (Medium).
  3. Orphaned files remain on disk if a database commit fails after writing the file (Low).
  4. Diagnostic exceptions could leak server paths if debug mode is enabled (Low).
  (Positive note: No path traversal risk because filenames use random UUIDs, and `DocumentOut` hides internal storage paths).
- What I tested: Verified header-matching uploads and checked disk behavior.
- What I changed / Recorded: Kept the endpoint logic intact for the hackathon prototype, but recorded all findings as known operational limitations and threats in `THREATS.md`.

## 5 Nov 2026
- Tool: Gemini
- Used it for: implementing document routes (`GET /documents`, `GET /documents/{doc_id}`, `GET /documents/{doc_id}/download`, `DELETE /documents/{doc_id}`), sharing routes (`POST /documents/{id}/share`, `GET /documents/{id}/shares`, `DELETE /documents/{id}/share/{user_id}`), and writing automated pytest tests (`tests/test_sharing.py`).
- What I did myself: typed and tested the routes, unblocked PowerShell script execution, installed `httpx`, and verified all 10 unit and integration tests passed in pytest.
- What I kept: the central `can()` permission check on every route, path validation against directory traversal, and automated terminal tests instead of manual browser clicks.
- What I changed or rejected: rejected manual Swagger testing once automated tests were written.

## 5 Nov 2026 (review)
- Tool: Codex (ChatGPT) in VS Code, used as a read-only reviewer
- Asked it to: review the document and sharing routes for permission bypasses, IDOR, path traversal, and edge cases.
- What it found:
  1. Upload and delete can leave orphaned files if database commits or file unlinks fail (recorded in THREATS.md).
  2. The download and delete routes trusted the database's `stored_path` without checking if it stayed inside the upload directory.
  3. Inaccessible IDs return 403 while nonexistent IDs return 404, revealing that an ID exists (recorded in THREATS.md).
- What I tested: tested download with path checks, tried accessing missing vs unauthorized IDs, and ran all 10 pytest tests (all passed).
- What I changed: added `.resolve()` directory boundary validation so downloads and deletes can never escape `UPLOAD_DIR`.

## Mistakes the AI made
- 1 Nov: Claude gave me Command Prompt commands (rmdir /s /q) while I was in PowerShell, so they failed. I used the PowerShell equivalent.
- 1 Nov: Claude told me to pick "Installer" on nodejs.org, but the page no longer offers that option. I used winget instead.
- 2 Nov: When Claude rewrote my README in a public-repo style, it dropped the "What works right now" section, so my next instruction to edit it pointed at something that did not exist.
- 3 Nov: Claude's test for the production SECRET_KEY check printed nothing because my terminal still had a local SECRET_KEY set. I cleared it and the test showed the expected error.
- 4 Nov: Claude gave me `cd C:\Users\nnikh\testfiles` while my terminal was on the `D:` drive without the `/d` flag, so the 4 test files were created inside my repo root. I deleted them and used `cd /d` so they were never committed.
- 4 Nov: When pasting terminal commands, `pip freeze > requirements.txt` merged with the next command and created an untracked `requirements.txtpip` file, which I deleted before committing.