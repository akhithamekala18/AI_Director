# AI Director — Sequential Development Plan

Planning-only document. No implementation.

## 1. Planning Basis

This plan is derived exclusively from the approved project documentation.

| Source | Role |
| ------ | ---- |
| `AI_Director_Project_Overview_v2.0.pdf` (source: `docs/ai_director_overview.md`) | Product requirements, invariants, guardrail metrics, acceptance criteria (section numbering below refers to this document) |
| `Development_Roadmap.md` (approved, located outside the repo) | Phase structure, development sequence, sync points, phased exit criteria |
| `docs/prd-automatic-upload.md` | Source of truth for the Automatic Video Uploading feature (approval, validity, retry, per-platform rules) |
| `CLAUDE.md` | Current repository reality and conventions (documentation-only workspace; no application code exists today) |

Priority order when interpreting requirements: Project Overview → Development Roadmap → Feature PRDs → CLAUDE.md.

Planning constraints observed:
- Phases are fixed and non-invented: Frontend Phase 1/2/3 and Backend Phase 1/2/3.
- Development sequence respects the roadmap: Backend precedes Frontend within each matched pair (Backend owns invariants and contracts), then the pair is integrated at a sync point.
- Sync points are: Sync 1 (B1+F1), Sync 2 (B2+F2), Sync 3 (B3+F3).
- Nothing planned bypasses user approval before upload — approval is a non-negotiable system guarantee.
- Planned functionality (Overview/Roadmap/PRDs) is never confused with current repository state (CLAUDE.md: no app code, no git repo, no declared stack).
- Every undefined technical decision is marked **DECISION REQUIRED** in Section 9 and placed on the day it must be resolved. Nothing is silently assumed.

## 2. Development Principles

1. **Two synchronized streams.** Frontend and Backend evolve in matched pairs (B1→F1→Sync1→B2→F2→Sync2→B3→F3→Sync3). Within each pair, Backend precedes Frontend because Backend owns invariants and frozen contracts.
2. **Contract-first.** Each phase begins by freezing its contract pack (API/type contracts, lifecycle state machines, RBAC matrix). Frontend never implements against an unfrozen contract.
3. **Approval safety is non-negotiable.** No task may introduce autonomous publishing. The publishing path must structurally require a valid user approval per social entry before upload. Zero unapproved uploads is a guardrail metric (§35.5).
4. **Invariants over features.** Feature delivery includes automated tests for the governing invariants (e.g., preview-before-schedule, approval-before-upload, no silent republish, fact-grounding, character identity preservation, scoped regeneration).
5. **Mocks at sync seams.** Synchronization verifies real integration; out-of-phase capabilities are mocked (Sync 1: AI engines, media, video, publishing, analytics. Sync 2: video assembly, preview, scheduler, publishing, analytics. Sync 3: no mocks — external platform sandboxes only).
6. **Progressive disclosure.** Frontend surfaces are reserved and progressively revealed; no placeholder UI ships as completed functionality.
7. **Least privilege.** All backend operations enforce server-side RBAC; the UI only mirrors it.
8. **Audit completeness.** Every state-mutating action records actor, time, and reason.
9. **No unsupported decisions.** Unspecified choices are surfaced as DECISION REQUIRED and are blocking on their assigned day.

## 3. Phase Overview

| Phase | Scope | Matched Stream | Key Content | Sync |
| ----- | ----- | -------------- | ----------- | ---- |
| Phase 0 — Project Foundation | Global | — | Decision gate resolution, repository/tooling foundation, CI | — |
| Backend Phase 1 | Core Platform | F1 | Auth, users/teams, roles & permissions, projects, settings foundation, encrypted credential store, audit, notification primitive, storage-protection foundation, observability | Sync 1 |
| Frontend Phase 1 | Foundation & Project Shell | B1 | Auth UI + session lifecycle, dashboard, project management, workspace shell (reserved surfaces), settings foundation, role-aware UI, notifications shell, audit-view | Sync 1 |
| Backend Phase 2 | AI Studio | F2 | AI orchestration + jobs, research engine (Gate 1), script generator (Gate 2), character library (Gate 3), scene builder (Gate 4), scene media generation, editing/regeneration engine | Sync 2 |
| Frontend Phase 2 | Creative Studio | B2 | Research review, script editor, character setup/reuse, scene timeline, scene media controls, editing workflow, approval UI (Gates 1–4), generation task UI | Sync 2 |
| Backend Phase 3 | Production, Distribution, Insight | F3 | Video generator, thumbnails, preview rendering, scheduler, publishing + approval (PRD), notifications complete, analytics, team/governance, settings complete | Sync 3 |
| Frontend Phase 3 | Production, Distribution, Insight | B3 | Video status, preview player, content calendar, publishing approval UI (PRD), publish history, notifications complete, analytics dashboards, settings complete, governance, audit reporting | Sync 3 |
| System & Acceptance | Whole product | — | Acceptance-example testing, guardrail metrics, guideline regression, security validation | — |
| Production Readiness | Whole product | — | Hardening, deployment, launch packaging | — |

## 4. Day-by-Day Development Plan

