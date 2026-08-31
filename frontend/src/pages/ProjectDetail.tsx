import { useEffect, useState, type FormEvent } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  getProject,
  patchProject,
  archiveProject,
  duplicateProject,
  transitionProject,
  type Project,
} from "../api/projects";
import { ApiError } from "../api/client";

// All lifecycle states from the backend enum
const LIFECYCLE_STATES = [
  "Draft",
  "Researching",
  "Research Approved",
  "Scripting",
  "Script Approved",
  "Producing",
  "Video Approved",
  "Scheduled",
  "Published",
  "Archived",
];

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit state — only sent fields are PATCHed
  const [editTopic, setEditTopic] = useState("");
  const [editPlatform, setEditPlatform] = useState("");
  const [editFormat, setEditFormat] = useState("");
  const [editDirty, setEditDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  // Lifecycle
  const [transitionTarget, setTransitionTarget] = useState("");
  const [transitioning, setTransitioning] = useState(false);

  const projectId = Number(id);

  // Load project
  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    getProject(projectId)
      .then((res) => {
        setProject(res.project);
        setEditTopic(res.project.topic);
        setEditPlatform(res.project.platform_target);
        setEditFormat(res.project.format);
      })
      .catch((err) => {
        if (err instanceof ApiError) {
          setError(err.status === 404 ? "Project not found" : "Failed to load project");
        } else {
          setError("Failed to load project");
        }
      })
      .finally(() => setLoading(false));
  }, [projectId]);

  // PATCH — only send fields the user actually changed
  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    if (!project) return;
    setSaving(true);
    setError(null);

    try {
      // Only include fields that differ from original
      const payload: { topic?: string; platform_target?: string; format?: string } = {};
      if (editTopic.trim() !== project.topic) {
        payload.topic = editTopic.trim();
      }
      if (editPlatform !== project.platform_target) {
        payload.platform_target = editPlatform;
      }
      if (editFormat !== project.format) {
        payload.format = editFormat;
      }

      // Only PATCH if something changed
      if (Object.keys(payload).length > 0) {
        const res = await patchProject(projectId, payload);
        setProject(res.project);
        setEditDirty(false);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        const data = err.data as Record<string, unknown>;
        setError(typeof data.detail === "string" ? data.detail : "Update failed");
      } else {
        setError("Update failed");
      }
    } finally {
      setSaving(false);
    }
  };

  // Lifecycle transition
  const handleTransition = async () => {
    if (!transitionTarget || !project) return;
    setTransitioning(true);
    setError(null);
    try {
      const res = await transitionProject(projectId, transitionTarget);
      setProject(res.project);
      setTransitionTarget("");
    } catch (err) {
      if (err instanceof ApiError) {
        const data = err.data as Record<string, unknown>;
        setError(typeof data.detail === "string" ? data.detail : "Transition failed");
      } else {
        setError("Transition failed");
      }
    } finally {
      setTransitioning(false);
    }
  };

  // Archive
  const handleArchive = async () => {
    if (!project) return;
    if (!confirm("Archive this project?")) return;
    setTransitioning(true);
    setError(null);
    try {
      const res = await archiveProject(projectId);
      setProject(res.project);
    } catch (err) {
      if (err instanceof ApiError) {
        setError("Archive failed");
      } else {
        setError("Archive failed");
      }
    } finally {
      setTransitioning(false);
    }
  };

  // Duplicate
  const handleDuplicate = async () => {
    if (!project) return;
    setTransitioning(true);
    setError(null);
    try {
      const res = await duplicateProject(projectId);
      navigate(`/projects/${res.project.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError("Duplicate failed");
      } else {
        setError("Duplicate failed");
      }
    } finally {
      setTransitioning(false);
    }
  };

  if (loading) return <div className="page-loading">Loading project…</div>;
  if (error && !project) return <div className="page-error">{error}</div>;
  if (!project) return <div className="page-error">Project not found</div>;

  // Valid transitions: Draft→Researching, Researching→Research Approved, etc.
  const currentIdx = LIFECYCLE_STATES.indexOf(project.lifecycle_state);
  const validNextStates =
    project.lifecycle_state === "Draft"
      ? LIFECYCLE_STATES.slice(0, 2) // Draft → Researching
      : currentIdx >= 0 && currentIdx < LIFECYCLE_STATES.length - 2
        ? LIFECYCLE_STATES.slice(currentIdx, currentIdx + 2)
        : [];

  return (
    <div className="page">
      <div className="page-header">
        <h1>{project.topic}</h1>
        <div className="page-actions">
          <button
            type="button"
            className="btn"
            onClick={handleDuplicate}
            disabled={transitioning}
          >
            Duplicate
          </button>
          {project.lifecycle_state !== "Archived" && (
            <button
              type="button"
              className="btn btn-danger"
              onClick={handleArchive}
              disabled={transitioning}
            >
              Archive
            </button>
          )}
        </div>
      </div>

      {error && <div className="page-error">{error}</div>}

      <div className="project-detail-grid">
        {/* Metadata section */}
        <section className="detail-section">
          <h2>Metadata</h2>
          <form onSubmit={handleSave} className="form-card">
            <label htmlFor="d-topic">Topic</label>
            <input
              id="d-topic"
              type="text"
              value={editTopic}
              onChange={(e) => {
                setEditTopic(e.target.value);
                setEditDirty(true);
              }}
            />

            <label htmlFor="d-platform">Platform Target</label>
            <select
              id="d-platform"
              value={editPlatform}
              onChange={(e) => {
                setEditPlatform(e.target.value);
                setEditDirty(true);
              }}
            >
              <option value="">— Select —</option>
              <option value="YouTube">YouTube</option>
              <option value="TikTok">TikTok</option>
              <option value="Instagram Reels">Instagram Reels</option>
              <option value="Facebook">Facebook</option>
              <option value="LinkedIn">LinkedIn</option>
              <option value="X (Twitter)">X (Twitter)</option>
              <option value="Other">Other</option>
            </select>

            <label htmlFor="d-format">Format</label>
            <select
              id="d-format"
              value={editFormat}
              onChange={(e) => {
                setEditFormat(e.target.value);
                setEditDirty(true);
              }}
            >
              <option value="">— Select —</option>
              <option value="Short (15-60s)">Short (15-60s)</option>
              <option value="Medium (1-3min)">Medium (1-3min)</option>
              <option value="Long (3-10min)">Long (3-10min)</option>
            </select>

            {editDirty && (
              <button
                type="submit"
                disabled={saving}
                className="btn btn-primary"
              >
                {saving ? "Saving…" : "Save Changes"}
              </button>
            )}
          </form>
        </section>

        {/* Lifecycle section */}
        <section className="detail-section">
          <h2>Lifecycle</h2>
          <div className="lifecycle-info">
            <p>
              Current state:{" "}
              <span className="state-badge">{project.lifecycle_state}</span>
            </p>
            <p className="project-action">{project.next_required_action}</p>
          </div>

          {validNextStates.length >= 2 && (
            <div className="transition-controls">
              <label htmlFor="transition-target">Transition to</label>
              <select
                id="transition-target"
                value={transitionTarget}
                onChange={(e) => setTransitionTarget(e.target.value)}
                disabled={transitioning}
              >
                <option value="">— Select state —</option>
                {validNextStates
                  .filter((s) => s !== project.lifecycle_state)
                  .map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
              </select>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleTransition}
                disabled={transitioning || !transitionTarget}
              >
                {transitioning ? "Transitioning…" : "Transition"}
              </button>
            </div>
          )}
        </section>

        {/* Studio navigation */}
        <section className="detail-section">
          <h2>Studio</h2>
          <div className="studio-nav">
            <Link to={`/projects/${projectId}/research`} className="btn">
              Research Review
            </Link>
            <Link to={`/projects/${projectId}/script`} className="btn">
              Script Editor
            </Link>
            <Link to={`/projects/${projectId}/characters`} className="btn">
              Character Setup
            </Link>
            <Link to={`/projects/${projectId}/scenes`} className="btn">
              Scene Builder
            </Link>
            <Link to={`/projects/${projectId}/scene-media`} className="btn">
              Scene Media
            </Link>
            <Link to={`/projects/${projectId}/tasks`} className="btn">
              Generation Tasks
            </Link>
          </div>
        </section>

        {/* Info section */}
        <section className="detail-section">
          <h2>Details</h2>
          <dl className="detail-list">
            <dt>Owner</dt>
            <dd>{project.owner_username}</dd>
            <dt>Team</dt>
            <dd>{project.team_name}</dd>
            <dt>Created</dt>
            <dd>{new Date(project.created_at).toLocaleString()}</dd>
            <dt>Updated</dt>
            <dd>{new Date(project.updated_at).toLocaleString()}</dd>
          </dl>
        </section>
      </div>
    </div>
  );
}
