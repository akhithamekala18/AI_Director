# AI Director — Decision Log (Day 1 Foundation)

- **Document:** `planning/decision-log.md`
- **Status:** APPROVED
- **Date:** 2026-08-28
- **Owner (approver):** Harshitha Mekala (GitHub: `akhithamekala18`)
- **Recorded by:** AI coding agent (Day 1 execution)
- **Governs:** Phase 0 and Backend Phase 1 + Frontend Phase 1 (Development Plan Days 2–18)
- **Basis:** docs/DEVELOPMENT_PLAN.md — Day 1 row ("Decision gates") and Section 9 (Decision Gates)

## 1. Purpose

Day 1 of the approved Development Plan requires locking every **DECISION REQUIRED** gate from
Development Plan Section 9 that is needed during Phase 0–B1–F1, recording the choices and their
rationale in a decision log, and reconfirming acceptance of the phased scope plus the
approval-safety guarantee.

This log records those decisions. It is a planning/governance document; no application code was
written as part of Day 1.

Decision gates not needed until Backend Phase 2 or later are recorded as **DEFERRED** (Section 6)
— they are not open for Phase 0–B1–F1.

## 2. Locked Decisions (Phase 0 – B1 – F1)

| ID | Gate | Decision | Rationale | Owner | Effective From |
| --- | ---- | -------- | --------- | ----- | -------------- |
| DG-1 | Frontend framework | **React + TypeScript + Vite** | Approved docs specify no frontend stack. React+TS+Vite fits the progressive-disclosure dashboard/studio/schedule UIs, strong static typing, fast dev server/build, large ecosystem; Vite is the standard modern bundler. | Harshitha Mekala | Day 2 foundation |
| DG-2 | Backend framework/language | **Django + Django REST Framework (Python)** | Approved docs specify no backend stack. Django provides built-in auth/users/teams/admin/audit groundwork and a mature ORM; DRF covers the API/service layer. Suited to the state-machine + invariant + test-oriented requirements and consistent with the project's existing Python tooling. | Harshitha Mekala | Day 2 foundation |
| DG-3 | Database + ORM | **PostgreSQL + Django ORM** | Robust relational DB with strong correctness guarantees; Django ORM removes a separate ORM decision and integrates with Django admin/migrations. | Harshitha Mekala | Day 3 contract pack |
| DG-4 | Project tooling, layout, lint/format, test frameworks | **Single repo with `backend/` (Django) + `frontend/` (Vite); Python: pip + `pyproject.toml`, ruff, pytest (+ django test runner via pytest-django); TypeScript: npm, ESLint + Prettier, Vitest + React Testing Library** | Matches the roadmap's planned `frontend/`/`backend/` structure. Toolchain choices are minimal, conventional, and give CI a lint/format/test command per stream. | Harshitha Mekala | Day 2 foundation |
| DG-5 | CI; and deployment platform | **CI: GitHub Actions (workflows in-repo). Deployment platform: DEFERRED to Day 55 (production readiness).** | Repository will live on GitHub; Actions provides in-repo CI config. Deploy hosting is not consumed until production readiness, so the platform choice is recorded as pending rather than assumed. | Harshitha Mekala | Day 2 (CI) / Day 55 (deploy) |
| DG-6 | Authentication implementation; MFA/SSO policy | **In-house Django auth (built-in user/team model) + DRF session/token auth for the API. MFA/SSO are surfaced as optional setts/options only and are NOT mandatory in V1 (per PRD "MFA not mandatory"; Overview §29.2 lists options).** | Keeps identity in-house with the chosen framework; respects the PRD decision that MFA is not mandatory in V1 while keeping the §29.2 option surface. | Harshitha Mekala | Day 4 auth service |
| DG-15 | Observability | **Python stdlib `logging` + request logging + a `/healthz` endpoint during B1. Metrics/APM tooling: DEFERRED to Day 55 (production readiness).** | Minimal, zero-extra-dependency observability for B1; richer metrics/APM is a production-readiness concern, recorded as pending. | Harshitha Mekala | Day 10 observability |
| DG-16 | Localization scope | **English-first; no i18n in V1. Confirmed from Overview §38.2 ("English is the launch language") / §19.4.** | Already specified by the source documents; this entry records confirmation from the source, not a new choice. | Harshitha Mekala | Day 2 |

