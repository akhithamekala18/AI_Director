import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getPublishingHistory,
  getEntryApprovals,
  getEntryRetryStatus,
  type ScheduledEntry,
  type Approval,
  type RetryStatus,
} from "../api/publishing";
import { ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

// ---------------------------------------------------------------------------
// Publish History (Task 48). Shows the per-entry publication history:
// the payload snapshot, recorded approvals, outcome, and retry/cancellation
// state. Data comes from the real backend publishing endpoints only.
// ---------------------------------------------------------------------------

const SUCCESSFUL_STATUSES = ["published"];
const FAILED_STATUSES = ["failed", "failed_pending_user", "upload_failed"];
const CANCELED_STATUSES = ["canceled"];

function formatStatus(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function statusClass(status: string): string {
  if (SUCCESSFUL_STATUSES.includes(status)) return "state-approved";
  if (FAILED_STATUSES.includes(status)) return "state-revision";
  if (CANCELED_STATUSES.includes(status)) return "state-draft";
  return "state-review";
}

function formatUtc(iso: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

function formatPayloadEntry(value: unknown): string {
  if (value == null || value === "") return "—";
  return String(value);
}

function latestApproval(approvals: Approval[]): Approval | null {
  if (approvals.length === 0) return null;
  return [...approvals].sort(
    (a, b) => new Date(b.granted_at).getTime() - new Date(a.granted_at).getTime(),
  )[0];
}

export function PublishHistory() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);
  const { user } = useAuth();

  const [entries, setEntries] = useState<ScheduledEntry[]>([]);
  const [approvalsByEntry, setApprovalsByEntry] = useState<
    Record<number, Approval[]>
  >({});
  const [retryByEntry, setRetryByEntry] = useState<
    Record<number, RetryStatus | null>
  >({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const history = await getPublishingHistory(projectId);
      setEntries(history.history);

      // Fetch approvals + retry status per entry in parallel so per-entry
      // outcome, recorded decisions, and retry/cancel state can be surfaced.
      const approvalResults = await Promise.all(
        history.history.map((e) =>
          getEntryApprovals(projectId, e.id).then((r) => ({
            id: e.id,
            approvals: r.approvals,
          })),
        ),
      );
      const approvalMap: Record<number, Approval[]> = {};
      approvalResults.forEach((r) => {
        approvalMap[r.id] = r.approvals;
      });
      setApprovalsByEntry(approvalMap);

      const retryResults = await Promise.all(
        history.history.map((e) =>
          getEntryRetryStatus(projectId, e.id)
            .then((r) => ({ id: e.id, status: r.retry_status }))
            .catch(() => ({ id: e.id, status: null })),
        ),
      );
      const retryMap: Record<number, RetryStatus | null> = {};
      retryResults.forEach((r) => {
        retryMap[r.id] = r.status;
      });
      setRetryByEntry(retryMap);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? "Failed to load publishing history"
          : "Failed to load publishing history",
      );
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) return <div className="page-loading">Loading publishing history…</div>;

  const renderRetry = (entry: ScheduledEntry) => {
    if (entry.status === "canceled") {
      return (
        <p className="media-asset-ref">
          <em>Entry was canceled before publishing.</em>
        </p>
      );
    }
    const retry = retryByEntry[entry.id];
    if (!retry || retry.total_attempts === 0) {
      if (FAILED_STATUSES.includes(entry.status)) {
        return <p className="media-error">Publishing failed.</p>;
      }
      return null;
    }
    const details = [
      `${retry.total_attempts} attempt(s)`,
      `${retry.successful} successful`,
      `${retry.failed} failed`,
    ];
    return (
      <div className="media-asset-ref">
        <strong>Retry / attempts:</strong> {details.join(" · ")}
        {retry.next_retry_at ? (
          <span className="text-muted">
            {" "}
            · next retry {formatUtc(retry.next_retry_at)}
          </span>
        ) : null}
        {retry.last_error ? (
          <div className="media-error">
            Last error: {retry.last_error}
            {retry.retry_reason ? ` — ${retry.retry_reason}` : ""}
          </div>
        ) : null}
        {entry.status === "upload_failed" && retry.retryable && (
          <p className="text-muted">Retry is available for this entry.</p>
        )}
      </div>
    );
  };

  const renderEntry = (entry: ScheduledEntry) => {
    const payload = entry.payload_snapshot ?? {};
    const approvals = approvalsByEntry[entry.id] ?? [];
    const last = latestApproval(approvals);
    return (
      <div key={entry.id} className="source-card">
        <div className="source-header">
          <span className="job-type">{entry.platform}</span>
          <span className={`state-badge ${statusClass(entry.status)}`}>
            {formatStatus(entry.status)}
          </span>
        </div>

        <div className="media-asset-ref">
          <strong>Scheduled:</strong> {formatUtc(entry.scheduled_utc)} (
          {entry.timezone || "UTC"})
        </div>
        {entry.provider_request_id ? (
          <div className="media-asset-ref">
            <strong>Provider request:</strong> {entry.provider_request_id}
          </div>
        ) : null}

        {/* Payload snapshot */}
        <div className="media-asset-ref">
          <strong>Payload snapshot:</strong>
        </div>
        <div className="payload-summary">
          {Object.keys(payload).length === 0 ? (
            <p className="text-muted">No payload snapshot recorded.</p>
          ) : (
            <ul>
              {Object.entries(payload).map(([key, value]) => (
                <li key={key}>
                  <strong>{key}:</strong> {formatPayloadEntry(value)}
                </li>
              ))}
            </ul>
          )}
        </div>

        {last ? (
          <div className="media-asset-ref">
            <strong>Approval ({formatStatus(last.decision)}):</strong>{" "}
            {formatUtc(last.granted_at)}
            {last.decision === "approve" && last.expires_at
              ? ` — expires ${formatUtc(last.expires_at)}`
              : ""}
            {last.reason ? ` — ${last.reason}` : ""}
          </div>
        ) : (
          <p className="media-asset-ref">
            <em>No approval recorded for this entry.</em>
          </p>
        )}

        {renderRetry(entry)}

        {user && (
          <div className="media-asset-ref">
            <strong>Entry</strong> #{entry.id} · updated{" "}
            {formatUtc(entry.updated_at)}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="page">
      <h1>Publish History</h1>
      <p>
        <Link className="back-link" to={`/projects/${projectId}`}>
          &larr; Back to Project
        </Link>
      </p>

      <p className="text-muted">
        Per-entry publication history: payload snapshot, approval, outcome, and
        retry/cancellation state.
      </p>

      {error && <div className="page-error">{error}</div>}

      {entries.length === 0 ? (
        <div className="empty-state">
          <p>No publishing history for this project yet.</p>
        </div>
      ) : (
        <div className="media-list">{entries.map(renderEntry)}</div>
      )}
    </div>
  );
}
