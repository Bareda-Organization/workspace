# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is — the workspace

The **workspace** for **"바래다" (Baraeda)**, a **multi-tenant platform** for running academy shuttle buses and tracking students' arrivals and departures.
This folder (`baraeda/`) is the GitHub repo `Bareda-Organization/workspace` and tracks **only documents and Claude settings**.
Code lives in the three repos below, cloned side by side inside this folder (this repo's `.gitignore` ignores all three).

| Folder | Repo | Holds | Deploys to |
|---|---|---|---|
| `./` (this folder) | `workspace` | **All documents `docs/`** · this file · `.claude/` (settings, fact notes, skills) | — |
| `backend/` | `backend` | Spring Boot (`backend/backend/`) · `infra/` · `docker-compose*.yml` | AWS EC2 · local (home PC + Cloudflare Tunnel) |
| `web/` | `web` | Staff web (Next.js) · `design-system/` (read-only kit copy) | Vercel |
| `mobile/` | `mobile` | 2 apps (`apps/manager-app` · `apps/parent-app`) · shared packages `packages/baraeda_{core,ui}` | App Store · Play Store |

- **Split from the monorepo `mskim98/School-Bus` on 2026-10-02** (history moved with `git filter-repo`). Read old code paths in docs through the mapping table in `docs/README.md §0`
- **git is per repo** — `git` in this folder handles only docs and settings. For code: `git -C backend …` · `git -C web …` · `git -C mobile …`. Pull all four (`git pull` + `git -C <repo> pull`)
- **API-changing work merges in the order docs → backend → web·mobile.** Spec (`docs/planning/API_SPEC.md`) first, server next, clients last
- **Places that link the repos by relative path** — web's error-code contract test reads `../docs/planning/API_SPEC.md`, mobile's copy-text test reads `../web/…`, backend compose's `web` service reads `../web`. ⚠ **Worktrees live elsewhere**, so give agents inside them `API_SPEC_PATH` · `WEB_REPO_DIR` as absolute paths
- ⚠ **All remotes are public repos.** Before pushing, check that real values from `backend/backend/.env` · `web/.env.local` are not in the commit
- **Tracked here** — `docs/**/*.md` · `CLAUDE.md` · `.claude/{settings.json,PROJECT_NOTES.md}` · the 2 hand-written skills · `.claude/bin/` (old goal-table gate copy — the gate, `goal-verifier` · `task-gate-reviewer` and the working method moved to global on 2026-10-13: Skill `agent-workflow`). Global `~/.claude` settings are recorded in the separate remote-less repo `~/.claude-config.git` (`claude-cfg status` · `claude-cfg diff`). Untracked: human renders (`docs/render/`) · planning originals (`.docx` in `docs/planning/source/`) · reports (`report/`) · per-round working files (the rest of `.claude/`) · indexes (`graft/` · `.docgraph/`)
- Indexes — **docs: docgraph** (`.docgraph/` here, refreshed by an edit hook) · **code: one graft per repo** (`backend/graft/` · `web/graft/` · `mobile/graft/`). This folder's `.mcp.json` starts them as `graft-backend` · `graft-web` · `graft-mobile` — pick the tool for the repo you're asking about. The CLI takes the folder: `graft ask "…" web`
  - Why not one index (measured 2026-10-02) — graft skips sub-repos that git ignores. Merging would require this repo to stop ignoring the three folders, and then a single `git add -A` would wrongly add them as submodule links

**Frontend is in scope by user decision on 2026-09-10** — overturning Ruling 255 (2026-09-04, permanently out of scope). The Phase F1–F4 `➖` marks in `docs/IMPLEMENTATION_PLAN` refer to the old Flutter plan and stay as is; **the entry point for frontend work is the separate `docs/frontend/IMPLEMENTATION_PLAN.md`.**

- 3 products — staff web (**Next.js**; the main admin console merged in as the `(admin)` route group) · parent/student app (**Flutter**) · manager app (**Flutter**)
- **One app splits by the role in the login result** — parent↔student, driver↔escort. What splits is permissions and entry points, not screens
- Code rules: `docs/frontend/web/CONVENTIONS_REACT.md` (React) · `docs/frontend/mobile/CONVENTIONS_FLUTTER.md` (Dart)
- The design-system copy is the web repo's `design-system/` (**read-only**; the source is remote on claude.ai). ⚠ **The kit is based on the old plan and diverges from `docs/` in places** — `docs/` wins; the 4 confirmed cases are in `docs/frontend/IMPLEMENTATION_PLAN.md §4`

- **Always read [`docs/README.md`](docs/README.md) before starting work.** It's the entry point to the 4 product specs (`FEATURE_SPEC` · `PRD` · `USER_FLOWS` · `API_SPEC`), which are the **single source of truth (SoT)**. **They were fully rewritten after the 2026-08-24 change of service direction and are pure To-Be plans with no implementation-status marks** — much of the current code diverges from them and is to be fixed toward the spec.
- **The foundation is `docs/planning/FEATURE_SPEC.md`** — common rules C-01~18, policy constants (confirm 30 min before departure · section ② once per run · run start ±10 min, etc.), entities/state machines and the feature-ID scheme are defined there, and the other 3 reference it. Don't invent new feature IDs or state values.
- `🔸` in docs marks items absorbed from the old plan whose **retention is undecided** — don't treat them as confirmed facts. (`🆕`, which marked ungrounded new designs, was approved wholesale and removed on 2026-08-24.)
- **The design docs are `docs/backend/ARCHITECTURE.md` (modules · authorization · route pipeline · time-based batch) and `docs/backend/ERD.md` (tables · constraints · indexes).** Both are **To-Be designs** derived from the 4 specs and differ from the current code — aligning code to them is the work ahead. The pre-pivot code snapshot: `git show HEAD:docs/backend/ARCHITECTURE.md`.
- **Time is the backbone of this service** — a run's `idle → confirmed` transition is triggered not by a user action but by **reaching 30 minutes before departure** (`ARCHITECTURE §9`). The batch is 30-second polling + idempotent conditional UPDATE; never mix the two clocks, "execution time" and "judgment time (departure − 30 min)".
- **Implementation planning and progress tracking go through [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) only.** On resume, check the current Phase in the §8 progress table and update that table when work ends. Cross-cutting rules are §7 (**26** — #26 is the stop criterion for spec-audit rounds, `Ruling 889`). **Cleaned up 2026-10-01 — the body keeps only the rules (§0–§7), the progress table (§8), open items (§9), the Ruling index (§11) and recent round sections (`R46-*`); finished Phase/round records were moved verbatim to `docs/archive/rounds/`** (file and section ranges are in that folder's `README.md` — find old section numbers like 8.45 by the same-numbered heading). Find where a Ruling is recorded via the §11 index.
- **The smallest unit of work is one feature ID, not a Phase, processed with the TDD cycle in `IMPLEMENTATION_PLAN §4.6`** — goal → RED (see the failure with your own eyes) → GREEN (minimal implementation) → REFACTOR → verify. **A test you never saw fail is not a deliverable.** This system's 4 defect classes (time · concurrency · authorization · personal-data exposure) all look identical to "an empty test that passes", so seeing RED is the only way to tell.
- **Code conventions: `docs/backend/CODE_CONVENTIONS.md`** — especially §19 (one-line description comments on classes, public methods, enums, events and ports) and §20 (SRP · size limits · clean code) are graded every Phase.
- The only planning original is `docs/planning/source/학원 통학버스 통합관리 시스템.docx` (immutable). The root `projectInfo.md` was **deleted on 2026-08-24** — it was two generations stale with a high risk of misquoting. If needed: `git show HEAD:projectInfo.md`.
- When facts conflict across documents, **`docs/` wins.**
- ⭐ **Documents live only in this folder's `docs/` — split into planning · backend · frontend (web · app) on 2026-10-02.** Folder map: `docs/README.md §0`.

  | Location | Holds |
  |---|---|
  | `docs/` root | doc map `README.md` · overall progress tracking and Ruling index `IMPLEMENTATION_PLAN.md` |
  | `docs/planning/` | **Planning** — the 4 specs (`FEATURE_SPEC` · `PRD` · `USER_FLOWS` · `API_SPEC`) · planning original `source/` |
  | `docs/backend/` | **Backend** — `ARCHITECTURE` · `ERD` · `TECH_DECISIONS` · `CODE_CONVENTIONS` · `LOAD_TESTING` · `plans/` · `infra/` (`DEPLOYMENT` · `STAGING`) |
  | `docs/frontend/` | **Frontend common** — `IMPLEMENTATION_PLAN` · `SETUP` · `web/CONVENTIONS_REACT` · `mobile/CONVENTIONS_FLUTTER` |
  | `docs/archive/` | Finished per-feature plans/designs · `rounds/` = finished plan rounds and Phase records |
  | `docs/render/` | Human renders (untracked) |

  - Code repos keep only `README.md` · `CLAUDE.md` · `AGENTS.md` · app/package `README`·`CHANGELOG` (tools look for them by directory)

- 6 user types (`Role` enum): parent `PARENT` · student `STUDENT` · driver `DRIVER` · escort `ESCORT` · academy staff `STAFF` · main admin `SYSTEM_ADMIN` — academy staff and main admin are separate roles with completely different permission scopes
- Multi-tenancy: one account belongs to one academy (`account.academy_id`; null only for the main admin — `ck_account_academy_scope`). The old `User`↔`Tenant` N:M and the `UserTenantRole` join table disappeared with the 2026-08-24 pivot. Isolation is enforced not at the DB level (RLS · `@Filter`) but **in application code** — `AcademyScope`, which takes the scope only from the token, plus the academy condition in repository queries (`ARCHITECTURE §6`).

## Launching worktrees and worker windows with Orca

🔴 **Before running `orca worktree create` · `worker-start` · `terminal create`, read Skill `orca-launch` (global — general rules) and Skill `orca-baraeda` (this repo's Orca ids · base branch · worktree location · design windows).** They cover `--setup skip` by default · explicit `--model`·`--effort` per worker (sonnet always `[1m]`) · one-line launch · the `Default view` trap · `worker_done` sending (Haiku 4.5 doesn't send · 5.5 confirmed to send) · `worktreeBaseRef`. For coordination (waiting · settling up), continue with Skill `orchestration`.
**Write worker briefs and inter-agent messages in English** (global Language rule).

## Per-repo guides

Touching a repo's files also loads that folder's `CLAUDE.md`.

- **backend** — build/test commands (`-PtestDbUrl` required) · Docker layout (ports 15432·16379·3000) · Flyway policy · stack: `backend/CLAUDE.md`
- **web** — commands (`scripts/verify.sh` · `scripts/test-contract.sh`) · Vercel caveats: `web/CLAUDE.md`
- **mobile** — commands (`scripts/verify.sh`) · `--dart-define=API_BASE_URL`: `mobile/CLAUDE.md`

**For design constraints, the data model and feature scope, read `docs/`** — common rules, entities, state machines and permissions: `docs/planning/FEATURE_SPEC.md` (§2·§3·§6); policy rationale and priorities: `docs/planning/PRD.md` (§6·§7); endpoint contracts: `docs/planning/API_SPEC.md`. Module boundaries, the 3 authorization layers, the route pipeline and the time-based batch: `docs/backend/ARCHITECTURE.md` (§3·§5·§6·§8·§9).

## Reply / document rules

The user is a backend developer at the Spring-beginner stage. Follow the global `~/.claude/CLAUDE.md` rules (Korean replies in the main session, a one-line summary per concept → numbered flow → request→processing→response, link to Controller/Service/Repository, at least one common misconception).

**Document format**: technical docs that humans read in a browser (architecture, rules, etc.) are written as HTML + inline SVG per the global policy. But **the spec/design/progress/convention docs Claude re-reads every session (the 8 in `docs/`, `CODE_CONVENTIONS.md`, etc.) stay Markdown for token efficiency** (HTML's SVG/CSS scaffolding only adds reload cost). A human HTML render of the same content (e.g. `CODE_CONVENTIONS.html`) may exist separately; the two sync principles only and don't replace each other.

**HTML doc edit rule (confirmed 2026-07-18)**: human HTML docs such as `CODE_CONVENTIONS.html` are created or edited **only when the user explicitly asks.** Changing the Markdown source (`CODE_CONVENTIONS.md` etc.) does not auto-sync the matching HTML — the user asks separately if needed.