Legend: **DR** = departures are forbidden; a DECISION REQUIRED gate shown on a day must be resolved before that day's tasks start.

| Day | Phase | Area | Tasks | Dependencies | Deliverable | Validation / Exit Criteria |
| --- | ----- | ---- | ----- | ------------ | ----------- | -------------------------- |
| 1 | Phase 0 | Decision gates | Review and lock every **DECISION REQUIRED** item in Section 9 required for Phase 0–B1–F1; record choices and rationale in a decision log/ADR; confirm acceptance of phased scope | Approved Overview, Roadmap, PRD, CLAUDE.md | Signed decision log; no Phase-0/B1/F1 blocking gate remains open | Every applicable gate has a recorded choice + owner; approval safety is explicitly reconfirmed; no technology is used that lacks a recorded decision |
| 2 | Phase 0 | Repository & tooling foundation | Initialize repository per chosen tooling; establish workspace layout; install lint/format/test toolchains and CI pipelines; add `.env.example` convention and project conventions doc | Day 1 decision log | Building repo skeleton, CI green on empty baseline, conventions documented | `git status` clean baseline; CI pipeline passes lint/format/test on the empty skeleton; nothing is stubbed as implementation |
| 3 | Backend 1 | Contract pack & domain scaffolding | Define Phase-1 contract pack: identity/auth session contract, RBAC matrix (§29.3: Creator/Editor/Reviewer/Approver-Owner/Admin/Viewer), project lifecycle state machine (§20.1.1 Draft→…→Published/Archived), notification primitive contract; scaffold service boundaries | Days 1–2 | Frozen Phase-1 API/type contract pack (openAPI/types) + service boundary scaffolding | Contract pack review sign-off; state machine unit tests pass for every legal transition and reject illegal ones |
| 4 | Backend 1 | Authentication service | Registration, login, session management with expiry, MFA/SSO options surfaced (implementation per §29.2 options), team-membership scoping of access | Day 3 contract pack | Working identity service behind contract | §11.1/§19.1 auth acceptance: register→login→session works; expired session rejected; credentials never logged; cross-team access denied |
| 5 | Backend 1 | Roles & permissions | Server-side RBAC enforcement (least privilege), role gates on all endpoints; publish permission restricted to accountable roles | Day 4 | RBAC enforcement + matrix tests | §29.3 matrix test: Viewer cannot approve or view approval controls; Editor cannot publish; over-privileged requests return 403 |
| 6 | Backend 1 | Project service | Project CRUD with topic/platform/format; lifecycle transitions with invariants; duplicate; template; archive | Day 5 | Project service with enforced lifecycle | §20.1.1 states test: out-of-order transitions rejected; duplicate/template/archive behave per spec |
| 7 | Backend 1 | Settings foundation + credential store | Account/security settings foundations; encrypted credential store for platform credentials, secrets never logged | Day 6 | Settings API + encrypted credential store | Encryption at-rest test; no-secret log verification (grep-style guard test); platform credential round-trip works |
| 8 | Backend 1 | Audit service | Immutable audit records (actor, time, reason) on every mutation; retention controls | Day 7 | Audit service + completeness test | Mutation replay produces a complete, append-only audit trail; records cannot be altered |
| 9 | Backend 1 | Notification primitive | In-app notification primitive for status and approval-request events; notification model + event API | Day 8 | Notification primitive (status + approval-request) | Event tests: status update emits notification; approval-request carries artifact link; feeds Phase-3 completion |
| 10 | Backend 1 | Media/storage protection + observability | Signed, controlled media/storage access foundation; logging/monitoring/alerting hooks per §36.2 | Day 9 | Protected storage foundation + observability scaffolding | Access-control test: unauthorized media read rejected; observability smoke test emits logs/metrics |
| 11 | Backend 1 | B1 acceptance | Run Backend Phase 1 acceptance: register→login→manage projects surviving restart; cross-role denial; audit proof; expired-session handling; assert **no unapproved-upload endpoint exists** | Days 3–10 | Backend Phase 1 complete | All §4.1 exit criteria pass; B1 contract pack remains frozen; zero guardrail regressions |
| 12 | Frontend 1 | App shell + auth UI | F1 app shell: routing, session lifecycle UI, auth screens (register/login/logout/MFA option surface) wired to B1 contracts; role-aware navigation | Day 11 B1 + frozen B1 pack | F1 app shell + working auth flows | §3.1 auth-flow UI test: register/login/logout pass; session expiry returns to login; UI routes blocked without session |
| 13 | Frontend 1 | Dashboard | Project list with lifecycle state and next action derived from §20.1.1 state machine | Day 12 | Dashboard | Next-action is correct for every lifecycle state; archived projects absent; list reflects server state |
| 14 | Frontend 1 | Project management UI | Create project (topic/platform/format), metadata editing, duplicate, template, archive flows | Day 13 | Project CRUD UI | §3.1 project-management flow test: create→edit→duplicate→archive works and persists |
| 15 | Frontend 1 | Workspace shell | Stage-navigation shell with reserved surfaces: research, script, characters, scenes, video, preview, schedule (§20.1.2–§20.3.1); progressive disclosure | Day 14 | Workspace shell (reserved only) | All seven surfaces navigable and correctly reserved; no studio functionality present (mocks/seams only) |
| 16 | Frontend 1 | Settings foundation + role-aware UI | Account/security settings UI; 6-role-aware UI scaffolding mirroring §29.3 | Day 15 | Settings foundation UI + role scaffolding | Viewer/Editor can never see approval or publish controls; role switch reflects immediately |
| 17 | Frontend 1 | Notifications shell + audit view | Notifications center shell rendering status + approval-request (with artifact link); audit-view surface showing actor/time/reason | Day 16 | Notifications shell + audit surface | Approval-request notification renders with artifact link; audit view shows actor/time/reason |
| 18 | Frontend 1 | F1 acceptance | Run Frontend Phase 1 acceptance: "login → manage projects" vertical slice; responsive checks (desktop/laptop/tablet/mobile); accessibility; no console errors | Days 12–17 | Frontend Phase 1 complete | §3.1 exit criteria pass (auth flows, lifecycle states, role-aware UI, next action, reserved-only surfaces); responsive + accessibility checks pass |
| 19 | Sync 1 | Integration | Deploy B1+F1 together; verify vertical slice end-to-end; run guardrail tests (assert no auto-publish path exists); freeze Phase-1 contract pack; introduce mock seams for AI engines, media, video, publishing, analytics; refresh mocks on Frontend Phase-2/3 planning data | Days 11, 18 | Integrated Phase-1 product slice; Phase-1 contract pack frozen | Milestone M1 (Foundation) go/no-go; §3.1 vertical slice passes live; guardrail suite green; no open acceptance blockers |
| 20 | Backend 2 | AI orchestration + jobs | Provider-agnostic AI adapter contract; async job infrastructure with progress/resume/cancel/retry and cost tracking (§36.2, G-9) | Day 19 (frozen B1 pack) + **DR**: AI provider(s), queue | AI orchestration layer + job runner | Provider-swap test passes; job resume/cancel works; cost per job recorded |
| 21 | Backend 2 | Research Engine + Gate 1 | Research sourcing, cited summary, source list, gap/contradiction flags, approval state machine; G-1 fact-grounding enforcement | Day 20 | Research Engine + Gate 1 | Gate 1 test: no scripting before research approval; every claim maps to a cited source; contradiction surfaced |
| 22 | Backend 2 | Script Generation + Gate 2 | Script package generator (title/outline/script/narration/scenes/captions/hashtags); revision cycles; Gate 2 approval | Day 21 | Script Generator + Gate 2 | Script gate test: script revision depends on approved research; package fields complete per §20.1.3 |
| 23 | Backend 2 | Character Library + Gate 3 | Character detection, attributes (age/gender/appearance/clothing/accessories), stable IDs, versioning, cross-project reuse; G-5 identity preservation | Day 22 | Character Library + Gate 3 | Identity-preservation test: same character ID yields consistent attributes across projects; version change tracked |
| 24 | Backend 2 | Scene Builder + Gate 4 | Scene mapping, assignment, ordering, pacing, transitions; Gate 4 approval | Day 23 | Scene Builder + Gate 4 | Scene gate test: approved scenes map to assigned characters/visuals/narration; order/pacing validated |
| 25 | Backend 2 | Scene media generation | Per-scene visuals, voice-over, music, subtitles (§20.1.8–§20.1.10), scoped by approved scene package | Day 24 | Per-scene media pipeline | Each approved scene produces visual/voice/music/subtitle assets tied to scene ID |
| 26 | Backend 2 | Editing/regeneration engine | Scoped single-scene regeneration with deterministic blast radius; versioning and compare; G-4 enforcement | Day 25 | Regeneration engine (scene scope) | §44.2 test: regenerating scene S2 leaves S1/S3/S4 untouched; previous version compareable; ✓ G-4 |
| 27 | Backend 2 | B2 acceptance | Run Backend Phase 2 acceptance: concept → approved scene package; invariants G-1..G-8; retry/resume under injected failure | Days 20–26 | Backend Phase 2 complete | All §4.2 exit criteria pass; invariance tests green; no unapproved downstream generation |
| 28 | Frontend 2 | Research review surface | Research review UI: cited summary, source list, gaps/contradictions, approve/request-changes; Gate 1 UI | Day 27 B2 + frozen B2 contract | Research review UI | UI enforces research-before-scripting; approve/request-changes both persist correctly |
| 29 | Frontend 2 | Script package editor | Script package editor (title/outline/script/narration/scenes/captions/hashtags) with approve/edit/regenerate, revision list + compare; Gate 2 UI | Day 28 | Script editor + Gate 2 UI | Edit→regenerate→compare→approve cycle works; revisions visibly versioned |
| 30 | Frontend 2 | Character setup & library | Detected-character presentation, attribute form, appearance preview, save to library, reuse picker with version indicator; Gate 3 UI | Day 29 | Character setup + library UI | Character reuse renders consistent attributes/identity; version changes surfaced |
| 31 | Frontend 2 | Scene builder timeline | Scene timeline: map scenes, assign characters/visuals/narration, order/pacing, transitions, per-scene preview; Gate 4 UI | Day 30 | Scene builder + Gate 4 UI | Scene package editable at scene granularity; approval gates presented in-context |
| 32 | Frontend 2 | Scene media controls + editing workflow | Per-scene voice/music/captions, replace visuals, regenerate one scene, re-render voice/subs/music, compare versions | Day 31 | Scene media controls + regeneration UI | Single-scene regeneration via UI with other scenes untouched (✓ G-4 at UI layer) |
| 33 | Frontend 2 | Generation task UI + approval surfaces | Long-job UI (progress/resume/cancel); Gates 1–4 in-context approval with decisions/comments, escalation visibility, audit | Day 32 | Generation task UI + complete approval UI | Approval flows work; escalate/request-changes returns to editable state without data loss |
| 34 | Frontend 2 | F2 acceptance | Run Frontend Phase 2 acceptance via UI only: concept → approved scene package; all four gates; invariant enforcement; responsive; no console errors | Days 28–33 | Frontend Phase 2 complete | §3.2 exit criteria pass; invariant violations impossible via UI; accessibility passes |
| 35 | Sync 2 | Integration | Deploy B2+F2 together; verify "concept → approved scene package" end-to-end; guardrail/invariant regression; mock seams for video assembly, preview, scheduler, publishing, analytics; freeze Phase-2 contract pack | Days 27, 34 | Integrated Phase-2 slice; Phase-2 contract frozen | Milestone M2 (Creative Studio) go/no-go; vertical slice passes live; invariant suite green |
| 36 | Backend 3 | Video + thumbnail generation | Video generator: composite scenes/narration/captions/music (§20.1.7); per-platform aspect; per-scene re-render; thumbnail generator + variations (§20.1.11) | Day 35 + **DR**: media pipeline tech | Video + thumbnail renderers | Composite render test; per-scene re-render leaves other scenes intact; thumbnail set produced |
| 37 | Backend 3 | Preview rendering service | Platform-accurate preview renderer; mandatory preview-before-schedule invariant | Day 36 | Preview service | Invariant test: schedule is blocked until an approved preview exists for the entry's target |
| 38 | Backend 3 | Scheduler service | Per-platform schedule entries with explicit date/time (UTC + timezone normalization), calendar dataset API, reschedule/cancel, best-time guidance, reminders tied to production state | Day 37 + **DR**: platform set for scheduling | Scheduler service (per-entry) | Scheduling invariants test: per-entry normalized times; reschedule/cancel history audited; reminders fire only from valid states |
| 39 | Backend 3 | Publishing core (PRD entities) | PRD entities: ScheduledPost, ScheduledEntry, SocialAccount, Approval, UploadAttempt, PublishingAuditLog; per-entry granular approval records; in-app approval; upload only via official interfaces (§41.1); **no unapproved-upload path** | Day 38 + **DR**: social platform SDK/OAuth strategy | Publishing service (approval-gated) | Structural test: no endpoint uploads without a valid per-entry approval; per-platform independent status; official-interface usage only |
| 40 | Backend 3 | Approval validity & invalidation (PRD) | Approval 24h-before-scheduled-time validity; expiry blocks publishing and requires re-approval; schedule/platform change invalidates approval; rejection → DRAFT (can delete/edit/reschedule); approval bound to payload snapshot | Day 39 | Approval lifecycle logic | Expiry test: approval inside 24h window accepted, outside blocked; change-to-entry invalidates approval; rejection lands in DRAFT |
| 41 | Backend 3 | Retry + failure handling (PRD) | Transient-only retry: initial + max 3 (waits 1/5/15 min = max 4 attempts); permanent failures → explain/notify/user action/new approval; idempotent publish (at most one success per entry); per-platform partial-failure handling without false overall success | Day 40 | Retry + idempotency + multi-platform publishing | Retry-schedule test (1/5/15) passes; injected transient failure recovers; permanent failure surfaces for user; idempotency test yields at most one success; partial platform failure reported per-platform |
| 42 | Backend 3 | Notifications complete + settings complete | All notification types (§20.3.3, §27.4) incl. approval-request, reminder, publish outcome, failure; platform connections, publishing/notification preferences, default styles, security settings | Day 41 + **DR**: notification delivery channels | Complete notifications + settings backend | Notification dispatch tests for each type; settings persistence test; platform connection lifecycle works |
| 43 | Backend 3 | Analytics + team/governance | Published-performance tracking (views/engagement, by platform/topic) sourced from published events only; role-based workspaces, approval chains, client separation, audit reporting | Day 42 | Analytics + governance services | Boundary test: analytics never measures un-published content; governance test: Editor cannot approve/publish; audit reporting is exportable |
| 44 | Backend 3 | B3 acceptance | Run Backend Phase 3 acceptance: approved video → scheduled → approved per entry → published per platform → recorded → measured; invariants (preview-before-schedule, approval-before-upload, scoped re-render, no silent republish); guardrail metrics | Days 36–43 | Backend Phase 3 complete | All §4.3 exit criteria pass; guardrail metrics (zero unapproved uploads, zero unpreviewed schedules, no data loss) verified |
| 45 | Frontend 3 | Video status + preview UI | Video generation status/progress, thumbnail variation picker, full preview player, scene-by-scene navigation, per-platform format surfaces | Day 44 B3 + frozen B3 contract | Video status + preview player UI | Preview UI renders platform surfaces; video status reflects job state; playback works |
| 46 | Frontend 3 | Scheduler UI + content calendar | Per-platform schedule entries, calendar view, reschedule/cancel, best-time display, reminders surfaced | Day 45 | Scheduler UI + calendar | Schedule-before-preview blocked in UI; reschedule/cancel flow; calendar entry matches per-entry state |
| 47 | Frontend 3 | Publishing approval UI (PRD) | Per-entry payload summary + granular in-app approval per platform; 24h validity surfaced with countdown; invalidation notice on schedule/platform change; no-approval → no-upload enforced; rejected → Drafts list | Day 46 | Publishing approval UI | Granular approval: approving YouTube does not approve TikTok; expired approval cannot upload; rejection returns to Draft; invalidation notice shown on change |
| 48 | Frontend 3 | Publish history + notifications complete | History per entry: payload snapshot, approval, outcome, retries/cancellations; complete notifications center incl. approval-request, reminder, publish outcome, failure | Day 47 | History UI + complete notifications UI | History accuracy test; all notification types render; retry/cancel paths presented clearly |
| 49 | Frontend 3 | Analytics dashboards + settings complete | Engagement/views dashboards by platform/topic; settings screens complete: team, platform connections, publishing/notification preferences, default styles, security | Day 48 | Analytics + settings UIs | Analytics reflect published events only; settings CRUD persist; connection status visible |
| 50 | Frontend 3 | Governance + audit reporting UI | Role-based workspace views, approval chains, client-facing review surfaces, audit report viewing/export | Day 49 | Governance + audit UI | Role test: Editor cannot publish; audit UI shows actor/time/reason and is exportable |
| 51 | Frontend 3 | F3 acceptance | Run Frontend Phase 3 acceptance: approved package → published → measured; invariants (preview-before-schedule, per-entry approval, reschedule/cancel up to approval, history + analytics after publish, notification prefs, role restrictions); multi-platform partial-failure display and retry UI | Days 45–50 | Frontend Phase 3 complete | §3.3 exit criteria pass; per-platform failure shown independently; no console errors; accessibility passes |
| 52 | Sync 3 | Integration | Full real integration with **no mocks**; external platform sandboxes only for official platform interfaces; full-pipeline E2E; guardrail metrics regression; freeze Phase-3 contract pack | Days 44, 51 | Fully integrated product on sandboxes | Milestone M3 (Production/Distribution/Insight) go/no-go; E2E pipeline passes in sandbox; zero unapproved uploads across all runs |
| 53 | System & Acceptance | Acceptance testing | §44.2 acceptance examples; §35.5 guardrail metrics (zero unapproved uploads, zero unpreviewed schedules, zero data loss, zero unauthorized access); §10 rule guideline regression; §23.2 approval-gate audit; audit completeness | Day 52 | Signed acceptance report | All acceptance examples pass; guardrail metrics zero-violation; audit trail complete for every decision; M4 go/no-go |
| 54 | System & Acceptance | Security validation + hardening | Least-privilege penetration checks, credential store, sessions, webhook signing, no-secret verification, dependency/secret cleanup | Day 53 | Security validation report, findings closed | No blocking findings; secrets absent from repo; webhook/credential controls verified |
| 55 | Production readiness | Launch packaging | Deployment configuration, environment/secrets management, monitoring/alerting, runbooks, backup/retention, §34.2 launch checklist + certification | Day 54 | Deployment-ready product + launch checklist | M5 go/no-go; §34.2 exit criteria met; runbook drills pass |

