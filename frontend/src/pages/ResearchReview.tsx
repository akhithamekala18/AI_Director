import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getResearch,
  getResearchSources,
  getResearchGaps,
  generateResearch,
  approveResearch,
  requestResearchChanges,
  type Research,
  type ResearchSource,
  type ResearchGap,
} from "../api/research";
import { ApiError } from "../api/client";

function stateClass(state: string): string {
  if (state === "approved") return "state-approved";
  if (state === "revision_requested") return "state-revision";
  if (state === "generating") return "state-generating";
  if (state === "draft") return "state-draft";
  return "state-review";
}

function formatState(state: string): string {
  return state.replace(/_/g, " ").replace(/\w/g, (c) => c.toUpperCase());
}

export function ResearchReview() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);

  const [research, setResearch] = useState<Research | null>(null);
  const [sources, setSources] = useState<ResearchSource[]>([]);
  const [gaps, setGaps] = useState<ResearchGap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [approving, setApproving] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");
  const [submittingRejection, setSubmittingRejection] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [res, srcRes, gapRes] = await Promise.all([
        getResearch(projectId),
        getResearchSources(projectId).catch(() => ({ sources: [] as ResearchSource[] })),
        getResearchGaps(projectId).catch(() => ({ gaps: [] as ResearchGap[] })),
      ]);
      setResearch(res.research);
      setSources(srcRes.sources);
      setGaps(gapRes.gaps);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setResearch(null);
      } else {
        setError("Failed to load research");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (projectId) loadData();
  }, [projectId]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const res = await generateResearch(projectId);
      setResearch(res.research);
      await loadData();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) return <div className="page-loading">Loading research...</div>;

  return (
    <div className="page">
      <h1>Research Review</h1>
      <p>
        <Link to={"/projects/" + projectId}>&larr; Back to Project</Link>
      </p>
      {error && <div className="page-error">{error}</div>}

      {!research ? (
        <div className="detail-section">
          <p>No research found for this project.</p>
          <button className="btn" onClick={handleGenerate} disabled={generating}>
            {generating ? "Generating..." : "Generate Research"}
          </button>
        </div>
      ) : (
        <>
          <div className="detail-section">
            <h2>Research Status</h2>
            <span className={"badge " + stateClass(research.gate_state)}>
              {formatState(research.gate_state)}
            </span>
            <span className="text-muted" style={{ marginLeft: 12 }}>
              Version {research.version}
            </span>
            {research.approval_at && (
              <span className="text-muted" style={{ marginLeft: 12 }}>
                Approved by {research.approval_actor_username} at{" "}
                {new Date(research.approval_at).toLocaleString()}
              </span>
            )}
            {research.rejection_reason && (
              <p style={{ marginTop: 8, fontStyle: "italic" }}>
                Rejection reason: {research.rejection_reason}
              </p>
            )}
          </div>

          <div className="detail-section">
            <h2>Summary</h2>
            <div className="research-summary">{research.summary}</div>
          </div>

          <div className="detail-section">
            <h2>Sources ({sources.length})</h2>
            {sources.length === 0 ? (
              <p className="text-muted">No sources yet.</p>
            ) : (
              <div className="source-list">
                {sources.map((src) => (
                  <div key={src.id} className="source-card">
                    <div className="source-header">
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="source-title"
                      >
                        {src.title || src.url}
                      </a>
                      <span className="source-credibility">
                        Score: {(src.credibility_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    {src.snippet && (
                      <p className="source-snippet">{src.snippet}</p>
                    )}
                    <p className="source-url">{src.url}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="detail-section">
            <h2>Knowledge Gaps ({gaps.length})</h2>
            {gaps.length === 0 ? (
              <p className="text-muted">No gaps identified.</p>
            ) : (
              <div className="gap-list">
                {gaps.map((gap) => (
                  <div
                    key={gap.id}
                    className={
                      "gap-card" +
                      (gap.gap_type === "contradiction" ? " gap-contradiction" : "") +
                      (gap.gap_type === "missing" ? " gap-missing" : "")
                    }
                  >
                    <div className="gap-header">
                      <span className="gap-type">{gap.gap_type}</span>
                      <span className="gap-status">{formatState(gap.status)}</span>
                    </div>
                    <p className="gap-description">{gap.description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="detail-section">
            <h2>Actions</h2>
            <div className="action-buttons">
              <button
                className="btn"
                onClick={handleGenerate}
                disabled={generating}
              >
                {generating ? "Regenerating..." : "Regenerate"}
              </button>
              {(research.gate_state === "in_review" || research.gate_state === "revision_requested") && (
                <>
                  <button
                    className="btn btn-primary"
                    onClick={handleApprove}
                    disabled={approving}
                  >
                    {approving ? "Approving..." : "Approve"}
                  </button>
                  <form className="rejection-form" onSubmit={handleReject}>
                    <label htmlFor="rejection-reason">Rejection Reason</label>
                    <textarea
                      id="rejection-reason"
                      value={rejectionReason}
                      onChange={(e) => setRejectionReason(e.target.value)}
                      placeholder="Explain what needs to change..."
                      rows={3}
                    />
                    <div className="form-actions">
                      <button
                        type="submit"
                        className="btn btn-danger"
                        disabled={submittingRejection || !rejectionReason.trim()}
                      >
                        {submittingRejection ? "Submitting..." : "Request Changes"}
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
