import { useEffect, useState } from "react";
import {
  listNotifications,
  markNotificationRead,
  type Notification,
} from "../api/notifications";

export function Notifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listNotifications()
      .then((res) => setNotifications(res.notifications))
      .catch(() => setError("Failed to load notifications"))
      .finally(() => setLoading(false));
  }, []);

  const handleMarkRead = async (pk: number) => {
    try {
      const res = await markNotificationRead(pk);
      setNotifications((prev) =>
        prev.map((n) =>
          n.id === pk ? { ...n, ...res.notification } : n,
        ),
      );
    } catch {
      // Silently ignore — notification may already be read
    }
  };

  if (loading) return <div className="page-loading">Loading notifications…</div>;

  return (
    <div className="page">
      <h1>Notifications</h1>
      {error && <div className="page-error">{error}</div>}

      {notifications.length === 0 ? (
        <div className="empty-state">
          <p>No notifications yet.</p>
        </div>
      ) : (
        <ul className="notification-list full">
          {notifications.map((n) => (
            <li
              key={n.id}
              className={`notification-item ${n.read ? "read" : "unread"}`}
            >
              <div className="notification-content">
                <div className="notification-header">
                  <strong>{n.title}</strong>
                  <span className="notification-type">{n.type}</span>
                  <span className="notification-date">
                    {new Date(n.created_at).toLocaleString()}
                  </span>
                </div>
                <p>{n.message}</p>
                {n.artifact_type && n.artifact_id && (
                  <span className="notification-artifact">
                    {n.artifact_type} #{n.artifact_id}
                  </span>
                )}
              </div>
              {!n.read && (
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => handleMarkRead(n.id)}
                >
                  Mark read
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
