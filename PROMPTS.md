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
- What I changed or rejected: I did not use the paid Claude Code extension. [Add only if true: I installed it in VS Code but did not sign in.]

## Mistakes the AI made
- 1 Nov: Claude gave me Command Prompt commands (rmdir /s /q) while I was in PowerShell, so they failed. I used the PowerShell equivalent.
- 1 Nov: Claude told me to pick "Installer" on nodejs.org, but the page no longer offers that option. I used winget instead.