## 5. Feature-to-Day Mapping

Every feature below comes from the Overview/Roadmap/PRD. No feature has been added that is not in those documents; none of these features is left unassigned.

| Feature | Source | Phase | BE Day | FE Day | Dependencies | Validation |
| ------- | ------ | ----- | ------ | ------ | ------------ | ---------- |
| Project Management (Draft→Published/Archived lifecycle) | §20.1.1 | B1/F1 | 6 | 13–14 | RBAC (5) | State machine + CRUD UI tests |
| Research Engine (facts, cited summary, gaps/contradictions) | §20.1.2 | B2/F2 | 21 | 28 | AI orchestration (20) | Gate 1 tests + research-review UI |
| Script Generator (title/outline/script/narration/scenes/captions/hashtags) | §20.1.3 | B2/F2 | 22 | 29 | Research (21) | Gate 2 tests + editor UI |
| Character Library + detection/attributes | §20.1.4 | B2/F2 | 23 | 30 | Script (22) | G-5 identity test + setup UI |
| Character Reuse (stable IDs, versions, cross-project) | §20.1.5 | B2/F2 | 23 | 30 | Character library (23) | Reuse consistency test + picker |
| Scene Builder (map/assign/order/pacing/transitions) | §20.1.6 | B2/F2 | 24 | 31 | Character (23) | Gate 4 tests + timeline UI |
| Video Generation (composite, per-platform aspect) | §20.1.7 | B3/F3 | 36 | 45 | Bonds: approved scene package (24–26) | Composite + re-render tests, status UI |
| Voice Generation (per scene) | §20.1.8 | B2/F2 | 25 | 32 | Scene Builder (24) | Per-scene asset test + controls UI |
| Music Generation (per scene) | §20.1.9 | B2/F2 | 25 | 32 | Scene Builder (24) | Per-scene asset test + controls UI |
| Subtitle Generation (per scene) | §20.1.10 | B2/F2 | 25 | 32 | Scene Builder (24) | Per-scene asset test + controls UI |
| Thumbnail Generation (variations) | §20.1.11 | B3/F3 | 36 | 45 | Video (36) | Variation set test + picker UI |
| Preview System (platform-accurate, preview-before-schedule) | §20.2.1 | B3/F3 | 37 | 45 | Video (36) | Invariant test + player UI |
| Editing / Regeneration Workflow (scoped, versioned, compare) | §20.2.2 | B2/F2 + B3/F3 | 26 (scene) / 36 (video re-render) | 32 (scene) / 45 (video) | Scene package (24) | §44.2 blast-radius test + edit UI |
| Scheduler (per-platform, calendar, reschedule/cancel, reminders) | §20.3.1 | B3/F3 | 38 | 46 | Preview (37) | Invariants + calendar UI |
| Publishing (official interfaces, approval-gated) | §20.3.2 | B3/F3 | 39–41 | 47 | Scheduler (38), Preview (37) | Structural no-unapproved-upload test |
| Automatic Upload (PRD: in-app approval, 24h validity, invalidation, retry, per-platform, rejection → Draft) | PRD §D1–D8 | B3/F3 | 39–41 | 47–48 | Scheduler (38), publishing core (39) | PRD acceptance: §D2/D5/D8 tests + approval UI |
| Notifications (status + approval-request; complete set) | §20.3.3, §27.4 | B1/F1 shell → B3/F3 complete | 9 → 42 | 17 → 48 | Auth (4–5) for scoping | Event tests + notifications UI |
| Analytics (published-only performance) | §20.4.1 | B3/F3 | 43 | 49 | Published events (41) | Boundary test + dashboards |
| Settings (account/security → complete) | §20.4.2 | B1/F1 foundation → B3/F3 complete | 7 → 42 | 16 → 49 | RBAC (5) | Settings CRUD + credential store tests |
| Roles, Teams & Governance (6 roles, approval chains, client separation) | §19.1, §29.3, §34.4 | B1/F1 + B3/F3 | 5 → 43 | 16 → 50 | Auth (4) | §29.3 matrix + governance UI tests |
| Audit (actor/time/reason; reporting) | §5.8, §34.4 | B1/F1 + B3/F3 | 8 → 43 | 17 → 50 | All administrative ops | Completeness + export tests |
| Video/Media Asset Protection + storage foundations | §29.6 | B1 foundation → B3 media | 10 | — | Project (6) | Access-control test |

