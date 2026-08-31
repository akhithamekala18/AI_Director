import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getScene,
  buildScenes,
  approveScene,
  requestSceneChanges,
  type SceneEntry,
} from "../api/scene";
import { ApiError } from "../api/client";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function stateClass(state: string): string {
  if (state === "approved") return "state-approved";
  if (state === "revision_requested") return "state-revision";
  if (state === "draft") return "state-draft";
  return "state-review";
}

function formatState(state: string): string {
  return state.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatObject(obj: Record<string, unknown> | undefined | null): string {
  if (!obj || Object.keys(obj).length === 0) return "—";
  return Object.entries(obj)
    .map(([k, v]) => {
      if (typeof v === "object" && v !== null) {
        return `${k}: ${JSON.stringify(v)}`;
      }
      return `${k}: ${String(v)}`;
    })
    .join(", ");
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SceneBuilderPage() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);

  // Scene builder data
  const [builder, setBuilder] = useState<{
    id: number;
    scenes: SceneEntry[];
    gate_state: string;
    version: number;
    scene_count: number;
    rejection_reason: string | null;
    approval_actor_username: string | null;
    approval_at: string | null;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Action states
  const [building, setBuilding] = useState(false);
  const [approving, setApproving] = useState(false);
  const [submittingRejection, setSubmittingRejection] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");

  // Expanded scene detail
  const [expandedScene, setExpandedScene] = useState<string | null>(null);

  // ---- Data loading ----

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getScene(projectId);
      setBuilder(res.scene);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setBuilder(null);
      } else {
        setError("Failed to load scene package");
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) loadData();
  }, [projectId, loadData]);

  // ---- Actions ----

  const handleBuild = async () => {
    setBuilding(true);
    setError(null);
    try {
      const res = await buildScenes(projectId);
      setBuilder(res.scene);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Build failed");
    } finally {
      setBuilding(false);
    }
  };

  const handleApprove = async () => {
    setApproving(true);
    setError(null);
    try {
      const res = await approveScene(projectId);
      setBuilder(res.scene);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Approval failed");
    } finally {
      setApproving(false);
    }
  };

  const handleReject = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingRejection(true);
    setError(null);
    try {
      const res = await requestSceneChanges(projectId, rejectionReason);
      setBuilder(res.scene);
      setRejectionReason("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Rejection failed");
    } finally {
      setSubmittingRejection(false);
    }
  };

  // ---- Loading / empty ----

  if (loading) return <div className="page-loading">Loading scene package…</div>;

  return (
    <div className="page">
      <h1>Scene Builder</h1>
      <p>
        <Link to={`/projects/${projectId}`}>&larr; Back to Project</Link>
      </p>

      {error && <div className="page-error">{error}</div>}

      {!builder ? (
        <div className="detail-section">
          <p>No scene package found for this project.</p>
          <button className="btn" onClick={handleBuild} disabled={building}>
            {building ? "Building Scenes…" : "Build Scenes"}
          </button>
        </div>
      ) : (
        <>
          {/* ---- Status ---- */}
          <div className="detail-section">
            <h2>Scene Package Status</h2>
            <div className="scene-status-row">
              <span className={`badge ${stateClass(builder.gate_state)}`}>
                {formatState(builder.gate_state)}
              </span>
              <span className="text-muted" style={{ marginLeft: 12 }}>
                Version {builder.version}
              </span>
              <span className="text-muted" style={{ marginLeft: 12 }}>
                {builder.scene_count} scene{builder.scene_count !== 1 ? "s" : ""}
              </span>
              {builder.approval_at && (
                <span className="text-muted" style={{ marginLeft: 12 }}>
                  Approved by {builder.approval_actor_username} at{" "}
                  {new Date(builder.approval_at).toLocaleString()}
                </span>
              )}
            </div>
            {builder.rejection_reason && (
              <p className="scene-rejection-reason">
                Rejection reason: {builder.rejection_reason}
              </p>
            )}
          </div>

          {/* ---- Scene Timeline ---- */}
          <div className="detail-section">
            <h2>Scene Timeline ({builder.scenes?.length ?? 0})</h2>
            {(!builder.scenes || builder.scenes.length === 0) ? (
              <p className="text-muted">
                No scenes built yet. Build scenes from the approved script and characters.
              </p>
            ) : (
              <div className="scene-timeline">
                {builder.scenes
                  .slice()
                  .sort((a, b) => a.order - b.order)
                  .map((scene) => (
                    <div key={scene.id} className="scene-timeline-card">
                      <div
                        className="scene-timeline-header"
                        onClick={() =>
                          setExpandedScene(expandedScene === scene.id ? null : scene.id)
                        }
                      >
                        <div className="scene-timeline-title">
                          <span className="scene-order">#{scene.order}</span>
                          <span className="scene-heading">
                            {scene.heading || `Scene ${scene.order}`}
                          </span>
                        </div>
                        <div className="scene-timeline-meta">
                          {scene.duration_seconds > 0 && (
                            <span className="scene-duration">
                              {scene.duration_seconds}s
                            </span>
                          )}
                          {scene.characters.length > 0 && (
                            <span className="scene-characters-badge">
                              {scene.characters.length} character{scene.characters.length !== 1 ? "s" : ""}
                            </span>
                          )}
                          {scene.transition && scene.transition !== "none" && (
                            <span className="scene-transition-badge">
                              {scene.transition}
                            </span>
                          )}
                          <span className="scene-expand">
                            {expandedScene === scene.id ? "▲" : "▼"}
                          </span>
                        </div>
                      </div>

                      {expandedScene === scene.id && (
                        <div className="scene-detail">
                          <div className="scene-attrs">
                            <div className="scene-attr">
                              <strong>Narration:</strong>
                              <div className="scene-narration">{scene.narration || "—"}</div>
                            </div>
                            <div className="scene-attr">
                              <strong>Visual Direction:</strong>
                              <div className="scene-visual">{scene.visual_direction || "—"}</div>
                            </div>
                            <div className="scene-attr">
                              <strong>Characters:</strong>{" "}
                              {scene.characters.length > 0
                                ? scene.characters.join(", ")
                                : "—"}
                            </div>
                            <div className="scene-attr">
                              <strong>Pacing:</strong> {scene.pacing || "—"}
                            </div>
                            <div className="scene-attr">
                              <strong>Transition:</strong> {scene.transition || "—"}
                            </div>
                            <div className="scene-attr">
                              <strong>Duration:</strong>{" "}
                              {scene.duration_seconds > 0
                                ? `${scene.duration_seconds} seconds`
                                : "—"}
                            </div>
                            {scene.metadata && Object.keys(scene.metadata).length > 0 && (
                              <div className="scene-attr">
                                <strong>Metadata:</strong> {formatObject(scene.metadata)}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            )}
          </div>

          {/* ---- Actions (Gate 4) ---- */}
          <div className="detail-section">
            <h2>Actions</h2>
            <div className="action-buttons">
              <button
                className="btn"
                onClick={handleBuild}
                disabled={building}
              >
                {building ? "Building…" : "Re-build Scenes"}
              </button>

              {(builder.gate_state === "review" ||
                builder.gate_state === "revision_requested") && (
                <>
                  <button
                    className="btn btn-primary"
                    onClick={handleApprove}
                    disabled={approving}
                  >
                    {approving ? "Approving…" : "Approve Scenes"}
                  </button>

                  <form className="rejection-form" onSubmit={handleReject}>
                    <label htmlFor="rejection-reason">Rejection Reason</label>
                    <textarea
                      id="rejection-reason"
                      value={rejectionReason}
                      onChange={(e) => setRejectionReason(e.target.value)}
                      placeholder="Explain what needs to change…"
                      rows={3}
                    />
                    <div className="form-actions">
                      <button
                        type="submit"
                        className="btn btn-danger"
                        disabled={submittingRejection || !rejectionReason.trim()}
                      >
                        {submittingRejection ? "Submitting…" : "Request Changes"}
                      </button>
                    </div>
                  </form>
                </>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
