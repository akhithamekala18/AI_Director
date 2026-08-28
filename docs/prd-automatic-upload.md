# PRD — Automatic Upload with Mandatory User Approval

| Property | Value |
|---|---|
| Product | AI Director (AI Content Creator) |
| Feature | Scheduled social-media publishing with mandatory pre-upload human approval |
| Version / Status | 1.1 / Finalized decisions incorporated |
| Source of truth | AI Director Project Overview v2.0 — §3.4 (G6), §20.3.1–20.3.2, §23.2 (Gate 6), §27, §29.7; Development Roadmap §3.3 (B3/F3) |
| Priority | P0 — approval-before-upload is a product invariant |

## 1. Problem Statement
Publishing short-form video across platforms is manual: creators log in to each platform, upload, and verify — slow, error-prone, and unrecorded. Automating upload without approval removes the human and creates the product's worst failure: unapproved content reaching an audience, with reputational, compliance, and governance damage. Approval-before-upload is therefore a non-negotiable guarantee: "every scheduled upload requires explicit, recorded human approval; silence never publishes" (§3.4). **No approval means no upload — never automatically.** The problem affects individual creators, businesses, and agencies publishing multi-platform video at scale. This feature automates every mechanical step — scheduling, payload prep, upload, transient-failure retry, notification, history — while keeping the human as the final, mandatory decision-maker (Gate 6, §23.2).

## 2. Feature Goal
| Concern | Goal |
|---|---|
| Automation | Prepare payloads, run upload jobs, notify status; auto-retry **transient failures only** (max 3 retries); never decide to publish (§27.3) |
| Scheduling | Per-platform entries with explicit date/time; one video may target **multiple platforms**; reschedule/cancel/re-platform allowed, but any schedule/platform **change invalidates approval** (Decision 5) |
| User approval | Explicit, granular, recorded, **in-app-only** consent — one approval per platform entry; **valid only within 24 hours before the scheduled time**, otherwise expired (§27.5, Decisions 2 & 4) |
| Publishing | Upload only through **officially supported** platform APIs and only after a **valid, unexpired** approval (§27.6, §41.1) |
| Tracking | Per-platform status, publish history, retry trace, and audit for every entry and attempt (§27.7, Decision 9) |

## 3. Success Metrics (V1)
Targets are proposed and subject to SRS validation.
| Metric | Proposed target |
|---|---|
| Scheduled uploads completed | Baseline tracked **per platform** |
| Upload success rate (per platform) | ≥ 98% |
| Failed (terminal) upload rate | ≤ 2% |
| Approval rate | ≥ 90% of requested entries |
| Approval granted outside 24h window (must re-approve) | ≤ 5% |
| Approval → publish completion | ≥ 95% of approved |
| Avg time scheduled → approved | ≤ 30 min (within the 24h window) |
| Notification delivery success | ≥ 99% |
| Duplicate publications | 0 |
| Unauthorized publications | 0 (guardrail, §35.5) |

## 4. User Stories + Acceptance Criteria
| ID | Story | Acceptance (Given / When / Then) |
|---|---|---|
| US-001 — Schedule a video | I schedule an approved, previewed video for one or more platforms (§27.1) | G: approved and previewed video exists. W: I create a schedule with platform(s), date, time. T: post DRAFT → SCHEDULED; one entry per platform, UTC + timezone persisted. |
| US-002 — Select platform(s) | I choose any officially supported platform | G: scheduling screen. W: I select one or more supported platforms/accounts. T: only officially supported, active, connected accounts are listed; the list is extensible; per-platform entries created. |
| US-003 — Select date/time | I set publish date/time in my local zone | G: scheduling. W: I input local time. T: stored as a UTC instant with timezone; re-displayed in the user's local zone; DST-safe. |
| US-004 — Receive approval notification | A pending approval is surfaced to me | G: payload preparation completes. W: system readies entries. T: states READY_FOR_APPROVAL; user informed via notification — **notification informs only; approval happens in the app** (§23.4, Decision 4). |
| US-005 — Review scheduled post | I review the post before approving | G: entries READY_FOR_APPROVAL. W: I open the review. T: complete publishing configuration shown for **every selected platform**: platform, title, video, thumbnail, captions, scheduled time (§27.5, Decision 9). |
| US-006 — Approve upload | I explicitly approve | G: entries READY_FOR_APPROVAL and scheduled time within 24h. W: I confirm in-app. T: approval recorded (actor, time); entry APPROVED; upload begins only after this record. |
| US-007 — Re-approve expired approval | I approve when a prior approval has expired | G: prior approval expired (granted > 24h before scheduled time). W: upload is due. T: publishing blocked; entry returns to READY_FOR_APPROVAL; a new valid in-app approval is required (Decision 2). |
| US-008 — Reject upload | I reject the post | G: entry READY_FOR_APPROVAL. W: I reject with a reason. T: rejection recorded; entry REJECTED → DRAFT and retained until I delete it; never auto-deleted (§27.2, Decision 6). |
| US-009 — Modify after approval | I change date/time/platform after approval | G: entry APPROVED. W: I change schedule or platform. T: prior approval **invalidated**; entry returns to READY_FOR_APPROVAL; a new approval is required before upload (Decision 5). |
| US-010 — Cancel scheduled post | I cancel before publishing | G: entry not yet uploaded. W: I cancel. T: entry CANCELED; no upload; audited. |
| US-011 — Successful upload | My approved post publishes | G: entry APPROVED with valid approval. W: upload executes. T: that platform PUBLISHED; record in history (§27.7); other platforms tracked independently (Decision 9). |
| US-012 — Failed upload (transient) | A transient failure occurs | G: temporary outage/network/server error/timeout. W: attempt fails. T: loud status; auto-retry up to 3 more times (waits 1/5/15 min) before terminal FAILED; approval re-validated each attempt (Decision 8). |
| US-013 — Failed upload (permanent) | A permanent failure occurs | G: expired auth, revoked permissions, invalid format, content rejection, missing permission, deleted account. W: upload fails. T: no auto-retry; failure explained and user notified; user fixes issue; **new approval required**; upload may then proceed (Decision 8). |
| US-014 — View publishing history | I audit my history | G: entries exist across platforms. W: I open history. T: per-platform entry, approval record, payload snapshot, retries, and outcome visible; a failure on one platform never reports the whole post as successful (§27.7, Decision 9). |

