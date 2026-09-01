import { api } from "./client";

// ---------------------------------------------------------------------------
// Governance + audit reporting (backend: apps.audit, apps.analytics).
// Read-only audit-view surface. Every record is append-only on the backend
// and team-scoped to the requesting user.
// ---------------------------------------------------------------------------

export interface AuditEntry {
  id: number;
  actor_username: string;
  action: string;
  target_type: string;
  target_id: string;
  reason: string;
  created_at: string;
}

export interface AuditLogsResponse {
  audit_log: AuditEntry[];
}

export interface AuditExport {
  id: number;
  format: string;
  record_count: number;
  created_at: string;
}

export interface AuditExportResponse {
  export: AuditExport;
}

// ---------------------------------------------------------------------------
// Governance / Audit API
// ---------------------------------------------------------------------------

export async function getAuditLogs(): Promise<AuditLogsResponse> {
  return api.get<AuditLogsResponse>("/audit/logs/");
}

export async function createAuditExport(
  format: "csv" | "json",
): Promise<AuditExportResponse> {
  return api.post<AuditExportResponse>("/analytics/audit-export/", { format });
}
