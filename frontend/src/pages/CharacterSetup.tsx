import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getCharacter,
  generateCharacter,
  approveCharacter,
  requestCharacterChanges,
  getCharacterLibrary,
  reuseCharacter,
  type CharacterEntry,
  type LibraryCharacter,
} from "../api/character";
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

export function CharacterSetup() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);

  // Character set data
  const [characterSet, setCharacterSet] = useState<{
    id: number;
    characters: CharacterEntry[];
    gate_state: string;
    version: number;
    character_count: number;
    rejection_reason: string | null;
    approval_actor_username: string | null;
    approval_at: string | null;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Action states
  const [generating, setGenerating] = useState(false);
  const [approving, setApproving] = useState(false);
  const [submittingRejection, setSubmittingRejection] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");

  // Library
  const [library, setLibrary] = useState<LibraryCharacter[]>([]);
  const [libraryLoading, setLibraryLoading] = useState(false);

  // Reuse
  const [reuseTarget, setReuseTarget] = useState<number | null>(null);
  const [reusing, setReusing] = useState(false);
  const [showReusePicker, setShowReusePicker] = useState(false);

  // Expanded character detail
  const [expandedChar, setExpandedChar] = useState<string | null>(null);

  // ---- Data loading ----

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getCharacter(projectId);
      setCharacterSet(res.character);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setCharacterSet(null);
      } else {
        setError("Failed to load characters");
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const loadLibrary = useCallback(async () => {
    setLibraryLoading(true);
    try {
      const res = await getCharacterLibrary(projectId);
      setLibrary(res.library);
    } catch {
      // Library endpoint may not exist yet; gracefully degrade
      setLibrary([]);
    } finally {
      setLibraryLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) {
      loadData();
      loadLibrary();
    }
  }, [projectId, loadData, loadLibrary]);

  // ---- Actions ----

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const res = await generateCharacter(projectId);
      setCharacterSet(res.character);
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
      const res = await approveCharacter(projectId);
      setCharacterSet(res.character);
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
      const res = await requestCharacterChanges(projectId, rejectionReason);
      setCharacterSet(res.character);
      setRejectionReason("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Rejection failed");
    } finally {
      setSubmittingRejection(false);
    }
  };

  const handleReuse = async (libraryEntryId: number) => {
    setReusing(true);
    setError(null);
    try {
      const res = await reuseCharacter(projectId, libraryEntryId);
      setCharacterSet(res.character);
      setShowReusePicker(false);
      setReuseTarget(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reuse failed");
    } finally {
      setReusing(false);
    }
  };

  // ---- Loading / empty ----

  if (loading) return <div className="page-loading">Loading characters…</div>;

  return (
    <div className="page">
      <h1>Character Setup & Library</h1>
      <p>
        <Link to={`/projects/${projectId}`}>&larr; Back to Project</Link>
      </p>

      {error && <div className="page-error">{error}</div>}

      {!characterSet ? (
        <div className="detail-section">
          <p>No characters found for this project.</p>
          <button className="btn" onClick={handleGenerate} disabled={generating}>
            {generating ? "Detecting Characters…" : "Detect Characters"}
          </button>
        </div>
      ) : (
        <>
          {/* ---- Status ---- */}
          <div className="detail-section">
            <h2>Character Status</h2>
            <div className="char-status-row">
              <span className={`badge ${stateClass(characterSet.gate_state)}`}>
                {formatState(characterSet.gate_state)}
              </span>
              <span className="text-muted" style={{ marginLeft: 12 }}>
                Version {characterSet.version}
              </span>
              <span className="text-muted" style={{ marginLeft: 12 }}>
                {characterSet.character_count} character{characterSet.character_count !== 1 ? "s" : ""} detected
              </span>
              {characterSet.approval_at && (
                <span className="text-muted" style={{ marginLeft: 12 }}>
                  Approved by {characterSet.approval_actor_username} at{" "}
                  {new Date(characterSet.approval_at).toLocaleString()}
                </span>
              )}
            </div>
            {characterSet.rejection_reason && (
              <p className="char-rejection-reason">
                Rejection reason: {characterSet.rejection_reason}
              </p>
            )}
          </div>

          {/* ---- Detected Characters ---- */}
          <div className="detail-section">
            <h2>Detected Characters ({characterSet.characters?.length ?? 0})</h2>
            {(!characterSet.characters || characterSet.characters.length === 0) ? (
              <p className="text-muted">No characters detected yet. Generate to detect from the approved script.</p>
            ) : (
              <div className="char-list">
                {characterSet.characters.map((char) => (
                  <div key={char.id} className="char-card">
                    <div
                      className="char-card-header"
                      onClick={() => setExpandedChar(expandedChar === char.id ? null : char.id)}
                    >
                      <div className="char-card-title">
                        <span className="char-name">{char.name || `Character ${char.id}`}</span>
                        <span className="char-id">ID: {char.id}</span>
                      </div>
                      <div className="char-card-meta">
                        {char.gender && <span className="char-badge">{char.gender}</span>}
                        {char.age && <span className="char-badge">{char.age}</span>}
                        <span className="char-expand">{expandedChar === char.id ? "▲" : "▼"}</span>
                      </div>
                    </div>

                    {expandedChar === char.id && (
                      <div className="char-detail">
                        <div className="char-attrs">
                          <div className="char-attr">
                            <strong>Age:</strong> {char.age || "—"}
                          </div>
                          <div className="char-attr">
                            <strong>Gender:</strong> {char.gender || "—"}
                          </div>
                          <div className="char-attr">
                            <strong>Appearance:</strong> {formatObject(char.appearance)}
                          </div>
                          <div className="char-attr">
                            <strong>Clothing:</strong> {formatObject(char.clothing)}
                          </div>
                          <div className="char-attr">
                            <strong>Accessories:</strong>{" "}
                            {char.accessories && char.accessories.length > 0
                              ? char.accessories.join(", ")
                              : "—"}
                          </div>
                          <div className="char-attr">
                            <strong>Style:</strong> {formatObject(char.style)}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ---- Actions (Gate 3) ---- */}
          <div className="detail-section">
            <h2>Actions</h2>
            <div className="action-buttons">
              <button
                className="btn"
                onClick={handleGenerate}
                disabled={generating || characterSet.gate_state === "generating"}
              >
                {generating || characterSet.gate_state === "generating"
                  ? "Detecting…"
                  : "Re-detect Characters"}
              </button>

              <button
                className="btn"
                onClick={() => setShowReusePicker(!showReusePicker)}
                disabled={characterSet.gate_state === "generating"}
              >
                Reuse from Library
              </button>

              {(characterSet.gate_state === "review" ||
                characterSet.gate_state === "revision_requested") && (
                <>
                  <button
                    className="btn btn-primary"
                    onClick={handleApprove}
                    disabled={approving}
                  >
                    {approving ? "Approving…" : "Approve Characters"}
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

          {/* ---- Reuse Picker ---- */}
          {showReusePicker && (
            <div className="detail-section">
              <h2>Library Characters</h2>
              {libraryLoading ? (
                <p className="text-muted">Loading library…</p>
              ) : library.length === 0 ? (
                <p className="text-muted">No library characters available yet.</p>
              ) : (
                <div className="library-list">
                  {library.map((libChar) => (
                    <div key={libChar.id} className="library-card">
                      <div className="library-card-header">
                        <span className="library-name">{libChar.name || libChar.character_id}</span>
                        <span className="library-version">v{libChar.version}</span>
                      </div>
                      <div className="library-meta">
                        {libChar.gender && <span className="char-badge">{libChar.gender}</span>}
                        {libChar.age && <span className="char-badge">{libChar.age}</span>}
                      </div>
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={() => handleReuse(libChar.id)}
                        disabled={reusing}
                      >
                        {reusing && reuseTarget === libChar.id ? "Reusing…" : "Use This Character"}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ---- Character Library (team-level) ---- */}
          <div className="detail-section">
            <h2>Team Character Library ({library.length})</h2>
            {library.length === 0 ? (
              <p className="text-muted">
                No characters saved to the team library yet. Approve characters to save them.
              </p>
            ) : (
              <div className="library-list">
                {library.map((libChar) => (
                  <div key={libChar.id} className="library-card">
                    <div className="library-card-header">
                      <span className="library-name">{libChar.name || libChar.character_id}</span>
                      <span className="library-version">v{libChar.version}</span>
                    </div>
                    <div className="library-meta">
                      {libChar.gender && <span className="char-badge">{libChar.gender}</span>}
                      {libChar.age && <span className="char-badge">{libChar.age}</span>}
                      {libChar.origin_project && (
                        <span className="text-muted">Origin: project #{libChar.origin_project}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
