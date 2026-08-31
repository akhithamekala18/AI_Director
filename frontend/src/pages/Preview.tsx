import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  listPreviews,
  generatePreview,
  approvePreview,
  rejectPreview,
  type PreviewAsset,
} from "../api/preview";
import { ApiError } from "../api/client";

// ---------------------------------------------------------------------------
// Preview states (backend: apps.preview.models.PreviewAsset — do not invent)
// status: pending | rendering | ready | failed
// approval_state: pending | approved | rejected
// ---------------------------------------------------------------------------

function statusClass(status: string): string {
  if (status === "ready") return "state-approved";
  if (status === "failed") return "state-revision";
  if (status === "rendering" || status === "pending") return "state-generating";
  return "state-review";
}

function approvalClass(state: string): string {
  if (state === "approved") return "state-approved";
  if (state === "rejected") return "state-revision";
  return "state-review";
}

function formatStatus(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function durationLabel(seconds: number): string {
  if (!seconds) return "—";
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function Preview() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);

  const [previews, setPreviews] = useState<PreviewAsset[]>([]);
  const [selected, setSelected] = useState<PreviewAsset | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [generating, setGenerating] = useState(false);
  const [platform, setPlatform] = useState("YouTube");
  const [actionId, setActionId] = useState<number | null>(null);
  const [rejectingId, setRejectingId] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [showReject, setShowReject] = useState(false);

  // Scene navigation surface (scene-by-scene)
  const [activeScene, setActiveScene] = useState(1);

  // ---- Data loading ----

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listPreviews(projectId);
      setPreviews(res.previews);
      setSelected((prev) => prev ?? res.previews[0] ?? null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setPreviews([]);
        setSelected(null);
      } else {
        setError("Failed to load previews");
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) loadData();
  }, [projectId, loadData]);

  // When a preview object updates via an API action, sync the selected view
  useEffect(() => {
    if (selected) {
      const fresh = previews.find((p) => p.id === selected.id);
      if (fresh) {
        setSelected(fresh);
        const count = Math.max(1, fresh.scene_count);
        setActiveScene((cur) => Math.min(cur, count));
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [previews]);

  // ---- Actions ----

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const res = await generatePreview(projectId, platform);
      setPreviews((prev) => {
        const next = prev.filter((p) => p.id !== res.preview.id);
        return [res.preview, ...next];
      });
      setSelected(res.preview);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `Preview generation failed: ${err.message}`
          : "Preview generation failed",
      );
    } finally {
      setGenerating(false);
    }
  };

  const handleApprove = async (p: PreviewAsset) => {
    setActionId(p.id);
    setError(null);
    try {
      const res = await approvePreview(projectId, p.id);
      setPreviews((prev) => prev.map((x) => (x.id === res.preview.id ? res.preview : x)));
    } catch (err) {
      setError(err instanceof ApiError ? `Approval failed: ${err.message}` : "Approval failed");
    } finally {
      setActionId(null);
    }
  };

  const handleReject = async (p: PreviewAsset) => {
    if (!rejectReason.trim()) {
      setError("A rejection reason is required");
      return;
    }
    setRejectingId(p.id);
    setError(null);
    try {
      const res = await rejectPreview(projectId, p.id, rejectReason.trim());
      setPreviews((prev) => prev.map((x) => (x.id === res.preview.id ? res.preview : x)));
      setShowReject(false);
      setRejectReason("");
    } catch (err) {
      setError(err instanceof ApiError ? `Rejection failed: ${err.message}` : "Rejection failed");
    } finally {
      setRejectingId(null);
    }
  };

  if (loading) return <div className="page-loading">Loading previews…</div>;

  const current = selected;

  return (
    <div className="page">
      <h1>Preview</h1>
      <p>
        <Link to={`/projects/${projectId}/video`}>&larr; Back to Video Status</Link>
      </p>

      {error && <div className="page-error">{error}</div>}

      {/* ---- Generate control ---- */}
      <div className="detail-section">
        <h2>Generate Preview</h2>
        <div className="action-buttons">
          <label htmlFor="preview-platform">Platform Target</label>
          <select
            id="preview-platform"
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
          >
            <option value="YouTube">YouTube</option>
            <option value="TikTok">TikTok</option>
            <option value="Instagram Reels">Instagram Reels</option>
            <option value="Instagram Feed">Instagram Feed</option>
            <option value="Twitter">Twitter</option>
            <option value="LinkedIn">LinkedIn</option>
          </select>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating ? "Generating…" : "Generate Preview"}
          </button>
        </div>
        <p className="text-muted">
          A preview requires a ready video and an approved scene package (Gate 4).
          Regenerating a preview resets its approval to pending.
        </p>
      </div>

      {previews.length === 0 ? (
        <div className="detail-section">
          <h2>No Previews</h2>
          <p className="text-muted">
            No preview has been generated yet. Generate a preview above.
          </p>
        </div>
      ) : (
        <div className="preview-layout">
          {/* ---- Preview list ---- */}
          <div className="detail-section preview-list-col">
            <h2>Previews ({previews.length})</h2>
            <div className="preview-select-list">
              {previews.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  className={`preview-select-item ${current?.id === p.id ? "active" : ""}`}
                  onClick={() => setSelected(p)}
                >
                  <span className="job-type">{p.platform_target || "Default"}</span>
                  <span className={`state-badge ${statusClass(p.status)}`}>
                    {formatStatus(p.status)}
                  </span>
                  <span className={`state-badge ${approvalClass(p.approval_state)}`}>
                    {formatStatus(p.approval_state)}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* ---- Player surface ---- */}
          {current && (
            <div className="detail-section preview-player-col">
              <div className="source-header">
                <h2 style={{ margin: 0, padding: 0, border: "none" }}>
                  {current.platform_target || "Default"} Preview
                </h2>
                <span className={`state-badge ${approvalClass(current.approval_state)}`}>
                  {formatStatus(current.approval_state)}
                </span>
              </div>

              {/* Platform-accurate surface frame */}
              <div
                className="preview-frame"
                style={{
                  aspectRatio: current.aspect_ratio === "9:16" ? "9/16" : "16/9",
                  maxWidth: current.aspect_ratio === "9:16" ? 360 : 720,
                }}
              >
                <div className="preview-frame-inner">
                  {current.status === "ready" ? (
                    <>
                      <p className="preview-placeholder">
                        Platform-accurate preview surface
                      </p>
                      <p className="media-asset-ref">
                        {current.resolution_width}×{current.resolution_height} ·{" "}
                        {current.aspect_ratio} · {durationLabel(current.duration_seconds)}
                      </p>
                      <p className="media-asset-ref">Asset: {current.asset_ref}</p>
                      <p className="media-asset-ref">Provider: {current.provider}</p>
                    </>
                  ) : current.status === "failed" ? (
                    <p className="media-error">
                      Preview failed: {current.error_message || "Unknown error"}
                    </p>
                  ) : (
                    <p className="text-muted">
                      Preview {formatStatus(current.status)}…
                    </p>
                  )}
                  <p className="text-muted preview-note">
                    Fake preview provider — asset metadata shown; no playable
                    stream is produced by the current backend provider.
                  </p>
                </div>
              </div>

              {/* Scene-by-scene navigation */}
              <div className="preview-scene-nav">
                <span className="text-muted">
                  Scene {activeScene} of {Math.max(1, current.scene_count)}
                </span>
                <div className="action-buttons">
                  <button
                    type="button"
                    className="btn btn-sm"
                    disabled={activeScene <= 1}
                    onClick={() => setActiveScene((s) => Math.max(1, s - 1))}
                  >
                    &larr; Prev
                  </button>
                  <button
                    type="button"
                    className="btn btn-sm"
                    disabled={activeScene >= Math.max(1, current.scene_count)}
                    onClick={() =>
                      setActiveScene((s) =>
                        Math.min(Math.max(1, current.scene_count), s + 1),
                      )
                    }
                  >
                    Next &rarr;
                  </button>
                </div>
              </div>

              {/* Approval workflow — only when ready and not already approved */}
              {current.status === "ready" && current.approval_state !== "approved" && (
                <div className="preview-approval">
                  <h3>Approval</h3>
                  {showReject ? (
                    <div className="rejection-form">
                      <label htmlFor={`reject-${current.id}`}>Reason for rejection</label>
                      <textarea
                        id={`reject-${current.id}`}
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        placeholder="Required — explain what needs to change"
                      />
                      <div className="form-actions">
                        <button
                          type="button"
                          className="btn btn-primary"
                          onClick={() => handleReject(current)}
                          disabled={rejectingId === current.id}
                        >
                          {rejectingId === current.id ? "Rejecting…" : "Reject Preview"}
                        </button>
                        <button
                          type="button"
                          className="btn"
                          onClick={() => {
                            setShowReject(false);
                            setRejectReason("");
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="action-buttons">
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => handleApprove(current)}
                        disabled={actionId === current.id}
                      >
                        {actionId === current.id ? "Approving…" : "Approve Preview"}
                      </button>
                      <button
                        type="button"
                        className="btn btn-danger"
                        onClick={() => setShowReject(true)}
                      >
                        Reject Preview
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
