import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listProjects, type Project } from "../api/projects";
import { listNotifications, type Notification } from "../api/notifications";
import { ApiError } from "../api/client";

export function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      listProjects().catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          return { projects: [] };
        }
        throw err;
      }),
      listNotifications().catch(() => ({ notifications: [] })),
    ])
      .then(([projRes, notifRes]) => {
        setProjects(projRes.projects);
        setNotifications(notifRes.notifications);
      })
      .catch(() => setError("Failed to load dashboard"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="page-loading">Loading dashboard…</div>;
  }

  if (error) {
    return <div className="page-error">{error}</div>;
  }

  const unread = notifications.filter((n) => !n.read).length;

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <Link to="/projects/new" className="btn btn-primary">
          New Project
        </Link>
      </div>

      {unread > 0 && (
        <div className="notification-badge">
          You have {unread} unread notification{unread !== 1 ? "s" : ""}.
          <Link to="/notifications"> View</Link>
        </div>
      )}

      <section className="dashboard-section">
        <h2>Projects</h2>
        {projects.length === 0 ? (
          <div className="empty-state">
            <p>No projects yet. Create your first project to get started.</p>
            <Link to="/projects/new" className="btn btn-primary">
              Create Project
            </Link>
          </div>
        ) : (
          <div className="project-grid">
            {projects.map((p) => (
              <Link
                key={p.id}
                to={`/projects/${p.id}`}
                className="project-card"
              >
                <div className="project-card-header">
                  <span className="project-state">{p.lifecycle_state}</span>
                </div>
                <h3 className="project-topic">{p.topic}</h3>
                {p.platform_target && (
                  <span className="project-meta">
                    Platform: {p.platform_target}
                  </span>
                )}
                {p.format && (
                  <span className="project-meta">Format: {p.format}</span>
                )}
                <p className="project-action">{p.next_required_action}</p>
              </Link>
            ))}
          </div>
        )}
      </section>

      <section className="dashboard-section">
        <h2>Recent Notifications</h2>
        {notifications.length === 0 ? (
          <p className="empty-text">No notifications yet.</p>
        ) : (
          <ul className="notification-list">
            {notifications.slice(0, 5).map((n) => (
              <li key={n.id} className={n.read ? "" : "unread"}>
                <strong>{n.title}</strong>
                <span>{n.message}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
