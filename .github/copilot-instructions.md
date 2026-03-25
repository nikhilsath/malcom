# Agent Instructions for nikhilsath/malcom

**AGENTS policy files are the authoritative source for all development decisions in this repo.**

All agents working on this project MUST read and follow the rules in:
- **[AGENTS.md](../AGENTS.md)** — Root routing, rules matrix, and machine index (read this first)
- **[backend/AGENTS.md](../backend/AGENTS.md)** — Backend, schema, and tool/backend contract policy
- **[ui/AGENTS.md](../ui/AGENTS.md)** — Frontend structure, shell, styles, and route wiring policy
- **[tests/AGENTS.md](../tests/AGENTS.md)** — Verification workflow and testing policy
- **[README.md](../README.md)** — Project overview and goals

## Critical Rules (TL;DR)

1. AGENTS.md is the source of truth for how to build in this repo
2. Follow the file placement rules — do not invent new structure
3. Extend existing sources of truth; do not create parallel ones
4. Include testing/verification in every response
5. Schema changes go in `backend/database.py`, not in the database file itself
6. Google connector onboarding must start from the `Connect provider` control and must not use browser `prompt()` dialogs for OAuth credentials

For the full ruleset, read **AGENTS.md** first, then load only the relevant domain AGENTS file(s) based on task scope.

## Before You Code

- Read routing and machine index sections in AGENTS.md, then read relevant domain AGENTS file(s)
- Check if a similar pattern exists in the repo
- Follow "Do" and "Do Not" rules at the end of AGENTS.md