## 6. Dependency Matrix

| Task / Phase | Depends On | Blocks | Reason |
| ------------ | ---------- | ------ | ------ |
| Decision gates (Day 1) | Approved docs | Phase 0 tooling (2), all phases | Unspecified choices cannot be implemented |
| Repository/tooling (Day 2) | Decisions (1) | All backend/frontend days | No build/test/CI baseline existing today (CLAUDE.md) |
| B1 contract pack (3) | Foundation (2) | B1 (4–10), F1 (12–18) | Contracts, RBAC matrix, lifecycle must exist before implementation |
| B1 auth/RBAC (4–5) | B1 contract (3) | B1 projects/settings/audit/notifications (6–10) | Every operation is role-gated |
| B1 project/settings/audit/notification/storage (6–10) | RBAC (5) | Sync 1 (19) | Completes B1 core platform |
| Sync 1 (19) | B1 (11), F1 (18) | B2 (20+) | B1+F1 must integrate before stream 2 begins |
| B2 AI orchestration + jobs (20) | Sync 1 (19), queue/provider decisions | Research/script/characters/scenes/media/editing (21–26) | AI features depend on the orchestration layer |
| B2 Gates chain (21→22→23→24) | Orchestration (20) | Scene media (25), editing (26) | Gate 1 before Gate 2 before Gate 3 before Gate 4 |
| Scene media + editing (25–26) | Scene builder (24) | B2 acceptance (27), F2 (28–33) | Media/regeneration are scene-scoped |
| F2 review surfaces (28–33) | B2 acceptance (27), frozen B2 pack | Sync 2 (35) | Frontend consumes B2 contracts |
| Sync 2 (35) | B2 (27), F2 (34) | B3 (36+) | Integrates stream 2 |
| Video/preview (36–37) | Sync 2 (35), media pipeline decisions | Scheduler (38) | Preview-before-schedule invariant |
| Scheduler (38) | Preview (37), platform decisions | Publishing core (39) | Entries require a schedulable, approved preview target |
| Publishing core (39) | Scheduler (38), platform SDK decisions | Approval validity (40), retry (41) | Approval-gated publish is the base |
| Approval validity/invalidation (40) | Publishing core (39) | Retry/failure (41) | Validity rules govern upload attempts |
| Retry + idempotency (41) | Approval rules (40) | Notifications complete (42) | Publish outcomes feed notifications |
| Notifications/settings complete (42) | Retry (41), channel decisions | Analytics/governance (43) | User must be reachable on outcomes |
| Analytics/governance (43) | Published events (41), notifications (42) | B3 acceptance (44) | Analytics is published-only; governance gates roles |
| F3 preview/schedule/approval/history/analytics/settings (45–50) | B3 (44), frozen B3 pack | Sync 3 (52) | Frontend consumes B3 contracts |
| Sync 3 (52) | B3 (44), F3 (51) | Acceptance (53) | Real, mock-free integration before acceptance |
| Acceptance + security (53–54) | Sync 3 (52) | Production readiness (55) | Gate on release quality |
| Production readiness (55) | Acceptance (53), security (54) | Product launch (M5) | Release-sequenced last |

