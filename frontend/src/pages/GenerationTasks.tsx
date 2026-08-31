import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  listJobs,
  cancelJob,
  retryJob,
  type AsyncJob,
} from "../api/jobs";
import { ApiError } from "../api/client";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function statusClass(status: string): string {
  if (status === "completed") return "state-approved";
  if (status === "failed") return "state-revision";
  if (status === "running" || status === "retrying") return "state-generating";
  if (status === "cancelled") return "state-draft";
  return "state-review";
}

function formatStatus(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function jobTypeLabel(t: string): string {
  const labels: Record<string, string> = {
    research_generation: "Research Generation",
    script_generation: "Script Generation",
    character_detection: "Character Detection",
    scene_media_generation: "Scene Media Generation",
    regeneration: "Scene Regeneration",
  };
  return labels[t] || t;
}

function formatDuration(start: string | null, end: string | null): string {
  if (!start) return "—";
  const startTime = new Date(start).getTime();
  const endTime = end ? new Date(end).getTime() : Date.now();
  const seconds = Math.floor((endTime - startTime) / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return `${minutes}m ${remaining}s`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function GenerationTasks() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);

  const [jobs, setJobs] = useState<AsyncJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Action states
  const [cancellingId, setCancellingId] = useState<number | null>(null);
  const [retryingId, setRetryingId] = useState<number | null>(null);

  // Expanded job detail
  const [expandedJob, setExpandedJob] = useState<number | null>(null);

  // ---- Data loading ----

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listJobs(projectId);
      setJobs(res.jobs);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setJobs([]);
      } else {
        setError("Failed to load jobs");
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) loadData();
  }, [projectId, loadData]);

  // Auto-refresh running jobs every 5 seconds
  useEffect(() => {
    const hasRunning = jobs.some(
      (j) => j.status === "running" || j.status === "retrying" || j.status === "pending",
    );
    if (!hasRunning) return;
    const interval = setInterval(() => loadData(), 5000);
    return () => clearInterval(interval);
  }, [jobs, loadData]);

  // ---- Actions ----

  const handleCancel = async (jobId: number) => {
    setCancellingId(jobId);
    setError(null);
    try {
      await cancelJob(jobId);
      await loadData();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Cancel failed");
    } finally {
      setCancellingId(null);
    }
  };

  const handleRetry = async (jobId: number) => {
    setRetryingId(jobId);
    setError(null);
    try {
      await retryJob(jobId);
      await loadData();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Retry failed");
    } finally {
      setRetryingId(null);
    }
  };

  // ---- Loading / empty ----

  if (loading) return <div className="page-loading">Loading generation tasks…</div>;

  // Group jobs by status
  const activeJobs = jobs.filter((j) => ["pending", "running", "retrying"].includes(j.status));
  const completedJobs = jobs.filter((j) => j.status === "completed");
  const failedJobs = jobs.filter((j) => j.status === "failed");
  const cancelledJobs = jobs.filter((j) => j.status === "cancelled");

  return (
    <div className="page">
      <h1>Generation Tasks</h1>
      <p>
        <Link to={`/projects/${projectId}`}>&larr; Back to Project</Link>
      </p>

      {error && <div className="page-error">{error}</div>}

      {/* ---- Active Jobs ---- */}
      <div className="detail-section">
        <h2>Active Jobs ({activeJobs.length})</h2>
        {activeJobs.length === 0 ? (
          <p className="text-muted">No active generation jobs.</p>
        ) : (
          <div className="job-list">
            {activeJobs.map((job) => (
              <div key={job.id} className="job-card job-active">
                <div
                  className="job-header"
                  onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
                >
                  <div className="job-title">
                    <span className="job-type">{jobTypeLabel(job.job_type)}</span>
                    <span className={`badge ${statusClass(job.status)}`}>
                      {formatStatus(job.status)}
                    </span>
                  </div>
                  <div className="job-meta">
                    <span className="job-progress">{job.progress}%</span>
                    <span className="job-expand">{expandedJob === job.id ? "▲" : "▼"}</span>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="job-progress-bar">
                  <div
                    className="job-progress-fill"
                    style={{ width: `${job.progress}%` }}
                  />
                </div>

                {expandedJob === job.id && (
                  <div className="job-detail">
                    <div className="job-attrs">
                      <div className="job-attr">
                        <strong>Owner:</strong> {job.owner_username}
                      </div>
                      <div className="job-attr">
                        <strong>Provider:</strong> {job.provider || "—"}
                      </div>
                      <div className="job-attr">
                        <strong>Cost:</strong>{" "}
                        {job.cost ? `${job.cost} ${job.cost_currency}` : "—"}
                      </div>
                      <div className="job-attr">
                        <strong>Retry:</strong> {job.retry_count}/{job.max_retries}
                      </div>
                      <div className="job-attr">
                        <strong>Duration:</strong> {formatDuration(job.started_at, null)}
                      </div>
                      <div className="job-attr">
                        <strong>Created:</strong>{" "}
                        {new Date(job.created_at).toLocaleString()}
                      </div>
                      {job.error_message && (
                        <div className="job-attr job-error">
                          <strong>Error:</strong> {job.error_message}
                        </div>
                      )}
                    </div>
                    <div className="job-actions">
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => handleCancel(job.id)}
                        disabled={cancellingId === job.id}
                      >
                        {cancellingId === job.id ? "Cancelling…" : "Cancel"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ---- Failed Jobs ---- */}
      {failedJobs.length > 0 && (
        <div className="detail-section">
          <h2>Failed Jobs ({failedJobs.length})</h2>
          <div className="job-list">
            {failedJobs.map((job) => (
              <div key={job.id} className="job-card job-failed">
                <div
                  className="job-header"
                  onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
                >
                  <div className="job-title">
                    <span className="job-type">{jobTypeLabel(job.job_type)}</span>
                    <span className={`badge ${statusClass(job.status)}`}>
                      {formatStatus(job.status)}
                    </span>
                  </div>
                  <div className="job-meta">
                    <span className="job-expand">{expandedJob === job.id ? "▲" : "▼"}</span>
                  </div>
                </div>

                {expandedJob === job.id && (
                  <div className="job-detail">
                    <div className="job-attrs">
                      <div className="job-attr">
                        <strong>Owner:</strong> {job.owner_username}
                      </div>
                      <div className="job-attr">
                        <strong>Provider:</strong> {job.provider || "—"}
                      </div>
                      <div className="job-attr">
                        <strong>Retry:</strong> {job.retry_count}/{job.max_retries}
                      </div>
                      <div className="job-attr">
                        <strong>Duration:</strong>{" "}
                        {formatDuration(job.started_at, job.completed_at)}
                      </div>
                      {job.error_message && (
                        <div className="job-attr job-error">
                          <strong>Error:</strong> {job.error_message}
                        </div>
                      )}
                    </div>
                    <div className="job-actions">
                      {job.retry_count < job.max_retries && (
                        <button
                          className="btn btn-sm"
                          onClick={() => handleRetry(job.id)}
                          disabled={retryingId === job.id}
                        >
                          {retryingId === job.id ? "Retrying…" : "Retry"}
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ---- Completed Jobs ---- */}
      <div className="detail-section">
        <h2>Completed Jobs ({completedJobs.length})</h2>
        {completedJobs.length === 0 ? (
          <p className="text-muted">No completed jobs yet.</p>
        ) : (
          <div className="job-list">
            {completedJobs.map((job) => (
              <div key={job.id} className="job-card job-completed">
                <div
                  className="job-header"
                  onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
                >
                  <div className="job-title">
                    <span className="job-type">{jobTypeLabel(job.job_type)}</span>
                    <span className={`badge ${statusClass(job.status)}`}>
                      {formatStatus(job.status)}
                    </span>
                  </div>
                  <div className="job-meta">
                    <span className="job-cost">
                      {job.cost ? `${job.cost} ${job.cost_currency}` : ""}
                    </span>
                    <span className="job-expand">{expandedJob === job.id ? "▲" : "▼"}</span>
                  </div>
                </div>

                {expandedJob === job.id && (
                  <div className="job-detail">
                    <div className="job-attrs">
                      <div className="job-attr">
                        <strong>Owner:</strong> {job.owner_username}
                      </div>
                      <div className="job-attr">
                        <strong>Provider:</strong> {job.provider || "—"}
                      </div>
                      <div className="job-attr">
                        <strong>Duration:</strong>{" "}
                        {formatDuration(job.started_at, job.completed_at)}
                      </div>
                      <div className="job-attr">
                        <strong>Completed:</strong>{" "}
                        {job.completed_at
                          ? new Date(job.completed_at).toLocaleString()
                          : "—"}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ---- Cancelled Jobs ---- */}
      {cancelledJobs.length > 0 && (
        <div className="detail-section">
          <h2>Cancelled Jobs ({cancelledJobs.length})</h2>
          <div className="job-list">
            {cancelledJobs.map((job) => (
              <div key={job.id} className="job-card job-cancelled">
                <div className="job-header">
                  <div className="job-title">
                    <span className="job-type">{jobTypeLabel(job.job_type)}</span>
                    <span className={`badge ${statusClass(job.status)}`}>
                      {formatStatus(job.status)}
                    </span>
                  </div>
                  <div className="job-meta">
                    <span className="text-muted">
                      {new Date(job.updated_at).toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ---- Refresh ---- */}
      <div className="detail-section">
        <h2>Actions</h2>
        <div className="action-buttons">
          <button className="btn" onClick={loadData}>
            Refresh
          </button>
        </div>
      </div>
    </div>
  );
}
