<h1 align="center">🔐 Trust Vault</h1>

<p align="center">
  A secure document-sharing application with per-document permissions, strict role-based access control, and robust security hardening.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-completed%20prototype-success" alt="status" />
  <img src="https://img.shields.io/badge/frontend-React%20%2B%20Vite-61DAFB" alt="frontend" />
  <img src="https://img.shields.io/badge/backend-FastAPI-009688" alt="backend" />
  <img src="https://img.shields.io/badge/database-SQLite%20%7C%20PostgreSQL-336791" alt="database" />
</p>

> Built for the Snovasys Fresher Hiring Challenge 2026 – RISE. Individual submission.
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

- [x] Registration and login (bcrypt password hashing, JWT authentication)
- [x] Role-based access control: user, admin, auditor
- [x] File upload with type validation, magic-byte checks, and 5 MB size limit
- [x] Document listing, secure downloading, and deletion
- [x] Per-document permissions: read, edit, share, and revoke
- [x] Centralized server-side permission checks
- [x] Tamper-evident HMAC-SHA256 audit logging
- [x] Audit events for successful operations and denied attempts
- [x] Permission-aware document access and search
- [x] Personal and system-wide Activity History
- [x] Admin and auditor views with role-based authorization
- [x] Document persistence and recovery using database-stored file bytes
- [x] Responsive React frontend
- [x] Automated backend authorization, audit, and sharing tests
- [x] Live deployment on Render

---

## ✅ Current Status

Implemented and deployed:

- Frontend: https://trustvault-f58w.onrender.com
- Backend: https://snovasys-hackthon-project.onrender.com
- API documentation: https://snovasys-hackthon-project.onrender.com/docs

Implemented functionality:

- Registration, login, bcrypt password hashing, JWT authentication, and `/auth/me`.
- Roles (`user`, `admin`, `auditor`) with server-side authorization.
- Document upload with file validation, magic-byte checks, and a 5 MB size limit.
- Document listing, downloading, deletion, sharing, and permission revocation.
- Centralized document authorization using `can()`.
- HMAC-SHA256 tamper-evident audit logging and audit verification.
- Personal and system-wide Activity History with filtering and export functionality.
- Admin and auditor authorization and management views.
- Database-backed document persistence and recovery.
- Atomic database transactions for document mutations and their corresponding success audit events.

The project includes automated backend tests covering authentication, permissions, document operations, audit logging, and authorization.

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
│   ├── seed.py
│   ├── requirements.txt
│   ├── uploads/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── security.py
│   │   ├── dependencies.py
│   │   ├── permissions.py
│   │   ├── audit.py
│   │   └── routes/
│   └── tests/
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
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

**Run the backend**
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

**Run the frontend**
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
- Passwords are hashed using bcrypt and never stored in plaintext.
- Production requires a configured `SECRET_KEY`.
- Production requires a configured `AUDIT_KEY`.
- User roles are read from the database on each request, rather than trusted from the JWT.
- Document operations use centralized server-side permission checks.
- Invalid permission levels do not grant access.
- Files are stored privately and served through authenticated routes.
- Resolved file paths are checked against the upload directory.
- Audit events use an HMAC-SHA256 hash chain.
- Successful document mutations and their corresponding audit events are committed in the same database transaction.
- Personal and administrative Activity History access is restricted by role.

See [THREATS.md](THREATS.md) for verified findings, mitigations, and remaining limitations.

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

I used Claude, Antigravity, Gemini, Codex, and ChatGPT during development for planning, understanding the requirements, implementation guidance, code reviews, security analysis, testing assistance, and documentation.

AI-generated suggestions and code were reviewed and tested before being retained. I made the final implementation decisions and maintained the project code and development workflow.

The tools used, their contributions, and mistakes identified during development are documented in [PROMPTS.md](PROMPTS.md).

---

## ⚠️ Known Limitations

- No login rate limiting.
- Registration responses can reveal whether an email address already exists.
- The audit-write threading lock is process-local and does not coordinate multiple workers or service instances.
- The audit chain does not yet have an independent protected checkpoint to detect deletion of its latest records.
- File storage quotas and automated retention/cleanup policies are not implemented.
- Physical file cleanup is separate from the database transaction.
- The application has not undergone an independent production security audit.

See [THREATS.md](THREATS.md) for details.