## 7. Integration Points

Integration happens only at sync points, after the matched phase pair completes its own acceptance. All three sync points include: deploy both streams, run the vertical slice live, run invariant/guardrail regression, and freeze the phase contract pack.

| Sync | Day | Frontend Dependency | Backend Dependency | Integration Objective | Expected Result | Validation |
| ---- | --- | ------------------- | ------------------- | --------------------- | --------------- | ---------- |
| Sync 1 (M1 Foundation) | 19 | F1 accepted (18) | B1 accepted (11) | Authenticated user manages projects in a workspace shell; notifications/audit seams reachable | "Login → manage projects" works end-to-end; role-aware UI mirrors RBAC; only reserved surfaces exist | Vertical slice pass, guardrail suite (no auto-publish path), Phase-1 contract freeze |
| Sync 2 (M2 Creative Studio) | 35 | F2 accepted (34) | B2 accepted (27) | Concept becomes an approved scene package through the four gates; jobs visible in UI | "Concept → approved scene package" works live; gates enforced both ends | Invariant regression (G-1..G-8), Phase-2 contract freeze |
| Sync 3 (M3 Production/Distribution/Insight) | 52 | F3 accepted (51) | B3 accepted (44) | No mocks: approved package schedules, per-entry approval, publish to platform sandboxes, history + analytics | "Approved package → published → measured" works end-to-end on sandboxes | Full E2E pass, zero unapproved uploads, guardrail metrics, Phase-3 contract freeze |

