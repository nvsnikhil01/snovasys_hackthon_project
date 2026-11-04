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
- Created the React (Vite) frontend scaffold and ran the starter page
- Committed each step separately
- Created a Render web service for the backend (root directory backend, free plan, start command uvicorn app.main:app) [result: live / failed / still deploying]

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
- Central permission function (permissions.py) with automated tests [confirm: 9 passed]
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
- Set APP_ENV and SECRET_KEY on Render [confirm]
- Made the database URL work with the psycopg 3 driver [confirm]
- Postgres on Render: [created / connected / not yet]

**Not done / problems**
- Port 8000 was already in use by an old server I never stopped. I found the process and stopped it.

**AI used today**
- Claude: step-by-step code and explanations.

**Tomorrow**
- Document upload and per-document routes calling can()