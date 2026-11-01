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

- [ ] Registration and login (hashed passwords, JWT)
- [ ] Roles: user, admin, auditor
- [ ] File upload with type and size validation, stored privately
- [ ] Per-document permissions: read, edit, share, revoke
- [ ] Central permission check used by every route
- [ ] Audit log including denied attempts, tamper-evident
- [ ] Permission-aware search
- [ ] Admin view
- [ ] Automated permission tests
- [ ] Live deployment

---

## 🛠 Tech Stack
| Layer | Technology |
|---|---|
| Frontend | React, Vite |
| Backend | FastAPI (Python), SQLAlchemy |
| Database | SQLite (development), PostgreSQL (deployment) |
| Hosting | Render (planned) |

---

## 📁 Project Structure
Planned layout. Folders appear as they are built.

```
.
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── security.py        # passwords, tokens
│   │   ├── permissions.py     # the single permission check
│   │   ├── audit.py
│   │   └── routes/
│   └── tests/
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
Setup instructions are not available yet. They will be added once there is something to run, and tested on a fresh clone before submission.

**Prerequisites** (already installed on my machine)
- Python 3.10 or newer
- Node.js 20 or newer
- Git

**Demo accounts:** not created yet. They will be listed here once the seed script exists.

---

## 🛡 Security Approach
- Passwords are hashed, never stored in plain text.
- Every route calls the same permission function.
- A denied request looks the same as "not found".
- Search only returns documents the user may read.
- Files are served only through an authenticated route, never as public static files.

This lists the design goals. See [THREATS.md](THREATS.md) for what I actually tested.

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
I used AI tools (Claude for planning and guidance, Antigravity as an editor/reference) and log each use in [PROMPTS.md](PROMPTS.md). I read and run all generated code, and I only keep code I can explain.

---

## ⚠️ Known Limitations
- Features marked unchecked above are not built yet.
- This list will be updated at the end with anything unfinished or untested.