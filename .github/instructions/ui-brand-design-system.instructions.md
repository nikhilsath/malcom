---
applyTo: "ui/**/*.{css,html,js,ts,tsx}"
description: "Enforce Malcom UI brand color token usage for buttons, selected states, hover emphasis, hero gradients, technical accents, and connector focus states."
---

# Malcom UI Brand Design System Enforcement

For any UI edits in this repo, use the shared token system in `ui/styles/base.css`.

## Canonical Palette

- `--brand-deep`: `#341475`
- `--brand-primary`: `#441D81`
- `--brand-main`: `#5631BA`
- `--brand-bright`: `#783AD0`
- `--brand-highlight`: `#AF50E6`
- `--accent-sky`: `#4FA8F4`
- `--accent-electric`: `#304DF5`
- `--neutral-surface`: `#E0DAED`
- `--neutral-muted`: `#B4ADCD`
- `--neutral-secondary-text`: `#7A759A`

## Required Usage Mapping

- Main brand actions/buttons/selected state: `--brand-main` or semantic alias `--primary`
- Hover/strong emphasis: `--brand-primary` or semantic alias `--primary-hover`
- Hero highlights/gradients: `--brand-bright` + `--brand-highlight` or semantic aliases `--hero-gradient-start` + `--hero-gradient-end`
- Technical accent/active connectors/focus state: `--accent-sky` or semantic alias `--technical-accent`
- Strong active blue emphasis: `--accent-electric` or semantic alias `--technical-accent-strong`

## Hard Rules

1. Do not introduce new hardcoded hex values for brand/accent/neutral roles in UI code.
2. Prefer semantic variables before direct canonical variables when a semantic variable already exists.
3. If a new UI color role is needed, add a semantic token in `ui/styles/base.css` mapped to canonical palette values.
4. Keep color source of truth centralized in `ui/styles/base.css`; do not define new per-page palette systems.
