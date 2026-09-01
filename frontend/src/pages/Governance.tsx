import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import {
  getAuditLogs,
  createAuditExport,
  type AuditEntry,
  type AuditExport,
} from "../api/governance";
import { ApiError } from "../api/client";

// ---------------------------------------------------------------------------
// Governance + Audit Reporting UI (Task 50).
//
// Role-based workspace view: surfaces the operating privilege matrix from the
// authenticated user's role (Editor cannot approve/publish, per Overview
// §29.3). Audit report: actor / time / reason for team-scoped, append-only
// audit records (`GET /api/audit/logs/`). Export: records a real server-side
// export via `POST /api/analytics/audit-export/` and generates a matching
// client-side CSV/JSON file from the same real data.
// ---------------------------------------------------------------------------

// Role privilege order (highest → lowest), mirroring backend permissions.py.
const ROLE_ORDER = ["Admin", "Approver/Owner", "Creator", "Editor", "Reviewer", "Viewer"];

function roleAtLeast(role: string, minimum: string): boolean {
  const r = ROLE_ORDER.indexOf(role);
  const m = ROLE_ORDER.indexOf(minimum);
  if (r === -1 || m === -1) return false;
  return r <= m;
}

interface Capability {
  name: string;
  label: string;
  minimum: string;
  granted: boolean;
}

const CAPABILITIY_MATRIX: { name: string; label: string; minimum: string }[] = [
  { name: "view_projects", label: "View projects", minimum: "Viewer" },
  { name: "manage_projects", label: "Manage projects", minimum: "Editor" },
  { name: "view_audit", label: "View audit logs", minimum: "Editor" },
  { name: "approve", label: "Approve publishing", minimum: "Approver/Owner" },
  { name: "publish", label: "Publish content", minimum: "Approver/Owner" },
  { name: "admin", label: "Admin", minimum: "Admin" },
];

function formatTimestamp(value: string): string {
  const d = new Date(value);
  if (isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function formatActionLabel(action: string): string {
  return action.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function Governance() {
  const { user } = useAuth();

  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [exporting, setExporting] = useState<"csv" | "json" | null>(null);
  const [exportResult, setExportResult] = useState<AuditExport | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  const role = user?.role ?? "Viewer";
  const capabilities: Capability[] = CAPABILITIY_MATRIX.map((c) => ({
    ...c,
    granted: roleAtLeast(role, c.minimum),
  }));
  const canViewAudit = roleAtLeast(role, "Editor");

  const loadLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAuditLogs();
      setLogs(res.audit_log);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 403
          ? "You do not have permission to view audit logs (Editor role or higher required)."
          : "Failed to load audit records.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (canViewAudit) loadLogs();
    else setLoading(false);
  }, [canViewAudit, loadLogs]);

  const download = (filename: string, content: string, mime: string) => {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const buildCsv = (entries: AuditEntry[]): string => {
    const header = "id,actor_username,action,target_type,target_id,reason,created_at";
    const esc = (v: string) => `"${(v ?? "").replace(/"/g, '""')}"`;
    const rows = entries.map((e) =>
      [e.id, esc(e.actor_username), esc(e.action), esc(e.target_type), esc(e.target_id), esc(e.reason), esc(e.created_at)].join(","),
    );
    return [header, ...rows].join("\n");
  };

  const handleExport = async (format: "csv" | "json") => {
    setExporting(format);
    setExportError(null);
    setExportResult(null);
    try {
      // Record a real server-side export (counts the team-scoped audit trail).
      const res = await createAuditExport(format);
      setExportResult(res.export);
      // Generate a client-side file from the same real data since the backend
      // returns export metadata (not file bytes).
      if (format === "csv") {
        download(`audit-report-${Date.now()}.csv`, buildCsv(logs), "text/csv");
      } else {
        download(
          `audit-report-${Date.now()}.json`,
          JSON.stringify(logs, null, 2),
          "application/json",
        );
      }
    } catch (err) {
      setExportError(
        err instanceof ApiError && err.status === 403
          ? "You do not have permission to export audit records."
          : "Failed to export audit records.",
      );
    } finally {
      setExporting(null);
    }
  };

  const contributorCount =
    [...new Set(logs.map((l) => l.actor_username))].length;

  return (
    <div className="page">
      <h1>Governance & Audit</h1>
      <p className="text-muted">
        Role-based workspace overview and an append-only audit report of
        tracked actions (actor / time / reason). Publishing is restricted to
        accountable roles; Editors can create and manage content but cannot
        approve or publish.
      </p>

      <section className="detail-section">
        <h2>Workspace & Roles</h2>
        <div className="governance-role-banner">
          <strong>Signed in as:</strong> {user?.username ?? "—"} · Role:{" "}
          <span className="user-role">{role}</span>
        </div>
        <table className="project-table">
          <thead>
            <tr>
              <th>Capability</th>
              <th>Minimum Role</th>
              <th>Granted</th>
            </tr>
          </thead>
          <tbody>
            {capabilities.map((c) => (
              <tr key={c.name}>
                <td>{c.label}</td>
                <td>{c.minimum}</td>
                <td>
                  {c.granted ? (
                    <span className="badge badge-active">Yes</span>
                  ) : (
                    <span className="badge badge-inactive">No</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!roleAtLeast(role, "Approver/Owner") && (
          <p className="empty-text">
            Your role cannot approve or publish. Only Approver/Owner and Admin
            roles can approve and publish content.
          </p>
        )}
      </section>

      <section className="detail-section">
        <h2>Audit Report</h2>
        <div className="audit-toolbar">
          <span className="text-muted">
            {logs.length > 0
              ? `${logs.length} records${contributorCount > 0 ? ` · ${contributorCount} actor(s)` : ""}`
              : "No records"}
          </span>
          <div className="audit-actions">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={!canViewAudit || logs.length === 0 || exporting !== null}
              onClick={() => handleExport("csv")}
            >
              {exporting === "csv" ? "Exporting…" : "Export CSV"}
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={!canViewAudit || logs.length === 0 || exporting !== null}
              onClick={() => handleExport("json")}
            >
              {exporting === "json" ? "Exporting…" : "Export JSON"}
            </button>
          </div>
        </div>

        {exportError && <div className="page-error">{exportError}</div>}
        {exportResult && (
          <p className="empty-text audit-export-note">
            Server export recorded: {exportResult.format.toUpperCase()} ·{" "}
            {exportResult.record_count} records · {formatTimestamp(exportResult.created_at)}
          </p>
        )}

        {!canViewAudit ? (
          <p className="empty-state">
            You do not have permission to view the audit report.
          </p>
        ) : loading ? (
          <div className="page-loading">Loading audit report…</div>
        ) : error ? (
          <div className="page-error">{error}</div>
        ) : logs.length === 0 ? (
          <p className="empty-state">
            No audit records yet. Tracked actions will appear here as they
            occur.
          </p>
        ) : (
          <table className="project-table">
            <thead>
              <tr>
                <th>Actor</th>
                <th>Action</th>
                <th>Target</th>
                <th>Reason</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((entry) => (
                <tr key={entry.id}>
                  <td>{entry.actor_username}</td>
                  <td>{formatActionLabel(entry.action)}</td>
                  <td>
                    {entry.target_type ? (
                      <>
                        {entry.target_type}
                        {entry.target_id ? ` #${entry.target_id}` : ""}
                      </>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>{entry.reason || "—"}</td>
                  <td>{formatTimestamp(entry.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