## 5. Scope
**V1 ships:** video selection (approved/previewed only); multi-platform selection (any officially supported platform; extensible); scheduling with timezone handling; approval notification; in-app approval/review screen with full payload summary; 24h approval validity + re-approval; explicit per-platform approval; schedule/platform changes invalidating approval; idempotent publishing; upload status **per platform**; transient retries (max 3); cancellation; rejection → Drafts; publishing history; audit trail.

**V1 does not ship:** AI content generation; analytics dashboards; trend detection; fully autonomous publishing (prohibited); email/SMS/external approval links; mandatory MFA on approval; campaign management; team approval chains; best-time/cross-platform optimization; engagement tools; marketplace; unsupported platform integrations; localization beyond timezone and date formatting.

## 6. Data Model Changes (conceptual)
| Entity | Purpose | Key fields | Relationships & states |
|---|---|---|---|
| ScheduledPost | Logical publication of one video to the selected platform set | videoRef, ownerRef, scheduledAt (UTC), timezone, status, payloadSnapshot | 1 post → N ScheduledEntries; overall status = per-platform rollup |
| ScheduledEntry (per platform, §27.3) | Plan to publish the video to one platform at one time | postRef, socialAccountRef, platform, scheduledAt (UTC), timezone, status, payloadSnapshot | states per §7; each platform tracks independently (Decision 9) |
| SocialAccount | User's connected platform account | platform, scopes, encryptedTokens, status (active/revoked/expired), ownerRef | 1 user → N accounts; connected → revoked |
| Approval | Recorded, in-app consent for one entry | entryRef, actor, role, decision (approve/reject), reason, grantedAt, expiresAt (= scheduledAt − 24h), invalidatedBy | 1 entry → N approvals; exactly one may be valid/gating; invalidated on schedule/platform/payload change or expiry |
| UploadAttempt | Idempotent execution trace | entryRef, attemptNo (1–4), status, failureKind (transient/permanent), providerRequestId, startedAt/finishedAt, error | 1 entry → N attempts; at most one success |
| PublishingAuditLog | Immutable audit (§5.8, G-7) | actor, time, reason, action, entry/approval/attempt refs | append-only; references all above |

## 7. State Machine
```
DRAFT → SCHEDULED → READY_FOR_APPROVAL → APPROVED → UPLOADING → PUBLISHED
                                 │          │
              REJECTED → DRAFT ◄─┤          ├─(any schedule/platform change)──► APPROVAL INVALIDATED ──► READY_FOR_APPROVAL
                                 │          └─(expired: approval older than 24h ahead of schedule)──► READY_FOR_APPROVAL
UPLOADING --(transient fail)--> UPLOAD_FAILED --(auto-retry ×3, wait 1/5/15 min)--> UPLOADING  |  --(retries exhausted)--> FAILED
UPLOADING --(permanent fail)--> FAILED_PENDING_USER --(user fixes + new approval)--> READY_FOR_APPROVAL
DRAFT/SCHEDULED/READY_FOR_APPROVAL --(user cancel)--> CANCELED
DRAFT --(user delete)--> DELETED
```
States are tracked **per platform entry**; a multi-platform post is a rollup of its entries. Guard (non-negotiable): the transition into **UPLOADING** is reachable only from **APPROVED**, and only when a valid, recorded, unexpired Approval exists for that entry. **NO APPROVAL → NO UPLOAD.** No automated transition enters UPLOADING; scheduling-time arrival never publishes on its own (§29.7, Decision 3). Retries re-check approval validity and **never bypass the approval requirement** (Decision 8).