## 8. Testing Strategy by Day

Testing is embedded per-day in Section 4 (each day lists its validation). The strategy by phase:

| Day Range | Test Focus |
| --------- | ---------- |
| 3–11 (B1) | Unit (state machines, RBAC matrix, auth/session, encryption, audit completeness); integration between identity/RBAC/projects; no unapproved-upload structural test |
| 12–18 (F1) | Frontend UI flows (auth, project CRUD, dashboard next-action, role-scoped visibility); responsive + accessibility; console-error checks |
| 19 (Sync 1) | End-to-end vertical slice; guardrail suite; contract-kind conformance (contract–implementation) |
| 20–27 (B2) | Invariant tests G-1..G-8 (fact-grounding, identity preservation, scoped regeneration/blast radius, gating); job infra failure-state tests (retry, resume, cancel); cost tracking |
| 28–34 (F2) | Gate-flow UI tests (approve/request-changes intact); regeneration blast-radius via UI; long-job progress/resume/cancel UI |
| 35 (Sync 2) | Invariant regression; vertical slice E2E; contract conformance |
| 36–44 (B3) | Approval-flow logic (validity window, invalidation on change, rejection → Draft); scheduling invariants; retry schedule (1/5/15, max 4 attempts) + injected transient/permanent failures; idempotency (at most one success); multi-platform partial-failure; preview-before-schedule; published-only analytics boundary |
| 45–51 (F3) | Approval-flow UI (per-platform granularity, validity surfaced, no-approval blocks upload, rejection return); scheduler/calendar; history accuracy; multi-platform failure display; role restrictions (Editor cannot publish); accessibility |
| 52 (Sync 3) | Real end-to-end on platform sandboxes; zero unapproved uploads instrumentation; full regression |
| 53–54 (Acceptance/Security) | §44.2 acceptance examples; §35.5 guardrail metrics; §10 guideline regression; §23.2 approval-gate audit; least-privilege penetration, secrets, sessions, webhooks |
| 55 (Production) | Deployment runbook, backup/restore drill, alerting smoke |

