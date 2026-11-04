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
- What I changed or rejected: [anything you changed]

## 3 Nov 2026 (review)
- Tool: Codex (ChatGPT) in VS Code, used as a read-only reviewer
- Asked it to: review my auth code (round 1) and my permission code (round 2)
- What it found: (1) the JWT secret changed on every restart, (2) registration reveals whether an email exists, (3) an invalid grant level in the database could give access, (4) no document routes yet to check, plus missing tests
- What I tested: [which findings you reproduced]
- What I changed: production now refuses to start without SECRET_KEY, only "read" and "edit" count as grants, and I added three tests
- What I rejected and why: the email-exists message stays, because hiding it needs email verification, which is out of scope. It is recorded in THREATS.md.

## Mistakes the AI made
- 1 Nov: Claude gave me Command Prompt commands (rmdir /s /q) while I was in PowerShell, so they failed. I used the PowerShell equivalent.
- 1 Nov: Claude told me to pick "Installer" on nodejs.org, but the page no longer offers that option. I used winget instead.
- 2 Nov: When Claude rewrote my README in a public-repo style, it dropped the "What works right now" section, so my next instruction to edit it pointed at something that did not exist.
- 3 Nov: Claude's test for the production SECRET_KEY check printed nothing because my terminal still had a local SECRET_KEY set. I cleared it and the test showed the expected error.