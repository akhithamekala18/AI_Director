# AI DIRECTOR

## Development Roadmap

### AI-Powered Social Media Video Production Platform

**From a single topic to a published, human-approved social media video.**

| Field | Value |
| --- | --- |
| **Document Type** | Development Roadmap (Planning Only) |
| **Version** | 1.0 |
| **Date** | 2026-08-02 |
| **Source of Truth** | AI Director Project Overview v2.0 (July 31, 2026) |
| **Scope** | Frontend roadmap (3 phases), Backend roadmap (3 phases), integrated workflow, feature mapping, dependency matrix, milestones |
| **Classification** | Planning document — no implementation, no code, no schema, no APIs |

> [!IMPORTANT]
> This document is a **planning artifact only**. It contains no source code, no database schema, no API specifications, no folder structure, and no technology selection. Every requirement herein traces back to the authoritative Project Overview. Where the Project Overview is silent on a detail, that detail is explicitly marked as *unspecified* rather than assumed.

---

## Table of Contents

- [1. Executive Summary](#1-executive-summary)
- [2. Overall Development Strategy](#2-overall-development-strategy)
  - [2.1 Two Streams, One Product](#21-two-streams-one-product)
  - [2.2 Stream Separation Rules](#22-stream-separation-rules)
  - [2.3 Phase Alignment Rationale](#23-phase-alignment-rationale)
- [3. Frontend Roadmap](#3-frontend-roadmap)
  - [3.1 Phase 1 — Foundation and Project Shell](#31-phase-1--foundation-and-project-shell)
  - [3.2 Phase 2 — Creative Studio](#32-phase-2--creative-studio)
  - [3.3 Phase 3 — Production, Distribution and Insight](#33-phase-3--production-distribution-and-insight)
- [4. Backend Roadmap](#4-backend-roadmap)
  - [4.1 Phase 1 — Core Platform](#41-phase-1--core-platform)
  - [4.2 Phase 2 — AI Studio: Research to Scene Production](#42-phase-2--ai-studio-research-to-scene-production)
  - [4.3 Phase 3 — Production, Distribution and Insight](#43-phase-3--production-distribution-and-insight)
- [5. Integrated Development Workflow](#5-integrated-development-workflow)
  - [5.1 Development Sequence](#51-development-sequence)
  - [5.2 Integration Plan](#52-integration-plan)
- [6. Feature-to-Phase Mapping](#6-feature-to-phase-mapping)
  - [6.1 In-Scope Capabilities](#61-in-scope-capabilities)
  - [6.2 Cross-Cutting Features](#62-cross-cutting-features)
  - [6.3 Priority Matrix](#63-priority-matrix)
- [7. Dependency Matrix](#7-dependency-matrix)
  - [7.1 Phase-to-Phase Dependencies](#71-phase-to-phase-dependencies)
  - [7.2 Key Dependency Rules](#72-key-dependency-rules)
- [8. Milestones](#8-milestones)
- [9. Validation Checklist](#9-validation-checklist)
- [10. Conclusion](#10-conclusion)

---

## 1. Executive Summary

AI Director is an AI-powered social media video production platform built on one governing principle: **AI produces; humans decide**. The platform transforms a single topic into a complete, ready-to-publish social media video through a structured, human-approved workflow (Project Overview §3.1).

The Project Overview defines six non-negotiable product guarantees (§3.4, §12.4):

| # | Guarantee | Mechanism |
| --- | --- | --- |
| 1 | Verified research | The Research Engine gathers sourced information, presents a cited summary, and blocks scripting until research is approved. |
| 2 | Reviewed scripts | The Script Generator produces a complete package (title, outline, script, narration, scenes, captions, hashtags) that must be approved before production. |
| 3 | Reusable characters | The Character Library detects, defines, and persists characters under stable IDs for visual consistency across an entire catalog. |
| 4 | Controllable scenes | The Scene Builder and editing workflow operate at scene granularity, so only what changes is regenerated. |
| 5 | Mandatory preview | A video cannot be scheduled until it has been previewed on a platform-accurate surface. |
| 6 | Approval before upload | Every scheduled upload requires explicit, recorded human approval; silence never publishes. |

These guarantees are enforced through **six approval gates** (§23.2): Research, Script, Character, Scene, Video, and Publishing. No gate may be bypassed by any role (§41.1, G-3).

The development effort splits into **two independent but coordinated workstreams**:

| Stream | Responsibility (per Project Overview) |
| --- | --- |
| **Frontend** | All screens and workflows the user touches: dashboard, project workspace, research review, script editing, character setup, scene builder, media/video status, preview, scheduler, publishing approval, notifications, analytics, settings, team governance. |
| **Backend** | Identity, roles, projects, audit, the AI engines (research, script, character, scene), media generation jobs, video assembly, scheduling, publishing, notifications, analytics, and all non-negotiable guardrails. |

Each stream is split into exactly **three sequential phases**, aligned pair-wise (B1↔F1, B2↔F2, B3↔F3), with a synchronization point after each aligned pair. This document defines the phases, the integrated workflow, every feature's assignment, the dependency matrix, and the milestones.

**Items the Project Overview leaves open (recorded, not assumed):**

- Numeric targets for "predictable service times," "median time-to-video," and "cost per video" are defined only as target directions (§16.3, §35) — the SRS must set the numbers.
- The specific set of target platforms, AI providers, and notification delivery channels are named generically ("official platform publishing interfaces," "provider-agnostic," "notifications") — the SRS must enumerate them (§19.3, §41.2).

---

## 2. Overall Development Strategy

### 2.1 Two Streams, One Product

The Frontend and Backend are planned and built as separate workstreams, but they are not independent in behavior — the Project Overview's pipeline is a single integrated state machine (§22.4, §41.2: "Research → script → production → publish order is a product invariant"). Their relationship:

```
   FRONTEND  (interaction layer)                 BACKEND  (logic + engines)
   ┌──────────────────────────────────┐          ┌──────────────────────────────────────┐
   │ Screens & workflows for every    │  <─────► │ Identity, roles, projects, audit      │
   │ stage + approval gate            │ contract │ AI engines, media jobs, publishing,   │
   │ (§20, §21, §23)                  │   seam   │ analytics; invariant enforcement      │
   └──────────────────────────────────┘          └──────────────────────────────────────┘
        │  consumes frozen contracts only                │
        └───────────── Synchronization points (Sync 1–3) ─────────────┘
```

- **How they interact:** the Frontend renders artifacts and captures human decisions (approve / request changes / reject / edit); the Backend produces artifacts, owns the pipeline state machine (§22.4), and enforces every invariant (no writing before research approval, no scheduling before preview, no publishing without approval — §22.3, §41.1).
- **Dependencies:** every Frontend phase depends on the *contracts* of the matching Backend phase, not on its implementation. Backend work never depends on Frontend.
- **Synchronization points:** after each aligned pair, both streams are deployed together and the vertical slice for that phase is verified (see Section 5).

### 2.2 Stream Separation Rules

Derived from the Project Overview:

- The Frontend may never be the authority on any rule. All gating, invariants, and audit are Backend-owned (§5.8, §23.2, §29.7).
- The Backend may never present a screen. Approval "context," "evidence," and "change highlights" are presentation concerns of the Frontend (§5.5, §23.4, §28.2).
- The two streams join only at the frozen contract seam and only at synchronization points.

### 2.3 Phase Alignment Rationale

| Phase pair | Product scope covered | PDF basis |
| --- | --- | --- |
| B1 + F1 | Identity, project management, dashboard, settings foundation, role scaffolding, notification center shell | §20.1.1, §20.4.2, §29 |
| B2 + F2 | Research → Script → Characters → Scenes, gates 1–4, scene-level editing/regeneration | §20.1.2–20.1.6, §22.2, §23.2, §25, §26 |
| B3 + F3 | Video assembly, preview, scheduling, publishing, notifications, analytics, team governance | §20.1.7–20.4.2, §27, §30.1, §34.4 |

---

## 3. Frontend Roadmap

**Frontend rationale:** the Project Overview's roadmap priorities are (1) core production value, (2) consistency and control, (3) team and governance (§34.1). The Frontend phases follow the same order. The order matters because each later screen renders artifacts that the earlier phase established a home for (Progressive Disclosure, §5.4).

---

### 3.1 Phase 1 — Foundation and Project Shell

**Why this phase exists:** every artifact and workflow in the Project Overview lives inside a *project* with a lifecycle and a dashboard that shows "every video, its status, and its next required action" (§20.1.1). Nothing else can be built until this container exists. **Why its order matters:** identity and project state are prerequisites for every later stage; building screens before the container exists would create rework.

**Objective**

Provide the product's home: authentication, dashboard, project management, the project workspace container, settings foundation, role-aware UI, and a notifications center shell — so every later creative stage has a place to live (§20.1.1, §20.4.2, §29).

**Scope**

- Sign-in / sign-up / session UI, with MFA and SSO surfaced as options (§29.2: "secure credentials or single sign-on").
- Dashboard: project list with lifecycle state (Draft → Researching → Research Approved → Scripting → Script Approved → Producing → Video Approved → Scheduled → Published / Archived, §20.1.1) and the next required action.
- Project management UI: create project (topic, platform target, format — §21 stage 1); metadata; duplicate and template projects; archive (§20.1.1).
- Project workspace shell: stage-navigation container for the pipeline stages (research, script, characters, scenes, video, preview, schedule) rendered as reserved surfaces (§5.4).
- Settings foundation: account and security settings (§20.4.2, partial).
- Role-aware UI scaffolding for Creator, Editor, Reviewer, Approver/Owner, Admin, Viewer (§17.4, §29.3).
- Notifications center shell showing status and approval-request notifications (§20.3.3).

**User experience goals**

- Status-first: the dashboard always reveals the next required action (§20.1.1).
- The human is never a spectator (§5.1): every screen positions the user as decision-maker.
- Progressive disclosure: complexity appears only when reached for (§5.4).

**Deliverables**

- Routable application shell with role-aware navigation.
- Auth screens and session lifecycle.
- Dashboard + project CRUD + lifecycle-state display + duplicate/template/archive flows.
- Project workspace container with reserved stage surfaces.
- Account/security settings screens.
- Notifications center shell with approval-request rendering.
- Audit-view surface that reveals "actor, time, reason" (§5.8).

**Dependencies**

- Contracts from Backend Phase 1 (identity, roles, projects, settings, audit, notifications) must be frozen.
- Design/brand direction consistent with the §5 design principles.

**Acceptance criteria**

- A new user registers, logs in, creates a project with topic/platform/format, and sees its lifecycle state and next action.
- Duplicate and template creation work; archive removes a project from the active dashboard.
- The UI reflects the viewer's role (e.g., a Viewer cannot see approval controls — §29.3).
- Notifications center renders an approval request with a link to the artifact (§23.4).
- Audit records are visible for project mutations (§5.8).

**Risks**

- Role-model churn (§29.3) → mitigation: role matrix frozen in B1 contracts before F1 UI is built.
- Contract drift on project lifecycle states → mitigation: state machine owned by Backend; F1 renders states only (§22.4).
- Scope creep into studio screens → mitigation: stage surfaces are reserved, not built, in this phase.

**Completion checklist**

- [ ] All auth flows pass scripted tests.
- [ ] Project lifecycle states render correctly from Backend data.
- [ ] Role-aware UI verified against the §29.3 matrix.
- [ ] Dashboard "next action" field proven.
- [ ] No studio surfaces implemented (only reserved).

**Exit criteria**

A user can authenticate and manage projects through their lifecycle with a correct next-action dashboard; role restrictions are visibly enforced; audit is visible. Product state: *"Login → manage projects"*.

**What should NOT be started yet**

Research review surface, script editor, character setup, scene builder, video/preview, scheduler, publishing approval, analytics dashboards. (These are F2/F3; the gate order forbids reaching them earlier — §22.1, §23.2.)

---

### 3.2 Phase 2 — Creative Studio

**Why this phase exists:** this is the heart of the product — "AI produces; humans decide" (§3.1) is experienced here as the four creative gates: research, script, character, scene (§23.2). **Why its order matters:** the studio is the largest surface in the product; building it after the container (F1) and after the Backend engines (B2) lets every screen target real, working pipelines rather than guesses.

**Objective**

Provide every screen a user needs to move a project from Research through Scene Production: research review, script review/editing, character setup and reuse, scene building, and the scene-level editing workflow — with approval surfaces for gates 1–4 (§23.2).

**Scope**

- **Research review surface:** cited summary with source list, contradiction flags, gaps surfaced; approve / request changes (§20.1.2, §28.2).
- **Script package editor:** working title, outline, script, narration, scene decomposition, captions, on-screen text, hashtags; approve / edit / regenerate (§20.1.3, §21 stages 4–5).
- **Character setup:** detected-character presentation, attribute definition form (age, gender, appearance, clothing, accessories — §20.1.4), appearance preview, save to library, reuse selection and version indicator (§20.1.4–20.1.5, §25).
- **Scene builder:** map scenes from script; assign characters, visuals, narration per scene; set order and pacing; configure transitions; per-scene preview (§20.1.6).
- **Scene media controls:** per-scene voice characteristics, per-scene music mood/mixing, subtitle/caption styling (§20.1.8–20.1.10, produced during scene production — §21 stage 7).
- **Editing workflow:** edit script text, change scene order, replace scene visuals, regenerate an individual scene, re-render voice/subtitles/music for a scene, compare versions (§20.2.2, §26).
- **Approval UI for gates 1–4:** in-context review (script in editor, scenes in builder), decision actions with comments, escalation visibility, audit record (§23.4).
- **Generation task UI:** progress visibility, resume/cancel for long-running jobs (§36.2).

**User experience goals**

- Show the evidence: sources beside claims, change highlights beside reviews (§5.2, §5.5).
- Surgical change by default: editing one scene never implies re-rendering others (§5.3, §26).
- Guidance over gatekeeping: approval surfaces explain what is asked, what changed, and the consequence of approval (§5.5).
- Fail loud, never silent: generation failures show status and retry paths (§5.7).

**Deliverables**

- Research review + approval workflow UI.
- Full script package editor with revision cycles and compare.
- Character gallery, definition form, library, reuse picker, versioning UI.
- Scene builder timeline with per-scene assignment and preview.
- Scene-level editing and regeneration controls (visual, voice, captions, music).
- Approval surfaces for gates 1–4 with comments and audit.
- Task/progress panel for generation jobs.

**Dependencies**

- Backend Phase 2 contracts (research, script, character, scene engines; regeneration; task status) frozen.
- F1 shell and project workspace available for mounting.

**Acceptance criteria**

- A project goes from concept to an approved scene package using only the UI, passing gates 1–4 (§21, §23.2).
- Research must be approved before the script surface becomes writable (workflow invariant, §22.3).
- Changing one scene regenerates only that scene; other scenes remain untouched (§44.2 acceptance example).
- A library character renders with identical attributes in a new project (§44.2).
- Any request-changes decision returns the artifact to an editable state without data loss (§23.5, §22.2).
- Generation failures surface with status and retry; nothing is left ambiguous (§5.7).

**Risks**

- Approval fatigue → mitigation: guidance-over-gatekeeping surfaces and fast, clear reviews (§16 assumption 16).
- Regeneration scope confusion → mitigation: explicit "what will change" summary before regeneration (§26.4).
- Version/diff complexity → mitigation: compare at structural level (script sections, scene cards), consistent with §26.
- Evidence overload → mitigation: progressive disclosure layers evidence by depth (§5.4).

**Completion checklist**

- [ ] All four creative gates implemented and passing scripted flows.
- [ ] Research-before-scripting invariant visible and enforced from UI.
- [ ] Single-scene regeneration demo passes (scene 2 changed, scenes 1/3/4 untouched).
- [ ] Character reuse demo passes with identical attributes.
- [ ] Autosave / edit / compare / revision cycles verified.

**Exit criteria**

A creator can produce, review, and approve an entire scene package (research → script → characters → scenes) with evidence at every gate. Product state: *"Concept → approved scene package"*.

**What should NOT be started yet**

Video assembly/composite UI, thumbnail UI, full preview player, scheduler/calendar, publishing approval, analytics dashboards, team governance surfaces. (§20.1.7, §20.1.11, §20.2.1, §20.3.x, §20.4.1 — all assigned to F3.)

---

### 3.3 Phase 3 — Production, Distribution and Insight

**Why this phase exists:** completes the product surface per the publishing lifecycle (§27) and closes the loop with analytics (§20.4.1). **Why its order matters:** these screens consume artifacts that only exist after video assembly and publishing events — building them before B3 would mean building against empty states.

**Objective**

Provide the surfaces for the back half of the pipeline: media/video generation status, the mandatory preview, scheduling, per-entry publishing approval, publish history, complete notifications, analytics, completed settings, and team governance (§20.1.7–20.4.2, §27, §34.4).

**Scope**

- **Media/Video generation status UI:** video generator progress (composite), thumbnail generation and variations (§20.1.7, §20.1.11).
- **Preview system UI:** full-video playback, scene-by-scene navigation, platform-format preview — "what I scheduled is what I reviewed" (§20.2.1).
- **Scheduler UI:** per-platform schedule entries with individual dates/times, content calendar view, reschedule, cancel, best-time guidance (§20.3.1, §27.3).
- **Publishing approval UI:** full payload summary per platform (platform, title, video, thumbnail, captions, scheduled time); granular, explicit, recorded confirmation — approving one platform does not approve another (§27.5).
- **Publish history UI:** publication entry, approval record, payload snapshot, upload outcome (§27.7).
- **Notifications center (complete):** status, approval-request, scheduling/publish reminders, publish success, team assignment (§20.3.3, §27.4).
- **Analytics dashboards:** views and engagement, comparison by platform and topic, relationship to production choices (§20.4.1).
- **Settings completion:** team and role management, platform connections, publishing preferences, notification preferences, default styles (voice, captions, music), security (§20.4.2).
- **Team governance surfaces:** role-based workspaces, approval chains, client-facing review, audit reporting (§34.4, §30.1).

**User experience goals**

- Trust moments: research review, script review, character approval, video preview, publishing approval, history — each shows exactly what will happen (§28.2).
- Approval clarity at the final gate: a complete, per-entry summary before confirm (§27.5).
- Predictability: gates, regeneration scope, and publishing rules never surprise (§28.1).

**Deliverables**

- Preview player with platform-format surfaces.
- Content calendar and schedule-entry management UI.
- Per-platform publishing approval flow with payload summary.
- Publish history and status views with retry/cancel paths.
- Notifications center with all notification types (§20.3.3).
- Analytics dashboards (views, engagement, platform/topic comparison).
- Completed settings screens (team, platform, preferences, defaults, security).
- Team governance and audit-reporting UI.

**Dependencies**

- Backend Phase 3 contracts (video assembly, preview, scheduler, publisher, notifications, analytics, teams) frozen.
- F2 approval contract (publishing originates from approved, previewed packages).

**Acceptance criteria**

- A video cannot be scheduled through the UI unless it has been previewed (§20.2.1, §27 principle 1).
- Each platform entry requires its own explicit confirmation; approving one platform does not approve another (§27.5).
- Scheduled entries can be rescheduled and cancelled up to the approval point (§27.3).
- After publishing, history and analytics are visible for the published entry (§27.7, §20.4.1).
- Notification preferences work; pending-approval reminders surface (§27.4).
- Role restrictions render correctly for team governance (Editor cannot approve publishing — §29.3).

**Risks**

- Preview fidelity vs. published output → mitigation: platform-accurate preview surface defined in B3 contract (§20.2.1).
- Scheduler timezone/format ambiguity → mitigation: schedule data normalized in Backend; UI displays explicit per-entry times (§27.3).
- Analytics scope creep → mitigation: dashboard fixed to the Project Overview's metrics (views, engagement, by platform/topic — §20.4.1).
- Governance complexity → mitigation: team governance phased to §34.4 capabilities only.

**Completion checklist**

- [ ] Preview-before-schedule rule verified from UI.
- [ ] Per-entry publishing approval verified (granular, explicit, recorded).
- [ ] Publish history shows payload snapshot and outcome.
- [ ] All notification types demonstrable.
- [ ] Analytics reflect published events in verification data.
- [ ] Team governance flows pass against §29.3.

**Exit criteria**

A creator can schedule, approve, publish, record, and measure a complete video with mandatory preview and per-entry approval. Product state: *"Approved package → published → measured"*.

**What should NOT be started yet**

Anything the Project Overview explicitly marks out of scope (§19.2) or future (§34.5): live streaming, full non-linear editing suite, native mobile capture, engagement/comment tools, ad buying, stock/marketplace, influencer marketplace, messaging, offline desktop editing, multi-language, marketplace.

---

## 4. Backend Roadmap

**Backend rationale:** the Project Overview's constraints make the Backend the sole owner of rules and invariants (§41.1: approval gates may not be bypassed by any role; preview precedes scheduling; the research→script→production→publish order is a product invariant). Each Backend phase exists to enforce the guarantees that the corresponding Frontend phase renders.

---

### 4.1 Phase 1 — Core Platform

**Objective**

Provide identity, roles and permissions, project management, settings, audit, encrypted credential storage, and the notification primitive — the substrate every AI engine and publishing action later depends on (§29, §20.1.1, §20.4.2).

**Scope**

- Authentication service: registration, login, session management with expiry, MFA and SSO as options (§29.2).
- Users and teams: membership scoping to a user's teams (§29.2).
- Role & permission service: Creator, Editor, Reviewer, Approver/Owner, Admin, Viewer with least privilege and server-side enforcement (§29.1, §29.3).
- Project service: create/organize/track projects; topic, platform target, format; lifecycle state machine (Draft → … → Published/Archived, §20.1.1); duplicate and template projects; archive.
- Settings service: account, team, platform connection, publishing and notification preferences, default styles, security (§20.4.2).
- Audit service: immutable record of every state/artifact/publication change with actor, time, reason (§5.8, G-7).
- Notification service (in-app primitive): status and approval-request events (§20.3.3).
- Encrypted credential store for platform publishing credentials; never logged (§29.4).
- Media/storage protection foundation: access control and signed delivery readiness (§29.6).
- Observability: logging and monitoring aligned to §36.2 ("clear status," "progress visibility," "retry").

**Business logic**

- Project lifecycle enforcement: no stage may be entered out of order (invariant, §41.2).
- Role enforcement: publishing approval restricted to accountable roles; a Viewer can never see an approval action (§29.3).
- Audit completeness: every mutating operation is recorded (§5.8).
- Structural publishing safety: no automated path to upload exists; uploading requires explicit approval action (§9.2 "human agency," §29.7).

**Dependencies**

- Identity and security policy decisions (credential vs. SSO modes, session lifetime, MFA triggers) — the Project Overview specifies both options exist but not the exact policy (§29.2).
- Audit and retention policy for §29.5 (retention control) and §36 (legal data protection).

**Acceptance criteria**

- A user can register, log in, and manage projects through their lifecycle; state persists across restart.
- Cross-role access is denied server-side; a Viewer cannot trigger approval (§29.3).
- Every mutation appears in audit with actor, time, result (§5.8).
- Expired sessions are rejected; credentials are never logged (§29.4).
- No endpoint exists that publishes without an approval record (§29.7).

**Risks**

- Security misconfiguration → mitigation: least privilege + defense in depth + audit (§29.1).
- Role-model drift → mitigation: RBAC matrix frozen before F1 UI.
- Audit/storage growth → mitigation: retention control and managed storage tiers (§36.2).

**Completion checklist**

- [ ] Auth, roles, projects, settings, audit, notification primitive pass acceptance tests.
- [ ] Lifecycle state machine tested for all §20.1.1 states.
- [ ] RBAC verified against §29.3 matrix.
- [ ] Publishing-safety structural test passes (no unapproved-upload path exists).
- [ ] Credential store encryption and no-log verified.

**Exit criteria**

Authenticated, role-enforced, audited project management is production-grade, with the job/storage substrate in place for the AI engines. Product state: *"Authenticate → manage projects"*. Unlocks F1 and B2.

---

### 4.2 Phase 2 — AI Studio: Research to Scene Production

**Objective**

Deliver the AI engines that produce and govern the creative artifacts — research, script, characters, scenes, scene-level media — plus the orchestration layer and the gate state machines for gates 1–4, all provider-agnostic (§24, §20.1.2–20.1.6, §23.2).

**Scope**

- Research Engine: gather from trustworthy sources, summarize with citations, surface source list, flag gaps and contradictions, present summary for approval (§20.1.2).
- Script Generator: working title, outline and structure, full script with narration, scene decomposition, captions and on-screen text, platform hashtags, revision cycles (§20.1.3).
- Character Library engine: character detection from scripts, attribute definition (age, gender, appearance, clothing, accessories — §20.1.4), stable IDs, appearance rendering, versioning, cross-project reuse (§20.1.4–20.1.5, §25).
- Scene Builder engine: scene mapping from script, assignment of characters/visuals/narration per scene, ordering, pacing, transitions (§20.1.6).
- Scene-level media generation: scene visuals, per-scene voice-over, per-scene music, per-scene subtitles (§21 stage 7, §22.1 "scene media").
- Editing / regeneration engine: scoped, scene-level regeneration; deterministic blast radius; versioning and compare (§20.2.2, §26).
- AI orchestration layer: provider-agnostic model adapter so "model selection does not change workflow" (§24.3, §41.2); prompt/governance layer implementing the §10 guidelines; asynchronous job infrastructure with progress, resume, retry, and clear status (§36.2).
- Gate services 1–4 (Research, Script, Character, Scene) as explicit, unbypassable state machines (§23.2).

**Business logic**

- **Fact-grounding invariant (G-1):** no writing stage begins until approved research exists (§10.2, §22.3).
- **Identity preservation (G-5):** characters render from stored attributes by ID; no generation step alters identity without a recorded change (§25.6).
- **Deterministic scene scope (G-4):** regeneration covers only the changed scene unless full regeneration is explicitly requested (§26, §10.2).
- **Approval gating (G-3):** gates 1–4 may not be bypassed by any role (§10.2, §41.1).
- **Source transparency (G-2):** contradictions surfaced, not silently resolved (§10.2).
- **Revision semantics:** revisions link to a parent version; only one current version exists (§20.1.3, §25.5).
- **Content constraints (G-8, §9.2):** harm/deception prevention enforced at generation boundaries.

**Dependencies**

- B1 exits: identity, roles, project lifecycle, audit, job substrate, storage readiness.
- Prompt governance and content-policy decisions (§10, §9.4).

**Acceptance criteria**

- A concept yields an approved scene package passing gates 1–4 end-to-end (§21).
- No script is generated before research is approved (invariant test, §44.2).
- Changing one scene regenerates that scene and no other (§44.2).
- A reused character renders identically in a new project (§44.2, §25.4).
- A generation failure retries with clear status and resumes from the failed step (§36.2).
- A rejected gate returns the artifact to editable state; rejections are audited (§23.2, §23.5).
- Provider swap does not change the workflow (§41.2).

**Risks**

- Factual inaccuracy / hallucinated sources (§36.4) → mitigation: research gate, sourced summaries, source verification.
- Character drift (§36.4) → mitigation: stable IDs + attribute-based rendering.
- Generation cost overrun (§36.2) → mitigation: provider-agnostic layer, cost monitoring, per-project limits (G-9).
- Provider instability (§41.2) → mitigation: no single provider required; adapter isolation.

**Completion checklist**

- [ ] All four engines and gate services operational.
- [ ] Fact-grounding, identity, scoped-regeneration, and gating invariants tested.
- [ ] Retry/resume/cancel verified under injected failure.
- [ ] Provider-agnostic adapter verified.
- [ ] Scene-media generation (visual, VO, music, subs) verified per scene.

**Exit criteria**

The pipeline from research through scene production completes with gates 1–4 enforced, scene-level media produced, and regeneration scoped correctly. Product state: *"Concept → approved scene package"*. Unlocks F2 and B3.

---

### 4.3 Phase 3 — Production, Distribution and Insight

**Objective**

Complete the pipeline: video assembly, thumbnail generation, platform-accurate preview rendering, scheduling, publishing with approval-gate enforcement, full notifications, analytics, team governance, and completed settings — all under the guardrail metrics (§20.1.7–20.4.2, §27, §30.1, §34.4, §35.5).

**Scope**

- Video Generator: composite scene visuals, narration, captions, music; maintain resolution/aspect per platform; per-scene re-render (§20.1.7).
- Thumbnail Generator: from key scene visuals, with title text and variations, at platform dimensions (§20.1.11).
- Preview rendering service: platform-accurate surface for the mandatory preview (§20.2.1).
- Scheduler service: per-platform entries, explicit dates/times, content calendar, reschedule, cancel, best-time guidance, reminders tied to production state (§20.3.1, §27.3–27.4).
- Publishing service: uploads through official platform publishing interfaces only; per-entry payload preparation and verification; explicit approval record required before upload; retry handling that never silently republishes; publish history (entry, approval, payload snapshot, outcome) (§20.3.2, §27.5–27.7, §29.7).
- Notifications service (complete): status, approval-request, scheduling/publish reminders, publish-success, team assignment (§20.3.3).
- Analytics service: track published performance (views, engagement), compare by platform and topic, relate performance to production choices, feed insights into topic selection (§20.4.1).
- Team/governance backend: role-based workspaces, approval chains, client separation, audit reporting (§34.4, §30.1, §29.3).
- Settings completion: platform connections, publishing/notification preferences, default styles, security (§20.4.2).

**Business logic**

- **Preview-before-scheduling invariant:** scheduling is impossible for unpreviewed videos (§41.1, §22.3).
- **Approval-before-upload invariant:** every upload requires an explicit per-entry approval record (§27.5, §44.2).
- **Publishing lifecycle (§27.2):** video approved → preview → schedule → reminder → approval request → upload → success → history; rejection → unschedule/revise.
- **Scoped re-render:** a changed scene re-renders only that scene (§26, §20.1.7).
- **Publishing via official interfaces only; policy compliance (G-8, §36.5):** platform interface stability monitored.
- **Analytics boundary:** tracks performance only for published videos; no engagement/comment tooling (§19.2).

**Dependencies**

- B2 exits: approved scene package contract, gate machines, task substrate.
- Channel integration policy and notification deliverability decisions (the Project Overview requires official publishing interfaces §41.1 but does not enumerate channels).
- Sandbox/test environments of target platforms for regression (derived from §29.7 "retry handling that never silently republishes"; the Project Overview does not name them).

**Acceptance criteria**

- A scheduled run publishes per platform entry only after its own explicit approval record (§44.2).
- An unpreviewed video cannot be scheduled (§44.2).
- A failed upload surfaces a clear error with retry and never silently republishes (§27.6, §29.7).
- Changing one scene re-renders that scene and no other (§44.2).
- Publish history records entry, approver, payload snapshot, and outcome (§27.7).
- Analytics reflect actual published performance after publish (§20.4.1).
- Guardrail metrics: zero unapproved uploads, zero unpreviewed schedules (§35.5).

**Risks**

- Platform interface instability / policy changes (§36.2, §36.5) → mitigation: official interfaces only, failure surfacing, retry with backoff, policy monitoring.
- Credential revocation (§36.5) → mitigation: re-authentication flows, clear status, no silent failures.
- Double-publish on retry → mitigation: idempotent publish with recorded outcome (§29.7).
- Media storage growth (§36.2) → mitigation: managed storage tiers, cleanup policy.
- Analytics volume → mitigation: aggregation aligned to §20.4.1 scope.

**Completion checklist**

- [ ] Preview-before-schedule and approval-before-upload invariants pass tests.
- [ ] Per-entry granular approval verified (one platform's approval does not approve another).
- [ ] Retry never republishes silently.
- [ ] Publish history complete for a seeded run.
- [ ] All notification types dispatch correctly.
- [ ] Analytics verified against seeded publish events.
- [ ] Team/client separation and audit reporting verified (§34.4).

**Exit criteria**

An approved, previewed video can be scheduled, approved per entry, published through official interfaces, recorded, and measured — the complete MVP pipeline of §34.2. Product state: *"Assets → publish → analyze"*. Unlocks F3 and the system-testing milestone.

---

## 5. Integrated Development Workflow

### 5.1 Development Sequence

The Project Overview's own sequencing (§34.2–34.6 product roadmap; §22.1 pipeline order) is the basis for this order. Backend precedes Frontend within each pair because the Project Overview makes the Backend the owner of invariants and contracts (§41.1), so the Frontend must consume frozen contracts.

```
 Project Overview v2.0 (PDF)  ──►  SRS + Technical Planning (§44.1 mapping)
        │
        ▼
 B1  Core Platform (§29, §20.1.1, §20.4.2)      ← auth, roles, projects, audit, substrate
        │  contracts frozen
        ▼
 F1  Foundation & Project Shell                 ← dashboard, workspace, settings foundation
        │
        ▼
 Sync 1  ● Deploy B1+F1 together ● verify "login → manage projects" vertical slice
        ● MOCK: AI engines, media generation, publishing, analytics
        ● Freeze Phase-1 contract pack
        │
        ▼
 B2  AI Studio: Research→Scenes (§20.1.2–20.1.6, §24)  ← engines, gates 1–4, regeneration
        │  contracts frozen
        ▼
 F2  Creative Studio                             ← research/script/character/scene surfaces
        │
        ▼
 Sync 2  ● Deploy B2+F2 ● verify "concept → approved scene package"
        ● MOCK: video assembly, preview, scheduler, publishing, analytics
        ● Freeze Phase-2 contract pack
        │
        ▼
 B3  Production, Distribution, Insight (§20.1.7–20.4.2, §27)
        │  contracts frozen
        ▼
 F3  Production, Distribution, Insight surfaces
        │
        ▼
 Sync 3  ● Full real integration, no mocks remain ● external platform sandboxes only
        ● Freeze Phase-3 contract pack
        │
        ▼
 System & Acceptance Testing — §44.2 acceptance examples, §35.5 guardrail metrics,
 approval-gate audit (§23.2), §10 guideline regression
        │
        ▼
 PRODUCTION (MVP) — §34.2 exit criterion: "A creator can produce, review, schedule, and
 publish a complete short video with approval at every gate."
```

**Phase dependency rules** (for every phase in the diagram):

- **What must already exist:** the phase directly above it in its stream, plus the other stream's matching phase at the previous sync point.
- **What cannot exist yet:** work of later phases (the mock seams).
- **What blocks the phase:** the exit criteria of its immediate predecessor.
- **What unlocks the next phase:** its own exit criteria plus the frozen contract pack.

### 5.2 Integration Plan

| Aspect | Decision | Basis |
| --- | --- | --- |
| When Frontend integrates with Backend | Only at Sync 1, Sync 2, Sync 3 — never between phase boundaries | Contract-first rule (§2.1–2.2); sequential phase gating |
| What is mocked | Sync 1: AI engines, media, video, publishing, analytics. Sync 2: video assembly, preview, scheduler, publishing, analytics. Sync 3: nothing. | Each mock replaces only *later-phase* seams |
| What stays isolated | All gate/invariant enforcement stays Backend-only (§41.1); all review surfaces stay Frontend-only (§23.4) | §2.2 stream separation |
| When real integration begins | Sync 3 (after B3 + F3), using official-interface sandboxes | §27.6, §29.7 |
| How regressions are avoided | 1) Contract packs frozen at each sync; 2) vertical-slice regression suite after every sync; 3) guardrail-metric tests (§35.5) run at every sync; 4) mock-to-real swap requires mock parity tests | §35.5, §44.2, §36.2 (reliability) |

---

## 6. Feature-to-Phase Mapping

Every in-scope capability from §19.1 and every core feature from §20 is assigned. No feature is left unassigned.

### 6.1 In-Scope Capabilities

| # | Feature (PDF §19.1 / §20) | Frontend | Backend | Reason | Dependency | Priority (§19.4 basis) | Milestone |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Project Management (§20.1.1) | F1 | B1 | Container for all pipeline state | Identity | P0 (product core) | M1 |
| 2 | Research Engine (§20.1.2) | F2 | B2 | Gate 1 | Projects | P0 | M2 |
| 3 | Script Generator (§20.1.3) | F2 | B2 | Gate 2 | Approved research | P0 | M2 |
| 4 | Character Library (§20.1.4) | F2 | B2 | Gate 3 | Approved script | P0 | M2 |
| 5 | Scene Builder (§20.1.6) | F2 | B2 | Gate 4 | Script + characters | P0 | M2 |
| 6 | Video Generation (§20.1.7) | F3 | B3 | Composite after approved scenes | Approved scenes | P0 | M3 |
| 7 | Voice Generation (§20.1.8) | F2 | B2 | Produced per scene (§21 stage 7) | Approved narration | P0 | M2 |
| 8 | Music Generation (§20.1.9) | F2 | B2 | Per-scene mood/mixing | Scene media | P0 | M2 |
| 9 | Subtitle Generation (§20.1.10) | F2 | B2 | Derived + time-aligned per scene | Script/narration | P0 | M2 |
| 10 | Thumbnail Generation (§20.1.11) | F3 | B3 | Produced at video assembly (§21 stage 8) | Video assembly | P0 | M3 |
| 11 | Preview System (§20.2.1) | F3 | B3 | Gate 5; platform-accurate | Approved video | P0 | M3 |
| 12 | Editing Workflow (§20.2.2) | F2 (scene-level), F3 (video-level re-edit) | B2 (regeneration), B3 (video re-render) | Surgical change (§5.3, §26) | Scenes | P0 | M2 / M3 |
| 13 | Scheduler (§20.3.1) | F3 | B3 | Gate 5 → schedule | Preview | P0 | M3 |
| 14 | Publishing (§20.3.2) | F3 | B3 | Gate 6; official interfaces | Scheduled entries + approval | P0 | M3 |
| 15 | Notifications (§20.3.3) | F1 shell, F3 complete | B1 primitive, B3 full | Gate request mechanism (§23.4) | Events | P0 (supports gates; §19.4 does not rank separately) | M1 / M3 |
| 16 | Analytics (§20.4.1) | F3 | B3 | Post-publish performance | Published videos | P1 (§19.4) | M3 |
| 17 | Settings (§20.4.2) | F1 (account/security), F3 (team/platform/prefs/defaults) | B1 + B3 | Configuration | Identity | Supporting (not ranked separately in §19.4) | M1 / M3 |
| 18 | Roles & Governance (§19.1 #18, §34.4) | F1 (role UI), F3 (team governance) | B1 (RBAC), B3 (teams, chains, audit) | Governance | Identity | Team governance = P1 (§19.4) | M1 / M3 |

### 6.2 Cross-Cutting Features

| Cross-cutting feature | Assigned to | Notes |
| --- | --- | --- |
| Six approval gates (§23.2) | Gates 1–4 → B2/F2; gates 5–6 → B3/F3 | Gate state machines are Backend-owned; review surfaces are Frontend (§23.4). |
| AI workflow orchestration (§24) | B2 (research→publishing stage orchestration), B3 (analytics stage) | The 7 AI stages span both Backend phases. |
| Security & privacy (§29) | B1 (auth, RBAC, encryption, audit), B3 (publish-time safety, teams) | §29.1–29.8 mapped across B1/B3. |
| Guardrail metrics (§35.5) | B1 (no auto-publish path), B2 (fact grounding), B3 (preview rule, approval rule) | Zero-unapproved-upload and zero-unpreviewed-schedule are structural. |
| Notifications during gates (§23.4) | B1 primitive, B3 full; F1 shell, F3 complete | Approval-request routing is a gate mechanism. |

**No feature from the Project Overview is unassigned. No feature was invented.** Items in §19.2 (out of scope) and §34.5 (future) are intentionally not assigned to any phase.

### 6.3 Priority Matrix

Priorities come from §19.4 (scope priority decision matrix) and §34 (roadmap philosophy). P0 = **Critical**, P1 = **High**, P2 = **Medium/Low**.

| Priority | Features | Why (PDF basis) |
| --- | --- | --- |
| **Critical (P0)** | Research + Script, Character Library, Scene Builder + Media, Preview + Schedule, Approval + Publish | §19.4 marks all as "P0 — must have"; they are the six guarantees (§3.4). |
| **High (P1)** | Analytics | §19.4: "P1 — important." |
| **High (P1)** | Team governance | §19.4: "P1 — important"; §34.4. |
| **Medium/Low (P2)** | Multi-language | §19.4: "P2 — later"; §38.2 (English-first). |
| **Supporting (not ranked in §19.4)** | Notifications, Settings, Roles & Governance | Not separately ranked by the Project Overview; required to *operate* the P0 gates (§23.4, §29.3, §20.4.2). Treated as P0-adjacent supporting features; this is a stated inference, not a Project Overview ranking. |

---

## 7. Dependency Matrix

### 7.1 Phase-to-Phase Dependencies

| Phase | Must already exist | Cannot exist yet | Blocks | Unlocks |
| --- | --- | --- | --- | --- |
| B1 | Identity/security policy decisions | Any AI engine, media, publishing | F1, B2 | F1, B2 |
| F1 | B1 contracts | Studio/production surfaces | Sync 1 | Sync 1, F2 |
| B2 | B1 exits | Video assembly, scheduling, publishing, analytics | F2, B3 | F2, B3 |
| F2 | F1 shell, B2 contracts | Video/preview/scheduler/publishing/analytics UI | Sync 2 | Sync 2, F3 |
| B3 | B2 exits | Marketplace, localization, engagement tools | F3 | F3, System testing |
| F3 | F2, B3 contracts | Out-of-scope/future items (§19.2, §34.5) | Sync 3 | System & acceptance testing |
| System testing | B3 + F3 + Sync 3 | — | Production (MVP) | Production (MVP) |

### 7.2 Key Dependency Rules

All derived from the Project Overview:

- **Research → Script:** "No writing stage may begin until approved research exists" (G-1, §10.2).
- **Script → Production:** "No production before script approval" (§22.3).
- **Character feeds scenes:** "Character Library feeds scenes and video" (§20.5).
- **Scenes → Media:** the media package is produced per scene and joined at the media package stage (§20.5).
- **Media → Video:** video assembly composites approved scenes (§20.1.7).
- **Preview → Schedule:** "No scheduling before preview" (§22.3, §41.1).
- **Schedule → Publish:** "No publishing before publishing approval" (§22.3, §41.1).
- **Publish → Analytics:** "Performance start — analytics begin at publication time" (§27.7).

---

## 8. Milestones

| Milestone | Content | Becomes testable | Remains unfinished |
| --- | --- | --- | --- |
| **M1 — Foundation** | B1 + F1 + Sync 1 | Registration, login, project lifecycle, role enforcement, settings, audit, notification shell, dashboard "next action" | AI engines, media, video, preview, scheduling, publishing, analytics |
| **M2 — Creative Studio** | B2 + F2 + Sync 2 | Concept → approved scene package; gates 1–4; character consistency; single-scene regeneration; generation retry/resume | Video assembly, preview, scheduling, publishing, analytics |
| **M3 — Production, Distribution, Insight** | B3 + F3 + Sync 3 | Full MVP pipeline: video, thumbnail, mandatory preview, per-entry scheduling, per-entry publishing approval, publish history, notifications, analytics, team governance | Only future roadmap items (§34.3–34.5: marketplace, localization, intelligence features, enterprise/SSO) |
| **M4 — System & Acceptance Testing** | Full-system testing | §44.2 acceptance examples; §35.5 guardrail metrics (zero unapproved uploads, zero unpreviewed schedules, zero data loss, zero unauthorized access); §10 guideline regression; audit completeness | Nothing product-level; only hardening/scale |
| **M5 — Production Launch (MVP)** | Certification + launch | §34.2 exit criterion: "A creator can produce, review, schedule, and publish a complete short video with approval at every gate" | Future roadmap phases 2–5 (§34.3–34.6) |

Each milestone is a go/no-go checkpoint. M1–M3 each ends at a synchronization point where both streams are tested together (Section 5).

---

## 9. Validation Checklist

- [x] **Every feature from the Project Overview has been assigned** — all 18 in-scope capabilities (§19.1) plus cross-cutting gates, security, AI workflow, and guardrails are mapped in Section 6. No feature left unassigned.
- [x] **No extra features were invented** — nothing beyond §19.1/§20 is assigned; §19.2 (out of scope) and §34.5 (future) items are explicitly excluded.
- [x] **No requirements were removed** — all six guarantees (§3.4), six gates (§23.2), lifecycle states (§20.1.1), 12-stage journey (§21), and all four workflow invariants (§22.3) are preserved in the plan.
- [x] **Frontend contains exactly three phases** — F1, F2, F3 (Section 3).
- [x] **Backend contains exactly three phases** — B1, B2, B3 (Section 4).
- [x] **Workflow is sequential** — each phase begins only after its predecessor's exit criteria (Section 5).
- [x] **Dependencies are logical** — every dependency traces to a Project Overview invariant (§7.2).
- [x] **No implementation details were introduced** — no code, schema, APIs, folder structure, libraries, or deployment steps appear anywhere in this plan.
- [x] **Unspecified items are flagged, not assumed** — numeric service-time/cost targets (§16.3, §35), the exact platform list (§19.3), AI provider list (§41.2), and notification delivery channels are recorded as SRS inputs.

---

## 10. Conclusion

AI Director addresses a genuine, growing market need: the gap between the volume of social media content demanded and the capacity of creators to produce it while maintaining quality, consistency, and brand safety (Project Overview §45).

The product's differentiation is structural, not cosmetic. Where other AI video tools generate in a single pass and hand the result to the user, AI Director operates as a supervised production pipeline in which:

- Every fact is researched and sourced before it is written.
- Every script, character, scene, and video is reviewed and approved by a human.
- Every character is reusable and consistent across an entire content catalog.
- Every correction is surgical, regenerating only what changed.
- Every publication is scheduled, reminded, approved, uploaded, and recorded.

This roadmap translates that product into a buildable sequence: two coordinated workstreams (Frontend and Backend), three sequential phases each, aligned pair-wise with synchronization points, and a feature-to-phase mapping in which nothing is left unassigned and nothing is invented.

The platform is positioned to grow from a single creator's studio to an agency-scale production and governance system, and beyond to an intelligent content ecosystem and marketplace — always governed by the same philosophy: the machine does the work, and the human keeps the control (Project Overview §45).

The next step is to convert this roadmap and the Project Overview into a detailed Software Requirements Specification (SRS), preserving the six guarantees — verified research, reviewed scripts, reusable characters, controllable scenes, mandatory preview, and approval-before-upload — as the non-negotiable foundation of the product (Project Overview §44.1).

---

*End of Document — AI Director Development Roadmap v1.0 — 2026-08-02. Planning only; consistent with AI Director Project Overview v2.0.*