## 3. Approval-Safety Reconfirmation (Day 1 exit criterion)

The following product guarantees are explicitly reconfirmed and bind all future development:

- **User approval before upload is non-negotiable.** No planned task may introduce autonomous
  publishing that bypasses approval (automatic-upload PRD).
- Approval is **in-app only**.
- **No approval → NO UPLOAD.**
- Approval is valid within the PRD's validity rule (expires 24 h before scheduled time);
  schedule/platform changes invalidate approval; approval always triggers a new approval cycle.
- Rejected posts return to **Draft**.
- Publishing is **per social entry / per platform** with independent status; transient failures
  retry (initial + max 3, waits 1/5/15 min); permanent failures require user intervention and a
  new approval.
- Zero unapproved uploads is a guardrail metric (Overview §35.5).

Any Day that would violate the above is not implementable without re-approval of this log.

## 4. Phase Scope Acceptance

The six-phase structure from the approved Development Roadmap and Development Plan is accepted as
the execution shape:

- Frontend Phase 1 / 2 / 3
- Backend Phase 1 / 2 / 3
- Sync points (Sync 1 Day 19, Sync 2 Day 35, Sync 3 Day 52)
- System & Acceptance (Days 53–54), Production Readiness (Day 55)

This log governs Days 2–18 (Phase 0 remainder through Sync 1). Later phases are governed by the
Development Plan and will not be implemented before their scheduled day or without explicit
instruction.

## 5. "No technology without a recorded decision" rule

Every technology introduced into the project must first appear as a recorded decision — either in
this log or in a later decision-log entry created by a future Day's gate work. Nothing is silently
adopted. As of Day 1, no dependencies have been installed and no framework has been scaffolded.

## 6. Deferred Gates (not blocking Phase 0–B1–F1)

These gates are recorded here so they are not forgotten; they are consumed by later phases.

| ID | Gate | Required By (Day) | Status |
| --- | ---- | ----------------- | ------ |
| DG-7 | AI provider(s) + provider-agnostic adapter contract | Day 20 (B2 orchestration) | PENDING — resolve before Day 20 |
| DG-8 | Async job/queue infrastructure | Day 20 | PENDING — resolve before Day 20 |
| DG-9 | Media storage/CDN + media pipeline technology | Day 36 (video) | PENDING — resolve before Day 36 |
| DG-10 | Officially supported social platforms (V1 list); scheduling/publishing scope | Day 38 (scheduler) | PENDING — resolve before Day 38 |
| DG-11 | Platform integration approach: official SDK/OAuth strategy | Day 39 (publishing core) | PENDING — resolve before Day 39 |
| DG-12 | Notification delivery channels (email/push/SMS/in-app) | Day 42 (notifications complete) | PENDING — also PRD open question |
| DG-13 | Edge policy: terminal handling of a never-approved scheduled entry | Day 40 (approval validity) | PENDING — also PRD open question |
| DG-14 | Edge policy: invalidation granularity on multi-platform change | Day 40 | PENDING — also PRD open question |
| DG-5 (deploy) | Hosting/deployment platform | Day 55 | PENDING — resolve before Day 55 |
| DG-15 (part) | Metrics/APM tooling | Day 55 | PENDING — resolve before Day 55 |

## 7. Sign-off

The decisions in Section 2 were selected and confirmed by the owner during the Day 1 decision
session (2026-08-28). This document, once committed, represents the signed decision log required by
the Development Plan Day 1 deliverable.

- Approver: **Harshitha Mekala** (GitHub: `akhithamekala18`)
- Date: **2026-08-28**
- Next required gate action: Day 20 (DG-7, DG-8).