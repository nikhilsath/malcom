# Agent Instructions for nikhilsath/malcom

**This is the authoritative source for all development decisions in this repo.**

All agents working on this project MUST read and follow the rules in:
- **[AGENTS.md](../AGENTS.md)** — Primary operational manual (read this first)
- **[README.md](../README.md)** — Project overview and goals
- **[DESIGN.md](../DESIGN.md)** — UI design rules (when creating or modifying UI)

## Critical Rules (TL;DR)

1. AGENTS.md is the source of truth for how to build in this repo
2. Follow the file placement rules — do not invent new structure
3. Extend existing sources of truth; do not create parallel ones
4. Include testing/verification in every response
5. Schema changes go in `backend/database.py`, not in the database file itself

For the full ruleset, **open AGENTS.md and read it in full before starting work.**

## Before You Code

- Read the relevant section of AGENTS.md for your task type
- Check if a similar pattern exists in the repo
- Follow "Do" and "Do Not" rules at the end of AGENTS.md
