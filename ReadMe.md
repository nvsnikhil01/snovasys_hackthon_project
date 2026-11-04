<h1 align="center">🔐 Trust Vault</h1>

<p align="center">
  A secure document-sharing app with per-document permissions and a tamper-evident audit log.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-work%20in%20progress-orange" alt="status" />
  <img src="https://img.shields.io/badge/frontend-React%20%2B%20Vite-61DAFB" alt="frontend" />
  <img src="https://img.shields.io/badge/backend-FastAPI-009688" alt="backend" />
  <img src="https://img.shields.io/badge/database-SQLite%20%7C%20PostgreSQL-336791" alt="database" />
</p>

> Built for the Snovasys hackathon, 1 to 7 Nov 2026. Individual submission.

---

## 📑 Table of Contents
- [About](#-about)
- [Current Status](#-current-status)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Security Approach](#-security-approach)
- [Documentation](#-documentation)
- [Use of AI](#-use-of-ai)
- [Known Limitations](#-known-limitations)

---

## 📖 About
Trust Vault lets users upload files and decide exactly who can read or edit each one. The server checks permissions on every request, and every action, including refused attempts, is written to an audit log.

**Design principles**
- Access is denied by default.
- One central permission function makes every decision.
- The browser is never trusted, so all checks run on the server.
- Denied attempts are logged too, because failed access is what an investigator needs to see.

---

## ✨ Features
Checked items work and have been tested. Unchecked items are planned.

- [x] Registration and login (hashed passwords, JWT)
- [x] Roles: user, admin, auditor
- [ ] File upload with type and size validation, stored privately
- [ ] Per-document permissions: read, edit, share, revoke
- [ ] Central permission check used by every route
- [ ] Audit log including denied attempts, tamper-evident
- [ ] Permission-aware search
- [ ] Admin view
- [ ] Automated permission tests
- [ ] Live deployment

---

## ✅ Current Status
Working and tested:
- Backend deployed on Render: https://snovasys-hackthon-project.onrender.com
- Registration, login (bcrypt + JWT) and `/auth/me`
- Roles (user, admin, auditor) with an admin-only `/admin/users` route
- Seed script for demo accounts
- Central permission function with automated tests
- React + Vite starter page (local, no app pages yet)

Not built yet: document upload, per-document routes, sharing, audit log, search, and the frontend pages.

---

## 🛠 Tech Stack
| Layer | Technology |
|---|---|
| Frontend | React, Vite |
| Backend | FastAPI (Python), SQLAlchemy |
| Database | SQLite (development), PostgreSQL (deployment) |
| Hosting | Render (backend live) |

---

## 📁 Project Structure
Current layout. More files are added as features are built.

```
.
├── backend/
│   ├── seed.py                # demo accounts
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── security.py        # passwords, tokens
│   │   ├── dependencies.py    # current user, role checks
│   │   ├── permissions.py     # the single permission check
│   │   └── routes/            # auth.py, admin.py
│   └── tests/                 # test_permissions.py
├── frontend/
│   └── src/
├── docs/
│   └── PERMISSIONS.md
├── DAILY_LOG.md
├── PROMPTS.md
├── THREATS.md
└── README.md
```

---

## 🚀 Getting Started
**Prerequisites:** Python 3.10 or newer, Node.js 20 or newer, Git.

**Run the backend** (Windows, Command Prompt)
```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload
```
Then open http://127.0.0.1:8000/docs

**Run the tests**
```
cd backend
python -m pytest -v
```

**Run the frontend** (starter page only for now)
```
cd frontend
npm install
npm run dev
```

**Demo accounts** (created by `seed.py`, for demonstration only)

| Email | Password | Role |
|---|---|---|
| admin@example.com | admin-demo-123 | admin |
| auditor@example.com | auditor-demo-123 | auditor |
| alice@example.com | password123 | user |
| bob@example.com | password123 | user |

I will re-test these steps on a fresh clone before submitting.

---

## 🛡 Security Approach
Implemented:
- Passwords are hashed with bcrypt and never stored in plain text.
- The user's role is read from the database on every request, not trusted from the token.
- Login gives the same error for a wrong email and a wrong password.
- In production the app refuses to start without a fixed `SECRET_KEY`.

Planned (not built yet):
- Every document route calls the central permission function.
- A denied document request looks the same as "not found".
- Search only returns documents the user may read.
- Files are served only through an authenticated route.

See [THREATS.md](THREATS.md) for what I actually tested.

---

## 📚 Documentation
| File | Contents |
|---|---|
| [docs/PERMISSIONS.md](docs/PERMISSIONS.md) | Roles and per-document access rules |
| [DAILY_LOG.md](DAILY_LOG.md) | What I did each day, and what went wrong |
| [PROMPTS.md](PROMPTS.md) | Log of every AI-assisted step |
| [THREATS.md](THREATS.md) | Attacks I tried on my own system and what I fixed |

---

## 🤖 Use of AI
I used Claude for step-by-step guidance and code explanations, Antigravity to read and understand the brief, and Codex as a read-only security reviewer. Each use is logged in [PROMPTS.md](PROMPTS.md). I read and run all generated code, and I only keep code I can explain.

---

## ⚠️ Known Limitations
- Document upload, sharing, the audit log, search and the frontend pages are not built yet.
- There is no login rate limiting.
- Registration reveals whether an email is already registered (accepted, see THREATS.md).