## 9. Decision Gates

The following decisions are genuinely unspecified in the approved documents. Each must be recorded before the day that consumes it (day in parentheses). Nothing in this plan assumes a choice.

| # | Gate | Needed By | Notes |
| - | ---- | --------- | ----- |
| DG-1 | Frontend framework | Day 2 (foundation) | Unspecified in Roadmap/CLAUDE.md |
| DG-2 | Backend framework/language | Day 2 | Unspecified |
| DG-3 | Database + ORM/data access | Day 3 (B1 contract) | Unspecified |
| DG-4 | Project tooling: monorepo layout, package manager, lint/format, test framework | Day 2 | Unspecified; none exists today |
| DG-5 | Hosting + CI/CD platform and deployment strategy | Day 2 (CI) / Day 55 (deploy) | Unspecified |
| DG-6 | Authentication implementation: in-house vs provider; MFA/SSO policy detail | Day 4 (auth) | §29.2 lists options only |
| DG-7 | AI provider(s) + provider-agnostic adapter contract | Day 20 (B2 orchestration) | §41.2/G-9; must allow provider swap |
| DG-8 | Asynchronous job/queue infrastructure | Day 20 | §36.2; drives progress/resume/retry |
| DG-9 | Media storage/CDN + media pipeline technology | Day 36 (video) | §29.6 |
| DG-10 | Officially supported social platforms (V1 platform list) + scheduling/publishing scope | Day 38 (scheduler) | §19.3/§3.3 leave V1 list open; also PRD "any officially supported platform" |
| DG-11 | Platform integration approach: official SDK/OAuth strategy, interface contracts, sandbox credentials | Day 39 (publishing core) | §41.1 |
| DG-12 | Notification delivery channels (email / push / SMS / in-app only) | Day 42 (notifications complete) | §19.3; also PRD open question (message delivery for pending approval) |
| DG-13 | Edge policy: terminal handling of a never-approved scheduled entry after its scheduled time | Day 40 (approval validity) | PRD open question (neither approved nor rejected at scheduled time) |
| DG-14 | Edge policy: invalidation granularity when a schedule/platform change affects multi-platform entries | Day 40 | PRD open question (all entries vs. only changed entries) |
| DG-15 | Observability stack (logging/metrics/alerting) | Day 10 (B1 observability) | §36.2 |
| DG-16 | Localization scope confirmation (English-first, §38.2) | Day 2 | Confirm no i18n in V1 |

