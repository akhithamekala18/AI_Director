import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listProjects, type Project } from "../api/projects";
import { ApiError } from "../api/client";

export function ProjectList() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    listProjects(includeArchived)
      .then((res) => setProjects(res.projects))
      .catch((err) => {
        if (err instanceof ApiError) {
          setError(`Failed to load projects (${err.status})`);
        } else {
          setError("Failed to load projects");
        }
      })
      .finally(() => setLoading(false));
  }, [includeArchived]);

  return (
    <div className="page">
      <div className="page-header">
        <h1>Projects</h1>
        <div className="page-actions">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(e) => setIncludeArchived(e.target.checked)}
            />
            Include archived
          </label>
          <Link to="/projects/new" className="btn btn-primary">
            New Project
          </Link>
        </div>
      </div>

      {loading && <p className="page-loading">Loading…</p>}
      {error && <div className="page-error">{error}</div>}

      {!loading && !error && projects.length === 0 && (
        <div className="empty-state">
          <p>No projects found.</p>
        </div>
      )}

      {!loading && !error && projects.length > 0 && (
        <table className="project-table">
          <thead>
            <tr>
              <th>Topic</th>
              <th>State</th>
              <th>Platform</th>
              <th>Format</th>
              <th>Next Action</th>
              <th>Owner</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((p) => (
              <tr key={p.id}>
                <td>
                  <Link to={`/projects/${p.id}`}>{p.topic}</Link>
                </td>
                <td>
                  <span className={`state-badge state-${p.lifecycle_state.toLowerCase().replace(/\s+/g, "-")}`}>
                    {p.lifecycle_state}
                  </span>
                </td>
                <td>{p.platform_target || "—"}</td>
                <td>{p.format || "—"}</td>
                <td>{p.next_required_action}</td>
                <td>{p.owner_username}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
