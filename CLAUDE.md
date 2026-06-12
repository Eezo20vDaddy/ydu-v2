# YDU PARTS Rebuild

Ground-up rebuild of ydu.com.au (WooCommerce car parts store, VW/Audi/VAG specialist).
Deliverables: custom hybrid theme `ydu` + companion plugin `ydu-fitment`, evaluated
side-by-side at test.ydu.com.au before production launch.

Contracts: `spec.md` (product, authoritative) > `Plans.md` (task ledger). Read both
before any work.

## Stack

- WordPress 7.0 / WooCommerce 10.8 on LiteSpeed hosting (production: ydu.com.au)
- Theme: hybrid (classic PHP templates + theme.json + block patterns), wp-scripts build
- Front-end interactivity: WordPress Interactivity API (script modules), vanilla JS, no frameworks
- Plugin `ydu-fitment`: hierarchical vehicle taxonomy, `fitment/v1` REST endpoints, importer
- PHP 8.x; HPOS-safe CRUD only (no direct postmeta SQL); local dev via wp-env (or LocalWP)
- Access to live site: REST API with Application Password only — **read-only until launch**

## Team & Hierarchy (canonical source: `.claude/agents/`)

```
CEO (Ernest — approvals, direction, exceptions)
├── cto-architect        (Opus)  — technical authority, task decomposition, review, Gate 1
├── auditor-watchkeeper  (Opus)  — independent audit, READ-ONLY, Gate 2, cannot be overridden by CTO
├── document-flow        (Opus)  — HTML plan/flow documents for CEO review
└── cto-architect delegates to:
    ├── wordpress-lead   (Sonnet) — ydu-fitment plugin, PHP/Woo server-side, data import, discovery tooling
    ├── frontend-lead    (Sonnet) — brand system, all theme UI, pixel-perfect/mobile quality bar
    ├── qa-engineer      (Sonnet) — PHPUnit + Playwright suites, QA checklist, quality gatekeeper
    └── code-inspector   (Sonnet) — READ-ONLY inspection reports to CTO
```

## Working Norms (imported from LevelUpAI harness governance)

- **All changes via the harness** — the main context never edits code directly; delegate
  (start with `/harness-plan`, execute with `/harness-work`). Bypass only on explicit CEO
  say-so, valid for a single change (not the session).
- **Harness governs ALL changes** — including tooling and docs. No exceptions.
- **Announce agent handoffs** before launching any agent.
- **No aggressive polling** — background long tasks, check sparsely.
- **Never deploy without an explicit CEO go** — an answer about targets/preferences is
  not a deploy trigger. This includes installing anything on test.ydu.com.au.
- **CEO communication style:** lead with the answer; very concise; flag decisions needing
  CEO input explicitly; escalation format = summary / options / trade-offs / recommendation.

## Release Process

**3-Gate chain:** cto-architect approves → auditor-watchkeeper approves → CEO approves.

| Gate target | What it means here |
|---|---|
| Deploy to test.ydu.com.au | Theme/plugin zips installed on the side-by-side clone (Plans 5.1) |
| Production launch | Activation on ydu.com.au (Plans 5.3) — highest gate, double confirmation |

- No direct commits to `main`/`develop`. All work on `feature/*` branches:
  `feature/theme-*` (frontend-lead), `feature/fitment-*` (wordpress-lead),
  `feature/qa-*` (qa-engineer), `feature/docs-*`.
- TDD where Plans.md marks `[tdd:required]` (fitment importer + REST endpoints).

## Hard Safety Rules (from spec.md §2 — non-negotiable)

1. **Production write policy:** never delete or edit products, orders, customers, or
   catalog data — on production or the clone. Pre-launch production writes are limited
   to clone creation; launch writes are limited to installing zips, creating pages/menus,
   activating.
2. **Never copy the staging database over production** — live orders accrue during the
   side-by-side period.
3. **Zoho Inventory connector:** working on production, must not be disturbed; MUST be
   disabled on the clone before any test order (else real Zoho sales orders/stock moves).
4. Backups before any production change; old theme/plugin cleanup only after CEO
   confirms the new site stable.

## What the CEO Approves

- Any install/activation on production OR test.ydu.com.au
- Production launch and cleanup (Plans 5.3, 5.4)
- Design direction (mockup variant selection) and scope changes to spec.md
- Plugin purchases/licenses (e.g. WP Staging Pro) and any spend
- Anything touching the Zoho connector or live store data
