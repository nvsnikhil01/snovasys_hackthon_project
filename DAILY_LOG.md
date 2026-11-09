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

---

## Day 6: Fri 6 Nov
**Done**
- Evaluated early `sample_V1` prototype against current implementation with Codex for UI design and security hardening gaps
- Planned migration from inconsistent inline styles to a centralized design system using a dark amber/gold cyber-vault theme
- Documented key UX layouts matching mobile/desktop references: login/registration cards, dashboard document listings ("My documents" and "Shared with me"), upload modal, and the bottom-sheet share access picker
- Identified future hardening targets from prototype comparison: login rate limiting, session revocation, and explicit audit trigger verification

**Not done / problems**
- Zipped prototype initially included `.venv` and cache files, which caused file analysis limits; bypassed by inspecting custom code paths locally
- Frontend full restyling implementation queued for final polish

**AI used today**
- Codex: prototype code comparison, security review, and UI design evaluation. Gemini: planning prompt generation and Markdown documentation synchronization. Details in PROMPTS.md.

**Tomorrow**
- Complete UI styling overhaul, wire up frontend sharing views to backend endpoints, and final submission prep

---

## Day 7: Sat 7 Nov

**Done**
- Completed the major frontend redesign using a consistent dark-themed TrustVault interface, responsive layouts, navigation, document tables and sharing dialogs.
- Improved authentication and audit security: required JWT expiration and subject claims, added password-length protection, and expanded audit event coverage.
- Improved permission filtering so only valid `read` and `edit` grants provide document access.
- Added document persistence and recovery support using database-stored file bytes alongside local file storage.
- Added Activity History functionality and improved document search and user-management interfaces.
- Expanded backend authorization and document-route test coverage.
- Added responsive layout improvements to Activity History.
- Updated the project through multiple focused Git commits.

**Not done / problems**
- Multi-process audit-write coordination was not implemented; the existing threading lock is process-local.
- Audit-chain deletion of the final records was not independently detectable.
- The final documentation and README still needed synchronization with the implementation.

**AI used today**
- Codex: code implementation assistance, security reviews and test coverage improvements.
- Gemini: planning and documentation assistance.
- ChatGPT: project review, task planning and implementation guidance.
- Details and specific contributions are recorded in PROMPTS.md.

**Tomorrow**
- Complete safe production role provisioning.
- Expand admin and auditor authorization tests.
- Harden document persistence and recovery.
- Continue Activity History and security improvements.

---

## Day 8: Sun 8 Nov

**Done**
- Completed safe production role provisioning for existing accounts, with explicit role selection and safeguards against accidental admin demotion.
- Expanded admin and auditor authorization coverage, including role-restricted routes and audit access.
- Hardened document file persistence by storing file bytes in the database as a recovery source alongside local file storage.
- Added document recovery behavior so downloads can restore missing local files from database-stored content.
- Improved audit logging for document mutations so successful delete, share and revoke operations record their operation-specific audit events in the same database transaction.
- Added tests for successful operations, denied attempts, transaction failures and audit-chain verification.
- Reviewed the Render deployment configuration and confirmed that the Uvicorn start command does not explicitly configure multiple workers.
- Confirmed that `AUDIT_KEY` and `APP_ENV` are configured in the Render environment.
- Pushed the completed changes to GitHub and confirmed that the latest Render deployment was Live.

**Not done / problems**
- The audit-write threading lock is process-local; it does not coordinate multiple workers or service instances.
- Deleting the latest audit records can still go undetected because an independent checkpoint mechanism has not been implemented.
- The Render instance count was not conclusively verified from the available dashboard information.
- Final documentation still needs to be synchronized with the implemented features and current security limitations.

**AI used today**
- Codex: implementation assistance, code review, security hardening and automated test improvements.
- ChatGPT: task planning, implementation review, Render configuration analysis and documentation guidance.
- Details and specific contributions are recorded in PROMPTS.md.

**Tomorrow**
- Review and update all submission documentation.
- Recheck the implementation against the assessment requirements.
- Review the remaining audit-chain and deployment limitations.
- Complete final testing and submission preparation.