# Daily log

One entry per day, written at the end of the day. Only what really happened.

## Day 1: Sun 1 Nov
**Done**
- Created the private GitHub repository
- Checked Node, npm, Git and Python on my laptop
- Fixed Node not being on PATH (added it manually)
- Tested that Python 3.15 can install FastAPI, SQLAlchemy and the Postgres driver
- Wrote the documentation skeleton and the first draft of the permission model

**Not done / problems**
- Backend skeleton, frontend scaffold and Render deployment moved to Day 2

**AI used today**
- Claude: planning, stack choice, setup help. Antigravity: used to read and understand the brief, no code generated. Details in PROMPTS.md.

**Tomorrow**
- FastAPI backend with a working /health route
- Database models, registration, login, roles

---

## Day 2: Mon 2 Nov
**Done**
- Created the FastAPI backend skeleton with a /health route and ran it locally
- Created the React (Vite) scaffold and ran the starter page
- Committed each step separately
- Created a Render web service for the backend (root directory backend, free plan, start command uvicorn app.main:app)

**Not done / problems**
- main.py was not saved when I first ran uvicorn, so it said the app was not found. Saving fixed it.
- A typo at the npm prompt ("y" typed with a stray dot) cancelled the Vite install, so I ran the command again.
- I typed the uvicorn command into the Build Command box on Render by mistake, and fixed it before deploying.
- Database, authentication and roles not started yet

**AI used today**
- Claude: step-by-step setup of the backend, frontend and Render settings. Details in PROMPTS.md.

**Tomorrow**
- Finish Render deploy, create the database tables, registration and login

---

## Day 3: Tue 3 Nov
**Done**
- Database connection and four tables (users, documents, permissions, audit_log)
- Password hashing with bcrypt, register endpoint, login endpoint with JWT, /auth/me
- Roles (user, admin, auditor), an admin-only /admin/users route and a seed script for demo accounts
- Central permission function (permissions.py) with automated tests (9 passed)
- Backend live on Render, with APP_ENV and SECRET_KEY set there
- Second-opinion security review of my auth and permission code with Codex, and fixes (see PROMPTS.md and THREATS.md)

**Not done / problems**
- Named a file modules.py instead of models.py, which caused an import error until I renamed it
- Ran the server from the wrong folder and without the virtual environment
- Left alice as an admin after a role test, so the admin login failed until I reset her and ran the seed
- Created vault.db by hand once instead of letting the app create it
- Committed 10 files in one commit at the end of the day instead of small commits
- No document upload yet

**AI used today**
- Claude: step-by-step code and explanations. Codex: read-only security reviewer. Details in PROMPTS.md.

**Tomorrow**
- Postgres on Render, then document upload, document routes and sharing

---

## Day 4: Wed 4 Nov
**Done**
- Set APP_ENV and SECRET_KEY on Render
- Made the database URL work with the psycopg 3 driver
- Built file upload with type whitelist, magic-byte checks, 5 MB cap, and random UUID storage
- Codex security review for uploads (Round 3) and logged 4 findings in THREATS.md

**Not done / problems**
- Port 8000 was already in use by an old server I never stopped. I found the process and stopped it.
- Postponed connecting live Postgres on Render to keep moving on core document logic locally.

**AI used today**
- Claude: step-by-step code and explanations. Codex & Gemini: security review and threats. Details in PROMPTS.md.

**Tomorrow**
- Document management routes (list, download, delete) and sharing routes calling can()

---

## Day 5: Thu 5 Nov
**Done**
- Implemented document management routes: GET /documents, GET /documents/{id}, GET /documents/{id}/download, and DELETE /documents/{id}
- Enforced can() across all document operations (only owners can delete; readers/editors can download)
- Codex security review (Round 4): hardened download and delete routes against path traversal using resolved directory boundary checks
- Implemented document sharing lifecycle: POST /documents/{id}/share, GET /documents/{id}/shares, and DELETE /documents/{id}/share/{user_id}
- Replaced repetitive Swagger testing with automated pytest suite (test_sharing.py) covering upload, permission checks, unauthorized downloads, and revocation (10 tests passing)

**Not done / problems**
- Hit Claude's free tier token wall in a long chat thread; switched to Gemini and started using automated tests to work faster
- PowerShell script execution policy blocked venv activation script until unblocked with Set-ExecutionPolicy
- TestClient failed initially because httpx was missing from venv; installed httpx and updated requirements.txt
- Audit log not built yet

**AI used today**
- Gemini: guidance for document routes, path traversal hardening, sharing endpoints, and pytest suite. Codex: read-only security reviewer (Round 4). Details in PROMPTS.md.

**Tomorrow**
- Tamper-evident SHA-256 audit log, Postgres database attachment on Render