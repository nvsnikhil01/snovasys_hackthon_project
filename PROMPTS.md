# AI usage log

I use AI tools and record every use here, including where they were wrong.

## 1 Nov 2026
- Tool: Claude (chat)
- Used it for: planning the 7-day timeline, choosing the stack, the folder structure, and the laptop setup checks.
- What I did myself: created the private repo, installed Node, tested that Python and the libraries install.
- Note: Node was installed but missing from PATH, so I added it manually.

## 1 Nov 2026 (second entry)
- Tool: Antigravity
- Used it for: reading the assessment brief and getting a first idea of the project
- What it suggested: building a document-sharing app with login, roles and an audit log
- What I kept: nothing, I only used it to understand the brief
- What I changed or rejected: I chose my own stack (FastAPI + React) after planning with Claude
- What I understood from it: the project needs per-document permissions checked on the server, and an audit log that records denied attempts too

## Plan for 2 Nov 2026 (Day 2)
- Set up the FastAPI backend and a working /health route
- Build the database models
- Build registration, login and password hashing
- Add roles
- Commit at least 3 times with real messages

## Mistakes the AI made
- 1 Nov: Claude gave me Command Prompt commands (rmdir /s /q) while I was in PowerShell, so they failed. I used the PowerShell equivalent.
- 1 Nov: Claude told me to pick "Installer" on nodejs.org, but the page no longer offers that option. I used winget instead.