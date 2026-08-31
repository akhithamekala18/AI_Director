import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getPublishingHistory,
  getEntryApprovals,
  approveEntry,
  rejectEntry,
  type ScheduledEntry,
  type Approval,
} from "../api/publishing";
import { ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

// ---------------------------------------------------------------------------
// Publishing approval is the final gate: a per-platform summary is shown and an
// explicit, recorded confirmation is required. Approving one platform never
// approves another. A valid approval is required before anything uploads, and
// approval is valid for 24h up to the scheduled time.
// ---------------------------------------------------------------------------

const APPROVABLE_STATUSES = ["ready_for_approval", "approval_invalidated"];
const APPROVE_CAPABLE_ROLES = ["Approver/Owner", "Admin"];

// 24h validity is enforced by the backend (expires_at = scheduled_utc - 24h).
const VALIDITY_HOURS = 24;

function formatStatus(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function statusClass(status: string): string {
  if (status === "approved" || status === "published") return "state-approved";
  if (status === "rejected" || status === "upload_failed" || status === "failed")
    return "state-revision";
  if (
    status === "ready_for_approval" ||
    status === "approval_invalidated" ||
    status === "scheduled" ||
    status === "draft"
  )
    return "state-review";
  if (status === "uploading") return "state-generating";
  return "state-draft";
}

// ---------------------------------------------------------------------------
// Validity helpers (backend: Approval.is_valid + is_approval_valid)
// ---------------------------------------------------------------------------

function latestValidApproval(approvals: Approval[]): Approval | null {
  const valid = approvals
    .filter(
      (a) =>
        a.decision === "approve" &&
        !a.invalidated &&
        (a.expires_at == null || new Date(a.expires_at).getTime() >= Date.now()),
    )
    .sort(
      (a, b) =>
        new Date(b.granted_at).getTime() - new Date(a.granted_at).getTime(),
    );
  return valid[0] ?? null;
}

function countdown(expiresAt: string | null): {
  ms: number;
  label: string;
  expired: boolean;
} {
  if (!expiresAt) return { ms: 0, label: "no expiry", expired: false };
  const ms = new Date(expiresAt).getTime() - Date.now();
  if (ms <= 0) return { ms: 0, label: "expired", expired: true };
  const totalMinutes = Math.floor(ms / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return {
    ms,
    label: `${hours}h ${String(minutes).padStart(2, "0")}m`,
    expired: false,
  };
}

function payloadSummary(entry: ScheduledEntry): Record<string, unknown> {
  const p = entry.payload_snapshot ?? {};
  return p;
}

function formatUtc(iso: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PublishingApproval() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);
  const { user } = useAuth();

  const [entries, setEntries] = useState<ScheduledEntry[]>([]);
  const [approvalsByEntry, setApprovalsByEntry] = useState<
    Record<number, Approval[]>
  >({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Approve / reject confirmation state
  const [reasonByEntry, setReasonByEntry] = useState<Record<number, string>>(
    {},
  );
  const [activeAction, setActiveAction] = useState<number | null>(null);
  const [busyEntry, setBusyEntry] = useState<number | null>(null);

  const canApprove =
    user != null && APPROVE_CAPABLE_ROLES.includes(user.role);

  const approveReasons = (entryId: number) => reasonByEntry[entryId] ?? "";

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const history = await getPublishingHistory(projectId);
      setEntries(history.history);
      // Fetch approvals for every entry in parallel so per-entry validity
      // (24h countdown) and recorded decisions can be surfaced.
      const result = await Promise.all(
        history.history.map((e) =>
          getEntryApprovals(projectId, e.id).then((r) => ({
            id: e.id,
            approvals: r.approvals,
          })),
        ),
      );
      const map: Record<number, Approval[]> = {};
      result.forEach((r) => {
        map[r.id] = r.approvals;
      });
      setApprovalsByEntry(map);
    } catch (err) {
      setError(err instanceof ApiError ? "Failed to load publishing data" : "Failed to load publishing data");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) loadData();
  }, [projectId, loadData]);

  const handleApprove = async (entry: ScheduledEntry) => {
    if (!canApprove) return;
    setBusyEntry(entry.id);
    setError(null);
    try {
      const res = await approveEntry(
        projectId,
        entry.id,
        approveReasons(entry.id).trim(),
      );
      setApprovalsByEntry((prev) => ({
        ...prev,
        [entry.id]: [res.approval, ...(prev[entry.id] ?? [])],
      }));
      setEntries((prev) =>
        prev.map((e) => (e.id === entry.id ? { ...e, status: "approved" } : e)),
      );
      setActiveAction(null);
      setReasonByEntry((prev) => ({ ...prev, [entry.id]: "" }));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `Approval failed: ${err.message}`
          : "Approval failed",
      );
    } finally {
      setBusyEntry(null);
    }
  };

  const handleReject = async (entry: ScheduledEntry) => {
    if (!canApprove) return;
    setBusyEntry(entry.id);
    setError(null);
    try {
      const res = await rejectEntry(
        projectId,
        entry.id,
        approveReasons(entry.id).trim(),
      );
      setApprovalsByEntry((prev) => ({
        ...prev,
        [entry.id]: [res.approval, ...(prev[entry.id] ?? [])],
      }));
      setEntries((prev) =>
        prev.map((e) => (e.id === entry.id ? { ...e, status: "rejected" } : e)),
      );
      setActiveAction(null);
      setReasonByEntry((prev) => ({ ...prev, [entry.id]: "" }));
      // A rejection returns the entry to the pre-publish (draft) state.
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `Rejection failed: ${err.message}`
          : "Rejection failed",
      );
    } finally {
      setBusyEntry(null);
    }
  };

  if (loading) return <div className="page-loading">Loading publishing approvals…</div>;

  const pending = entries.filter((e) => APPROVABLE_STATUSES.includes(e.status));
  const approved = entries.filter((e) => e.status === "approved");
  const rejected = entries.filter((e) => e.status === "rejected");
  const other = entries.filter(
    (e) =>
      !APPROVABLE_STATUSES.includes(e.status) &&
      e.status !== "approved" &&
      e.status !== "rejected",
  );

  const renderActions = (entry: ScheduledEntry) => {
    if (!APPROVABLE_STATUSES.includes(entry.status)) return null;
    if (!canApprove) {
      return (
        <p className="text-muted">
          Approval is restricted to Approver/Owner and Admin roles.
        </p>
      );
    }
    if (activeAction !== entry.id) {
      return (
        <div className="action-buttons">
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => setActiveAction(entry.id)}
          >
            Approve
          </button>
          <button
            type="button"
            className="btn btn-danger btn-sm"
            onClick={() => setActiveAction(entry.id)}
          >
            Reject
          </button>
        </div>
      );
    }
    return (
      <div className="reschedule-form approval-form">
        <label htmlFor={`approval-reason-${entry.id}`}>Reason (optional)</label>
        <input
          id={`approval-reason-${entry.id}`}
          type="text"
          value={approveReasons(entry.id)}
          onChange={(e) =>
            setReasonByEntry((prev) => ({
              ...prev,
              [entry.id]: e.target.value,
            }))
          }
          placeholder="Optional"
        />
        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={() => handleApprove(entry)}
          disabled={busyEntry === entry.id}
        >
          {busyEntry === entry.id ? "Saving…" : "Confirm Approve"}
        </button>
        <button
          type="button"
          className="btn btn-danger btn-sm"
          onClick={() => handleReject(entry)}
          disabled={busyEntry === entry.id}
        >
          {busyEntry === entry.id ? "Saving…" : "Confirm Reject"}
        </button>
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => setActiveAction(null)}
        >
          Back
        </button>
      </div>
    );
  };

  const renderValidity = (entry: ScheduledEntry) => {
    const approvals = approvalsByEntry[entry.id] ?? [];
    const validApproval = latestValidApproval(approvals);
    if (!validApproval || entry.status !== "approved") {
      return (
        <p className="media-asset-ref">
          <em>No valid approval — upload is blocked.</em>
        </p>
      );
    }
    const cd = countdown(validApproval.expires_at);
    if (cd.expired) {
      return (
        <p className="media-error">Approval expired — upload is blocked.</p>
      );
    }
    return (
      <p className="media-asset-ref approval-valid">
        <strong>Approved</strong> — valid for {VALIDITY_HOURS}h up to scheduled
        time · expires in {cd.label}
      </p>
    );
  };

  const renderEntry = (entry: ScheduledEntry) => {
    const payload = payloadSummary(entry);
    const approvals = approvalsByEntry[entry.id] ?? [];
    const lastDecision = approvals[0];
    const isInvalidated = entry.status === "approval_invalidated";
    return (
      <div key={entry.id} className="source-card">
        <div className="source-header">
          <span className="job-type">{entry.platform}</span>
          <span className={`state-badge ${statusClass(entry.status)}`}>
            {formatStatus(entry.status)}
          </span>
        </div>

        {/* Payload summary for this platform */}
        <div className="media-asset-ref">
          <strong>Scheduled:</strong> {formatUtc(entry.scheduled_utc)} ({entry.timezone || "UTC"})
        </div>
        {payload.title ? (
          <div className="media-asset-ref">
            <strong>Title:</strong> {String(payload.title)}
          </div>
        ) : null}
        {payload.video ? (
          <div className="media-asset-ref">
            <strong>Video:</strong> {String(payload.video)}
          </div>
        ) : null}
        {payload.thumbnail ? (
          <div className="media-asset-ref">
            <strong>Thumbnail:</strong> {String(payload.thumbnail)}
          </div>
        ) : null}
        {payload.captions ? (
          <div className="media-asset-ref">
            <strong>Captions:</strong> {String(payload.captions)}
          </div>
        ) : null}
        {Object.keys(payload).length === 0 && (
          <p className="text-muted">No payload summary recorded for this entry.</p>
        )}

        {/* Invalidation notice on schedule/platform change */}
        {isInvalidated && (
          <div className="media-error approval-invalidated">
            Approval was invalidated because the schedule or platform changed.
            Re-approval is required before this entry can upload.
          </div>
        )}

        {renderValidity(entry)}

        {lastDecision && (
          <div className="media-asset-ref">
            <strong>Last decision:</strong> {formatStatus(lastDecision.decision)}{" "}
            by actor #{lastDecision.actor} · {formatUtc(lastDecision.granted_at)}
            {lastDecision.reason ? ` — ${lastDecision.reason}` : ""}
          </div>
        )}

        {renderActions(entry)}
      </div>
    );
  };

  return (
    <div className="page">
      <h1>Publishing Approval</h1>
      <p>
        <Link className="back-link" to={`/projects/${projectId}`}>
          &larr; Back to Project
        </Link>
      </p>

      <p className="text-muted">
        Review and explicitly approve or reject each platform entry before it can
        upload. Approving one platform does <strong>not</strong> approve another.
        Approval is valid for {VALIDITY_HOURS}h up to the scheduled time; no
        approval means no upload.
      </p>

      {error && <div className="page-error">{error}</div>}

      <div className="detail-section">
        <h2>Pending Approval ({pending.length})</h2>
        {pending.length === 0 ? (
          <p className="text-muted">
            No entries awaiting approval.
          </p>
        ) : (
          <div className="media-list">
            {pending.map(renderEntry)}
          </div>
        )}
      </div>

      <div className="detail-section">
        <h2>Approved ({approved.length})</h2>
        {approved.length === 0 ? (
          <p className="text-muted">No approved entries.</p>
        ) : (
          <div className="media-list">{approved.map(renderEntry)}</div>
        )}
      </div>

      <div className="detail-section">
        <h2>Rejected — Returned to Draft ({rejected.length})</h2>
        {rejected.length === 0 ? (
          <p className="text-muted">No rejected entries.</p>
        ) : (
          <div className="media-list">{rejected.map(renderEntry)}</div>
        )}
      </div>

      {other.length > 0 && (
        <div className="detail-section">
          <h2>Other ({other.length})</h2>
          <div className="media-list">{other.map(renderEntry)}</div>
        </div>
      )}
    </div>
  );
}
