import { api } from "./client";

// ---------------------------------------------------------------------------
// Publishing approval (backend: apps.publishing.models)
//
// Entry statuses (do not invent):
// draft | scheduled | ready_for_approval | approved | approval_invalidated |
// rejected | uploading | published | upload_failed | failed |
// failed_pending_user | canceled | deleted
//
// Approval decision (do not invent): approve | reject
// ---------------------------------------------------------------------------

export interface ScheduledEntry {
  id: number;
  post: number;
  social_account: number;
  platform: string;
  status: string;
  scheduled_utc: string;
  timezone: string;
  payload_snapshot: Record<string, unknown>;
  provider_request_id: string;
  created_at: string;
  updated_at: string;
}

export interface Approval {
  id: number;
  entry: number;
  actor: number;
  decision: string;
  reason: string;
  granted_at: string;
  expires_at: string | null;
  invalidated: boolean;
  invalidated_at: string | null;
}

export interface PendingApprovalsResponse {
  pending: ScheduledEntry[];
}

export interface HistoryResponse {
  history: ScheduledEntry[];
}

export interface ApprovalsResponse {
  approvals: Approval[];
}

export interface ApprovalResponse {
  approval: Approval;
}

export interface RecheckResponse {
  expired_count: number;
}

// ---------------------------------------------------------------------------
// Publishing approval API (all project-scoped endpoints live under
// /projects/<pk>/publishing/; pending + social-account endpoints live under
// /publishing/).
// ---------------------------------------------------------------------------

export async function getPublishingHistory(
  projectId: number,
): Promise<HistoryResponse> {
  return api.get<HistoryResponse>(
    `/projects/${projectId}/publishing/history/`,
  );
}

export async function getEntryApprovals(
  projectId: number,
  entryId: number,
): Promise<ApprovalsResponse> {
  return api.get<ApprovalsResponse>(
    `/projects/${projectId}/publishing/entries/${entryId}/approvals/`,
  );
}

export async function approveEntry(
  projectId: number,
  entryId: number,
  reason = "",
): Promise<ApprovalResponse> {
  return api.post<ApprovalResponse>(
    `/projects/${projectId}/publishing/entries/${entryId}/approve/`,
    { reason },
  );
}

export async function rejectEntry(
  projectId: number,
  entryId: number,
  reason = "",
): Promise<ApprovalResponse> {
  return api.post<ApprovalResponse>(
    `/projects/${projectId}/publishing/entries/${entryId}/reject/`,
    { reason },
  );
}

export async function getPendingApprovals(): Promise<PendingApprovalsResponse> {
  return api.get<PendingApprovalsResponse>(`/publishing/pending-approvals/`);
}

export async function recheckApprovals(): Promise<RecheckResponse> {
  return api.post<RecheckResponse>(`/publishing/recheck-approvals/`, {});
}
