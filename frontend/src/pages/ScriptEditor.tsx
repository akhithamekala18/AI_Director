import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getScript,
  generateScript,
  approveScript,
  requestScriptChanges,
  type Script,
} from "../api/script";
import { ApiError } from "../api/client";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function stateClass(state: string): string {
  if (state === "approved") return "state-approved";
  if (state === "revision_requested") return "state-revision";
  if (state === "generating") return "state-generating";
  if (state === "draft") return "state-draft";
  return "state-review";
}

function formatState(state: string): string {
  return state.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// Revision snapshot (kept locally for compare)
// ---------------------------------------------------------------------------

interface RevisionSnapshot {
  version: number;
  title: string;
  outline: string;
  script: string;
  narration: string;
  scenes: string[];
  captions: string[];
  hashtags: string[];
  capturedAt: string;
  actor: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ScriptEditor() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);

  // Script data
  const [script, setScript] = useState<Script | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Action states
  const [generating, setGenerating] = useState(false);
  const [approving, setApproving] = useState(false);
  const [submittingRejection, setSubmittingRejection] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");

  // Editable fields (title and outline are editable per §20.1.3)
  const [editTitle, setEditTitle] = useState("");
  const [editOutline, setEditOutline] = useState("");
  const [editDirty, setEditDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  // Revision history for compare
  const [revisions, setRevisions] = useState<RevisionSnapshot[]>([]);
  const [compareIndex, setCompareIndex] = useState<number | null>(null);
  const [showCompare, setShowCompare] = useState(false);

  // ---- Data loading ----

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getScript(projectId);
      setScript(res.script);
      setEditTitle(res.script.title);
      setEditOutline(res.script.outline);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setScript(null);
      } else {
        setError("Failed to load script");
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) loadData();
  }, [projectId, loadData]);

  // ---- Capture revision snapshot on load if script exists and is approved/revision_requested ----

  const captureRevision = useCallback(
    (s: Script) => {
      const snapshot: RevisionSnapshot = {
        version: s.version,
        title: s.title,
        outline: s.outline,
        script: s.script,
        narration: s.narration,
        scenes: s.scenes,
        captions: s.captions,
        hashtags: s.hashtags,
        capturedAt: new Date().toISOString(),
        actor: s.approval_actor_username ?? "system",
      };
      setRevisions((prev) => {
        // Avoid duplicates for the same version
        if (prev.length > 0 && prev[prev.length - 1].version === s.version) {
          return prev;
        }
        return [...prev, snapshot];
      });
    },
    [],
  );

  // Capture when script loads and is in review/approved state
  useEffect(() => {
    if (script && (script.gate_state === "review" || script.gate_state === "approved")) {
      captureRevision(script);
    }
  }, [script, captureRevision]);

  // ---- Actions ----

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const res = await generateScript(projectId);
      setScript(res.script);
      setEditTitle(res.script.title);
      setEditOutline(res.script.outline);
      setEditDirty(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  };

  const handleApprove = async () => {
    setApproving(true);
    setError(null);
    try {
      const res = await approveScript(projectId);
      setScript(res.script);
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
      const res = await requestScriptChanges(projectId, rejectionReason);
      setScript(res.script);
      setRejectionReason("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Rejection failed");
    } finally {
      setSubmittingRejection(false);
    }
  };

  const handleSaveEdits = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!script) return;
    setSaving(true);
    setError(null);
    try {
      // The backend currently does not support PATCH on script title/outline;
      // this is a client-side edit that will be sent once the backend exposes
      // the endpoint. For now we persist locally and show the updated values.
      setScript({ ...script, title: editTitle, outline: editOutline });
      setEditDirty(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  // ---- Compare ----

  const handleCompare = (index: number) => {
    setCompareIndex(index);
    setShowCompare(true);
  };

  const closeCompare = () => {
    setShowCompare(false);
    setCompareIndex(null);
  };

  // ---- Loading / empty ----

  if (loading) return <div className="page-loading">Loading script…</div>;

  return (
    <div className="page">
      <h1>Script Package Editor</h1>
      <p>
        <Link to={`/projects/${projectId}`}>&larr; Back to Project</Link>
      </p>

      {error && <div className="page-error">{error}</div>}

      {!script ? (
        <div className="detail-section">
          <p>No script found for this project.</p>
          <button className="btn" onClick={handleGenerate} disabled={generating}>
            {generating ? "Generating…" : "Generate Script"}
          </button>
        </div>
      ) : (
        <>
          {/* ---- Status ---- */}
          <div className="detail-section">
            <h2>Script Status</h2>
            <div className="script-status-row">
              <span className={`badge ${stateClass(script.gate_state)}`}>
                {formatState(script.gate_state)}
              </span>
              <span className="text-muted" style={{ marginLeft: 12 }}>
                Version {script.version}
              </span>
              {script.approval_at && (
                <span className="text-muted" style={{ marginLeft: 12 }}>
                  Approved by {script.approval_actor_username} at{" "}
                  {new Date(script.approval_at).toLocaleString()}
                </span>
              )}
            </div>
            {script.rejection_reason && (
              <p className="script-rejection-reason">
                Rejection reason: {script.rejection_reason}
              </p>
            )}
          </div>

          {/* ---- Editable fields (title / outline) ---- */}
          <div className="detail-section">
            <h2>Script Package</h2>
            <form onSubmit={handleSaveEdits} className="script-edit-form">
              <div className="script-field">
                <label htmlFor="script-title">Title</label>
                <input
                  id="script-title"
                  type="text"
                  value={editTitle}
                  onChange={(e) => {
                    setEditTitle(e.target.value);
                    setEditDirty(true);
                  }}
                  disabled={script.gate_state !== "review" && script.gate_state !== "revision_requested"}
                  placeholder="Working title…"
                />
              </div>

              <div className="script-field">
                <label htmlFor="script-outline">Outline</label>
                <textarea
                  id="script-outline"
                  value={editOutline}
                  onChange={(e) => {
                    setEditOutline(e.target.value);
                    setEditDirty(true);
                  }}
                  disabled={script.gate_state !== "review" && script.gate_state !== "revision_requested"}
                  placeholder="Outline / structure…"
                  rows={6}
                />
              </div>

              {editDirty && (
                <div className="form-actions">
                  <button type="submit" className="btn btn-primary" disabled={saving}>
                    {saving ? "Saving…" : "Save Edits"}
                  </button>
                </div>
              )}
            </form>
          </div>

          {/* ---- Script body (read-only) ---- */}
          <div className="detail-section">
            <h2>Script</h2>
            <div className="script-body">{script.script || <span className="text-muted">No script body yet.</span>}</div>
          </div>

          {/* ---- Narration (read-only) ---- */}
          <div className="detail-section">
            <h2>Narration</h2>
            <div className="script-body">{script.narration || <span className="text-muted">No narration yet.</span>}</div>
          </div>

          {/* ---- Scenes ---- */}
          <div className="detail-section">
            <h2>Scenes ({script.scenes?.length ?? 0})</h2>
            {(!script.scenes || script.scenes.length === 0) ? (
              <p className="text-muted">No scenes yet.</p>
            ) : (
              <div className="script-scenes">
                {script.scenes.map((scene, idx) => (
                  <div key={idx} className="scene-card">
                    <span className="scene-number">Scene {idx + 1}</span>
                    <p className="scene-text">{scene}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ---- Captions ---- */}
          <div className="detail-section">
            <h2>Captions ({script.captions?.length ?? 0})</h2>
            {(!script.captions || script.captions.length === 0) ? (
              <p className="text-muted">No captions yet.</p>
            ) : (
              <ul className="script-list">
                {script.captions.map((cap, idx) => (
                  <li key={idx}>{cap}</li>
                ))}
              </ul>
            )}
          </div>

          {/* ---- Hashtags ---- */}
          <div className="detail-section">
            <h2>Hashtags ({script.hashtags?.length ?? 0})</h2>
            {(!script.hashtags || script.hashtags.length === 0) ? (
              <p className="text-muted">No hashtags yet.</p>
            ) : (
              <div className="hashtag-list">
                {script.hashtags.map((tag, idx) => (
                  <span key={idx} className="hashtag-badge">{tag}</span>
                ))}
              </div>
            )}
          </div>

          {/* ---- Actions (Gate 2) ---- */}
          <div className="detail-section">
            <h2>Actions</h2>
            <div className="action-buttons">
              <button
                className="btn"
                onClick={handleGenerate}
                disabled={generating || script.gate_state === "generating"}
              >
                {generating || script.gate_state === "generating" ? "Generating…" : "Regenerate"}
              </button>

              {(script.gate_state === "review" || script.gate_state === "revision_requested") && (
                <>
                  <button
                    className="btn btn-primary"
                    onClick={handleApprove}
                    disabled={approving}
                  >
                    {approving ? "Approving…" : "Approve Script"}
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

          {/* ---- Revision History ---- */}
          {revisions.length > 0 && (
            <div className="detail-section">
              <h2>Revision History ({revisions.length})</h2>
              <div className="revision-list">
                {revisions.map((rev, idx) => (
                  <div key={idx} className="revision-card">
                    <div className="revision-header">
                      <span className="revision-version">v{rev.version}</span>
                      <span className="text-muted">
                        {new Date(rev.capturedAt).toLocaleString()}
                      </span>
                      <span className="text-muted">by {rev.actor}</span>
                      <button
                        className="btn btn-sm"
                        onClick={() => handleCompare(idx)}
                      >
                        Compare
                      </button>
                    </div>
                    <div className="revision-preview">
                      <strong>{rev.title || "(untitled)"}</strong>
                      <span className="text-muted">
                        {" "}
                        — {rev.scenes.length} scenes, {rev.captions.length} captions
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ---- Compare Modal ---- */}
          {showCompare && compareIndex !== null && script && (
            <div className="compare-overlay" onClick={closeCompare}>
              <div className="compare-modal" onClick={(e) => e.stopPropagation()}>
                <div className="compare-header">
                  <h2>
                    Compare: v{revisions[compareIndex].version} → v{script.version}
                  </h2>
                  <button className="btn btn-sm" onClick={closeCompare}>
                    Close
                  </button>
                </div>
                <div className="compare-grid">
                  <div className="compare-column">
                    <h3>v{revisions[compareIndex].version}</h3>
                    <div className="compare-field">
                      <strong>Title:</strong> {revisions[compareIndex].title || "(empty)"}
                    </div>
                    <div className="compare-field">
                      <strong>Outline:</strong>
                      <pre>{revisions[compareIndex].outline || "(empty)"}</pre>
                    </div>
                    <div className="compare-field">
                      <strong>Script:</strong>
                      <pre>{revisions[compareIndex].script || "(empty)"}</pre>
                    </div>
                    <div className="compare-field">
                      <strong>Scenes:</strong> {revisions[compareIndex].scenes.length}
                    </div>
                  </div>
                  <div className="compare-column">
                    <h3>v{script.version} (current)</h3>
                    <div className="compare-field">
                      <strong>Title:</strong> {script.title || "(empty)"}
                    </div>
                    <div className="compare-field">
                      <strong>Outline:</strong>
                      <pre>{script.outline || "(empty)"}</pre>
                    </div>
                    <div className="compare-field">
                      <strong>Script:</strong>
                      <pre>{script.script || "(empty)"}</pre>
                    </div>
                    <div className="compare-field">
                      <strong>Scenes:</strong> {script.scenes?.length ?? 0}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
