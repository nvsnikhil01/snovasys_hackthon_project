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
-

**Not done / problems**
-

**AI used today**
-

**Tomorrow**
-

---

(Copy the same block for Day 4 Wed 4 Nov, Day 5 Thu 5 Nov, Day 6 Fri 6 Nov, and Day 7 Sat 7 Nov.)