## 8. Edge Cases + Failure States
| Case | Expected behavior |
|---|---|
| User never approves | No upload, ever; pending reminder sent (§27.4); entry terminal handling → Open Q1 |
| Approval granted > 24h before scheduled time | Expired → publishing blocked; entry READY_FOR_APPROVAL; new approval required (Decision 2) |
| Schedule/platform changed after approval | Approval invalidated; entry READY_FOR_APPROVAL; new approval required; approved config never reused (Decision 5) |
| User rejects | REJECTED → DRAFT; retained until user deletes; may edit/reschedule later (Decision 6) |
| Scheduled time passes unapproved | Never auto-uploads; entry stays READY_FOR_APPROVAL (Decision 3) |
| Transient failure (outage/network/server/timeout) | Auto-retry ×3 (waits 1/5/15 min); then terminal FAILED; loud status (§5.7, Decision 8) |
| Permanent failure (expired auth, revoked perms, invalid format, content rejection, missing permission, deleted account) | No auto-retry; failure explained + user notified; user fixes issue; new approval; upload proceeds (Decision 8) |
| Account disconnected/revoked | That platform's entries blocked; no retry; tokens rotated; user notified |
| Duplicate / partial upload | Idempotency key per entry; at most one success; reconcile via providerRequestId; retry never re-sends a succeeded payload |
| Rate limit | Treated as transient; retry respecting provider policy; status surfaced |
| Provider unknown error | Treated as transient once; on repeat, classified; surfaced; no infinite retry loop |
| Multiple platforms, one fails | Per-platform statuses independent: Instagram Published / YouTube Published / Facebook FAILED / TikTok Published — post never falsely reported fully successful (Decision 9) |
| Concurrent approvals (two sessions) | First valid approval wins; second sees current state; no double upload |
| Notification not delivered | In-app approval request always reachable; notification retried (delivery channel → Open Q2) |

## 9. Security + Safety Requirements
- No upload path exists without a valid, unexpired per-entry Approval; **no approval → no upload** (state-machine guard; structural test, Decision 3).
- Approval is granted **inside the application only**; no email/SMS/external/third-party approval mechanisms exist (Decision 4).
- Approval freshness: an approval is valid only within 24 hours before the scheduled publishing time; expired approvals are never treated as valid (Decision 2).
- Approval integrity: bound to the approved payload snapshot; any schedule, platform, or content change invalidates it and requires new approval (Decision 5).
- **MFA is not mandatory** for any publishing approval in V1 (Decision 7).
- Authorization per §29.3 / §27.8: only Owner/Admin may approve; Viewer/Reviewer never see approval controls (enforced server-side).
- Official platform OAuth only; tokens encrypted at rest, scoped, never logged; secrets never in source or git.
- Idempotency keys prevent duplicate publishing; at most one success per entry; retries re-validate approval and never bypass it.
- Webhooks/callbacks: HTTPS, signed and verified, no secrets in URLs.
- Approval performed inside an authenticated session.
- Revocation/disconnect: disable scheduling, block/stop uploads for that account, rotate tokens immediately.

## 10. Global / International Requirements
- Store all instants in UTC; keep the entry's timezone; render in the user's local zone.
- DST-safe: schedule by absolute instant; re-validate entries across DST shifts.
- Locale-independent scheduling: absolute time is the source of truth; formatting is display-only.
- Platform availability: enforce per-region availability when selecting officially supported platforms; surface unavailable states.
- Language-independent approval: approval is a positive, explicit in-app action whose meaning does not depend on UI language; payload summaries are i18n-ready.
- 24-hour approval/retry windows computed from the scheduled instant in store-time (UTC), not local calendar time.
- Regional API limits recorded and surfaced per provider/region.

## 11. Open Questions
1. When a scheduled time passes with no approval, what is the entry's terminal handling — remain pending for later in-app approval, auto-return to Draft, or auto-cancel (with user notified)? (Decision 3 forbids auto-publish only.)
2. Which notification delivery channels inform the user that in-app approval is pending (e.g., email, push, SMS)? Approval itself remains in-app only (Decision 4).
3. When the schedule or selected-platform set of a multi-platform post changes after approval, is approval invalidated for **all** platform entries or only the changed ones? (Decision 5 requires invalidation on change; granularity unstated.)