Unresolved gates are blocking. A gate is considered resolved only when the decision is recorded in the decision log (Day 1 activity) with an owner.

## 10. Milestones

Milestone names follow the roadmap's own phases; no milestone functionality is invented.

| Milestone | Day | Completion Evidence |
| --------- | --- | ------------------- |
| M1 — Foundation | Day 19 (Sync 1) | B1+F1 integrated; "login → manage projects" live; no auto-publish path; Phase-1 contract frozen |
| M2 — Creative Studio | Day 35 (Sync 2) | B2+F2 integrated; "concept → approved scene package" live; invariants green; Phase-2 contract frozen |
| M3 — Production/Distribution/Insight | Day 52 (Sync 3) | B3+F3 integrated mock-free; publishes on sandboxes through per-entry approval; guardrails zero-violation; Phase-3 contract frozen |
| M4 — System & Acceptance | Day 54 | §44.2 acceptance + §35.5 guardrail metrics pass; security validation complete |
| M5 — Production Launch | Day 55 | §34.2 exit criteria met; deployment + runbook drills pass |

## 11. Phase Completion Gates

| Phase | Exit Condition (all must hold) |
| ----- | ------------------------------- |
| Backend 1 | §4.1 core-platform acceptance passes; contract pack frozen; no unapproved-upload endpoint exists; audience-restricted access verified |
| Frontend 1 | §3.1 shell acceptance passes; login → manage projects works; only reserved workspace surfaces; role-aware UI; responsive + accessible |
| Backend 2 | §4.2 acceptance passes; G-1..G-8 invariants green; scene-scoped regeneration proven (§44.2) |
| Frontend 2 | §3.2 studio acceptance passes via UI only; all four gates; invariant violations impossible in UI |
| Backend 3 | §4.3 acceptance passes; PRD D1–D8 behaviors proven; guardrail metrics zero-violation |
| Frontend 3 | §3.3 production/insight acceptance passes; per-entry approval and per-platform failure display complete; history/analytics accurate |
| System & Acceptance | §44.2 examples, §35.5 metrics, §10 regression, §23.2 audit all pass |
| Production Readiness | §34.2 launch exit criteria met |

## 12. Final Production Readiness Sequence

Applied in order on Days 53–55 after every invariant, acceptance, and security requirement is green:

1. Confirm zero outstanding blocking findings (acceptance + security).
2. Verify all DECISION REQUIRED gates have recorded decisions (DG-1..DG-16).
3. Perform least-privilege and no-secret sweep (credentials, tokens, keys, webhook secrets).
4. Run §35.5 guardrail metrics under load/injected failures (zero unapproved uploads, zero unpreviewed schedules, zero data loss, zero unauthorized access).
5. Deploy backend + frontend builds to the chosen hosting (DG-5) with environment/secrets management.
6. Enable monitoring and alerting (DG-15) and connect runbooks; verify alert routing.
7. Configure backup, retention, and restore drill per §5.8/§36.2.
8. Execute the §34.2 launch checklist (incl. team onboarding, certification, client-facing review surfaces ready).
9. Freeze final contract packs for all three phases; tag M5 release.
10. Record launch sign-off (M5 milestone) with owner.

The product does not proceed to the next readiness step while the current step has a failing exit condition.